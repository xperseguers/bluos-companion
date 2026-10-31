"""Find the album covers the player refuses to show because they are too large."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime

from homeassistant.util import dt as dt_util

from .api import Album, BluOSClient, BluOSError

# The picture the player shows instead of a cover heavier than 600 KiB ("Artwork Too Large").
PLACEHOLDER_SHA256 = frozenset(
    {"e1ce440608edda8361b46e1f72b5343ef4cff8981013445c28bb7045f3cbb854"}
)
CONCURRENCY = 4


@dataclass(frozen=True, slots=True)
class CoverCheck:
    """What the last check of the covers found."""

    checked: int
    too_large: tuple[Album, ...]
    errors: int
    checked_at: datetime


async def async_check_covers(client: BluOSClient) -> CoverCheck:
    """Read the cover of every album of the library and list those that are too large.

    One request per album, a few at a time: this takes a minute or two for a big
    library, so it is only run when asked.
    """
    albums = await client.async_get_library_albums()
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def too_large(album: Album) -> bool | None:
        async with semaphore:
            try:
                data, _ = await client.async_get_image(album.image)
            except BluOSError:
                return None
            return hashlib.sha256(data).hexdigest() in PLACEHOLDER_SHA256

    results = await asyncio.gather(*(too_large(album) for album in albums))
    return CoverCheck(
        checked=len(albums),
        too_large=tuple(album for album, large in zip(albums, results) if large),
        errors=results.count(None),
        checked_at=dt_util.utcnow(),
    )
