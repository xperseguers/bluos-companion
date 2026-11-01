"""The script that runs before something new plays (to switch on an amplifier, for instance)."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from .conftest import calls

PRESET = "/Preset?id=1"
ADD_LAST = "/Add?file=a&playnow=-1&service=LocalMusic&where=last"
PLAY_NOW = "/Add?playnow=1&service=LocalMusic&album=x"


def _stop(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The player does not play."""
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data(replace(coordinator.data, state="stop"))


async def _play(hass: HomeAssistant, hass_ws_client: WebSocketGenerator, entry: MockConfigEntry, path: str) -> dict:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/play", "entry_id": entry.entry_id, "path": path}
    )
    return await client.receive_json()


@pytest.mark.parametrize("path", [PRESET, PLAY_NOW])
async def test_the_script_runs_before_something_starts(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    path: str,
) -> None:
    """The script is called, with the player, and the player is asked after it."""
    hass.config_entries.async_update_entry(init_integration, options={"before_playback_script": "script.onkyo"})
    _stop(hass, init_integration)
    order: list[str] = []

    async def script(call: ServiceCall) -> None:
        order.append(f"script {call.data['player']} {len(calls(player_api))} requests so far")

    hass.services.async_register("script", "onkyo", script)
    response = await _play(hass, hass_ws_client, init_integration, path)

    assert response["success"]
    assert order == ["script media_player.sejour 0 requests so far"]
    assert len(calls(player_api)) == 1


@pytest.mark.parametrize(
    ("playing", "path"),
    [(True, PRESET), (False, ADD_LAST)],
    ids=["the player plays already", "only added to the queue"],
)
async def test_the_script_is_left_out_when_there_is_no_need(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    playing: bool,
    path: str,
) -> None:
    """Nothing runs while the player plays (the amplifier is on), nor when nothing starts."""
    hass.config_entries.async_update_entry(init_integration, options={"before_playback_script": "script.onkyo"})
    if not playing:
        _stop(hass, init_integration)
    ran = async_mock_service(hass, "script", "onkyo")
    response = await _play(hass, hass_ws_client, init_integration, path)

    assert response["success"]
    assert not ran
    assert len(calls(player_api)) == 1


async def test_nothing_runs_without_the_option(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Without a script chosen, playing is as before."""
    _stop(hass, init_integration)
    ran = async_mock_service(hass, "script", "onkyo")
    assert (await _play(hass, hass_ws_client, init_integration, PRESET))["success"]
    assert not ran


async def test_a_failing_script_stops_the_playback(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The error of the script is shown and the player is not asked to play."""
    hass.config_entries.async_update_entry(init_integration, options={"before_playback_script": "script.onkyo"})
    _stop(hass, init_integration)

    async def script(call: ServiceCall) -> None:
        raise HomeAssistantError("the plug does not answer")

    hass.services.async_register("script", "onkyo", script)
    response = await _play(hass, hass_ws_client, init_integration, PRESET)

    assert not response["success"]
    assert "the plug does not answer" in response["error"]["message"]
    assert not calls(player_api)


async def test_a_script_that_takes_too_long_stops_the_playback(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """After the delay the playback is given up, with a clear message."""
    hass.config_entries.async_update_entry(init_integration, options={"before_playback_script": "script.onkyo"})
    _stop(hass, init_integration)

    async def script(call: ServiceCall) -> None:
        raise TimeoutError

    hass.services.async_register("script", "onkyo", script)
    with patch("custom_components.bluos_companion.coordinator.BEFORE_PLAYBACK_TIMEOUT", 5):
        response = await _play(hass, hass_ws_client, init_integration, PRESET)

    assert not response["success"]
    assert not calls(player_api)


async def test_the_media_player_runs_the_script_too(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Resuming from Home Assistant needs the amplifier as well."""
    hass.config_entries.async_update_entry(init_integration, options={"before_playback_script": "script.onkyo"})
    _stop(hass, init_integration)
    ran = async_mock_service(hass, "script", "onkyo")

    await hass.services.async_call("media_player", "media_play", {"entity_id": "media_player.sejour"}, blocking=True)

    assert len(ran) == 1


async def test_the_options_take_a_script(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The script is chosen in the options of the player."""
    player_api.get(f"http://192.168.1.100:11000/Browse", text="<browse/>")
    config_entry.add_to_hass(hass)
    with patch("custom_components.bluos_companion.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"before_playback_script": "script.onkyo"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options["before_playback_script"] == "script.onkyo"
