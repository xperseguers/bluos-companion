"""On/off settings of a player, and the power of the amplifier it is built into."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .amplifier import BluOSAmplifier
from .api import BluOSError
from .const import DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .settings import BluOSSettingEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the on/off settings of the player."""
    coordinator = entry.runtime_data
    if coordinator.volume_level >= 0:
        # A player with a fixed volume cannot be muted
        async_add_entities([BluOSMuteSwitch(coordinator)])
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


class BluOSMuteSwitch(CoordinatorEntity[BluOSCoordinator], SwitchEntity):
    """The mute of the player itself, to flip with one tap (a media player has no toggle).

    In a group it is the mute of this player only, not of the group.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "mute"

    def __init__(self, coordinator: BluOSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_mute"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)

    @property
    def is_on(self) -> bool:
        """Return whether the player is muted."""
        return self.coordinator.is_muted

    async def _async_mute(self, mute: bool) -> None:
        try:
            await self.coordinator.client.async_set_mute(mute)
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mute the player."""
        await self._async_mute(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unmute the player."""
        await self._async_mute(False)


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
