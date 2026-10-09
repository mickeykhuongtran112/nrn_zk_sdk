"""Deterministic in-memory UART peer; these are synthetic, never hardware captures."""

import asyncio

import pytest

from zk_rfid import append_crc, crc16


def response(command, data=b"", status=0, address=0):
    return append_crc(bytes((5 + len(data), address, command, status)) + data)


class FakeTransport:
    def __init__(self, handler=None, *, fragment=4096, short_write=None):
        self.handler = handler
        self.fragment = fragment
        self.short_write = short_write
        self.rx = asyncio.Queue()
        self.tx = bytearray()
        self.writes = []
        self.readers = 0
        self.max_readers = 0
        self.opened = False
        self.baudrate = 57600

    async def open(self):
        self.opened = True

    async def close(self):
        self.opened = False

    async def set_baudrate(self, baudrate):
        self.baudrate = baudrate

    def feed(self, wire):
        for p in range(0, len(wire), self.fragment):
            self.rx.put_nowait(wire[p : p + self.fragment])

    async def read(self, size=4096):
        self.readers += 1
        self.max_readers = max(self.max_readers, self.readers)
        try:
            return await self.rx.get()
        finally:
            self.readers -= 1

    async def write(self, data):
        count = min(len(data), self.short_write or len(data))
        self.tx.extend(data[:count])
        while self.tx and len(self.tx) >= self.tx[0] + 1:
            raw = bytes(self.tx[: self.tx[0] + 1])
            del self.tx[: len(raw)]
            assert crc16(raw) == 0
            self.writes.append(raw)
            if self.handler:
                out = self.handler(raw[2], raw[3:-2])
                if out is not None:
                    self.feed(out)
        return count


class ModulePeer:
    """Minimal synthetic state machine, not a hardware emulator/validation claim."""

    def __init__(self):
        self.cfg = {9: bytes((6, 1)), 10: bytes((0, 0)), 11: bytes((1, 0, 32, 0))}
        self.ant = 1
        self.tag = bytes.fromhex("0104DEADBEEF55")
        self.mode = 0

    def __call__(self, command, data):
        if command == 0x21:
            return response(command, bytes((1, 2, 0x20, 2, 255, 255, 20, 20, self.ant, 0, 0, 1)))
        if command == 0xEB:
            return response(command, self.cfg[data[0]])
        if command == 0xEA:
            self.cfg[data[1]] = data[2:]
            return response(command)
        if command == 0x3F:
            self.ant = data[0] & 15
            return response(command)
        if command == 0x50:
            return response(0xEE, self.tag) + response(command)
        if command == 0x51:
            return response(0xEE, self.tag) + response(command)
        if command == 0x77:
            return response(
                command, bytes((self.mode, 0, 3, 0, 4, 0, 1, 0, 32, 0)) + bytes(32) + bytes(2)
            )
        if command == 0x76:
            self.mode = data[0]
            return response(command)
        return response(command)


@pytest.fixture
def fake_factory():
    return FakeTransport
