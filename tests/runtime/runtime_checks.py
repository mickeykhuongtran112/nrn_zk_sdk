"""Shared CPython/Pyodide async and byte-lifecycle checks; stdlib only."""

import asyncio
import gc
import json
import math
import sys
from pathlib import Path

from zk_rfid import (
    FrameParser,
    InventoryConfig,
    Outcome,
    ReaderState,
    TagMask,
    TagTarget,
    ZKReader,
    append_crc,
    crc16,
    decode_answer,
    encode_command,
)


def response(cmd, data=b"", status=0):
    return append_crc(bytes((len(data) + 5, 0, cmd, status)) + data)


class Peer:
    def __init__(self):
        self.rx = asyncio.Queue()
        self.writes = []
        self.silent = False
        self.active = 0

    async def open(self):
        pass

    async def close(self):
        pass

    async def write(self, data):
        self.writes.append(bytes(data))
        if self.silent:
            return len(data)
        cmd = data[2]
        payload = b"\0\1" if cmd == 2 else bytes.fromhex("010102ABCD55") if cmd == 1 else b""
        reply = response(cmd, payload, 1 if cmd == 1 else 0)
        for v in reply:
            self.rx.put_nowait(bytes((v,)))
        return len(data)

    async def read(self, size=4096):
        self.active += 1
        try:
            assert self.active == 1
            return await self.rx.get()
        finally:
            self.active -= 1


async def run_checks(vector_path):
    measurement = decode_answer(
        bytes.fromhex("010142ABCD6E018F018D0E06D2"), InventoryConfig(), ports=1
    )[0]
    assert measurement.phase_begin_raw == 399 and measurement.phase_end_raw == 397
    assert math.isclose(measurement.phase_begin_degrees, 34.713)
    assert math.isclose(measurement.phase_end_radians, 34.539 * math.pi / 180)
    assert measurement.rssi_raw == 110 and measurement.rssi_dbm == -25
    assert measurement.rssi_source == "user_linear_raw_minus_135"
    assert measurement.rssi_in_calibration_range is True
    vectors = json.loads(Path(vector_path).read_text())["vectors"]
    for v in vectors:
        wire = bytes.fromhex(v["frame"])
        assert encode_command(v["address"], v["command"], bytes.fromhex(v["data"])) == wire
        assert crc16(wire) == 0
    parser = FrameParser()
    total = 0
    wire = response(1, bytes.fromhex("010102ABCD55"), 1)
    for _ in range(2000):
        for v in wire:
            total += len(parser.feed(bytes((v,))))
    assert total == 2000 and not parser.buffer
    baseline = set(asyncio.all_tasks())
    peer = Peer()
    async with ZKReader(peer, timeout=0.05) as r:
        out = await r.inventory_once(InventoryConfig())
        assert out.reports[0].epc == bytes.fromhex("ABCD")
        target = TagTarget(mask=TagMask(2, 0, 16, bytes.fromhex("E280")))
        result = await r.write_memory(3, 0, b"\0\1", target=target, verify=True)
        assert result.ok
        peer.silent = True
        task = asyncio.create_task(r.write_memory(3, 0, b"\0\1", target=target))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert r.state is ReaderState.UNKNOWN and r.last_result.outcome is Outcome.UNKNOWN
    await asyncio.sleep(0)
    gc.collect()
    assert peer.active == 0
    leaked = [t for t in asyncio.all_tasks() - baseline if not t.done()]
    assert not leaked, leaked
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "vectors": len(vectors),
        "replayed_frames": total,
        "fragmented_rx": True,
        "phase_conversion": True,
        "user_rssi_mapping": True,
        "readback": True,
        "cancellation": True,
        "leaked_tasks": len(leaked),
    }
