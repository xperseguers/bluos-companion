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

from .conftest import BASE, browse_url, calls, respond

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
