"""Tests for the amplifier a player is built into: its power and its speaker outputs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.bluos_companion.amplifier import (
    AmplifierClient,
    AmplifierError,
    AmplifierState,
    BluOSAmplifier,
    async_detect_amplifier,
)
from custom_components.bluos_companion.const import DOMAIN


class FakeAmplifier:
    """An amplifier that greets and answers queries and commands."""

    def __init__(self) -> None:
        self.values = {"Main.Power": "On", "Main.SpeakerA": "On", "Main.SpeakerB": "Off"}
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
                key, operator, value = command.partition("?")[0], "?" in command, None
                if not operator:
                    key, _, value = command.partition("=")
                    if key in self.values:
                        self.values[key] = value
                # An output the amplifier does not have is not answered
                if key in self.values and not self.silent:
                    writer.write(f"{key}={self.values[key]}\r\n".encode())
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


async def test_the_client_reads_and_sets(amplifier_server: FakeAmplifier) -> None:
    """The greeting is skipped, one connection reads the power and the speakers."""
    client = AmplifierClient("127.0.0.1", amplifier_server.port)

    assert await client.async_get_state() == AmplifierState(True, True, False)
    assert amplifier_server.commands == ["Main.Power?", "Main.SpeakerA?", "Main.SpeakerB?"]

    assert await client.async_set("Main.Power", False) is False
    assert await client.async_set("Main.SpeakerB", True) is True
    assert await client.async_get_state() == AmplifierState(False, True, True)
    assert "Main.Power=Off" in amplifier_server.commands
    assert "Main.SpeakerB=On" in amplifier_server.commands


async def test_an_amplifier_without_speaker_outputs(amplifier_server: FakeAmplifier) -> None:
    """Outputs it does not answer for are None, after a short wait."""
    del amplifier_server.values["Main.SpeakerA"], amplifier_server.values["Main.SpeakerB"]
    client = AmplifierClient("127.0.0.1", amplifier_server.port)

    assert await client.async_get_state() == AmplifierState(True, None, None)


async def test_an_unreachable_amplifier_is_an_error(socket_enabled: None) -> None:
    """Nothing listens on the port: the client reports it, it does not hang."""
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()

    with pytest.raises(AmplifierError):
        await AmplifierClient("127.0.0.1", port).async_get_state()


async def test_a_silent_amplifier_times_out(amplifier_server: FakeAmplifier) -> None:
    """An amplifier that does not answer is an error after the timeout."""
    amplifier_server.silent = True
    with pytest.raises(AmplifierError):
        await AmplifierClient("127.0.0.1", amplifier_server.port).async_get_state(0.1)


async def test_detection(
    hass: HomeAssistant, config_entry: MockConfigEntry, amplifier_server: FakeAmplifier
) -> None:
    """A player whose address answers has an amplifier, one that does not has none."""
    found = await async_detect_amplifier(hass, config_entry, "127.0.0.1", amplifier_server.port)
    assert found is not None and found.data == AmplifierState(True, True, False)

    amplifier_server.values["Main.Power"] = "Off"
    found = await async_detect_amplifier(hass, config_entry, "127.0.0.1", amplifier_server.port)
    assert found is not None and found.data.power is False

    assert await async_detect_amplifier(hass, config_entry, "127.0.0.1", 1) is None


@pytest.fixture
def amplifier(
    hass: HomeAssistant, config_entry: MockConfigEntry, detect_amplifier: AsyncMock
) -> BluOSAmplifier:
    """Give the player an amplifier that is on, with speaker A on and speaker B off."""
    client = MagicMock()
    client.async_set = AsyncMock(side_effect=lambda key, on: on)
    coordinator = BluOSAmplifier(hass, config_entry, client)
    coordinator.async_set_updated_data(AmplifierState(True, True, False))
    detect_amplifier.return_value = coordinator
    return coordinator


def _switch(hass: HomeAssistant, entry: MockConfigEntry, name: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.unique_id}_amplifier_{name}"
    )


async def test_no_switch_without_an_amplifier(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """A player that is not built into an amplifier gets no amplifier switch."""
    for name in ("power", "speaker_a", "speaker_b"):
        assert _switch(hass, init_integration, name) is None


async def test_the_switches_show_and_set_the_amplifier(
    hass: HomeAssistant, amplifier: BluOSAmplifier, init_integration: MockConfigEntry
) -> None:
    """Power and speaker outputs are switches that show the amplifier and set it."""
    power, speaker_a, speaker_b = (
        _switch(hass, init_integration, name) for name in ("power", "speaker_a", "speaker_b")
    )
    assert [hass.states.get(entity).state for entity in (power, speaker_a, speaker_b)] == [
        STATE_ON,
        STATE_ON,
        STATE_OFF,
    ]

    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: speaker_b}, blocking=True)
    amplifier.client.async_set.assert_awaited_with("Main.SpeakerB", True)
    assert hass.states.get(speaker_b).state == STATE_ON

    await hass.services.async_call("switch", "turn_off", {ATTR_ENTITY_ID: power}, blocking=True)
    amplifier.client.async_set.assert_awaited_with("Main.Power", False)
    assert hass.states.get(power).state == STATE_OFF
    # The other outputs are left alone
    assert hass.states.get(speaker_a).state == STATE_ON


async def test_an_amplifier_without_speaker_outputs_has_only_the_power(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    player_api: AiohttpClientMocker,
    amplifier: BluOSAmplifier,
) -> None:
    """No switch is made for an output the amplifier does not have."""
    amplifier.async_set_updated_data(AmplifierState(True, None, None))
    config_entry.add_to_hass(hass)
    with patch(
        "custom_components.bluos_companion.BluOSCoordinator.async_long_poll", new=AsyncMock()
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    assert _switch(hass, config_entry, "power") is not None
    assert _switch(hass, config_entry, "speaker_a") is None
    assert _switch(hass, config_entry, "speaker_b") is None


async def test_the_switch_reports_an_amplifier_error(
    hass: HomeAssistant, amplifier: BluOSAmplifier, init_integration: MockConfigEntry
) -> None:
    """An amplifier that cannot be reached is an error, not a silent failure."""
    amplifier.client.async_set.side_effect = AmplifierError("no answer")
    with pytest.raises(HomeAssistantError, match="no answer"):
        await hass.services.async_call(
            "switch",
            "turn_off",
            {ATTR_ENTITY_ID: _switch(hass, init_integration, "power")},
            blocking=True,
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
    amplifier.client.async_set.assert_awaited_with("Main.Power", False)


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
