"""Back up the favourites of the library as a text file, and put them back.

One JSON file in the Home Assistant configuration folder, so that every Home
Assistant backup contains it. The favourites are shared by the players, so the
first player that answers is enough. The file can be edited, for example to change
the path of the music share in the songs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import BluOSError, Favourite, Favourites
from .const import CONF_BACKUP_PLAYLISTS, DOMAIN
from .playlist_backup import _write

_LOGGER = logging.getLogger(__name__)

FILE = ("bluos_companion", "favourites.json")


def file_path(hass: HomeAssistant) -> Path:
    """Return the file the favourites are saved in."""
    return Path(hass.config.path(*FILE))


def render(items: tuple[Favourite, ...], player: str, now: datetime) -> str:
    """Return the text of the favourites file."""
    data = {
        "saved": now.isoformat(timespec="seconds"),
        "player": player,
        "note": "After moving the music share, change the beginning of the song files below, "
        "then restore with the service bluos_companion.restore_favourites.",
        "albums": [
            {"artist": item.artist, "album": item.album} for item in items if item.kind == "album"
        ],
        "artists": [item.artist for item in items if item.kind == "artist"],
        "songs": [
            {"artist": item.artist, "album": item.album, "title": item.title, "file": item.file}
            for item in items
            if item.kind == "song"
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def parse(text: str) -> tuple[Favourite, ...]:
    """Return the favourites of a file, leaving out what is not understood."""
    try:
        data = json.loads(text)
    except ValueError as err:
        raise HomeAssistantError(f"The favourites file is not valid: {err}") from err
    if not isinstance(data, dict):
        raise HomeAssistantError("The favourites file is not valid")
    items: list[Favourite] = []
    for album in data.get("albums") or []:
        if isinstance(album, dict) and album.get("artist") and album.get("album"):
            items.append(Favourite("album", str(album["artist"]), str(album["album"])))
    for artist in data.get("artists") or []:
        if isinstance(artist, str) and artist:
            items.append(Favourite("artist", artist))
    for song in data.get("songs") or []:
        if isinstance(song, dict) and song.get("file"):
            items.append(
                Favourite(
                    "song",
                    str(song.get("artist", "")),
                    str(song.get("album", "")),
                    str(song["file"]),
                    str(song.get("title", "")),
                )
            )
    return tuple(items)


def describe(item: Favourite) -> str:
    """Return a short name of a favourite, to tell the user about it."""
    match item.kind:
        case "album":
            return f"{item.artist} - {item.album}"
        case "artist":
            return item.artist
        case _:
            return f"{item.artist} - {item.title}" if item.title else item.file


async def async_backup_favourites(hass: HomeAssistant) -> dict[str, int]:
    """Write the favourites of the library to a file, return how many of each kind.

    A player that reads no favourite at all (it may be off, or have lost them) keeps
    the previous file.
    """
    entries = sorted(
        (
            entry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry.options.get(CONF_BACKUP_PLAYLISTS, True)
        ),
        key=lambda entry: entry.created_at,
    )
    for entry in entries:
        try:
            favourites = await entry.runtime_data.client.async_get_favourites()
        except BluOSError as err:
            _LOGGER.warning("Could not read the favourites of %s: %s", entry.title, err)
            continue
        if not favourites.items:
            _LOGGER.warning("The player has no favourite, the previous backup is kept")
            return {}
        await hass.async_add_executor_job(
            _write, file_path(hass), render(favourites.items, entry.title, dt_util.now())
        )
        return {
            f"{kind}s": sum(item.kind == kind for item in favourites.items)
            for kind in ("album", "artist", "song")
        }
    return {}


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


async def async_restore_favourites(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, object]:
    """Add the favourites of the file that the player does not have. Nothing is removed.

    The player takes any song without complaint but keeps only those of its library, so
    the favourites are read again to tell which ones did not come back.
    """
    text = await hass.async_add_executor_job(_read, file_path(hass))
    if text is None:
        raise HomeAssistantError(f"No favourites file: {file_path(hass)}")
    items = parse(text)
    client = entry.runtime_data.client
    try:
        present = await client.async_get_favourites()
        missing = [item for item in items if item not in present]
        for item in missing:
            await client.async_set_favourite(item, True)
        after: Favourites = await client.async_get_favourites() if missing else present
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err
    not_found = [describe(item) for item in missing if item not in after]
    if not_found:
        _LOGGER.warning(
            "%d favourites are not in the library of the player and were not added", len(not_found)
        )
    return {
        "added": len(missing) - len(not_found),
        "already": len(items) - len(missing),
        "not_found": not_found,
    }
