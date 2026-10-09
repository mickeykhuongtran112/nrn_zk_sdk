import asyncio

import pytest

from tests.conftest import FakeTransport, response
from zk_rfid import Dispatcher, RequestTimeout, StateError, TransportError

pytestmark = pytest.mark.asyncio


async def test_pending_registered_before_fast_response_short_write_and_single_rx():
    transport = FakeTransport(lambda cmd, data: response(cmd, b"\x11"), fragment=1, short_write=2)
    d = Dispatcher(transport)
    await d.open()
    try:
        results = await asyncio.gather(*(d.exchange(0x47) for _ in range(12)))
        assert all(r[0].data == b"\x11" for r in results)
        assert transport.max_readers == 1
        assert len(transport.writes) == 12
    finally:
        await d.close()
    assert transport.readers == 0


async def test_wrong_address_ignored_broadcast_learns_actual_address():
    t = FakeTransport(lambda cmd, data: response(cmd, b"\1", address=7))
    d = Dispatcher(t, address=255)
    await d.open()
    try:
        assert (await d.exchange(0x47))[0].address == 7
        assert d.address == 7
        t.handler = lambda cmd, data: (
            response(cmd, b"\2", address=6) + response(cmd, b"\3", address=7)
        )
        assert (await d.exchange(0x47))[0].data == b"\3"
        assert d.parser.diagnostics.unexpected_frames == 1
    finally:
        await d.close()


async def test_timeout_poison_and_late_response_cannot_satisfy_next_request():
    t = FakeTransport()
    d = Dispatcher(t)
    await d.open()
    try:
        with pytest.raises(RequestTimeout) as err:
            await d.exchange(3, timeout=0.015)
        assert err.value.transmitted
        t.feed(response(3))
        await asyncio.sleep(0)
        with pytest.raises(StateError):
            await d.exchange(3)
        assert len(t.writes) == 1
    finally:
        await d.close()
    with pytest.raises(StateError):
        await d.open()


async def test_cancel_preserves_uncertainty_without_retry():
    t = FakeTransport()
    d = Dispatcher(t)
    await d.open()
    try:
        task = asyncio.create_task(d.exchange(3))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert d.fault and d.last_exchange_error.transmitted
        assert len(t.writes) == 1
    finally:
        await d.close()


async def test_stop93_bypasses_pending_and_does_not_wait_for_own_ack():
    t = FakeTransport(lambda cmd, data: response(1, b"\1\0", status=1) if cmd == 0x93 else None)
    d = Dispatcher(t)
    await d.open()
    try:
        task = asyncio.create_task(d.exchange(1, terminal=lambda f: f.status != 3))
        await asyncio.sleep(0)
        assert await d.interrupt_answer()
        assert (await task)[0].status == 1
        assert [w[2] for w in t.writes] == [1, 0x93]
    finally:
        await d.close()


async def test_notifications_routed_separately_and_unknown_command_response():
    t = FakeTransport(
        lambda cmd, data: response(0xEE, b"\1\2\xaa\xbb\x60") + response(0, status=0xFE)
    )
    d = Dispatcher(t)
    seen = []
    d.on_notification = seen.append
    await d.open()
    try:
        frames = await d.exchange(0x21)
        assert frames[0].status == 0xFE and len(seen) == 1
    finally:
        await d.close()


async def test_disconnect_preserves_previous_frames():
    t = FakeTransport(lambda cmd, data: response(1, b"\1\0", status=3))
    d = Dispatcher(t)
    await d.open()
    try:
        task = asyncio.create_task(d.exchange(1, terminal=lambda f: f.status != 3))
        await asyncio.sleep(0.01)
        t.rx.put_nowait(b"")
        with pytest.raises(TransportError) as err:
            await task
        assert len(err.value.frames) == 1
    finally:
        await d.close()


async def test_unsolicited_reply_after_ack_poisoned():
    t = FakeTransport(lambda cmd, data: response(cmd) + response(cmd))
    d = Dispatcher(t)
    await d.open()
    try:
        await d.exchange(0x2F, b"\x90")
        assert d.fault is not None
        with pytest.raises(StateError):
            await d.exchange(0x2F, b"\x90")
    finally:
        await d.close()
