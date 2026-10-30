"""Maintenance buttons of a player."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import BluOSError
from .const import DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator


@dataclass(frozen=True, kw_only=True)
class BluOSButtonDescription(ButtonEntityDescription):
    """A button and what it asks of the player."""

    press_fn: Callable[[BluOSCoordinator], Awaitable[None]]


BUTTONS = (
    BluOSButtonDescription(
        key="reindex",
        translation_key="reindex",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_reindex(),
    ),
    BluOSButtonDescription(
        key="restart",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda coordinator: coordinator.client.async_reboot(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons of the player."""
    async_add_entities(BluOSButton(entry.runtime_data, description) for description in BUTTONS)


class BluOSButton(ButtonEntity):
    """Ask the player to reindex its library or to restart."""

    _attr_has_entity_name = True
    entity_description: BluOSButtonDescription

    def __init__(self, coordinator: BluOSCoordinator, description: BluOSButtonDescription) -> None:
        """Initialize the entity."""
        self.entity_description = description
        self._coordinator = coordinator
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)

    async def async_press(self) -> None:
        """Press the button."""
        try:
            await self.entity_description.press_fn(self._coordinator)
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err
