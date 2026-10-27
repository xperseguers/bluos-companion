"""Keep the playback status of a player up to date."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BluOSClient, BluOSError, Source, Status, SyncStatus
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
        self.sync: SyncStatus | None = None
        self.sources: list[Source] = []
        self._sync_stat: str | None = None

    async def _async_update_data(self) -> Status:
        try:
            status = await self.client.async_get_status()
            await self._async_refresh_sync(status)
        except BluOSError as err:
            raise UpdateFailed(str(err)) from err
        return status

    async def _async_refresh_sync(self, status: Status) -> None:
        """Reload the group and the inputs when the player says they changed."""
        if self.sync is not None and status.sync_stat == self._sync_stat:
            return
        self.sync = await self.client.async_get_sync_status()
        self._sync_stat = status.sync_stat
        try:
            self.sources = await self.client.async_get_sources()
        except BluOSError as err:
            _LOGGER.debug("Could not list the inputs: %s", err)

    async def async_long_poll(self) -> None:
        """Push status changes as the player reports them."""
        while True:
            etag = self.data.etag if self.data else None
            try:
                status = await self.client.async_get_status(etag, LONG_POLL_TIMEOUT)
                await self._async_refresh_sync(status)
            except BluOSError as err:
                _LOGGER.debug("Status poll failed: %s", err)
                self.last_update_success = False
                self.async_update_listeners()
                await asyncio.sleep(RETRY_INTERVAL)
                continue
            self.async_set_updated_data(status)
            await asyncio.sleep(MIN_POLL_INTERVAL)
