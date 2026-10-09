"""Lossless framing. Len counts everything after itself."""

from dataclasses import dataclass
from ..errors import ProtocolError
from ..models import integer, octets
from .crc import append_crc, crc16


@dataclass(frozen=True)
class ResponseFrame:
    address: int
    command: int
    status: int
    data: bytes
    raw: bytes


def encode_command(address: int, command: int, data: bytes = b"") -> bytes:
    integer(address, 0, 255, "address")
    integer(command, 0, 255, "command")
    octets(data, "command data")
    return append_crc(bytes((len(data) + 4, address, command)) + data)


def decode_response(raw: bytes) -> ResponseFrame:
    if not 6 <= len(raw) <= 256 or raw[0] != len(raw) - 1:
        raise ProtocolError("Response length mismatch")
    if crc16(raw) != 0:
        raise ProtocolError("Response CRC mismatch")
    return ResponseFrame(raw[1], raw[2], raw[3], raw[4:-2], bytes(raw))
