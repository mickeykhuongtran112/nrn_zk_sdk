"""Connection discovery regressions use byte peers, never a serial device."""

import pytest

from tests.demo_app.controller import Controller
from tests.demo_app.records import EventLog
from tests.demo_app.simulator import DemoTransport
from tests.integration.test_demo_app import run


def commands(c):
    return [e["trace"]["command"] for e in c.log.events if e["kind"] == "tx"]


@pytest.mark.asyncio
@pytest.mark.parametrize("declared,actual", [(1, 4), (4, 1), (1, 8), (1, 16)])
async def test_discovery_corrects_declared_layout_before_power_and_inventory(declared, actual):
    peer = DemoTransport(actual)
    c = Controller(EventLog(), transport_factory=lambda _: peer)
    try:
        job = await run(c, "connect", {"ports": declared})
        assert job["state"] == "success"
        assert c.connection["requested_ports"] == declared
        assert c.connection["ports"] == actual == c.reader.capabilities.antenna_ports
        assert c.connection["ports_source"] == "reader_info_and_power"
        assert c.connection["model_code"] == peer.model_code
        # The enabled mask of 1 must not be mistaken for physical port count.
        assert peer.ant == 1 and peer.powers == [20] * actual and peer.mode == 0
        assert commands(c) == [0x21, 0x77, 0x94]
        assert not c.reader.capabilities.hardware_verified
        assert (await run(c, "get_power"))["result"]["data"] == [20] * actual
        if actual <= 4:
            start = await run(c, "start_inventory", {"antenna_mask": (1 << actual) - 1})
            assert start["state"] == "success"
            assert (await run(c, "stop_inventory"))["result"]["complete"]
            assert peer.ant == 1
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_unknown_type_uses_validated_power_layout_not_name_or_enabled_mask():
    peer = DemoTransport(4)
    peer.model_code = 0xEF
    c = Controller(EventLog(), transport_factory=lambda _: peer)
    try:
        job = await run(c, "connect", {"ports": 1, "model": "UHF7180M"})
        assert job["state"] == "success"
        assert c.connection["ports"] == c.reader.capabilities.antenna_ports == 4
        assert c.connection["reported_model"] is None
        assert c.connection["ports_source"] == "power_response"
        assert commands(c) == [0x21, 0x77, 0x94]
        assert (await run(c, "get_power"))["state"] == "success"
    finally:
        await c.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["conflict", "length", "value", "reject", "timeout"])
async def test_failed_discovery_closes_without_writes_or_silent_one_port_fallback(failure):
    class Peer(DemoTransport):
        async def handle(self, command, data):
            if command == 0x94 and failure in {"reject", "timeout"}:
                if failure == "reject":
                    self.send(command, status=0xF9)
                return
            await super().handle(command, data)

    peer = Peer(4)
    if failure == "conflict":
        peer.model_code = 0x71
    if failure == "length":
        peer.powers = [20] * 3
    if failure == "value":
        peer.powers[-1] = 31
    c = Controller(EventLog(), transport_factory=lambda _: peer)
    try:
        job = await run(c, "connect", {"port": "TEST", "ports": 1, "timeout": 0.03})
        assert job["state"] == ("unknown" if failure == "timeout" else "failure")
        assert not c.snapshot()["connected"] and not peer.opened
        assert commands(c) == [0x21, 0x77, 0x94]
        assert peer.ant == 1 and peer.mode == 0
        if failure == "timeout":
            assert c.recovery_required and "TEST" in c.uncertain_ports
        if failure == "conflict":
            assert "declares 1 ports" in job["error"]["message"]
    finally:
        await c.shutdown()


@pytest.mark.asyncio
@pytest.mark.parametrize("known", [True, False])
async def test_active_work_mode_uses_known_type_without_power_query_or_mode_write(known):
    peer = DemoTransport(4)
    peer.mode = 1
    if not known:
        peer.model_code = 0xEF
    c = Controller(EventLog(), transport_factory=lambda _: peer)
    try:
        job = await run(c, "connect", {"ports": 1})
        assert job["state"] == ("success" if known else "failure")
        assert commands(c) == [0x21, 0x77]
        assert peer.mode == 1
        if known:
            assert c.connection["ports"] == 4
            assert c.connection["ports_source"] == "reader_info"
            assert c.snapshot()["working_mode"] == 1
        else:
            assert not c.snapshot()["connected"]
            assert "Select the verified port count manually" in job["error"]["message"]
    finally:
        await c.shutdown()


@pytest.mark.asyncio
async def test_manual_layout_remains_available_without_automatic_commands():
    c = Controller(EventLog(), transport_factory=lambda _: DemoTransport(4))
    try:
        job = await run(c, "connect", {"ports": 4, "detect_ports": False})
        assert job["state"] == "success"
        assert c.connection["ports_source"] == "manual"
        assert c.reader.capabilities.antenna_ports == 4
        assert commands(c) == []
        assert (await run(c, "get_power"))["result"]["data"] == [20] * 4
    finally:
        await c.shutdown()
