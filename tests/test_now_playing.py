"""Tests for the answer to what is playing."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import DOMAIN

from .conftest import BASE, GROUPED_SYNC_STATUS, calls, respond, status_xml

ENTITY_ID = "media_player.sejour"


async def _ask(hass: HomeAssistant) -> dict:
    response = await hass.services.async_call(
        DOMAIN, "now_playing", {"entity_id": ENTITY_ID}, blocking=True, return_response=True
    )
    return response


async def _refresh(
    hass: HomeAssistant, entry: MockConfigEntry, api: AiohttpClientMocker, xml: str
) -> None:
    respond(api, f"{BASE}/Status", text=xml)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_a_song(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The answer carries the data and a sentence a script can speak."""
    player_api.mock_calls.clear()
    answer = await _ask(hass)
    assert answer == {
        "player": "Séjour",
        "state": "playing",
        "text": "Rolling In the Deep by Adele",
        "title": "Rolling In the Deep",
        "channel": None,
        "artist": "Adele",
        "album": "21",
        "service": "LocalMusic",
        "service_name": None,
        "stream_format": None,
        "quality": None,
        "preset_name": None,
        "position": 10,
        "duration": 228,
        "queue_position": None,
        "shuffle": False,
        "repeat": "off",
        "volume": 25,
        "muted": False,
        "group_name": None,
        "grouped_with": [],
    }
    # Asking changes nothing and costs the player nothing: the status it already has is used
    assert calls(player_api) == []


async def test_a_station_has_no_artist(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A radio says its name, with what the player knows of the stream."""
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml(
            "stream",
            artist="",
            album="",
            name="Rouge FM",
            title1="Rouge FM",
            service="TuneIn",
            serviceName="TuneIn",
            streamFormat="AAC 128 kb/s",
            quality="128",
            preset_name="Rouge FM",
            song="2",
            shuffle="1",
            repeat="1",
        ),
    )
    answer = await _ask(hass)
    assert (answer["state"], answer["text"], answer["artist"]) == ("playing", "Rouge FM", None)
    assert (answer["stream_format"], answer["quality"], answer["preset_name"]) == (
        "AAC 128 kb/s",
        "128",
        "Rouge FM",
    )
    assert (answer["queue_position"], answer["shuffle"], answer["repeat"]) == (3, True, "one")


@pytest.mark.parametrize(
    ("language", "text"),
    [("en", "Nothing is playing"), ("fr", "Rien n'est en cours de lecture"), ("de", "Es läuft nichts")],
)
async def test_nothing_playing_is_said_in_the_language(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    language: str,
    text: str,
) -> None:
    """A stopped player says so, in the language of Home Assistant."""
    hass.config.language = language
    await _refresh(hass, init_integration, player_api, '<status etag="e2"><state>stop</state><volume>25</volume></status>')
    answer = await _ask(hass)
    assert (answer["state"], answer["text"], answer["title"]) == ("idle", text, None)


@pytest.mark.parametrize(
    ("language", "text"),
    [("fr", "Skyfall de Adele"), ("de", "Skyfall von Adele")],
)
async def test_the_sentence_is_translated(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    language: str,
    text: str,
) -> None:
    """"Title by artist" reads naturally in each language."""
    hass.config.language = language
    await _refresh(hass, init_integration, player_api, status_xml(title1="Skyfall", artist="Adele"))
    assert (await _ask(hass))["text"] == text


async def test_a_fixed_volume_is_none(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player whose volume is fixed has none to report."""
    await _refresh(hass, init_integration, player_api, status_xml(volume="-1"))
    assert (await _ask(hass))["volume"] is None


async def test_the_group_is_listed(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A player in a group says which one and with whom."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    # The player tells that its group changed with a new syncStat
    await _refresh(hass, init_integration, player_api, status_xml(syncStat="99"))
    answer = await _ask(hass)
    assert (answer["group_name"], answer["grouped_with"]) == ("Séjour+Pulse", ["Pulse"])


async def test_a_station_tells_what_is_on_air(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """A station is the channel, what it has on air (as sent, never split) is the title."""
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml(
            "stream",
            artist="",
            album="",
            name="Melody Radio Vintage",
            title1="Melody Radio Vintage",
            title2="AC - DC - BACK IN BLACK",
            serviceType="RadioService",
        ),
    )
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes["media_title"] == "AC - DC - BACK IN BLACK"
    assert attributes["media_channel"] == "Melody Radio Vintage"
    assert "media_artist" not in attributes
    answer = await _ask(hass)
    assert answer["text"] == "AC - DC - BACK IN BLACK on Melody Radio Vintage"
    assert (answer["title"], answer["channel"]) == ("AC - DC - BACK IN BLACK", "Melody Radio Vintage")


async def test_a_second_line_is_only_on_air_for_a_radio(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The second line of an input is not a track."""
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml("stream", artist="", album="", title1="Bluetooth", title2="Phone"),
    )
    attributes = hass.states.get(ENTITY_ID).attributes
    assert attributes["media_title"] == "Bluetooth"
    assert "media_channel" not in attributes


@pytest.mark.parametrize("line", ["-", " ", "", " - ", "9999999 - 9999999"])
async def test_a_station_between_two_songs_has_no_artist(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    line: str,
) -> None:
    """A lone dash, a blank line or digits only, sent by a station without a song, is not an artist."""
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml(
            "stream",
            artist="",
            album="",
            title1="Melody Radio Vintage",
            title2=line,
            serviceType="RadioService",
        ),
    )
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes["media_title"] == "Melody Radio Vintage"
