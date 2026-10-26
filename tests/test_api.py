"""Tests for the BluOS API client."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.api import (
    Album,
    BluOSClient,
    BluOSError,
)

from .conftest import (
    ALBUM_KEY,
    BASE,
    HOST,
    MAC,
    SECTION_A_KEY,
    browse_url,
    calls,
    status_xml,
)


@pytest.fixture
async def client(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> BluOSClient:
    """Return a client."""
    return BluOSClient(async_get_clientsession(hass), HOST, 11000)


@pytest.mark.usefixtures("player_api")
async def test_player_info(client: BluOSClient) -> None:
    """The identity is read from SyncStatus."""
    info = await client.async_get_player_info()
    assert (info.name, info.mac, info.model, info.brand) == ("Séjour", MAC, "C368", "NAD")


async def test_player_info_rejects_other_devices(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """A response without MAC is not a BluOS player."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text="<html/>")
    with pytest.raises(BluOSError):
        await client.async_get_player_info()


@pytest.mark.parametrize(
    ("kwargs", "text"),
    [
        pytest.param({"exc": aiohttp.ClientError}, None, id="connection-error"),
        pytest.param({"status": 500}, "oops", id="http-error"),
        pytest.param({}, "not xml", id="invalid-xml"),
        pytest.param(
            {}, "<error><message>boom</message></error>", id="error-element"
        ),
    ],
)
async def test_errors(
    client: BluOSClient,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict,
    text: str | None,
) -> None:
    """Every failure is reported as BluOSError."""
    aioclient_mock.get(f"{BASE}/Status", text=text, **kwargs)
    with pytest.raises(BluOSError):
        await client.async_get_status()


async def test_status(client: BluOSClient, aioclient_mock: AiohttpClientMocker) -> None:
    """Status attributes are parsed."""
    aioclient_mock.get(f"{BASE}/Status", text=status_xml(mute="1", shuffle="1", repeat="0"))
    status = await client.async_get_status()
    assert status.etag == "e1"
    assert status.state == "play"
    assert (status.title, status.artist, status.album) == (
        "Rolling In the Deep",
        "Adele",
        "21",
    )
    assert (status.volume, status.muted, status.shuffle, status.repeat) == (25, True, True, 0)
    assert (status.can_seek, status.position, status.duration) == (True, 10, 228)


async def test_status_without_optional_values(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """A fixed-volume player on an input has no position."""
    aioclient_mock.get(
        f"{BASE}/Status", text='<status><state>stop</state><volume>-1</volume></status>'
    )
    status = await client.async_get_status()
    assert (status.volume, status.position, status.duration, status.title) == (
        -1,
        None,
        None,
        None,
    )


async def test_long_poll_parameters(
    client: BluOSClient, player_api: AiohttpClientMocker
) -> None:
    """The etag and timeout are sent for long polling."""
    await client.async_get_status("abc", 100)
    assert calls(player_api) == [("/Status", {"timeout": "100", "etag": "abc"})]


@pytest.mark.usefixtures("player_api")
async def test_recent_albums(client: BluOSClient) -> None:
    """Recent albums get their keys from album and artist."""
    albums = await client.async_get_recent_albums()
    assert albums[0] == Album("Definitely Maybe", "Oasis", "album=Definitely+Maybe&artist=Oasis")
    assert albums[1].query == "album=%C3%80+fleur+de+cordes&artist=Lynda+Lemay"
    assert albums[0].browse_key == "LocalMusic:MG/LocalMusic-Album?album=Definitely+Maybe&artist=Oasis"
    assert albums[0].image == "/Artwork?service=LocalMusic&album=Definitely+Maybe&artist=Oasis"
    assert albums[0].play_path == (
        "/Add?playnow=1&service=LocalMusic&album=Definitely+Maybe&artist=Oasis"
    )


@pytest.mark.usefixtures("player_api")
async def test_sections_and_albums(client: BluOSClient) -> None:
    """Sections and the albums of a section are parsed."""
    sections = await client.async_get_album_sections()
    assert [(s.name, s.count) for s in sections] == [("A", 84), ("#", 36)]
    assert sections[0].key == SECTION_A_KEY

    albums = await client.async_get_albums(SECTION_A_KEY)
    assert albums == [
        Album(
            "À côté du soleil",
            "Cristina Marocco",
            "album=%C3%80+c%C3%B4t%C3%A9+du+soleil&artist=Cristina+Marocco",
        )
    ]


@pytest.mark.usefixtures("player_api")
async def test_tracks(client: BluOSClient) -> None:
    """Tracks prefer the autoplay URL and need a play URL."""
    tracks = await client.async_get_tracks(ALBUM_KEY)
    assert [(t.title, t.duration) for t in tracks] == [
        ("1. Rolling In the Deep", 228),
        ("5. Set Fire to the Rain", 243),
    ]
    assert tracks[0].play_path.startswith("/Add?service=LocalMusic&listindex=0")
    assert tracks[1].play_path == "/Add?playnow=1&file=%2Fb.m4a"


@pytest.mark.usefixtures("player_api")
async def test_presets(client: BluOSClient) -> None:
    """Presets are parsed."""
    presets = await client.async_get_presets()
    assert [(p.id, p.name, p.image) for p in presets] == [
        (1, "RTS La Première", "http://cdn.example/s6809.png"),
        (2, "Rouge FM", "https://cdn.example/s58290.png"),
        (3, "No image", None),
    ]


@pytest.mark.parametrize(
    ("method", "args", "path", "query"),
    [
        ("async_play", (), "/Play", {}),
        ("async_seek", (42,), "/Play", {"seek": "42"}),
        ("async_pause", (), "/Pause", {}),
        ("async_stop", (), "/Stop", {}),
        ("async_skip", (), "/Skip", {}),
        ("async_back", (), "/Back", {}),
        ("async_set_volume", (30,), "/Volume", {"level": "30"}),
        ("async_set_mute", (True,), "/Volume", {"mute": "1"}),
        ("async_set_mute", (False,), "/Volume", {"mute": "0"}),
        ("async_set_shuffle", (True,), "/Shuffle", {"state": "1"}),
        ("async_set_repeat", (1,), "/Repeat", {"state": "1"}),
        ("async_load_preset", (4,), "/Preset", {"id": "4"}),
    ],
)
async def test_commands(
    client: BluOSClient,
    player_api: AiohttpClientMocker,
    method: str,
    args: tuple,
    path: str,
    query: dict[str, str],
) -> None:
    """Each command maps to the documented request."""
    await getattr(client, method)(*args)
    assert calls(player_api) == [(path, query)]


async def test_image(client: BluOSClient, player_api: AiohttpClientMocker) -> None:
    """Images come from the player."""
    assert await client.async_get_image("/Artwork?service=LocalMusic&album=x") == (
        b"image",
        "image/jpeg",
    )
    assert calls(player_api) == [("/Artwork", {"service": "LocalMusic", "album": "x"})]
