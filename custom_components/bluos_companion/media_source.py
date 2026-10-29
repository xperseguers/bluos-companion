"""Expose the BluOS library, presets and playback as a Home Assistant media source."""

from __future__ import annotations

import base64
import json
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
from homeassistant.helpers.translation import async_get_translations

from .api import Album, BluOSError, Node
from .const import DOMAIN, ICONS_URL
from .coordinator import BluOSConfigEntry
from .http import async_artwork_url

URI_PREFIX = f"media-source://{DOMAIN}/"
PLAY_PATH_PREFIXES = ("/Add?", "/Preset?", "/Load?", "/Play?id=")

LIBRARY = {
    "artists": "LocalMusic:bySection:Artist/%2Flibrary%2Fv1%2FArtists%3Fservice=LocalMusic",
    "albums": "LocalMusic:bySection:Album/%2Flibrary%2Fv1%2FAlbums%3Fservice=LocalMusic",
    "songs": "LocalMusic:bySection:Song/%2Flibrary%2Fv1%2FSongs%3Fall=1&service=LocalMusic",
    "genres": "LocalMusic:GG/Genres",
    "playlists": "BluOS:",
    "composers": "LocalMusic:bySection:Composer/%2Flibrary%2Fv1%2FComposers%3Fservice=LocalMusic",
}
TITLES = ("recently_added", *LIBRARY, "presets", "queue", "favourites", "folders")
MENU_LABELS = {
    **{category.capitalize(): category for category in LIBRARY},
    "Favourites": "favourites",
    "Favorites": "favourites",
    "Folders": "folders",
}
NODE_CLASSES = {
    "artist": (MediaClass.ARTIST, MediaType.ARTIST),
    "album": (MediaClass.ALBUM, MediaType.ALBUM),
    "track": (MediaClass.TRACK, MediaType.TRACK),
    "playlist": (MediaClass.PLAYLIST, MediaType.PLAYLIST),
    "genre": (MediaClass.GENRE, MediaType.GENRE),
    "composer": (MediaClass.COMPOSER, MediaType.COMPOSER),
}


async def async_get_media_source(hass: HomeAssistant) -> BluOSMediaSource:
    """Set up the media source."""
    return BluOSMediaSource(hass)


def _encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _encode_node(node: Node, title: str | None = None) -> str:
    return _encode(
        json.dumps(
            {"k": node.browse_key, "p": node.play_path, "t": title or node.title}
        )
    )


def _decode_node(value: str) -> dict[str, str | None]:
    try:
        data = json.loads(_decode(value))
    except ValueError as err:
        raise BrowseError("Invalid media identifier") from err
    if not isinstance(data, dict):
        raise BrowseError("Invalid media identifier")
    return data


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
        case [entry_id, "queue", item_id] if item_id.isdigit():
            path = f"/Play?id={item_id}"
        case [entry_id, "node", payload]:
            path = _decode_node(payload).get("p") or ""
        case _:
            raise BrowseError("This item cannot be played")
    if not path.startswith(PLAY_PATH_PREFIXES):
        raise BrowseError("This item cannot be played")
    return entry_id, path


def _icon(name: str) -> str:
    return f"{ICONS_URL}/{name}.svg"


async def async_get_titles(hass: HomeAssistant) -> dict[str, str]:
    """Return the translated titles of the browse menus."""
    translations = await async_get_translations(
        hass, hass.config.language, "common", [DOMAIN]
    )
    return {
        key: translations.get(
            f"component.{DOMAIN}.common.{key}", key.replace("_", " ").capitalize()
        )
        for key in TITLES
    }


def menu_label(node: Node, titles: dict[str, str]) -> tuple[str, str | None]:
    """Return the translated label of a menu link and its icon, if it has one."""
    if node.type == "link" and node.title in MENU_LABELS:
        category = MENU_LABELS[node.title]
        return titles[category], _icon(category)
    return node.title, None


def _directory(
    identifier: str | None,
    title: str,
    children: list[BrowseMediaSource] | None = None,
    children_media_class: str | None = None,
    thumbnail: str | None = None,
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
        thumbnail=thumbnail,
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
        raise Unresolvable(
            "BluOS Companion items can only be played on a BluOS player: "
            "select your BluOS player as the target"
        )

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse players, library and presets."""
        parts = item.identifier.split("/") if item.identifier else []
        if not parts:
            return _directory(
                None,
                self.name,
                [
                    _directory(entry.entry_id, entry.title, thumbnail=_icon("player"))
                    for entry in self.hass.config_entries.async_loaded_entries(DOMAIN)
                ],
            )

        entry = self.hass.config_entries.async_get_entry(parts[0])
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise BrowseError("Unknown player")

        titles = await self._async_get_titles()
        try:
            return await self._browse(entry, parts[1:], titles)
        except BluOSError as err:
            raise BrowseError(str(err)) from err

    async def _async_get_titles(self) -> dict[str, str]:
        return await async_get_titles(self.hass)

    async def _browse(
        self, entry: BluOSConfigEntry, parts: list[str], titles: dict[str, str]
    ) -> BrowseMediaSource:
        client = entry.runtime_data.client
        eid = entry.entry_id
        match parts:
            case []:
                return _directory(
                    eid,
                    entry.title,
                    [
                        _directory(
                            f"{eid}/recent",
                            titles["recently_added"],
                            thumbnail=_icon("recently_added"),
                        ),
                        *(
                            _directory(
                                f"{eid}/{category}",
                                titles[category],
                                thumbnail=_icon(category),
                            )
                            for category in LIBRARY
                        ),
                        _directory(
                            f"{eid}/presets",
                            titles["presets"],
                            thumbnail=_icon("presets"),
                        ),
                        _directory(
                            f"{eid}/queue",
                            titles["queue"],
                            thumbnail=_icon("queue"),
                        ),
                    ],
                )
            case ["recent"]:
                albums = await client.async_get_recent_albums()
                return _directory(
                    f"{eid}/recent",
                    titles["recently_added"],
                    [self._album(entry, album) for album in albums],
                    MediaClass.ALBUM,
                )
            case [category] if category in LIBRARY:
                return await self._browse_node(
                    entry,
                    f"{eid}/{category}",
                    titles[category],
                    LIBRARY[category],
                    titles,
                )
            case ["node", payload]:
                data = _decode_node(payload)
                if not (key := data.get("k")):
                    raise BrowseError("This item cannot be browsed")
                return await self._browse_node(
                    entry, f"{eid}/node/{payload}", data.get("t") or "", key, titles
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
            case ["queue"]:
                queue = await client.async_get_queue()
                return _directory(
                    f"{eid}/queue",
                    titles["queue"],
                    [
                        BrowseMediaSource(
                            domain=DOMAIN,
                            identifier=f"{eid}/queue/{item.id}",
                            media_class=MediaClass.TRACK,
                            media_content_type=MediaType.TRACK,
                            title=(
                                f"{item.title} - {item.artist}"
                                if item.artist
                                else item.title
                            ),
                            can_play=True,
                            can_expand=False,
                            thumbnail=(
                                async_artwork_url(self.hass, eid, item.image)
                                if item.image
                                else None
                            ),
                        )
                        for item in queue
                    ],
                    MediaClass.TRACK,
                )
            case ["presets"]:
                presets = await client.async_get_presets()
                return _directory(
                    f"{eid}/presets",
                    titles["presets"],
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

    async def _browse_node(
        self,
        entry: BluOSConfigEntry,
        identifier: str,
        title: str,
        key: str,
        titles: dict[str, str],
    ) -> BrowseMediaSource:
        nodes = await entry.runtime_data.client.async_browse(key)
        return _directory(
            identifier,
            title,
            [
                item
                for node in nodes
                if (item := self._node_item(entry, node, titles)) is not None
            ],
        )

    def _node_item(
        self, entry: BluOSConfigEntry, node: Node, titles: dict[str, str]
    ) -> BrowseMediaSource | None:
        can_expand = node.browse_key is not None and node.type != "playlist"
        can_play = node.play_path is not None
        if not (can_expand or can_play):
            return None
        media_class, media_type = NODE_CLASSES.get(
            node.type, (MediaClass.DIRECTORY, "")
        )
        label, thumbnail = menu_label(node, titles)
        if thumbnail is None and node.image and node.type != "track":
            thumbnail = async_artwork_url(self.hass, entry.entry_id, node.image)
        title = label
        if node.type == "section":
            title = f"{node.title} ({node.subtitle})"
        elif node.type in ("album", "track") and node.subtitle:
            title = f"{node.title} - {node.subtitle}"
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry.entry_id}/node/{_encode_node(node, label)}",
            media_class=media_class,
            media_content_type=media_type,
            title=title,
            can_play=can_play,
            can_expand=can_expand,
            thumbnail=thumbnail,
        )

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
