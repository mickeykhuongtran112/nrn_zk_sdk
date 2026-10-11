"""Start/Stop races and browser outcome retention; no physical serial port."""

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, ModulePeer, response
from zk_rfid import (
    InventoryMode,
    OperationError,
    Outcome,
    ReaderCapabilities,
    ReaderState,
    StateError,
    ValidationError,
    UnsupportedFeature,
    ZKReader,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("cancel_stop", [False, True])
async def test_stop_waits_for_start_preflight_and_cleans_up_even_if_cancelled(cancel_stop):
    peer = ModulePeer()
    original = dict(peer.cfg)
    queried = asyncio.Event()

    def handle(cmd, data):
        if cmd == 0x77:
            queried.set()
            return None
        return peer(cmd, data)

    t = FakeTransport(handle)
    async with ZKReader(t) as reader:
        start = asyncio.create_task(reader.start_inventory())
        await asyncio.wait_for(queried.wait(), 1)
        stop = asyncio.create_task(reader.stop_inventory())
        await asyncio.sleep(0)
        assert not stop.done()
        with pytest.raises(StateError, match="Start/Stop/close"):
            await reader.start_inventory()
        if cancel_stop:
            stop.cancel()
        t.feed(peer(0x77, b""))
        session = await start
        if cancel_stop:
            with pytest.raises(asyncio.CancelledError):
                await stop
            result = session.outcome
        else:
            result = await stop
        assert result.complete and result.outcome is Outcome.SUCCESS
        assert reader.state is ReaderState.IDLE and peer.cfg == original
        assert [w[2] for w in t.writes].count(0x50) == 1
        assert [w[2] for w in t.writes].count(0x51) == 1


async def test_close_waits_for_pending_start_then_stops_reader():
    peer = ModulePeer()
    queried = asyncio.Event()

    def handle(cmd, data):
        if cmd == 0x77:
            queried.set()
            return None
        return peer(cmd, data)

    t = FakeTransport(handle)
    reader = await ZKReader(t).open()
    start = asyncio.create_task(reader.start_inventory())
    await asyncio.wait_for(queried.wait(), 1)
    closing = asyncio.create_task(reader.close())
    await asyncio.sleep(0)
    assert not closing.done()
    t.feed(peer(0x77, b""))
    session = await start
    await closing
    assert session.outcome.complete and not t.opened
    assert reader.state is ReaderState.DISCONNECTED


async def test_stop_after_pending_start_timeout_remains_unknown():
    t = FakeTransport()
    async with ZKReader(t, timeout=0.03) as reader:
        start = asyncio.create_task(reader.start_inventory())
        await asyncio.sleep(0)
        stop = asyncio.create_task(reader.stop_inventory())
        with pytest.raises(OperationError):
            await start
        result = await stop
        assert result.outcome is Outcome.UNKNOWN and not result.complete
        assert [w[2] for w in t.writes] == [0x77]


@pytest.mark.parametrize("mask", [0, 2, -1, True, 1.0])
async def test_one_port_rejects_invalid_scenario_mask_before_io(mask):
    t = FakeTransport()
    async with ZKReader(t) as reader:
        with pytest.raises(ValidationError):
            await reader.start_inventory(antenna_mask=mask)
        assert t.writes == []


@pytest.mark.parametrize("mode", [InventoryMode.ANSWER, InventoryMode.REAL_TIME])
async def test_mask_is_not_silently_ignored_by_other_modes(mode):
    t = FakeTransport()
    async with ZKReader(t) as reader:
        with pytest.raises(UnsupportedFeature):
            await reader.start_inventory(mode, antenna_mask=1)
        assert t.writes == []


async def test_browser_autostop_preserves_partial_result_tail_and_state():
    spec = importlib.util.spec_from_file_location(
        "browser_review", Path(__file__).parents[2] / "web/zk_browser.py"
    )
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    peer = ModulePeer()
    t = FakeTransport(
        lambda cmd, data: (
            response(0xEE, peer.tag) * 3 + response(cmd) if cmd == 0x50 else peer(cmd, data)
        )
    )
    async with ZKReader(t) as reader:
        browser = bridge.BrowserReader.__new__(bridge.BrowserReader)
        browser.reader, browser.session, browser.consumer = reader, None, None
        events = []
        browser.notify = lambda kind, data: events.append((kind, json.loads(data)))
        assert json.loads(await browser.call("start_inventory", '{"queue_size": 1}'))["ok"]
        await asyncio.wait_for(browser.consumer, 1)
        assert browser.session.outcome.dropped_count == 2
        for _ in range(2):
            result = json.loads(await browser.call("stop_inventory", "{}"))["data"]
            assert result["outcome"] == "partial" and not result["complete"]
            assert result["dropped_count"] == 2
        assert ("state", {"state": "idle"}) in events
        assert next(data for kind, data in events if kind == "error")["inventory_outcome"] == result
        assert len([kind for kind, _ in events if kind == "tag"]) == 2
        # A later connection fault must override a historical partial/success result.
        reader.dispatcher._fail(StateError("connection lost"))
        result = json.loads(await browser.call("stop_inventory", "{}"))["data"]
        assert result["outcome"] == "unknown"


@pytest.mark.parametrize("ports", [1, 4])
async def test_browser_fastid_antenna_error_stops_and_preserves_failed_outcome(ports):
    spec = importlib.util.spec_from_file_location(
        "browser_fastid_error", Path(__file__).parents[2] / "web/zk_browser.py"
    )
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    peer = ModulePeer()
    t = FakeTransport(
        lambda cmd, data: (
            response(1, bytes.fromhex("010102ABCD60"), 3) + response(1, status=0xF8)
            if cmd == 1
            else peer(cmd, data)
        )
    )
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=ports)) as reader:
        browser = bridge.BrowserReader.__new__(bridge.BrowserReader)
        browser.reader, browser.session, browser.consumer = reader, None, None
        events = []
        browser.notify = lambda kind, data: events.append((kind, json.loads(data)))
        args = json.dumps(
            {
                "mode": "answer",
                "config": {"data": "fastid"},
                "antenna_sequence": [1] if ports == 1 else [1, 3, 4],
            }
        )
        assert json.loads(await browser.call("start_inventory", args))["ok"]
        await asyncio.wait_for(browser.consumer, 1)
        error = next(data for kind, data in events if kind == "error")
        assert error["type"] == "DeviceError"
        assert error["inventory_outcome"]["status"] == 0xF8
        assert not error["inventory_outcome"]["complete"]
        assert reader.state is ReaderState.IDLE
        assert [w[2] for w in t.writes].count(1) == 1
        assert len([kind for kind, _ in events if kind == "tag"]) == 1
        for _ in range(2):
            stopped = json.loads(await browser.call("stop_inventory", "{}"))["data"]
            assert stopped == error["inventory_outcome"]
        assert browser.session.drain() == ()
