"""Back up the playlists saved on the players as text files.

One standard `.m3u8` file per playlist is written below the Home Assistant
configuration folder, so that every Home Assistant backup contains them. The files
can be edited, for example to change the path of the music share, and are read
back to rebuild the playlists on a player.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import BluOSError, PlaylistTrack
from .const import CONF_BACKUP_PLAYLISTS, DOMAIN

_LOGGER = logging.getLogger(__name__)

FOLDER = ("bluos_companion", "playlists")
EXTENSION = ".m3u8"
FORBIDDEN = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def folder(hass: HomeAssistant) -> Path:
    """Return the folder the playlists are saved in."""
    return Path(hass.config.path(*FOLDER))


def file_name(name: str) -> str:
    """Return a file name for a playlist, whatever characters its name has."""
    return (FORBIDDEN.sub("_", name).strip(" .") or "playlist") + EXTENSION


def render(name: str, tracks: list[PlaylistTrack], player: str, now: datetime) -> str:
    """Return the text of a playlist file."""
    lines = [
        "#EXTM3U",
        f"#PLAYLIST:{name}",
        f'# Saved by BluOS Companion from the player "{player}" on {now.isoformat(timespec="seconds")}.',
        "# After moving the music share, change the beginning of the paths below (find and",
        "# replace), then restore with the service bluos_companion.restore_playlists.",
    ]
    for track in tracks:
        display = " - ".join(part for part in (track.artist, track.title) if part)
        lines.append(f"#EXTINF:{track.duration or -1},{display}")
        if track.album:
            lines.append(f"#EXTALB:{track.album}")
        lines.append(track.path)
    return "\n".join(lines) + "\n"


def parse(text: str, default_name: str) -> tuple[str, list[PlaylistTrack]]:
    """Return the name and the tracks of a playlist file (the paths are what matters)."""
    name = default_name
    tracks: list[PlaylistTrack] = []
    duration: int | None = None
    artist = title = album = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#PLAYLIST:"):
            name = line.removeprefix("#PLAYLIST:").strip() or default_name
        elif line.startswith("#EXTINF:"):
            length, _, display = line.removeprefix("#EXTINF:").partition(",")
            duration = int(length) if length.lstrip("-").isdigit() and int(length) > 0 else None
            artist, sep, title = display.partition(" - ")
            if not sep:
                artist, title = "", display
        elif line.startswith("#EXTALB:"):
            album = line.removeprefix("#EXTALB:")
        elif not line.startswith("#"):
            tracks.append(PlaylistTrack(title, artist, album, duration, line))
            duration = None
            artist = title = album = ""
    return name, tracks


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


async def async_backup_playlists(hass: HomeAssistant) -> dict[str, int]:
    """Write the playlists of the players to text files, return the number of tracks of each.

    A playlist that is read empty (or not at all) keeps its previous file, so that
    a player that is off or has lost its entries does not erase the backup. When two
    players have the same playlist, the one of the player added first is used.
    """
    entries = sorted(
        (
            entry
            for entry in hass.config_entries.async_loaded_entries(DOMAIN)
            if entry.options.get(CONF_BACKUP_PLAYLISTS, True)
        ),
        key=lambda entry: entry.created_at,
    )
    saved: dict[str, int] = {}
    seen: set[str] = set()
    for entry in entries:
        client = entry.runtime_data.client
        try:
            names = await client.async_get_playlist_names()
        except BluOSError as err:
            _LOGGER.warning("Could not list the playlists of %s: %s", entry.title, err)
            continue
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            try:
                tracks = await client.async_get_playlist_tracks(name)
            except BluOSError as err:
                _LOGGER.warning("Could not read the playlist %s: %s", name, err)
                continue
            if not tracks:
                _LOGGER.warning("The playlist %s has no track, its backup is kept", name)
                continue
            text = render(name, tracks, entry.title, dt_util.now())
            await hass.async_add_executor_job(
                _write, folder(hass) / file_name(name), text
            )
            saved[name] = len(tracks)
    return saved


def _read_files(path: Path) -> dict[str, list[PlaylistTrack]]:
    """Read the playlist files of a folder, by playlist name."""
    playlists: dict[str, list[PlaylistTrack]] = {}
    for file in sorted(path.glob(f"*{EXTENSION}")):
        name, tracks = parse(file.read_text(encoding="utf-8"), file.stem)
        playlists[name] = tracks
    return playlists


async def async_restore_playlists(
    hass: HomeAssistant,
    entry: ConfigEntry,
    names: list[str] | None = None,
    replace: bool = False,
) -> dict[str, object]:
    """Rebuild playlists on a player from the text files.

    The player only saves its queue as a playlist, so the queue of the player is
    emptied and refilled for each playlist. A playlist that exists already is left
    alone unless `replace` is set: its tracks are then added first, so that the old
    playlist is only deleted once the new queue is ready.
    """
    files = await hass.async_add_executor_job(_read_files, folder(hass))
    wanted = list(files) if not names else names
    client = entry.runtime_data.client
    result: dict[str, object] = {
        "restored": {},
        "skipped": [],
        "not_found": [name for name in wanted if name not in files],
    }
    try:
        existing = set(await client.async_get_playlist_names())
        for name in (name for name in wanted if name in files):
            tracks = files[name]
            if not tracks:
                result["skipped"].append(name)
                continue
            if name in existing and not replace:
                result["skipped"].append(name)
                continue
            await client.async_clear_queue()
            for track in tracks:
                await client.async_add_file(track.path)
            queued = await client.async_get_queue_length()
            if name in existing:
                await client.async_delete_playlist(name)
            await client.async_save_queue(name)
            result["restored"][name] = queued
            if queued < len(tracks):
                _LOGGER.warning(
                    "Playlist %s: the player found %d of the %d files, check the paths",
                    name,
                    queued,
                    len(tracks),
                )
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err
    return result
