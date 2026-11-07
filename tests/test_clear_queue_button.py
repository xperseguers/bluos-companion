"""Tests for the Clear queue button of a player."""

from __future__ import annotations

import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import BASE, calls, respond

ENTITY_ID = "button.sejour_clear_queue"


async def test_the_button_clears_the_queue(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """Pressing the button empties the queue of the player."""
    await hass.services.async_call("button", "press", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert calls(player_api) == [("/Clear", {})]


async def test_a_failing_player_is_an_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player that cannot be reached raises a readable error."""
    respond(player_api, f"{BASE}/Clear", status=500)
    with pytest.raises(HomeAssistantError, match="BluOS player error"):
        await hass.services.async_call(
            "button", "press", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )
