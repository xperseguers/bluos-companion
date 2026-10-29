"""Minimal client for the BluOS player HTTP API."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientSession, ClientTimeout

REQUEST_TIMEOUT = 20
MAX_BROWSE_PAGES = 8
MAX_EMPTY_BROWSE_PAGES = 60
PLAYLIST_BATCH = 10
PLAYLIST_EMPTY_WINDOWS = 60
PLAYLIST_LEADING_WINDOWS = 120
HOME_ROWS = ("mostUsed", "recent-stations", "recent")
UI_HEADERS = {"x-sovi-schema-version": "35", "x-sovi-ui-schema-version": "7"}
MAX_QUEUE_LENGTH = 500
SLEEP_OPTIONS = (15, 30, 45, 60, 90)


class BluOSError(Exception):
    """Raised when the player cannot be reached or answers unexpectedly."""


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    """Identity of a BluOS player."""

    name: str
    mac: str
    model: str
    brand: str


@dataclass(frozen=True, slots=True)
class Status:
    """Playback status of a player."""

    etag: str | None
    state: str
    title: str | None
    artist: str | None
    album: str | None
    service: str | None
    image: str | None
    volume: int
    muted: bool
    shuffle: bool
    repeat: int
    can_seek: bool
    position: int | None
    duration: int | None
    sync_stat: str | None = None
    sleep: int | None = None
    stream_url: str | None = None
    queue_id: str | None = None
    queue_position: int | None = None
    presets_id: str | None = None
    preset_name: str | None = None
    can_move: bool = False


@dataclass(frozen=True, slots=True)
class Member:
    """A player grouped with another one, as listed by /SyncStatus."""

    host: str
    port: int
    name: str


@dataclass(frozen=True, slots=True)
class Source:
    """An input of the player (Bluetooth, optical...), selected by its type and index."""

    name: str
    type_index: str
    url: str


@dataclass(frozen=True, slots=True)
class ExternalSource:
    """An input of an amplifier (TV, Phono...), selected by its id."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class SyncStatus:
    """Group and input information of a player."""

    group: str | None
    master: Member | None
    slaves: tuple[Member, ...]
    external_source: str | None
    external_sources: tuple[ExternalSource, ...] = ()

    @property
    def is_grouped(self) -> bool:
        """Return whether the player is part of a group."""
        return self.master is not None or bool(self.slaves)


@dataclass(frozen=True, slots=True)
class QueueItem:
    """A track of the play queue."""

    id: int
    title: str
    artist: str
    album: str
    image: str | None


@dataclass(frozen=True, slots=True)
class Node:
    """An entry of the BluOS browse hierarchy (section, artist, album, track...)."""

    type: str
    title: str
    subtitle: str
    browse_key: str | None
    play_path: str | None
    image: str | None
    context_key: str | None = None


@dataclass(frozen=True, slots=True)
class Action:
    """An action of an item's context menu, e.g. add it to the end of the queue."""

    type: str
    title: str
    path: str


@dataclass(frozen=True, slots=True)
class BrowsePage:
    """The entries of a browse level and the key to search within its source."""

    nodes: list[Node]
    search_key: str | None
    next_key: str | None = None


@dataclass(frozen=True, slots=True)
class Album:
    """An album of the local library, identified by its URL-encoded query."""

    title: str
    artist: str
    query: str

    @classmethod
    def from_names(cls, title: str, artist: str) -> Album:
        """Build an album from its title and artist."""
        return cls(title, artist, urlencode({"album": title, "artist": artist}))

    @property
    def browse_key(self) -> str:
        """Key to list the tracks of the album."""
        return f"LocalMusic:MG/LocalMusic-Album?{self.query}"

    @property
    def context_key(self) -> str:
        """Key to list the actions (play now, add next...) of the album."""
        return f"LocalMusic:CM/LocalMusic-Album?{self.query}"

    @property
    def image(self) -> str:
        """Player path of the cover."""
        return f"/Artwork?service=LocalMusic&{self.query}"

    @property
    def play_path(self) -> str:
        """Player path starting the album."""
        return f"/Add?playnow=1&service=LocalMusic&{self.query}"


@dataclass(frozen=True, slots=True)
class PlaylistTrack:
    """A track of a playlist saved on the player, identified by its file on the music share."""

    title: str
    artist: str
    album: str
    duration: int | None
    path: str


@dataclass(frozen=True, slots=True)
class HomeItem:
    """An album, song or station of the home screen of the player."""

    kind: str
    title: str
    subtitle: str
    image: str | None
    browse_key: str | None
    play_path: str
    context_key: str | None


@dataclass(frozen=True, slots=True)
class HomeRow:
    """A row of the home screen of the player, titled in the language asked."""

    id: str
    title: str
    items: list[HomeItem]


@dataclass(frozen=True, slots=True)
class Track:
    """A track of an album."""

    title: str
    artist: str
    duration: int | None
    play_path: str
    image: str | None


@dataclass(frozen=True, slots=True)
class Preset:
    """A preset of the player."""

    id: int
    name: str
    image: str | None
    url: str = ""


def _ui_query(uri: str, name: str) -> str | None:
    """Return a parameter of a URI of the player's screens (already decoded once)."""
    values = parse_qs(urlparse(uri).query).get(name)
    return values[0] if values else None


def _home_item(element: ET.Element) -> HomeItem | None:
    """Turn an item of the home screen into an album, a song or a station."""
    play = element.find("playAction")
    actions = element.findall("action")
    play_uri = (play if play is not None else next(iter(actions), None))
    play_path = _ui_query(play_uri.get("URI", ""), "u") if play_uri is not None else None
    title = unquote(element.get("title", ""))
    if not title:
        return None
    browse = next((a for a in actions if a.get("type") == "browse"), None)
    target = _ui_query(browse.get("URI", ""), "url") if browse is not None else None
    query = parse_qs(urlparse(target).query) if target else {}
    if element.get("objectType") == "album" and query.get("service") == ["LocalMusic"]:
        if query.get("album") and query.get("artist"):
            album = Album.from_names(query["album"][0], query["artist"][0])
            return HomeItem(
                "album",
                album.title,
                album.artist,
                album.image,
                album.browse_key,
                album.play_path,
                album.context_key,
            )
        return None
    if not play_path:
        return None
    if element.get("objectType") == "song":
        context = element.find("contextMenu")
        params = parse_qs(urlparse(context.get("URI", "")).query) if context is not None else {}
        context_key = None
        if params.get("filename"):
            wanted = {k: params[k][0] for k in ("album", "artist", "filename", "title") if k in params}
            context_key = f"LocalMusic:CM/LocalMusic-Song?{urlencode(wanted)}"
        return HomeItem(
            "song", title, element.get("subTitle", ""), element.get("image"), None, play_path, context_key
        )
    if play_path.startswith("/Play?url="):
        return HomeItem("station", title, "", element.get("image"), None, play_path, None)
    return None


def _int(value: str | None, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


class BluOSClient:
    """Talk to a single BluOS player over plain HTTP."""

    def __init__(self, session: ClientSession, host: str, port: int) -> None:
        """Initialize the client."""
        self._session = session
        self.base_url = f"http://{host}:{port}"

    async def _get(
        self,
        path: str,
        params: dict[str, str] | None = None,
        timeout: float = REQUEST_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        try:
            async with self._session.get(
                f"{self.base_url}{path}",
                params=params,
                headers=headers,
                timeout=ClientTimeout(total=timeout),
            ) as response:
                response.raise_for_status()
                return await response.read()
        except (ClientError, TimeoutError) as err:
            raise BluOSError(str(err)) from err

    async def _get_xml(
        self,
        path: str,
        params: dict[str, str] | None = None,
        timeout: float = REQUEST_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> ET.Element:
        body = await self._get(path, params, timeout, headers)
        try:
            root = ET.fromstring(body)  # noqa: S314
        except ET.ParseError as err:
            raise BluOSError("Invalid response from player") from err
        if root.tag == "error":
            raise BluOSError(root.findtext("message") or "Player returned an error")
        return root

    async def async_get_player_info(self) -> PlayerInfo:
        """Return the identity of the player."""
        root = await self._get_xml("/SyncStatus")
        if (mac := root.get("mac")) is None:
            raise BluOSError("Not a BluOS player")
        return PlayerInfo(
            name=root.get("name", mac),
            mac=mac,
            model=root.get("modelName", ""),
            brand=root.get("brand", ""),
        )

    async def async_get_sync_status(self) -> SyncStatus:
        """Return the group and external source of the player."""
        root = await self._get_xml("/SyncStatus")
        master = root.find("master")
        external = root.find("externalSource")
        return SyncStatus(
            group=root.get("group"),
            master=(
                Member(
                    (master.text or "").strip(),
                    _int(master.get("port"), 11000),
                    master.get("name", ""),
                )
                if master is not None and (master.text or "").strip()
                else None
            ),
            slaves=tuple(
                Member(slave.get("id", ""), _int(slave.get("port"), 11000), slave.get("name", ""))
                for slave in root.findall("slave")
            ),
            external_source=external.get("name") if external is not None else None,
            external_sources=tuple(
                ExternalSource(item.get("id", ""), item.get("name", ""))
                for item in (external.findall("item") if external is not None else [])
                if item.get("id")
            ),
        )

    async def async_get_status(
        self, etag: str | None = None, long_poll_timeout: int | None = None
    ) -> Status:
        """Return the playback status, optionally waiting for a change."""
        params: dict[str, str] = {}
        timeout: float = REQUEST_TIMEOUT
        if etag is not None and long_poll_timeout is not None:
            params = {"timeout": str(long_poll_timeout), "etag": etag}
            timeout = long_poll_timeout + REQUEST_TIMEOUT
        root = await self._get_xml("/Status", params, timeout)
        position = root.findtext("secs")
        duration = root.findtext("totlen")
        return Status(
            etag=root.get("etag"),
            state=root.findtext("state", "stop"),
            title=root.findtext("title1") or root.findtext("name"),
            artist=root.findtext("artist"),
            album=root.findtext("album"),
            service=root.findtext("service"),
            image=root.findtext("image"),
            volume=_int(root.findtext("volume"), -1),
            muted=root.findtext("mute") == "1",
            shuffle=root.findtext("shuffle") == "1",
            repeat=_int(root.findtext("repeat"), 2),
            can_seek=root.findtext("canSeek") == "1",
            position=_int(position) if position else None,
            duration=_int(duration) if duration else None,
            sync_stat=root.findtext("syncStat"),
            sleep=_int(root.findtext("sleep")) or None,
            stream_url=root.findtext("streamUrl"),
            queue_id=root.findtext("pid"),
            presets_id=root.findtext("prid"),
            preset_name=root.findtext("preset_name"),
            can_move=root.findtext("canMovePlayback") == "true",
            queue_position=(
                _int(song) if (song := root.findtext("song")) is not None else None
            ),
        )

    async def async_browse(self, key: str | None) -> list[Node]:
        """Return all entries below a browse key (the root of all sources if None)."""
        return (await self.async_browse_page(key)).nodes

    async def async_browse_page(
        self,
        key: str | None,
        query: str | None = None,
        max_pages: int = MAX_BROWSE_PAGES,
    ) -> BrowsePage:
        """Return the entries below a browse key, or the results of a search.

        Long listings are split in pages. The player may repeat earlier entries
        in later pages, so entries are merged in order of first appearance.
        With a query, the key is the searchKey of a source.
        """
        nodes: dict[Node, None] = {}
        search_key: str | None = None
        next_key: str | None = key
        first = True
        useful_pages = 0
        # Pages without entries are skipped: the player answers an empty first page
        # for a saved playlist, and more for the entries it cannot find any more.
        for _ in range(max_pages + MAX_EMPTY_BROWSE_PAGES):
            params = {"key": next_key} if next_key else {}
            if query is not None and first:
                params["q"] = query
            root = await self._get_xml("/Browse", params or None)
            if first:
                search_key = root.get("searchKey")
                first = False
            found = False
            for item in root.iter("item"):
                found = True
                node = Node(
                    type=item.get("type", ""),
                    title=item.get("text", ""),
                    subtitle=item.get("text2", ""),
                    browse_key=item.get("browseKey"),
                    play_path=item.get("autoplayURL") or item.get("playURL"),
                    image=item.get("image"),
                    context_key=item.get("contextMenuKey"),
                )
                nodes.setdefault(node, None)
            useful_pages += found
            if not (next_key := root.get("nextKey")) or useful_pages >= max_pages:
                break
        return BrowsePage(list(nodes), search_key, next_key)

    async def async_find_album(self, title: str, artist: str | None) -> Node | None:
        """Find an album of the library by its title.

        The album key needs the album artist, which differs from the track artist
        on compilations, so the album is searched and the best match is returned.
        """
        # The player's search chokes on punctuation (it finds nothing for "A-B"), so
        # search the longest word and match the exact title afterwards.
        query = max(re.findall(r"\w+", title), key=len, default=title)
        menu = await self.async_browse_page("LocalMusic:Search", query, 1)
        category = next((node for node in menu.nodes if node.title == "Albums"), None)
        if category is None or category.browse_key is None:
            return None
        albums = [
            node
            for node in (await self.async_browse_page(category.browse_key, None, 1)).nodes
            if node.type == "album" and node.browse_key and node.title == title
        ]
        for wanted in (artist, "Various Artists"):
            for node in albums:
                if node.subtitle == wanted:
                    return node
        return albums[0] if albums else None

    async def async_get_actions(self, context_key: str) -> list[Action]:
        """Return the actions (play now, shuffle, add next...) of an item."""
        root = await self._get_xml("/Browse", {"key": context_key})
        return [
            Action(item.get("type", ""), item.get("text", ""), item.get("actionURL", ""))
            for item in root.iter("item")
            if item.get("actionURL")
        ]

    async def async_get_playlist_names(self) -> list[str]:
        """Return the names of the playlists saved on the player."""
        root = await self._get_xml("/Playlists", {"service": "BluOS"})
        return [name.text for name in root.iter("name") if name.text]

    async def _async_playlist_window(self, name: str, end: int) -> list[PlaylistTrack]:
        """Return the (at most 10) tracks of a playlist ending at an offset."""
        root = await self._get_xml("/Songs", {"playlist": name, "offset": str(end)})
        return [
            PlaylistTrack(
                title=song.findtext("title", ""),
                artist=song.findtext("art", ""),
                album=song.findtext("alb", ""),
                duration=_int(song.findtext("time")) or None,
                path=song.findtext("fn", ""),
            )
            for song in root.iter("song")
            if song.findtext("fn")
        ]

    async def async_get_playlist_tracks(self, name: str) -> list[PlaylistTrack]:
        """Return all the tracks of a playlist saved on the player, in order.

        The player answers the window of 10 entries ending at an offset. The entries
        it cannot find any more (moved files) give empty windows, also at the start,
        so windows are read until a long run of them is empty.
        """
        tracks: list[PlaylistTrack] = []
        empty = 0
        end = PLAYLIST_BATCH
        while True:
            ends = range(end, end + PLAYLIST_BATCH * PLAYLIST_BATCH, PLAYLIST_BATCH)
            for window in await asyncio.gather(
                *(self._async_playlist_window(name, e) for e in ends)
            ):
                tracks.extend(window)
                empty = 0 if window else empty + 1
            end = ends[-1] + PLAYLIST_BATCH
            if empty >= PLAYLIST_EMPTY_WINDOWS or (
                not tracks and end // PLAYLIST_BATCH > PLAYLIST_LEADING_WINDOWS
            ):
                return tracks

    async def async_get_home(self, language: str = "en") -> list[HomeRow]:
        """Return the recently played, recent stations and most used rows of the player."""
        root = await self._get_xml(
            "/ui/Home",
            headers={**UI_HEADERS, "Accept-Language": language},
        )
        rows = []
        for row in root.iter("row"):
            if row.get("id") not in HOME_ROWS:
                continue
            items = [item for child in row if (item := _home_item(child))]
            if items:
                rows.append(HomeRow(row.get("id", ""), row.get("title", ""), items))
        return rows

    async def async_get_recent_albums(self) -> list[Album]:
        """Return the most recently added albums of the library."""
        root = await self._get_xml("/Albums", {"service": "LocalMusic", "recent": "1"})
        return [
            Album.from_names(album.findtext("alb", ""), album.findtext("art", ""))
            for album in root.iter("album")
        ]

    async def async_get_tracks(self, album_key: str) -> list[Track]:
        """Return the tracks of an album."""
        root = await self._get_xml("/Browse", {"key": album_key})
        return [
            Track(
                title=item.get("text", ""),
                artist=item.get("text2", ""),
                duration=_int(item.get("duration")) or None,
                play_path=play_path,
                image=item.get("image"),
            )
            for item in root.iter("item")
            if item.get("type") == "track"
            and (play_path := item.get("autoplayURL") or item.get("playURL"))
        ]

    async def async_get_presets(self) -> list[Preset]:
        """Return the presets of the player."""
        root = await self._get_xml("/Presets")
        return [
            Preset(
                _int(item.get("id")),
                item.get("name", ""),
                item.get("image"),
                item.get("url", ""),
            )
            for item in root.iter("preset")
        ]

    async def async_get_sources(self) -> list[Source]:
        """Return the inputs that can be selected on the player."""
        root = await self._get_xml("/RadioBrowse", {"service": "Capture"})
        return [
            Source(item.get("text", ""), type_index, unquote(item.get("URL", "")))
            for item in root.iter("item")
            if (type_index := item.get("typeIndex"))
        ]

    async def async_get_queue(self) -> list[QueueItem]:
        """Return the tracks of the play queue (the first MAX_QUEUE_LENGTH)."""
        root = await self._get_xml(
            "/Playlist", {"start": "0", "end": str(MAX_QUEUE_LENGTH - 1)}
        )
        return [
            QueueItem(
                id=_int(song.get("id")),
                title=song.findtext("title", ""),
                artist=song.findtext("art", ""),
                album=song.findtext("alb", ""),
                image=song.findtext("image"),
            )
            for song in root.iter("song")
        ]

    async def async_get_image(self, path: str) -> tuple[bytes, str]:
        """Fetch an image from the player (relative path) or a preset CDN (URL)."""
        url = (
            path
            if path.startswith(("http://", "https://"))
            else f"{self.base_url}{path}"
        )
        try:
            async with self._session.get(
                url, timeout=ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                response.raise_for_status()
                return await response.read(), response.content_type
        except (ClientError, TimeoutError) as err:
            raise BluOSError(str(err)) from err

    async def async_command(
        self, path: str, params: dict[str, str] | None = None
    ) -> None:
        """Send a control command, e.g. /Play or a play URL of a browse item."""
        await self._get(path, params)

    async def async_play(self) -> None:
        """Start or resume playback."""
        await self.async_command("/Play")

    async def async_seek(self, position: int) -> None:
        """Seek in the current track."""
        await self.async_command("/Play", {"seek": str(position)})

    async def async_pause(self) -> None:
        """Pause playback."""
        await self.async_command("/Pause")

    async def async_stop(self) -> None:
        """Stop playback."""
        await self.async_command("/Stop")

    async def async_skip(self) -> None:
        """Go to the next track."""
        await self.async_command("/Skip")

    async def async_back(self) -> None:
        """Go to the previous track."""
        await self.async_command("/Back")

    async def async_set_volume(self, level: int) -> None:
        """Set the volume, 0..100."""
        await self.async_command("/Volume", {"level": str(level)})

    async def async_get_volume(self) -> tuple[int, bool]:
        """Return the own volume of the player (0..100, -1 if fixed) and its mute state.

        In a group, /Status of a secondary player reports the volume of the group.
        """
        root = await self._get_xml("/Volume")
        return _int(root.text, -1), root.get("mute") == "1"

    async def async_step_volume(self, delta_db: int, group: bool = False) -> None:
        """Change the volume by a number of dB, of the whole group if asked."""
        await self.async_command(
            "/Volume", {"db": str(delta_db), "tell_slaves": "1" if group else "0"}
        )

    async def async_set_mute(self, mute: bool, group: bool = False) -> None:
        """Mute or unmute the player, or all the players of its group."""
        params = {"mute": "1" if mute else "0"}
        if group:
            params["tell_slaves"] = "1"
        await self.async_command("/Volume", params)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable or disable shuffle."""
        await self.async_command("/Shuffle", {"state": "1" if shuffle else "0"})

    async def async_set_repeat(self, state: int) -> None:
        """Set repeat: 0 queue, 1 track, 2 off."""
        await self.async_command("/Repeat", {"state": str(state)})

    async def async_load_preset(self, preset_id: int) -> None:
        """Load a preset."""
        await self.async_command("/Preset", {"id": str(preset_id)})

    async def async_play_queue_item(self, item_id: int) -> None:
        """Play a track of the queue."""
        await self.async_command("/Play", {"id": str(item_id)})

    async def async_clear_queue(self) -> None:
        """Remove all the tracks of the queue."""
        await self.async_command("/Clear")

    async def async_delete_queue_item(self, position: int) -> None:
        """Remove a track from the queue."""
        await self.async_command("/Delete", {"id": str(position)})

    async def async_move_queue_item(self, old: int, new: int) -> None:
        """Move a track of the queue to another position."""
        await self.async_command("/Move", {"old": str(old), "new": str(new)})

    async def async_save_queue(self, name: str) -> None:
        """Save the queue as a playlist."""
        await self.async_command("/Save", {"name": name})

    async def async_add_file(self, path: str) -> None:
        """Add a file of the music share to the end of the queue, without playing it."""
        await self.async_command(
            "/Add",
            {"file": path, "playnow": "-1", "service": "LocalMusic", "where": "last"},
        )

    async def async_get_queue_length(self) -> int:
        """Return the number of tracks of the queue."""
        root = await self._get_xml("/Playlist", {"length": "1"})
        return _int(root.findtext("length") or root.get("length"))

    async def async_delete_playlist(self, name: str) -> None:
        """Delete a playlist saved on the player."""
        await self.async_command("/Delete", {"name": name, "service": "BluOS"})

    async def async_select_source(self, type_index: str) -> None:
        """Switch to an input."""
        await self.async_command("/Play", {"inputTypeIndex": type_index})

    async def async_select_external_source(self, source_id: str) -> None:
        """Switch to an external input of an amplifier."""
        await self.async_command("/ExternalSource", {"id": source_id})

    async def async_move_playback(self, host: str, port: int) -> None:
        """Move what this player plays (queue, position, stream) to another player.

        The request goes to the source player, which pauses itself.
        """
        await self.async_command("/MovePlayback", {"id": host, "port": str(port)})

    async def async_add_slave(self, host: str, port: int) -> None:
        """Group another player with this one, which becomes the primary player."""
        await self.async_command("/AddSlave", {"slave": host, "port": str(port)})

    async def async_remove_slave(self, host: str, port: int) -> None:
        """Remove a secondary player from the group of this player."""
        await self.async_command("/RemoveSlave", {"slave": host, "port": str(port)})

    async def async_set_sleep(self, minutes: int) -> None:
        """Set the sleep timer to one of SLEEP_OPTIONS, 0 to turn it off.

        The player only offers a command that moves to the next value and answers
        with the new one (/Status lags behind), so it is pressed until it says so.
        """
        current = sleep_bucket((await self.async_get_status()).sleep)
        for _ in range(len(SLEEP_OPTIONS) + 1):
            if current == minutes:
                return
            root = await self._get_xml("/Sleep")
            current = sleep_bucket(_int(root.text) or None)
        raise BluOSError("Could not set the sleep timer")


def sleep_bucket(remaining: int | None) -> int:
    """Return the sleep timer option matching the minutes remaining, 0 if off."""
    if not remaining:
        return 0
    return next((option for option in SLEEP_OPTIONS if option >= remaining), SLEEP_OPTIONS[-1])
