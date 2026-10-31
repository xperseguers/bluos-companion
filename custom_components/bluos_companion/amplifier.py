"""Switch on and off the amplifier a player is built into."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, replace
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


@dataclass(frozen=True, slots=True)
class AmplifierState:
    """What the amplifier reports: its power and its speaker outputs (None if it has none)."""

    power: bool
    speaker_a: bool | None = None
    speaker_b: bool | None = None


SPEAKERS = {"speaker_a": "Main.SpeakerA", "speaker_b": "Main.SpeakerB"}
POWER = "Main.Power"
# Once the power is known, the other answers come at once: do not wait long for an output it lacks
GRACE_TIMEOUT = 1


class AmplifierClient:
    """Talk to an amplifier through its network control, one short connection per request."""

    def __init__(self, host: str, port: int = AMPLIFIER_PORT) -> None:
        """Initialize the client."""
        self._host = host
        self._port = port

    async def _async_ask(
        self, commands: list[str], keys: list[str], timeout: float
    ) -> dict[str, str]:
        """Send commands and return the values answered for `keys`, by key.

        The amplifier greets with a line of its own, which is skipped. An output it
        does not have is not answered: after the first key, it is waited for briefly.
        """
        answers: dict[str, str] = {}
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), timeout
            )
            try:
                writer.write("".join(f"\r{command}\r" for command in commands).encode())
                await writer.drain()
                deadline = asyncio.get_running_loop().time() + timeout
                while not set(keys) <= answers.keys():
                    remaining = deadline - asyncio.get_running_loop().time()
                    if answers:
                        remaining = min(remaining, GRACE_TIMEOUT)
                    try:
                        raw = await asyncio.wait_for(reader.readline(), max(remaining, 0.01))
                    except TimeoutError:
                        break
                    if not raw:
                        break
                    key, _, value = raw.decode(errors="replace").strip().partition("=")
                    if key in keys:
                        answers[key] = value
            finally:
                writer.close()
                with contextlib.suppress(OSError):
                    await writer.wait_closed()
        except (OSError, TimeoutError) as err:
            raise AmplifierError(str(err) or type(err).__name__) from err
        if not answers:
            raise AmplifierError("The amplifier did not answer")
        return answers

    async def async_get_state(self, timeout: float = READ_TIMEOUT) -> AmplifierState:
        """Return the power and the speaker outputs of the amplifier."""
        answers = await self._async_ask(
            [f"{key}?" for key in (POWER, *SPEAKERS.values())], [POWER, *SPEAKERS.values()], timeout
        )
        if POWER not in answers:
            raise AmplifierError("The amplifier did not report its power")
        return AmplifierState(
            power=answers[POWER] == "On",
            **{name: answers[key] == "On" if key in answers else None for name, key in SPEAKERS.items()},
        )

    async def async_set(self, key: str, on: bool) -> bool:
        """Switch a function (the power or a speaker output) on or off and return its state."""
        answers = await self._async_ask(
            [f"{key}={'On' if on else 'Off'}"],
            [key],
            POWER_ON_TIMEOUT if on and key == POWER else READ_TIMEOUT,
        )
        return answers[key] == "On"


class BluOSAmplifier(DataUpdateCoordinator[AmplifierState]):
    """Keep the state of the amplifier of a player up to date."""

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

    async def _async_update_data(self) -> AmplifierState:
        try:
            return await self.client.async_get_state()
        except AmplifierError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set(self, name: str, on: bool) -> None:
        """Switch the power ("power") or a speaker output ("speaker_a", "speaker_b")."""
        key = POWER if name == "power" else SPEAKERS[name]
        try:
            result = await self.client.async_set(key, on)
        except AmplifierError as err:
            raise HomeAssistantError(f"Amplifier error: {err}") from err
        self.async_set_updated_data(replace(self.data, **{name: result}))


async def async_detect_amplifier(
    hass: HomeAssistant, entry: ConfigEntry, host: str, port: int = AMPLIFIER_PORT
) -> BluOSAmplifier | None:
    """Return the amplifier of a player, or None if it does not answer on its control port."""
    client = AmplifierClient(host, port)
    try:
        state = await client.async_get_state(DETECT_TIMEOUT)
    except AmplifierError:
        return None
    amplifier = BluOSAmplifier(hass, entry, client)
    amplifier.async_set_updated_data(state)
    return amplifier
