"""Tests for the import of playlists exported from another music player."""

from __future__ import annotations

import unicodedata
from pathlib import Path
from urllib.parse import quote

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.api import BluOSClient
from custom_components.bluos_companion.const import DOMAIN
from custom_components.bluos_companion.playlist_backup import parse
from custom_components.bluos_companion.playlist_import import (
    ExportedTrack,
    async_detect_library_root,
    common_source_root,
    convert,
    parse_export,
)

from .conftest import BASE, calls, respond

MAC_ROOT = "/Users/me/Music/Music/Media.localized/Music/"
SHARE_ROOT = "/var/mnt/nas-BluOS/Music/"
FIORI = "Patrick Fiori/4 mots/10 Je sais où aller.m4a"
# What Apple Music writes: carriage returns only, "Title - Artist", accents decomposed
EXPORT = "\r".join(
    [
        "#EXTM3U",
        "#EXTINF:164,Amoureux de ma femme - Richard Anthony",
        f"{MAC_ROOT}Richard Anthony/Unknown Album/Amoureux de ma femme.mp3",
        "#EXTINF:210,Je sais où aller - Patrick Fiori",
        unicodedata.normalize("NFD", f"{MAC_ROOT}{FIORI}"),
        "#EXTINF:100,Elsewhere - Someone",
        "/Volumes/Other/Someone/Album/Elsewhere.mp3",
        "",
    ]
)


def test_parse_export() -> None:
    """The lines end with carriage returns, accents are composed, titles come first."""
    name, tracks = parse_export(EXPORT, unicodedata.normalize("NFD", "Par cœur é"))

    assert name == "Par cœur é"
    assert [(t.title, t.duration) for t in tracks] == [
        ("Amoureux de ma femme", 164),
        ("Je sais où aller", 210),
        ("Elsewhere", 100),
    ]
    assert tracks[1].path == f"{MAC_ROOT}{FIORI}"
    assert unicodedata.is_normalized("NFC", tracks[1].path)


def test_parse_export_takes_the_name_of_the_file() -> None:
    """A #PLAYLIST line wins over the name of the file."""
    assert parse_export("#EXTM3U\n#PLAYLIST:Mine\n#EXTINF:5,A - B\n/x/y/z/f.m4a\n", "File")[0] == "Mine"


def test_the_folder_of_the_library_is_what_comes_before_artist_album_and_file() -> None:
    """The most common folder wins, a track elsewhere does not move it."""
    _, tracks = parse_export(EXPORT, "x")
    assert common_source_root(tracks) == MAC_ROOT
    assert common_source_root([ExportedTrack("a", None, "/short.mp3")]) is None


def test_convert_swaps_the_folder_and_leaves_out_the_rest() -> None:
    """The paths become the ones of the share, other folders are reported."""
    _, tracks = parse_export(EXPORT, "x")

    converted, outside = convert(tracks, MAC_ROOT, SHARE_ROOT)

    assert [track.path for track in converted] == [
        f"{SHARE_ROOT}Richard Anthony/Unknown Album/Amoureux de ma femme.mp3",
        f"{SHARE_ROOT}{FIORI}",
    ]
    assert outside == ["/Volumes/Other/Someone/Album/Elsewhere.mp3"]
    fiori = converted[1]
    assert (fiori.title, fiori.artist, fiori.album, fiori.duration) == (
        "Je sais où aller",
        "Patrick Fiori",
        "4 mots",
        210,
    )


def songs(*paths: str) -> str:
    """Return the answer of the player for the songs of an artist."""
    body = "".join(f"<song><fn>{path}</fn></song>" for path in paths)
    return f"<songs>{body}</songs>"


async def test_the_library_is_found_on_the_player(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """The files of an artist on the player tell where the library is, whichever track matches."""
    _, tracks = parse_export(EXPORT, "x")
    aioclient_mock.get(f"{BASE}/Songs?service=LocalMusic&artist=Richard+Anthony", text=songs())
    aioclient_mock.get(
        f"{BASE}/Songs?service=LocalMusic&artist=Patrick+Fiori",
        text=songs(f"{SHARE_ROOT}Patrick Fiori/Promesse/03 Chez nous.m4a", f"{SHARE_ROOT}{FIORI}"),
    )

    assert await async_detect_library_root(client, tracks, MAC_ROOT) == SHARE_ROOT
    assert [query["artist"] for _, query in calls(aioclient_mock)] == [
        "Richard Anthony",
        "Patrick Fiori",
    ]


async def test_a_library_that_is_not_found_is_an_error(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """The error says what to do when no track is on the player."""
    _, tracks = parse_export(EXPORT, "x")
    aioclient_mock.get(f"{BASE}/Songs", text=songs())

    with pytest.raises(HomeAssistantError, match="library_path"):
        await async_detect_library_root(client, tracks, MAC_ROOT)


@pytest.fixture
def importable(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    tmp_path: Path,
) -> Path:
    """A player that has the music, and an exported playlist waiting in the import folder."""
    hass.config.config_dir = str(tmp_path)
    folder = tmp_path / "bluos_companion" / "import"
    folder.mkdir(parents=True)
    (folder / "Par cœur.m3u8").write_text(EXPORT, encoding="utf-8")
    respond(player_api, f"{BASE}/Playlists", text="<playlists/>")
    respond(player_api, f"{BASE}/Songs?service=LocalMusic&artist=Richard+Anthony", text=songs())
    respond(
        player_api,
        f"{BASE}/Songs?service=LocalMusic&artist={quote('Patrick Fiori').replace('%20', '+')}",
        text=songs(f"{SHARE_ROOT}{FIORI}"),
    )
    for command in ("Delete", "Save", "Clear"):
        respond(player_api, f"{BASE}/{command}", text="<ok/>")
    respond(player_api, f"{BASE}/Playlist", text="<playlist><length>2</length><id>3</id></playlist>")
    player_api.mock_calls.clear()
    return tmp_path / "bluos_companion"


async def _import(hass: HomeAssistant, **data: object) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "import_playlists",
        {"entity_id": "media_player.sejour", **data},
        blocking=True,
        return_response=True,
    )


async def test_import_converts_and_builds_the_playlist(
    hass: HomeAssistant, importable: Path, player_api: AiohttpClientMocker
) -> None:
    """The exported file becomes a backup file of the share, and the playlist is built."""
    result = await _import(hass)

    assert result["imported"] == {"Par cœur": {"tracks": 2, "left_out": 1}}
    assert result["restore"] == {"restored": {"Par cœur": 2}, "skipped": [], "not_found": []}
    text = (importable / "playlists" / "Par cœur.m3u8").read_text(encoding="utf-8")
    assert 'Imported by BluOS Companion from "Par cœur.m3u8"' in text
    name, tracks = parse(text, "x")
    assert name == "Par cœur"
    assert [track.path for track in tracks] == [
        f"{SHARE_ROOT}Richard Anthony/Unknown Album/Amoureux de ma femme.mp3",
        f"{SHARE_ROOT}{FIORI}",
    ]
    added = [query["file"] for path, query in calls(player_api) if path == "/Add"]
    assert added == [track.path for track in tracks]
    assert ("/Save", {"name": "Par cœur"}) in calls(player_api)


async def test_import_without_restore_only_writes_the_file(
    hass: HomeAssistant, importable: Path, player_api: AiohttpClientMocker
) -> None:
    """The file can be looked at before anything touches the player."""
    result = await _import(hass, restore=False)

    assert "restore" not in result
    assert (importable / "playlists" / "Par cœur.m3u8").exists()
    assert not [path for path, _ in calls(player_api) if path in ("/Clear", "/Add", "/Save")]


async def test_import_keeps_a_file_that_exists_unless_replace(
    hass: HomeAssistant, importable: Path
) -> None:
    """An existing playlist file is not overwritten, replace does it."""
    playlists = importable / "playlists"
    playlists.mkdir()
    (playlists / "Par cœur.m3u8").write_text("#EXTM3U\n#PLAYLIST:Par cœur\n/old/a.m4a\n", encoding="utf-8")

    result = await _import(hass, restore=False)
    assert result["imported"] == {} and result["skipped"] == ["Par cœur"]
    assert "/old/a.m4a" in (playlists / "Par cœur.m3u8").read_text(encoding="utf-8")

    result = await _import(hass, restore=False, replace=True)
    assert result["imported"] == {"Par cœur": {"tracks": 2, "left_out": 1}}
    assert "/old/a.m4a" not in (playlists / "Par cœur.m3u8").read_text(encoding="utf-8")


async def test_import_with_the_folders_given(
    hass: HomeAssistant, importable: Path, player_api: AiohttpClientMocker
) -> None:
    """Given folders are used, the player is not asked where the library is."""
    result = await _import(
        hass, restore=False, source_path=MAC_ROOT.rstrip("/"), library_path="/elsewhere/Music"
    )

    assert result["imported"] == {"Par cœur": {"tracks": 2, "left_out": 1}}
    text = (importable / "playlists" / "Par cœur.m3u8").read_text(encoding="utf-8")
    assert "/elsewhere/Music/Patrick Fiori/4 mots/10 Je sais où aller.m4a" in text
    assert not [path for path, _ in calls(player_api) if path == "/Songs"]


async def test_import_without_a_file_says_where_to_put_it(
    hass: HomeAssistant, init_integration: MockConfigEntry, tmp_path: Path
) -> None:
    """The folder is made and the error names it."""
    hass.config.config_dir = str(tmp_path)

    with pytest.raises(HomeAssistantError, match="import"):
        await _import(hass)
    assert (tmp_path / "bluos_companion" / "import").is_dir()
