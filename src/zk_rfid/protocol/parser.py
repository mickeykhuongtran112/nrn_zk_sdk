"""Bounded incremental parser with CRC resynchronization and loss counters."""

from ..models import ParserDiagnostics, integer
from .crc import crc16
from .frame import ResponseFrame, decode_response


class FrameParser:
    def __init__(self, max_buffer: int = 4096):
        self.max_buffer = integer(max_buffer, 256, 1048576, "max_buffer")
        self.buffer = bytearray()
        self.diagnostics = ParserDiagnostics()

    def reset(self):
        self.buffer.clear()

    def feed(self, data: bytes) -> list[ResponseFrame]:
        result = []
        for offset in range(0, len(data), 256):
            self.buffer.extend(data[offset : offset + 256])
            while self.buffer:
                if self.buffer[0] < 5:
                    self._discard(1)
                    continue
                length = self.buffer[0] + 1
                if len(self.buffer) >= length:
                    raw = bytes(self.buffer[:length])
                    if crc16(raw) == 0:
                        result.append(decode_response(raw))
                        del self.buffer[:length]
                        self.diagnostics.frames += 1
                        continue
                    self.diagnostics.crc_failures += 1
                    self._discard(1)
                    continue
                found = None
                for pos in range(1, len(self.buffer) - 5):
                    end = pos + self.buffer[pos] + 1
                    if self.buffer[pos] >= 5 and end <= len(self.buffer):
                        if crc16(self.buffer[pos:end]) == 0:
                            found = pos
                            break
                if found is not None:
                    self._discard(found)
                    continue
                break
            if len(self.buffer) > self.max_buffer:
                self.diagnostics.buffer_overflows += 1
                self._discard(len(self.buffer) - 255)
        return result

    def _discard(self, count):
        self.diagnostics.discarded_bytes += count
        del self.buffer[:count]
