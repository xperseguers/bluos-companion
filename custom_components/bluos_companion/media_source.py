"""Expose the BluOS library, presets and playback as a Home Assistant media source."""

from __future__ import annotations

import base64
from urllib.parse import parse_qs

from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .api import Album, BluOSError
from .const import DOMAIN
from .coordinator import BluOSConfigEntry
from .http import async_artwork_url

URI_PREFIX = f"media-source://{DOMAIN}/"
PLAY_PATH_PREFIXES = ("/Add?", "/Preset?", "/Load?")


async def async_get_media_source(hass: HomeAssistant) -> BluOSMediaSource:
    """Set up the media source."""
    return BluOSMediaSource(hass)


def _encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _decode(value: str) -> str:
    try:
        return base64.b64decode(value, altchars=b"-_", validate=True).decode()
    except ValueError as err:
        raise BrowseError("Invalid media identifier") from err


def play_path_from_media_id(media_id: str) -> tuple[str, str]:
    """Return the entry id and the player path that plays a media id."""
    parts = media_id.removeprefix(URI_PREFIX).split("/")
    match parts:
        case [entry_id, "album", query]:
            path = f"/Add?playnow=1&service=LocalMusic&{_decode(query)}"
        case [entry_id, "track", encoded_path]:
            path = _decode(encoded_path)
        case [entry_id, "preset", preset_id] if preset_id.isdigit():
            path = f"/Preset?id={preset_id}"
        case _:
            raise BrowseError("This item cannot be played")
    if not path.startswith(PLAY_PATH_PREFIXES):
        raise BrowseError("This item cannot be played")
    return entry_id, path


def _directory(
    identifier: str | None,
    title: str,
    children: list[BrowseMediaSource] | None = None,
    children_media_class: str | None = None,
) -> BrowseMediaSource:
    return BrowseMediaSource(
        domain=DOMAIN,
        identifier=identifier,
        media_class=MediaClass.DIRECTORY,
        media_content_type="",
        title=title,
        can_play=False,
        can_expand=True,
        children=children,
        children_media_class=children_media_class or MediaClass.DIRECTORY,
    )


class BluOSMediaSource(MediaSource):
    """Browse the library of BluOS players."""

    name = "BluOS Companion"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the media source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Library items are played by the player itself, not through a URL."""
        raise Unresolvable("Play this item on a BluOS Companion media player")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse players, library and presets."""
        parts = item.identifier.split("/") if item.identifier else []
        if not parts:
            return _directory(
                None,
                self.name,
                [
                    _directory(entry.entry_id, entry.title)
                    for entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
                ],
            )

        entry = self.hass.config_entries.async_get_entry(parts[0])
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise BrowseError("Unknown player")

        try:
            return await self._browse(entry, parts[1:])
        except BluOSError as err:
            raise BrowseError(str(err)) from err

    async def _browse(
        self, entry: BluOSConfigEntry, parts: list[str]
    ) -> BrowseMediaSource:
        client = entry.runtime_data.client
        eid = entry.entry_id
        match parts:
            case []:
                return _directory(
                    eid,
                    entry.title,
                    [
                        _directory(f"{eid}/recent", "Recently added"),
                        _directory(f"{eid}/albums", "Albums"),
                        _directory(f"{eid}/presets", "Presets"),
                    ],
                )
            case ["recent"]:
                albums = await client.async_get_recent_albums()
                return _directory(
                    f"{eid}/recent",
                    "Recently added",
                    [self._album(entry, album) for album in albums],
                    MediaClass.ALBUM,
                )
            case ["albums"]:
                sections = await client.async_get_album_sections()
                return _directory(
                    f"{eid}/albums",
                    "Albums",
                    [
                        _directory(
                            f"{eid}/albums/{_encode(section.key)}",
                            f"{section.name} ({section.count})",
                        )
                        for section in sections
                    ],
                )
            case ["albums", section]:
                albums = await client.async_get_albums(_decode(section))
                return _directory(
                    f"{eid}/albums/{section}",
                    "Albums",
                    [self._album(entry, album) for album in albums],
                    MediaClass.ALBUM,
                )
            case ["album", query]:
                album_query = _decode(query)
                tracks = await client.async_get_tracks(
                    f"LocalMusic:MG/LocalMusic-Album?{album_query}"
                )
                title = parse_qs(album_query).get("album", ["Album"])[0]
                return BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{eid}/album/{query}",
                    media_class=MediaClass.ALBUM,
                    media_content_type=MediaType.ALBUM,
                    title=title,
                    can_play=True,
                    can_expand=True,
                    children_media_class=MediaClass.TRACK,
                    children=[
                        BrowseMediaSource(
                            domain=DOMAIN,
                            identifier=f"{eid}/track/{_encode(track.play_path)}",
                            media_class=MediaClass.TRACK,
                            media_content_type=MediaType.TRACK,
                            title=track.title,
                            can_play=True,
                            can_expand=False,
                        )
                        for track in tracks
                    ],
                    thumbnail=async_artwork_url(
                        self.hass, eid, f"/Artwork?service=LocalMusic&{album_query}"
                    ),
                )
            case ["presets"]:
                presets = await client.async_get_presets()
                return _directory(
                    f"{eid}/presets",
                    "Presets",
                    [
                        BrowseMediaSource(
                            domain=DOMAIN,
                            identifier=f"{eid}/preset/{preset.id}",
                            media_class=MediaClass.MUSIC,
                            media_content_type=MediaType.MUSIC,
                            title=preset.name,
                            can_play=True,
                            can_expand=False,
                            thumbnail=(
                                async_artwork_url(self.hass, eid, preset.image)
                                if preset.image
                                else None
                            ),
                        )
                        for preset in presets
                    ],
                    MediaClass.MUSIC,
                )
        raise BrowseError("Unknown media item")

    def _album(self, entry: BluOSConfigEntry, album: Album) -> BrowseMediaSource:
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry.entry_id}/album/{_encode(album.query)}",
            media_class=MediaClass.ALBUM,
            media_content_type=MediaType.ALBUM,
            title=f"{album.title} - {album.artist}",
            can_play=True,
            can_expand=True,
            thumbnail=async_artwork_url(self.hass, entry.entry_id, album.image),
        )
