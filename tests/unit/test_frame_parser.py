import random
import pytest
from zk_rfid.errors import ProtocolError, ValidationError
from zk_rfid.protocol import FrameParser, decode_response, encode_command
from tests.conftest import response


@pytest.mark.parametrize("size", [1, 2, 3, 5, 11, 64, 257, 4096])
def test_chunking_and_coalescing(size):
    wire = b"".join(response(0x21, bytes((n,)) * 12) for n in range(40))
    parser = FrameParser()
    frames = []
    for p in range(0, len(wire), size):
        frames += parser.feed(wire[p : p + size])
    assert len(frames) == 40
    assert frames[-1].data == bytes((39,)) * 12
    assert not parser.buffer
    assert not parser.diagnostics.discarded_bytes


def test_noise_bad_crc_and_corrupt_length_recover():
    good = response(0x47, b"\x11")
    bad = bytearray(good)
    bad[-1] ^= 1
    p = FrameParser()
    out = p.feed(b"\x00\x01" + bad + b"\xf0" + good)
    assert [f.data for f in out] == [b"\x11"]
    assert p.diagnostics.discarded_bytes == len(bad) + 3
    assert p.diagnostics.crc_failures > 0


def test_random_noise_bounded():
    p = FrameParser(max_buffer=256)
    r = random.Random(422)
    for _ in range(100):
        p.feed(r.randbytes(400))
        assert len(p.buffer) < 256


def test_invalid_lengths_and_crc():
    with pytest.raises(ValidationError):
        encode_command(0, 1, bytes(252))
    with pytest.raises(ProtocolError):
        decode_response(bytes(6))
    with pytest.raises(ProtocolError):
        decode_response(response(0x47, b"\0")[:-1] + b"\0")
