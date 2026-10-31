"""Keep the playback status of a player up to date."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BluOSClient, BluOSError, Source, Status, SyncStatus, VolumeState
from .amplifier import BluOSAmplifier
from .cover_check import CoverCheck, async_check_covers
from .settings import BluOSSettingsCoordinator
from .const import (
    CONF_MAX_VOLUME,
    DOMAIN,
    EXTERNAL_SOURCE_URL,
    INDEXING_POLL_INTERVAL,
    INDEXING_START_TIMEOUT,
    LONG_POLL_TIMEOUT,
    MIN_POLL_INTERVAL,
    RETRY_INTERVAL,
    VOLUME_IDLE_INTERVAL,
)

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
        self.settings = BluOSSettingsCoordinator(hass, entry, client)
        self.sources: list[Source] = []
        self._sync_stat: str | None = None
        # Cover (player path) of the first track of a playlist, with the time it was read.
        self.playlist_covers: dict[str, tuple[float, str | None]] = {}
        self.cover_check: CoverCheck | None = None
        self.checking_covers = False
        # Own volume and mute of a secondary player, whose /Status carries the group's
        self.own_volume: VolumeState | None = None
        # The amplifier the player is built into, if it answers on its control port
        self.amplifier: BluOSAmplifier | None = None

    @property
    def is_secondary(self) -> bool:
        """Return whether the player follows another one."""
        return self.sync is not None and self.sync.master is not None

    @property
    def volume_level(self) -> int:
        """Return the own volume of the player (0..100, -1 if fixed), not the group's."""
        if self.is_secondary and self.own_volume is not None:
            return self.own_volume.level
        return self.data.volume

    @property
    def is_muted(self) -> bool:
        """Return whether the player itself is muted, not the group."""
        if self.is_secondary and self.own_volume is not None:
            return self.own_volume.muted
        return self.data.muted

    @property
    def max_volume(self) -> int:
        """Return the volume (0..100) the player may be set to from Home Assistant."""
        return int(self.config_entry.options.get(CONF_MAX_VOLUME, 100))

    def ensure_can_group(self) -> None:
        """Refuse to group the second speaker of a stereo pair: the pair would be split."""
        if self.sync is not None and self.sync.pair_secondary:
            raise HomeAssistantError(
                f"{self.config_entry.title} is the second speaker of a stereo pair, "
                "group the first speaker of the pair instead"
            )

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

    def _library_owner(self) -> BluOSCoordinator:
        """Return the player that holds the library: a player grouped under another one has none."""
        if self.sync is not None and self.sync.master is not None:
            primary = self._coordinator_of(self.sync.master.host)
            if primary is None:
                raise HomeAssistantError("The primary player of the group is not configured")
            return primary
        return self

    def _begin_cover_check(self) -> None:
        if self.checking_covers:
            raise HomeAssistantError("The covers are already being checked")
        self.checking_covers = True
        self.async_update_listeners()

    async def _async_run_cover_check(self) -> CoverCheck:
        try:
            try:
                self.cover_check = await async_check_covers(self._library_owner().client)
            except BluOSError as err:
                raise HomeAssistantError(f"BluOS player error: {err}") from err
        finally:
            self.checking_covers = False
            self.async_update_listeners()
        return self.cover_check

    async def async_check_covers(self) -> CoverCheck:
        """Look for the covers the player does not show because they are too large."""
        self._begin_cover_check()
        return await self._async_run_cover_check()

    def async_start_cover_check(self) -> None:
        """Check the covers in the background, the sensor shows the result."""
        self._begin_cover_check()
        self.config_entry.async_create_background_task(
            self.hass, self._async_log_cover_check(), f"{DOMAIN} cover check"
        )

    async def _async_log_cover_check(self) -> None:
        try:
            await self._async_run_cover_check()
        except HomeAssistantError as err:
            _LOGGER.warning("Checking the covers of %s failed: %s", self.config_entry.title, err)

    async def async_reindex(self) -> None:
        """Start reading the library and follow the scan closely until it is over.

        A player grouped under another one does not read the library: the primary does.
        """
        primary = self._library_owner()
        await primary.client.async_reindex()
        for coordinator in {self, primary}:
            coordinator.config_entry.async_create_background_task(
                self.hass, coordinator._async_follow_indexing(), f"{DOMAIN} indexing"
            )

    def _coordinator_of(self, host: str) -> BluOSCoordinator | None:
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.data[CONF_HOST] == host:
                return entry.runtime_data
        return None

    async def _async_follow_indexing(self) -> None:
        """Poll the status often while the scan runs: its last count is short lived."""
        started = False
        deadline = time.monotonic() + INDEXING_START_TIMEOUT
        while started or time.monotonic() < deadline:
            await asyncio.sleep(INDEXING_POLL_INTERVAL)
            try:
                status = await self.client.async_get_status()
            except BluOSError as err:
                _LOGGER.debug("Status poll failed while indexing: %s", err)
                continue
            self.async_set_updated_data(status)
            if status.indexing:
                started = True
            elif started:
                return

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
        """Push status and own volume changes as the player reports them."""
        await asyncio.gather(self._async_poll_status(), self._async_poll_volume())

    async def _async_poll_volume(self) -> None:
        """Follow the own volume and mute of a secondary player, whose /Status shows the group's."""
        while True:
            if not self.is_secondary:
                if self.own_volume is not None:
                    self.own_volume = None
                    self.async_update_listeners()
                await asyncio.sleep(VOLUME_IDLE_INTERVAL)
                continue
            etag = self.own_volume.etag if self.own_volume else None
            try:
                volume = await self.client.async_poll_volume(etag, LONG_POLL_TIMEOUT)
            except BluOSError as err:
                _LOGGER.debug("Volume poll failed: %s", err)
                await asyncio.sleep(RETRY_INTERVAL)
                continue
            if volume != self.own_volume:
                self.own_volume = volume
                self.async_update_listeners()
            await asyncio.sleep(MIN_POLL_INTERVAL)

    async def _async_poll_status(self) -> None:
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
