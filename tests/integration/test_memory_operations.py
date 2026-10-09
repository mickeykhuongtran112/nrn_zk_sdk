import asyncio
import pytest
from zk_rfid import (
    ZKReader,
    MemoryBank,
    TagMask,
    TagTarget,
    Outcome,
    Confirmation,
    ValidationError,
    ReaderState,
    OperationError,
)
from tests.conftest import FakeTransport, response

pytestmark = pytest.mark.asyncio
TARGET = TagTarget(mask=TagMask(MemoryBank.TID, 0, 16, bytes.fromhex("E280")))


async def test_write_readback_and_single_rx():
    t = FakeTransport(lambda cmd, data: response(cmd, b"\0\x01" if cmd == 2 else b""))
    async with ZKReader(t) as r:
        result = await r.write_memory(3, 0, b"\0\x01", target=TARGET, verify=True)
        assert result.confirmation is Confirmation.READ_BACK and result.ok
        assert [w[2] for w in t.writes] == [3, 2]
        assert len(result.steps) == 2 and t.max_readers == 1


async def test_readback_mismatch_preserves_ack():
    async with ZKReader(
        FakeTransport(lambda cmd, data: response(cmd, b"\xff\xff" if cmd == 2 else b""))
    ) as r:
        result = await r.write_memory(3, 0, b"\0\x01", target=TARGET, verify=True)
        assert result.outcome is Outcome.PARTIAL
        assert result.confirmation is Confirmation.ACKNOWLEDGED
        with pytest.raises(OperationError):
            result.require_success()


async def test_timeout_after_write_is_unknown_never_retried():
    t = FakeTransport()
    async with ZKReader(t, timeout=0.02) as r:
        result = await r.write_memory(3, 0, b"\0\x01", target=TARGET, verify=True)
        assert result.outcome is Outcome.UNKNOWN and len(t.writes) == 1
        assert r.state is ReaderState.UNKNOWN


async def test_nested_tag_error_and_persistence_partial():
    t = FakeTransport(lambda cmd, data: response(cmd, b"\x04", status=0xFC))
    async with ZKReader(t) as r:
        result = await r.write_memory(3, 0, b"\0\x01", target=TARGET)
        assert result.tag_error == 4 and result.status == 0xFC and result.outcome is Outcome.FAILURE
        t.handler = lambda cmd, data: response(cmd, status=0x13)
        result = await r.set_power(20, persist=True)
        assert result.outcome is Outcome.PARTIAL and not result.ok


async def test_epc_pc_preserved_and_verify_stable_tid():
    pc, epc = bytes.fromhex("37A5"), bytes.fromhex("ABCD1234")
    desired = bytes.fromhex("17A5ABCD1234")
    writes = []

    def peer(cmd, data):
        if cmd == 2:
            return response(cmd, pc if data[3] == 1 else desired)
        if cmd == 3:
            writes.append(data)
        return response(cmd)

    async with ZKReader(FakeTransport(peer)) as r:
        result = await r.write_epc(epc, target=TARGET)
        assert result.confirmation is Confirmation.READ_BACK
        assert writes[0][4:10] == desired
        assert len(result.steps) == 3


async def test_epc_selector_must_be_updated_before_any_tx():
    t = FakeTransport()
    async with ZKReader(t) as r:
        with pytest.raises(ValidationError):
            await r.write_epc(b"\xaa\xbb", target=TagTarget(epc=b"\xcc\xdd"))
        with pytest.raises(ValidationError):
            await r.write_memory(0, 2, bytes(4), target=TARGET, verify=True)
        assert not t.writes


async def test_access_password_readback_uses_new_password():
    new = bytes.fromhex("12345678")
    t = FakeTransport(lambda cmd, data: response(cmd, new if cmd == 2 else b""))
    async with ZKReader(t) as r:
        result = await r.set_access_password(new, target=TARGET)
        assert result.ok
        assert t.writes[-1][3:-2][4:8] == new


async def test_address_and_baud_only_update_after_ack():
    t = FakeTransport(lambda cmd, data: response(cmd))
    async with ZKReader(t) as r:
        assert (await r.set_address(7)).ok and r.address == 7
        t.handler = lambda cmd, data: response(cmd, address=7)
        assert (await r.set_baudrate(115200)).ok and t.baudrate == 115200


async def test_cancel_write_keeps_last_result_and_blocks_reuse():
    t = FakeTransport()
    async with ZKReader(t) as r:
        task = asyncio.create_task(r.write_memory(3, 0, b"\0\1", target=TARGET))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert r.last_result.outcome is Outcome.UNKNOWN
        assert len(t.writes) == 1


async def test_invalid_success_payload_not_reported_as_success():
    async with ZKReader(FakeTransport(lambda cmd, data: response(cmd, b"\1"))) as r:
        result = await r.write_memory(3, 0, b"\0\1", target=TARGET)
        assert result.outcome is Outcome.UNKNOWN
