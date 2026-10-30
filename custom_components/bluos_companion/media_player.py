"""Media player entity for a BluOS player."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import datetime
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    SearchMedia,
    SearchMediaQuery,
    async_process_play_media_url,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import BluOSError
from .const import CONF_PORT, DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .media_search import async_search
from .media_source import URI_PREFIX, play_path_from_media_id

STATES = {
    "play": MediaPlayerState.PLAYING,
    "stream": MediaPlayerState.PLAYING,
    "pause": MediaPlayerState.PAUSED,
    "connecting": MediaPlayerState.BUFFERING,
}
SEARCH_CLASSES = {
    "artist": [MediaClass.ARTIST],
    "album": [MediaClass.ALBUM],
    "track": [MediaClass.TRACK],
    "playlist": [MediaClass.PLAYLIST],
}
REPEAT_TO_BLUOS = {RepeatMode.ALL: 0, RepeatMode.ONE: 1, RepeatMode.OFF: 2}
REPEAT_FROM_BLUOS = {value: key for key, value in REPEAT_TO_BLUOS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the media player."""
    async_add_entities([BluOSMediaPlayer(entry.runtime_data)])


class BluOSMediaPlayer(CoordinatorEntity[BluOSCoordinator], MediaPlayerEntity):
    """A BluOS player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_media_image_remotely_accessible = False
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.SEEK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SHUFFLE_SET
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.GROUPING
        | MediaPlayerEntityFeature.CLEAR_PLAYLIST
        | MediaPlayerEntityFeature.SEARCH_MEDIA
    )

    def __init__(self, coordinator: BluOSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._client = coordinator.client
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title,
            manufacturer="BluOS",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )
        self._position_updated_at: datetime | None = None

    def _handle_coordinator_update(self) -> None:
        self._position_updated_at = dt_util.utcnow()
        super()._handle_coordinator_update()

    @property
    def state(self) -> MediaPlayerState:
        """Return the playback state."""
        return STATES.get(self.coordinator.data.state, MediaPlayerState.IDLE)

    @property
    def volume_level(self) -> float | None:
        """Return the volume, None when the player has a fixed volume."""
        volume = self.coordinator.data.volume
        return volume / 100 if volume >= 0 else None

    @property
    def is_volume_muted(self) -> bool:
        """Return whether the player is muted."""
        return self.coordinator.data.muted

    @property
    def shuffle(self) -> bool:
        """Return whether shuffle is on."""
        return self.coordinator.data.shuffle

    @property
    def repeat(self) -> RepeatMode:
        """Return the repeat mode."""
        return REPEAT_FROM_BLUOS.get(self.coordinator.data.repeat, RepeatMode.OFF)

    @property
    def source_list(self) -> list[str]:
        """Return the inputs that can be selected."""
        return self.coordinator.source_names

    @property
    def source(self) -> str | None:
        """Return the active input, if the player is playing one."""
        return self.coordinator.active_source

    @property
    def group_members(self) -> list[str] | None:
        """Return the entity ids of the players playing together, primary first."""
        if (sync := self.coordinator.sync) is None or not sync.is_grouped:
            return None
        if sync.master is not None:
            master = self._coordinator_of(sync.master.host)
            if master is None or master.sync is None:
                return None
            hosts = [sync.master.host, *(m.host for m in master.sync.slaves)]
        else:
            hosts = [self._host, *(m.host for m in sync.slaves)]
        registry = er.async_get(self.hass)
        entity_ids = (self._entity_id_of(registry, host) for host in hosts)
        return [entity_id for entity_id in entity_ids if entity_id]

    def _coordinator_of(self, host: str) -> BluOSCoordinator | None:
        for entry in self.hass.config_entries.async_loaded_entries(DOMAIN):
            if entry.data[CONF_HOST] == host:
                return entry.runtime_data
        return None

    def _entity_id_of(self, registry: er.EntityRegistry, host: str) -> str | None:
        coordinator = self._coordinator_of(host)
        if coordinator is None or not coordinator.config_entry.unique_id:
            return None
        return registry.async_get_entity_id(
            "media_player", DOMAIN, coordinator.config_entry.unique_id
        )

    @property
    def _host(self) -> str:
        return self.coordinator.config_entry.data[CONF_HOST]

    @property
    def media_title(self) -> str | None:
        """Return the title of the current media."""
        return self.coordinator.data.title

    @property
    def media_artist(self) -> str | None:
        """Return the artist of the current media."""
        return self.coordinator.data.artist

    @property
    def media_album_name(self) -> str | None:
        """Return the album of the current media."""
        return self.coordinator.data.album

    @property
    def app_name(self) -> str | None:
        """Return the music service."""
        return self.coordinator.data.service

    @property
    def media_duration(self) -> int | None:
        """Return the duration of the current media."""
        return self.coordinator.data.duration

    @property
    def media_position(self) -> int | None:
        """Return the position in the current media."""
        return self.coordinator.data.position

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the position was last reported."""
        return self._position_updated_at

    @property
    def media_image_url(self) -> str | None:
        """Return the cover URL, fetched by Home Assistant and proxied to the UI."""
        if not (image := self.coordinator.data.image):
            return None
        if image.startswith(("http://", "https://")):
            return image
        return f"{self._client.base_url}{image}"

    async def _async_call(self, call: Awaitable[None]) -> None:
        try:
            await call
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err

    async def async_media_play(self) -> None:
        """Resume playback."""
        await self._async_call(self._client.async_play())

    async def async_media_pause(self) -> None:
        """Pause playback."""
        await self._async_call(self._client.async_pause())

    async def async_media_stop(self) -> None:
        """Stop playback."""
        await self._async_call(self._client.async_stop())

    async def async_media_next_track(self) -> None:
        """Skip to the next track."""
        await self._async_call(self._client.async_skip())

    async def async_media_previous_track(self) -> None:
        """Go back to the previous track."""
        await self._async_call(self._client.async_back())

    async def async_media_seek(self, position: float) -> None:
        """Seek in the current track."""
        await self._async_call(self._client.async_seek(int(position)))

    async def async_set_volume_level(self, volume: float) -> None:
        """Set the volume."""
        level = min(round(volume * 100), self.coordinator.max_volume)
        await self._async_call(self._client.async_set_volume(level))

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        await self._async_call(self._client.async_set_mute(mute))

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle."""
        await self._async_call(self._client.async_set_shuffle(shuffle))

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat."""
        await self._async_call(self._client.async_set_repeat(REPEAT_TO_BLUOS[repeat]))

    async def async_select_source(self, source: str) -> None:
        """Switch to an input."""
        await self._async_call(self.coordinator.async_select_source(source))

    async def async_clear_playlist(self) -> None:
        """Empty the play queue."""
        await self._async_call(self._client.async_clear_queue())

    async def async_join_players(self, group_members: list[str]) -> None:
        """Add players to the group of this one, which becomes the primary player."""
        registry = er.async_get(self.hass)
        entries = [
            self._entry_of_entity(registry, entity_id)
            for entity_id in group_members
            if entity_id != self.entity_id
        ]
        # Check everything first so that a refusal leaves the group untouched
        self.coordinator.ensure_can_group()
        for entry in entries:
            entry.runtime_data.ensure_can_group()
        for entry in entries:
            await self._async_call(
                self._client.async_add_slave(
                    entry.data[CONF_HOST], entry.data[CONF_PORT]
                )
            )

    async def async_unjoin_player(self) -> None:
        """Leave the group. The primary player dissolves the whole group."""
        sync = self.coordinator.sync
        if sync is None:
            return
        if sync.master is not None:
            master = self._coordinator_of(sync.master.host)
            if master is None:
                raise HomeAssistantError("The primary player of the group is not configured")
            await self._async_call(
                master.client.async_remove_slave(
                    self._host, self.coordinator.config_entry.data[CONF_PORT]
                )
            )
            return
        for member in sync.slaves:
            await self._async_call(
                self._client.async_remove_slave(member.host, member.port)
            )

    def _entry_of_entity(self, registry: er.EntityRegistry, entity_id: str) -> ConfigEntry:
        entity = registry.async_get(entity_id)
        entry = (
            self.hass.config_entries.async_get_entry(entity.config_entry_id)
            if entity and entity.config_entry_id
            else None
        )
        if entry is None or entry.domain != DOMAIN:
            raise HomeAssistantError(f"{entity_id} is not a BluOS Companion player")
        return entry

    async def async_search_media(self, query: SearchMediaQuery) -> SearchMedia:
        """Search the library, the saved playlists and the presets (Assist, AI agents)."""
        return await async_search(self._client, self.coordinator.config_entry.entry_id, query)

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        """Browse the library of this player."""
        if media_content_id is None or not media_content_id.startswith(URI_PREFIX):
            media_content_id = f"{URI_PREFIX}{self.coordinator.config_entry.entry_id}"
        return await media_source.async_browse_media(self.hass, media_content_id)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play a library item, or any other media source / URL."""
        if media_id.startswith(URI_PREFIX):
            entry_id, path = play_path_from_media_id(media_id)
            if entry_id != self.coordinator.config_entry.entry_id:
                raise HomeAssistantError("This item belongs to another player")
            await self._async_call(self._client.async_command(path))
            return

        if media_source.is_media_source_id(media_id):
            play_item = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            media_id = play_item.url
        elif not media_id.startswith(("http://", "https://", "/")):
            # A name, as AI agents ask for: play the best match of a search.
            results = await self.async_search_media(
                SearchMediaQuery(
                    search_query=media_id,
                    media_content_type=media_type,
                    media_filter_classes=SEARCH_CLASSES.get(str(media_type).lower()),
                )
            )
            if not results.result:
                raise HomeAssistantError(f"No results found for {media_id}")
            _, path = play_path_from_media_id(results.result[0].media_content_id)
            await self._async_call(self._client.async_command(path))
            return
        url = async_process_play_media_url(self.hass, media_id)
        await self._async_call(self._client.async_command("/Play", {"url": url}))
