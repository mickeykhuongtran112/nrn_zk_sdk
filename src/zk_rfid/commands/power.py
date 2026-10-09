"""RF power is integer dBm; write-power bit7 is enable, not persistence."""

from ._common import Request, ack, exact
from ..models import WritePower, boolean, integer
from ..errors import ProtocolError, ValidationError


def set_power(power_dbm: int | tuple[int, ...], *, ports: int, persist=False) -> Request[None]:
    boolean(persist, "persist")
    powers = (power_dbm,) if isinstance(power_dbm, int) else tuple(power_dbm)
    if len(powers) not in (1, ports):
        raise ValidationError("Supply one global value or exactly one per configured antenna")
    values = bytes(integer(p, 0, 30, "power_dbm") | (0 if persist else 128) for p in powers)
    return Request(0x2F, values, ack, True)


def get_power(*, ports: int) -> Request[tuple[int, ...]]:
    def decode(data):
        exact(data, ports)
        if any(p > 30 for p in data):
            raise ProtocolError("Power response is outside documented 0..30 dBm")
        return tuple(data)

    return Request(0x94, decode=decode)


def set_write_power(power_dbm: int | None) -> Request[None]:
    value = 0 if power_dbm is None else 128 | integer(power_dbm, 0, 30, "power_dbm")
    return Request(0x79, bytes((value,)), ack, True)


def decode_write_power(data: bytes) -> WritePower:
    value = exact(data, 1)[0]
    if value & 127 > 30:
        raise ProtocolError("Invalid write power")
    return WritePower(bool(value & 128), value & 127)


def get_write_power() -> Request[WritePower]:
    return Request(0x7A, decode=decode_write_power)


def write_retries(count: int | None = None) -> Request[int]:
    value = 0 if count is None else 128 | integer(count, 0, 7, "write retries")

    def decode(data):
        n = exact(data, 1)[0]
        if n > 7:
            raise ProtocolError("Invalid write retries")
        return n

    return Request(0x7B, bytes((value,)), decode, count is not None)
