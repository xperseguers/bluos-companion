"""Bring playlists exported from another music player (Apple Music...) to the players.

An exported playlist lists the files of the computer. The import converts it to the
files of the music share as the player knows them, writes it like a playlist backup,
and lets the restore build it on the player.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import BluOSClient, BluOSError, PlaylistTrack
from .playlist_backup import (
    EXTENSION,
    _write,
    async_restore_playlists,
    file_name,
    folder,
    render,
)

_LOGGER = logging.getLogger(__name__)

IMPORT_FOLDER = ("bluos_companion", "import")
EXTENSIONS = (".m3u8", ".m3u")
# A library organised by Apple Music or iTunes: Artist/Album/File
TAIL = 3
MAX_ARTISTS_TRIED = 15


@dataclass(frozen=True, slots=True)
class ExportedTrack:
    """A track of an exported playlist."""

    title: str
    duration: int | None
    path: str


def import_folder(hass: HomeAssistant) -> Path:
    """Return the folder the exported playlists are put in."""
    return Path(hass.config.path(*IMPORT_FOLDER))


def _compose(text: str) -> str:
    """Return text with composed accents: the music share has them, a Mac export may not."""
    return unicodedata.normalize("NFC", text)


def _slashes(path: str) -> str:
    """Return the path with slashes, whatever the computer it comes from."""
    return path.replace("\\", "/") if "\\" in path and "/" not in path else path


def parse_export(text: str, default_name: str) -> tuple[str, list[ExportedTrack]]:
    """Return the name and the tracks of an exported playlist.

    Apple Music writes the lines of the file with carriage returns only, and names
    a track "Title - Artist".
    """
    name = _compose(default_name)
    tracks: list[ExportedTrack] = []
    title, duration = "", None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#PLAYLIST:"):
            name = _compose(line.removeprefix("#PLAYLIST:").strip()) or name
        elif line.startswith("#EXTINF:"):
            length, _, display = line.removeprefix("#EXTINF:").partition(",")
            duration = int(length) if length.isdigit() and int(length) > 0 else None
            title = display.rsplit(" - ", 1)[0] if " - " in display else display
        elif not line.startswith("#"):
            tracks.append(ExportedTrack(title, duration, _compose(_slashes(line))))
            title, duration = "", None
    return name, tracks


def common_source_root(tracks: list[ExportedTrack]) -> str | None:
    """Return the folder of the library: the most common path without Artist/Album/File."""
    roots = Counter(
        "/".join(parts[:-TAIL]) + "/"
        for track in tracks
        if len(parts := track.path.split("/")) > TAIL
    )
    return roots.most_common(1)[0][0] if roots else None


def convert(
    tracks: list[ExportedTrack], source_root: str, library_root: str
) -> tuple[list[PlaylistTrack], list[str]]:
    """Return the tracks as the player knows their files, and the paths outside the library."""
    converted: list[PlaylistTrack] = []
    outside: list[str] = []
    for track in tracks:
        if not track.path.startswith(source_root):
            outside.append(track.path)
            continue
        relative = track.path.removeprefix(source_root)
        parts = relative.split("/")
        title = track.title or Path(parts[-1]).stem
        artist, album = (parts[-3], parts[-2]) if len(parts) >= TAIL else ("", "")
        converted.append(
            PlaylistTrack(title, artist, album, track.duration, library_root + relative)
        )
    return converted, outside


async def async_detect_library_root(
    client: BluOSClient, tracks: list[ExportedTrack], source_root: str
) -> str:
    """Find where the library is on the player: look for a track among the files of its artist."""
    tried: set[str] = set()
    for track in tracks:
        if not track.path.startswith(source_root):
            continue
        relative = track.path.removeprefix(source_root)
        parts = relative.split("/")
        if len(parts) < TAIL or parts[0] in tried:
            continue
        tried.add(parts[0])
        if len(tried) > MAX_ARTISTS_TRIED:
            break
        for path in await client.async_get_artist_files(parts[0]):
            path = _compose(path)
            if path.endswith("/" + relative):
                return path.removesuffix(relative)
    raise HomeAssistantError(
        "Could not find these tracks on the player. Is the music on the player's share? "
        "Give library_path, the folder of the music as the player knows it."
    )


def _read(path: Path) -> list[tuple[str, str]]:
    """Read the exported playlists of a folder: (file name, text)."""
    path.mkdir(parents=True, exist_ok=True)
    return [
        (file.stem, file.read_text(encoding="utf-8-sig"))
        for file in sorted(path.iterdir())
        if file.suffix.lower() in EXTENSIONS
    ]


def _folder_path(path: str | None) -> str | None:
    """Return a folder given by the user, composed and ending with a slash."""
    return _compose(_slashes(path.strip())).rstrip("/") + "/" if path and path.strip() else None


async def async_import_playlists(
    hass: HomeAssistant,
    entry: ConfigEntry,
    restore: bool = True,
    replace: bool = False,
    source_path: str | None = None,
    library_path: str | None = None,
) -> dict[str, object]:
    """Convert the exported playlists of the import folder, and build them on the player.

    A playlist whose file exists already is left alone unless `replace` is set.
    """
    exported = await hass.async_add_executor_job(_read, import_folder(hass))
    if not exported:
        raise HomeAssistantError(
            f"No playlist file (.m3u8) found: put the exported playlists in {import_folder(hass)}"
        )
    client = entry.runtime_data.client
    library = _folder_path(library_path)
    imported: dict[str, dict[str, int]] = {}
    skipped: list[str] = []
    for stem, text in exported:
        name, tracks = parse_export(text, stem)
        source = _folder_path(source_path) or common_source_root(tracks)
        if not tracks or source is None:
            skipped.append(name)
            continue
        target = folder(hass) / file_name(name)
        if not replace and await hass.async_add_executor_job(target.exists):
            skipped.append(name)
            continue
        try:
            library = library or await async_detect_library_root(client, tracks, source)
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err
        converted, outside = convert(tracks, source, library)
        if outside:
            _LOGGER.warning(
                "Playlist %s: %d tracks are not below %s and are left out", name, len(outside), source
            )
        if not converted:
            skipped.append(name)
            continue
        await hass.async_add_executor_job(
            _write,
            target,
            render(name, converted, "", dt_util.now(), imported_from=f"{stem}{EXTENSION}"),
        )
        imported[name] = {"tracks": len(converted), "left_out": len(outside)}
    result: dict[str, object] = {"imported": imported, "skipped": skipped}
    if restore and imported:
        result["restore"] = await async_restore_playlists(hass, entry, list(imported), replace)
    return result
