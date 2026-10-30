"""On/off settings of a player."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BluOSConfigEntry
from .settings import BluOSSettingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the on/off settings of the player."""
    settings = entry.runtime_data.settings
    async_add_entities(
        BluOSSettingSwitch(settings, setting)
        for setting in (settings.data or {}).values()
        if setting.kind == "boolean"
    )


class BluOSSettingSwitch(BluOSSettingEntity, SwitchEntity):
    """A setting that is on or off, such as Late Night."""

    @property
    def is_on(self) -> bool | None:
        """Return whether the setting is on."""
        return self.setting.value == "ON" if self.setting else None

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn the setting on."""
        await self._async_write("ON")

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the setting off."""
        await self._async_write("OFF")
