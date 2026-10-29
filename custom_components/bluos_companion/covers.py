"""Covers of what the player gives without one (saved playlists, tracks of a playlist)."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import parse_qs, urlencode, urlparse

from .api import BluOSError, Node, Preset
from .coordinator import BluOSCoordinator

PLAYLIST_KEY_PREFIX = "BluOS:MG/BluOS-Playlist?"
PLAYLIST_COVER_TTL = 600


def image_path(node: Node) -> str | None:
    """Return the player path of the cover of an entry.

    The tracks of a saved playlist come with an empty song id, so their cover is
    looked up with the artist and the album written in the subtitle.
    """
    if node.image and node.image.endswith("songid="):
        artist, _, album = node.subtitle.partition(" • ")
        if artist and album:
            return "/Artwork?" + urlencode(
                {"service": "LocalMusic", "artist": artist, "album": album}
            )
        return None
    return node.image


async def async_playlist_covers(
    coordinator: BluOSCoordinator, keys: list[str]
) -> dict[str, str | None]:
    """Return the cover (a player path) of saved playlists: the one of their first track.

    The first tracks of an old playlist may be missing, so this can take a few
    requests on the player, and the result is kept for a while.
    """

    async def cover(key: str) -> tuple[str, str | None]:
        cached = coordinator.playlist_covers.get(key)
        if cached and time.monotonic() - cached[0] < PLAYLIST_COVER_TTL:
            return key, cached[1]
        path = None
        try:
            page = await coordinator.client.async_browse_page(key, None, 1)
            path = next((p for node in page.nodes if (p := image_path(node))), None)
        except BluOSError:
            pass
        coordinator.playlist_covers[key] = (time.monotonic(), path)
        return key, path

    return dict(
        await asyncio.gather(
            *(cover(key) for key in keys if key.startswith(PLAYLIST_KEY_PREFIX))
        )
    )


def preset_playlist_key(url: str) -> str | None:
    """Return the key of the saved playlist a preset loads (`/Load?name=...`), if it does."""
    if not url.startswith("/Load"):
        return None
    names = parse_qs(urlparse(url).query).get("name")
    return f"{PLAYLIST_KEY_PREFIX}{urlencode({'playlist': names[0]})}" if names else None


async def async_preset_images(
    coordinator: BluOSCoordinator, presets: list[Preset]
) -> dict[int, str | None]:
    """Return the image (a player path or an address) of each preset.

    A preset that loads a saved playlist and has no image of its own gets the cover
    of that playlist.
    """
    keys = {
        preset.id: key
        for preset in presets
        if not preset.image and (key := preset_playlist_key(preset.url))
    }
    covers = await async_playlist_covers(coordinator, list(keys.values()))
    return {
        preset.id: preset.image or covers.get(keys.get(preset.id, ""))
        for preset in presets
    }
