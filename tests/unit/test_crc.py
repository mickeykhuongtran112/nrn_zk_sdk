import json
from pathlib import Path

import pytest

from zk_rfid import crc16, encode_command

VECTORS = [
    (255, 0x21, "", "04ff211995"),
    (0, 1, "0400008003", "0900010400008003e347"),
    (0, 1, "040002000010e280008003", "0f0001040002000010e2800080036c65"),
    (0, 0x2F, "96", "05002f96323c"),
    (0, 0x3F, "82", "05003f8206ff"),
    (
        0,
        2,
        "06e2000000000000000000000102000600000000",
        "18000206e20000000000000000000001020006000000003a3e",
    ),
    (0, 3, "01ff030012340000000002002010e280", "14000301ff030012340000000002002010e280faf6"),
    (0, 0x94, "", "040094ff88"),
]


@pytest.mark.parametrize("address,command,data,expected", VECTORS)
def test_vendor_dll_vectors(address, command, data, expected):
    # Historical DLL-to-loopback vectors; provenance is in fixtures manifest.
    raw = bytes.fromhex(expected)
    assert encode_command(address, command, bytes.fromhex(data)) == raw
    assert crc16(raw) == 0


def test_standard_crc_check():
    assert crc16(b"123456789") == 0x6F91
    assert crc16(b"") == 0xFFFF


def test_fixture_manifest_has_provenance():
    path = Path(__file__).parents[2] / "fixtures/zk/documented/frames.json"
    data = json.loads(path.read_text())
    assert data["evidence"] == "vendor-dll-loopback (historical), not RF capture"
    assert len(data["vectors"]) == len(VECTORS)
