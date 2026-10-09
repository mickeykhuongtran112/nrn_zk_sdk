"""Temperature and return loss have documented units; RSSI does not."""

from ._common import Request, exact, u8
from ..models import integer
from ..errors import ProtocolError, ValidationError


def decode_temperature(data: bytes) -> int:
    exact(data, 2)
    if data[0] not in (0, 1):
        raise ProtocolError("Invalid temperature sign")
    return data[1] * (1 if data[0] else -1)


def get_temperature() -> Request[int]:
    return Request(0x92, decode=decode_temperature)


def measure_return_loss(frequency_khz: int, antenna: int, *, ports: int) -> Request[int]:
    integer(frequency_khz, 840000, 960000, "frequency_khz")
    if frequency_khz % 100 and frequency_khz % 125:
        raise ValidationError("Frequency must be a multiple of 100 or 125 kHz")
    integer(antenna, 1, min(ports, 4), "antenna (documented diagnostic range)")
    return Request(0x91, frequency_khz.to_bytes(4, "big") + bytes((antenna - 1,)), u8)


def return_loss_threshold(threshold_db: int | None = None) -> Request[int]:
    value = 0 if threshold_db is None else 128 | integer(threshold_db, 0, 20, "threshold_db")

    def decode(data):
        n = u8(data)
        if n > 20:
            raise ProtocolError("Invalid return-loss threshold")
        return n

    return Request(0x6E, bytes((value,)), decode, threshold_db is not None)
