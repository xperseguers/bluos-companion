"""Range settings of a player."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BluOSConfigEntry
from .settings import BluOSSettingEntity

from .api import PlayerSetting
from .settings import BluOSSettingsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the range settings of the player."""
    settings = entry.runtime_data.settings
    async_add_entities(
        BluOSSettingNumber(settings, setting)
        for setting in (settings.data or {}).values()
        if setting.kind == "range"
    )


class BluOSSettingNumber(BluOSSettingEntity, NumberEntity):
    """A setting with a range, such as bass or treble."""

    def __init__(self, coordinator: BluOSSettingsCoordinator, setting: PlayerSetting) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, setting)
        self._attr_native_min_value = setting.minimum
        self._attr_native_max_value = setting.maximum
        self._attr_native_step = setting.step
        self._attr_native_unit_of_measurement = setting.unit

    @property
    def native_value(self) -> float | None:
        """Return the value of the setting."""
        try:
            return float(self.setting.value) if self.setting else None
        except ValueError:
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Change the setting."""
        await self._async_write(f"{value:g}")
