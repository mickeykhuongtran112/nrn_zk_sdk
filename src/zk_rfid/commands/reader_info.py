"""V2.25 sections 8.4.1, 8.4.12 (table layout, not erroneous example Len)."""

from ._common import Request, exact
from ..errors import ProtocolError
from ..models import ReaderInfo


def decode_reader_info(data: bytes, address: int = 0) -> ReaderInfo:
    exact(data, 12)
    if data[11] not in (0, 1):
        raise ProtocolError("Invalid antenna-check field in reader information")
    return ReaderInfo(
        address,
        tuple(data[:2]),
        data[2],
        data[3],
        data[4],
        data[5],
        data[6],
        data[7],
        data[8],
        data[9:11],
        bool(data[11]),
    )


def get_reader_info() -> Request[ReaderInfo]:
    return Request(0x21, decode=decode_reader_info)


def get_serial_number() -> Request[bytes]:
    return Request(0x4C, decode=lambda d: exact(d, 4))
