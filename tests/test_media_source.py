"""Tests for the media source and the artwork proxy."""

from __future__ import annotations

import base64

import aiohttp
import pytest
from homeassistant.components.media_player import BrowseError
from homeassistant.components.media_source import (
    Unresolvable,
    async_browse_media,
    async_resolve_media,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, SECTION_A_KEY, calls

ROOT = f"media-source://{DOMAIN}"


def _b64(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _ids(item) -> list[str]:
    return [child.media_content_id for child in item.children]


def _thumb_path(thumbnail: str) -> str:
    return thumbnail.split("&authSig=")[0]


@pytest.mark.usefixtures("init_integration")
async def test_root_lists_players(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Each loaded player is listed."""
    item = await async_browse_media(hass, ROOT)
    assert [child.title for child in item.children] == ["Séjour"]
    assert _ids(item) == [f"{ROOT}/{init_integration.entry_id}"]


async def test_player_menu(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """The player offers recent albums, albums and presets."""
    item = await async_browse_media(hass, f"{ROOT}/{init_integration.entry_id}")
    assert [child.title for child in item.children] == [
        "Recently added",
        "Albums",
        "Presets",
    ]


async def test_recent_albums(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Recent albums are playable, expandable and have a proxied thumbnail."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/recent")
    first = item.children[0]
    assert first.title == "Definitely Maybe - Oasis"
    assert first.can_play
    assert first.can_expand
    assert first.media_content_id == (
        f"{ROOT}/{eid}/album/{_b64('album=Definitely+Maybe&artist=Oasis')}"
    )
    assert first.thumbnail.startswith(f"/api/{DOMAIN}/{eid}/artwork?path=/Artwork")
    assert "authSig=" in first.thumbnail


async def test_albums_by_section(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Sections lead to the albums of a letter."""
    eid = init_integration.entry_id
    sections = await async_browse_media(hass, f"{ROOT}/{eid}/albums")
    assert [child.title for child in sections.children] == ["A (84)", "# (36)"]
    assert sections.children[0].media_content_id == (
        f"{ROOT}/{eid}/albums/{_b64(SECTION_A_KEY)}"
    )

    albums = await async_browse_media(hass, sections.children[0].media_content_id)
    assert [child.title for child in albums.children] == [
        "À côté du soleil - Cristina Marocco"
    ]


async def test_album_tracks(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """An album lists its tracks, each playable."""
    eid = init_integration.entry_id
    item = await async_browse_media(
        hass, f"{ROOT}/{eid}/album/{_b64('album=21&artist=Adele')}"
    )
    assert item.title == "21"
    assert item.can_play
    assert [child.title for child in item.children] == [
        "1. Rolling In the Deep",
        "5. Set Fire to the Rain",
    ]
    assert all(child.can_play and not child.can_expand for child in item.children)


async def test_presets(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """HTTPS preset images are used as is, others are proxied."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/presets")
    http_preset, https_preset, no_image = item.children
    assert http_preset.thumbnail.startswith(f"/api/{DOMAIN}/{eid}/artwork?path=http")
    assert https_preset.thumbnail == "https://cdn.example/s58290.png"
    assert no_image.thumbnail is None
    assert [child.media_content_id for child in item.children] == [
        f"{ROOT}/{eid}/preset/{n}" for n in (1, 2, 3)
    ]


@pytest.mark.parametrize(
    "tail",
    [
        pytest.param("unknown", id="unknown-entry"),
        pytest.param("{eid}/nope", id="unknown-item"),
        pytest.param("{eid}/albums/!!!", id="bad-identifier"),
    ],
)
async def test_browse_errors(
    hass: HomeAssistant, init_integration: MockConfigEntry, tail: str
) -> None:
    """Invalid identifiers raise a browse error."""
    with pytest.raises(BrowseError):
        await async_browse_media(
            hass, f"{ROOT}/{tail.format(eid=init_integration.entry_id)}"
        )


async def test_browse_player_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Player errors become browse errors."""
    player_api.clear_requests()
    player_api.get(f"{BASE}/Presets", exc=aiohttp.ClientError)
    with pytest.raises(BrowseError):
        await async_browse_media(hass, f"{ROOT}/{init_integration.entry_id}/presets")


async def test_resolve_is_not_supported(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Library items cannot be turned into a URL."""
    with pytest.raises(Unresolvable):
        await async_resolve_media(
            hass, f"{ROOT}/{init_integration.entry_id}/preset/1", "media_player.sejour"
        )


async def test_artwork_proxy(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
) -> None:
    """Thumbnails are fetched from the player and served by Home Assistant."""
    eid = init_integration.entry_id
    item = await async_browse_media(hass, f"{ROOT}/{eid}/recent")
    player_api.mock_calls.clear()
    client = await hass_client()

    response = await client.get(item.children[0].thumbnail)

    assert response.status == 200
    assert response.content_type == "image/jpeg"
    assert await response.read() == b"image"
    assert calls(player_api) == [
        (
            "/Artwork",
            {"service": "LocalMusic", "album": "Definitely Maybe", "artist": "Oasis"},
        )
    ]


@pytest.mark.parametrize(
    ("entry_id", "path", "status"),
    [
        pytest.param("{eid}", "relative", 404, id="relative-path"),
        pytest.param("{eid}", "", 404, id="missing-path"),
        pytest.param("unknown", "/Artwork", 404, id="unknown-entry"),
        pytest.param("{eid}", "/Missing", 502, id="player-error"),
    ],
)
async def test_artwork_proxy_errors(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    hass_client: ClientSessionGenerator,
    entry_id: str,
    path: str,
    status: int,
) -> None:
    """Bad requests and player failures are not proxied."""
    player_api.get(f"{BASE}/Missing", status=404)
    client = await hass_client()
    response = await client.get(
        f"/api/{DOMAIN}/{entry_id.format(eid=init_integration.entry_id)}/artwork",
        params={"path": path},
    )
    assert response.status == status
    assert [call for call in calls(player_api) if call[0] == "/Artwork"] == []


async def test_artwork_proxy_requires_auth(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    hass_client_no_auth: ClientSessionGenerator,
) -> None:
    """Unsigned, unauthenticated requests are refused."""
    client = await hass_client_no_auth()
    response = await client.get(
        f"/api/{DOMAIN}/{init_integration.entry_id}/artwork", params={"path": "/Artwork"}
    )
    assert response.status == 401
