"""BluOS Companion."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .amplifier import async_detect_amplifier
from .api import BluOSClient, BluOSError
from .const import CONF_PORT, DOMAIN, ICONS_URL
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .http import BluOSArtworkView
from .panel import (
    async_register_card,
    async_register_panel,
    async_register_static_path,
    async_remove_panel,
)
from .playlist_backup import async_backup_playlists, async_restore_playlists
from .websocket_api import async_setup_websocket_api

PLATFORMS = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


_LOGGER = logging.getLogger(__name__)


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

    def loaded_entry(entity_id: str) -> BluOSConfigEntry:
        """Return the config entry of the player an entity belongs to."""
        entity = er.async_get(hass).async_get(entity_id)
        entry = (
            hass.config_entries.async_get_entry(entity.config_entry_id)
            if entity and entity.config_entry_id
            else None
        )
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise HomeAssistantError("Choose a BluOS Companion player")
        return entry

    async def restore_playlists(call: ServiceCall) -> dict[str, object]:
        """Rebuild playlists on a player from the text files."""
        return await async_restore_playlists(
            hass,
            loaded_entry(call.data["entity_id"]),
            call.data.get("playlists"),
            call.data["replace"],
        )

    async def check_covers(call: ServiceCall) -> dict[str, object]:
        """List the albums whose cover is too large for the player to show."""
        check = await loaded_entry(call.data["entity_id"]).runtime_data.async_check_covers()
        return {
            "checked": check.checked,
            "unreadable_covers": check.errors,
            "too_large": [
                {"artist": album.artist, "album": album.title} for album in check.too_large
            ],
        }

    hass.services.async_register(
        DOMAIN,
        "backup_playlists",
        backup_playlists,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        "restore_playlists",
        restore_playlists,
        schema=vol.Schema(
            {
                vol.Required("entity_id"): cv.entity_id,
                vol.Optional("playlists"): vol.All(cv.ensure_list, [str]),
                vol.Optional("replace", default=False): bool,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        "check_covers",
        check_covers,
        schema=vol.Schema({vol.Required("entity_id"): cv.entity_id}),
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
    await _async_register_device(hass, entry, client)
    coordinator.amplifier = await async_detect_amplifier(hass, entry, entry.data[CONF_HOST])
    # Not every player has settings, and none is needed to play: never block the setup
    await coordinator.settings.async_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass)
    entry.async_create_background_task(
        hass, coordinator.async_long_poll(), "bluos_companion_long_poll"
    )
    return True


async def _async_register_device(
    hass: HomeAssistant, entry: BluOSConfigEntry, client: BluOSClient
) -> None:
    """Describe the device with what the player reports (brand, model, firmware, MAC)."""
    try:
        info = await client.async_get_player_info()
    except BluOSError as err:
        _LOGGER.debug("Cannot read the identity of %s: %s", entry.title, err)
        return
    mac = dr.format_mac(info.mac)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        name=entry.title,
        manufacturer=info.brand or None,
        model=info.model or None,
        sw_version=info.version or None,
        configuration_url=f"http://{entry.data[CONF_HOST]}",
    )


async def async_migrate_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Normalise the MAC address used as unique ID, keeping the entities and the device."""
    if entry.minor_version < 2:
        old = entry.unique_id
        new = dr.format_mac(old) if old else old
        if old and new != old:

            @callback
            def migrate(entity: er.RegistryEntry) -> dict[str, str] | None:
                """Move the entities of the player to the new unique ID."""
                if entity.unique_id.startswith(old):
                    return {"new_unique_id": new + entity.unique_id[len(old) :]}
                return None

            await er.async_migrate_entries(hass, entry.entry_id, migrate)
            registry = dr.async_get(hass)
            for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
                if (DOMAIN, old) in device.identifiers:
                    registry.async_update_device(
                        device.id, new_identifiers={(DOMAIN, new)}
                    )
        hass.config_entries.async_update_entry(entry, unique_id=new, minor_version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BluOSConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_loaded_entries(DOMAIN):
        async_remove_panel(hass)
    return unloaded
