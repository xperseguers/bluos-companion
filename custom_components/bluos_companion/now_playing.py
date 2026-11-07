"""The answer to "what is playing?", for scripts, automations and announcements."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import MediaPlayerState, RepeatMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN
from .coordinator import BluOSCoordinator
from .media_player import REPEAT_FROM_BLUOS, STATES

PREFIX = f"component.{DOMAIN}.common."


async def async_now_playing(hass: HomeAssistant, coordinator: BluOSCoordinator) -> dict[str, Any]:
    """Return what a player plays, as data and as a sentence in the language of Home Assistant.

    Every key is always there, with None when the player does not say (a radio has no album).
    """
    status = coordinator.data
    state = STATES.get(status.state, MediaPlayerState.IDLE)
    sync = coordinator.sync
    others = (
        [member.name for member in ([sync.master] if sync.master else []) + list(sync.slaves)]
        if sync is not None and sync.is_grouped
        else []
    )
    volume = coordinator.volume_level
    texts = await async_get_translations(hass, hass.config.language, "common", [DOMAIN])
    if state == MediaPlayerState.IDLE or not status.title:
        text = texts[f"{PREFIX}now_playing_nothing"]
    elif status.artist:
        text = texts[f"{PREFIX}now_playing_by"].format(title=status.title, artist=status.artist)
    else:
        text = status.title
    return {
        "player": coordinator.config_entry.title,
        "state": str(state),
        "text": text,
        "title": status.title or None,
        "artist": status.artist or None,
        "album": status.album or None,
        "service": status.service or None,
        "service_name": status.service_name or None,
        "stream_format": status.stream_format or None,
        "quality": status.quality or None,
        "preset_name": status.preset_name or None,
        "position": status.position,
        "duration": status.duration,
        "queue_position": None if status.queue_position is None else status.queue_position + 1,
        "shuffle": status.shuffle,
        "repeat": str(REPEAT_FROM_BLUOS.get(status.repeat, RepeatMode.OFF)),
        "volume": None if volume < 0 else volume,
        "muted": coordinator.is_muted,
        "group_name": sync.group if sync is not None and sync.is_grouped else None,
        "grouped_with": others,
    }
