"""Websocket API used by the sidebar panel."""

from __future__ import annotations

import asyncio
from urllib.parse import urlencode
from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations

from .api import SLEEP_OPTIONS, BluOSClient, BluOSError, Favourite, Node, sleep_bucket
from .const import CONF_HIDDEN_SERVICES, CONF_PORT, DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .covers import async_playlist_covers, async_preset_images, image_path
from .http import async_artwork_url
from .media_source import (
    async_get_titles,
    is_play_path,
    menu_label,
    node_can_expand,
)

CONTROLS: dict[str, Callable[[BluOSClient, Any, bool], Awaitable[None]]] = {
    "play": lambda client, _, __: client.async_play(),
    "pause": lambda client, _, __: client.async_pause(),
    "stop": lambda client, _, __: client.async_stop(),
    "next": lambda client, _, __: client.async_skip(),
    "previous": lambda client, _, __: client.async_back(),
    "seek": lambda client, value, _: client.async_seek(int(value)),
    "volume": lambda client, value, _: client.async_set_volume(
        min(max(int(value), 0), 100)
    ),
    "volume_step": lambda client, value, group: client.async_step_volume(
        min(max(int(value), -10), 10), group
    ),
    "mute": lambda client, value, group: client.async_set_mute(bool(value), group),
    "sleep": lambda client, value, _: client.async_set_sleep(
        int(value) if int(value) in (0, *SLEEP_OPTIONS) else 0
    ),
    "shuffle": lambda client, value, _: client.async_set_shuffle(bool(value)),
    "repeat": lambda client, value, _: client.async_set_repeat(int(value)),
}


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket commands."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_favourite)
    websocket_api.async_register_command(hass, ws_control)
    websocket_api.async_register_command(hass, ws_browse)
    websocket_api.async_register_command(hass, ws_search)
    websocket_api.async_register_command(hass, ws_actions)
    websocket_api.async_register_command(hass, ws_group)
    websocket_api.async_register_command(hass, ws_translations)
    websocket_api.async_register_command(hass, ws_playlist_covers)
    websocket_api.async_register_command(hass, ws_move)
    websocket_api.async_register_command(hass, ws_group_volumes)
    websocket_api.async_register_command(hass, ws_home)
    websocket_api.async_register_command(hass, ws_locate)
    websocket_api.async_register_command(hass, ws_presets)
    websocket_api.async_register_command(hass, ws_queue)
    websocket_api.async_register_command(hass, ws_queue_action)
    websocket_api.async_register_command(hass, ws_play)


def _coordinator(hass: HomeAssistant, entry_id: str) -> BluOSCoordinator:
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
    ):
        raise HomeAssistantError("Unknown player")
    return entry.runtime_data


async def _async_call(call: Awaitable[Any]) -> Any:
    try:
        return await call
    except BluOSError as err:
        raise HomeAssistantError(f"BluOS player error: {err}") from err


def _snapshot(
    hass: HomeAssistant, entry: BluOSConfigEntry, entry_ids: dict[str, str]
) -> dict[str, Any]:
    """Return the state of a player as the panel needs it (image is not signed yet)."""
    coordinator = entry.runtime_data
    status = coordinator.data
    sync = coordinator.sync
    return {
        "entry_id": entry.entry_id,
        "entity_id": er.async_get(hass).async_get_entity_id(
            "media_player", DOMAIN, entry.unique_id
        ),
        "name": entry.title,
        "configuration_url": f"http://{entry.data[CONF_HOST]}",
        "available": coordinator.last_update_success,
        "state": status.state,
        "title": status.title,
        "artist": status.artist,
        "album": status.album,
        "service": status.service,
        "image": status.image,
        "volume": coordinator.volume_level,
        "muted": coordinator.is_muted,
        "shuffle": status.shuffle,
        "repeat": status.repeat,
        "can_seek": status.can_seek,
        "position": status.position,
        "duration": status.duration,
        "sleep": sleep_bucket(status.sleep),
        "sleep_options": list(SLEEP_OPTIONS),
        "queue_id": status.queue_id,
        "queue_position": status.queue_position,
        "can_move": status.can_move,
        "presets_id": status.presets_id,
        "stream_url": status.stream_url,
        "preset_name": status.preset_name,
        "max_volume": coordinator.max_volume,
        # None for a player that is not built into an amplifier we can switch
        "power": coordinator.amplifier.data.power if coordinator.amplifier else None,
        "sources": coordinator.source_names,
        "source": coordinator.active_source,
        "group": {
            "name": sync.group if sync else None,
            "master": sync and sync.master and entry_ids.get(sync.master.host),
            "slaves": [
                entry_ids[member.host]
                for member in (sync.slaves if sync else ())
                if member.host in entry_ids
            ],
        },
    }


def _items(
    hass: HomeAssistant, entry_id: str, nodes: list[Node], titles: dict[str, str]
) -> list[dict[str, Any]]:
    """Return the entries the panel can open or play."""
    items = []
    for node in nodes:
        can_play = bool(node.play_path and is_play_path(node.play_path))
        can_expand = node_can_expand(node)
        if not (can_play or can_expand):
            continue
        title, icon = menu_label(node, titles)
        image = icon
        if image is None and (path := image_path(node)):
            image = async_artwork_url(hass, entry_id, path)
        items.append(
            {
                "type": node.type,
                "title": title,
                "subtitle": node.subtitle,
                "image": image,
                "browse_key": node.browse_key if can_expand else None,
                "play_path": node.play_path if can_play else None,
                "context_key": node.context_key,
            }
        )
    return items


def _snapshots(hass: HomeAssistant) -> list[dict[str, Any]]:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    entry_ids = {entry.data[CONF_HOST]: entry.entry_id for entry in entries}
    return [_snapshot(hass, entry, entry_ids) for entry in entries]


@websocket_api.websocket_command({vol.Required("type"): "bluos_companion/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Push the state of all players on every change."""
    last: list[dict[str, Any]] | None = None

    @callback
    def publish() -> None:
        nonlocal last
        players = _snapshots(hass)
        if players == last:
            return
        last = players
        connection.send_message(
            websocket_api.event_message(
                msg["id"],
                {
                    "players": [
                        {
                            **player,
                            "image": player["image"]
                            and async_artwork_url(
                                hass, player["entry_id"], player["image"]
                            ),
                        }
                        for player in players
                    ]
                },
            )
        )

    unsubscribes: list[CALLBACK_TYPE] = [
        coordinator.async_add_listener(publish)
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        for coordinator in (entry.runtime_data, entry.runtime_data.amplifier)
        if coordinator is not None
    ]

    @callback
    def unsubscribe() -> None:
        for remove in unsubscribes:
            remove()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    publish()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/control",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In([*CONTROLS, "source", "power"]),
        vol.Optional("value"): vol.Any(bool, int, str),
        vol.Optional("group"): bool,
    }
)
@websocket_api.async_response
async def ws_control(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send a transport, volume or mode command to a player."""
    coordinator = _coordinator(hass, msg["entry_id"])
    value = msg.get("value", 0)
    if msg["action"] == "volume":
        msg = {**msg, "value": min(int(value), coordinator.max_volume)}
    elif (
        msg["action"] == "volume_step"
        and int(value) > 0
        and coordinator.max_volume < 100
    ):
        own, _ = await _async_call(coordinator.client.async_get_volume())
        if own >= coordinator.max_volume:
            connection.send_result(msg["id"])
            return
    if msg["action"] == "source":
        await _async_call(coordinator.async_select_source(str(msg.get("value", ""))))
    elif msg["action"] == "power":
        if coordinator.amplifier is None:
            raise HomeAssistantError("This player has no amplifier to switch")
        await coordinator.amplifier.async_set("power", bool(value))
    else:
        await _async_call(
            CONTROLS[msg["action"]](
                coordinator.client, msg.get("value", 0), msg.get("group", False)
            )
        )
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/browse",
        vol.Required("entry_id"): str,
        vol.Optional("key"): str,
    }
)
@websocket_api.async_response
async def ws_browse(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List the entries below a browse key (the sources if there is no key)."""
    coordinator = _coordinator(hass, msg["entry_id"])
    page = await _async_call(coordinator.client.async_browse_page(msg.get("key")))
    titles = await async_get_titles(hass)
    nodes = page.nodes
    if "key" not in msg:
        hidden = coordinator.config_entry.options.get(CONF_HIDDEN_SERVICES, [])
        nodes = [node for node in nodes if node.browse_key not in hidden]
    connection.send_result(
        msg["id"],
        {
            "items": _items(hass, msg["entry_id"], nodes, titles),
            "search_key": page.search_key,
            "next_key": page.next_key,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/search",
        vol.Required("entry_id"): str,
        vol.Required("key"): str,
        vol.Required("query"): vol.All(str, vol.Length(min=1, max=100)),
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Search a source and return the first results of each category."""
    entry_id = msg["entry_id"]
    client = _coordinator(hass, entry_id).client
    menu = await _async_call(client.async_browse_page(msg["key"], msg["query"], 1))
    categories = [node for node in menu.nodes if node.browse_key]
    pages = await asyncio.gather(
        *(client.async_browse_page(node.browse_key, None, 1) for node in categories),
        return_exceptions=True,
    )
    errors = [page for page in pages if isinstance(page, BluOSError)]
    if errors and len(errors) == len(pages):
        raise HomeAssistantError(f"BluOS player error: {errors[0]}")
    titles = await async_get_titles(hass)
    groups = []
    for node, page in zip(categories, pages, strict=True):
        if isinstance(page, BluOSError):
            continue
        if items := _items(hass, entry_id, page.nodes, titles):
            groups.append(
                {"title": menu_label(node, titles)[0], "type": node.title, "items": items}
            )
    connection.send_result(msg["id"], {"groups": groups})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/actions",
        vol.Required("entry_id"): str,
        vol.Required("key"): str,
    }
)
@websocket_api.async_response
async def ws_actions(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """List what can be done with an item: play now, shuffle, add next / last."""
    client = _coordinator(hass, msg["entry_id"]).client
    actions = await _async_call(client.async_get_actions(msg["key"]))
    result: list[dict[str, Any]] = [
        {"type": action.type, "title": action.title, "path": action.path}
        for action in actions
        if is_play_path(action.path)
    ]
    # The player offers to add the item as a favourite: offer the one that fits what it is now
    favourite = next(
        (
            found
            for action in actions
            if action.type == "favourite-add" and (found := Favourite.from_path(action.path))
        ),
        None,
    )
    if favourite is not None:
        try:
            on = favourite in await client.async_get_favourites()
        except BluOSError:
            pass
        else:
            result.append(
                {
                    "type": "favourite",
                    "title": "",
                    "favourite": {
                        "kind": favourite.kind,
                        "artist": favourite.artist,
                        "album": favourite.album,
                        "file": favourite.file,
                    },
                    "on": on,
                }
            )
    connection.send_result(msg["id"], {"actions": result})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/favourite",
        vol.Required("entry_id"): str,
        vol.Required("kind"): vol.In(["album", "artist", "song"]),
        vol.Optional("artist", default=""): str,
        vol.Optional("album", default=""): str,
        vol.Optional("file", default=""): str,
        vol.Required("on"): bool,
    }
)
@websocket_api.async_response
async def ws_favourite(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Make an album, an artist or a song of the library a favourite, or not any more."""
    favourite = Favourite(msg["kind"], msg["artist"], msg["album"], msg["file"])
    if not (
        (favourite.kind == "album" and favourite.artist and favourite.album)
        or (favourite.kind == "artist" and favourite.artist)
        or (favourite.kind == "song" and favourite.file)
    ):
        raise HomeAssistantError("Say which album, artist or song")
    client = _coordinator(hass, msg["entry_id"]).client
    await _async_call(client.async_set_favourite(favourite, msg["on"]))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/locate",
        vol.Required("entry_id"): str,
        vol.Optional("album"): str,
        vol.Optional("artist"): str,
    }
)
@websocket_api.async_response
async def ws_locate(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Find the library pages of the album and of the artist of a track."""
    client = _coordinator(hass, msg["entry_id"]).client
    artist, album = msg.get("artist"), msg.get("album")
    result: dict[str, Any] = {"artist": None, "album": None}
    if artist:
        query = urlencode({"artist": artist})
        result["artist"] = {
            "title": artist,
            "browse_key": f"LocalMusic:MG/LocalMusic-Artist?{query}",
            "context_key": f"LocalMusic:CM/LocalMusic-Artist?{query}",
        }
    if album and (node := await _async_call(client.async_find_album(album, artist))):
        result["album"] = {
            "title": node.title,
            "browse_key": node.browse_key,
            "context_key": node.context_key,
        }
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): "bluos_companion/presets", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_presets(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the presets (radio stations...) of a player."""
    coordinator = _coordinator(hass, msg["entry_id"])
    presets = await _async_call(coordinator.client.async_get_presets())
    images = await async_preset_images(coordinator, presets)
    connection.send_result(
        msg["id"],
        {
            "presets": [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "url": preset.url,
                    "image": images[preset.id]
                    and async_artwork_url(hass, msg["entry_id"], images[preset.id]),
                }
                for preset in presets
            ]
        },
    )


HOME_ALBUMS = 12
PANEL_PREFIX = f"component.{DOMAIN}.common.panel_"


@websocket_api.websocket_command(
    {vol.Required("type"): "bluos_companion/translations", vol.Optional("language"): str}
)
@websocket_api.async_response
async def ws_translations(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the texts of the panel and the cards in a language (English if unknown)."""
    language = (msg.get("language") or hass.config.language).split("-")[0]
    translations = await async_get_translations(hass, language, "common", [DOMAIN])
    connection.send_result(
        msg["id"],
        {
            "strings": {
                key.removeprefix(PANEL_PREFIX): text
                for key, text in translations.items()
                if key.startswith(PANEL_PREFIX)
            }
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/playlist_covers",
        vol.Required("entry_id"): str,
        vol.Required("keys"): vol.All([str], vol.Length(max=50)),
    }
)
@websocket_api.async_response
async def ws_playlist_covers(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the cover of saved playlists: the one of their first track.

    The first tracks of an old playlist may be missing, so this can take a few
    requests, and the result is kept for a while.
    """
    entry_id = msg["entry_id"]
    covers = await async_playlist_covers(_coordinator(hass, entry_id), msg["keys"])
    connection.send_result(
        msg["id"],
        {
            "covers": {
                key: path and async_artwork_url(hass, entry_id, path)
                for key, path in covers.items()
            }
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "bluos_companion/home", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_home(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the start page: the presets, the recent albums and the sources."""
    entry_id = msg["entry_id"]
    coordinator = _coordinator(hass, entry_id)
    client = coordinator.client
    page, presets, albums, recents, saved, library = await asyncio.gather(
        client.async_browse_page(None),
        client.async_get_presets(),
        client.async_get_recent_albums(),
        client.async_get_home(hass.config.language),
        client.async_browse_page("BluOS:", None, 1),
        client.async_browse_page("LocalMusic:", None, 1),
        return_exceptions=True,
    )
    if isinstance(page, BluOSError):
        raise HomeAssistantError(f"BluOS player error: {page}")
    titles = await async_get_titles(hass)
    hidden = coordinator.config_entry.options.get(CONF_HIDDEN_SERVICES, [])
    groups = []
    images = {}
    if not isinstance(presets, BluOSError) and presets:
        images = await async_preset_images(coordinator, presets)
        groups.append(
            {
                "title": titles["presets"],
                "items": [
                    {
                        "type": "preset",
                        "title": preset.name,
                        "subtitle": "",
                        "image": images[preset.id]
                        and async_artwork_url(hass, entry_id, images[preset.id]),
                        "browse_key": None,
                        "play_path": f"/Preset?id={preset.id}",
                        "context_key": None,
                    }
                    for preset in presets
                ],
            }
        )
    playlists = (
        []
        if isinstance(saved, BluOSError) or "BluOS:" in hidden
        else [node for node in saved.nodes if node.type == "playlist"]
    )
    if playlists:
        # Their covers are asked for after the page is shown, see playlist_covers.
        groups.append(
            {
                "title": titles["playlists"],
                "items": _items(hass, entry_id, playlists, titles),
            }
        )
    # The entries of the library (artists, albums...) one tap from the start page; the
    # saved playlists have their own row.
    entries = (
        []
        if isinstance(library, BluOSError) or "LocalMusic:" in hidden
        else [node for node in library.nodes if node.type == "link" and node.title != "Playlists"]
    )
    if entries:
        groups.append(
            {"title": titles["library"], "items": _items(hass, entry_id, entries, titles)}
        )
    if not isinstance(recents, BluOSError):
        # Titled by the player, in the language of Home Assistant.
        rows = {row.id: row for row in recents}
        for row_id in ("recent", "recent-stations", "mostUsed"):
            if row := rows.get(row_id):
                groups.append(
                    {
                        "title": row.title,
                        "items": [
                            {
                                "type": item.kind,
                                "title": item.title,
                                "subtitle": item.subtitle,
                                "image": item.image
                                and async_artwork_url(hass, entry_id, item.image),
                                "browse_key": item.browse_key,
                                "play_path": item.play_path,
                                "context_key": item.context_key,
                            }
                            for item in row.items
                            if is_play_path(item.play_path)
                        ],
                    }
                )
    if not isinstance(albums, BluOSError) and albums:
        groups.append(
            {
                "title": titles["recently_added"],
                "items": [
                    {
                        "type": "album",
                        "title": album.title,
                        "subtitle": album.artist,
                        "image": async_artwork_url(hass, entry_id, album.image),
                        "browse_key": album.browse_key,
                        "play_path": album.play_path,
                        "context_key": album.context_key,
                    }
                    for album in albums[:HOME_ALBUMS]
                ],
            }
        )
    nodes = [node for node in page.nodes if node.browse_key not in hidden]
    groups.append(
        {"title": titles["sources"], "items": _items(hass, entry_id, nodes, titles)}
    )
    connection.send_result(msg["id"], {"groups": groups, "search_key": page.search_key})


def _coordinator_of_host(hass: HomeAssistant, host: str) -> BluOSCoordinator | None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if entry.data[CONF_HOST] == host:
            return entry.runtime_data
    return None


def _address(coordinator: BluOSCoordinator) -> tuple[str, int]:
    data = coordinator.config_entry.data
    return data[CONF_HOST], data[CONF_PORT]


def _primary(hass: HomeAssistant, coordinator: BluOSCoordinator) -> BluOSCoordinator:
    """Return the player that leads the group of a player (itself if it leads or is alone)."""
    sync = coordinator.sync
    if sync is None or sync.master is None:
        return coordinator
    if (primary := _coordinator_of_host(hass, sync.master.host)) is None:
        raise HomeAssistantError("The primary player of the group is not configured")
    return primary


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/move",
        vol.Required("entry_id"): str,
        vol.Required("target"): str,
    }
)
@websocket_api.async_response
async def ws_move(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Move what a player plays to another player."""
    source = _coordinator(hass, msg["entry_id"])
    target = _coordinator(hass, msg["target"])
    if source is target:
        raise HomeAssistantError("The player is already the target")
    if not source.data.can_move:
        raise HomeAssistantError("This player cannot move its playback")
    if source.data.state == "stop":
        raise HomeAssistantError("Nothing to move, the player is stopped")
    host, port = _address(target)
    await _async_call(source.client.async_move_playback(host, port))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): "bluos_companion/group_volumes", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_group_volumes(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the own volume of each player of the group of a player.

    The volume of a secondary player in /Status is the one of the group, so each
    player is asked for its own.
    """
    primary = _primary(hass, _coordinator(hass, msg["entry_id"]))
    members = [primary]
    for member in primary.sync.slaves if primary.sync else ():
        if (coordinator := _coordinator_of_host(hass, member.host)) is not None:
            members.append(coordinator)
    results = await asyncio.gather(
        *(member.client.async_get_volume() for member in members),
        return_exceptions=True,
    )
    connection.send_result(
        msg["id"],
        {
            "volumes": [
                {
                    "entry_id": member.config_entry.entry_id,
                    "volume": result[0],
                    "muted": result[1],
                    "max_volume": member.max_volume,
                }
                for member, result in zip(members, results, strict=True)
                if not isinstance(result, BluOSError)
            ]
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/group",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In(["join", "leave"]),
        vol.Optional("target"): str,
    }
)
@websocket_api.async_response
async def ws_group(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add a player to the group of another one, or take it out of its group.

    Only the primary player of a group can add or remove players. A primary player
    that leaves dissolves its group.
    """
    coordinator = _coordinator(hass, msg["entry_id"])
    host, port = _address(coordinator)
    sync = coordinator.sync
    if msg["action"] == "leave":
        if sync is not None and sync.master is not None:
            primary = _primary(hass, coordinator)
            await _async_call(primary.client.async_remove_slave(host, port))
        elif sync is not None:
            for member in sync.slaves:
                await _async_call(
                    coordinator.client.async_remove_slave(member.host, member.port)
                )
    else:
        if "target" not in msg:
            raise HomeAssistantError("Missing target")
        primary = _primary(hass, _coordinator(hass, msg["target"]))
        coordinator.ensure_can_group()
        primary.ensure_can_group()
        if primary is not coordinator:
            if sync is not None and sync.slaves:
                raise HomeAssistantError("This player leads a group, ungroup it first")
            if sync is not None and sync.master is not None:
                if (old := _primary(hass, coordinator)) is primary:
                    connection.send_result(msg["id"])
                    return
                await _async_call(old.client.async_remove_slave(host, port))
            await _async_call(primary.client.async_add_slave(host, port))
    connection.send_result(msg["id"])


QUEUE_ACTIONS: dict[str, Callable[[BluOSClient, dict[str, Any]], Awaitable[None]]] = {
    "play": lambda client, msg: client.async_play_queue_item(msg["position"]),
    "remove": lambda client, msg: client.async_delete_queue_item(msg["position"]),
    "move": lambda client, msg: client.async_move_queue_item(
        msg["position"], msg["to"]
    ),
    "clear": lambda client, msg: client.async_clear_queue(),
    "save": lambda client, msg: client.async_save_queue(msg["name"]),
}


@websocket_api.websocket_command(
    {vol.Required("type"): "bluos_companion/queue", vol.Required("entry_id"): str}
)
@websocket_api.async_response
async def ws_queue(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Return the tracks of the play queue."""
    client = _coordinator(hass, msg["entry_id"]).client
    queue = await _async_call(client.async_get_queue())
    connection.send_result(
        msg["id"],
        {
            "items": [
                {
                    "position": item.id,
                    "title": item.title,
                    "artist": item.artist,
                    "album": item.album,
                    "image": item.image
                    and async_artwork_url(hass, msg["entry_id"], item.image),
                }
                for item in queue
            ]
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/queue_action",
        vol.Required("entry_id"): str,
        vol.Required("action"): vol.In(QUEUE_ACTIONS),
        vol.Optional("position"): vol.All(int, vol.Range(min=0)),
        vol.Optional("to"): vol.All(int, vol.Range(min=0)),
        vol.Optional("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=100)),
    }
)
@websocket_api.async_response
async def ws_queue_action(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Play, remove or move a track of the queue, clear it or save it as a playlist."""
    needed = {"play": ("position",), "remove": ("position",), "move": ("position", "to"), "save": ("name",)}
    if missing := [key for key in needed.get(msg["action"], ()) if key not in msg]:
        raise HomeAssistantError(f"Missing {', '.join(missing)}")
    client = _coordinator(hass, msg["entry_id"]).client
    await _async_call(QUEUE_ACTIONS[msg["action"]](client, msg))
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {
        vol.Required("type"): "bluos_companion/play",
        vol.Required("entry_id"): str,
        vol.Required("path"): str,
    }
)
@websocket_api.async_response
async def ws_play(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Play an item of the browse tree."""
    if not is_play_path(msg["path"]):
        raise HomeAssistantError("This item cannot be played")
    client = _coordinator(hass, msg["entry_id"]).client
    await _async_call(client.async_command(msg["path"]))
    connection.send_result(msg["id"])
