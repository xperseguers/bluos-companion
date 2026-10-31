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
    async_add_entities([BluOSLibraryTracks(entry.runtime_data), BluOSCoversTooLarge(entry.runtime_data)])


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


# A state attribute may not be larger than the recorder keeps (16 KiB)
MAX_LISTED_ALBUMS = 25
CHECK_ATTRIBUTES = ("albums", "checked_albums", "unreadable_covers", "checked_at")


class BluOSCoversTooLarge(CoordinatorEntity[BluOSCoordinator], RestoreSensor):
    """Number of albums whose cover the player refuses to show because it is too large.

    Unknown until the covers have been checked with the service
    bluos_companion.check_covers, then the result of the last check.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "covers_too_large"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BluOSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_covers_too_large"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)
        self._restored: int | None = None
        self._restored_attributes: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Bring back the result of the last check, with its albums, after a restart."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._restored = (
                int(last.native_value) if isinstance(last.native_value, (int, float)) else None
            )
        if (state := await self.async_get_last_state()) is not None:
            self._restored_attributes = {
                key: value for key, value in state.attributes.items() if key in CHECK_ATTRIBUTES
            }

    @property
    def native_value(self) -> int | None:
        """Return how many albums have a cover that is too large."""
        if (check := self.coordinator.cover_check) is not None:
            return len(check.too_large)
        return self._restored

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the albums, and how far the last check went."""
        attributes: dict[str, Any] = {"checking": self.coordinator.checking_covers}
        if self.coordinator.cover_check is None:
            return attributes | self._restored_attributes
        if (check := self.coordinator.cover_check) is not None:
            attributes |= {
                "albums": [
                    f"{album.artist} - {album.title}" for album in check.too_large[:MAX_LISTED_ALBUMS]
                ],
                "checked_albums": check.checked,
                "unreadable_covers": check.errors,
                "checked_at": check.checked_at.isoformat(),
            }
        return attributes
