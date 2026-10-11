"""Approved application choices; synthetic protocol results, not RF equivalence."""

import asyncio

import pytest

from mapping.nation_to_zk import NationAdapter
from mapping.nation_to_zk.policy import baseband_choice, region_choice
from tests.conftest import FakeTransport, ModulePeer, response
from zk_rfid import (
    Confirmation,
    CustomRegion,
    DeviceError,
    InventoryConfig,
    InventoryMode,
    Outcome,
    ReaderCapabilities,
    ReaderState,
    Region,
    UnsupportedFeature,
    ValidationError,
    ZKReader,
)


class PolicyPeer(ModulePeer):
    def __init__(self):
        super().__init__()
        self.profile = 125
        self.region = bytes((2, 49, 0))

    def __call__(self, command, data):
        if command == 0x7F:
            if data[0]:
                self.profile = int.from_bytes(data[1:], "big")
            return response(command, self.profile.to_bytes(2, "big"))
        if command == 0x22:
            self.region = data[1:]
            return response(command)
        if command == 0x9E:
            return response(command, self.region)
        return super().__call__(command, data)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "speed,profile",
    [
        (0, 205),
        (1, 146),
        (2, 141),
        (3, 203),
        (4, 123),
        (5, 103),
        (6, 141),
        (7, 141),
        (10, 146),
        (11, 146),
        (12, 141),
        (13, 141),
        (255, 125),
    ],
)
async def test_approved_speed_applies_profile_and_stages_run_parameters(speed, profile):
    peer = PolicyPeer()
    t = FakeTransport(peer)
    async with ZKReader(t) as reader:
        adapter = NationAdapter(reader)
        result = await adapter.configure_baseband(speed, 7, 2, 1)
        assert result.require_success() == profile
        assert adapter.inventory_config == InventoryConfig(q=7, session=2, target=1)
        value = (await adapter.query_baseband_profile()).require_success()
        assert value["zk_profile_id"] == profile and value["run_settings_source"] == "application"
        before = len(t.writes)
        session = await adapter.start_inventory_with_mode([1])
        assert peer.cfg[9] == bytes((7, 2))
        assert next(w[3:-2] for w in t.writes[before:] if w[2] == 0x50) == b"\x01"
        assert not any(w[2] in (0x7F, 0x22, 0x3F) for w in t.writes[before:])
        assert (await session.stop()).complete
    assert (not any(w[3] for w in t.writes if w[2] == 0x7F)) is (speed == 255)


@pytest.mark.asyncio
@pytest.mark.parametrize("band", range(17))
async def test_full_channel_plans_are_exact_or_rejected_before_io(band):
    t = FakeTransport(PolicyPeer())
    async with ZKReader(t) as reader:
        adapter = NationAdapter(reader)
        if band in (2, 4, 8, 9, 10, 16):
            with pytest.raises(UnsupportedFeature):
                await adapter.set_rf_band(band)
            assert t.writes == []
        else:
            result = await adapter.set_rf_band(band)
            assert result.require_success() == region_choice(band)
            assert result.confirmation is Confirmation.READ_BACK
            assert t.writes[0][2:4] == bytes((0x22, 1))  # Volatile.
            assert len(t.writes) == 2


def test_dialect_and_center_choices_are_not_id_aliases():
    assert baseband_choice(4)["zk_profile_id"] == 123
    assert region_choice(0) == Region(1, 2, 17)
    assert region_choice(7) == CustomRegion(923125, 9, 250)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rejected", "save_failed", "mismatch", "read_timeout"])
async def test_failed_profile_change_does_not_commit_pending_run_settings(failure):
    peer = PolicyPeer()

    def handle(cmd, data):
        if cmd == 0x7F:
            if data[0] and failure in ("rejected", "save_failed"):
                return response(cmd, status=0xF9 if failure == "rejected" else 0x13)
            if not data[0] and failure == "read_timeout":
                return None
            if data[0] and failure == "mismatch":
                return response(cmd, bytes((0, 123)))
        return peer(cmd, data)

    async with ZKReader(FakeTransport(handle), timeout=0.02) as reader:
        adapter = NationAdapter(reader)
        result = await adapter.configure_baseband(4, 8, 2, 1, persist=True)
        assert not result.ok and adapter.inventory_config == InventoryConfig()


@pytest.mark.asyncio
async def test_saved_antenna_configuration_survives_start_stop_without_resave():
    peer = PolicyPeer()
    t = FakeTransport(peer)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        (await adapter.save_antenna_mask(13)).require_success()
        before = len(t.writes)
        session = await adapter.start_inventory_with_mode([1, 3, 4])
        assert (await session.stop()).complete
        assert peer.ant == 13
        assert not any(w[2] == 0x3F for w in t.writes[before:])
        assert t.writes[0][2:-2] == bytes((0x3F, 13))
        with pytest.raises(ValidationError, match="SAVE"):
            await adapter.enable_ant(2, save=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("ports", [[1], [1, 3, 4]])
async def test_fastid_rounds_preserve_selected_ports_and_epc_only_tags(ports):
    peer = ModulePeer()
    peer.ant = sum(1 << (port - 1) for port in ports)
    requested = []

    def handle(cmd, data):
        if cmd == 1:
            port = (data[-2] & 0x7F) + 1
            requested.append(port)
            assert data[0] & 0x20  # FastID flag.
            tid = bytes(range(12)) if len(requested) % 2 else b""
            payload = b"\xab\xcd" + tid
            return response(
                cmd,
                bytes((1 << (port - 1), 1, len(payload) | (128 if tid else 0))) + payload + b"\x60",
                1,
            )
        if cmd == 0x93:
            return None
        return peer(cmd, data)

    t = FakeTransport(handle)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode(ports, include_tid=True)
        tags = [await asyncio.wait_for(anext(session), 1) for _ in range(len(ports) * 2)]
        assert [tag.antenna for tag in tags] == ports * 2
        assert tags[0].tid == bytes(range(12)) and tags[1].tid is None
        assert all(tag.epc == b"\xab\xcd" for tag in tags)
        assert (await adapter.stop_inventory()).complete
        assert reader.state is ReaderState.IDLE
        assert peer.ant == sum(1 << (port - 1) for port in ports)
        assert not any(w[2] in (0x50, 0x51, 0x3F) for w in t.writes)


@pytest.mark.asyncio
@pytest.mark.parametrize("sequence", [[], [1, 1], [0], [5], [True], [1.5]])
async def test_answer_sequence_validation_is_before_io(sequence):
    t = FakeTransport()
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        with pytest.raises(ValidationError):
            await reader.start_inventory(InventoryMode.ANSWER, antenna_sequence=sequence)
        assert t.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_stop", [False, True])
async def test_fastid_stop_joins_pending_round_and_never_starts_next_port(cancel_stop):
    peer = ModulePeer()
    entered = asyncio.Event()
    interrupt = asyncio.Event()

    def handle(cmd, data):
        if cmd == 1:
            entered.set()
            return None
        if cmd == 0x93:
            interrupt.set()
            return None
        return peer(cmd, data)

    t = FakeTransport(handle)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode([4, 1, 3], include_tid=True)
        await asyncio.wait_for(entered.wait(), 1)
        stopping = asyncio.create_task(adapter.stop_inventory())
        await asyncio.wait_for(interrupt.wait(), 1)
        if cancel_stop:
            stopping.cancel()
        t.feed(response(1, b"\x08\x00", 1))
        if cancel_stop:
            with pytest.raises(asyncio.CancelledError):
                await stopping
        else:
            await stopping
        assert session.outcome.complete and reader.state is ReaderState.IDLE
        assert [w[2] for w in t.writes].count(1) == 1
        assert [w[2] for w in t.writes].count(0x93) == 1


@pytest.mark.asyncio
async def test_answer_sequence_requires_answer_mode_and_bounded_multiport_rounds():
    t = FakeTransport()
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        with pytest.raises(UnsupportedFeature):
            await reader.start_inventory(antenna_sequence=(1, 2))
        with pytest.raises(ValidationError, match="bounded"):
            await reader.start_inventory(
                InventoryMode.ANSWER,
                antenna_sequence=(1, 2),
                config=InventoryConfig(scan_time_100ms=0),
            )
        assert not t.writes


@pytest.mark.asyncio
@pytest.mark.parametrize("ports", [[1], [1, 3, 4]])
@pytest.mark.parametrize("status", [0xF8, 0xF9])
@pytest.mark.parametrize("report_before_error", [False, True])
async def test_fastid_device_error_ends_sequence_and_preserves_reports(
    ports, status, report_before_error
):
    peer = ModulePeer()
    requested = []

    def handle(cmd, data):
        if cmd != 1:
            return peer(cmd, data)
        port = (data[-2] & 0x7F) + 1
        requested.append(port)
        tag = bytes((1 << (port - 1), 1, 2)) + b"\xab\xcd\x60"
        if len(ports) > 1 and len(requested) == 1:
            return response(1, tag, 1)
        prefix = response(1, tag, 3) if report_before_error else b""
        return prefix + response(1, status=status)

    t = FakeTransport(handle)
    caps = ReaderCapabilities(antenna_ports=1 if ports == [1] else 4)
    async with ZKReader(t, capabilities=caps) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode(ports, include_tid=True)
        reports = []
        try:
            with pytest.raises(DeviceError) as raised:
                async with asyncio.timeout(1):
                    async for tag in session:
                        reports.append(tag)
            assert raised.value.command == 1 and raised.value.status == status
        finally:
            outcome = await adapter.stop_inventory()
        assert requested == (ports[:2] if len(ports) > 1 else ports)
        assert len(reports) == (len(ports) > 1) + report_before_error
        assert outcome.received_count == len(reports)
        assert outcome.outcome is Outcome.PARTIAL and not outcome.complete
        assert outcome.status == status and outcome.termination_reason == "stopped"
        assert reader.state is ReaderState.IDLE and reader.dispatcher.fault is None
        assert session.drain() == () and (await session.stop()) is outcome
        assert not any(w[2] in (0x93, 0x50, 0x51, 0x3F) for w in t.writes)
        assert (await reader.get_reader_info()).ok  # No recovery needed after a valid rejection.


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [1, 2, 4, 0xFB])
async def test_fastid_normal_round_ends_continue_to_next_port(status):
    peer = ModulePeer()
    requested = []

    def handle(cmd, data):
        if cmd != 1:
            return peer(cmd, data)
        port = (data[-2] & 0x7F) + 1
        requested.append(port)
        if len(requested) == 4:
            return response(1, status=0xF8)
        payload = b"" if status == 0xFB else bytes((1 << (port - 1), 0))
        return response(1, payload, status)

    async with ZKReader(
        FakeTransport(handle), capabilities=ReaderCapabilities(antenna_ports=4)
    ) as reader:
        session = await NationAdapter(reader).start_inventory_with_mode([4, 1, 3], include_tid=True)
        try:
            with pytest.raises(DeviceError):
                await asyncio.wait_for(anext(session), 1)
        finally:
            await session.stop()
        assert requested == [4, 1, 3, 4]
