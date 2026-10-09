import asyncio
import pytest
from tests.conftest import FakeTransport, response
from zk_rfid import ZKReader, InventoryConfig, InventoryData, Outcome, ReaderCapabilities

pytestmark = pytest.mark.asyncio


async def test_buffer_counts_then_multiframe_identifiers_and_read_counts():
    def peer(cmd, data):
        if cmd == 0x18:
            return response(cmd, bytes.fromhex("00020005"))
        if cmd == 0x72:
            return response(cmd, bytes.fromhex("010102ABCD5503"), status=3) + response(
                cmd, bytes.fromhex("01020201234A02"), status=1
            )

    async with ZKReader(
        FakeTransport(peer), capabilities=ReaderCapabilities(antenna_ports=4)
    ) as reader:
        counts = (
            await reader.inventory_to_buffer(InventoryConfig(scan_time_100ms=3))
        ).require_success()
        assert counts.stored_tags == 2 and counts.round_reads == 5
        out = await reader.read_buffer()
        assert out.complete and out.unique_count == 2
        assert out.reports[0].epc == bytes.fromhex("ABCD")
        assert out.reports[0].read_count == 3 and out.reports[1].antenna_mask == 2


async def test_buffer_timeout_preserves_received_tid():
    t = FakeTransport(lambda cmd, data: response(cmd, bytes.fromhex("010102E2805501"), status=3))
    async with ZKReader(t) as reader:
        out = await reader.read_buffer(data_kind=InventoryData.TID, timeout=0.03)
        assert out.outcome is Outcome.PARTIAL and not out.complete
        assert out.reports[0].tid == bytes.fromhex("E280")
        assert out.reports[0].epc is None


async def test_buffer_cancel_retains_partial_outcome():
    t = FakeTransport(lambda cmd, data: response(cmd, bytes.fromhex("010102E2805501"), status=3))
    async with ZKReader(t) as reader:
        task = asyncio.create_task(reader.read_buffer())
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert reader.last_inventory_outcome.outcome is Outcome.PARTIAL
        assert len(reader.last_inventory_outcome.reports) == 1
