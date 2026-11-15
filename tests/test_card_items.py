"""Tests for the playlists and the favourite albums that the presets card shows as a grid."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from .conftest import BASE, browse_url, calls, respond

SAVED = """<browse type="playlists">
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Relaxing" text="Relaxing" type="playlist"></item>
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Morning+Jazz" text="Morning Jazz" type="playlist"></item>
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Dance" text="Dance" type="playlist"></item>
</browse>"""
FAVOURITES = "LocalMusic:MG/LocalMusic-Favourites"
FAVOURITE_ALBUMS = "LocalMusic:Album/%2Flibrary%2Fv1%2FAlbums%3Fcategory=FAVOURITES&service=LocalMusic"
SECTION = f"""<browse>
  <item browseKey="LocalMusic:Artist/x" text="Artists" type="link"></item>
  <item browseKey="{FAVOURITE_ALBUMS.replace("&", "&amp;")}" text="Albums" type="link"></item>
</browse>"""
ALBUMS = """<browse>
  <item browseKey="LocalMusic:MG/LocalMusic-Album?album=Egregore&amp;artist=Mylene" playURL="/Add?playnow=1&amp;service=LocalMusic&amp;album=Egregore&amp;artist=Mylene" text="Egregore" text2="Mylene" image="/Artwork?service=LocalMusic&amp;album=Egregore&amp;artist=Mylene" type="album"></item>
  <item browseKey="LocalMusic:MG/LocalMusic-Album?album=Almost&amp;artist=Elvis" playURL="/Add?playnow=1&amp;service=LocalMusic&amp;album=Almost&amp;artist=Elvis" text="Almost" text2="Elvis" type="album"></item>
</browse>"""


@pytest.fixture(autouse=True)
def library(player_api: AiohttpClientMocker) -> None:
    """Saved playlists, and favourite albums among the favourites of the library."""
    respond(player_api, browse_url("BluOS:"), text=SAVED)
    respond(player_api, browse_url(FAVOURITES), text=SECTION)
    respond(player_api, browse_url(FAVOURITE_ALBUMS), text=ALBUMS)
    for name in ("Relaxing", "Morning+Jazz", "Dance"):
        respond(player_api, browse_url(f"BluOS:MG/BluOS-Playlist?playlist={name}"), text="<browse></browse>")


async def _items(
    hass: HomeAssistant, client: Any, entry: MockConfigEntry, content: str, **extra: Any
) -> list[dict[str, Any]]:
    await client.send_json_auto_id(
        {"type": "bluos_companion/card_items", "entry_id": entry.entry_id, "content": content, **extra}
    )
    response = await client.receive_json()
    assert response["success"], response
    return response["result"]["items"]


async def test_playlists_come_sorted_with_their_play_path(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """Alphabetical, each tile carries the path that plays the playlist."""
    client = await hass_ws_client(hass)
    items = await _items(hass, client, init_integration, "playlists")
    assert [item["name"] for item in items] == ["Dance", "Morning Jazz", "Relaxing"]
    assert items[2]["path"] == "/Add?clear=0&playlist=Relaxing&playnow=1&service=BluOS&shuffle=0"


async def test_the_limit_cuts_the_list_before_the_covers_are_looked_up(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Only the tiles that are shown cost a request for their cover."""
    client = await hass_ws_client(hass)
    items = await _items(hass, client, init_integration, "playlists", limit=1)
    assert [item["name"] for item in items] == ["Dance"]
    assert all("Relaxing" not in query.get("key", "") for _, query in calls(player_api))


async def test_favourites_are_the_favourite_albums(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """The albums of the favourites, with their play path and, when they have one, a cover."""
    client = await hass_ws_client(hass)
    items = await _items(hass, client, init_integration, "favourites")
    assert [(item["name"], item["subtitle"]) for item in items] == [("Egregore", "Mylene"), ("Almost", "Elvis")]
    assert items[0]["path"] == "/Add?playnow=1&service=LocalMusic&album=Egregore&artist=Mylene"
    assert items[0]["image"].startswith("/api/bluos_companion/")
    assert items[1]["image"] is None
    assert [item["name"] for item in await _items(hass, client, init_integration, "favourites", limit=1)] == ["Egregore"]


async def test_no_favourite_albums_is_an_empty_grid(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A library without the albums section of the favourites gives no tile, not an error."""
    player_api.clear_requests()
    respond(player_api, browse_url(FAVOURITES), text="<browse></browse>")
    client = await hass_ws_client(hass)
    assert await _items(hass, client, init_integration, "favourites") == []


@pytest.mark.parametrize("message", [{"content": "genres"}, {"content": "playlists", "limit": 0}])
async def test_other_content_and_silly_limits_are_refused(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry, message: dict[str, Any]
) -> None:
    """Only playlists and favourites, between 1 and 200 tiles."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/card_items", "entry_id": init_integration.entry_id, **message}
    )
    assert not (await client.receive_json())["success"]


@pytest.mark.parametrize(
    "path",
    [
        "/Add?clear=0&playlist=Relaxing&playnow=1&service=BluOS&shuffle=0",
        "/Add?playnow=1&service=LocalMusic&album=Egregore&artist=Mylene",
    ],
)
async def test_the_tiles_play_through_the_panel_command(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    path: str,
) -> None:
    """The paths of the tiles are accepted by the command that plays something."""
    respond(player_api, f"{BASE}/Add", text="<ok/>")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/play", "entry_id": init_integration.entry_id, "path": path})
    assert (await client.receive_json())["success"]
