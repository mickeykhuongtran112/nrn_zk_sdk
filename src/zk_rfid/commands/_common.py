"""Small command value and strict response helpers, no I/O."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar
from ..errors import ProtocolError
from ..models import octets

T = TypeVar("T")


def raw(data: bytes) -> bytes:
    return data


def exact(data: bytes, size: int) -> bytes:
    if len(data) != size:
        raise ProtocolError(f"Expected {size} response bytes, received {len(data)}")
    return data


def ack(data: bytes) -> None:
    exact(data, 0)


def u8(data: bytes) -> int:
    return exact(data, 1)[0]


def u16(data: bytes) -> int:
    return int.from_bytes(exact(data, 2), "big")


def switch(data: bytes) -> bool:
    value = u8(data)
    if value not in (0, 1):
        raise ProtocolError("Invalid boolean response")
    return bool(value)


@dataclass(frozen=True)
class Request(Generic[T]):
    command: int
    data: bytes = b""
    decode: Callable[[bytes], T] = raw
    mutating: bool = False

    def __post_init__(self):
        octets(self.data, "command payload")
