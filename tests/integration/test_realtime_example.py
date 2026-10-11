"""Run the optional example without hardware and verify final queue delivery."""

import importlib.util
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, ModulePeer, response
from zk_rfid import ZKReader

SPEC = importlib.util.spec_from_file_location(
    "realtime_example", Path(__file__).parents[2] / "examples/inventory_realtime.py"
)
example = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example)


@pytest.mark.asyncio
@pytest.mark.parametrize("trigger", [False, True])
@pytest.mark.parametrize("tid", [False, True])
async def test_realtime_example_drains_final_report_and_uses_existing_data_kind(
    capsys, trigger, tid
):
    peer = ModulePeer()

    def handle(cmd, data):
        if cmd == 0x77:
            return response(
                cmd,
                bytes((peer.mode, 0, 0, 0, 4, 0, 0, 0, 0, 0))
                + bytes(33)
                + bytes((2 if tid else 0,)),
            )
        reply = peer(cmd, data)
        if cmd == 0x76:
            assert data[0] & 0x80  # Neither Start nor Stop persists a mode.
            return response(0xEE, peer.tag) + reply
        return reply

    transport = FakeTransport(handle)
    async with ZKReader(transport) as reader:
        outcome = await example.read_tags(reader, seconds=0.01, trigger=trigger)
    output = capsys.readouterr().out
    assert outcome.complete and outcome.received_count == 2
    assert output.count("TagReport(") == 2
    assert ("epc=None" if tid else "tid=None") in output
    assert [w[3] for w in transport.writes if w[2] == 0x76] == [0x82 if trigger else 0x81, 0x80]
