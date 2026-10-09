import asyncio

import pytest

from tests.conftest import FakeTransport, response
from zk_rfid import Confirmation, MemoryBank, Outcome, RequestTimeout, TagMask, TagTarget, ZKReader

pytestmark = pytest.mark.asyncio
TARGET = TagTarget(mask=TagMask(MemoryBank.TID, 0, 16, bytes.fromhex("E280")))


async def test_queued_call_deadline_does_not_transmit_or_poison():
    t = FakeTransport(lambda cmd, data: response(cmd, bytes(4)))
    async with ZKReader(t, timeout=0.02) as r:
        async with r._operation():
            with pytest.raises(RequestTimeout) as error:
                await r.get_serial_number()
            assert not error.value.transmitted
        assert not t.writes and r.dispatcher.fault is None
        assert (await r.get_serial_number()).ok


async def test_cancel_readback_retains_acknowledged_write():
    read_started = asyncio.Event()

    def peer(cmd, data):
        if cmd == 2:
            read_started.set()
            return None
        return response(cmd)

    t = FakeTransport(peer)
    async with ZKReader(t) as r:
        task = asyncio.create_task(r.write_memory(3, 0, bytes((0, 1)), target=TARGET, verify=True))
        await read_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        result = r.last_result
        assert result.outcome is Outcome.PARTIAL
        assert result.confirmation is Confirmation.ACKNOWLEDGED
        assert result.steps[0].ok and result.steps[1].outcome is Outcome.UNKNOWN
        assert [w[2] for w in t.writes] == [3, 2]


async def test_whole_write_sequence_uses_one_deadline():
    t = FakeTransport()

    def peer(cmd, data):
        asyncio.get_running_loop().call_later(
            0.045, t.feed, response(cmd, bytes((0, 1)) if cmd == 2 else b"")
        )

    t.handler = peer
    async with ZKReader(t, timeout=1) as r:
        result = await r.write_memory(3, 0, bytes((0, 1)), target=TARGET, verify=True, timeout=0.07)
        assert result.outcome is Outcome.PARTIAL
        assert result.steps[0].ok
        assert result.steps[1].outcome is Outcome.UNKNOWN


async def test_buffer_lock_wait_uses_supplied_deadline():
    t = FakeTransport()
    async with ZKReader(t, timeout=1) as r:
        async with r._operation():
            with pytest.raises(RequestTimeout):
                await r.read_buffer(timeout=0.01)
        assert not t.writes
