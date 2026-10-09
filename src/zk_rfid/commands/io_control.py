"""LED/buzzer/GPIO control, limited to documented two output pins."""

from ._common import Request, ack, exact
from ..models import GPIOState, boolean, integer
from ..errors import ProtocolError


def set_buzzer(enabled: bool) -> Request[None]:
    return Request(0x40, bytes((boolean(enabled, "enabled"),)), ack, True)


def indicator(active_50ms: int, silent_50ms: int, count: int) -> Request[None]:
    return Request(
        0x33,
        bytes(
            (
                integer(active_50ms, 0, 255, "active_50ms"),
                integer(silent_50ms, 0, 255, "silent_50ms"),
                integer(count, 0, 255, "count"),
            )
        ),
        ack,
        True,
    )


def set_gpio(output1: bool, output2: bool) -> Request[None]:
    value = boolean(output1, "output1") | (boolean(output2, "output2") << 1)
    return Request(0x46, bytes((value,)), ack, True)


def decode_gpio(data: bytes) -> GPIOState:
    v = exact(data, 1)[0]
    if v & ~0x31:
        raise ProtocolError("GPIO response has reserved bits")
    return GPIOState(bool(v & 1), bool(v & 16), bool(v & 32), v)


def get_gpio() -> Request[GPIOState]:
    return Request(0x47, decode=decode_gpio)
