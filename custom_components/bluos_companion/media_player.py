"""Media player entity for a BluOS player."""

from __future__ import annotations

from collections.abc import Awaitable
from datetime import datetime
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    async_process_play_media_url,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import BluOSError
from .const import DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .media_source import URI_PREFIX, play_path_from_media_id

STATES = {
    "play": MediaPlayerState.PLAYING,
    "stream": MediaPlayerState.PLAYING,
    "pause": MediaPlayerState.PAUSED,
    "connecting": MediaPlayerState.BUFFERING,
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
        await self._async_call(self._client.async_set_volume(round(volume * 100)))

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        await self._async_call(self._client.async_set_mute(mute))

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Set shuffle."""
        await self._async_call(self._client.async_set_shuffle(shuffle))

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        """Set repeat."""
        await self._async_call(self._client.async_set_repeat(REPEAT_TO_BLUOS[repeat]))

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
        url = async_process_play_media_url(self.hass, media_id)
        await self._async_call(self._client.async_command("/Play", {"url": url}))
