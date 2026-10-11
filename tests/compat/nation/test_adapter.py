import asyncio

import pytest

from tests.conftest import FakeTransport, ModulePeer, response
from mapping.nation_to_zk import NationAdapter
from zk_rfid import (
    Outcome,
    InventoryMode,
    ProtocolError,
    ReaderCapabilities,
    ReaderState,
    UnsupportedFeature,
    UnverifiedFeature,
    ValidationError,
    ZKReader,
)

pytestmark = pytest.mark.asyncio


async def test_partial_power_patch_preserves_other_antennas():
    t = FakeTransport(
        lambda cmd, data: response(cmd, bytes((10, 11, 12, 13)) if cmd == 0x94 else b"")
    )
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as r:
        adapter = NationAdapter(r)
        result = await adapter.configure_reader_power({2: 20})
        assert result.ok and t.writes[-1][3:-2] == bytes((138, 148, 140, 141))
        assert len(result.steps) == 2


async def test_rf_is_not_mapped_by_id_and_errors_preserved():
    t = FakeTransport(lambda cmd, data: response(cmd, status=0xF8))
    async with ZKReader(t) as r:
        a = NationAdapter(r)
        with pytest.raises(UnverifiedFeature):
            await a.select_profile(1)
        assert t.writes == []
        result = await a.query_reader_power()
        assert result.outcome is Outcome.FAILURE and result.status == 0xF8


async def test_scenario_default_and_final_reports_survive_relocation():
    peer = ModulePeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer, fragment=1)
    async with ZKReader(t) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode([1])
        first = await anext(session)
        assert first.epc == bytes.fromhex("DEADBEEF")
        outcome = await adapter.stop_inventory()
        final = session.drain()
        assert outcome.complete and outcome.outcome is Outcome.SUCCESS
        assert len(final) == 1 and final[0].epc == first.epc
        assert peer.cfg == before
        assert [w[2] for w in t.writes].count(0x50) == 1
        assert [w[2] for w in t.writes].count(0x51) == 1
        assert not any(w[2] in (0x01, 0x76, 0x7F, 0x22) for w in t.writes)


async def test_callback_error_still_stops_and_restores_scenario():
    peer = ModulePeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer)

    async def broken_callback(tag):
        assert tag["epc"] == "DEADBEEF"
        raise RuntimeError("application callback failed")

    async with ZKReader(t) as reader:
        with pytest.raises(RuntimeError, match="application callback failed"):
            await NationAdapter(reader).run_inventory([1], broken_callback, duration=1)
        assert not reader.is_inventory_running
        assert peer.cfg == before
        assert any(w[2] == 0x51 for w in t.writes)


@pytest.mark.parametrize("callback_kind", ["sync", "async", "nested_timeout", "duration_cancel"])
async def test_callback_timeout_is_propagated_after_stop_and_restore(callback_kind):
    peer = ModulePeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer)
    failure = TimeoutError("application callback timed out")

    def sync_callback(tag):
        raise failure

    async def async_callback(tag):
        if callback_kind == "duration_cancel":
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError as error:
                raise failure from error
        if callback_kind == "nested_timeout":
            try:
                async with asyncio.timeout(0.01):
                    await asyncio.Event().wait()
            except TimeoutError as error:
                raise failure from error
        await asyncio.sleep(0)
        raise failure

    callback = sync_callback if callback_kind == "sync" else async_callback
    async with ZKReader(t) as reader:
        with pytest.raises(TimeoutError) as raised:
            await NationAdapter(reader).run_inventory(
                [1], callback, duration=0.02 if callback_kind == "duration_cancel" else 1
            )
        assert raised.value is failure
        assert peer.cfg == before and reader.state is ReaderState.IDLE
        assert [w[2] for w in t.writes].count(0x51) == 1


@pytest.mark.parametrize("failure_at", ["stop", "restore"])
async def test_callback_timeout_survives_incomplete_cleanup(failure_at):
    peer = FourPortPeer()
    original = dict(peer.cfg)

    def handle(cmd, data):
        if failure_at == "stop" and cmd == 0x51:
            return response(cmd, status=0xF8)
        if failure_at == "restore" and cmd == 0x3F and data == b"\x8f":
            return response(cmd, status=0xF8)
        return peer(cmd, data)

    t = FakeTransport(handle)
    failure = TimeoutError("callback deadline exceeded")

    def callback(tag):
        raise failure

    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        with pytest.raises(TimeoutError) as raised:
            await NationAdapter(reader).run_inventory([3], callback, duration=1)
        assert raised.value is failure
        assert reader.state is ReaderState.UNKNOWN
        assert peer.ant == 0b0100
        assert (peer.cfg == original) is (failure_at == "restore")
        sent = list(t.writes)
        out = await reader.stop_inventory()
        assert out.outcome is Outcome.UNKNOWN and not out.complete
        assert t.writes == sent


async def test_run_duration_expiry_returns_stop_outcome_and_restores():
    peer = ModulePeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer)
    tags = []
    async with ZKReader(t) as reader:
        outcome = await NationAdapter(reader).run_inventory([1], tags.append, duration=0.02)
        assert outcome.complete and outcome.outcome is Outcome.SUCCESS
        assert outcome.termination_reason == "stopped"
        assert len(tags) == 1 and tags[0]["epc"] == "DEADBEEF"
        assert peer.cfg == before and reader.state is ReaderState.IDLE
        assert [w[2] for w in t.writes].count(0x51) == 1


async def test_run_cancellation_propagates_after_stop_and_restore():
    peer = ModulePeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer)
    received = asyncio.Event()

    async def callback(tag):
        received.set()
        await asyncio.Event().wait()

    async with ZKReader(t) as reader:
        task = asyncio.create_task(NationAdapter(reader).run_inventory([1], callback, duration=5))
        await asyncio.wait_for(received.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert peer.cfg == before and reader.state is ReaderState.IDLE
        assert [w[2] for w in t.writes].count(0x51) == 1


class FourPortPeer(ModulePeer):
    """Synthetic four-port register state; not a hardware validation claim."""

    def __init__(self):
        super().__init__()
        self.ant = 0b1111
        self.powers = (10, 11, 12, 13)

    def __call__(self, command, data):
        if command == 0x94:
            return response(command, bytes(self.powers))
        if command == 0x2F:
            self.powers = tuple(value & 0x7F for value in data)
            return response(command)
        if command in (0x50, 0x51):
            return b"".join(
                response(0xEE, bytes((1 << index,)) + self.tag[1:])
                for index in range(4)
                if self.ant & (1 << index)
            ) + response(command)
        return super().__call__(command, data)


@pytest.mark.parametrize("port", [1, 2, 3, 4])
async def test_four_port_selection_reports_and_restore(port):
    peer = FourPortPeer()
    before = dict(peer.cfg)
    t = FakeTransport(peer, fragment=1)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode([port])
        report = await anext(session)
        assert report.antenna == port and peer.ant == 1 << (port - 1)
        out = await adapter.stop_inventory()
        assert out.complete and out.outcome is Outcome.SUCCESS
        assert [tag.antenna for tag in session.drain()] == [port]
        assert (await adapter.query_enabled_ant_mask()).require_success() == 0b1111
        assert peer.cfg == before and peer.powers == (10, 11, 12, 13)
        antenna_writes = [w[3:-2] for w in t.writes if w[2] == 0x3F]
        assert antenna_writes == [bytes((0x80 | (1 << (port - 1)),)), b"\x8f"]
        assert not any(w[2] in (0x2F, 0x7F, 0x22) for w in t.writes)


@pytest.mark.parametrize("port", [1, 2, 3, 4])
@pytest.mark.parametrize("persist", [False, True])
async def test_four_port_power_patch_readback_preserves_other_ports(port, persist):
    peer = FourPortPeer()
    t = FakeTransport(peer)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        (await adapter.configure_reader_power({port: 20}, persistence=persist)).require_success()
        expected = {1: 10, 2: 11, 3: 12, 4: 13}
        expected[port] = 20
        assert (await adapter.query_reader_power()).require_success() == expected
        payload = next(w[3:-2] for w in t.writes if w[2] == 0x2F)
        assert payload == bytes(value | (0 if persist else 0x80) for value in expected.values())
        assert peer.ant == 0b1111


async def test_concurrent_four_port_power_patches_preserve_both_updates():
    peer = FourPortPeer()
    async with ZKReader(
        FakeTransport(peer), capabilities=ReaderCapabilities(antenna_ports=4)
    ) as reader:
        adapter = NationAdapter(reader)
        results = await asyncio.gather(
            adapter.configure_reader_power({1: 18}), adapter.configure_reader_power({4: 22})
        )
        assert all(result.ok for result in results)
        assert (await adapter.query_reader_power()).require_success() == {
            1: 18,
            2: 11,
            3: 12,
            4: 22,
        }


@pytest.mark.parametrize("port", [1, 2, 3, 4])
async def test_four_port_disable_enable_preserves_other_bits(port):
    peer = FourPortPeer()
    t = FakeTransport(peer)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        (await adapter.disable_ant(port)).require_success()
        assert (await adapter.query_enabled_ant_mask()).require_success() == 15 & ~(1 << (port - 1))
        (await adapter.enable_ant(port)).require_success()
        assert (await adapter.query_enabled_ant_mask()).require_success() == 15
        assert peer.powers == (10, 11, 12, 13)
        assert all(not (w[3] & 0x80) for w in t.writes if w[2] == 0x3F)


async def test_four_port_rejects_last_port_disable_invalid_port_and_multiport_answer():
    peer = FourPortPeer()
    peer.ant = 0b0100
    t = FakeTransport(peer)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        with pytest.raises(ValidationError, match="antenna mask"):
            await adapter.disable_ant(3)
        assert peer.ant == 0b0100 and not any(w[2] == 0x3F for w in t.writes)
        sent = list(t.writes)
        with pytest.raises(ValidationError):
            await adapter.configure_reader_power({5: 20})
        with pytest.raises(ValidationError):
            await adapter.start_inventory_with_mode([5])
        with pytest.raises(UnsupportedFeature, match="require Scenario"):
            await adapter.start_inventory_with_mode([1, 4], mode=InventoryMode.REAL_TIME)
        assert t.writes == sent


@pytest.mark.parametrize("ports", [[1, 3, 4], [1, 2, 3, 4], [2, 4]])
async def test_multi_antenna_scenario_uses_one_start_and_restores_mask(ports):
    peer = FourPortPeer()
    peer.ant = 1
    original = dict(peer.cfg)
    t = FakeTransport(peer, fragment=1)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode(ports)
        assert peer.ant == sum(1 << (port - 1) for port in ports)
        assert [(await anext(session)).antenna for _ in ports] == ports
        out = await adapter.stop_inventory()
        assert out.complete
        assert [report.antenna for report in session.drain()] == ports
        assert peer.ant == 1 and peer.cfg == original
        assert peer.powers == (10, 11, 12, 13)
        assert [w[2] for w in t.writes].count(0x50) == 1
        assert [w[2] for w in t.writes].count(0x51) == 1


async def test_antenna_readback_mismatch_blocks_start_and_restores():
    peer = FourPortPeer()
    peer.ant = 1
    original = dict(peer.cfg)

    def handle(cmd, data):
        if cmd == 0x3F and data == b"\x8d":
            return response(cmd)  # ACK without applying the requested mask.
        return peer(cmd, data)

    t = FakeTransport(handle)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        with pytest.raises(ProtocolError, match="Antenna selection read-back mismatch"):
            await NationAdapter(reader).start_inventory_with_mode([1, 3, 4])
        assert peer.ant == 1 and peer.cfg == original
        assert not any(w[2] == 0x50 for w in t.writes)
        assert reader.state is ReaderState.IDLE


@pytest.mark.parametrize("failure", ["reject", "mismatch"])
async def test_multi_antenna_stop_restore_failure_remains_unknown(failure):
    peer = FourPortPeer()
    peer.ant = 1

    def handle(cmd, data):
        if cmd == 0x3F and data == b"\x81":
            return response(cmd, status=0xF9 if failure == "reject" else 0)
        return peer(cmd, data)

    t = FakeTransport(handle)
    async with ZKReader(t, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        adapter = NationAdapter(reader)
        session = await adapter.start_inventory_with_mode([1, 3, 4])
        assert peer.ant == 0b1101
        result = await adapter.stop_inventory()
        assert result.outcome is Outcome.UNKNOWN and not result.complete
        assert any("Restoration failed" in message for message in result.diagnostics)
        assert reader.state is ReaderState.UNKNOWN and peer.ant == 0b1101
        assert {report.antenna for report in session.drain()} == {1, 3, 4}
        sent = list(t.writes)
        assert (await adapter.stop_inventory()).outcome is Outcome.UNKNOWN
        assert t.writes == sent  # No guessed retry after failed restoration.


async def test_unapproved_generic_profile_and_unrepresentable_band_stay_blocked():
    t = FakeTransport()
    async with ZKReader(t) as reader:
        adapter = NationAdapter(reader)
        with pytest.raises(UnsupportedFeature):
            await adapter.set_rf_band(2)
        with pytest.raises(UnverifiedFeature):
            await adapter.select_profile(1)
        assert t.writes == []


async def test_cached_mask_and_persistence_difference_is_preserved():
    t = FakeTransport(ModulePeer())
    async with ZKReader(t) as reader:
        # The old adapter writes a saved mask; unlike the reference's host cache.
        result = await NationAdapter(reader).save_antenna_mask(1)
        assert result.ok
        assert t.writes[0][2:-2] == bytes.fromhex("3F01")
        assert t.writes[-1][2] == 0x21
