"""Exercise the standalone example with a synthetic peer; never open serial ports."""

import importlib.util
from pathlib import Path

import pytest

from tests.conftest import FakeTransport, ModulePeer, response
from zk_rfid import ReaderCapabilities, ScenarioSession, ZKReader
from tests.demo_app.simulator import DemoTransport

PATH = Path(__file__).parents[2] / "examples/inventory_scenario.py"
SPEC = importlib.util.spec_from_file_location("scenario_example", PATH)
example = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(example)


@pytest.mark.asyncio
async def test_cli_multiple_antennas_restore_original_selection(capsys):
    peer = DemoTransport(4)
    args = example.parse_args(
        ["--port", "unused", "--ports", "4", "--antenna-mask", "0xD", "--seconds", "0.02"]
    )
    async with ZKReader(peer, capabilities=ReaderCapabilities(antenna_ports=4)) as reader:
        outcome = await example.read_tags(reader, args)
        assert outcome.complete and peer.ant == 1
    output = capsys.readouterr().out
    assert all(f"antenna={port}" in output for port in (1, 3, 4))
    assert "antenna=2" not in output


@pytest.mark.parametrize("mask", ["0", "0x10", "-1"])
def test_cli_rejects_invalid_antenna_masks_before_connecting(mask):
    with pytest.raises(SystemExit):
        example.parse_args(["--port", "unused", "--ports", "4", "--antenna-mask", mask])


@pytest.mark.asyncio
@pytest.mark.parametrize("write_profiles", [False, True])
async def test_s_cst_example_uses_requested_selector_and_keeps_cfg31(write_profiles):
    peer = ModulePeer()
    peer.cfg[31] = bytes.fromhex("006700f1011d")
    original = dict(peer.cfg)
    expected_profiles = bytes.fromhex("006700670067") if write_profiles else original[31]

    def handle(command, data):
        if command == 0x50:
            assert data == b"\x01"  # Target B, not the CLI default A.
            assert peer.cfg[9] == bytes((0x16, 128))
            assert peer.cfg[31] == expected_profiles
        return peer(command, data)

    argv = [
        "--port",
        "unused",
        "--session",
        "S-CST" if write_profiles else "128",
        "--target",
        "B",
        "--q",
        "6",
        "--phase",
        "--seconds",
        "0.02",
    ]
    if write_profiles:
        argv += ["--profiles", "103", "103", "103"]
    args = example.parse_args(argv)
    assert args.session is ScenarioSession.S_CST
    transport = FakeTransport(handle)
    async with ZKReader(transport) as reader:
        outcome = await example.read_tags(reader, args)
    assert outcome.complete
    assert peer.cfg == {**original, 31: expected_profiles}
    cfg31_writes = [w for w in transport.writes if w[2] == 0xEA and w[4] == 31]
    assert len(cfg31_writes) == int(write_profiles)
    assert not any(w[2] == 0x9A for w in transport.writes)


@pytest.mark.asyncio
async def test_profile_readback_mismatch_prevents_start():
    peer = ModulePeer()

    def handle(command, data):
        if command == 0xEB and data == b"\x1f":
            return response(command, bytes.fromhex("000100010001"))
        return peer(command, data)

    args = example.parse_args(
        ["--port", "unused", "--session", "S-CST", "--profiles", "103", "241", "285"]
    )
    transport = FakeTransport(handle)
    async with ZKReader(transport) as reader:
        with pytest.raises(RuntimeError, match="read-back mismatch"):
            await example.read_tags(reader, args)
    assert not any(w[2] == 0x50 for w in transport.writes)


def test_profile_arguments_require_s_cst_before_connecting():
    with pytest.raises(SystemExit) as error:
        example.parse_args(["--port", "unused", "--session", "S1", "--profiles", "1", "5", "13"])
    assert error.value.code == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "diagnostic"),
    [
        (None, None),
        ("stop_rejected", "command_failed"),
        ("stop_timeout", "Host deadline expired"),
        ("restore_rejected", "Restoration failed: Operation failure: command_failed"),
        ("restore_mismatch", "Configuration restoration read-back mismatch"),
    ],
)
async def test_cli_reports_cleanup_failures_and_returns_failure_status(
    monkeypatch, capsys, failure, diagnostic
):
    peer = ModulePeer()
    peer.cfg[31] = bytes.fromhex("006700f1011d")
    original = dict(peer.cfg)
    stopping = False

    def handle(command, data):
        nonlocal stopping
        if command == 0x51:
            stopping = True
            if failure == "stop_rejected":
                return response(command, status=0xF9)
            if failure == "stop_timeout":
                return None
        if stopping and command == 0xEA:
            if failure == "restore_rejected":
                return response(command, status=0xF9)
            if failure == "restore_mismatch":
                return response(command)  # ACK without applying the old value.
        return peer(command, data)

    transport = FakeTransport(handle)
    monkeypatch.setattr(example, "SerialTransport", lambda *args: transport)
    args = example.parse_args(
        ["--port", "unused", "--session", "S-CST", "--seconds", "0.02", "--timeout", "0.1"]
    )
    exit_code = await example.main(args)
    captured = capsys.readouterr()
    assert not transport.opened
    assert sum(w[2] == 0x51 for w in transport.writes) == 1
    if failure is None:
        assert exit_code == 0
        assert "Stop: stopped complete= True" in captured.out
        assert captured.err == ""
        assert peer.cfg == original
    else:
        assert exit_code == 1
        assert "Stop: stop_unconfirmed complete= False" in captured.out
        assert "Diagnostic:" in captured.err
        assert diagnostic in captured.err


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tag_hex", "raw_phase"),
    [
        ("0142ABCDC8018F018D0E06D2", (399, 397)),
        ("0142ABCDC8000000000E06D2", (0, 0)),
        ("0102ABCDC8", None),
    ],
)
async def test_phase_output_preserves_values_and_omits_absent_fields(capsys, tag_hex, raw_phase):
    peer = ModulePeer()
    peer.tag = bytes.fromhex(tag_hex)

    def handle(command, data):
        if command == 0x50:
            assert peer.cfg[9][0] & 0x10  # Phase was requested on the wire.
        return peer(command, data)

    args = example.parse_args(["--port", "unused", "--phase", "--seconds", "0.02"])
    async with ZKReader(FakeTransport(handle)) as reader:
        outcome = await example.read_tags(reader, args)
    assert outcome.complete
    captured = capsys.readouterr()
    line = next(line for line in captured.out.splitlines() if line.startswith("EPC "))
    assert line.startswith("EPC ABCD antenna=1 rssi_raw=200")
    if raw_phase is None:
        assert "phase_" not in line and "frequency_" not in line
    else:
        fields = dict(field.split("=", 1) for field in line.split()[2:])
        assert int(fields["phase_begin_raw"]) == raw_phase[0]
        assert int(fields["phase_end_raw"]) == raw_phase[1]
        expected_degrees = (34.713, 34.539) if raw_phase == (399, 397) else (0, 0)
        assert float(fields["phase_begin_degrees"]) == pytest.approx(expected_degrees[0])
        assert float(fields["phase_end_degrees"]) == pytest.approx(expected_degrees[1])
        assert int(fields["frequency_khz"]) == 919250
    assert captured.err == ""
    assert (
        sum(line.startswith("EPC ") for line in captured.out.splitlines()) == outcome.received_count
    )


@pytest.mark.asyncio
async def test_scenario_example_checks_mode_before_profile_write():
    peer = ModulePeer()
    peer.mode = 1
    transport = FakeTransport(peer)
    args = example.parse_args(
        ["--port", "unused", "--session", "S-CST", "--profiles", "103", "241", "285"]
    )
    async with ZKReader(transport) as reader:
        with pytest.raises(RuntimeError, match="Switch explicitly"):
            await example.read_tags(reader, args)
    assert [w[2] for w in transport.writes] == [0x77]
