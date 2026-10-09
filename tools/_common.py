"""CLI serialization and opt-in transport capture; not imported by SDK core."""

import json
import time
from dataclasses import asdict, is_dataclass
from enum import Enum


def json_default(value):
    if isinstance(value, bytes):
        return value.hex().upper()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(type(value).__name__)


def emit(value):
    print(json.dumps(value, default=json_default, ensure_ascii=False))


class CaptureTransport:
    """Record the bytes accepted by each write and returned by each read."""

    def __init__(self, transport, stream, metadata):
        self.transport, self.stream = transport, stream
        self.sequence = 0
        self._record("metadata", b"", metadata=metadata)

    def _record(self, direction, data, **extra):
        entry = dict(
            sequence=self.sequence,
            direction=direction,
            monotonic_ns=time.monotonic_ns(),
            unix_ns=time.time_ns(),
            hex=data.hex().upper(),
            **extra,
        )
        self.sequence += 1
        self.stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.stream.flush()

    async def open(self):
        await self.transport.open()

    async def close(self):
        await self.transport.close()

    async def read(self, size=4096):
        data = await self.transport.read(size)
        if data:
            self._record("rx", data)
        return data

    async def write(self, data):
        n = await self.transport.write(data)
        if n:
            self._record("tx", data[:n])
        return n
