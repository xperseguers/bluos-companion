"""Tests for what the play button card needs: the playlist service and the items it lists."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.bluos_companion.api import playlist_play_path
from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, browse_url, calls, respond

ENTITY_ID = "media_player.sejour"
PLAYLIST_NAMES = (
    "<playlists><name>Relaxing</name><name>Morning Jazz</name><name>Jazz Night</name></playlists>"
)
SAVED = """<browse type="playlists">
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Relaxing" playURL="/Load?service=BluOS&amp;name=Relaxing" text="Relaxing" type="playlist"></item>
  <item browseKey="BluOS:MG/BluOS-Playlist?playlist=Morning+Jazz" playURL="/Load?service=BluOS&amp;name=Morning+Jazz" text="Morning Jazz" type="playlist"></item>
</browse>"""
GENRES = "<genres><genre>Jazz</genre><genre>Dance</genre><genre>blues</genre></genres>"


@pytest.fixture(autouse=True)
def library(player_api: AiohttpClientMocker) -> None:
    """A few saved playlists and genres."""
    respond(player_api, f"{BASE}/Playlists", text=PLAYLIST_NAMES)
    respond(player_api, browse_url("BluOS:"), text=SAVED)
    respond(player_api, f"{BASE}/Genres", text=GENRES)


def test_the_play_path_of_a_playlist() -> None:
    """The path is the one of Play now, or of Shuffle."""
    assert playlist_play_path("Morning Jazz") == (
        "/Add?clear=0&playlist=Morning+Jazz&playnow=1&service=BluOS&shuffle=0"
    )
    assert playlist_play_path("Relaxing", shuffle=True) == (
        "/Add?playlist=Relaxing&playnow=1&service=BluOS&shuffle=1"
    )


@pytest.mark.parametrize(
    ("playlist", "shuffle", "clear", "name", "paths"),
    [
        ("Relaxing", False, False, "Relaxing", ["/Playlists", "/Add"]),
        ("relaxing", True, False, "Relaxing", ["/Playlists", "/Add"]),
        ("morning", False, True, "Morning Jazz", ["/Playlists", "/Clear", "/Add"]),
    ],
)
async def test_the_service_plays_a_playlist(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    playlist: str,
    shuffle: bool,
    clear: bool,
    name: str,
    paths: list[str],
) -> None:
    """A playlist is found by its name, and plays in order or shuffled, with the queue emptied or not."""
    await hass.services.async_call(
        DOMAIN,
        "play_playlist",
        {"entity_id": ENTITY_ID, "playlist": playlist, "shuffle": shuffle, "clear_queue": clear},
        blocking=True,
    )
    made = calls(player_api)
    assert [path for path, _ in made] == paths
    assert made[-1][1]["playlist"] == name
    assert made[-1][1]["shuffle"] == ("1" if shuffle else "0")


@pytest.mark.parametrize(
    ("playlist", "message"),
    [("Metal", "Unknown playlist: Metal"), ("jazz", "ambiguous.*Jazz Night, Morning Jazz|ambiguous")],
)
async def test_the_service_refuses_what_it_cannot_tell(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    playlist: str,
    message: str,
) -> None:
    """An unknown or ambiguous playlist is an error and the queue is left alone."""
    with pytest.raises(HomeAssistantError, match=message):
        await hass.services.async_call(
            DOMAIN,
            "play_playlist",
            {"entity_id": ENTITY_ID, "playlist": playlist, "clear_queue": True},
            blocking=True,
        )
    assert [path for path, _ in calls(player_api)] == ["/Playlists"]


async def _items(
    hass: HomeAssistant, client: object, mode: str, item: str | None = None, entity_id: str = ENTITY_ID
) -> list[dict]:
    message = {"type": "bluos_companion/play_button_items", "entity_id": entity_id, "mode": mode}
    if item is not None:
        message["item"] = item
    await client.send_json_auto_id(message)
    response = await client.receive_json()
    assert response["success"], response
    return response["result"]["items"]


async def test_the_editor_lists_what_a_player_has(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """Genres and playlists come sorted by name, presets in their order and told apart by their number."""
    client = await hass_ws_client(hass)
    assert [item["name"] for item in await _items(hass, client, "genre")] == ["blues", "Dance", "Jazz"]
    assert [item["name"] for item in await _items(hass, client, "playlist")] == [
        "Morning Jazz",
        "Relaxing",
    ]
    presets = await _items(hass, client, "preset")
    assert [(item["value"], item["name"]) for item in presets] == [
        ("1", "RTS La Première"),
        ("2", "Rouge FM"),
        ("3", "No image"),
    ]
    # The list carries no artwork to look up: only the card asks for it
    assert {item["image"] for item in await _items(hass, client, "playlist")} == {None}


async def test_the_card_asks_for_its_own_item_with_its_artwork(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """One item, found without case, with a usable artwork URL (or none)."""
    respond(
        player_api,
        browse_url("BluOS:MG/BluOS-Playlist?playlist=Relaxing"),
        text="""<browse type="tracks">
  <item playURL="/Add?playnow=1&amp;file=a" text="Skyfall" text2="ADELE" image="/Artwork?service=LocalMusic&amp;album=Skyfall&amp;artist=ADELE" type="track"></item>
</browse>""",
    )
    client = await hass_ws_client(hass)
    [relaxing] = await _items(hass, client, "playlist", "relaxing")
    assert relaxing["name"] == "Relaxing"
    assert relaxing["image"].startswith("/api/bluos_companion/")
    [rouge] = await _items(hass, client, "preset", "2")
    assert rouge["image"] == "https://cdn.example/s58290.png"
    assert await _items(hass, client, "preset", "9") == []
    [dance] = await _items(hass, client, "genre", "dance")
    assert dance == {"value": "Dance", "name": "Dance", "image": None}


async def test_the_items_of_something_that_is_not_a_player_are_refused(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """An entity that is not a BluOS Companion player is an error."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/play_button_items",
            "entity_id": "light.kitchen",
            "mode": "genre",
        }
    )
    assert not (await client.receive_json())["success"]
