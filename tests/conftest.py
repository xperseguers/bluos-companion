"""Fixtures for the BluOS Companion tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from yarl import URL

from custom_components.bluos_companion.const import CONF_PORT, DOMAIN
from custom_components.bluos_companion.media_source import LIBRARY

HOST = "192.168.1.100"
BASE = f"http://{HOST}:11000"
MAC = "AA:BB:CC:DD:EE:FF"

SYNC_STATUS = (
    f'<SyncStatus id="{HOST}:11000" mac="{MAC}" name="Séjour" model="C368" '
    'modelName="C368" brand="NAD" volume="25"/>'
)

SECTIONS = """<browse type="sections">
  <item browseKey="LocalMusic:S:Album/%2Flibrary%2Fv1%2FAlbums%3Fservice=LocalMusic&amp;limit=50&amp;section=A" text="A" text2="84" type="section"></item>
  <item browseKey="LocalMusic:S:Album/%2Flibrary%2Fv1%2FAlbums%3Fservice=LocalMusic&amp;limit=50&amp;section=%23" text="#" text2="36" type="section"></item>
</browse>"""
SECTION_A_KEY = (
    "LocalMusic:S:Album/%2Flibrary%2Fv1%2FAlbums%3Fservice=LocalMusic"
    "&limit=50&section=A"
)
ALBUMS = """<browse type="albums">
  <item browseKey="LocalMusic:MG/LocalMusic-Album?album=%C3%80+c%C3%B4t%C3%A9+du+soleil&amp;artist=Cristina+Marocco" playURL="/Add?playnow=1&amp;service=LocalMusic&amp;album=x" text="À côté du soleil" text2="Cristina Marocco" tracks="13" image="/Artwork?service=LocalMusic&amp;album=x" type="album"></item>
  <item text="Not an album" type="link"></item>
</browse>"""
ALBUM_KEY = "LocalMusic:MG/LocalMusic-Album?album=21&artist=Adele"
TRACKS = """<browse type="tracks">
  <item playURL="/Add?playnow=1&amp;file=%2Fa.m4a" autoplayURL="/Add?service=LocalMusic&amp;listindex=0&amp;playnow=1&amp;album=21&amp;artist=Adele" text="1. Rolling In the Deep" text2="Adele" duration="228" image="/Artwork?service=LocalMusic&amp;artist=Adele&amp;album=21" type="track"></item>
  <item playURL="/Add?playnow=1&amp;file=%2Fb.m4a" text="5. Set Fire to the Rain" text2="Adele" duration="243" type="track"></item>
  <item text="no play url" type="track"></item>
</browse>"""
RECENT = """<albums recent="1" id="585" service="LocalMusic">
  <album><alb>Definitely Maybe</alb><art>Oasis</art></album>
  <album><alb>À fleur de cordes</alb><art>Lynda Lemay</art></album>
</albums>"""
PRESETS = """<presets prid="0">
  <preset id="1" name="RTS La Première" url="TuneIn:s6809" image="http://cdn.example/s6809.png"></preset>
  <preset id="2" name="Rouge FM" url="TuneIn:s58290" image="https://cdn.example/s58290.png"></preset>
  <preset id="3" name="No image" url="TuneIn:s1"></preset>
</presets>"""


ARTISTS_SECTIONS = """<browse type="sections">
  <item browseKey="LocalMusic:S:Artist/x&amp;section=A" text="A" text2="67" type="section"></item>
</browse>"""
GENRES = """<browse type="genres">
  <item browseKey="LocalMusic:MG/Genres?genre=Pop" text="Pop" type="genre"></item>
  <item text="Not browsable" type="text"></item>
</browse>"""
PLAYLISTS = """<browse type="playlists">
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Relaxing" playURL="/Load?service=BluOS&amp;name=Relaxing" text="Relaxing" type="playlist"></item>
</browse>"""
SONGS_SECTION = """<browse type="tracks">
  <item playURL="/Add?playnow=1&amp;file=%2Fa.m4a" text="À 82 ans" text2="Axelle Red • Toujours moi" image="/Artwork?service=LocalMusic&amp;album=x" type="track"></item>
</browse>"""


def status_xml(state: str = "play", **overrides: str) -> str:
    """Return a /Status response."""
    values = {
        "album": "21",
        "artist": "Adele",
        "canSeek": "1",
        "image": "/Artwork?service=LocalMusic&amp;album=21&amp;artist=Adele",
        "mute": "0",
        "name": "Rolling In the Deep",
        "title1": "Rolling In the Deep",
        "repeat": "2",
        "service": "LocalMusic",
        "shuffle": "0",
        "totlen": "228",
        "secs": "10",
        "volume": "25",
    } | overrides
    body = "".join(f"<{key}>{value}</{key}>" for key, value in values.items())
    return f'<status etag="e1"><state>{state}</state>{body}</status>'


def browse_url(key: str) -> URL:
    """Return the mocked /Browse URL for a key."""
    return URL(f"{BASE}/Browse").with_query({"key": key})


def calls(aioclient_mock: AiohttpClientMocker) -> list[tuple[str, dict[str, str]]]:
    """Return the (path, query) of the requests made so far."""
    return [(call[1].path, dict(call[1].query)) for call in aioclient_mock.mock_calls]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration."""


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        title="Séjour",
        data={CONF_HOST: HOST, CONF_PORT: 11000},
    )


@pytest.fixture
def player_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the HTTP API of a player."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)
    aioclient_mock.get(f"{BASE}/Status", text=status_xml())
    aioclient_mock.get(f"{BASE}/Presets", text=PRESETS)
    aioclient_mock.get(f"{BASE}/Albums", text=RECENT)
    for category, text in (
        ("albums", SECTIONS),
        ("artists", ARTISTS_SECTIONS),
        ("genres", GENRES),
        ("playlists", PLAYLISTS),
    ):
        aioclient_mock.get(browse_url(LIBRARY[category][1]), text=text)
    aioclient_mock.get(browse_url(SECTION_A_KEY), text=ALBUMS)
    aioclient_mock.get(browse_url(ALBUM_KEY), text=TRACKS)
    for path in ("Play", "Pause", "Stop", "Skip", "Back", "Volume", "Shuffle", "Repeat"):
        aioclient_mock.get(f"{BASE}/{path}", text="<state>play</state>")
    aioclient_mock.get(f"{BASE}/Add", text="<ok/>")
    aioclient_mock.get(f"{BASE}/Preset", text="<ok/>")
    aioclient_mock.get(f"{BASE}/Load", text="<ok/>")
    aioclient_mock.get(f"{BASE}/Artwork", content=b"image", headers={"Content-Type": "image/jpeg"})
    return aioclient_mock


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> MockConfigEntry:
    """Set up the integration without the background long poll."""
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.bluos_companion.BluOSCoordinator.async_long_poll",
        new=AsyncMock(),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    player_api.mock_calls.clear()
    return config_entry
