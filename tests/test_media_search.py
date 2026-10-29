"""Tests for the search of media (Assist, AI agents, the search_media service)."""

from __future__ import annotations

import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaClass,
    MediaPlayerEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.media_search import (
    _probes,
    fuzzy_score,
    match_score,
    normalize,
)
from custom_components.bluos_companion.media_source import play_path_from_media_id

from .conftest import BASE, browse_url, calls, respond

ENTITY_ID = "media_player.sejour"
MENU = """<browse type="menu">
  <item browseKey="artists" text="Artists" type="link"/>
  <item browseKey="albums" text="Albums" type="link"/>
  <item browseKey="songs" text="Songs" type="link"/>
  <item browseKey="composers" text="Composers" type="link"/>
</browse>"""
ARTISTS = '<browse><item browseKey="a" text="Adele" type="artist"/></browse>'
ALBUMS = """<browse>
  <item browseKey="b" playURL="/Add?playnow=1&amp;service=LocalMusic&amp;album=21&amp;artist=Adele" text="21" text2="Adele" type="album"/>
  <item browseKey="c" playURL="/Add?playnow=1&amp;service=LocalMusic&amp;album=Adele+Live&amp;artist=Adele" text="Adele Live" text2="Adele" type="album"/>
</browse>"""
SONGS = """<browse>
  <item playURL="/Add?playnow=1&amp;file=%2Fhello.m4a" autoplayURL="/Add?service=LocalMusic&amp;expr=hello&amp;playnow=1"
        text="Hello" text2="Adele • 25" type="track"/>
</browse>"""


@pytest.fixture
def library(player_api: AiohttpClientMocker) -> AiohttpClientMocker:
    """A player whose library has an artist, two albums and a song."""
    respond(player_api, browse_url("LocalMusic:Search"), text=MENU)
    for key, text in (("artists", ARTISTS), ("albums", ALBUMS), ("songs", SONGS)):
        respond(player_api, browse_url(key), text=text)
    respond(
        player_api,
        f"{BASE}/Playlists",
        text="<playlists><name>Adele Favourites</name><name>Tuning</name></playlists>",
    )
    player_api.mock_calls.clear()
    return player_api


async def _search(hass: HomeAssistant, text: str, classes: list[str] | None = None) -> list:
    response = await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        "search_media",
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            "search_query": text,
            **({"media_filter_classes": classes} if classes else {}),
        },
        blocking=True,
        return_response=True,
    )
    return list(response[ENTITY_ID].result)


@pytest.mark.parametrize(
    ("title", "subtitle", "query", "score"),
    [
        ("Adele", "", "adele", 100),
        ("Céline Dion", "", "Celine DION", 100),
        ("Adele Live", "", "adele", 60),
        ("Greatest Hits of Adele", "", "adele", 40),
        ("Hello", "Adele • 25", "adele", 20),
        ("Recommence-moi", "", "recommence moi", 100),
        ("Hello", "Adele", "Lionel", 0),
        ("Hello", "", "", 0),
    ],
)
def test_match_score(title: str, subtitle: str, query: str, score: int) -> None:
    """Names are compared without case, accents or punctuation."""
    assert match_score(title, subtitle, query) == score


def test_normalize() -> None:
    """Accents and punctuation are dropped."""
    assert normalize("L'été – Ça va!") == "l ete ca va"


async def test_entity_supports_the_search(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Assist only offers search and play for players that can search."""
    features = hass.states.get(ENTITY_ID).attributes[ATTR_SUPPORTED_FEATURES]
    assert features & MediaPlayerEntityFeature.SEARCH_MEDIA


async def test_search_ranks_exact_matches_first(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The artist comes first, then what only starts with or mentions the name."""
    results = await _search(hass, "adele")

    assert [(r.title, r.media_class) for r in results] == [
        ("Adele", MediaClass.ARTIST),
        ("Adele Favourites", MediaClass.PLAYLIST),
        ("Adele Live - Adele", MediaClass.ALBUM),
        ("21 - Adele", MediaClass.ALBUM),
        ("Hello - Adele", MediaClass.TRACK),
    ]


async def test_results_play_what_they_say(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """Each kind of result starts the right thing on the player."""
    results = {r.media_class: r for r in await _search(hass, "adele")}

    paths = {
        media_class: play_path_from_media_id(result.media_content_id)[1]
        for media_class, result in results.items()
    }
    assert paths[MediaClass.ARTIST] == "/Add?artist=Adele&playnow=1&service=LocalMusic&shuffle=0"
    assert paths[MediaClass.TRACK] == "/Add?playnow=1&file=%2Fhello.m4a"
    assert paths[MediaClass.PLAYLIST] == "/Load?service=BluOS&name=Adele+Favourites"
    assert paths[MediaClass.ALBUM].startswith("/Add?playnow=1&service=LocalMusic&album=")


async def test_search_filters_by_class(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """Asking for an artist or an album only searches and returns those."""
    artists = await _search(hass, "adele", ["artist"])
    assert [(r.title, r.media_class) for r in artists] == [("Adele", MediaClass.ARTIST)]
    assert "/Playlists" not in [path for path, _ in calls(library)]

    albums = await _search(hass, "adele", ["album"])
    assert {r.media_class for r in albums} == {MediaClass.ALBUM}


async def test_search_finds_a_radio_preset(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """A station is found by its name, without accents, and plays as a preset."""
    respond(library, browse_url("LocalMusic:Search"), text="<browse/>")
    [result] = await _search(hass, "rtS la premiere")

    assert (result.title, result.media_class) == ("RTS La Première", MediaClass.CHANNEL)
    assert play_path_from_media_id(result.media_content_id)[1] == "/Preset?id=1"


async def test_search_retries_on_the_longest_word(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The player finds nothing for a title with a hyphen, a word of it is searched then."""
    respond(library, browse_url("LocalMusic:Search"), text="<browse/>")
    library.mock_calls.clear()
    results = await _search(hass, "Recommence-moi")
    assert results == []
    searched = [q.get("q") for path, q in calls(library) if path == "/Browse"]
    # The exact search first (the whole text, then its longest word), then the
    # typo tolerant one tries fragments, as nothing was found.
    assert searched[:2] == ["Recommence-moi", "Recommence"]
    assert searched[2:] == ["reco", "ence", "moi"]


async def test_play_media_accepts_a_search_result(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """Assist plays the first result with play_media."""
    [first, *_] = await _search(hass, "adele", ["artist"])
    library.mock_calls.clear()

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: first.media_content_id,
            ATTR_MEDIA_CONTENT_TYPE: first.media_content_type,
        },
        blocking=True,
    )

    assert calls(library) == [
        ("/Add", {"artist": "Adele", "playnow": "1", "service": "LocalMusic", "shuffle": "0"})
    ]


async def test_a_preset_that_loads_a_playlist_is_not_a_second_result(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The playlist is found once, a preset loading a missing one is a playlist too."""
    respond(
        library,
        f"{BASE}/Presets",
        text="""<presets prid="0">
  <preset id="1" name="Tuning" url="/Load?name=Tuning"/>
  <preset id="2" name="Old Mix" url="/Load?name=Old+Mix"/>
  <preset id="3" name="Tuning FM" url="TuneIn:s1"/>
</presets>""",
    )
    respond(library, browse_url("LocalMusic:Search"), text="<browse/>")

    results = await _search(hass, "tuning")
    assert [(r.title, r.media_class) for r in results] == [
        ("Tuning", MediaClass.PLAYLIST),
        ("Tuning FM", MediaClass.CHANNEL),
    ]
    old = await _search(hass, "old mix")
    assert [(r.title, r.media_class) for r in old] == [("Old Mix", MediaClass.PLAYLIST)]
    assert [r.media_class for r in await _search(hass, "tuning", ["album"])] == []


@pytest.mark.parametrize(
    ("title", "query", "found"),
    [
        ("Adele", "adelle", True),
        ("Coldplay", "cold play", True),
        ("Coldplay", "Coldpley", True),
        ("Led Zeppelin", "led zepelin", True),
        ("Led Zeppelin", "zepelin", True),
        ("Eddy Mitchell", "edy mitchel", True),
        ("Adele", "abba", False),
        ("Adele", "ade", False),
        ("Hello", "", False),
        ("Santana", "santa claus", False),
        ("Chicago Symphony Orchestra", "xylophone orchestra", False),
        ("Radio Swiss Jazz", "radio swis jazz", True),
    ],
)
def test_fuzzy_score(title: str, query: str, found: bool) -> None:
    """Typos and different spacing are tolerated, other names are not, and an exact match always wins."""
    score = fuzzy_score(title, query)
    assert bool(score) is found
    assert score < match_score(title, "", title)


def test_probes_are_the_start_and_the_end_of_the_longest_words() -> None:
    """The typo is unlikely to be both at the start and at the end of a word."""
    assert _probes("Led Zepelin") == ["zepe", "elin", "led"]
    assert _probes("abba") == ["abba"]
    assert _probes("Coldpley live") == ["cold", "pley", "live"]
    assert _probes("a b") == []


async def test_a_misspelled_artist_is_still_found(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """When nothing matches exactly, close names are offered, the best first."""
    results = await _search(hass, "adelle", ["artist"])
    assert [(r.title, r.media_class) for r in results] == [("Adele", MediaClass.ARTIST)]

    playlists = await _search(hass, "tunning", ["playlist"])
    assert [r.title for r in playlists] == ["Tuning"]


async def test_exact_matches_do_not_trigger_the_typo_tolerant_search(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """The extra requests are only made when nothing was found."""
    await _search(hass, "adele", ["artist"])
    searched = [q.get("q") for path, q in calls(library) if path == "/Browse" and "q" in q]
    assert searched == ["adele"]


async def test_nonsense_finds_nothing(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """A name that resembles nothing gives no result and no wrong guess."""
    assert await _search(hass, "xylophone orchestra") == []


def test_the_closest_whole_name_wins_among_close_words() -> None:
    """A misspelled artist ranks before the collaborations that contain his name."""
    query = "jean-jaque goldman"
    alone = fuzzy_score("Jean-Jacques Goldman", query)
    duo = fuzzy_score("Céline Dion; Jean-Jacques Goldman", query)
    many = fuzzy_score("Catherine Deneuve; Alain Souchon; Laurent Voulzy; Jean-Jacques Goldman", query)
    assert alone > duo > many > 0
    assert alone < match_score("Jean-Jacques Goldman", "", "Jean-Jacques Goldman")


@pytest.mark.parametrize(
    ("media_type", "name", "expected"),
    [
        ("music", "adele", ("/Add", {"artist": "Adele", "playnow": "1", "service": "LocalMusic", "shuffle": "0"})),
        ("artist", "adelle", ("/Add", {"artist": "Adele", "playnow": "1", "service": "LocalMusic", "shuffle": "0"})),
        ("playlist", "tuning", ("/Load", {"service": "BluOS", "name": "Tuning"})),
        ("music", "Rtsf la premiere", ("/Preset", {"id": "1"})),
    ],
)
async def test_play_media_accepts_a_name(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    library: AiohttpClientMocker,
    media_type: str,
    name: str,
    expected: tuple[str, dict[str, str]],
) -> None:
    """An AI agent asks to play a title as text: the best match of a search is played."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_ID: name,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
        },
        blocking=True,
    )
    assert calls(library)[-1] == expected


async def test_play_media_by_name_without_a_match(
    hass: HomeAssistant, init_integration: MockConfigEntry, library: AiohttpClientMocker
) -> None:
    """A name that matches nothing says so, and sends nothing to the player."""
    from homeassistant.exceptions import HomeAssistantError

    library.mock_calls.clear()
    with pytest.raises(HomeAssistantError, match="No results found for xylophone orchestra"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_ID: "xylophone orchestra",
                ATTR_MEDIA_CONTENT_TYPE: "music",
            },
            blocking=True,
        )
    assert [path for path, _ in calls(library) if path in ("/Add", "/Play", "/Load", "/Preset")] == []
