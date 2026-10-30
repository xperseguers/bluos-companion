"""Config flow for Library Browser for BluOS."""

from __future__ import annotations

import ipaddress
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
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import BluOSClient, BluOSError, PlayerInfo
from .const import (
    CONF_BACKUP_PLAYLISTS,
    CONF_HIDDEN_SERVICES,
    CONF_MAX_VOLUME,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
)


OFFICIAL_DOMAIN = "bluesound"


class BluOSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._info: PlayerInfo | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BluOSOptionsFlow:
        """Return the options flow."""
        return BluOSOptionsFlow()

    def _official_players(self) -> dict[str, tuple[str, int]]:
        """Return the players of the Bluesound integration not added yet, by entry id.

        Disabled entries are included: they still know the address of the player.
        """
        known = {entry.unique_id for entry in self._async_current_entries(include_ignore=False)}
        players: dict[str, tuple[str, int]] = {}
        for entry in self.hass.config_entries.async_entries(OFFICIAL_DOMAIN):
            host = entry.data.get(CONF_HOST)
            if not host:
                continue
            mac = (entry.unique_id or "").rsplit("-", 1)[0]
            if mac and format_mac(mac) in known:
                continue
            players[entry.entry_id] = (host, entry.data.get(CONF_PORT, DEFAULT_PORT))
        return players

    async def _async_identify(self, host: str, port: int) -> PlayerInfo:
        """Contact the player and use its MAC address as the unique ID of the flow."""
        info = await BluOSClient(
            async_get_clientsession(self.hass), host, port
        ).async_get_player_info()
        await self.async_set_unique_id(format_mac(info.mac))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
        return info

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer the players known to the Bluesound integration, if any."""
        if self._official_players():
            return self.async_show_menu(step_id="user", menu_options=["manual", "official"])
        return await self.async_step_manual()

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the address of the player."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await self._async_identify(
                    user_input[CONF_HOST], user_input[CONF_PORT]
                )
            except BluOSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=info.name, data=user_input)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, vol.UNDEFINED)): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_official(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick one of the players of the Bluesound integration."""
        players = self._official_players()
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = players[user_input["player"]]
            try:
                info = await self._async_identify(host, port)
            except BluOSError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=info.name, data={CONF_HOST: host, CONF_PORT: port}
                )

        titles = {
            entry.entry_id: entry.title
            for entry in self.hass.config_entries.async_entries(OFFICIAL_DOMAIN)
        }
        return self.async_show_form(
            step_id="official",
            data_schema=vol.Schema(
                {
                    vol.Required("player"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=entry_id,
                                    label=f"{titles.get(entry_id, host)} ({host})",
                                )
                                for entry_id, (host, _) in players.items()
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Offer a player found on the network."""
        try:
            if ipaddress.ip_address(discovery_info.host).version != 4:
                return self.async_abort(reason="no_ipv4_address")
        except ValueError:
            return self.async_abort(reason="no_ipv4_address")
        self._host = discovery_info.host
        self._port = discovery_info.port or DEFAULT_PORT
        try:
            self._info = await self._async_identify(self._host, self._port)
        except BluOSError:
            return self.async_abort(reason="cannot_connect")
        self.context["title_placeholders"] = {"name": self._info.name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the player found on the network."""
        assert self._info is not None and self._host is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._info.name,
                data={CONF_HOST: self._host, CONF_PORT: self._port},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._info.name, "host": self._host},
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
