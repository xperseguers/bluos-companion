"""Tests for the text backup of the playlists."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMockResponse,
    AiohttpClientMocker,
)
from yarl import URL

from custom_components.bluos_companion.api import BluOSClient, PlaylistTrack
from custom_components.bluos_companion.backup import async_pre_backup
from custom_components.bluos_companion.const import DOMAIN
from custom_components.bluos_companion.playlist_backup import (
    async_backup_playlists,
    file_name,
    parse,
    render,
)

from .conftest import BASE, calls, respond

SONG = (
    "<song service='LocalMusic'><art>{artist}</art><alb>{album}</alb><title>{title}</title>"
    "<time>{time}</time><fn>/var/mnt/10.20.30.45-BluOS/Music/{title}.m4a</fn></song>"
)
TRACKS = [
    PlaylistTrack("I Got a Name", "Samuel Hui", "Sam Hui 30th", 193, "/var/mnt/nas/Music/a.m4a"),
    PlaylistTrack("Skyfall", "ADELE", "", None, "/var/mnt/nas/Music/b.m4a"),
]


class Playlists:
    """Mock /Playlists and /Songs the way the player answers: windows of 10 ending at an offset."""

    def __init__(self, player_api: AiohttpClientMocker, base: str, content: dict[str, list[str]]) -> None:
        self.content = content
        names = "".join(f"<name>{name}</name>" for name in content)
        respond(player_api, f"{base}/Playlists", text=f"<playlists>{names}</playlists>")
        respond(player_api, f"{base}/Songs", side_effect=self._songs)

    async def _songs(self, method: str, url: URL, data: object) -> AiohttpClientMockResponse:
        titles = self.content[url.query["playlist"]]
        end = int(url.query["offset"])
        window = titles[max(end - 10, 0) : end]
        songs = "".join(
            SONG.format(artist="Artist", album="Album", title=title, time=200) for title in window
        )
        return AiohttpClientMockResponse(method, url, text=f"<songs>{songs}</songs>")


@pytest.fixture
def config_dir(hass: HomeAssistant, tmp_path: Path) -> Path:
    """Use a temporary configuration folder."""
    hass.config.config_dir = str(tmp_path)
    return tmp_path / "bluos_companion" / "playlists"


def test_render_and_parse_round_trip() -> None:
    """The text file keeps the paths and what is useful to read them."""
    text = render("Tuning", TRACKS, "Séjour", datetime(2026, 10, 29, 14, 30))
    assert text.startswith("#EXTM3U\n#PLAYLIST:Tuning\n")
    assert "#EXTINF:193,Samuel Hui - I Got a Name\n#EXTALB:Sam Hui 30th\n/var/mnt/nas/Music/a.m4a\n" in text
    assert "#EXTINF:-1,ADELE - Skyfall\n/var/mnt/nas/Music/b.m4a\n" in text

    name, tracks = parse(text, "fallback")

    assert name == "Tuning"
    assert tracks == TRACKS


def test_parse_edited_file() -> None:
    """A hand written file works: comments and blank lines are ignored, the name falls back."""
    text = "#EXTM3U\n# a comment\n\n/new/place/a.mp3\r\n#EXTINF:oops,No Artist\n/new/place/b.mp3\n"
    name, tracks = parse(text, "From file name")
    assert name == "From file name"
    assert [track.path for track in tracks] == ["/new/place/a.mp3", "/new/place/b.mp3"]
    assert tracks[1].title == "No Artist"


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Tuning", "Tuning.m3u8"), ("AC/DC: Live?", "AC_DC_ Live_.m3u8"), ("...", "playlist.m3u8")],
)
def test_file_names(name: str, expected: str) -> None:
    """Any playlist name gives a safe file name."""
    assert file_name(name) == expected


async def test_windows_are_read_until_the_end(
    hass: HomeAssistant,
    client: BluOSClient,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Empty leading windows (missing files) are skipped, all the tracks come in order."""
    titles = [f"T{i}" for i in range(25)]
    # The first 250 entries of an old playlist cannot be found: 25 empty windows.
    Playlists(aioclient_mock, BASE, {"Old": [""] * 250 + titles})
    aioclient_mock.mock_calls.clear()

    tracks = await client.async_get_playlist_tracks("Old")

    assert [track.title for track in tracks if track.title] == titles
    assert tracks[0].path.endswith(".m4a")


async def test_backup_writes_one_file_per_playlist(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> None:
    """Every playlist of the player becomes an editable text file."""
    Playlists(player_api, BASE, {"Tuning": ["a", "b"], "AC/DC": ["c"], "Empty": []})

    saved = await async_backup_playlists(hass)

    assert saved == {"Tuning": 2, "AC/DC": 1}
    text = (config_dir / "Tuning.m3u8").read_text(encoding="utf-8")
    assert "#PLAYLIST:Tuning" in text
    assert text.count("/var/mnt/10.20.30.45-BluOS/Music/") == 2
    assert (config_dir / "AC_DC.m3u8").exists()
    assert not (config_dir / "Empty.m3u8").exists()


async def test_an_empty_read_keeps_the_previous_backup(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> None:
    """A player that lost its entries does not erase what was saved."""
    Playlists(player_api, BASE, {"Tuning": ["a", "b"]})
    await async_backup_playlists(hass)
    before = (config_dir / "Tuning.m3u8").read_text(encoding="utf-8")

    Playlists(player_api, BASE, {"Tuning": []})
    assert await async_backup_playlists(hass) == {}

    assert (config_dir / "Tuning.m3u8").read_text(encoding="utf-8") == before


async def test_player_can_be_left_out_and_the_first_player_wins(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> None:
    """The option leaves a player out; the same playlist is saved from one player only."""
    Playlists(player_api, BASE, {"Tuning": ["a"]})
    hass.config_entries.async_update_entry(init_integration, options={"backup_playlists": False})
    assert await async_backup_playlists(hass) == {}
    assert not config_dir.exists()

    hass.config_entries.async_update_entry(init_integration, options={})
    assert await async_backup_playlists(hass) == {"Tuning": 1}


async def test_pre_backup_hook_never_blocks_the_backup(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The hook writes the files, and a failure is only logged."""
    Playlists(player_api, BASE, {"Tuning": ["a"]})
    await async_pre_backup(hass)
    assert (config_dir / "Tuning.m3u8").exists()

    respond(player_api, f"{BASE}/Playlists", status=500)
    await async_pre_backup(hass)
    assert (config_dir / "Tuning.m3u8").exists()


async def test_backup_service_returns_what_it_saved(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> None:
    """The manual service writes the files and tells what was saved."""
    Playlists(player_api, BASE, {"Tuning": ["a", "b", "c"]})
    result = await hass.services.async_call(
        DOMAIN, "backup_playlists", {}, blocking=True, return_response=True
    )
    assert result == {"playlists": {"Tuning": 3}}


FILE = """#EXTM3U
#PLAYLIST:Tuning
#EXTINF:193,Samuel Hui - I Got a Name
/new/share/a.m4a
/new/share/b.m4a
"""


@pytest.fixture
def restorable(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    config_dir: Path,
) -> AiohttpClientMocker:
    """A player with the playlist Existing, and a saved file for Tuning and Existing."""
    config_dir.mkdir(parents=True)
    (config_dir / "Tuning.m3u8").write_text(FILE, encoding="utf-8")
    (config_dir / "Existing.m3u8").write_text(FILE.replace("Tuning", "Existing"), encoding="utf-8")
    (config_dir / "Nothing.m3u8").write_text("#EXTM3U\n#PLAYLIST:Nothing\n", encoding="utf-8")
    respond(player_api, f"{BASE}/Playlists", text="<playlists><name>Existing</name></playlists>")
    for command in ("Delete", "Save"):
        respond(player_api, f"{BASE}/{command}", text="<ok/>")
    # The real player gives the header of the queue as child elements.
    respond(player_api, f"{BASE}/Playlist", text="<playlist><length>2</length><id>3</id></playlist>")
    player_api.mock_calls.clear()
    return player_api


async def _restore(hass: HomeAssistant, **data: object) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "restore_playlists",
        {"entity_id": "media_player.sejour", **data},
        blocking=True,
        return_response=True,
    )


async def test_restore_a_new_playlist(hass: HomeAssistant, restorable: AiohttpClientMocker) -> None:
    """The queue is emptied, filled file by file and saved under the name."""
    result = await _restore(hass, playlists=["Tuning", "Unknown"])

    assert result == {"restored": {"Tuning": 2}, "skipped": [], "not_found": ["Unknown"]}
    add = {"playnow": "-1", "service": "LocalMusic", "where": "last"}
    assert calls(restorable) == [
        ("/Playlists", {"service": "BluOS"}),
        ("/Clear", {}),
        ("/Add", {"file": "/new/share/a.m4a", **add}),
        ("/Add", {"file": "/new/share/b.m4a", **add}),
        ("/Playlist", {"length": "1"}),
        ("/Save", {"name": "Tuning"}),
    ]


async def test_restore_leaves_an_existing_playlist_alone(
    hass: HomeAssistant, restorable: AiohttpClientMocker
) -> None:
    """Without the explicit request to replace, nothing of an existing playlist is touched."""
    result = await _restore(hass)

    assert result["restored"] == {"Tuning": 2}
    assert sorted(result["skipped"]) == ["Existing", "Nothing"]
    assert ("/Delete", {"name": "Existing", "service": "BluOS"}) not in calls(restorable)
    assert [query for path, query in calls(restorable) if path == "/Save"] == [{"name": "Tuning"}]


async def test_restore_replaces_only_when_asked(
    hass: HomeAssistant, restorable: AiohttpClientMocker
) -> None:
    """The old playlist is deleted after the new queue is ready, just before saving."""
    result = await _restore(hass, playlists=["Existing"], replace=True)

    assert result["restored"] == {"Existing": 2}
    paths = [path for path, _ in calls(restorable)]
    assert paths == ["/Playlists", "/Clear", "/Add", "/Add", "/Playlist", "/Delete", "/Save"]
    assert calls(restorable)[-2] == ("/Delete", {"name": "Existing", "service": "BluOS"})


async def test_restore_warns_when_the_player_finds_fewer_files(
    hass: HomeAssistant,
    restorable: AiohttpClientMocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Files that are not found at their path (moved share) are reported."""
    respond(restorable, f"{BASE}/Playlist", text="<playlist><length>1</length><id>3</id></playlist>")

    result = await _restore(hass, playlists=["Tuning"])

    assert result["restored"] == {"Tuning": 1}
    assert "found 1 of the 2 files" in caplog.text


async def test_restore_needs_a_bluos_player(hass: HomeAssistant, restorable: AiohttpClientMocker) -> None:
    """Another entity is refused."""
    from homeassistant.exceptions import HomeAssistantError

    with pytest.raises(HomeAssistantError, match="Choose a BluOS Companion player"):
        await _restore(hass, entity_id="media_player.nope")
