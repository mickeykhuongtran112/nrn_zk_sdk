"""Synthetic byte transport for GUI inspection; never a hardware validation source."""

import asyncio
from zk_rfid.protocol import crc16
from zk_rfid.protocol.crc import append_crc


def response(command, data=b"", status=0, address=0):
    return append_crc(bytes((len(data) + 5, address, command, status)) + data)


class DemoTransport:
    def __init__(self, ports=1):
        self.ports, self.address, self.baudrate = ports, 0, 115200
        self.rx, self.tx = asyncio.Queue(), bytearray()
        self.opened = False
        self.stream = None
        self.inject = None
        self.powers = [20] * ports
        self.ant, self.ant_check, self.mode, self.profile = 1, 1, 0, 103
        self.region = bytes((2, 49, 0))
        self.cfg = {
            7: bytes((0, 2, 4)),
            8: bytes((0,)),
            9: bytes((4, 0)),
            10: bytes(2),
            11: bytes((1, 0, 32, 0)),
            25: bytes((15, 1, 3, 2, 3, 0)),
            29: bytes(5),
            31: bytes.fromhex("006700F1011D"),
        }
        self.write_power, self.retries, self.drm, self.threshold, self.heartbeat = 0, 3, 0, 6, 0
        self.save_len, self.gpio = 0, 0
        self.memory = [bytearray(512) for _ in range(4)]
        self.memory[1][2:4] = bytes.fromhex("3000")
        self.memory[1][4:16] = bytes.fromhex("E20034120123456789000001")
        self.memory[2][:12] = bytes.fromhex("E280116060000205DEADBEEF")
        self.rt = bytes((0, 3, 0, 4, 0, 1, 0, 32, 0)) + bytes(32) + bytes(2)
        self.inventory_config = None

    @property
    def epc(self):
        count = int.from_bytes(self.memory[1][2:4], "big") >> 11
        return bytes(self.memory[1][4 : 4 + count * 2])

    async def open(self):
        self.opened = True

    async def set_baudrate(self, value):
        self.baudrate = value

    async def read(self, size=4096):
        return await self.rx.get()

    async def close(self):
        self.opened = False
        if self.stream:
            self.stream.cancel()
            await asyncio.gather(self.stream, return_exceptions=True)
            self.stream = None

    def send(self, command, data=b"", status=0):
        self.rx.put_nowait(response(command, data, status, self.address))

    def tag_payload(self, *, scenario=False):
        cfg = self.inventory_config
        n = (
            self.cfg[10][1]
            if scenario
            else (cfg.tid_word_count if cfg and cfg.data.value == "tid" else 0)
        )
        value = bytes(self.memory[2][: n * 2]) if n else self.epc
        fast = not scenario and cfg and cfg.data.value == "fastid"
        if fast:
            value += bytes(self.memory[2][:12])
        phase = bool(self.cfg[9][0] & 16) if scenario else bool(cfg and cfg.phase)
        flags = len(value) | (128 if fast else 0) | (64 if phase else 0)
        trailer = bytes.fromhex("010002000DE31A") if phase else b""
        ant = 0 if self.ports == 16 else 1
        return bytes((ant, flags)) + value + bytes((85,)) + trailer

    async def streaming(self, scenario):
        try:
            while self.opened:
                self.send(0xEE, self.tag_payload(scenario=scenario))
                await asyncio.sleep(0.15)
        except asyncio.CancelledError:
            pass

    async def write(self, data):
        self.tx.extend(data)
        while self.tx and len(self.tx) >= self.tx[0] + 1:
            raw = bytes(self.tx[: self.tx[0] + 1])
            del self.tx[: len(raw)]
            if crc16(raw) != 0:
                raise ValueError("Simulator received invalid CRC")
            if raw[1] not in (self.address, 255):
                continue
            command, payload = raw[2], raw[3:-2]
            if self.inject:
                error, self.inject = self.inject, None
                if error == "timeout":
                    continue
                if error == "tag_error":
                    self.send(command, bytes((4,)), 0xFC)
                elif error == "partial":
                    self.send(command, status=0x13)
                else:
                    self.send(command, status=0xF9)
                continue
            await self.handle(command, payload)
        return len(data)

    async def handle(self, c, d):
        if c == 0x21:
            out = bytes(
                (2, 1, 0x20, 2, 255, 255, self.powers[0], 10, self.ant & 255, 0, 0, self.ant_check)
            )
        elif c == 0x4C:
            out = bytes.fromhex("DEADBEEF")
        elif c == 0x94:
            out = bytes(self.powers)
        elif c == 0x2F:
            self.powers = [v & 127 for v in d]
            if len(self.powers) == 1:
                self.powers *= self.ports
            out = b""
        elif c == 0x3F:
            self.ant = d[0] & 15 if len(d) == 1 else int.from_bytes(d[1:], "big")
            out = b""
        elif c == 0x66:
            self.ant_check, out = d[0], b""
        elif c == 0x24:
            self.send(c)
            self.address = d[0]
            return
        elif c == 0xEB:
            out = self.cfg[d[0]]
        elif c == 0xEA:
            self.cfg[d[1]], out = d[2:], b""
        elif c == 0x22:
            self.region = (
                d[1:]
                if len(d) == 4
                else bytes((((d[0] >> 6) << 2) | (d[1] >> 6), d[0] & 63, d[1] & 63))
            )
            out = b""
        elif c == 0x9E:
            out = self.region
        elif c == 0x7F:
            if len(d) == 3:
                if d[0]:
                    self.profile = int.from_bytes(d[1:], "big")
                out = self.profile.to_bytes(2, "big")
            else:
                if d[0] & 128:
                    self.profile = d[0] & 63
                out = bytes((self.profile & 63,))
        elif c in (0x7B, 0x90, 0x6E, 0x78):
            attr = {0x7B: "retries", 0x90: "drm", 0x6E: "threshold", 0x78: "heartbeat"}[c]
            if d[0] & 128:
                setattr(self, attr, d[0] & 127)
            out = bytes((getattr(self, attr),))
        elif c == 0x79:
            self.write_power, out = d[0], b""
        elif c == 0x7A:
            out = bytes((self.write_power,))
        elif c == 0x46:
            self.gpio, out = d[0], b""
        elif c == 0x47:
            out = bytes(((self.gpio << 4) | 1,))
        elif c == 0x92:
            out = bytes((1, 32))
        elif c == 0x91:
            out = bytes((18,))
        elif c == 0x70:
            self.save_len, out = d[0], b""
        elif c == 0x71:
            out = bytes((self.save_len,))
        elif c == 0x74:
            out = bytes((0, 1))
        elif c == 0x18:
            out = bytes.fromhex("00010003")
        elif c == 0x72:
            self.send(c, bytes((1, 1, len(self.epc))) + self.epc + bytes((85, 3)), 1)
            return
        elif c in (1, 0x0F, 0x1A):
            tag = self.tag_payload()
            self.send(c, tag[:1] + bytes((1,)) + tag[1:], 1)
            if d and d[0] & 128 and c == 1:
                self.send(c, bytes.fromhex("01001400000001"), 0x26)
            return
        elif c == 0x19:
            cfg = self.inventory_config
            value = bytes(
                self.memory[cfg.memory_bank][
                    cfg.word_address * 2 : (cfg.word_address + cfg.word_count) * 2
                ]
            )
            self.send(
                c,
                bytes((1, 2, 0, len(self.epc)))
                + self.epc
                + bytes((85, 129, len(value)))
                + value
                + bytes((85,)),
                1,
            )
            if d[0] & 128:
                self.send(c, bytes.fromhex("01001400000001"), 0x26)
            return
        elif c in (0x50, 0x76):
            self.mode = d[0] if c == 0x76 else self.mode
            if c == 0x50 or self.mode:
                if self.stream:
                    self.stream.cancel()
                self.stream = asyncio.create_task(self.streaming(c == 0x50))
            elif self.stream:
                self.stream.cancel()
                await asyncio.gather(self.stream, return_exceptions=True)
                self.stream = None
            out = b""
        elif c == 0x51:
            if self.stream:
                self.stream.cancel()
                await asyncio.gather(self.stream, return_exceptions=True)
                self.stream = None
            out = b""
        elif c == 0x77:
            out = bytes((self.mode,)) + self.rt
        elif c == 0x75:
            # The simulator only implements the basic saved EPC configuration.
            if len(d) != 5:
                self.send(c, status=0xF9)
                return
            self.rt = d + bytes((1, 0, 32, 0)) + bytes(32) + bytes(2)
            out = b""
        elif c in (2, 0x15, 3, 0x16, 0x10):
            writing = c in (3, 0x16, 0x10)
            offset = 1 if writing else 0
            count = d[0] if writing else None
            enum = d[offset]
            offset += 1 + (enum * 2 if enum not in (0, 255) else 0)
            bank, offset = d[offset], offset + 1
            width = 2 if c in (0x15, 0x16) else 1
            adr = int.from_bytes(d[offset : offset + width], "big")
            offset += width
            if writing:
                self.memory[bank][adr * 2 : (adr + count) * 2] = d[offset : offset + count * 2]
                out = b""
            else:
                count = d[offset]
                out = bytes(self.memory[bank][adr * 2 : (adr + count) * 2])
                if len(out) != count * 2:
                    self.send(c, bytes((3,)), 0xFC)
                    return
        elif c in (0x25, 0x28, 0x33, 0x40, 0x6A, 0x73, 0x9A):
            out = b""
        elif c == 0x93:
            return
        else:
            self.send(c, status=0xF9)
            return
        self.send(c, out)
