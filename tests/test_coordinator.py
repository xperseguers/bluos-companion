"""Tests for the long polling loop."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import LONG_POLL_TIMEOUT, UNREACHABLE_INTERVAL

from .conftest import BASE, calls, status_xml

SLEEP = "custom_components.bluos_companion.coordinator.asyncio.sleep"


async def test_long_poll_pushes_changes(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The etag of the last status is sent and the new status is published."""
    coordinator = init_integration.runtime_data
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", text=status_xml("pause"))

    with patch(SLEEP, AsyncMock(side_effect=asyncio.CancelledError)):
        with pytest.raises(asyncio.CancelledError):
            await coordinator._async_poll_status()  # noqa: SLF001

    assert calls(player_api) == [
        ("/Status", {"timeout": str(LONG_POLL_TIMEOUT), "etag": "e1"})
    ]
    assert coordinator.data.state == "pause"


async def test_long_poll_marks_unavailable_on_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A failing player is reported unavailable and retried later."""
    coordinator = init_integration.runtime_data
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", exc=aiohttp.ClientError)

    with patch(SLEEP, AsyncMock(side_effect=asyncio.CancelledError)) as sleep:
        with pytest.raises(asyncio.CancelledError):
            await coordinator._async_poll_status()  # noqa: SLF001

    assert coordinator.last_update_success is False
    sleep.assert_awaited_once_with(UNREACHABLE_INTERVAL)


async def test_long_poll_survives_an_unexpected_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Whatever goes wrong in a poll, the loop goes on and the player shows as unavailable."""
    coordinator = init_integration.runtime_data
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", exc=ValueError("boom"))

    with patch(SLEEP, AsyncMock(side_effect=asyncio.CancelledError)) as sleep:
        with pytest.raises(asyncio.CancelledError):
            await coordinator._async_poll_status()  # noqa: SLF001

    assert coordinator.last_update_success is False
    sleep.assert_awaited_once_with(UNREACHABLE_INTERVAL)


async def test_command_refreshes_the_status(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A command is followed by a read of the status, without waiting for the long poll."""
    coordinator = init_integration.runtime_data
    player_api.clear_requests()
    player_api.get(f"{BASE}/Pause", text="<state>pause</state>")
    player_api.get(f"{BASE}/Status", text=status_xml("pause"))

    with patch(SLEEP, AsyncMock()):
        await coordinator.client.async_pause()
        await asyncio.gather(*init_integration._background_tasks)  # noqa: SLF001

    assert coordinator.data.state == "pause"
    assert [path for path, _ in calls(player_api)] == ["/Pause", "/Status", "/Status"]
