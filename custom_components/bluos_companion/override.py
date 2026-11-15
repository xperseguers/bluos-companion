"""Volume, inputs and power of a player that are those of other entities (an amplifier it feeds)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_POWER_ENTITY, CONF_SOURCE_ENTITY, CONF_VOLUME_ENTITY

UNKNOWN_STATES = ("unavailable", "unknown")
OFF_STATES = ("off", "standby")
ACTIONS = ("volume", "volume_step", "mute", "source", "power")


def override_entities(entry: ConfigEntry) -> dict[str, str]:
    """Return the entities chosen in the options, by option name."""
    return {
        key: entry.options[key]
        for key in (CONF_VOLUME_ENTITY, CONF_SOURCE_ENTITY, CONF_POWER_ENTITY)
        if entry.options.get(key)
    }


def override_snapshot(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return the fields of the state of a player that the entities replace."""
    chosen = override_entities(entry)
    fields: dict[str, Any] = {}
    if CONF_VOLUME_ENTITY in chosen:
        state = hass.states.get(chosen[CONF_VOLUME_ENTITY])
        level = state.attributes.get("volume_level") if state else None
        fields.update(
            volume=round(level * 100) if isinstance(level, int | float) else -1,
            muted=bool(state and state.attributes.get("is_volume_muted")),
            max_volume=100,
        )
    if CONF_SOURCE_ENTITY in chosen:
        state = hass.states.get(chosen[CONF_SOURCE_ENTITY])
        names = state.attributes.get("source_list") if state else None
        fields.update(
            sources=list(names) if isinstance(names, list) else [],
            source=state.attributes.get("source") if state else None,
        )
    if CONF_POWER_ENTITY in chosen:
        state = hass.states.get(chosen[CONF_POWER_ENTITY])
        fields["power"] = (
            None
            if state is None or state.state in UNKNOWN_STATES
            else state.state not in OFF_STATES
        )
    return fields


async def async_override_control(
    hass: HomeAssistant, entry: ConfigEntry, action: str, value: Any
) -> bool:
    """Do what the entities stand for; return False if the player itself has to do it."""
    chosen = override_entities(entry)
    if action in ("volume", "volume_step", "mute") and CONF_VOLUME_ENTITY in chosen:
        entity_id = chosen[CONF_VOLUME_ENTITY]
        if action == "mute":
            await hass.services.async_call(
                "media_player",
                "volume_mute",
                {"entity_id": entity_id, "is_volume_muted": bool(value)},
                blocking=True,
            )
            return True
        level = int(value)
        if action == "volume_step":
            state = hass.states.get(entity_id)
            current = state.attributes.get("volume_level") if state else None
            level += round(current * 100) if isinstance(current, int | float) else 0
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": entity_id, "volume_level": min(max(level, 0), 100) / 100},
            blocking=True,
        )
        return True
    if action == "source" and CONF_SOURCE_ENTITY in chosen:
        await hass.services.async_call(
            "media_player",
            "select_source",
            {"entity_id": chosen[CONF_SOURCE_ENTITY], "source": str(value)},
            blocking=True,
        )
        return True
    if action == "power" and CONF_POWER_ENTITY in chosen:
        entity_id = chosen[CONF_POWER_ENTITY]
        await hass.services.async_call(
            "media_player" if entity_id.startswith("media_player.") else "homeassistant",
            "turn_on" if value else "turn_off",
            {"entity_id": entity_id},
            blocking=True,
        )
        return True
    return False
