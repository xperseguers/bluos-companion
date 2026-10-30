"""Size of the music library of a player."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import RestoreSensor, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the library sensor."""
    async_add_entities([BluOSLibraryTracks(entry.runtime_data)])


# The player shows a count of 1 for a second when it is asked to reindex, whether it scans or not
MIN_SCAN_COUNT = 100


class BluOSLibraryTracks(CoordinatorEntity[BluOSCoordinator], RestoreSensor):
    """Number of tracks the player found when it last read its library.

    The player only counts the tracks while it reads the library and forgets the
    number afterwards, so the last count seen is kept.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "library_tracks"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BluOSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_library_tracks"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)
        self._attr_native_value: int | None = None
        self._counted = 0

    async def async_added_to_hass(self) -> None:
        """Bring back the last count after a restart."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = (
                int(last.native_value) if isinstance(last.native_value, (int, float)) else None
            )

    def _handle_coordinator_update(self) -> None:
        indexing = self.coordinator.data.indexing if self.coordinator.data else 0
        if indexing:
            self._counted = indexing
        elif self._counted:
            # The scan is over: the last count is the number of tracks
            if self._counted >= MIN_SCAN_COUNT:
                self._attr_native_value = self._counted
            self._counted = 0
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return how far a running scan is."""
        return {"indexing": self._counted or None}
