import pytest
from zk_rfid import ZKReader, ReaderCapabilities, UnverifiedFeature, Outcome
from zk_rfid.compat.nation import NationAdapter
from tests.conftest import FakeTransport, response

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
