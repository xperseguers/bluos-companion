"""Tests for playing a genre of the library."""

from __future__ import annotations

import pytest
from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.api import genre_play_path
from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, calls, respond

ENTITY_ID = "media_player.sejour"
GENRES = (
    '<genres service="LocalMusic"><genre>Dance</genre><genre>Eurodance</genre>'
    "<genre>Acid Jazz</genre><genre>Jazz</genre><genre>Chanson française</genre>"
    "<genre>Folk, World, &amp; Country</genre><genre>Alternative</genre>"
    "<genre>Alternative &amp; Punk</genre><genre>French Pop</genre><genre>Latin Pop</genre></genres>"
)


@pytest.fixture(autouse=True)
def genres(player_api: AiohttpClientMocker) -> None:
    """The library has a few genres."""
    respond(player_api, f"{BASE}/Genres", text=GENRES)


def test_the_play_path_of_a_genre() -> None:
    """The path is the one of Play now, or of Shuffle."""
    assert genre_play_path("Dance") == (
        "/Add?clear=0&genre=Dance&playnow=1&service=LocalMusic&shuffle=0"
    )
    assert genre_play_path("Dance", shuffle=True) == (
        "/Add?genre=Dance&playnow=1&service=LocalMusic&shuffle=1"
    )


@pytest.mark.parametrize(
    ("genre", "shuffle", "expected"),
    [
        ("Dance", False, {"clear": "0", "genre": "Dance", "shuffle": "0"}),
        ("dance", True, {"genre": "Dance", "shuffle": "1"}),
        ("chanson francaise", False, {"clear": "0", "genre": "Chanson française", "shuffle": "0"}),
        ("country", False, {"clear": "0", "genre": "Folk, World, & Country", "shuffle": "0"}),
        ("acid", False, {"clear": "0", "genre": "Acid Jazz", "shuffle": "0"}),
    ],
)
async def test_the_service_plays_a_genre(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    genre: str,
    shuffle: bool,
    expected: dict[str, str],
) -> None:
    """A genre is found by its name, without case or accents, or by a word of it."""
    await hass.services.async_call(
        DOMAIN,
        "play_genre",
        {"entity_id": ENTITY_ID, "genre": genre, "shuffle": shuffle},
        blocking=True,
    )
    assert calls(player_api) == [
        ("/Genres", {"service": "LocalMusic"}),
        ("/Add", {"playnow": "1", "service": "LocalMusic"} | expected),
    ]


async def test_an_unknown_genre_is_an_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """An unknown genre is an error and nothing starts."""
    with pytest.raises(HomeAssistantError, match="Unknown genre: Metal"):
        await hass.services.async_call(
            DOMAIN, "play_genre", {"entity_id": ENTITY_ID, "genre": "Metal"}, blocking=True
        )
    assert calls(player_api) == [("/Genres", {"service": "LocalMusic"})]


async def test_the_exact_name_wins_over_the_genres_that_contain_it(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """"Alternative" is a genre of its own, not ambiguous with "Alternative & Punk"."""
    await hass.services.async_call(
        DOMAIN, "play_genre", {"entity_id": ENTITY_ID, "genre": "alternative"}, blocking=True
    )
    assert calls(player_api)[-1][1]["genre"] == "Alternative"


async def test_a_word_in_several_genres_is_ambiguous(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A word that fits several genres asks for a precise one."""
    with pytest.raises(HomeAssistantError, match="ambiguous.*French Pop, Latin Pop"):
        await hass.services.async_call(
            DOMAIN, "play_genre", {"entity_id": ENTITY_ID, "genre": "pop"}, blocking=True
        )


async def test_play_media_plays_a_genre(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """media_player.play_media with the type genre plays the genre."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_PLAY_MEDIA,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_MEDIA_CONTENT_TYPE: "genre",
            ATTR_MEDIA_CONTENT_ID: "Dance",
        },
        blocking=True,
    )
    assert calls(player_api)[-1] == (
        "/Add",
        {"clear": "0", "genre": "Dance", "playnow": "1", "service": "LocalMusic", "shuffle": "0"},
    )


async def test_a_failing_player_is_an_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player that cannot be reached raises a readable error."""
    respond(player_api, f"{BASE}/Genres", status=500)
    with pytest.raises(HomeAssistantError, match="BluOS player error"):
        await hass.services.async_call(
            DOMAIN, "play_genre", {"entity_id": ENTITY_ID, "genre": "Dance"}, blocking=True
        )
