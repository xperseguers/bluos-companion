"""BluOS Companion."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BluOSClient
from .const import CONF_PORT
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .http import BluOSArtworkView

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Set up a player from a config entry."""
    client = BluOSClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_PORT]
    )
    coordinator = BluOSCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    hass.http.register_view(BluOSArtworkView())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_create_background_task(
        hass, coordinator.async_long_poll(), "bluos_companion_long_poll"
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
