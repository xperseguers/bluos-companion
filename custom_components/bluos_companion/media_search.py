"""Search the media of a player, for Assist, AI agents and the search_media service."""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlencode

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaType,
    SearchMedia,
    SearchMediaQuery,
)

from .api import BluOSClient, BluOSError, Node
from .media_source import URI_PREFIX, _encode, is_play_path

MAX_RESULTS = 10
SEARCH_KEY = "LocalMusic:Search"
CATEGORIES = {
    "Artists": (MediaClass.ARTIST, MediaType.ARTIST, 2),
    "Albums": (MediaClass.ALBUM, MediaType.ALBUM, 1),
    "Songs": (MediaClass.TRACK, MediaType.TRACK, 0),
}
# Added to the score so that, for the same match, a playlist or a station wins
# over an artist, an album and a song.
PLAYLIST_BONUS = 3
STATION_BONUS = 3


def normalize(text: str) -> str:
    """Return lower case words without accents or punctuation, to compare names."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", plain.lower()))


def match_score(title: str, subtitle: str, query: str) -> int:
    """Return how well a title answers a query, 0 if it does not."""
    name, wanted = normalize(title), normalize(query)
    if not wanted:
        return 0
    if name == wanted:
        return 100
    if name.startswith(wanted):
        return 60
    words = wanted.split()
    if all(word in name.split() for word in words):
        return 40
    if all(word in f"{name} {normalize(subtitle)}".split() for word in words):
        return 20
    return 0


@dataclass(frozen=True)
class Candidate:
    """A result before it is sorted."""

    title: str
    media_class: MediaClass
    media_type: MediaType
    path: str
    score: int


def _media(entry_id: str, candidate: Candidate) -> BrowseMedia:
    return BrowseMedia(
        media_class=candidate.media_class,
        media_content_id=f"{URI_PREFIX}{entry_id}/path/{_encode(candidate.path)}",
        media_content_type=candidate.media_type,
        title=candidate.title,
        can_play=True,
        can_expand=False,
    )


async def _library(
    client: BluOSClient, query: str, wanted: set[MediaClass]
) -> list[tuple[Node, str]]:
    """Return the entries of the library that match, with their category."""
    menu = await client.async_browse_page(SEARCH_KEY, query, 1)
    categories = [
        node
        for node in menu.nodes
        if node.browse_key
        and node.title in CATEGORIES
        and (not wanted or CATEGORIES[node.title][0] in wanted)
    ]
    pages = await asyncio.gather(
        *(client.async_browse_page(node.browse_key, None, 1) for node in categories),
        return_exceptions=True,
    )
    return [
        (node, category.title)
        for category, page in zip(categories, pages, strict=True)
        if not isinstance(page, BaseException)
        for node in page.nodes
    ]


async def async_search(
    client: BluOSClient, entry_id: str, query: SearchMediaQuery
) -> SearchMedia:
    """Search the library, the saved playlists and the presets of a player."""
    text = query.search_query.strip()
    wanted = set(query.media_filter_classes or [])
    music = MediaClass.MUSIC in wanted
    if music:
        wanted = set()
    candidates: list[Candidate] = []

    def station_allowed() -> bool:
        return not wanted or MediaClass.CHANNEL in wanted

    # The player's own search fails on punctuation (a hyphen), so retry on the longest word.
    words = re.findall(r"\w+", text)
    terms = [text] + ([max(words, key=len)] if len(words) and max(words, key=len) != text else [])
    entries: list[tuple[Node, str]] = []
    for term in terms:
        try:
            entries = await _library(client, term, wanted)
        except BluOSError:
            entries = []
        if entries:
            break
    for node, category in entries:
        media_class, media_type, bonus = CATEGORIES[category]
        subtitle = node.subtitle
        score = match_score(node.title, subtitle, text)
        if not score:
            continue
        if category == "Artists":
            path = "/Add?" + urlencode(
                {"artist": node.title, "playnow": 1, "service": "LocalMusic", "shuffle": 0}
            )
            title = node.title
        else:
            path = node.play_url if category == "Songs" and node.play_url else node.play_path
            title = f"{node.title} - {subtitle.split(' • ')[0]}" if subtitle else node.title
        if path and is_play_path(path):
            candidates.append(Candidate(title, media_class, media_type, path, score + bonus))

    playlists = set()
    if not wanted or MediaClass.PLAYLIST in wanted:
        for name in await _safe(client.async_get_playlist_names()):
            playlists.add(name)
            if score := match_score(name, "", text):
                path = "/Load?" + urlencode({"service": "BluOS", "name": name})
                candidates.append(
                    Candidate(name, MediaClass.PLAYLIST, MediaType.PLAYLIST, path, score + PLAYLIST_BONUS)
                )
    for preset in await _safe(client.async_get_presets()):
        is_playlist = preset.url.startswith("/Load")
        if is_playlist:
            # It loads a saved playlist, which is a result already.
            if preset.name in playlists or (wanted and MediaClass.PLAYLIST not in wanted):
                continue
        elif not station_allowed():
            continue
        if score := match_score(preset.name, "", text):
            candidates.append(
                Candidate(
                    preset.name,
                    MediaClass.PLAYLIST if is_playlist else MediaClass.CHANNEL,
                    MediaType.PLAYLIST if is_playlist else MediaType.CHANNEL,
                    f"/Preset?id={preset.id}",
                    score + (PLAYLIST_BONUS if is_playlist else STATION_BONUS),
                )
            )

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return SearchMedia(
        result=[_media(entry_id, candidate) for candidate in candidates[:MAX_RESULTS]]
    )


async def _safe(call):  # noqa: ANN001, ANN202
    """Return the result of a call, or nothing if the player cannot answer."""
    try:
        return await call
    except BluOSError:
        return []
