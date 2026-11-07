"""Delete and rename the playlists saved on a player.

The player has no rename: a playlist is copied under its new name, checked track by
track, and only then is the old one deleted. A text file of the old playlist is written
first (see `playlist_backup`), so that a deleted playlist can be restored.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .api import BluOSClient, BluOSError, PlaylistTrack
from .names import normalize
from .playlist_backup import _write, file_name, folder, render

_LOGGER = logging.getLogger(__name__)

MAX_NAME_LENGTH = 100


def _existing(names: list[str], wanted: str) -> str:
    """Return the saved playlist a name designates: the exact name, whatever its case."""
    for name in names:
        if name == wanted:
            return name
    found = [name for name in names if normalize(name) == normalize(wanted)]
    if len(found) == 1:
        return found[0]
    raise HomeAssistantError(f"Unknown playlist: {wanted}")


async def _async_read(client: BluOSClient, name: str) -> list[PlaylistTrack]:
    try:
        return await client.async_get_playlist_tracks(name)
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err


async def _async_write_backup(
    hass: HomeAssistant, entry: ConfigEntry, name: str, tracks: list[PlaylistTrack]
) -> None:
    """Keep a text file of a playlist that is about to go (an empty read keeps the old file)."""
    if tracks:
        text = render(name, tracks, entry.title, dt_util.now())
        await hass.async_add_executor_job(_write, folder(hass) / file_name(name), text)


async def async_delete_playlist(hass: HomeAssistant, entry: ConfigEntry, name: str) -> str:
    """Delete a saved playlist, after writing its text file, and return its name."""
    client = entry.runtime_data.client
    try:
        name = _existing(await client.async_get_playlist_names(), name)
        try:
            tracks = await client.async_get_playlist_tracks(name)
        except BluOSError as err:
            # The player is asked to delete it anyway: the owner chose to
            _LOGGER.warning("Could not read the playlist %s before deleting it: %s", name, err)
            tracks = []
        await _async_write_backup(hass, entry, name, tracks)
        await client.async_delete_playlist(name)
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err
    return name


async def async_rename_playlist(
    hass: HomeAssistant, entry: ConfigEntry, name: str, new_name: str
) -> int:
    """Rename a saved playlist and return its number of tracks.

    Nothing is lost on the way: the old playlist stays as it is until the copy has the same
    tracks in the same order, and a copy that does not is deleted again.
    """
    client = entry.runtime_data.client
    new_name = new_name.strip()
    if not new_name or len(new_name) > MAX_NAME_LENGTH:
        raise HomeAssistantError("The new name must have between 1 and 100 characters")
    try:
        names = await client.async_get_playlist_names()
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err
    name = _existing(names, name)
    if normalize(new_name) == normalize(name) or any(
        normalize(new_name) == normalize(other) for other in names
    ):
        raise HomeAssistantError(f"A playlist named {new_name} exists already")

    # The player sometimes gives a part of a long playlist: two reads must agree
    tracks = await _async_read(client, name)
    if not tracks or len(tracks) != len(await _async_read(client, name)):
        raise HomeAssistantError(f"The playlist {name} could not be read completely, try again")
    paths = [track.path for track in tracks]

    await _async_write_backup(hass, entry, name, tracks)
    try:
        await client.async_add_files_to_playlist(new_name, paths)
        copy = [track.path for track in await client.async_get_playlist_tracks(new_name)]
    except BluOSError as err:
        await _async_discard(client, new_name)
        raise HomeAssistantError(f"BluOS player error: {err}. {name} was left as it was") from err
    if copy != paths:
        await _async_discard(client, new_name)
        raise HomeAssistantError(f"{name} could not be copied completely and was left as it was")
    try:
        await client.async_delete_playlist(name)
    except BluOSError as err:
        raise HomeAssistantError(
            f"{new_name} was made, but {name} could not be deleted: {err}"
        ) from err
    return len(paths)


async def _async_discard(client: BluOSClient, name: str) -> None:
    """Delete an unfinished copy, if the player lets us."""
    try:
        await client.async_delete_playlist(name)
    except BluOSError as err:
        _LOGGER.warning("Could not delete the unfinished playlist %s: %s", name, err)
