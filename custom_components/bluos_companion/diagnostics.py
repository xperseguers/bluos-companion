"""Diagnostics of a player."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .coordinator import BluOSConfigEntry

TO_REDACT = {CONF_HOST, "unique_id", "title", "id", "host", "name", "title1", "title2", "artist", "album", "image"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BluOSConfigEntry
) -> dict[str, Any]:
    """Return what helps to understand a problem, without addresses or names."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "entry": {
                "data": dict(entry.data),
                "options": dict(entry.options),
                "unique_id": entry.unique_id,
                "title": entry.title,
            },
            "status": asdict(coordinator.data) if coordinator.data else None,
            "sync": asdict(coordinator.sync) if coordinator.sync else None,
            "sources": [asdict(source) for source in coordinator.sources],
        },
        TO_REDACT,
    )
