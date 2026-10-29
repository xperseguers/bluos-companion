"""BluOS Companion."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import BluOSClient
from .const import CONF_PORT, DOMAIN, ICONS_URL
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .http import BluOSArtworkView
from .panel import (
    async_register_card,
    async_register_panel,
    async_register_static_path,
    async_remove_panel,
)
from .playlist_backup import async_backup_playlists
from .websocket_api import async_setup_websocket_api

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SELECT]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the browse icons and the artwork proxy."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(ICONS_URL, str(Path(__file__).parent / "icons"), True)]
    )
    hass.http.register_view(BluOSArtworkView())
    await async_register_static_path(hass)
    async_register_card(hass)
    async_setup_websocket_api(hass)

    async def backup_playlists(call: ServiceCall) -> dict[str, dict[str, int]]:
        """Save the playlists as text files, as before every Home Assistant backup."""
        return {"playlists": await async_backup_playlists(hass)}

    hass.services.async_register(
        DOMAIN,
        "backup_playlists",
        backup_playlists,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Set up a player from a config entry."""
    client = BluOSClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT]
    )
    coordinator = BluOSCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass)
    entry.async_create_background_task(
        hass, coordinator.async_long_poll(), "bluos_companion_long_poll"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        async_remove_panel(hass)
    return unloaded
