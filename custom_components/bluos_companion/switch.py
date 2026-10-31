"""On/off settings of a player, and the power of the amplifier it is built into."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .amplifier import BluOSAmplifier
from .const import DOMAIN
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
    if amplifier := entry.runtime_data.amplifier:
        # An amplifier without a speaker output does not report it: no switch for it
        async_add_entities(
            BluOSAmplifierSwitch(amplifier, name)
            for name in ("power", "speaker_a", "speaker_b")
            if getattr(amplifier.data, name) is not None
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


class BluOSAmplifierSwitch(CoordinatorEntity[BluOSAmplifier], SwitchEntity):
    """A function of the amplifier the player is built into: its power or a speaker output.

    The player itself stays reachable while the amplifier is in standby, and starting
    playback wakes the amplifier.
    """

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: BluOSAmplifier, name: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._name = name
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_amplifier_{name}"
        self._attr_translation_key = f"amplifier_{name}"
        if name != "power":
            self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)

    @property
    def is_on(self) -> bool | None:
        """Return whether the function is on."""
        return getattr(self.coordinator.data, self._name)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch it on."""
        await self.coordinator.async_set(self._name, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch it off (standby for the power)."""
        await self.coordinator.async_set(self._name, False)
