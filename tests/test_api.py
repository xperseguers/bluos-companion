"""Tests for the BluOS API client."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.api import (
    Action,
    Album,
    MAX_BROWSE_PAGES,
    BluOSClient,
    BluOSError,
    Node,
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
async def test_browse(client: BluOSClient) -> None:
    """Entries of a browse key are parsed."""
    nodes = await client.async_browse(SECTION_A_KEY)
    assert nodes[0] == Node(
        type="album",
        title="À côté du soleil",
        subtitle="Cristina Marocco",
        browse_key="LocalMusic:MG/LocalMusic-Album?album=%C3%80+c%C3%B4t%C3%A9+du+soleil&artist=Cristina+Marocco",
        play_path="/Add?playnow=1&service=LocalMusic&album=x",
        image="/Artwork?service=LocalMusic&album=x",
    )
    assert nodes[1].type == "link"
    assert nodes[1].browse_key is None


async def test_browse_merges_pages(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """Pages repeating earlier entries do not duplicate them."""
    first = '<browse nextKey="page2"><item text="a" type="track" playURL="/Add?a"/></browse>'
    second = (
        '<browse nextKey="page3"><item text="a" type="track" playURL="/Add?a"/>'
        '<item text="b" type="track" playURL="/Add?b"/></browse>'
    )
    third = (
        '<browse><item text="a" type="track" playURL="/Add?a"/>'
        '<item text="b" type="track" playURL="/Add?b"/>'
        '<item text="c" type="track" playURL="/Add?c"/></browse>'
    )
    for key, text in (("page1", first), ("page2", second), ("page3", third)):
        aioclient_mock.get(browse_url(key), text=text)

    nodes = await client.async_browse("page1")

    assert [node.title for node in nodes] == ["a", "b", "c"]


async def test_browse_stops_after_page_limit(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """A player looping on nextKey does not loop forever."""
    aioclient_mock.get(
        browse_url("loop"), text='<browse nextKey="loop"><item text="a" type="link" browseKey="k"/></browse>'
    )
    nodes = await client.async_browse("loop")
    assert len(nodes) == 1
    assert len(calls(aioclient_mock)) == MAX_BROWSE_PAGES


async def test_browse_page_search_and_limit(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """A search sends the query once, reports the source's search key and can stop at page one."""
    aioclient_mock.get(
        f"{BASE}/Browse",
        text='<browse searchKey="Deezer:Search" nextKey="more"><item text="a" type="link" browseKey="k"/></browse>',
    )

    page = await client.async_browse_page("Deezer:Search", "Michael", max_pages=1)

    assert page.search_key == "Deezer:Search"
    assert [node.title for node in page.nodes] == ["a"]
    assert calls(aioclient_mock) == [
        ("/Browse", {"key": "Deezer:Search", "q": "Michael"})
    ]


async def test_actions_of_an_item(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """The context menu of an item gives its play and queue actions."""
    aioclient_mock.get(
        browse_url("LocalMusic:CM/Album?album=21"),
        text="""<browse type="contextMenu">
  <item actionURL="/AddFavourite?album=21" text="Favourite" type="favourite-add"></item>
  <item actionURL="/Add?album=21&amp;playnow=-1&amp;where=last" text="Add last" type="addAll-last"></item>
  <item text="No action" type="x"></item>
</browse>""",
    )
    actions = await client.async_get_actions("LocalMusic:CM/Album?album=21")
    assert actions == [
        Action("favourite-add", "Favourite", "/AddFavourite?album=21"),
        Action("addAll-last", "Add last", "/Add?album=21&playnow=-1&where=last"),
    ]


async def test_browse_keeps_the_context_key(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """Items remember the key of their context menu."""
    aioclient_mock.get(
        browse_url("k"),
        text='<browse><item text="a" type="album" browseKey="b" contextMenuKey="ctx"/></browse>',
    )
    [node] = await client.async_browse("k")
    assert node.context_key == "ctx"


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
