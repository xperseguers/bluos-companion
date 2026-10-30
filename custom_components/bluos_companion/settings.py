"""Settings of a player: listening mode, tone controls, indicator brightness..."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .api import BluOSClient, BluOSError, PlayerSetting
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)
# The other settings are there but disabled until the user asks for them.
ENABLED_BY_DEFAULT = {"preset", "eq-bass", "eq-treble"}


class BluOSSettingsCoordinator(DataUpdateCoordinator[dict[str, PlayerSetting]]):
    """Read the settings of a player, which do not push their changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: BluOSClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} settings", update_interval=SCAN_INTERVAL
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, PlayerSetting]:
        try:
            return await self.client.async_get_settings()
        except BluOSError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set(self, setting: PlayerSetting, value: str) -> None:
        """Change a setting and read all of them again."""
        try:
            await self.client.async_set_setting(setting, value)
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err
        await self.async_refresh()


class BluOSSettingEntity(CoordinatorEntity[BluOSSettingsCoordinator]):
    """A setting of the player, shown with the name the player gives it."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: BluOSSettingsCoordinator, setting: PlayerSetting) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._setting_id = setting.id
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_setting_{setting.id}"
        self._attr_name = setting.label
        self._attr_entity_registry_enabled_default = setting.id in ENABLED_BY_DEFAULT
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)

    @property
    def setting(self) -> PlayerSetting | None:
        """Return the setting as the player last reported it."""
        return (self.coordinator.data or {}).get(self._setting_id)

    @property
    def available(self) -> bool:
        """Return whether the player still has this setting."""
        return super().available and self.setting is not None

    async def _async_write(self, value: str) -> None:
        if (setting := self.setting) is None:
            raise HomeAssistantError("This setting is not available now")
        await self.coordinator.async_set(setting, value)


def async_setting_coordinator(entry: ConfigEntry) -> BluOSSettingsCoordinator:
    """Return the settings coordinator of an entry."""
    return entry.runtime_data.settings
