"""Tests for the mute switch of a player."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, respond, status_xml

ENTITY_ID = "switch.sejour_mute"


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry, xml: str, api: AiohttpClientMocker) -> None:
    respond(api, f"{BASE}/Status", text=xml)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_the_switch_shows_the_mute(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The switch follows the mute of the player."""
    assert hass.states.get(ENTITY_ID).state == STATE_OFF
    await _refresh(hass, init_integration, status_xml(mute="1"), player_api)
    assert hass.states.get(ENTITY_ID).state == STATE_ON


@pytest.mark.parametrize(
    ("service", "mute"),
    [("turn_on", "1"), ("turn_off", "0")],
)
async def test_the_switch_mutes_and_unmutes(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    service: str,
    mute: str,
) -> None:
    """Turning the switch on mutes the player, off unmutes it."""
    await hass.services.async_call("switch", service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert calls(player_api) == [("/Volume", {"mute": mute})]


async def test_the_switch_toggles(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """One tap flips the mute, which a media player cannot do."""
    await hass.services.async_call("switch", "toggle", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert calls(player_api) == [("/Volume", {"mute": "1"})]
    await _refresh(hass, init_integration, status_xml(mute="1"), player_api)
    player_api.mock_calls.clear()
    await hass.services.async_call("switch", "toggle", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True)
    assert calls(player_api) == [("/Volume", {"mute": "0"})]


async def test_a_failing_player_is_an_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player that cannot be reached raises a readable error."""
    respond(player_api, f"{BASE}/Volume", status=500)
    with pytest.raises(HomeAssistantError, match="BluOS player error"):
        await hass.services.async_call(
            "switch", "turn_on", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )


async def test_no_switch_for_a_fixed_volume(
    hass: HomeAssistant, config_entry: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player with a fixed volume cannot be muted: no switch."""
    respond(player_api, f"{BASE}/Status", text=status_xml(volume="-1"))
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.bluos_companion.BluOSCoordinator.async_long_poll", new=AsyncMock()
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    registry = er.async_get(hass)
    assert registry.async_get_entity_id("switch", DOMAIN, f"{config_entry.unique_id}_mute") is None
