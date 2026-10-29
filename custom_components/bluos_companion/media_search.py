"""Search the media of a player, for Assist, AI agents and the search_media service."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from difflib import SequenceMatcher
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

from .api import BluOSClient, BluOSError, Node, Preset
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
# A typo tolerant search only runs when the exact one finds nothing.
FUZZY_THRESHOLD = 0.8
FUZZY_MIN_LENGTH = 4
FUZZY_PROBES = 4


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


def fuzzy_score(title: str, query: str) -> int:
    """Return how close a title is to a query that may have typos, 0 if not close.

    Either every word of the query is close to a word of the title ("led zepelin"
    is "Led Zeppelin", "zepelin" is a word of it), or the words are split or joined
    differently ("cold play" is "coldplay"). One word in common is not enough
    ("xylophone orchestra" is not "Chicago Symphony Orchestra"). The result stays
    below the scores of the exact matches.
    """
    name, wanted = normalize(title), normalize(query)
    if len(wanted) < FUZZY_MIN_LENGTH or not name:
        return 0

    def similarity(first: str, second: str) -> float:
        return SequenceMatcher(None, first, second).ratio()

    words, tokens = wanted.split(), name.split()
    by_words = min(max(similarity(word, token) for token in tokens) for word in words)
    # Runs of a different number of words than the query: only the spaces differ.
    joined = wanted.replace(" ", "")
    runs = {
        "".join(tokens[i : i + size])
        for size in range(1, len(tokens) + 1)
        if size != len(words)
        for i in range(len(tokens) - size + 1)
    }
    by_spaces = max((similarity(joined, run) for run in runs), default=0)
    best = max(by_words, by_spaces)
    return int(best * 40) if best >= FUZZY_THRESHOLD else 0


def _probes(query: str) -> list[str]:
    """Return fragments of a query to search the library with when it has a typo.

    The player only finds what contains the text, so the start and the end of the
    longest words are tried: the typo is unlikely to be in both.
    """
    probes: list[str] = []
    for word in sorted(normalize(query).split(), key=len, reverse=True)[:3]:
        if len(word) < 3:
            continue
        for probe in ([word] if len(word) <= 5 else [word[:4], word[-4:]]):
            if probe not in probes:
                probes.append(probe)
    return probes[:FUZZY_PROBES]


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


def _candidates(
    entries: list[tuple[Node, str]],
    playlist_names: list[str],
    presets: list[Preset],
    wanted: set[MediaClass],
    score_of: Callable[[str, str], int],
) -> list[Candidate]:
    """Turn what was found into results, with the score of each."""
    candidates: list[Candidate] = []
    for node, category in entries:
        media_class, media_type, bonus = CATEGORIES[category]
        subtitle = node.subtitle
        score = score_of(node.title, subtitle)
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

    for name in playlist_names:
        if score := score_of(name, ""):
            path = "/Load?" + urlencode({"service": "BluOS", "name": name})
            candidates.append(
                Candidate(name, MediaClass.PLAYLIST, MediaType.PLAYLIST, path, score + PLAYLIST_BONUS)
            )
    for preset in presets:
        is_playlist = preset.url.startswith("/Load")
        if is_playlist:
            # It loads a saved playlist, which is a result already.
            if preset.name in playlist_names or (wanted and MediaClass.PLAYLIST not in wanted):
                continue
        elif wanted and MediaClass.CHANNEL not in wanted:
            continue
        if score := score_of(preset.name, ""):
            candidates.append(
                Candidate(
                    preset.name,
                    MediaClass.PLAYLIST if is_playlist else MediaClass.CHANNEL,
                    MediaType.PLAYLIST if is_playlist else MediaType.CHANNEL,
                    f"/Preset?id={preset.id}",
                    score + (PLAYLIST_BONUS if is_playlist else STATION_BONUS),
                )
            )
    return candidates


async def _entries(
    client: BluOSClient, terms: list[str], wanted: set[MediaClass], *, merge: bool
) -> list[tuple[Node, str]]:
    """Search the library for the terms: the first that finds something, or all of them."""
    found: list[tuple[Node, str]] = []
    for term in terms:
        try:
            entries = await _library(client, term, wanted)
        except BluOSError:
            entries = []
        for entry in entries:
            if entry not in found:
                found.append(entry)
        if found and not merge:
            break
    return found


async def async_search(
    client: BluOSClient, entry_id: str, query: SearchMediaQuery
) -> SearchMedia:
    """Search the library, the saved playlists and the presets of a player."""
    text = query.search_query.strip()
    wanted = set(query.media_filter_classes or [])
    if MediaClass.MUSIC in wanted:
        wanted = set()
    playlist_names = (
        await _safe(client.async_get_playlist_names())
        if not wanted or MediaClass.PLAYLIST in wanted
        else []
    )
    presets = await _safe(client.async_get_presets())

    # The player's own search fails on punctuation (a hyphen), so retry on the longest word.
    words = re.findall(r"\w+", text)
    longest = max(words, key=len) if words else text
    terms = [text] + ([longest] if longest != text else [])
    entries = await _entries(client, terms, wanted, merge=False)
    candidates = _candidates(
        entries, playlist_names, presets, wanted, lambda title, sub: match_score(title, sub, text)
    )
    if not candidates and len(normalize(text)) >= FUZZY_MIN_LENGTH:
        entries = await _entries(client, _probes(text), wanted, merge=True)
        candidates = _candidates(
            entries, playlist_names, presets, wanted, lambda title, _: fuzzy_score(title, text)
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
