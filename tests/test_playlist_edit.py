"""Tests for deleting and renaming the playlists saved on a player."""

from __future__ import annotations

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

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, respond

ENTITY_ID = "media_player.sejour"
SONG = "<song><art>A</art><alb>B</alb><title>{file}</title><time>200</time><fn>/music/{file}.m4a</fn></song>"


class FakePlaylists:
    """A player that keeps saved playlists: it lists, reads, adds to and deletes them."""

    def __init__(self, player_api: AiohttpClientMocker, content: dict[str, list[str]]) -> None:
        self.content = content
        self.drop_adds_after: int | None = None  # a player that stops keeping tracks
        self.fail_delete_of: set[str] = set()
        respond(player_api, f"{BASE}/Playlists", side_effect=self._names)
        respond(player_api, f"{BASE}/Songs", side_effect=self._songs)
        respond(player_api, f"{BASE}/AddToPlaylist", side_effect=self._add)
        respond(player_api, f"{BASE}/Delete", side_effect=self._delete)

    async def _names(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        names = "".join(f"<name>{name}</name>" for name in self.content)
        return AiohttpClientMockResponse(method, url, text=f"<playlists>{names}</playlists>")

    async def _songs(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        songs = "".join(SONG.format(file=file) for file in self.content[url.query["playlist"]])
        return AiohttpClientMockResponse(method, url, text=f"<songs>{songs}</songs>")

    async def _add(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        name = url.query["name"]
        if name not in self.content:
            if "create" not in url.query:
                return AiohttpClientMockResponse(
                    method, url, text="<error><message>Playlist does not exist</message></error>"
                )
            self.content[name] = []
        elif "create" in url.query:
            return AiohttpClientMockResponse(
                method, url, text="<error><message>Playlist already exists</message></error>"
            )
        if self.drop_adds_after is None or len(self.content[name]) < self.drop_adds_after:
            self.content[name].append(url.query["songid"].split("/")[-1].removesuffix(".m4a"))
        return AiohttpClientMockResponse(method, url, text='<addToPlaylist service="BluOS"/>')

    async def _delete(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        name = url.query["name"]
        if name in self.fail_delete_of:
            return AiohttpClientMockResponse(method, url, status=500)
        self.content.pop(name, None)
        return AiohttpClientMockResponse(method, url, text="<playlists/>")


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Use a temporary configuration folder."""
    hass.config.config_dir = str(tmp_path)
    return tmp_path / "bluos_companion" / "playlists"


@pytest.fixture
def player(player_api: AiohttpClientMocker) -> FakePlaylists:
    """A player with two saved playlists."""
    return FakePlaylists(player_api, {"Relaxing": ["a", "b", "a", "c"], "Other": ["z"]})


async def test_rename_copies_checks_and_deletes(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    player: FakePlaylists,
    config_dir: Path,
) -> None:
    """The copy has the same tracks in the same order (a track twice stays twice), then the old one goes."""
    player_api.mock_calls.clear()
    await hass.services.async_call(
        DOMAIN,
        "rename_playlist",
        {"entity_id": ENTITY_ID, "playlist": "relaxing", "new_name": " Relaxing evening "},
        blocking=True,
    )
    assert player.content == {"Relaxing evening": ["a", "b", "a", "c"], "Other": ["z"]}
    made = calls(player_api)
    adds = [query for path, query in made if path == "/AddToPlaylist"]
    # Only the first request makes the playlist; the queue and the playback are not touched
    assert [("create" in query) for query in adds] == [True, False, False, False]
    assert adds[0]["sourceService"] == "LocalMusic"
    assert not [path for path, _ in made if path in ("/Clear", "/Play", "/Stop", "/Save")]
    assert made[-1][0] == "/Delete" and made[-1][1]["name"] == "Relaxing"
    # A text file of the old playlist was written first
    assert "/music/a.m4a" in (config_dir / "Relaxing.m3u8").read_text()


@pytest.mark.parametrize(
    ("new_name", "message"),
    [
        ("Other", "exists already"),
        ("other", "exists already"),
        ("relaxing", "exists already"),
        ("   ", "between 1 and 100"),
        ("x" * 101, "between 1 and 100"),
    ],
)
async def test_rename_refuses_a_bad_name(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    player: FakePlaylists,
    new_name: str,
    message: str,
) -> None:
    """A name that is taken or empty changes nothing."""
    with pytest.raises(HomeAssistantError, match=message):
        await hass.services.async_call(
            DOMAIN,
            "rename_playlist",
            {"entity_id": ENTITY_ID, "playlist": "Relaxing", "new_name": new_name},
            blocking=True,
        )
    assert set(player.content) == {"Relaxing", "Other"}


async def test_rename_of_an_unknown_playlist(
    hass: HomeAssistant, init_integration: MockConfigEntry, player: FakePlaylists
) -> None:
    """Only a saved playlist can be renamed."""
    with pytest.raises(HomeAssistantError, match="Unknown playlist: Nothing"):
        await hass.services.async_call(
            DOMAIN,
            "rename_playlist",
            {"entity_id": ENTITY_ID, "playlist": "Nothing", "new_name": "Else"},
            blocking=True,
        )


async def test_an_incomplete_copy_is_discarded_and_the_old_playlist_kept(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player: FakePlaylists,
    config_dir: Path,
) -> None:
    """When the copy lacks tracks the old playlist stays, and the half copy is deleted."""
    player.drop_adds_after = 2
    with pytest.raises(HomeAssistantError, match="could not be copied completely.*left as it was"):
        await hass.services.async_call(
            DOMAIN,
            "rename_playlist",
            {"entity_id": ENTITY_ID, "playlist": "Relaxing", "new_name": "Evening"},
            blocking=True,
        )
    assert player.content == {"Relaxing": ["a", "b", "a", "c"], "Other": ["z"]}


async def test_an_unreadable_playlist_is_not_renamed(
    hass: HomeAssistant, init_integration: MockConfigEntry, player: FakePlaylists
) -> None:
    """A playlist read empty (the player gave nothing) is not copied, so nothing is deleted."""
    player.content["Empty"] = []
    with pytest.raises(HomeAssistantError, match="could not be read completely"):
        await hass.services.async_call(
            DOMAIN,
            "rename_playlist",
            {"entity_id": ENTITY_ID, "playlist": "Empty", "new_name": "Else"},
            blocking=True,
        )
    assert "Empty" in player.content and "Else" not in player.content


async def test_a_failing_delete_of_the_old_playlist_is_said(
    hass: HomeAssistant, init_integration: MockConfigEntry, player: FakePlaylists
) -> None:
    """The copy exists but the old one stays: the error says so."""
    player.fail_delete_of = {"Relaxing"}
    with pytest.raises(HomeAssistantError, match="Evening was made, but Relaxing could not be deleted"):
        await hass.services.async_call(
            DOMAIN,
            "rename_playlist",
            {"entity_id": ENTITY_ID, "playlist": "Relaxing", "new_name": "Evening"},
            blocking=True,
        )
    assert {"Relaxing", "Evening"} <= set(player.content)


async def test_delete_keeps_a_text_file(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player: FakePlaylists,
    config_dir: Path,
) -> None:
    """A playlist is deleted after its text file is written, so restore_playlists can bring it back."""
    await hass.services.async_call(
        DOMAIN, "delete_playlist", {"entity_id": ENTITY_ID, "playlist": "RELAXING"}, blocking=True
    )
    assert set(player.content) == {"Other"}
    assert (config_dir / "Relaxing.m3u8").read_text().count("/music/a.m4a") == 2


async def test_delete_of_an_unknown_playlist(
    hass: HomeAssistant, init_integration: MockConfigEntry, player: FakePlaylists
) -> None:
    """Nothing else is deleted when the name is wrong."""
    with pytest.raises(HomeAssistantError, match="Unknown playlist: Rel"):
        await hass.services.async_call(
            DOMAIN, "delete_playlist", {"entity_id": ENTITY_ID, "playlist": "Rel"}, blocking=True
        )
    assert set(player.content) == {"Relaxing", "Other"}


async def test_the_panel_deletes_and_renames(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player: FakePlaylists,
    config_dir: Path,
) -> None:
    """The panel uses the same code as the services."""
    client = await hass_ws_client(hass)
    entry_id = init_integration.entry_id
    await client.send_json_auto_id(
        {"type": "bluos_companion/playlist_rename", "entry_id": entry_id, "name": "Relaxing", "new_name": "Calm"}
    )
    assert (await client.receive_json())["result"] == {"count": 4}
    await client.send_json_auto_id(
        {"type": "bluos_companion/playlist_delete", "entry_id": entry_id, "name": "Other"}
    )
    assert (await client.receive_json())["success"]
    assert set(player.content) == {"Calm"}
