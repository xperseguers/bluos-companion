"""Tests for the check of the album covers."""

from __future__ import annotations

import hashlib
from urllib.parse import quote

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion import cover_check
from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, respond

PLACEHOLDER = b"Artwork Too Large"
SECTION_A = """<albums service="LocalMusic"><sections><section name="A">
  <album tracks="3"><title>Big</title><art>Artist</art></album>
  <album tracks="3"><title>Small</title><art>Artist</art></album>
</section></sections></albums>"""
SECTION_OTHER = """<albums service="LocalMusic"><sections><section name="#">
  <album tracks="3"><title>2 Big</title><art>Other</art></album>
  <album tracks="3"><title>Broken</title><art>Other</art></album>
</section></sections></albums>"""


@pytest.fixture
def library(
    player_api: AiohttpClientMocker, monkeypatch: pytest.MonkeyPatch
) -> AiohttpClientMocker:
    """A library of four albums: two too large, one unreadable, one fine."""
    monkeypatch.setattr(
        cover_check, "PLACEHOLDER_SHA256", frozenset({hashlib.sha256(PLACEHOLDER).hexdigest()})
    )
    respond(player_api, f"{BASE}/Albums?service=LocalMusic&section=A", text=SECTION_A)
    respond(player_api, f"{BASE}/Albums?service=LocalMusic&section=%23", text=SECTION_OTHER)
    for album, artist, kwargs in (
        ("Big", "Artist", {"content": PLACEHOLDER}),
        ("Small", "Artist", {"content": b"a cover"}),
        ("2 Big", "Other", {"content": PLACEHOLDER}),
        ("Broken", "Other", {"status": 500}),
    ):
        respond(
            player_api,
            f"{BASE}/Artwork?service=LocalMusic&album={quote(album)}&artist={artist}",
            **kwargs,
        )
    player_api.mock_calls.clear()
    return player_api


async def _check(hass: HomeAssistant) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "check_covers",
        {"entity_id": "media_player.sejour"},
        blocking=True,
        return_response=True,
    )


async def test_check_lists_the_covers_that_are_too_large(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The service reads every cover and lists those the player replaced."""
    result = await _check(hass)

    assert result == {
        "checked": 4,
        "unreadable_covers": 1,
        "too_large": [
            {"artist": "Artist", "album": "Big"},
            {"artist": "Other", "album": "2 Big"},
        ],
    }
    assert sorted(path for path, _ in calls(library)).count("/Artwork") == 4


async def test_the_sensor_counts_them(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The sensor is unknown before the first check, then holds the count and the albums."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.unique_id}_covers_too_large"
    )
    assert hass.states.get(entity_id).state == "unknown"

    await _check(hass)

    state = hass.states.get(entity_id)
    assert state.state == "2"
    assert state.attributes["albums"] == ["Artist - Big", "Other - 2 Big"]
    assert (state.attributes["checked_albums"], state.attributes["unreadable_covers"]) == (4, 1)
    assert state.attributes["checking"] is False


async def test_a_check_cannot_run_twice_at_once(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """A second request while the covers are being read is refused."""
    init_integration.runtime_data.checking_covers = True
    with pytest.raises(HomeAssistantError, match="already"):
        await _check(hass)


async def test_the_button_checks_in_the_background(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """Pressing the button starts the check and the sensor shows the result."""
    registry = er.async_get(hass)
    button = registry.async_get_entity_id(
        "button", DOMAIN, f"{init_integration.unique_id}_check_covers"
    )
    sensor = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.unique_id}_covers_too_large"
    )

    await hass.services.async_call("button", "press", {ATTR_ENTITY_ID: button}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get(sensor).state == "2"
    assert hass.states.get(sensor).attributes["checking"] is False


async def test_the_button_refuses_a_second_check(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """Pressing the button while the covers are being read is refused."""
    button = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"{init_integration.unique_id}_check_covers"
    )
    init_integration.runtime_data.checking_covers = True
    with pytest.raises(HomeAssistantError, match="already"):
        await hass.services.async_call("button", "press", {ATTR_ENTITY_ID: button}, blocking=True)


async def test_the_sensor_comes_back_with_its_albums_after_a_restart(
    hass: HomeAssistant, config_entry: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The count and the list of the last check survive a restart of Home Assistant."""
    attributes = {"albums": ["Artist - Big"], "checked_albums": 4, "unreadable_covers": 0}
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State("sensor.sejour_covers_too_large", "1", attributes),
                {"native_value": 1, "native_unit_of_measurement": None},
            )
        ],
    )
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.bluos_companion.BluOSCoordinator.async_long_poll", new=AsyncMock()
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.sejour_covers_too_large")
    assert state.state == "1"
    assert state.attributes["albums"] == ["Artist - Big"]
    assert state.attributes["checked_albums"] == 4
