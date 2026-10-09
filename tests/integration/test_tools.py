import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import response
from zk_rfid import encode_command

ROOT = Path(__file__).parents[2]


def test_replay_fragmented_capture_and_comparator(tmp_path):
    capture = tmp_path / "synthetic.jsonl"
    tx = encode_command(0, 0x47)
    rx = response(0x47, b"\x11")
    items = [dict(direction="metadata", metadata=dict(source="synthetic"))]
    items += [dict(direction="tx", hex=b.hex()) for b in (tx[:2], tx[2:])]
    items += [dict(direction="rx", hex=b.hex()) for b in (rx[:1], rx[1:])]
    capture.write_text("\n".join(json.dumps(i) for i in items))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/replay_capture.py"), str(capture)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.splitlines()[-1])
    assert summary["tx_frames"] == summary["rx_frames"] == 1
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/compare_results.py")],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.splitlines()[-1])["unverified"] == 2


def test_cli_help_has_no_hardware_side_effects():
    files = list((ROOT / "examples").glob("*.py")) + list((ROOT / "tools").glob("*.py"))
    for script in files:
        if script.name.startswith("_"):
            continue
        result = subprocess.run(
            [sys.executable, str(script), "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0, (script, result.stderr)
        assert "usage:" in result.stdout
