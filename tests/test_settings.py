"""Tests for the settings of a player."""

from __future__ import annotations

import pytest
from homeassistant.components.number import ATTR_VALUE, DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.api import BluOSClient

from .conftest import BASE, calls, respond

AUDIO = """<settings pageId="audio" schemaVersion="36">
<menuGroup id="audio" url="http://x:11000/audiomodes">
 <menuGroup id="audioPreset" url="http://x:11000/alsa_setting">
  <setting id="preset" name="preset" displayName="Listening Mode" url="http://x:11000/alsa_setting" class="list" value="MUSIC">
   <value displayName="TV" name="TV"></value><value displayName="Music" name="MUSIC"></value>
  </setting>
  <setting id="eq-bass" name="eq-bass" displayName="Bass" url="http://x:11000/alsa_setting" class="range" value="0.5">
   <value min="-6" max="6" step="0.5" units="dB"></value>
  </setting>
  <setting id="eq-late_night" name="eq-late_night" displayName="Late Night" url="http://x:11000/alsa_setting" class="boolean" value="OFF"></setting>
  <setting id="reset" name="resetPreset" displayName="Reset" url="/alsa_setting" class="button"></setting>
 </menuGroup>
 <setting id="volumeLimits" name="volumeLimits" displayName="Volume limits" url="/audiomodes" class="dual-range" value="-70,0"></setting>
</menuGroup></settings>"""
PLAYER = """<settings pageId="player" schemaVersion="36"><menuGroup id="player">
<setting id="nodename" name="nodename" displayName="Room name" url="/Name" class="text" value="Séjour"></setting>
<setting id="ledbrightness" name="ledbrightness" displayName="Indicator brightness" url="/setting" class="list" value="dim">
 <value displayName="Normal" name="default"></value><value displayName="Dim" name="dim"></value>
</setting></menuGroup></settings>"""


@pytest.fixture
def settings_api(player_api: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the settings pages of the player."""
    respond(player_api, f"{BASE}/Settings?id=audio&schemaVersion=36", text=AUDIO)
    respond(player_api, f"{BASE}/Settings?id=player&schemaVersion=36", text=PLAYER)
    respond(player_api, f"{BASE}/alsa_setting", text="")
    respond(player_api, f"{BASE}/setting", text="")
    return player_api


async def test_settings_are_parsed(
    client: BluOSClient, settings_api: AiohttpClientMocker
) -> None:
    """Only list, on/off and range settings are kept, with what is needed to show them."""
    settings = await client.async_get_settings()
    assert list(settings) == ["preset", "eq-bass", "eq-late_night", "ledbrightness"]
    assert settings["preset"].options == (("TV", "TV"), ("MUSIC", "Music"))
    bass = settings["eq-bass"]
    assert (bass.minimum, bass.maximum, bass.step, bass.unit, bass.value) == (-6, 6, 0.5, "dB", "0.5")


@pytest.mark.usefixtures("settings_api")
async def test_setting_entities(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The common settings are enabled, the others wait to be enabled by the user."""
    assert hass.states.get("select.sejour_listening_mode").state == "Music"
    assert float(hass.states.get("number.sejour_bass").state) == 0.5
    registry = er.async_get(hass)
    for domain, setting in (("switch", "eq-late_night"), ("select", "ledbrightness")):
        entity_id = registry.async_get_entity_id(
            domain, "bluos_companion", f"{init_integration.unique_id}_setting_{setting}"
        )
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_changing_settings(
    hass: HomeAssistant, settings_api: AiohttpClientMocker, init_integration: MockConfigEntry
) -> None:
    """A choice and a number are sent to the address the player gave for them."""
    settings_api.mock_calls.clear()
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {"entity_id": "select.sejour_listening_mode", ATTR_OPTION: "TV"},
        blocking=True,
    )
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {"entity_id": "number.sejour_bass", ATTR_VALUE: -1.5},
        blocking=True,
    )
    writes = [call for call in calls(settings_api) if call[0] == "/alsa_setting"]
    assert writes == [("/alsa_setting", {"preset": "TV"}), ("/alsa_setting", {"eq-bass": "-1.5"})]
