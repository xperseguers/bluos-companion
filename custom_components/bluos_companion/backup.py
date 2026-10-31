"""Save the playlists and favourites of the players before Home Assistant makes a backup."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant

from .favourites_backup import async_backup_favourites
from .playlist_backup import async_backup_playlists

_LOGGER = logging.getLogger(__name__)

TIMEOUT = 120


async def async_pre_backup(hass: HomeAssistant) -> None:
    """Write the playlists and the favourites as files so that the backup contains them.

    A problem here must never prevent the backup itself.
    """
    try:
        async with asyncio.timeout(TIMEOUT):
            saved = await async_backup_playlists(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Could not save the BluOS playlists for the backup", exc_info=True)
    else:
        _LOGGER.debug("Saved %d BluOS playlists for the backup", len(saved))
    try:
        async with asyncio.timeout(TIMEOUT):
            favourites = await async_backup_favourites(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Could not save the BluOS favourites for the backup", exc_info=True)
    else:
        _LOGGER.debug("Saved the BluOS favourites for the backup: %s", favourites)


async def async_post_backup(hass: HomeAssistant) -> None:
    """Nothing to do after a backup."""
