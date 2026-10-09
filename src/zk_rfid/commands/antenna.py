"""Antenna layouts differ for 1/4, 8 and 16 ports."""

from ._common import Request, ack
from ..models import boolean, integer
from ..errors import ProtocolError


def set_antennas(mask: int, *, ports: int, persist=False) -> Request[None]:
    integer(mask, 1, (1 << ports) - 1, "antenna mask")
    boolean(persist, "persist")
    data = (
        bytes((mask | (0 if persist else 128),))
        if ports <= 4
        else bytes((0 if persist else 1,)) + mask.to_bytes(2, "big")
    )
    return Request(0x3F, data, ack, True)


def set_antenna_check(enabled: bool) -> Request[None]:
    return Request(0x66, bytes((boolean(enabled, "enabled"),)), ack, True)


def decode_antenna(raw: int, *, ports: int, mask_encoding=False) -> dict:
    if ports == 16 and not mask_encoding:
        if raw >= 16:
            raise ProtocolError("Invalid 16-port antenna index")
        return dict(antenna=raw + 1, antenna_raw=raw, antenna_mask=1 << raw)
    if raw <= 0 or raw >> ports:
        raise ProtocolError("Invalid antenna mask")
    return dict(
        antenna=raw.bit_length() if raw & (raw - 1) == 0 else None,
        antenna_raw=raw,
        antenna_mask=raw,
    )
