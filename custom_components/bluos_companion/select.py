"""Sleep timer of a BluOS player."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SLEEP_OPTIONS, BluOSError, sleep_bucket
from .const import DOMAIN
from .coordinator import BluOSConfigEntry, BluOSCoordinator
from .api import PlayerSetting
from .settings import BluOSSettingEntity, BluOSSettingsCoordinator

OFF = "off"
OPTIONS = [OFF, *(str(minutes) for minutes in SLEEP_OPTIONS)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BluOSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sleep timer."""
    settings = entry.runtime_data.settings
    async_add_entities(
        [
            BluOSSleepTimer(entry.runtime_data),
            *(
                BluOSSettingSelect(settings, setting)
                for setting in (settings.data or {}).values()
                if setting.kind == "list"
            ),
        ]
    )


class BluOSSleepTimer(CoordinatorEntity[BluOSCoordinator], SelectEntity):
    """Turn the player off after a delay."""

    _attr_has_entity_name = True
    _attr_translation_key = "sleep_timer"
    _attr_icon = "mdi:sleep"
    _attr_options = OPTIONS

    def __init__(self, coordinator: BluOSCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        identifier = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{identifier}_sleep_timer"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, identifier)}, name=entry.title)

    @property
    def current_option(self) -> str:
        """Return the delay set, rounded up to the closest option."""
        minutes = sleep_bucket(self.coordinator.data.sleep)
        return str(minutes) if minutes else OFF

    async def async_select_option(self, option: str) -> None:
        """Set the sleep timer."""
        try:
            await self.coordinator.client.async_set_sleep(
                0 if option == OFF else int(option)
            )
        except BluOSError as err:
            raise HomeAssistantError(f"BluOS player error: {err}") from err


class BluOSSettingSelect(BluOSSettingEntity, SelectEntity):
    """A setting with a few choices, such as the listening mode."""

    def __init__(self, coordinator: BluOSSettingsCoordinator, setting: PlayerSetting) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, setting)
        self._labels = dict(setting.options)
        self._attr_options = [label for _, label in setting.options]

    @property
    def current_option(self) -> str | None:
        """Return the label of the current choice."""
        return self._labels.get(self.setting.value) if self.setting else None

    async def async_select_option(self, option: str) -> None:
        """Choose one of the options."""
        value = next((name for name, label in self._labels.items() if label == option), None)
        if value is None:
            raise HomeAssistantError(f"Unknown option: {option}")
        await self._async_write(value)
