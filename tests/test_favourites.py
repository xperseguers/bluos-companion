"""Tests for the favourites of the library."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator
from yarl import URL

from custom_components.bluos_companion.api import BluOSClient, Favourite, Favourites
from custom_components.bluos_companion.const import DOMAIN
from custom_components.bluos_companion.favourites_backup import (
    async_backup_favourites,
    describe,
    parse,
    render,
)

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
        (
            Favourite("album", "Patrick Fiori", "Promesse"),
            Favourite("artist", "Marine"),
            Favourite("song", title="Dalida", file=FILE),
        )
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


# ---- backup and restore of the favourites ----

ITEMS = (
    Favourite("album", "Patrick Fiori", "Promesse"),
    Favourite("artist", "Marine"),
    Favourite("song", "Marine", "Cœur maladroit", FILE, "Dalida"),
)


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Use a temporary configuration folder, return the favourites file."""
    hass.config.config_dir = str(tmp_path)
    return tmp_path / "bluos_companion" / "favourites.json"


def test_render_and_parse_round_trip() -> None:
    """The file keeps what identifies each favourite and what is useful to read it."""
    text = render(ITEMS, "Séjour", datetime(2026, 10, 31, 12, 0))
    data = json.loads(text)

    assert data["player"] == "Séjour"
    assert data["albums"] == [{"artist": "Patrick Fiori", "album": "Promesse"}]
    assert data["artists"] == ["Marine"]
    assert data["songs"][0]["title"] == "Dalida"
    assert "Cœur maladroit" in text  # not escaped
    assert parse(text) == ITEMS


def test_parse_leaves_out_what_is_not_understood() -> None:
    """A file edited by hand keeps its good entries."""
    text = json.dumps(
        {
            "albums": [{"artist": "A", "album": "B"}, {"artist": "no album"}, "text"],
            "artists": ["Marine", "", 3],
            "songs": [{"file": "/a.m4a"}, {"title": "no file"}],
        }
    )
    assert parse(text) == (
        Favourite("album", "A", "B"),
        Favourite("artist", "Marine"),
        Favourite("song", file="/a.m4a"),
    )


@pytest.mark.parametrize("text", ["not json", "[1, 2]"])
def test_parse_refuses_a_file_that_is_not_one(text: str) -> None:
    """The error says the file is not valid."""
    with pytest.raises(HomeAssistantError, match="not valid"):
        parse(text)


def test_describe() -> None:
    """Each kind has a short name for the user."""
    assert [describe(item) for item in ITEMS] == [
        "Patrick Fiori - Promesse",
        "Marine",
        "Marine - Dalida",
    ]
    assert describe(Favourite("song", file="/a.m4a")) == "/a.m4a"


async def test_backup_writes_the_file(
    hass: HomeAssistant, init_integration: MockConfigEntry, favourites_api: AiohttpClientMocker, config_dir: Path
) -> None:
    """The favourites of the library are saved with how many of each kind."""
    assert await async_backup_favourites(hass) == {"albums": 1, "artists": 1, "songs": 1}
    assert [item.kind for item in parse(config_dir.read_text(encoding="utf-8"))] == [
        "album",
        "artist",
        "song",
    ]


async def test_backup_keeps_the_previous_file_when_the_player_has_none(
    hass: HomeAssistant, init_integration: MockConfigEntry, favourites_api: AiohttpClientMocker, config_dir: Path
) -> None:
    """A player that lost its favourites does not erase the backup."""
    await async_backup_favourites(hass)
    before = config_dir.read_text(encoding="utf-8")
    for kind in ("Albums", "Artists", "Songs"):
        respond(favourites_api, f"{BASE}/{kind}?service=LocalMusic&category=FAVOURITES", text=f"<{kind.lower()}/>")

    assert await async_backup_favourites(hass) == {}
    assert config_dir.read_text(encoding="utf-8") == before


async def test_backup_follows_the_option_of_the_player(
    hass: HomeAssistant, init_integration: MockConfigEntry, favourites_api: AiohttpClientMocker, config_dir: Path
) -> None:
    """A player left out of the backup is not read."""
    hass.config_entries.async_update_entry(init_integration, options={"backup_playlists": False})

    assert await async_backup_favourites(hass) == {}
    assert not config_dir.exists()


class FavouritesPlayer:
    """A player whose favourites change when it is asked: only songs of its library are kept."""

    def __init__(self, api: AiohttpClientMocker, favourites: list[Favourite], library: set[str]) -> None:
        self.favourites = favourites
        self.library = library
        for kind in ("Albums", "Artists", "Songs"):
            respond(api, f"{BASE}/{kind}", side_effect=self._list)
        respond(api, f"{BASE}/AddFavourite", side_effect=self._add)

    async def _list(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        kind = url.path.strip("/")
        body = ""
        for item in self.favourites:
            if kind == "Albums" and item.kind == "album":
                body += f"<album><alb>{item.album}</alb><art>{item.artist}</art></album>"
            elif kind == "Artists" and item.kind == "artist":
                body += f"<art>{item.artist}</art>"
            elif kind == "Songs" and item.kind == "song":
                body += f"<song><title>{item.title}</title><fn>{item.file}</fn></song>"
        return AiohttpClientMockResponse(method, url, text=f"<{kind.lower()}>{body}</{kind.lower()}>")

    async def _add(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        query = dict(url.query)
        if "fn" in query:
            item = Favourite("song", file=query["fn"])
            if item.file not in self.library:
                return AiohttpClientMockResponse(method, url, text="<favourite>added</favourite>")
        elif "album" in query:
            item = Favourite("album", query["artist"], query["album"])
        else:
            item = Favourite("artist", query["artist"])
        self.favourites.append(item)
        return AiohttpClientMockResponse(method, url, text="<favourite>added</favourite>")


async def test_restore_adds_what_the_player_does_not_have(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> None:
    """Only the missing favourites are added, the ones the library does not have are listed."""
    config_dir.parent.mkdir(parents=True, exist_ok=True)
    gone = Favourite("song", "X", "Y", "/gone/a.m4a", "Gone")
    config_dir.write_text(render((*ITEMS, gone), "Séjour", datetime(2026, 10, 31)), encoding="utf-8")
    player = FavouritesPlayer(player_api, [ITEMS[0]], library={FILE})
    player_api.mock_calls.clear()

    result = await hass.services.async_call(
        DOMAIN, "restore_favourites", {"entity_id": "media_player.sejour"}, blocking=True, return_response=True
    )

    assert result == {"added": 2, "already": 1, "not_found": ["X - Gone"]}
    assert {item.key for item in player.favourites} == {item.key for item in ITEMS}
    added = [query for path, query in calls(player_api) if path == "/AddFavourite"]
    assert len(added) == 3  # the album that was there is not sent again


async def test_restore_without_a_file_says_so(
    hass: HomeAssistant, init_integration: MockConfigEntry, config_dir: Path
) -> None:
    """The error names the file that is expected."""
    with pytest.raises(HomeAssistantError, match="favourites.json"):
        await hass.services.async_call(
            DOMAIN, "restore_favourites", {"entity_id": "media_player.sejour"}, blocking=True
        )


async def test_the_backup_service_returns_the_count(
    hass: HomeAssistant, init_integration: MockConfigEntry, favourites_api: AiohttpClientMocker, config_dir: Path
) -> None:
    """The action tells how many favourites were saved."""
    result = await hass.services.async_call(DOMAIN, "backup_favourites", blocking=True, return_response=True)
    assert result == {"favourites": {"albums": 1, "artists": 1, "songs": 1}}
