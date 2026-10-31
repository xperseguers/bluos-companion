"""Switch on and off the amplifier a player is built into."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BluOSError
from .const import AMPLIFIER_PORT, AMPLIFIER_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

READ_TIMEOUT = 5
# The amplifier answers a power on only when it is up, which takes a few seconds
POWER_ON_TIMEOUT = 15
DETECT_TIMEOUT = 3


class AmplifierError(BluOSError):
    """Raised when the amplifier cannot be reached or answers unexpectedly."""


class AmplifierClient:
    """Talk to an amplifier through its network control, one short connection per request."""

    def __init__(self, host: str, port: int = AMPLIFIER_PORT) -> None:
        """Initialize the client."""
        self._host = host
        self._port = port

    async def _async_ask(self, command: str, prefix: str, timeout: float) -> str:
        """Send a command and return what follows `prefix` in the line that answers it.

        The amplifier greets with a line of its own, which is skipped.
        """
        try:
            async with asyncio.timeout(timeout):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                try:
                    writer.write(f"\r{command}\r".encode())
                    await writer.drain()
                    while raw := await reader.readline():
                        line = raw.decode(errors="replace").strip()
                        if line.startswith(prefix):
                            return line[len(prefix) :]
                    raise AmplifierError("The amplifier closed the connection")
                finally:
                    writer.close()
                    with contextlib.suppress(OSError):
                        await writer.wait_closed()
        except (OSError, TimeoutError) as err:
            raise AmplifierError(str(err) or type(err).__name__) from err

    async def async_get_power(self, timeout: float = READ_TIMEOUT) -> bool:
        """Return whether the amplifier is on (not in standby)."""
        return await self._async_ask("Main.Power?", "Main.Power=", timeout) == "On"

    async def async_set_power(self, on: bool) -> bool:
        """Switch the amplifier on or off and return the state it reports."""
        answer = await self._async_ask(
            f"Main.Power={'On' if on else 'Off'}",
            "Main.Power=",
            POWER_ON_TIMEOUT if on else READ_TIMEOUT,
        )
        return answer == "On"


class BluOSAmplifier(DataUpdateCoordinator[bool]):
    """Keep the power state of the amplifier of a player up to date."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: AmplifierClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} amplifier",
            update_interval=timedelta(seconds=AMPLIFIER_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> bool:
        try:
            return await self.client.async_get_power()
        except AmplifierError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_power(self, on: bool) -> None:
        """Switch the amplifier on or off."""
        try:
            self.async_set_updated_data(await self.client.async_set_power(on))
        except AmplifierError as err:
            raise HomeAssistantError(f"Amplifier error: {err}") from err


async def async_detect_amplifier(
    hass: HomeAssistant, entry: ConfigEntry, host: str, port: int = AMPLIFIER_PORT
) -> BluOSAmplifier | None:
    """Return the amplifier of a player, or None if it does not answer on its control port."""
    client = AmplifierClient(host, port)
    try:
        power = await client.async_get_power(DETECT_TIMEOUT)
    except AmplifierError:
        return None
    amplifier = BluOSAmplifier(hass, entry, client)
    amplifier.async_set_updated_data(power)
    return amplifier
