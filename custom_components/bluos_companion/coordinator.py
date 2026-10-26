"""Keep the playback status of a player up to date."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BluOSClient, BluOSError, Status
from .const import DOMAIN, LONG_POLL_TIMEOUT, MIN_POLL_INTERVAL, RETRY_INTERVAL

_LOGGER = logging.getLogger(__name__)

type BluOSConfigEntry = ConfigEntry[BluOSCoordinator]


class BluOSCoordinator(DataUpdateCoordinator[Status]):
    """Track the status of a player through long polling."""

    config_entry: BluOSConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: BluOSConfigEntry, client: BluOSClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.client = client

    async def _async_update_data(self) -> Status:
        try:
            return await self.client.async_get_status()
        except BluOSError as err:
            raise UpdateFailed(str(err)) from err

    async def async_long_poll(self) -> None:
        """Push status changes as the player reports them."""
        while True:
            etag = self.data.etag if self.data else None
            try:
                status = await self.client.async_get_status(etag, LONG_POLL_TIMEOUT)
            except BluOSError as err:
                _LOGGER.debug("Status poll failed: %s", err)
                self.last_update_success = False
                self.async_update_listeners()
                await asyncio.sleep(RETRY_INTERVAL)
                continue
            self.async_set_updated_data(status)
            await asyncio.sleep(MIN_POLL_INTERVAL)
