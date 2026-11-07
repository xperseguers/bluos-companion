"""Tests for clearing the recent stations and the recently played."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, respond

ENTITY_ID = "media_player.sejour"
CLEAR = "/ui/clearUsageHistory"


@pytest.fixture(autouse=True)
def clearing(player_api: AiohttpClientMocker) -> None:
    """The player answers the clear requests."""
    respond(player_api, f"{BASE}{CLEAR}", text="<ok/>")


@pytest.mark.parametrize(
    ("what", "expected"),
    [
        ("stations", [{"stations": "1"}]),
        ("played", [{"queued": "1"}]),
        ("both", [{"stations": "1"}, {"queued": "1"}]),
    ],
)
async def test_the_service_clears_what_is_asked(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    what: str,
    expected: list[dict[str, str]],
) -> None:
    """Each list has its own request, and both are cleared by default."""
    data = {"entity_id": ENTITY_ID} | ({} if what == "both" else {"what": what})
    await hass.services.async_call(DOMAIN, "clear_history", data, blocking=True)
    assert calls(player_api) == [(CLEAR, query) for query in expected]
    # The player's own screens are asked for with the headers of its app
    assert player_api.mock_calls[0][3]["x-sovi-schema-version"] == "35"


async def test_a_failing_player_is_an_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player that cannot be reached raises a readable error."""
    respond(player_api, f"{BASE}{CLEAR}", status=500)
    with pytest.raises(HomeAssistantError, match="BluOS player error"):
        await hass.services.async_call(
            DOMAIN, "clear_history", {"entity_id": ENTITY_ID}, blocking=True
        )


@pytest.mark.parametrize(("what", "query"), [("stations", {"stations": "1"}), ("played", {"queued": "1"})])
async def test_the_panel_clears_a_list(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    what: str,
    query: dict[str, str],
) -> None:
    """The panel clears the recent stations or the recently played, one list at a time."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/clear_history", "entry_id": init_integration.entry_id, "what": what}
    )
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [(CLEAR, query)]


async def test_the_panel_refuses_other_lists(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """Only the two lists can be cleared."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/clear_history", "entry_id": init_integration.entry_id, "what": "queue"}
    )
    assert not (await client.receive_json())["success"]
