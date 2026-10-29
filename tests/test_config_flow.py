"""Tests for the config flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion.const import CONF_PORT, DOMAIN

from .conftest import BASE, HOST, MAC, SYNC_STATUS


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[None]:
    """Do not set up the entry."""
    with patch("custom_components.bluos_companion.async_setup_entry", return_value=True):
        yield


async def test_user_flow(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A reachable player creates an entry named after the player."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 11000}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Séjour"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 11000}
    assert result["result"].unique_id == MAC


async def test_cannot_connect_then_recover(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The form is shown again with an error, and can be submitted again."""
    aioclient_mock.get(f"{BASE}/SyncStatus", exc=aiohttp.ClientError)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 11000}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 11000}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured_updates_host(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """The same player on a new address updates the existing entry."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get("http://192.168.1.101:11000/SyncStatus", text=SYNC_STATUS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.1.101", CONF_PORT: 11000}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.1.101"


async def test_options_hide_services(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The options list what the player offers and store what is hidden."""
    player_api.get(
        f"{BASE}/Browse",
        text='''<browse><item browseKey="LocalMusic:" text="Library" type="link"/>
<item browseKey="Deezer:" text="Deezer" type="link"/><item text="No key" type="audio"/></browse>''',
    )
    config_entry.add_to_hass(hass)
    with patch("custom_components.bluos_companion.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        selector = result["data_schema"].schema["hidden_services"]
        assert [option["value"] for option in selector.config["options"]] == [
            "LocalMusic:",
            "Deezer:",
        ]

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"hidden_services": ["Deezer:"], "max_volume": 60}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        "hidden_services": ["Deezer:"],
        "max_volume": 60,
        "backup_playlists": True,
    }
