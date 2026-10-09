import asyncio
import pytest
from zk_rfid import (
    ZKReader,
    InventoryConfig,
    InventoryData,
    InventoryMode,
    Outcome,
    ReaderState,
    QueueOverflow,
    StateError,
)
from tests.conftest import FakeTransport, ModulePeer, response

pytestmark = pytest.mark.asyncio


async def test_answer_multiframe_statistics_and_device_timeout_partial():
    t = FakeTransport(
        lambda cmd, data: (
            response(1, bytes.fromhex("010102ABCD60"), status=3)
            + response(1, b"\1\0", status=2)
            + response(1, bytes.fromhex("01006400000001"), status=0x26)
        )
    )
    async with ZKReader(t) as reader:
        out = await reader.inventory_once(InventoryConfig(statistics=True))
        assert out.outcome is Outcome.PARTIAL and out.status == 2
        assert out.reports[0].epc == bytes.fromhex("ABCD")
        assert out.statistics.total_reads == 1
        assert reader.state is ReaderState.IDLE


async def test_host_timeout_preserves_reports_and_marks_unknown_reader():
    t = FakeTransport(lambda cmd, data: response(cmd, bytes.fromhex("010102ABCD60"), status=3))
    async with ZKReader(t, timeout=0.02) as reader:
        out = await reader.inventory_once()
        assert out.outcome is Outcome.PARTIAL and len(out.reports) == 1
        assert reader.state is ReaderState.UNKNOWN
        with pytest.raises(StateError):
            await reader.get_reader_info()


async def test_empty_field_success_not_fake_tag():
    async with ZKReader(FakeTransport(lambda cmd, data: response(cmd, status=0xFB))) as reader:
        out = await reader.inventory_once()
        assert out.complete and out.reports == () and out.termination_reason == "no_tag"


async def test_mix_epc_not_lost_when_memory_missing():
    t = FakeTransport(lambda cmd, data: response(cmd, bytes.fromhex("01010002ABCD60"), status=1))
    async with ZKReader(t) as reader:
        out = await reader.inventory_once(InventoryConfig(data=InventoryData.MIX))
        assert out.outcome is Outcome.PARTIAL and out.reports[0].memory_data is None


async def test_scenario_start_report_stop_and_restore():
    peer = ModulePeer()
    original = dict(peer.cfg)
    t = FakeTransport(peer, fragment=1)
    async with ZKReader(t) as reader:
        session = await reader.start_inventory()
        first = await anext(session)
        assert first.epc == bytes.fromhex("DEADBEEF")
        out = await session.stop()
        assert out.complete and out.received_count == 2
        assert peer.cfg == original and reader.state is ReaderState.IDLE
        assert t.max_readers == 1


async def test_scenario_tid_never_labels_tid_as_epc():
    peer = ModulePeer()
    peer.tag = bytes.fromhex("0104E280000050")
    async with ZKReader(FakeTransport(peer)) as reader:
        session = await reader.start_inventory(
            config=InventoryConfig(data=InventoryData.TID, tid_word_count=2)
        )
        report = await anext(session)
        assert report.epc is None and report.tid == bytes.fromhex("E2800000")
        await session.stop()


async def test_overflow_explicit_and_stop_still_possible():
    peer = ModulePeer()

    def handle(cmd, data):
        if cmd == 0x50:
            return response(0xEE, peer.tag) * 3 + response(cmd)
        return peer(cmd, data)

    async with ZKReader(FakeTransport(handle)) as reader:
        session = await reader.start_inventory(queue_size=1)
        await anext(session)
        with pytest.raises(QueueOverflow):
            await anext(session)
        out = await session.stop()
        assert out.outcome is Outcome.PARTIAL and out.dropped_count >= 2
        assert reader.state is ReaderState.IDLE


async def test_late_tag_after_stop_ack_does_not_leak_into_new_session():
    peer = ModulePeer()

    def handle(cmd, data):
        return response(cmd) + response(0xEE, peer.tag) if cmd == 0x51 else peer(cmd, data)

    async with ZKReader(FakeTransport(handle)) as reader:
        session = await reader.start_inventory()
        out = await session.stop()
        assert not out.complete and reader.state is ReaderState.UNKNOWN


async def test_realtime_commands_gated_and_heartbeat():
    peer = ModulePeer()
    t = FakeTransport(peer)
    async with ZKReader(t) as reader:
        session = await reader.start_inventory(InventoryMode.REAL_TIME)
        with pytest.raises(StateError):
            await reader.get_power()
        t.feed(response(0xEE, bytes.fromhex("000000010100000002"), status=0x28))
        heartbeat = await anext(session)
        assert heartbeat.total_reads == 2
        assert (await reader.get_reader_info()).ok
        assert (await session.stop()).complete
        assert peer.mode == 0


async def test_stopping_answer_session_does_not_deadlock():
    def handle(cmd, data):
        if cmd == 0x93:
            return response(1, b"\1\0", status=1)
        return None

    async with ZKReader(FakeTransport(handle)) as reader:
        session = await reader.start_inventory(InventoryMode.ANSWER)
        await asyncio.sleep(0.01)
        out = await asyncio.wait_for(session.stop(), 0.5)
        assert out.complete


async def test_answer_yields_before_terminal_frame_and_does_not_duplicate_at_stop():
    def handle(cmd, data):
        if cmd == 1:
            return response(1, bytes.fromhex("010102ABCD60"), status=3)
        if cmd == 0x93:
            return response(1, b"\1\0", status=1)

    t = FakeTransport(handle, fragment=1)
    async with ZKReader(t) as reader:
        session = await reader.start_inventory(InventoryMode.ANSWER)
        report = await asyncio.wait_for(anext(session), 0.5)
        assert report.epc.hex() == "abcd"
        assert reader.dispatcher.pending_command == 1  # Round has not ended.
        out = await session.stop()
        assert out.complete and out.received_count == 1
        assert [item async for item in session] == []
        assert len(reader.last_inventory_outcome.reports) == 1
        assert t.max_readers == 1


async def test_answer_live_overflow_counts_each_report_once_and_stop_works():
    def handle(cmd, data):
        if cmd == 1:
            return response(1, bytes.fromhex("010302ABCD6002ABCD6002ABCD60"), status=3)
        if cmd == 0x93:
            return response(1, b"\1\0", status=1)

    async with ZKReader(FakeTransport(handle)) as reader:
        session = await reader.start_inventory(InventoryMode.ANSWER, queue_size=1)
        await anext(session)
        with pytest.raises(QueueOverflow):
            await anext(session)
        out = await session.stop()
        assert out.received_count == 3 and out.dropped_count == 2
        assert out.outcome is Outcome.PARTIAL and reader.state is ReaderState.IDLE


async def test_parser_loss_means_partial_even_after_valid_final():
    t = FakeTransport(lambda cmd, data: b"\0" + response(cmd, b"\1\0", status=1))
    async with ZKReader(t) as reader:
        out = await reader.inventory_once()
        assert out.outcome is Outcome.PARTIAL and not out.complete
