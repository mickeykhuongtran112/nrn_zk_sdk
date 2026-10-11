"""CFG11 result semantics and byte-preserving Scenario cleanup."""

import pytest

from tests.conftest import FakeTransport, ModulePeer, response
from zk_rfid import (
    Confirmation,
    InventoryConfig,
    Outcome,
    ProtocolError,
    ScenarioSession,
    TagMask,
    ZKReader,
)

pytestmark = pytest.mark.asyncio


async def test_disabled_mask_get_set_and_clear_preserve_native_results():
    peer = ModulePeer()
    peer.cfg[11] = bytes(4)
    transport = FakeTransport(peer, fragment=1)
    async with ZKReader(transport) as reader:
        result = await reader.get_inventory_mask()
        assert result.ok and result.require_success() is None
        assert result.status == 0 and result.raw_data == bytes(4)
        assert result.confirmation is Confirmation.ACKNOWLEDGED
        assert result.diagnostics == ()
        assert (await reader.get_config(11)).require_success() is None
        assert (await reader.get_config(11, decoded=False)).require_success() == bytes(4)

        count = len(transport.writes)
        with pytest.raises(ProtocolError):
            await reader.set_config(11, bytes(4))
        assert len(transport.writes) == count  # Invalid outbound fields never reach UART.

        mask = TagMask(2, 0, 16, bytes.fromhex("E280"))
        (await reader.set_inventory_mask(mask)).require_success()
        assert (await reader.get_inventory_mask()).require_success() == mask
        (await reader.set_inventory_mask(None)).require_success()
        result = await reader.get_inventory_mask()
        assert result.require_success() is None
        assert result.raw_data == bytes.fromhex("01002000")
        assert peer.cfg[11] == bytes.fromhex("01002000")


@pytest.mark.parametrize("initial", [bytes(4), bytes.fromhex("01002000")])
async def test_scenario_restores_exact_disabled_mask_header(initial):
    peer = ModulePeer()
    peer.cfg[11] = initial
    original = dict(peer.cfg)
    mask = TagMask(1, 32, 8, b"\xde")

    def handle(command, data):
        if command == 0x50:
            assert peer.cfg[11] == mask.encode()
        return peer(command, data)

    transport = FakeTransport(handle, fragment=1)
    async with ZKReader(transport) as reader:
        session = await reader.start_inventory(
            config=InventoryConfig(session=ScenarioSession.S_CST, mask=mask)
        )
        report = await anext(session)
        assert report.epc == bytes.fromhex("DEADBEEF")
        outcome = await session.stop()
        assert outcome.complete
        assert peer.cfg == original
        result = await reader.get_inventory_mask()
        assert result.require_success() is None and result.raw_data == initial
    mask_writes = [wire[3:-2] for wire in transport.writes if wire[2] == 0xEA and wire[4] == 11]
    assert mask_writes == [b"\x01\x0b" + mask.encode(), b"\x01\x0b" + initial]


async def test_malformed_disabled_response_keeps_ack_but_fails_decoding():
    payload = bytes(5)
    async with ZKReader(FakeTransport(lambda cmd, data: response(cmd, payload))) as reader:
        result = await reader.get_inventory_mask()
    assert result.outcome is Outcome.FAILURE and not result.ok
    assert result.status == 0 and result.raw_data == payload
    assert result.confirmation is Confirmation.ACKNOWLEDGED
    assert "Expected 4 response bytes" in result.diagnostics[0]


async def test_working_mode_preserves_inactive_mask_buffer_in_raw_result():
    payload = bytes((1, 0, 0, 0, 4, 0, 0, 0, 0, 0)) + bytes.fromhex("E280") + bytes(32)
    async with ZKReader(FakeTransport(lambda cmd, data: response(cmd, payload))) as reader:
        result = await reader.get_working_mode()
    assert result.require_success().config.mask is None
    assert result.status == 0 and result.raw_data == payload
    assert result.confirmation is Confirmation.ACKNOWLEDGED and result.diagnostics == ()
