"""Tests for the media player entity."""

from __future__ import annotations

import base64
import json

import aiohttp
import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_REPEAT,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_SHUFFLE,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerState,
    RepeatMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_MEDIA_STOP,
    SERVICE_REPEAT_SET,
    SERVICE_SHUFFLE_SET,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, status_xml

ENTITY_ID = "media_player.sejour"


def _media_id(entry: MockConfigEntry, tail: str) -> str:
    return f"media-source://{DOMAIN}/{entry.entry_id}/{tail}"


def _b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _node(play_path: str | None) -> str:
    return _b64(json.dumps({"k": "key", "p": play_path, "t": "title"}))


async def _refresh(
    hass: HomeAssistant, entry: MockConfigEntry, player_api: AiohttpClientMocker, xml: str
) -> None:
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", text=xml)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.usefixtures("init_integration")
async def test_state_attributes(hass: HomeAssistant) -> None:
    """Now-playing information is exposed."""
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == MediaPlayerState.PLAYING
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.25
    assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is False
    assert state.attributes[ATTR_MEDIA_TITLE] == "Rolling In the Deep"
    assert state.attributes[ATTR_MEDIA_ARTIST] == "Adele"
    assert state.attributes[ATTR_MEDIA_ALBUM_NAME] == "21"
    assert state.attributes[ATTR_MEDIA_DURATION] == 228
    assert state.attributes[ATTR_MEDIA_POSITION] == 10
    assert state.attributes[ATTR_MEDIA_SHUFFLE] is False
    assert state.attributes[ATTR_MEDIA_REPEAT] == RepeatMode.OFF
    assert state.attributes["entity_picture"].startswith(f"/api/media_player_proxy/{ENTITY_ID}")


@pytest.mark.parametrize(
    ("bluos_state", "expected"),
    [
        ("play", MediaPlayerState.PLAYING),
        ("stream", MediaPlayerState.PLAYING),
        ("pause", MediaPlayerState.PAUSED),
        ("connecting", MediaPlayerState.BUFFERING),
        ("stop", MediaPlayerState.IDLE),
    ],
)
async def test_states(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    bluos_state: str,
    expected: MediaPlayerState,
) -> None:
    """BluOS states map to media player states."""
    await _refresh(hass, init_integration, player_api, status_xml(bluos_state))
    assert hass.states.get(ENTITY_ID).state == expected


@pytest.mark.parametrize(
    ("repeat", "expected"),
    [("0", RepeatMode.ALL), ("1", RepeatMode.ONE), ("2", RepeatMode.OFF)],
)
async def test_repeat(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    repeat: str,
    expected: RepeatMode,
) -> None:
    """Repeat values are mapped."""
    await _refresh(hass, init_integration, player_api, status_xml(repeat=repeat))
    assert hass.states.get(ENTITY_ID).attributes[ATTR_MEDIA_REPEAT] == expected


async def test_fixed_volume(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A player with fixed volume has no volume level."""
    await _refresh(hass, init_integration, player_api, status_xml(volume="-1"))
    assert ATTR_MEDIA_VOLUME_LEVEL not in hass.states.get(ENTITY_ID).attributes


@pytest.mark.parametrize(
    ("service", "data", "path", "query"),
    [
        (SERVICE_MEDIA_PLAY, {}, "/Play", {}),
        (SERVICE_MEDIA_PAUSE, {}, "/Pause", {}),
        (SERVICE_MEDIA_STOP, {}, "/Stop", {}),
        (SERVICE_MEDIA_NEXT_TRACK, {}, "/Skip", {}),
        (SERVICE_MEDIA_PREVIOUS_TRACK, {}, "/Back", {}),
        (SERVICE_MEDIA_SEEK, {ATTR_MEDIA_SEEK_POSITION: 30}, "/Play", {"seek": "30"}),
        (SERVICE_VOLUME_SET, {ATTR_MEDIA_VOLUME_LEVEL: 0.4}, "/Volume", {"level": "40"}),
        (SERVICE_VOLUME_MUTE, {ATTR_MEDIA_VOLUME_MUTED: True}, "/Volume", {"mute": "1"}),
        (SERVICE_SHUFFLE_SET, {ATTR_MEDIA_SHUFFLE: True}, "/Shuffle", {"state": "1"}),
        (SERVICE_REPEAT_SET, {ATTR_MEDIA_REPEAT: RepeatMode.ALL}, "/Repeat", {"state": "0"}),
        (SERVICE_REPEAT_SET, {ATTR_MEDIA_REPEAT: RepeatMode.ONE}, "/Repeat", {"state": "1"}),
        (SERVICE_REPEAT_SET, {ATTR_MEDIA_REPEAT: RepeatMode.OFF}, "/Repeat", {"state": "2"}),
    ],
)
async def test_services(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    service: str,
    data: dict,
    path: str,
    query: dict[str, str],
) -> None:
    """Services send the matching command."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        service,
        {ATTR_ENTITY_ID: ENTITY_ID, **data},
        blocking=True,
    )
    assert calls(player_api) == [(path, query)]


async def test_command_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A failing player raises a readable error."""
    player_api.clear_requests()
    player_api.get(f"{BASE}/Pause", exc=aiohttp.ClientError("down"))
    with pytest.raises(HomeAssistantError, match="BluOS player error"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_MEDIA_PAUSE,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )


@pytest.mark.parametrize(
    ("tail", "path", "query"),
    [
        pytest.param(
            f"album/{_b64('album=21&artist=Adele')}",
            "/Add",
            {"playnow": "1", "service": "LocalMusic", "album": "21", "artist": "Adele"},
            id="album",
        ),
        pytest.param(
            f"track/{_b64('/Add?playnow=1&file=%2Fa.m4a')}",
            "/Add",
            {"playnow": "1", "file": "/a.m4a"},
            id="track",
        ),
        pytest.param("preset/3", "/Preset", {"id": "3"}, id="preset"),
        pytest.param("queue/3", "/Play", {"id": "3"}, id="queue"),
        pytest.param(
            f"node/{_node('/Load?service=BluOS&name=Relaxing')}",
            "/Load",
            {"service": "BluOS", "name": "Relaxing"},
            id="playlist-node",
        ),
    ],
)
async def test_play_library_media(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    tail: str,
    path: str,
    query: dict[str, str],
) -> None:
    """Library items are started on the player."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_TYPE: "music",
            ATTR_MEDIA_CONTENT_ID: _media_id(init_integration, tail),
        },
        blocking=True,
    )
    assert calls(player_api) == [(path, query)]


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param("recent", id="not-playable"),
        pytest.param("preset/abc", id="bad-preset"),
        pytest.param("queue/abc", id="bad-queue-position"),
        pytest.param(f"track/{_b64('/Settings?id=x')}", id="path-not-allowed"),
        pytest.param(f"track/{_b64('http://evil/')}", id="absolute-url"),
        pytest.param(f"node/{_node(None)}", id="node-without-play-path"),
        pytest.param(f"node/{_node('/Settings?id=x')}", id="node-path-not-allowed"),
        pytest.param("node/!!!", id="node-invalid"),
    ],
)
async def test_play_rejects_invalid_items(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    tail: str,
) -> None:
    """Only known play paths are sent to the player."""
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: "music",
                ATTR_MEDIA_CONTENT_ID: _media_id(init_integration, tail),
            },
            blocking=True,
        )
    assert calls(player_api) == []


async def test_play_item_of_another_player(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """An item of another player is refused."""
    with pytest.raises(HomeAssistantError, match="another player"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_MEDIA_CONTENT_TYPE: "music",
                ATTR_MEDIA_CONTENT_ID: f"media-source://{DOMAIN}/other/preset/1",
            },
            blocking=True,
        )


async def test_play_url(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A plain URL is streamed by the player."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_TYPE: "music",
            ATTR_MEDIA_CONTENT_ID: "http://example.com/stream.mp3",
        },
        blocking=True,
    )
    assert calls(player_api) == [("/Play", {"url": "http://example.com/stream.mp3"})]


async def test_unavailable_when_player_unreachable(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The entity becomes unavailable when polling fails."""
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", exc=aiohttp.ClientError)
    await init_integration.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_setup_fails_when_player_unreachable(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The entry retries later when the first poll fails."""
    player_api.clear_requests()
    player_api.get(f"{BASE}/Status", exc=aiohttp.ClientError)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state.name == "SETUP_RETRY"


async def test_unload(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    assert hass.states.get(ENTITY_ID).state == STATE_UNAVAILABLE


async def test_set_volume_is_limited_to_the_maximum(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The volume entity service cannot go above the maximum volume option."""
    hass.config_entries.async_update_entry(init_integration, options={"max_volume": 40})
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: "media_player.sejour", ATTR_MEDIA_VOLUME_LEVEL: 0.9},
        blocking=True,
    )
    assert calls(player_api) == [("/Volume", {"level": "40"})]
