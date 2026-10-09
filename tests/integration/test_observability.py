import pytest
from zk_rfid import ZKReader, Outcome, ReaderState
from tests.conftest import FakeTransport, response

pytestmark = pytest.mark.asyncio


async def test_trace_correlates_request_chunks_frame_and_result():
    trace = []
    t = FakeTransport(
        lambda cmd, data: response(cmd, bytes.fromhex("12345678")), fragment=2, short_write=2
    )
    async with ZKReader(t, on_event=trace.append) as reader:
        result = await reader.get_serial_number()
        assert result.ok
    kinds = [e.kind for e in trace]
    assert "request" in kinds and "tx" in kinds and "rx" in kinds and "frame" in kinds
    assert "result" in kinds and "state" in kinds and kinds[-2:] == ["disconnected", "state"]
    request = next(e for e in trace if e.kind == "request")
    frame = next(e for e in trace if e.kind == "frame")
    assert request.exchange_id == frame.exchange_id == 1
    assert next(e for e in trace if e.kind == "result").exchange_id == request.exchange_id
    assert b"".join(e.raw for e in trace if e.kind == "tx") == request.raw
    assert frame.status == 0 and frame.command == 0x4C
    assert [e.sequence for e in trace] == list(range(1, len(trace) + 1))
    assert [e.timestamp for e in trace] == sorted(e.timestamp for e in trace)


async def test_broken_observer_cannot_fail_device_operation():
    def broken(event):
        raise RuntimeError("UI listener failed")

    async with ZKReader(
        FakeTransport(lambda c, d: response(c, bytes(4))), on_event=broken
    ) as reader:
        assert (await reader.get_serial_number()).ok
        assert reader.dispatcher.trace.observer_errors > 0
        assert reader.state is ReaderState.IDLE


async def test_timeout_has_fault_and_unknown_result_in_trace():
    trace = []
    async with ZKReader(FakeTransport(), timeout=0.02, on_event=trace.append) as reader:
        result = await reader.set_power(15)
        assert result.outcome is Outcome.UNKNOWN
        assert any(e.kind == "timeout" and e.exchange_id == 1 for e in trace)
        assert any(e.kind == "state" and e.detail.endswith("unknown") for e in trace)
        assert any(e.kind == "result" and "unknown" in e.detail for e in trace)
