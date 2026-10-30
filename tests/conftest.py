"""Fixtures for the BluOS Companion tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from yarl import URL

from custom_components.bluos_companion.api import BluOSClient
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


SOURCES = """<radiotime service="Capture">
  <item text="Bluetooth" id="input1" type="audio" inputType="bluetooth" URL="Capture%3Abluez%3Abluetooth" typeIndex="bluetooth-1"></item>
  <item text="No index" type="audio" URL="x"></item>
</radiotime>"""
QUEUE = """<playlist length="2" id="1491">
  <song service="LocalMusic" id="0"><art>Prince</art><alb>Hits</alb><title>U Got the Look</title><image>/Artwork?service=LocalMusic&amp;album=Hits</image></song>
  <song service="LocalMusic" id="1"><art></art><alb></alb><title>Kiss</title></song>
</playlist>"""
GROUPED_SYNC_STATUS = (
    f'<SyncStatus id="{HOST}:11000" mac="{MAC}" name="Séjour" group="Séjour+Pulse" '
    'syncStat="2" volume="25"><slave id="192.168.1.101" port="11000" name="Pulse"/>'
    '<externalSource id="10" name="AppleTV"><item id="5" name="Phono"/><item id="9" name="BluOS" isBluos="true"/><item name="Broken"/></externalSource>'
    "</SyncStatus>"
)

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
PLAYLIST_TRACKS = """<browse type="tracks">
  <item playURL="/Add?playnow=1&amp;file=a" text="Skyfall" text2="ADELE • Skyfall - Single" image="/Artwork?service=BluOS&amp;songid=" type="track"></item>
</browse>"""
SONGS_SECTION = """<browse type="tracks">
  <item playURL="/Add?playnow=1&amp;file=%2Fa.m4a" text="À 82 ans" text2="Axelle Red • Toujours moi" image="/Artwork?service=LocalMusic&amp;album=x" type="track"></item>
</browse>"""


HOME = """<screen>
  <row id="presets" title="Presets"><largeThumbnail title="Ignored"/></row>
  <row id="recent-stations" title="Recent Stations">
    <largeThumbnail image="http://cdn.example/s6814.jpg" title="Radio Swiss Jazz">
      <action type="player-link" URI="/ui/prf?u=%2FPlay%3Furl%3DTuneIn%253As6814%26title1%3DRadio%2BSwiss%2BJazz"></action>
      <playAction type="player-link" URI="/ui/prf?u=%2FPlay%3Furl%3DTuneIn%253As6814%26title1%3DRadio%2BSwiss%2BJazz"></playAction>
    </largeThumbnail>
    <largeThumbnail image="x" title="A web address">
      <action type="player-link" URI="/ui/prf?u=%2FPlay%3Furl%3Dhttp%253A%252F%252Fexample.com"></action>
    </largeThumbnail>
  </row>
  <row id="recent" title="Recently Played">
    <item image="/Artwork?service=LocalMusic&amp;album=Io+Canto+2&amp;artist=Laura+Pausini" objectType="album" title="Io Canto 2" subTitle="Laura Pausini">
      <action type="browse" URI="/ui/browseContext?service=LocalMusic&amp;title=Io+Canto+2&amp;type=Album&amp;url=%2FAlbums%3Fservice%3DLocalMusic%26album%3DIo%2BCanto%2B2%26artist%3DLaura%2BPausini" resultType="screen"></action>
      <action type="player-link" URI="/ui/prf?u=%2FAdd%3Fplaynow%3D1"></action>
    </item>
    <item image="/Artwork?service=LocalMusic&amp;album=En+Public&amp;artist=Goldman" objectType="song" title="Je te donne" subTitle="Goldman &#8226; En Public">
      <action type="player-link" URI="/ui/prf?u=%2FAdd%3Fplaynow%3D1%26file%3D%252Fa.m4a" haptic="true"></action>
      <contextMenu type="browse" URI="/ui/ContextMenu?album=En+Public&amp;artist=Goldman&amp;context=Song&amp;filename=%2Fa.m4a&amp;service=LocalMusic&amp;title=Je+te+donne" resultType="contextMenu"></contextMenu>
    </item>
    <item objectType="album" title="Deezer album" subTitle="x">
      <action type="browse" URI="/ui/browseContext?service=Deezer&amp;url=%2FAlbums%3Fservice%3DDeezer%26album%3Dx%26artist%3Dy"></action>
    </item>
  </row>
  <row id="mostUsed" title="Most Used"></row>
</screen>"""


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


def respond(mocker: AiohttpClientMocker, url: str | URL, **kwargs: object) -> None:
    """Mock a GET that takes precedence over the ones registered earlier."""
    mocker.get(url, **kwargs)
    mocker._mocks.insert(0, mocker._mocks.pop())  # noqa: SLF001


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the custom integration."""


@pytest.fixture
async def client(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> BluOSClient:
    """Return a client."""
    return BluOSClient(async_get_clientsession(hass), HOST, 11000)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=format_mac(MAC),
        title="Séjour",
        minor_version=2,
        data={CONF_HOST: HOST, CONF_PORT: 11000},
    )


@pytest.fixture
def player_api(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the HTTP API of a player."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)
    aioclient_mock.get(f"{BASE}/Status", text=status_xml())
    aioclient_mock.get(f"{BASE}/ui/Home", text=HOME)
    aioclient_mock.get(f"{BASE}/Presets", text=PRESETS)
    aioclient_mock.get(f"{BASE}/Albums", text=RECENT)
    aioclient_mock.get(f"{BASE}/RadioBrowse", text=SOURCES)
    aioclient_mock.get(f"{BASE}/Playlist", text=QUEUE)
    for category, text in (
        ("albums", SECTIONS),
        ("artists", ARTISTS_SECTIONS),
        ("genres", GENRES),
        ("playlists", PLAYLISTS),
    ):
        aioclient_mock.get(browse_url(LIBRARY[category]), text=text)
    aioclient_mock.get(
        browse_url("BluOS:MG/BluOS-Playlist?playlist=Relaxing"), text=PLAYLIST_TRACKS
    )
    aioclient_mock.get(browse_url(SECTION_A_KEY), text=ALBUMS)
    aioclient_mock.get(browse_url(ALBUM_KEY), text=TRACKS)
    for path in ("Play", "Pause", "Stop", "Skip", "Back", "Volume", "Shuffle", "Repeat", "Clear", "Sleep", "AddSlave", "RemoveSlave"):
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
