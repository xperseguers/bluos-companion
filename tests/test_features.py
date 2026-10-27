"""Tests for sources, queue, sleep timer and grouping."""

from __future__ import annotations

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
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMockResponse,
    AiohttpClientMocker,
)
from yarl import URL

from custom_components.bluos_companion.api import BluOSClient, BluOSError, sleep_bucket
from custom_components.bluos_companion.const import CONF_PORT, DOMAIN

from .conftest import BASE, GROUPED_SYNC_STATUS, HOST, calls, respond, status_xml

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
        return AiohttpClientMockResponse(method, url, text="<sleep/>")


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
