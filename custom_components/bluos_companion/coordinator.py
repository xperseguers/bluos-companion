"""Keep the playback status of a player up to date."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BluOSClient, BluOSError, Source, Status, SyncStatus
from .const import CONF_MAX_VOLUME, DOMAIN, EXTERNAL_SOURCE_URL, LONG_POLL_TIMEOUT, MIN_POLL_INTERVAL, RETRY_INTERVAL

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

    @property
    def max_volume(self) -> int:
        """Return the volume (0..100) the player may be set to from Home Assistant."""
        return int(self.config_entry.options.get(CONF_MAX_VOLUME, 100))

    def _input_name(self, source: Source) -> str:
        """Return the name of a player input, told apart from an amplifier input."""
        if self.sync and any(
            external.name == source.name for external in self.sync.external_sources
        ):
            return f"{source.name} (BluOS)"
        return source.name

    @property
    def source_names(self) -> list[str]:
        """Return the inputs that can be selected."""
        names = [self._input_name(source) for source in self.sources]
        if self.sync:
            names += [source.name for source in self.sync.external_sources]
        return names

    @property
    def active_source(self) -> str | None:
        """Return the active input, if the player is playing one."""
        if self.data.stream_url == EXTERNAL_SOURCE_URL and self.sync:
            return self.sync.external_source
        return next(
            (
                self._input_name(source)
                for source in self.sources
                if source.url == self.data.stream_url
            ),
            None,
        )

    async def async_select_source(self, name: str) -> None:
        """Switch to an input of the player or of the amplifier it is built in."""
        for source in self.sources:
            if self._input_name(source) == name:
                await self.client.async_select_source(source.type_index)
                return
        for external in self.sync.external_sources if self.sync else ():
            if external.name == name:
                await self.client.async_select_external_source(external.id)
                return
        raise HomeAssistantError(f"Unknown source: {name}")

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
