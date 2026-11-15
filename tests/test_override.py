"""Volume, inputs and power of a player that are those of other entities (options of the integration)."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service
from pytest_homeassistant_custom_component.typing import WebSocketGenerator
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import calls

AMPLIFIER = "media_player.amplifier"
PLUG = "switch.amplifier_plug"


@pytest.fixture
def override(hass: HomeAssistant, init_integration: MockConfigEntry) -> MockConfigEntry:
    """Choose an amplifier for the volume and the inputs, and a plug for the power."""
    hass.states.async_set(
        AMPLIFIER,
        "on",
        {"volume_level": 0.35, "is_volume_muted": False, "source_list": ["Phono", "Aux"], "source": "Aux"},
    )
    hass.states.async_set(PLUG, "on")
    hass.config_entries.async_update_entry(
        init_integration,
        options={"volume_entity": AMPLIFIER, "source_entity": AMPLIFIER, "power_entity": PLUG},
    )
    return init_integration


async def _players(hass: HomeAssistant, client: Any) -> list[dict[str, Any]]:
    await client.send_json_auto_id({"type": "bluos_companion/subscribe"})
    assert (await client.receive_json())["success"]
    return (await client.receive_json())["event"]["players"]


async def test_the_entities_replace_what_the_player_reports(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, override: MockConfigEntry
) -> None:
    """The panel and the cards read the volume, the inputs and the power of the chosen entities."""
    client = await hass_ws_client(hass)
    player = (await _players(hass, client))[0]
    assert (player["volume"], player["max_volume"], player["muted"]) == (35, 100, False)
    assert (player["sources"], player["source"], player["power"]) == (["Phono", "Aux"], "Aux", True)

    hass.states.async_set(PLUG, "off")
    assert (await client.receive_json())["event"]["players"][0]["power"] is False
    hass.states.async_set(AMPLIFIER, "on", {"volume_level": 0.5, "is_volume_muted": True, "source_list": ["Phono"], "source": "Phono"})
    player = (await client.receive_json())["event"]["players"][0]
    assert (player["volume"], player["muted"], player["sources"], player["source"]) == (50, True, ["Phono"], "Phono")
    assert player["power"] is False


async def test_an_entity_without_volume_is_fixed(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, override: MockConfigEntry
) -> None:
    """The volume of an amplifier that is off or gone shows as fixed, and its power as unknown."""
    hass.states.async_set(AMPLIFIER, "unavailable")
    hass.states.async_set(PLUG, "unavailable")
    client = await hass_ws_client(hass)
    player = (await _players(hass, client))[0]
    assert player["volume"] == -1
    assert player["power"] is None


@pytest.mark.parametrize(
    ("message", "domain", "service", "data"),
    [
        ({"action": "volume", "value": 40}, "media_player", "volume_set", {"entity_id": AMPLIFIER, "volume_level": 0.4}),
        ({"action": "volume_step", "value": 2}, "media_player", "volume_set", {"entity_id": AMPLIFIER, "volume_level": 0.37}),
        ({"action": "volume_step", "value": -50}, "media_player", "volume_set", {"entity_id": AMPLIFIER, "volume_level": 0.0}),
        ({"action": "mute", "value": True}, "media_player", "volume_mute", {"entity_id": AMPLIFIER, "is_volume_muted": True}),
        ({"action": "source", "value": "Phono"}, "media_player", "select_source", {"entity_id": AMPLIFIER, "source": "Phono"}),
        ({"action": "power", "value": False}, "homeassistant", "turn_off", {"entity_id": PLUG}),
        ({"action": "power", "value": True}, "homeassistant", "turn_on", {"entity_id": PLUG}),
    ],
)
async def test_controls_drive_the_entities(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    override: MockConfigEntry,
    player_api: AiohttpClientMocker,
    message: dict[str, Any],
    domain: str,
    service: str,
    data: dict[str, Any],
) -> None:
    """The commands of the panel go to the chosen entities and not to the player."""
    seen = async_mock_service(hass, domain, service)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/control", "entry_id": override.entry_id, **message})
    assert (await client.receive_json())["success"]
    assert [call.data for call in seen] == [data]
    assert calls(player_api) == []


async def test_the_volume_of_a_group_stays_with_the_players(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    override: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Only the own volume of the player is replaced, not the volume of its group."""
    seen = async_mock_service(hass, "media_player", "volume_set")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/control", "entry_id": override.entry_id, "action": "volume_step", "value": 2, "group": True}
    )
    assert (await client.receive_json())["success"]
    assert not seen
    assert calls(player_api) == [("/Volume", {"db": "2", "tell_slaves": "1"})]


async def test_without_entities_the_player_does_everything(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Nothing chosen in the options: the volume goes to the player."""
    seen = async_mock_service(hass, "media_player", "volume_set")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/control", "entry_id": init_integration.entry_id, "action": "volume", "value": 30}
    )
    assert (await client.receive_json())["success"]
    assert not seen
    assert calls(player_api) == [("/Volume", {"level": "30"})]
