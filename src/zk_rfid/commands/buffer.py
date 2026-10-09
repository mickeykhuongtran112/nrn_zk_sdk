"""Reader buffer management; data kind is supplied from the inventory context."""

from ._common import Request, ack, exact, u16
from .antenna import decode_antenna
from ..errors import ProtocolError, ValidationError, UnverifiedFeature
from ..measurements import _rssi_fields
from ..models import BufferCounts, InventoryData, TagReport, integer


def set_buffer_length(max_bytes: int) -> Request[None]:
    if max_bytes not in (16, 62):
        raise ValidationError("Buffer max_bytes must be 16 or 62; changing it clears buffer")
    return Request(0x70, bytes((0 if max_bytes == 16 else 1,)), ack, True)


def get_buffer_length() -> Request[int]:
    def decode(data):
        v = exact(data, 1)[0]
        if v not in (0, 1):
            raise ProtocolError("Invalid buffer length code")
        return 16 if v == 0 else 62

    return Request(0x71, decode=decode)


def clear_buffer() -> Request[None]:
    return Request(0x73, decode=ack, mutating=True)


def get_buffer_count() -> Request[int]:
    return Request(0x74, decode=u16)


def decode_counts(data: bytes) -> BufferCounts:
    exact(data, 4)
    return BufferCounts(int.from_bytes(data[:2], "big"), int.from_bytes(data[2:], "big"))


def decode_buffer(
    data: bytes, *, ports: int, data_kind=InventoryData.EPC, antenna_bytes: int | None = None
) -> list[TagReport]:
    if data_kind not in (InventoryData.EPC, InventoryData.TID):
        raise ValidationError("Buffer contains EPC or TID")
    if ports == 16 and antenna_bytes is None:
        raise UnverifiedFeature(
            "16-port buffer Ant width conflicts in manual; select verified width"
        )
    width = antenna_bytes or 1
    integer(width, 1, 2, "antenna_bytes")
    if not data:
        raise ProtocolError("Missing buffer count")
    reports, offset = [], 1
    for _ in range(data[0]):
        start = offset
        if offset + width + 1 > len(data):
            raise ProtocolError("Truncated buffer record")
        ant = int.from_bytes(data[offset : offset + width], "big")
        size = data[offset + width]
        offset += width + 1
        if size < 2 or size > 62 or size % 2 or offset + size + 2 > len(data):
            raise ProtocolError("Invalid buffer identifier length")
        value = data[offset : offset + size]
        offset += size
        reports.append(
            TagReport(
                epc=value if data_kind is InventoryData.EPC else None,
                tid=value if data_kind is InventoryData.TID else None,
                **decode_antenna(ant, ports=ports, mask_encoding=True),
                **_rssi_fields(data[offset]),
                read_count=data[offset + 1],
                raw=data[start : offset + 2],
            )
        )
        offset += 2
    if offset != len(data):
        raise ProtocolError("Trailing buffer bytes")
    return reports
