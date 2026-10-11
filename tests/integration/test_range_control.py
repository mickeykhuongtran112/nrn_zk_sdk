"""CFG16 wire regressions, including operator-supplied demo traces (2026-10-11).

Literal frames below were reported by the operator, not captured by these tests.
Synthetic error replies are explicitly generated with the shared test helper.
"""

import pytest

import zk_rfid as sdk
from tests.conftest import FakeTransport, response

GET = bytes.fromhex("05 00 EB 10 C6 70")
GET_100 = bytes.fromhex("09 00 EB 00 00 00 00 64 9B 5A")
SET_90_SAVED = bytes.fromhex("0A 00 EA 00 10 00 00 00 5A 78 28")
SET_ACK = bytes.fromhex("05 00 EA 00 9F 79")
GET_90 = bytes.fromhex("09 00 EB 00 00 00 00 5A 66 82")


@pytest.mark.asyncio
async def test_operator_cfg16_frames_through_public_api():
    replies = iter((GET_100, SET_ACK, GET_90))
    transport = FakeTransport(lambda cmd, data: next(replies), fragment=1, short_write=2)
    async with sdk.ZKReader(transport) as reader:
        initial = await reader.get_range_control()
        assert initial.require_success() == 100 and initial.raw_data == bytes.fromhex("00000064")
        changed = await reader.set_range_control(90, persist=True)
        assert changed.ok and changed.status == 0
        assert changed.confirmation is sdk.Confirmation.ACKNOWLEDGED
        checked = await reader.get_range_control()
        assert checked.require_success() == 90 and checked.raw_data == bytes.fromhex("0000005A")
    assert transport.writes == [GET, SET_90_SAVED, GET]
    assert transport.max_readers == 1 and not transport.opened
    assert all(sdk.crc16(frame) == 0 for frame in (GET_100, SET_ACK, GET_90))


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, 90, 100])
async def test_volatile_range_control_and_generic_config_round_trip(value):
    stored = bytes.fromhex("00000064")

    def handle(command, data):
        nonlocal stored
        if command == 0xEA:
            assert data[:2] == b"\x01\x10"
            stored = data[2:]
            return response(command)
        assert command == 0xEB and data == b"\x10"
        return response(command, stored)

    transport = FakeTransport(handle)
    async with sdk.ZKReader(transport) as reader:
        (await reader.set_range_control(value)).require_success()
        assert (await reader.get_range_control()).require_success() == value
        assert (await reader.get_config(16)).require_success() == value
        assert (await reader.get_config(16, decoded=False)).require_success() == stored
        (await reader.set_config(16, bytes.fromhex("00000064"))).require_success()
        assert (await reader.get_range_control()).require_success() == 100
    assert stored == bytes.fromhex("00000064")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 101, True, False, 90.0, "90", None])
async def test_invalid_range_control_fails_before_transmission(value):
    transport = FakeTransport()
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.ValidationError):
            await reader.set_range_control(value)
        assert transport.writes == []


@pytest.mark.asyncio
async def test_invalid_persistence_flag_fails_before_transmission():
    transport = FakeTransport()
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.ValidationError):
            await reader.set_range_control(90, persist=1)
        assert transport.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hexdata", ["", "00005A", "000000005A", "00000065", "00000100", "0100005A"]
)
async def test_malformed_cfg16_retains_native_status_and_raw_bytes(hexdata):
    payload = bytes.fromhex(hexdata)
    transport = FakeTransport(lambda cmd, data: response(cmd, payload))
    async with sdk.ZKReader(transport) as reader:
        result = await reader.get_range_control()
        assert result.outcome is sdk.Outcome.FAILURE and result.status == 0
        assert result.confirmation is sdk.Confirmation.ACKNOWLEDGED
        assert result.raw_data == payload and result.diagnostics
        assert (await reader.get_config(16, decoded=False)).require_success() == payload
        count = len(transport.writes)
        with pytest.raises(sdk.ProtocolError):
            await reader.set_config(16, payload)
        assert len(transport.writes) == count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,outcome",
    [(0xF9, sdk.Outcome.FAILURE), (0xFF, sdk.Outcome.FAILURE), (0x13, sdk.Outcome.PARTIAL)],
)
async def test_native_set_errors_are_not_reported_as_success(status, outcome):
    async with sdk.ZKReader(
        FakeTransport(lambda cmd, data: response(cmd, status=status))
    ) as reader:
        result = await reader.set_range_control(90, persist=True)
        assert result.status == status and result.outcome is outcome and not result.ok


@pytest.mark.asyncio
async def test_cfg25_operator_set_frame_keeps_explicit_layout_gate():
    # Operator's separate Impinj Scan SET and ACK; no claim of a Gen2X RF round.
    wire = bytes.fromhex("0C 00 EA 00 19 0F 01 03 02 03 00 49 5B")
    payload = bytes.fromhex("0F 01 03 02 03 00")
    transport = FakeTransport(lambda cmd, data: SET_ACK)
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.UnverifiedFeature):
            await reader.set_config(25, payload, persist=True)
        assert transport.writes == []
    async with sdk.ZKReader(
        transport, capabilities=sdk.ReaderCapabilities(cfg25_length=6)
    ) as reader:
        result = await reader.set_config(25, payload, persist=True)
        assert result.ok and result.status == 0
    assert transport.writes == [wire]
    assert sdk.crc16(wire) == sdk.crc16(SET_ACK) == 0
