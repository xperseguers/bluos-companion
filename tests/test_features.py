"""Tests for sources, queue, sleep timer and grouping."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant.components.media_player import (
    ATTR_GROUP_MEMBERS,
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_CLEAR_PLAYLIST,
    SERVICE_JOIN,
    SERVICE_SELECT_SOURCE,
    SERVICE_UNJOIN,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMockResponse,
    AiohttpClientMocker,
)
from yarl import URL

from homeassistant.helpers import entity_registry as er

from custom_components.bluos_companion.api import (
    BluOSClient,
    BluOSError,
    Member,
    SyncStatus,
    sleep_bucket,
)
from custom_components.bluos_companion.diagnostics import async_get_config_entry_diagnostics
from custom_components.bluos_companion.const import CONF_PORT, DOMAIN

from .conftest import BASE, GROUPED_SYNC_STATUS, HOST, MAC, calls, respond, status_xml

ENTITY_ID = "media_player.sejour"
SLEEP_ENTITY_ID = "select.sejour_sleep_timer"
OTHER_HOST = "192.168.1.101"
OTHER_BASE = f"http://{OTHER_HOST}:11000"


async def _refresh(
    hass: HomeAssistant, entry: MockConfigEntry, player_api: AiohttpClientMocker, xml: str
) -> None:
    player_api.mock_calls.clear()
    respond(player_api, f"{BASE}/Status", text=xml)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("remaining", "bucket"),
    [(None, 0), (0, 0), (1, 15), (15, 15), (16, 30), (89, 90), (120, 90)],
)
def test_sleep_bucket(remaining: int | None, bucket: int) -> None:
    """The remaining minutes are rounded up to an option."""
    assert sleep_bucket(remaining) == bucket


@pytest.mark.usefixtures("player_api")
async def test_sources_and_queue(client: BluOSClient) -> None:
    """Inputs without a type index are ignored, the queue keeps its positions."""
    sources = await client.async_get_sources()
    assert [(s.name, s.type_index, s.url) for s in sources] == [
        ("Bluetooth", "bluetooth-1", "Capture:bluez:bluetooth")
    ]
    queue = await client.async_get_queue()
    assert [(item.id, item.title, item.artist) for item in queue] == [
        (0, "U Got the Look", "Prince"),
        (1, "Kiss", ""),
    ]


async def test_sync_status(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """Group members and the external source are parsed."""
    aioclient_mock.get(f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    sync = await client.async_get_sync_status()
    assert sync.is_grouped
    assert sync.master is None
    assert [(m.host, m.port, m.name) for m in sync.slaves] == [(OTHER_HOST, 11000, "Pulse")]
    assert sync.external_source == "AppleTV"
    assert [(e.id, e.name) for e in sync.external_sources] == [("5", "Phono"), ("9", "BluOS")]


@pytest.mark.usefixtures("init_integration")
async def test_ungrouped_player(hass: HomeAssistant) -> None:
    """A player alone in its group has no group members."""
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes.get(ATTR_GROUP_MEMBERS) is None
    assert state.attributes[ATTR_INPUT_SOURCE_LIST] == ["Bluetooth"]
    assert ATTR_INPUT_SOURCE not in state.attributes


@pytest.mark.parametrize(
    ("stream_url", "source"),
    [
        ("Capture:bluez:bluetooth", "Bluetooth"),
        ("Capture:External", None),
        ("TuneIn:s1", None),
    ],
)
async def test_source(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    stream_url: str,
    source: str | None,
) -> None:
    """The active input is reported."""
    await _refresh(hass, init_integration, player_api, status_xml(streamUrl=stream_url))
    assert hass.states.get(ENTITY_ID).attributes.get(ATTR_INPUT_SOURCE) == source


async def test_external_source(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """An external input is named after the player's own setting."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml(streamUrl="Capture:External", syncStat="2"),
    )
    assert hass.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE] == "AppleTV"


@pytest.mark.usefixtures("init_integration")
async def test_select_source(
    hass: HomeAssistant, player_api: AiohttpClientMocker
) -> None:
    """Choosing an input plays it by type and index."""
    player_api.mock_calls.clear()
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Bluetooth"},
        blocking=True,
    )
    assert calls(player_api) == [("/Play", {"inputTypeIndex": "bluetooth-1"})]
    with pytest.raises(HomeAssistantError, match="Unknown source"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_SELECT_SOURCE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Vinyl"},
            blocking=True,
        )


async def test_same_named_inputs_are_told_apart(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The module's Bluetooth and the amplifier's Bluetooth get different names."""
    respond(
        player_api,
        f"{BASE}/SyncStatus",
        text=GROUPED_SYNC_STATUS.replace(
            '<item id="5" name="Phono"/>',
            '<item id="5" name="Phono"/><item id="8" name="Bluetooth"/>',
        ),
    )
    respond(player_api, f"{BASE}/ExternalSource", text="<externalSource/>")
    await _refresh(
        hass,
        init_integration,
        player_api,
        status_xml(streamUrl="Capture:bluez:bluetooth", syncStat="2"),
    )
    attributes = hass.states.get(ENTITY_ID).attributes
    assert sorted(attributes["source_list"]) == sorted(
        ["Bluetooth (BluOS)", "Phono", "Bluetooth", "BluOS"]
    )
    assert attributes[ATTR_INPUT_SOURCE] == "Bluetooth (BluOS)"

    player_api.mock_calls.clear()
    for name in ("Bluetooth (BluOS)", "Bluetooth"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_SELECT_SOURCE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: name},
            blocking=True,
        )
    assert calls(player_api) == [
        ("/Play", {"inputTypeIndex": "bluetooth-1"}),
        ("/ExternalSource", {"id": "8"}),
    ]


@pytest.mark.usefixtures("init_integration")
async def test_clear_queue(hass: HomeAssistant, player_api: AiohttpClientMocker) -> None:
    """The queue can be emptied."""
    player_api.mock_calls.clear()
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_CLEAR_PLAYLIST,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    assert calls(player_api) == [("/Clear", {})]


@pytest.mark.parametrize(
    ("sleep", "option"),
    [("", "off"), ("12", "15"), ("45", "45"), ("80", "90")],
)
async def test_sleep_timer_state(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    sleep: str,
    option: str,
) -> None:
    """The remaining time is shown as the closest option."""
    await _refresh(hass, init_integration, player_api, status_xml(sleep=sleep))
    assert hass.states.get(SLEEP_ENTITY_ID).state == option


class _Cycling:
    """A player whose sleep timer moves to the next value at every /Sleep."""

    def __init__(self, player_api: AiohttpClientMocker, values: list[str]) -> None:
        self.values = values
        self.index = 0
        player_api.mock_calls.clear()
        respond(player_api, f"{BASE}/Status", side_effect=self._status)
        respond(player_api, f"{BASE}/Sleep", side_effect=self._press)

    async def _status(
        self, method: str, url: URL, data: object
    ) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(
            method, url, text=status_xml(sleep=self.values[self.index])
        )

    async def _press(
        self, method: str, url: URL, data: object
    ) -> AiohttpClientMockResponse:
        self.index = (self.index + 1) % len(self.values)
        return AiohttpClientMockResponse(
            method, url, text=f"<sleep>{self.values[self.index]}</sleep>"
        )


@pytest.mark.parametrize(
    ("start", "option", "presses"),
    [(0, "45", 3), (3, "off", 3), (2, "30", 0), (5, "15", 2)],
)
async def test_set_sleep_timer(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    start: int,
    option: str,
    presses: int,
) -> None:
    """The timer is advanced until the player reports the chosen delay."""
    cycle = _Cycling(player_api, ["", "15", "30", "45", "60", "90"])
    cycle.index = start
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: SLEEP_ENTITY_ID, ATTR_OPTION: option},
        blocking=True,
    )
    assert [path for path, _ in calls(player_api) if path == "/Sleep"] == ["/Sleep"] * presses


async def test_set_sleep_timer_when_the_status_lags(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The player answers a press with the new delay while /Status keeps the old one."""

    class Lagging(_Cycling):
        async def _status(self, method, url, data):  # noqa: ANN001, ANN202
            return AiohttpClientMockResponse(method, url, text=status_xml(sleep=""))

    Lagging(player_api, ["", "15", "30", "45", "60", "90"])
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: SLEEP_ENTITY_ID, ATTR_OPTION: "30"},
        blocking=True,
    )
    assert [path for path, _ in calls(player_api) if path == "/Sleep"] == ["/Sleep"] * 2


async def test_set_sleep_timer_failure(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A player that never reaches the delay is reported as an error."""
    _Cycling(player_api, ["", ""])
    with pytest.raises(HomeAssistantError, match="sleep timer"):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: SLEEP_ENTITY_ID, ATTR_OPTION: "30"},
            blocking=True,
        )


@pytest.mark.parametrize(("value", "presses"), [(45, 3), (0, 0), (7, 0)])
async def test_panel_sets_the_sleep_timer(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    value: int,
    presses: int,
) -> None:
    """The panel picks a delay; a value the player does not offer means off."""
    _Cycling(player_api, ["", "15", "30", "45", "60", "90"])
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/control",
            "entry_id": init_integration.entry_id,
            "action": "sleep",
            "value": value,
        }
    )
    assert (await client.receive_json())["success"]
    assert [path for path, _ in calls(player_api) if path == "/Sleep"] == ["/Sleep"] * presses


@pytest.fixture
async def pulse(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> MockConfigEntry:
    """Add a second player, the Pulse, next to the main one."""
    respond(player_api, 
        f"{OTHER_BASE}/SyncStatus",
        text='<SyncStatus id="x" mac="11:22:33:44:55:66" name="Pulse" model="P225" '
        'modelName="P225" brand="Bluesound" syncStat="1"/>',
    )
    respond(player_api, f"{OTHER_BASE}/Status", text=status_xml())
    respond(player_api, f"{OTHER_BASE}/RadioBrowse", text="<radiotime/>")
    for command in ("RemoveSlave", "AddSlave"):
        respond(player_api, f"{OTHER_BASE}/{command}", text="<ok/>")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="11:22:33:44:55:66",
        title="Pulse",
        minor_version=2,
        data={"host": OTHER_HOST, CONF_PORT: 11000},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_join_players(
    hass: HomeAssistant, pulse: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The player joined becomes a secondary of the player the service targets."""
    player_api.mock_calls.clear()
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_JOIN,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_GROUP_MEMBERS: ["media_player.pulse"]},
        blocking=True,
    )
    assert calls(player_api) == [("/AddSlave", {"slave": OTHER_HOST, "port": "11000"})]


@pytest.mark.parametrize("pair_member", ["pulse", "main"])
async def test_join_refuses_to_split_a_stereo_pair(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
    pair_member: str,
) -> None:
    """The second speaker of a stereo pair can neither join nor be joined."""
    entry = pulse if pair_member == "pulse" else init_integration
    base = OTHER_BASE if pair_member == "pulse" else BASE
    respond(
        player_api,
        f"{base}/SyncStatus",
        text='<SyncStatus id="x" syncStat="3" zone="Pair" zoneSlave="true"/>',
    )
    respond(player_api, f"{base}/Status", text=status_xml(syncStat="3"))
    await entry.runtime_data.async_refresh()
    player_api.mock_calls.clear()

    with pytest.raises(HomeAssistantError, match="stereo pair"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_JOIN,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_GROUP_MEMBERS: ["media_player.pulse"]},
            blocking=True,
        )
    assert calls(player_api) == []


async def test_join_rejects_foreign_entities(
    hass: HomeAssistant, pulse: MockConfigEntry
) -> None:
    """Only players of this integration can be grouped."""
    with pytest.raises(HomeAssistantError, match="not a BluOS Companion player"):
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_JOIN,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_GROUP_MEMBERS: ["media_player.nope"]},
            blocking=True,
        )


async def test_group_members(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Both players of a group list the primary first, then the secondaries."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    respond(player_api, 
        f"{OTHER_BASE}/SyncStatus",
        text=f'<SyncStatus id="x" syncStat="2"><master port="11000">{HOST}</master></SyncStatus>',
    )
    for entry, base in ((init_integration, BASE), (pulse, OTHER_BASE)):
        respond(player_api, f"{base}/Status", text=status_xml(syncStat="2"))
        await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    expected = [ENTITY_ID, "media_player.pulse"]
    for entity_id in expected:
        assert hass.states.get(entity_id).attributes[ATTR_GROUP_MEMBERS] == expected


@pytest.mark.parametrize(
    "entity_id",
    [
        pytest.param("media_player.pulse", id="secondary"),
        pytest.param(ENTITY_ID, id="primary"),
    ],
)
async def test_unjoin(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
    entity_id: str,
) -> None:
    """A secondary asks its primary to drop it, a primary drops its secondaries."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    respond(player_api, 
        f"{OTHER_BASE}/SyncStatus",
        text=f'<SyncStatus id="x" syncStat="2"><master port="11000">{HOST}</master></SyncStatus>',
    )
    for entry, url in ((init_integration, BASE), (pulse, OTHER_BASE)):
        respond(player_api, f"{url}/Status", text=status_xml(syncStat="2"))
        await entry.runtime_data.async_refresh()
    player_api.mock_calls.clear()
    # RemoveSlave is always sent to the primary player
    respond(player_api, f"{BASE}/RemoveSlave", text="<ok/>")

    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN, SERVICE_UNJOIN, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert calls(player_api) == [
        ("/RemoveSlave", {"slave": OTHER_HOST, "port": "11000"})
    ]


async def test_unjoin_when_alone_does_nothing(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """Leaving a group that does not exist sends nothing."""
    player_api.mock_calls.clear()
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN, SERVICE_UNJOIN, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert calls(player_api) == []


async def test_sync_status_reloaded_when_it_changes(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The group is only fetched again when the player reports a change."""
    coordinator = init_integration.runtime_data
    player_api.mock_calls.clear()
    respond(player_api, f"{BASE}/Status", text=status_xml())
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    await coordinator.async_refresh()
    assert [path for path, _ in calls(player_api)] == ["/Status"]

    player_api.mock_calls.clear()
    respond(player_api, f"{BASE}/Status", text=status_xml(syncStat="2"))
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    await coordinator.async_refresh()
    assert [path for path, _ in calls(player_api)] == ["/Status", "/SyncStatus", "/RadioBrowse"]
    assert coordinator.sync.is_grouped


async def test_select_external_source(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The inputs of an amplifier are listed and selected by id."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    respond(player_api, f"{BASE}/ExternalSource", text="<externalSource/>")
    await _refresh(hass, init_integration, player_api, status_xml(syncStat="2"))
    assert hass.states.get(ENTITY_ID).attributes[ATTR_INPUT_SOURCE_LIST] == [
        "Bluetooth",
        "Phono",
        "BluOS",
    ]
    player_api.mock_calls.clear()
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Phono"},
        blocking=True,
    )
    assert calls(player_api) == [("/ExternalSource", {"id": "5"})]


def _group(primary: MockConfigEntry, secondary: MockConfigEntry) -> None:
    """Make the first player lead a group with the second one."""
    members = (Member(OTHER_HOST, 11000, "Pulse"),)
    primary.runtime_data.sync = SyncStatus("G", None, members, None)
    secondary.runtime_data.sync = SyncStatus("G", Member(HOST, 11000, "Séjour"), (), None)


async def _ws_group(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    entry: MockConfigEntry,
    action: str,
    target: MockConfigEntry | None = None,
) -> dict:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/group",
            "entry_id": entry.entry_id,
            "action": action,
            **({"target": target.entry_id} if target else {}),
        }
    )
    return await client.receive_json()


async def test_panel_joins_a_player_through_the_primary(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The primary player of the target adds the player to its group."""
    player_api.mock_calls.clear()
    response = await _ws_group(hass, hass_ws_client, pulse, "join", init_integration)
    assert response["success"]
    assert calls(player_api) == [("/AddSlave", {"slave": OTHER_HOST, "port": "11000"})]


async def test_panel_join_of_a_member_does_nothing(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Joining the group a player is already in changes nothing."""
    _group(init_integration, pulse)
    player_api.mock_calls.clear()
    assert (await _ws_group(hass, hass_ws_client, pulse, "join", pulse))["success"]
    assert (await _ws_group(hass, hass_ws_client, init_integration, "join", pulse))["success"]
    assert calls(player_api) == []


async def test_panel_leaves_a_group(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A secondary is removed by its primary, a primary dissolves its group."""
    _group(init_integration, pulse)
    player_api.mock_calls.clear()
    assert (await _ws_group(hass, hass_ws_client, pulse, "leave"))["success"]
    assert calls(player_api) == [("/RemoveSlave", {"slave": OTHER_HOST, "port": "11000"})]

    player_api.mock_calls.clear()
    assert (await _ws_group(hass, hass_ws_client, init_integration, "leave"))["success"]
    assert calls(player_api) == [("/RemoveSlave", {"slave": OTHER_HOST, "port": "11000"})]


@pytest.fixture
async def third(
    hass: HomeAssistant, pulse: MockConfigEntry, player_api: AiohttpClientMocker
) -> MockConfigEntry:
    """Add a third player, alone."""
    base = "http://192.168.1.102:11000"
    respond(
        player_api,
        f"{base}/SyncStatus",
        text='<SyncStatus id="x" mac="11:22:33:44:55:77" name="Kitchen" model="P125" '
        'modelName="P125" brand="Bluesound" syncStat="1"/>',
    )
    respond(player_api, f"{base}/Status", text=status_xml())
    respond(player_api, f"{base}/RadioBrowse", text="<radiotime/>")
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="11:22:33:44:55:77",
        title="Kitchen",
        minor_version=2,
        data={"host": "192.168.1.102", CONF_PORT: 11000},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_panel_join_refuses_a_primary_with_secondaries(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    third: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A player that leads a group must dissolve it before joining another one."""
    _group(init_integration, pulse)
    player_api.mock_calls.clear()
    response = await _ws_group(hass, hass_ws_client, init_integration, "join", third)
    assert response["success"] is False
    assert "ungroup it first" in response["error"]["message"]
    assert calls(player_api) == []


async def test_panel_moves_a_member_to_another_group(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    third: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A secondary joining another group first leaves its own one."""
    _group(init_integration, pulse)
    respond(player_api, "http://192.168.1.102:11000/AddSlave", text="<ok/>")
    player_api.mock_calls.clear()
    assert (await _ws_group(hass, hass_ws_client, pulse, "join", third))["success"]
    assert [(str(call[1]), call[1].query_string) for call in player_api.mock_calls] == [
        (f"{BASE}/RemoveSlave?slave={OTHER_HOST}&port=11000", f"slave={OTHER_HOST}&port=11000"),
        (
            f"http://192.168.1.102:11000/AddSlave?slave={OTHER_HOST}&port=11000",
            f"slave={OTHER_HOST}&port=11000",
        ),
    ]


@pytest.mark.parametrize(
    ("message", "query"),
    [
        ({"action": "volume_step", "value": 2, "group": True}, {"db": "2", "tell_slaves": "1"}),
        ({"action": "volume_step", "value": -50}, {"db": "-10", "tell_slaves": "0"}),
        ({"action": "mute", "value": True, "group": True}, {"mute": "1", "tell_slaves": "1"}),
    ],
)
async def test_panel_group_volume(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
    message: dict,
    query: dict[str, str],
) -> None:
    """Volume steps are relative (in dB, limited) and can apply to the whole group."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "bluos_companion/control", "entry_id": init_integration.entry_id, **message}
    )
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [("/Volume", query)]


async def test_group_volumes_are_the_own_volume_of_each_player(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Each member of the group is asked for its own volume (/Status shows the group's)."""
    _group(init_integration, pulse)
    respond(player_api, f"{BASE}/Volume", text='<volume db="-36" mute="0">49</volume>')
    respond(player_api, f"{OTHER_BASE}/Volume", text='<volume db="-39" mute="1">20</volume>')
    client = await hass_ws_client(hass)

    for entry in (pulse, init_integration):
        await client.send_json_auto_id(
            {"type": "bluos_companion/group_volumes", "entry_id": entry.entry_id}
        )
        volumes = (await client.receive_json())["result"]["volumes"]
        assert [(v["entry_id"], v["volume"], v["muted"]) for v in volumes] == [
            (init_integration.entry_id, 49, False),
            (pulse.entry_id, 20, True),
        ]


async def test_panel_moves_the_playback(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """The source player is asked to move its playback to the address of the target."""
    respond(
        player_api, f"{BASE}/Status", text=status_xml().replace("<state>", "<canMovePlayback>true</canMovePlayback><state>")
    )
    await init_integration.runtime_data.async_refresh()
    respond(player_api, f"{BASE}/MovePlayback", text="<state>play</state>")
    player_api.mock_calls.clear()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "bluos_companion/move",
            "entry_id": init_integration.entry_id,
            "target": pulse.entry_id,
        }
    )
    assert (await client.receive_json())["success"]
    assert calls(player_api) == [
        ("/MovePlayback", {"id": OTHER_HOST, "port": "11000"})
    ]

    for entry_id, target, message in (
        (init_integration.entry_id, init_integration.entry_id, "already the target"),
        (pulse.entry_id, init_integration.entry_id, "cannot move"),
    ):
        await client.send_json_auto_id(
            {"type": "bluos_companion/move", "entry_id": entry_id, "target": target}
        )
        response = await client.receive_json()
        assert response["success"] is False
        assert message in response["error"]["message"]


async def test_panel_does_not_move_a_stopped_player(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Moving nothing would replace what the target plays with silence."""
    respond(
        player_api,
        f"{BASE}/Status",
        text=status_xml("stop").replace("<state>", "<canMovePlayback>true</canMovePlayback><state>"),
    )
    await init_integration.runtime_data.async_refresh()
    player_api.mock_calls.clear()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "bluos_companion/move",
            "entry_id": init_integration.entry_id,
            "target": pulse.entry_id,
        }
    )
    response = await client.receive_json()
    assert response["success"] is False
    assert "stopped" in response["error"]["message"]
    assert calls(player_api) == []


async def test_diagnostics_hide_addresses_and_names(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The diagnostics carry the state of the player but not where or who it is."""
    result = await async_get_config_entry_diagnostics(hass, init_integration)
    assert result["status"]["state"]
    assert result["entry"]["data"]["host"] == "**REDACTED**"
    assert result["entry"]["unique_id"] == "**REDACTED**"
    assert HOST not in str(result)
    assert MAC.lower() not in str(result).lower()


async def test_reindex_button(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """Pressing the button asks the player to read its music library again."""
    respond(player_api, f"{BASE}/Reindex", text="<ok/>")
    entity_id = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"{init_integration.unique_id}_reindex"
    )
    player_api.mock_calls.clear()
    await hass.services.async_call(
        "button", "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert calls(player_api) == [("/Reindex", {})]


async def test_reindex_of_a_secondary_goes_to_its_primary(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """Only the primary of a group reads the library: a secondary's button asks it to."""
    respond(player_api, f"{BASE}/SyncStatus", text=GROUPED_SYNC_STATUS)
    respond(
        player_api,
        f"{OTHER_BASE}/SyncStatus",
        text=f'<SyncStatus id="x" syncStat="2"><master port="11000">{HOST}</master></SyncStatus>',
    )
    respond(player_api, f"{BASE}/Reindex", text="<indexing>1</indexing>")
    for entry, base in ((init_integration, BASE), (pulse, OTHER_BASE)):
        respond(player_api, f"{base}/Status", text=status_xml(syncStat="2"))
        await entry.runtime_data.async_refresh()
    entity_id = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"{pulse.unique_id}_reindex"
    )
    player_api.mock_calls.clear()
    await hass.services.async_call(
        "button", "press", {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert calls(player_api) == [("/Reindex", {})]
    assert str(player_api.mock_calls[0][1]).startswith(BASE)


async def test_reindex_follows_the_scan_until_it_ends(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """After a reindex the status is read often, until the count has been seen and is gone."""
    coordinator = init_integration.runtime_data
    statuses = [replace(coordinator.data, indexing=count) for count in (0, 1500, 17012, 0)]
    with (
        patch.object(coordinator.client, "async_get_status", AsyncMock(side_effect=statuses)) as get,
        patch("custom_components.bluos_companion.coordinator.asyncio.sleep", AsyncMock()),
    ):
        await coordinator._async_follow_indexing()
    assert get.await_count == 4
    assert coordinator.data.indexing == 0


async def test_restart_button_is_off_by_default_and_posts_to_the_web_server(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The restart goes to the player's web server, and has to be enabled first."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "button", DOMAIN, f"{init_integration.unique_id}_restart"
    )
    assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION

    player_api.post(f"http://{HOST}/reboot", text="Rebooting")
    await init_integration.runtime_data.client.async_reboot()
    method, url, data, _ = player_api.mock_calls[-1]
    assert (method, str(url), data) == ("POST", f"http://{HOST}/reboot", {"yes": "1"})


async def test_library_tracks_keep_the_last_count(
    hass: HomeAssistant, init_integration: MockConfigEntry, player_api: AiohttpClientMocker
) -> None:
    """The player forgets how many tracks it read once it is done: the sensor does not."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{init_integration.unique_id}_library_tracks"
    )
    assert hass.states.get(entity_id).state == "unknown"

    for counter, expected_state, expected_progress in (
        ("1500", "unknown", 1500),
        ("5500", "unknown", 5500),
        ("0", "5500", None),
        # A reindex the player does not carry out only flashes a count of 1
        ("1", "5500", 1),
        ("0", "5500", None),
    ):
        await _refresh(hass, init_integration, player_api, status_xml(indexing=counter))
        state = hass.states.get(entity_id)
        assert (state.state, state.attributes["indexing"]) == (expected_state, expected_progress)


VOLUME_SLEEP = "custom_components.bluos_companion.coordinator.asyncio.sleep"


async def test_volume_poll_state(
    client: BluOSClient, aioclient_mock: AiohttpClientMocker
) -> None:
    """The own volume, mute and etag of a player are read, waiting for a change if asked."""
    aioclient_mock.get(
        f"{BASE}/Volume", text='<volume db="-40" mute="1" etag="v1">18</volume>'
    )

    assert await client.async_get_volume() == (18, True)
    state = await client.async_poll_volume("v1", 100)
    assert (state.level, state.muted, state.etag) == (18, True, "v1")
    assert calls(aioclient_mock) == [
        ("/Volume", {}),
        ("/Volume", {"timeout": "100", "etag": "v1"}),
    ]


async def test_a_secondary_shows_its_own_volume_and_mute(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """/Status of a secondary carries the group's volume and mute, the entity shows its own."""
    _group(init_integration, pulse)
    respond(player_api, f"{OTHER_BASE}/Volume", text='<volume db="-40" mute="1" etag="v1">18</volume>')
    # The status of the group: volume 25, not muted
    assert hass.states.get("media_player.pulse").attributes["volume_level"] == 0.25

    with patch(VOLUME_SLEEP, AsyncMock(side_effect=asyncio.CancelledError)):
        with pytest.raises(asyncio.CancelledError):
            await pulse.runtime_data._async_poll_volume()  # noqa: SLF001
    await hass.async_block_till_done()

    state = hass.states.get("media_player.pulse")
    assert state.attributes["volume_level"] == 0.18
    assert state.attributes["is_volume_muted"] is True

    # Back alone, it shows what /Status says again
    pulse.runtime_data.sync = SyncStatus("G", None, (), None)
    with patch(VOLUME_SLEEP, AsyncMock(side_effect=asyncio.CancelledError)):
        with pytest.raises(asyncio.CancelledError):
            await pulse.runtime_data._async_poll_volume()  # noqa: SLF001
    await hass.async_block_till_done()
    state = hass.states.get("media_player.pulse")
    assert state.attributes["volume_level"] == 0.25
    assert state.attributes["is_volume_muted"] is False


async def test_the_primary_is_not_affected(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
) -> None:
    """The primary keeps the volume of /Status."""
    _group(init_integration, pulse)
    coordinator = init_integration.runtime_data
    assert (coordinator.volume_level, coordinator.is_muted) == (25, False)


@pytest.mark.parametrize("entity", ["media_player.sejour", "media_player.pulse"])
@pytest.mark.parametrize("mute", [True, False])
async def test_mute_group_goes_to_the_primary_for_the_whole_group(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    pulse: MockConfigEntry,
    player_api: AiohttpClientMocker,
    entity: str,
    mute: bool,
) -> None:
    """Whichever member is chosen, the primary mutes or unmutes every player of its group."""
    _group(init_integration, pulse)
    player_api.mock_calls.clear()

    await hass.services.async_call(
        DOMAIN, "mute_group", {"entity_id": entity, "mute": mute}, blocking=True
    )

    assert calls(player_api) == [("/Volume", {"mute": str(int(mute)), "tell_slaves": "1"})]
    assert str(player_api.mock_calls[0][1]).startswith(BASE)


async def test_mute_group_reports_a_player_error(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    player_api: AiohttpClientMocker,
) -> None:
    """A player that cannot be reached is an error."""
    respond(player_api, f"{BASE}/Volume", exc=aiohttp.ClientError)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "mute_group",
            {"entity_id": "media_player.sejour", "mute": True},
            blocking=True,
        )
