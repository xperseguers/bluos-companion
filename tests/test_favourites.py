"""Tests for the favourites of the library."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.bluos_companion.api import BluOSClient, Favourite, Favourites

from .conftest import BASE, browse_url, calls, respond

FILE = "/var/mnt/nas/Music/Marine/Cœur maladroit/06 Dalida.m4a"
FAVOURITE_ALBUMS = """<albums category="FAVOURITES"><album isFavourite="1"><alb>Promesse</alb><art>Patrick Fiori</art></album></albums>"""
FAVOURITE_ARTISTS = """<artists category="FAVOURITES"><art isFavourite="1">Marine</art></artists>"""
FAVOURITE_SONGS = f"""<songs category="FAVOURITES"><song isFavourite="1"><title>Dalida</title><fn>{FILE}</fn></song></songs>"""


@pytest.fixture
def favourites_api(player_api: AiohttpClientMocker) -> AiohttpClientMocker:
    """A player with a favourite album, artist and song."""
    for kind, text in (
        ("Albums", FAVOURITE_ALBUMS),
        ("Artists", FAVOURITE_ARTISTS),
        ("Songs", FAVOURITE_SONGS),
    ):
        respond(player_api, f"{BASE}/{kind}?service=LocalMusic&category=FAVOURITES", text=text)
    for command in ("AddFavourite", "DeleteFavourite"):
        respond(player_api, f"{BASE}/{command}", text='<favourite service="LocalMusic">done</favourite>')
    player_api.mock_calls.clear()
    return player_api


@pytest.mark.parametrize(
    ("favourite", "params"),
    [
        (Favourite("album", "Patrick Fiori", "Promesse"), {"album": "Promesse", "artist": "Patrick Fiori"}),
        (Favourite("artist", "Marine"), {"artist": "Marine"}),
        (Favourite("song", file=FILE), {"fn": FILE}),
    ],
)
def test_what_identifies_a_favourite(favourite: Favourite, params: dict[str, str]) -> None:
    """Each kind is given to the player with the parameters it knows."""
    assert favourite.params == {**params, "service": "LocalMusic"}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/AddFavourite?album=Promesse&artist=Patrick+Fiori&service=LocalMusic", Favourite("album", "Patrick Fiori", "Promesse")),
        ("/DeleteFavourite?artist=Marine&service=LocalMusic", Favourite("artist", "Marine")),
        (f"/AddFavourite?fn={FILE.replace(' ', '+')}&service=LocalMusic", Favourite("song", file=FILE)),
        ("/AddFavourite?albumid=1&service=Deezer", None),
        ("/AddFavourite?service=LocalMusic", None),
        ("/Reboot", None),
    ],
)
def test_a_favourite_from_the_path_of_the_player(path: str, expected: Favourite | None) -> None:
    """Only the library's favourites are understood, whatever else a path says."""
    assert Favourite.from_path(path) == expected


async def test_the_favourites_are_read(client: BluOSClient, favourites_api: AiohttpClientMocker) -> None:
    """The favourite albums, artists and songs are listed, and an item is told from them."""
    favourites = await client.async_get_favourites()

    assert favourites == Favourites(
        albums=frozenset({("Patrick Fiori", "Promesse")}),
        artists=frozenset({"Marine"}),
        songs=frozenset({FILE}),
    )
    assert Favourite("album", "Patrick Fiori", "Promesse") in favourites
    assert Favourite("album", "Patrick Fiori", "Other") not in favourites
    assert Favourite("artist", "Marine") in favourites
    assert Favourite("song", file="/other.m4a") not in favourites


@pytest.mark.parametrize(("on", "command"), [(True, "/AddFavourite"), (False, "/DeleteFavourite")])
async def test_a_favourite_is_added_or_removed(
    client: BluOSClient, favourites_api: AiohttpClientMocker, on: bool, command: str
) -> None:
    """The player is asked to add or to delete it."""
    await client.async_set_favourite(Favourite("album", "Patrick Fiori", "Promesse"), on)

    assert calls(favourites_api) == [
        (command, {"album": "Promesse", "artist": "Patrick Fiori", "service": "LocalMusic"})
    ]


CONTEXT_MENU = """<browse type="contextMenu">
  <item actionURL="/AddFavourite?album=Promesse&amp;artist=Patrick+Fiori&amp;service=LocalMusic" text="Favourite" type="favourite-add"></item>
  <item actionURL="/Add?album=Promesse&amp;artist=Patrick+Fiori&amp;playnow=1&amp;service=LocalMusic" text="Play now" type="add-now"></item>
</browse>"""


@pytest.mark.parametrize(
    ("menu", "on"),
    [
        (CONTEXT_MENU, True),
        (CONTEXT_MENU.replace("Promesse", "Elsewhere"), False),
    ],
)
async def test_the_actions_offer_the_favourite_that_fits(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    favourites_api: AiohttpClientMocker,
    menu: str,
    on: bool,
) -> None:
    """A favourite album is offered to be removed, another one to be added."""
    respond(favourites_api, browse_url("ctx"), text=menu)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "bluos_companion/actions", "entry_id": init_integration.entry_id, "key": "ctx"}
    )
    actions = (await client.receive_json())["result"]["actions"]

    assert [action["type"] for action in actions] == ["add-now", "favourite"]
    favourite = actions[1]
    assert favourite["on"] is on
    assert favourite["favourite"]["kind"] == "album"
    assert favourite["favourite"]["album"] in ("Promesse", "Elsewhere")
    assert "path" not in favourite


async def test_no_favourite_action_for_what_cannot_be_one(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    favourites_api: AiohttpClientMocker,
) -> None:
    """A menu without the favourite entry of the player (a radio station) has none."""
    respond(
        favourites_api,
        browse_url("ctx"),
        text='<browse><item actionURL="/Add?playnow=1&amp;service=LocalMusic" text="Play now" type="add-now"/></browse>',
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/actions", "entry_id": init_integration.entry_id, "key": "ctx"}
    )
    actions = (await client.receive_json())["result"]["actions"]
    assert [action["type"] for action in actions] == ["add-now"]


@pytest.mark.parametrize("on", [True, False])
async def test_the_panel_sets_a_favourite(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    favourites_api: AiohttpClientMocker,
    on: bool,
) -> None:
    """The websocket command adds or removes a song, an album or an artist."""
    client = await hass_ws_client(hass)
    for payload in (
        {"kind": "song", "file": FILE},
        {"kind": "album", "artist": "Patrick Fiori", "album": "Promesse"},
        {"kind": "artist", "artist": "Marine"},
    ):
        await client.send_json_auto_id(
            {
                "type": "bluos_companion/favourite",
                "entry_id": init_integration.entry_id,
                "on": on,
                **payload,
            }
        )
        assert (await client.receive_json())["success"]

    command = "/AddFavourite" if on else "/DeleteFavourite"
    assert [path for path, _ in calls(favourites_api)] == [command] * 3
    assert calls(favourites_api)[0][1] == {"fn": FILE, "service": "LocalMusic"}


@pytest.mark.parametrize(
    "payload",
    [{"kind": "song"}, {"kind": "album", "artist": "A"}, {"kind": "artist"}],
)
async def test_the_panel_must_say_what_to_favour(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    favourites_api: AiohttpClientMocker,
    payload: dict[str, str],
) -> None:
    """Nothing is sent to the player when the item is not identified."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/favourite", "entry_id": init_integration.entry_id, "on": True, **payload}
    )
    assert not (await client.receive_json())["success"]
    assert calls(favourites_api) == []
