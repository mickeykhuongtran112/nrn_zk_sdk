"""Custom Region regressions from DLL loopback and operator-supplied reader frames."""

import pytest

import zk_rfid as sdk
from tests.conftest import FakeTransport, response


@pytest.mark.asyncio
@pytest.mark.parametrize("fragment", [1, 4096])
async def test_operator_custom_region_frames_match_demo_space_and_save(fragment):
    # Demo: Start 918000 kHz, Count 8, Space 4 (*125 kHz), Save checked.
    set_tx = bytes.fromhex("0B002200FF04080E01F0F6F7")
    set_rx = bytes.fromhex("05002200F57D")
    get_tx = bytes.fromhex("04009EA527")
    get_rx = bytes.fromhex("0B009E00FF04080E01F0FEEA")
    for wire in (set_tx, set_rx, get_tx, get_rx):
        assert sdk.crc16(wire) == 0

    def handle(cmd, data):
        if cmd == 0x22:
            return set_rx
        assert cmd == 0x9E and not data
        return get_rx

    transport = FakeTransport(handle, fragment=fragment)
    async with sdk.ZKReader(transport) as reader:
        result = await reader.set_custom_region(918000, 8, 500, persist=True)
        assert result.ok and result.status == 0 and result.raw_data == b""
        assert transport.writes == [set_tx]
        result = await reader.get_custom_region()
        expected = sdk.CustomRegion(918000, 8, 500)
        assert result.require_success() == expected
        assert result.raw_data == bytes.fromhex("FF04080E01F0")
        assert transport.writes == [set_tx, get_tx]
        assert expected.last_frequency_khz == 921500
        assert (await reader.get_region()).require_success() == expected
        assert transport.writes[-1] == get_tx

        # The public API takes kHz, not the demo's raw Space byte.
        count = len(transport.writes)
        with pytest.raises(sdk.ValidationError, match="spacing_khz"):
            await reader.set_custom_region(918000, 8, 4, persist=True)
        assert len(transport.writes) == count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "persist,wire",
    [
        (False, "0B002201FF020A0E0C31300D"),
        (True, "0B002200FF020A0E0C31E592"),
    ],
)
async def test_custom_region_dll_vectors_and_native_restore(persist, wire):
    active = bytes.fromhex("023100")
    expected = sdk.CustomRegion(920625, 10, 250)

    def handle(cmd, data):
        nonlocal active
        if cmd == 0x22:
            active = data[1:]
            return bytes.fromhex("05002200F57D")
        assert cmd == 0x9E
        if active[:1] == b"\xff":
            return bytes.fromhex("0B009E00FF020A0E0C31ED8F")
        return response(cmd, active)

    transport = FakeTransport(handle, fragment=1)
    async with sdk.ZKReader(transport) as reader:
        original = (await reader.get_region()).require_success()
        assert (await reader.get_custom_region()).require_success() is None
        result = await reader.set_custom_region(920625, 10, 250, persist=persist)
        assert result.ok and transport.writes[-1] == bytes.fromhex(wire)
        result = await reader.get_custom_region()
        assert result.require_success() == expected
        assert result.raw_data == bytes.fromhex("FF020A0E0C31")
        assert transport.writes[-1] == bytes.fromhex("04009EA527")
        assert (await reader.get_region()).require_success() == expected
        assert expected.last_frequency_khz == 922875
        assert (await reader.set_region(original)).ok
        assert (await reader.get_region()).require_success() == original
        assert (await reader.get_custom_region()).require_success() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        (0, 1, 125),
        (0x1000000, 1, 125),
        (True, 1, 125),
        (920625, 0, 125),
        (920625, 62, 125),
        (920625, True, 125),
        (920625, 2, 0),
        (920625, 2, -125),
        (920625, 2, 200),
        (920625, 2, 32000),
        (920625, 2, True),
        (920625.0, 1, 125),
        (0xFFFFFF, 2, 125),
    ],
)
async def test_invalid_custom_region_never_transmits(args):
    transport = FakeTransport()
    async with sdk.ZKReader(transport) as reader:
        with pytest.raises(sdk.ValidationError):
            await reader.set_custom_region(*args)
    assert transport.writes == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        b"",
        bytes.fromhex("FF020A0E0C"),
        bytes.fromhex("FF020A0E0C3100"),
        bytes.fromhex("FF02000E0C31"),
        bytes.fromhex("FF023E0E0C31"),
        bytes.fromhex("FF00020E0C31"),
        bytes.fromhex("FF020A000000"),
        bytes.fromhex("FF020AFFFFFF"),
        bytes.fromhex("020031"),
    ],
)
async def test_malformed_region_response_retains_raw_bytes(payload):
    async with sdk.ZKReader(FakeTransport(lambda cmd, data: response(cmd, payload))) as reader:
        result = await reader.get_custom_region()
        assert result.outcome is sdk.Outcome.FAILURE and result.status == 0
        assert result.raw_data == payload and result.diagnostics


def test_custom_region_encoding_boundaries():
    single = sdk.CustomRegion(920625, 1, 0)
    assert single.last_frequency_khz == 920625
    many = sdk.CustomRegion(840000, 61, 125)
    assert sdk.decode_region(sdk.set_custom_region(many).data[1:]) == many
    assert sdk.CustomRegion(1, 1, 31875).spacing_khz == 31875
    with pytest.raises(sdk.ValidationError):
        sdk.set_custom_region(single, persist=1)


@pytest.mark.asyncio
async def test_custom_region_reader_rejection_is_not_retried():
    transport = FakeTransport(lambda cmd, data: response(cmd, status=0xF9))
    async with sdk.ZKReader(transport) as reader:
        result = await reader.set_custom_region(920625, 10, 250)
        assert result.outcome is sdk.Outcome.FAILURE and result.status == 0xF9
    assert len(transport.writes) == 1
