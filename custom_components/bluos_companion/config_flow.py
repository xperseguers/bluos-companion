"""Config flow for Library Browser for BluOS."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BluOSClient, BluOSError
from .const import CONF_PORT, DEFAULT_PORT, DOMAIN


class BluOSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the address of the player."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = BluOSClient(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_PORT],
            )
            try:
                info = await client.async_get_player_info()
            except BluOSError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info.mac)
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(title=info.name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )
