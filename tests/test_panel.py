"""Tests for the sidebar panel and its websocket API."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components import frontend
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import PANEL_PATH

from .conftest import BASE, browse_url, calls, respond, status_xml

ROOT = """<browse type="menu">
  <item browseKey="BluOS:" text="Playlists" image="/images/ci_myplaylists.png" type="link"></item>
  <item playURL="/Play?url=Capture%3Abluez%3Abluetooth" text="Bluetooth" type="audio"></item>
  <item browseKey="LocalMusic:" text="Library" image="/images/LibraryIcon.png" type="link"></item>
  <item browseKey="LocalMusic:Albums" playURL="/Add?playnow=1&amp;album=x" text="Albums" text2="Artist" type="album"></item>
</browse>"""


async def test_panel_is_registered_for_everyone_and_removed(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The panel is in the sidebar for non-admins and goes away with the last player."""
    panel = hass.data[frontend.DATA_PANELS][PANEL_PATH]
    assert panel.require_admin is False
    assert panel.sidebar_title == "BluOS Companion"

    await hass.config_entries.async_unload(init_integration.entry_id)
    assert PANEL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_card_module_is_loaded_by_the_frontend(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The presets card is available in the card picker without a manual resource."""
    urls = hass.data[frontend.DATA_EXTRA_MODULE_URL].urls
    assert any(
        url.startswith("/bluos_companion/panel/bluos-companion-presets-card.js?v=")
        for url in urls
    )


async def test_subscribe_pushes_players(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """Subscribing sends the state of every player with a signed cover URL."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/subscribe"})
    assert (await client.receive_json())["success"]
    event = (await client.receive_json())["event"]

    [player] = event["players"]
    assert player["entry_id"] == init_integration.entry_id
    assert player["name"] == "Séjour"
    assert (player["title"], player["artist"], player["state"]) == (
        "Rolling In the Deep",
        "Adele",
        "play",
    )
    assert player["volume"] == 25
    assert player["image"].startswith(
        f"/api/bluos_companion/{init_integration.entry_id}/artwork?path="
    )
    assert player["group"] == {"name": None, "master": None, "slaves": []}
    assert player["entity_id"] == "media_player.sejour"
    assert player["sources"] == ["Bluetooth"]
    assert player["source"] is None


@pytest.mark.parametrize(
    ("action", "value", "path", "query"),
    [
        ("play", None, "/Play", {}),
        ("pause", None, "/Pause", {}),
        ("stop", None, "/Stop", {}),
        ("next", None, "/Skip", {}),
        ("previous", None, "/Back", {}),
        ("seek", 42, "/Play", {"seek": "42"}),
        ("volume", 30, "/Volume", {"level": "30"}),
        ("volume", 250, "/Volume", {"level": "100"}),
        ("mute", True, "/Volume", {"mute": "1"}),
        ("shuffle", False, "/Shuffle", {"state": "0"}),
        ("repeat", 1, "/Repeat", {"state": "1"}),
    ],
)
async def test_control(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    action: str,
    value: Any,
    path: str,
    query: dict[str, str],
) -> None:
    """Controls are translated into player commands."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/control",
            "entry_id": init_integration.entry_id,
            "action": action,
            **({} if value is None else {"value": value}),
        }
    )
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [(path, query)]


async def test_control_errors(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Unknown players and player failures are reported."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/control", "entry_id": "nope", "action": "play"}
    )
    assert (await client.receive_json())["error"]["message"] == "Unknown player"

    respond(player_api, f"{BASE}/Play", status=500)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/control",
            "entry_id": init_integration.entry_id,
            "action": "play",
        }
    )
    assert (await client.receive_json())["error"]["message"].startswith(
        "BluOS player error"
    )


async def test_browse_root_and_menu(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The root lists the sources; only items that expand or play are kept."""
    respond(player_api, f"{BASE}/Browse", text=ROOT)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/browse", "entry_id": init_integration.entry_id}
    )
    items = (await client.receive_json())["result"]["items"]

    assert calls(player_api) == [("/Browse", {})]
    assert [item["title"] for item in items] == ["Playlists", "Library", "Albums"]
    assert items[0]["browse_key"] == "BluOS:"
    assert items[0]["play_path"] is None
    assert items[1]["image"] == "/bluos_companion/icons/library.svg"
    assert items[2]["play_path"].startswith("/Add?")
    assert items[2]["browse_key"] == "LocalMusic:Albums"


async def test_browse_translates_library_menu(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Library menu links get the French names of the player and our own icons."""
    hass.config.language = "fr"
    respond(
        player_api,
        f"{BASE}/Browse",
        text='<browse type="menu"><item browseKey="x" text="Songs" type="link"></item></browse>',
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/browse",
            "entry_id": init_integration.entry_id,
            "key": "LocalMusic:",
        }
    )
    [item] = (await client.receive_json())["result"]["items"]
    assert calls(player_api) == [("/Browse", {"key": "LocalMusic:"})]
    assert item["title"] == "Chansons"
    assert item["image"] == "/bluos_companion/icons/songs.svg"


@pytest.mark.parametrize(
    ("path", "allowed"),
    [
        ("/Add?playnow=1&album=x", True),
        ("/Load?service=BluOS&name=a", True),
        ("/Reboot", False),
        ("/Play?url=http%3A%2F%2Fevil", False),
    ],
)
async def test_play_only_allowed_paths(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    path: str,
    allowed: bool,
) -> None:
    """Only play URLs are forwarded to the player."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/play",
            "entry_id": init_integration.entry_id,
            "path": path,
        }
    )
    response = await client.receive_json()
    assert response["success"] is allowed
    assert len(calls(player_api)) == allowed


async def test_browse_reports_the_search_key(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The panel learns which key searches the source it is browsing."""
    respond(
        player_api,
        f"{BASE}/Browse",
        text='<browse searchKey="LocalMusic:Search" type="menu"><item browseKey="x" text="Albums" type="link"/></browse>',
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/browse", "entry_id": init_integration.entry_id}
    )
    assert (await client.receive_json())["result"]["search_key"] == "LocalMusic:Search"


async def test_search_groups_results_by_category(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A search returns the first results of each category, without empty ones."""
    respond(
        player_api,
        browse_url("LocalMusic:Search"),
        text="""<browse type="menu">
  <item browseKey="artists-key" text="Artists" type="link"/>
  <item browseKey="songs-key" text="Songs" type="link"/>
  <item browseKey="composers-key" text="Composers" type="link"/>
</browse>""",
    )
    respond(
        player_api,
        browse_url("artists-key"),
        text='<browse><item browseKey="a" text="Adele" type="artist"/></browse>',
    )
    respond(
        player_api,
        browse_url("songs-key"),
        text='<browse><item playURL="/Add?playnow=1&amp;file=x" text="Hello" text2="Adele" type="track"/></browse>',
    )
    respond(player_api, browse_url("composers-key"), text="<browse/>")
    hass.config.language = "fr"
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "bluos_companion/search",
            "entry_id": init_integration.entry_id,
            "key": "LocalMusic:Search",
            "query": "adele",
        }
    )
    groups = (await client.receive_json())["result"]["groups"]

    assert [group["title"] for group in groups] == ["Artistes", "Chansons"]
    assert groups[0]["items"][0]["title"] == "Adele"
    assert groups[1]["items"][0]["play_path"].startswith("/Add?")
    assert calls(player_api)[0] == (
        "/Browse",
        {"key": "LocalMusic:Search", "q": "adele"},
    )


async def test_search_rejects_an_empty_query(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """An empty search is refused before reaching the player."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/search",
            "entry_id": init_integration.entry_id,
            "key": "LocalMusic:Search",
            "query": "",
        }
    )
    assert (await client.receive_json())["success"] is False


async def test_search_skips_failing_categories(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A category the player cannot list does not hide the others, unless all fail."""
    respond(
        player_api,
        browse_url("Svc:Search"),
        text='<browse><item browseKey="ok" text="Albums" type="link"/><item browseKey="bad" text="Artists" type="link"/></browse>',
    )
    respond(
        player_api,
        browse_url("ok"),
        text='<browse><item browseKey="a" text="21" type="album"/></browse>',
    )
    respond(player_api, browse_url("bad"), status=500)
    client = await hass_ws_client(hass)
    request = {
        "type": "bluos_companion/search",
        "entry_id": init_integration.entry_id,
        "key": "Svc:Search",
        "query": "x",
    }

    await client.send_json_auto_id(request)
    groups = (await client.receive_json())["result"]["groups"]
    assert [group["title"] for group in groups] == ["Albums"]

    respond(player_api, browse_url("ok"), status=500)
    await client.send_json_auto_id(request)
    assert (await client.receive_json())["success"] is False


async def test_browse_root_hides_services(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Hidden services are left out of the root, but not of deeper levels."""
    respond(player_api, f"{BASE}/Browse", text=ROOT)
    hass.config_entries.async_update_entry(
        init_integration, options={"hidden_services": ["BluOS:"]}
    )
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {"type": "bluos_companion/browse", "entry_id": init_integration.entry_id}
    )
    root = (await client.receive_json())["result"]["items"]
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/browse",
            "entry_id": init_integration.entry_id,
            "key": "Any:",
        }
    )
    deeper = (await client.receive_json())["result"]["items"]

    assert [item["title"] for item in root] == ["Library", "Albums"]
    assert [item["title"] for item in deeper] == ["Playlists", "Library", "Albums"]


async def test_actions_only_allow_play_urls(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Play and queue actions are returned, favourites and others are not."""
    respond(
        player_api,
        browse_url("ctx"),
        text="""<browse type="contextMenu">
  <item actionURL="/AddFavourite?album=21" text="Favourite" type="favourite-add"></item>
  <item actionURL="/Add?album=21&amp;playnow=1" text="Play now" type="add-now"></item>
  <item actionURL="/Reboot" text="Reboot" type="add-last"></item>
  <item actionURL="/Add?album=21&amp;playnow=-1&amp;where=last" text="Add last" type="addAll-last"></item>
</browse>""",
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/actions",
            "entry_id": init_integration.entry_id,
            "key": "ctx",
        }
    )
    actions = (await client.receive_json())["result"]["actions"]
    assert [(action["type"], action["title"]) for action in actions] == [
        ("add-now", "Play now"),
        ("addAll-last", "Add last"),
    ]


async def test_browse_items_carry_the_context_key(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The panel can open the actions of an item."""
    respond(
        player_api,
        f"{BASE}/Browse",
        text='<browse><item browseKey="b" contextMenuKey="ctx" text="21" type="album"/></browse>',
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/browse", "entry_id": init_integration.entry_id, "key": "x"}
    )
    [item] = (await client.receive_json())["result"]["items"]
    assert item["context_key"] == "ctx"


async def test_queue_lists_tracks_with_covers(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """The queue gives the position of each track, with a signed cover."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/queue", "entry_id": init_integration.entry_id}
    )
    items = (await client.receive_json())["result"]["items"]
    assert [(item["position"], item["title"]) for item in items] == [
        (0, "U Got the Look"),
        (1, "Kiss"),
    ]
    assert items[0]["image"].startswith("/api/bluos_companion/")
    assert items[1]["image"] is None


@pytest.mark.parametrize(
    ("message", "path", "query"),
    [
        ({"action": "play", "position": 3}, "/Play", {"id": "3"}),
        ({"action": "remove", "position": 2}, "/Delete", {"id": "2"}),
        ({"action": "move", "position": 2, "to": 8}, "/Move", {"old": "2", "new": "8"}),
        ({"action": "clear"}, "/Clear", {}),
        ({"action": "save", "name": "  Dinner Music "}, "/Save", {"name": "Dinner Music"}),
    ],
)
async def test_queue_actions(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    message: dict[str, Any],
    path: str,
    query: dict[str, str],
) -> None:
    """Queue actions are translated into player commands."""
    player_api.get(f"{BASE}/Delete", text="<deleted>1</deleted>")
    player_api.get(f"{BASE}/Move", text="<moved/>")
    player_api.get(f"{BASE}/Save", text="<saved><entries>2</entries></saved>")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/queue_action",
            "entry_id": init_integration.entry_id,
            **message,
        }
    )
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [(path, query)]


@pytest.mark.parametrize(
    "message",
    [{"action": "remove"}, {"action": "move", "position": 1}, {"action": "save"}, {"action": "save", "name": " "}],
)
async def test_queue_action_needs_its_parameters(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    message: dict[str, Any],
) -> None:
    """Incomplete queue actions never reach the player."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/queue_action",
            "entry_id": init_integration.entry_id,
            **message,
        }
    )
    assert (await client.receive_json())["success"] is False
    assert calls(player_api) == []


async def test_snapshot_has_the_queue_position(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The panel knows which track of which queue is playing."""
    respond(
        player_api,
        f"{BASE}/Status",
        text=status_xml(song="4", pid="1491", prid="7"),
    )
    await init_integration.runtime_data.async_refresh()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/subscribe"})
    await client.receive_json()
    [player] = (await client.receive_json())["event"]["players"]
    assert (player["queue_id"], player["queue_position"]) == ("1491", 4)
    assert player["presets_id"] == "7"


async def test_locate_finds_the_album_and_the_artist(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The album is searched by title and matched on its (album) artist."""
    respond(
        player_api,
        browse_url("LocalMusic:Search"),
        text='<browse><item browseKey="albums-key" text="Albums" type="link"/></browse>',
    )
    respond(
        player_api,
        browse_url("albums-key"),
        text="""<browse>
  <item browseKey="other" contextMenuKey="cm-other" text="Hits" text2="Someone" type="album"/>
  <item browseKey="various" contextMenuKey="cm-various" text="Hits" text2="Various Artists" type="album"/>
  <item browseKey="longer" text="Hits 2" text2="Prince" type="album"/>
</browse>""",
    )
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/locate",
            "entry_id": init_integration.entry_id,
            "album": "Hits",
            "artist": "Meat Loaf & Co",
        }
    )
    result = (await client.receive_json())["result"]

    assert result["album"] == {
        "title": "Hits",
        "browse_key": "various",
        "context_key": "cm-various",
    }
    assert result["artist"]["browse_key"] == (
        "LocalMusic:MG/LocalMusic-Artist?artist=Meat+Loaf+%26+Co"
    )


async def test_locate_searches_a_word_of_the_title(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Punctuation in a title does not reach the player's search."""
    respond(player_api, browse_url("LocalMusic:Search"), text="<browse/>")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/locate",
            "entry_id": init_integration.entry_id,
            "album": "Recommence-moi",
        }
    )
    await client.receive_json()
    assert calls(player_api) == [
        ("/Browse", {"key": "LocalMusic:Search", "q": "Recommence"})
    ]


async def test_locate_without_a_match(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """An album missing from the library is reported as null."""
    respond(player_api, browse_url("LocalMusic:Search"), text="<browse/>")
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/locate",
            "entry_id": init_integration.entry_id,
            "album": "Nope",
        }
    )
    assert (await client.receive_json())["result"] == {"artist": None, "album": None}


async def test_presets_with_signed_images(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """The presets keep their order, with a usable image URL or none."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/presets", "entry_id": init_integration.entry_id}
    )
    presets = (await client.receive_json())["result"]["presets"]
    assert [(preset["id"], preset["name"]) for preset in presets] == [
        (1, "RTS La Première"),
        (2, "Rouge FM"),
        (3, "No image"),
    ]
    assert presets[0]["image"].startswith("/api/bluos_companion/")
    assert presets[1]["image"] == "https://cdn.example/s58290.png"
    assert presets[2]["image"] is None


async def test_control_selects_a_source(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Inputs are selected by name, an unknown one is refused."""
    player_api.get(f"{BASE}/Play", text="<ok/>")
    client = await hass_ws_client(hass)
    request = {
        "type": "bluos_companion/control",
        "entry_id": init_integration.entry_id,
        "action": "source",
    }

    await client.send_json_auto_id({**request, "value": "Bluetooth"})
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [("/Play", {"inputTypeIndex": "bluetooth-1"})]

    await client.send_json_auto_id({**request, "value": "Nope"})
    assert (await client.receive_json())["error"]["message"] == "Unknown source: Nope"
