"""Work-mode ownership, persistence, and Stop boundaries; synthetic UART peers."""

import asyncio

import pytest

import zk_rfid as sdk
from tests.conftest import FakeTransport, ModulePeer, response


class ModePeer(ModulePeer):
    def __init__(self, mode=0):
        super().__init__()
        self.mode = self.boot_mode = mode

    def __call__(self, command, data):
        if command == 0x76 and not data[0] & 0x80:
            self.boot_mode = data[0]
        return super().__call__(command, data)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [0, 1, 2])
@pytest.mark.parametrize("persist", [False, True])
async def test_mode_save_flag_and_readback(mode, persist):
    peer = ModePeer()
    transport = FakeTransport(peer, fragment=1)
    async with sdk.ZKReader(transport) as reader:
        assert (await reader.set_working_mode(mode, persist=persist)).ok
        assert transport.writes[0][3] == mode | (0 if persist else 0x80)
        assert (await reader.get_working_mode()).require_success().mode == mode
        assert peer.boot_mode == (mode if persist else 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("persist", [None, 1, "false"])
async def test_invalid_persist_never_transmits(persist):
    transport = FakeTransport(ModePeer())
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.ValidationError):
            await reader.set_working_mode(0, persist=persist)
    assert transport.writes == []


@pytest.mark.asyncio
async def test_save_failure_invalidates_cached_mode_before_inventory():
    peer = ModePeer()

    def handle(cmd, data):
        reply = peer(cmd, data)
        return response(cmd, status=0x13) if cmd == 0x76 else reply

    transport = FakeTransport(handle)
    async with sdk.ZKReader(transport) as reader:
        assert (await reader.get_working_mode()).require_success().mode == 0
        result = await reader.set_working_mode(1, persist=True)
        assert result.outcome is sdk.Outcome.PARTIAL
        with pytest.raises(sdk.StateError, match="Answer working mode"):
            await reader.inventory_once()
        assert [w[2] for w in transport.writes] == [0x77, 0x76, 0x77]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [1, 2])
@pytest.mark.parametrize("operation", ["answer", "scenario", "answer_session", "buffer"])
async def test_fresh_connection_blocks_inventory_in_autonomous_mode(mode, operation):
    peer = ModePeer(mode)
    original = dict(peer.cfg)
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.StateError, match="persist=False"):
            if operation == "answer":
                await reader.inventory_once()
            elif operation == "buffer":
                await reader.inventory_to_buffer()
            else:
                await reader.start_inventory(
                    sdk.InventoryMode.SCENARIO
                    if operation == "scenario"
                    else sdk.InventoryMode.ANSWER
                )
        assert [w[2] for w in transport.writes] == [0x77]
        assert peer.mode == peer.boot_mode == mode
        assert peer.cfg == original and reader._session is None


@pytest.mark.asyncio
async def test_explicit_switch_keeps_boot_mode_and_allows_scenario():
    peer = ModePeer(1)
    async with sdk.ZKReader(FakeTransport(peer)) as reader:
        (await reader.set_working_mode(sdk.WorkingMode.ANSWER)).require_success()
        session = await reader.start_inventory()
        assert (await session.stop()).complete
        assert len(session.drain()) == 2
        assert session.drain() == ()
        assert peer.mode == 0 and peer.boot_mode == 1


@pytest.mark.asyncio
async def test_managed_realtime_does_not_change_boot_mode():
    peer = ModePeer(2)
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        session = await reader.start_inventory(sdk.InventoryMode.REAL_TIME)
        assert peer.mode == 1 and peer.boot_mode == 2
        assert (await session.stop()).complete
        assert peer.mode == 0 and peer.boot_mode == 2
        assert [w[3] for w in transport.writes if w[2] == 0x76] == [0x81, 0x80]


# Exact final report supplied by the operator. Valid CRC, invalid one-port antenna.
OPERATOR_TAIL = bytes.fromhex(
    "18 00 EE 00 62 10 E2 80 11 11 22 22 33 33 44 44 55 55 66 66 77 77 68 49 A8"
)


@pytest.mark.asyncio
@pytest.mark.parametrize("fragment", [1, 4096])
async def test_operator_stop_tail_is_retained_without_becoming_a_tag(fragment):
    peer = ModePeer()

    def handle(cmd, data):
        reply = peer(cmd, data)
        return reply + OPERATOR_TAIL if cmd == 0x76 and data == b"\x80" else reply

    async with sdk.ZKReader(FakeTransport(handle, fragment=fragment)) as reader:
        session = await reader.start_inventory(sdk.InventoryMode.REAL_TIME)
        outcome = await session.stop()
        assert outcome.outcome is sdk.Outcome.PARTIAL and not outcome.complete
        assert outcome.termination_reason == "stopped"
        assert outcome.quarantined_count == 1
        assert outcome.quarantined_frames[0].raw == OPERATOR_TAIL
        assert session.drain() == () and outcome.received_count == 0
        assert reader.state is sdk.ReaderState.IDLE
        with pytest.raises(sdk.ProtocolError, match="antenna"):
            sdk.decode_stream(outcome.quarantined_frames[0].data, ports=1, scenario=False)
        next_session = await reader.start_inventory()
        assert (await anext(next_session)).epc == bytes.fromhex("DEADBEEF")
        assert (await next_session.stop()).complete


@pytest.mark.asyncio
async def test_report_after_settle_window_still_faults_connection():
    peer = ModePeer()
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        session = await reader.start_inventory()
        assert (await session.stop()).complete
        transport.feed(response(0xEE, peer.tag))
        await asyncio.sleep(0)
        assert reader.state is sdk.ReaderState.UNKNOWN
        with pytest.raises(sdk.StateError):
            await reader.start_inventory()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["rejected", "timeout", "readback", "partial_frame"])
async def test_failed_realtime_stop_stays_unknown(failure):
    peer = ModePeer()
    stopping = False

    def handle(cmd, data):
        nonlocal stopping
        if cmd == 0x76 and data == b"\x80":
            stopping = True
            if failure == "rejected":
                return response(cmd, status=0xF9)
            if failure == "timeout":
                return None
            if failure == "readback":
                return response(cmd)  # ACK without applying the mode.
            return peer(cmd, data) + b"\x18\x00"
        return peer(cmd, data)

    transport = FakeTransport(handle)
    async with sdk.ZKReader(transport, timeout=0.1) as reader:
        session = await reader.start_inventory(sdk.InventoryMode.REAL_TIME)
        result = await session.stop()
        assert stopping and not result.complete
        assert result.outcome is sdk.Outcome.UNKNOWN
        assert reader.state is sdk.ReaderState.UNKNOWN
        assert session.drain() == ()


@pytest.mark.asyncio
async def test_cancelled_consumer_does_not_steal_a_queued_report():
    peer = ModePeer()
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        session = await reader.start_inventory(sdk.InventoryMode.REAL_TIME)
        with pytest.raises(sdk.StateError, match="Stop"):
            session.drain()
        task = asyncio.create_task(anext(session))
        await asyncio.sleep(0)
        transport.feed(response(0xEE, peer.tag))
        # RX is queued before cancellation, but the consumer must not remove data.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        outcome = await session.stop()
        reports = session.drain()
        assert outcome.complete and outcome.received_count == len(reports) == 1
        assert reports[0].epc == bytes.fromhex("DEADBEEF")


@pytest.mark.asyncio
async def test_reconnect_forgets_mode_cache():
    peer = ModePeer()
    transport = FakeTransport(peer)
    reader = sdk.ZKReader(transport)
    async with reader:
        session = await reader.start_inventory()
        assert (await session.stop()).complete
    peer.mode = 1
    async with reader:
        transport.feed(response(0xEE, peer.tag))
        await asyncio.sleep(0)
        assert reader.dispatcher.fault is None
        with pytest.raises(sdk.StateError, match="Answer working mode"):
            await reader.inventory_once()


@pytest.mark.asyncio
async def test_cancelling_stop_waits_for_cleanup_and_preserves_queue():
    peer = ModePeer()
    async with sdk.ZKReader(FakeTransport(peer)) as reader:
        session = await reader.start_inventory()
        task = asyncio.create_task(session.stop())
        await asyncio.sleep(0.01)  # Stop is settling, not yet restoring CFG.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert session.outcome.complete and reader.state is sdk.ReaderState.IDLE
        assert len(session.drain()) == 2
        assert await session.stop() is session.outcome


@pytest.mark.asyncio
async def test_persistent_post_ack_stream_exceeds_bounded_stop_window():
    peer = ModePeer()
    pump = None

    async def send_forever():
        while True:
            transport.feed(response(0xEE, peer.tag) * 2)
            await asyncio.sleep(0.01)

    def handle(cmd, data):
        nonlocal pump
        if cmd == 0x51:
            pump = asyncio.create_task(send_forever())
            return response(cmd)
        return peer(cmd, data)

    transport = FakeTransport(handle)
    async with sdk.ZKReader(transport) as reader:
        session = await reader.start_inventory()
        try:
            result = await asyncio.wait_for(session.stop(), 1)
            assert result.outcome is sdk.Outcome.UNKNOWN
            assert result.quarantined_count > 32
            assert len(result.quarantined_frames) == 32
            assert "quiet" in " ".join(result.diagnostics)
        finally:
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)


@pytest.mark.asyncio
async def test_delayed_fragmented_tail_is_quarantined_before_restore():
    peer = ModePeer()
    tail = response(0xEE, peer.tag)

    def handle(cmd, data):
        if cmd == 0x51:
            loop = asyncio.get_running_loop()
            loop.call_later(0.01, transport.feed, tail[:5])
            loop.call_later(0.03, transport.feed, tail[5:])
            return response(cmd)
        return peer(cmd, data)

    transport = FakeTransport(handle)
    original = dict(peer.cfg)
    async with sdk.ZKReader(transport) as reader:
        session = await reader.start_inventory()
        result = await session.stop()
        assert result.outcome is sdk.Outcome.PARTIAL
        assert result.quarantined_count == 1 and result.quarantined_frames[0].raw == tail
        assert peer.cfg == original and reader.state is sdk.ReaderState.IDLE


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_mode", [1, 2])
@pytest.mark.parametrize("fragmented", [False, True])
async def test_direct_answer_switch_quarantines_old_stream_before_scenario(
    initial_mode, fragmented
):
    peer = ModePeer(initial_mode)
    tail = response(0xEE, bytes.fromhex("0104FACEFEED55"))

    def handle(cmd, data):
        if cmd == 0x76 and data == b"\x80":
            loop = asyncio.get_running_loop()
            if fragmented:
                loop.call_later(0.01, transport.feed, tail[:5])
                loop.call_later(0.03, transport.feed, tail[5:])
            else:
                loop.call_later(0.01, transport.feed, tail)
        return peer(cmd, data)

    transport = FakeTransport(handle)
    async with sdk.ZKReader(transport) as reader:
        # Cache is initially unknown: the public switch must still settle.
        result = await reader.set_working_mode(sdk.WorkingMode.ANSWER)
        assert result.ok and result.confirmation is sdk.Confirmation.READ_BACK
        assert reader.last_result is result
        assert [step.command for step in result.steps] == [0x76, 0x77]
        assert "Quarantined 1" in " ".join(result.diagnostics)
        assert reader.dispatcher.unsolicited[-1].raw == tail
        session = await reader.start_inventory()
        outcome = await session.stop()
        assert outcome.complete and outcome.received_count == 2
        assert all(report.epc == bytes.fromhex("DEADBEEF") for report in session.drain())
        assert peer.boot_mode == initial_mode


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["readback", "readback_rejected", "partial_frame", "timeout"])
async def test_direct_answer_switch_failure_blocks_next_inventory(failure):
    peer = ModePeer(1)

    def handle(cmd, data):
        if cmd == 0x76:
            if failure == "timeout":
                return None
            if failure == "readback":
                return response(cmd)
            reply = peer(cmd, data)
            return reply + b"\x18\x00" if failure == "partial_frame" else reply
        if cmd == 0x77 and failure == "readback_rejected":
            return response(cmd, status=0xF9)
        return peer(cmd, data)

    async with sdk.ZKReader(FakeTransport(handle), timeout=0.05) as reader:
        result = await reader.set_working_mode(sdk.WorkingMode.ANSWER)
        assert result.outcome is sdk.Outcome.UNKNOWN and reader.last_result is result
        assert reader.state is sdk.ReaderState.UNKNOWN
        with pytest.raises(sdk.StateError):
            await reader.start_inventory()


@pytest.mark.asyncio
async def test_direct_answer_switch_preserves_save_failure_after_runtime_readback():
    peer = ModePeer(1)

    def handle(cmd, data):
        reply = peer(cmd, data)
        return response(cmd, status=0x13) if cmd == 0x76 else reply

    async with sdk.ZKReader(FakeTransport(handle)) as reader:
        result = await reader.set_working_mode(sdk.WorkingMode.ANSWER, persist=True)
        assert result.outcome is sdk.Outcome.PARTIAL and result.status == 0x13
        assert result.confirmation is sdk.Confirmation.READ_BACK
        assert result.steps[-1].data.mode is sdk.WorkingMode.ANSWER
        assert result.diagnostics


@pytest.mark.asyncio
async def test_direct_switch_rejects_frame_arriving_after_cleanup():
    peer = ModePeer(1)
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        assert (await reader.set_working_mode(sdk.WorkingMode.ANSWER)).ok
        transport.feed(response(0xEE, peer.tag))
        await asyncio.sleep(0)
        assert reader.state is sdk.ReaderState.UNKNOWN


@pytest.mark.asyncio
async def test_cancelled_direct_switch_does_not_claim_a_clean_boundary():
    peer = ModePeer(1)
    transport = FakeTransport(peer)
    async with sdk.ZKReader(transport) as reader:
        task = asyncio.create_task(reader.set_working_mode(sdk.WorkingMode.ANSWER))
        while not transport.writes:
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert reader.state is sdk.ReaderState.UNKNOWN
        assert reader._working_mode is None
        with pytest.raises(sdk.StateError):
            await reader.start_inventory()


@pytest.mark.asyncio
async def test_rejected_direct_switch_does_not_retry_or_start_scenario():
    peer = ModePeer(1)
    transport = FakeTransport(
        lambda cmd, data: response(cmd, status=0xF9) if cmd == 0x76 else peer(cmd, data)
    )
    async with sdk.ZKReader(transport) as reader:
        result = await reader.set_working_mode(sdk.WorkingMode.ANSWER)
        assert result.outcome is sdk.Outcome.FAILURE and result.status == 0xF9
        with pytest.raises(sdk.StateError):
            await reader.start_inventory()
        assert [wire[2] for wire in transport.writes] == [0x76, 0x77]


@pytest.mark.asyncio
async def test_answer_interrupt_write_failure_still_finalizes_and_drains():
    peer = ModePeer()
    received = asyncio.Event()

    def handle(cmd, data):
        if cmd == 1:
            received.set()
            return response(1, bytes.fromhex("010102ABCD60"), status=3)
        if cmd == 0x93:
            raise OSError("Serial write failed during Answer interrupt")
        return peer(cmd, data)

    async with sdk.ZKReader(FakeTransport(handle)) as reader:
        session = await reader.start_inventory(sdk.InventoryMode.ANSWER)
        await received.wait()
        await asyncio.sleep(0)
        outcome = await session.stop()
        assert outcome.outcome is sdk.Outcome.UNKNOWN and not outcome.complete
        assert outcome.termination_reason == "stop_unconfirmed"
        assert reader.state is sdk.ReaderState.UNKNOWN and reader._session is None
        assert session._task.done()
        assert "interrupt" in " ".join(outcome.diagnostics)
        assert [tag.epc for tag in session.drain()] == [bytes.fromhex("ABCD")]
        assert await session.stop() is outcome
        assert session.drain() == ()


@pytest.mark.asyncio
async def test_repeated_stop_cancellation_waits_for_cleanup():
    async with sdk.ZKReader(FakeTransport(ModePeer())) as reader:
        session = await reader.start_inventory()
        task = asyncio.create_task(session.stop())
        await asyncio.sleep(0.005)
        task.cancel()
        await asyncio.sleep(0.005)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert session.outcome.complete and reader._session is None
        assert len(session.drain()) == 2
