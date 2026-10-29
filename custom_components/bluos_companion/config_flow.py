"""Config flow for Library Browser for BluOS."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import BluOSClient, BluOSError
from .const import (
    CONF_BACKUP_PLAYLISTS,
    CONF_HIDDEN_SERVICES,
    CONF_MAX_VOLUME,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
)


class BluOSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BluOSOptionsFlow:
        """Return the options flow."""
        return BluOSOptionsFlow()

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


class BluOSOptionsFlow(OptionsFlow):
    """Choose which services of the player the panel shows."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user hide the services they do not use."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **user_input,
                    CONF_MAX_VOLUME: int(user_input.get(CONF_MAX_VOLUME, 100)),
                    CONF_BACKUP_PLAYLISTS: user_input.get(CONF_BACKUP_PLAYLISTS, True),
                }
            )

        options = self.config_entry.options
        hidden = options.get(CONF_HIDDEN_SERVICES, [])
        client = BluOSClient(
            async_get_clientsession(self.hass),
            self.config_entry.data[CONF_HOST],
            self.config_entry.data[CONF_PORT],
        )
        try:
            nodes = await client.async_browse(None)
        except BluOSError:
            nodes = []
        choices = {node.browse_key: node.title for node in nodes if node.browse_key}
        # Keep what is hidden selectable even if the player does not list it any more.
        choices.update({key: key for key in hidden if key not in choices})
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HIDDEN_SERVICES, default=hidden): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=key, label=label)
                                for key, label in choices.items()
                            ],
                            multiple=True,
                        )
                    ),
                    vol.Optional(
                        CONF_MAX_VOLUME, default=options.get(CONF_MAX_VOLUME, 100)
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=10, max=100, step=1, mode=NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional(
                        CONF_BACKUP_PLAYLISTS,
                        default=options.get(CONF_BACKUP_PLAYLISTS, True),
                    ): BooleanSelector(),
                }
            ),
        )
