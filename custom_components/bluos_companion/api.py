"""Minimal client for the BluOS player HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from aiohttp import ClientError, ClientSession, ClientTimeout

REQUEST_TIMEOUT = 20
MAX_BROWSE_PAGES = 8


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


@dataclass(frozen=True, slots=True)
class Node:
    """An entry of the BluOS browse hierarchy (section, artist, album, track...)."""

    type: str
    title: str
    subtitle: str
    browse_key: str | None
    play_path: str | None
    image: str | None


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
    def image(self) -> str:
        """Player path of the cover."""
        return f"/Artwork?service=LocalMusic&{self.query}"

    @property
    def play_path(self) -> str:
        """Player path starting the album."""
        return f"/Add?playnow=1&service=LocalMusic&{self.query}"


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
    ) -> bytes:
        try:
            async with self._session.get(
                f"{self.base_url}{path}",
                params=params,
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
    ) -> ET.Element:
        body = await self._get(path, params, timeout)
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
        )

    async def async_browse(self, key: str) -> list[Node]:
        """Return all entries below a browse key.

        Long listings are split in pages. The player may repeat earlier entries
        in later pages, so entries are merged in order of first appearance.
        """
        nodes: dict[Node, None] = {}
        next_key: str | None = key
        for _ in range(MAX_BROWSE_PAGES):
            root = await self._get_xml("/Browse", {"key": next_key})
            for item in root.iter("item"):
                node = Node(
                    type=item.get("type", ""),
                    title=item.get("text", ""),
                    subtitle=item.get("text2", ""),
                    browse_key=item.get("browseKey"),
                    play_path=item.get("autoplayURL") or item.get("playURL"),
                    image=item.get("image"),
                )
                nodes.setdefault(node, None)
            if not (next_key := root.get("nextKey")):
                break
        return list(nodes)

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
            Preset(_int(item.get("id")), item.get("name", ""), item.get("image"))
            for item in root.iter("preset")
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

    async def async_set_mute(self, mute: bool) -> None:
        """Mute or unmute the player."""
        await self.async_command("/Volume", {"mute": "1" if mute else "0"})

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable or disable shuffle."""
        await self.async_command("/Shuffle", {"state": "1" if shuffle else "0"})

    async def async_set_repeat(self, state: int) -> None:
        """Set repeat: 0 queue, 1 track, 2 off."""
        await self.async_command("/Repeat", {"state": str(state)})

    async def async_load_preset(self, preset_id: int) -> None:
        """Load a preset."""
        await self.async_command("/Preset", {"id": str(preset_id)})
