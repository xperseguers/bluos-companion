"""Tests for the config flow."""

from __future__ import annotations

from collections.abc import Generator
from ipaddress import ip_address
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.bluos_companion import async_migrate_entry
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
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PORT: 11000}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Séjour"
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 11000}
    assert result["result"].unique_id == format_mac(MAC)


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


def _discovery(host: str = HOST) -> ZeroconfServiceInfo:
    """Return the announcement of a player."""
    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="sejour.local.",
        name="Séjour._musc._tcp.local.",
        port=11000,
        properties={},
        type="_musc._tcp.local.",
    )


async def test_zeroconf_flow(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A discovered player is added after a confirmation."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_discovery()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 11000}
    assert result["result"].unique_id == format_mac(MAC)


async def test_zeroconf_updates_host_of_known_player(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    """A known player announced on a new address is not offered again."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get("http://192.168.1.101:11000/SyncStatus", text=SYNC_STATUS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_discovery("192.168.1.101")
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.1.101"


@pytest.mark.parametrize(
    ("host", "mock_kwargs", "reason"),
    [
        ("fe80::1", {}, "no_ipv4_address"),
        (HOST, {"exc": aiohttp.ClientError}, "cannot_connect"),
    ],
)
async def test_zeroconf_aborts(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    host: str,
    mock_kwargs: dict[str, Any],
    reason: str,
) -> None:
    """An IPv6 or unreachable player is not offered."""
    aioclient_mock.get(f"{BASE}/SyncStatus", **mock_kwargs)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_discovery(host)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_official_players_are_offered(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The players of the Bluesound integration can be picked instead of typed."""
    MockConfigEntry(
        domain="bluesound",
        unique_id="aa:bb:cc:dd:ee:ff-11000",
        title="Séjour",
        data={CONF_HOST: HOST, CONF_PORT: 11000},
    ).add_to_hass(hass)
    aioclient_mock.get(f"{BASE}/SyncStatus", text=SYNC_STATUS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["manual", "official"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "official"}
    )
    assert result["step_id"] == "official"
    selector = result["data_schema"].schema["player"]
    assert [option["label"] for option in selector.config["options"]] == [
        f"Séjour ({HOST})"
    ]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"player": selector.config["options"][0]["value"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_PORT: 11000}


async def test_official_players_already_added_are_not_offered(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """A player that is already set up goes straight to the address form."""
    config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain="bluesound",
        unique_id="aa:bb:cc:dd:ee:ff-11000",
        title="Séjour",
        data={CONF_HOST: HOST, CONF_PORT: 11000},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "manual"


async def test_migrate_unique_id(hass: HomeAssistant) -> None:
    """An entry with a raw MAC address moves, with its entities, to the normalised one."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=MAC, data={CONF_HOST: HOST, CONF_PORT: 11000}
    )
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    for platform, unique_id in (("media_player", MAC), ("select", f"{MAC}_sleep_timer")):
        registry.async_get_or_create(
            platform, DOMAIN, unique_id, config_entry=entry
        )
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, MAC)}
    )

    assert await async_migrate_entry(hass, entry)

    new = format_mac(MAC)
    assert (entry.unique_id, entry.minor_version) == (new, 2)
    assert registry.async_get_entity_id("media_player", DOMAIN, new)
    assert registry.async_get_entity_id("select", DOMAIN, f"{new}_sleep_timer")
    assert dr.async_get(hass).async_get(device.id).identifiers == {(DOMAIN, new)}

