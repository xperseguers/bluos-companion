"""Tests for the power of the amplifier a player is built into."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.bluos_companion.amplifier import (
    AmplifierClient,
    AmplifierError,
    BluOSAmplifier,
    async_detect_amplifier,
)
from custom_components.bluos_companion.const import DOMAIN

from .conftest import HOST


class FakeAmplifier:
    """An amplifier that greets, answers queries and takes a moment to power on."""

    def __init__(self) -> None:
        self.power = "On"
        self.commands: list[str] = []
        self.silent = False
        self.port = 0

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writer.write(b"\rMain.Model=C368\r\n")
        await writer.drain()
        buffer = b""
        while data := await reader.read(100):
            *lines, buffer = (buffer + data).split(b"\r")
            for line in filter(None, lines):
                command = line.decode()
                self.commands.append(command)
                if command.startswith("Main.Power="):
                    self.power = command.removeprefix("Main.Power=")
                if command.startswith("Main.Power") and not self.silent:
                    writer.write(f"Main.Power={self.power}\r\n".encode())
                    await writer.drain()
        writer.close()


@pytest.fixture
async def amplifier_server(socket_enabled: None) -> AsyncGenerator[FakeAmplifier]:
    """Run a fake amplifier on a local port."""
    fake = FakeAmplifier()
    server = await asyncio.start_server(fake._handle, "127.0.0.1", 0)  # noqa: SLF001
    fake.port = server.sockets[0].getsockname()[1]
    yield fake
    server.close()
    await server.wait_closed()


async def test_the_client_reads_and_sets_the_power(amplifier_server: FakeAmplifier) -> None:
    """The greeting is skipped, the answer to the command is the state."""
    client = AmplifierClient("127.0.0.1", amplifier_server.port)

    assert await client.async_get_power() is True
    assert await client.async_set_power(False) is False
    assert await client.async_get_power() is False
    assert await client.async_set_power(True) is True
    assert amplifier_server.commands == [
        "Main.Power?",
        "Main.Power=Off",
        "Main.Power?",
        "Main.Power=On",
    ]


async def test_an_unreachable_amplifier_is_an_error(socket_enabled: None) -> None:
    """Nothing listens on the port: the client reports it, it does not hang."""
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    with pytest.raises(AmplifierError):
        await AmplifierClient("127.0.0.1", port).async_get_power()


async def test_a_silent_amplifier_times_out(amplifier_server: FakeAmplifier) -> None:
    """An amplifier that does not answer is an error after the timeout."""
    amplifier_server.silent = True
    with pytest.raises(AmplifierError):
        await AmplifierClient("127.0.0.1", amplifier_server.port).async_get_power(0.1)


async def test_detection(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    amplifier_server: FakeAmplifier,
) -> None:
    """A player whose address answers has an amplifier, one that does not has none."""
    found = await async_detect_amplifier(hass, config_entry, "127.0.0.1", amplifier_server.port)
    assert found is not None and found.data is True

    amplifier_server.power = "Off"
    found = await async_detect_amplifier(hass, config_entry, "127.0.0.1", amplifier_server.port)
    assert found is not None and found.data is False

    assert await async_detect_amplifier(hass, config_entry, "127.0.0.1", 1) is None


@pytest.fixture
def amplifier(hass: HomeAssistant, config_entry: MockConfigEntry, detect_amplifier: AsyncMock):
    """Give the player an amplifier that is on."""
    client = MagicMock()
    client.async_get_power = AsyncMock(return_value=True)
    client.async_set_power = AsyncMock(side_effect=lambda on: on)
    coordinator = BluOSAmplifier(hass, config_entry, client)
    coordinator.async_set_updated_data(True)
    detect_amplifier.return_value = coordinator
    return coordinator


def _switch(hass: HomeAssistant, entry: MockConfigEntry) -> str | None:
    return er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{entry.unique_id}_amplifier_power")


async def test_no_switch_without_an_amplifier(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """A player that is not built into an amplifier gets no power switch."""
    assert _switch(hass, init_integration) is None


async def test_the_switch_powers_the_amplifier(
    hass: HomeAssistant, amplifier: BluOSAmplifier, init_integration: MockConfigEntry
) -> None:
    """The switch shows the power and sets it."""
    entity_id = _switch(hass, init_integration)
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    amplifier.client.async_set_power.assert_awaited_with(False)
    assert hass.states.get(entity_id).state == STATE_OFF

    await hass.services.async_call(
        "switch", "turn_on", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    amplifier.client.async_set_power.assert_awaited_with(True)
    assert hass.states.get(entity_id).state == STATE_ON


async def test_the_switch_reports_an_amplifier_error(
    hass: HomeAssistant, amplifier: BluOSAmplifier, init_integration: MockConfigEntry
) -> None:
    """An amplifier that cannot be reached is an error, not a silent failure."""
    amplifier.client.async_set_power.side_effect = AmplifierError("no answer")
    with pytest.raises(HomeAssistantError, match="no answer"):
        await hass.services.async_call(
            "switch", "turn_off", {ATTR_ENTITY_ID: _switch(hass, init_integration)}, blocking=True
        )


async def test_the_panel_state_and_command(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    amplifier: BluOSAmplifier,
    init_integration: MockConfigEntry,
) -> None:
    """The websocket API gives the power and switches it."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/subscribe"})
    assert (await client.receive_json())["success"]
    [player] = (await client.receive_json())["event"]["players"]
    assert player["power"] is True

    await client.send_json_auto_id(
        {
            "type": "bluos_companion/control",
            "entry_id": init_integration.entry_id,
            "action": "power",
            "value": False,
        }
    )
    # The new state is pushed as soon as the amplifier answers, before the result of the command
    messages = [await client.receive_json(), await client.receive_json()]
    assert any(message.get("success") for message in messages if message["type"] == "result")
    [event] = [message for message in messages if message["type"] == "event"]
    assert event["event"]["players"][0]["power"] is False
    amplifier.client.async_set_power.assert_awaited_with(False)


async def test_the_panel_power_command_needs_an_amplifier(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, init_integration: MockConfigEntry
) -> None:
    """A player without an amplifier says so and shows no power."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "bluos_companion/subscribe"})
    await client.receive_json()
    [player] = (await client.receive_json())["event"]["players"]
    assert player["power"] is None

    await client.send_json_auto_id(
        {
            "type": "bluos_companion/control",
            "entry_id": init_integration.entry_id,
            "action": "power",
            "value": True,
        }
    )
    assert not (await client.receive_json())["success"]
