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
    InventoryMode,
    Outcome,
    ReaderState,
    StateError,
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
        self.range_control = bytes.fromhex("00000064")
        self.mode = 0

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
        if cmd == 0xEB and data[3:-2] == b"\x0b":
            payload = bytes(4)  # Disabled CFG11 header observed on the one-port reader.
        if cmd == 0xEB and data[3:-2] == b"\x10":
            payload = self.range_control
        if cmd == 0xEA and data[4] == 16:
            assert data[3] == 1  # Range Control defaults to volatile writes.
            self.range_control = data[5:-2]
        if cmd == 0x77:
            payload = (
                bytes((self.mode, 0, 0, 0, 4, 0, 0, 0, 0, 0)) + bytes.fromhex("E280") + bytes(32)
            )
        if cmd == 0x76:
            assert data[3] & 0x80
            self.mode = data[3] & 0x7F
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
        original_range = (await r.get_range_control()).require_success()
        assert original_range == 100
        (await r.set_range_control(90)).require_success()
        assert (await r.get_range_control()).require_success() == 90
        (await r.set_range_control(original_range)).require_success()
        assert (await r.get_range_control()).require_success() == original_range
        mask = await r.get_inventory_mask()
        assert mask.ok and mask.require_success() is None and mask.raw_data == bytes(4)
        mode = await r.get_working_mode()
        assert mode.require_success().config.mask is None
        assert mode.raw_data[10:12] == bytes.fromhex("E280")
        (await r.set_working_mode(1)).require_success()
        try:
            await r.inventory_once()
        except StateError:
            pass
        else:
            raise AssertionError("Inventory in autonomous mode was not blocked")
        stream = await r.start_inventory(InventoryMode.REAL_TIME)
        peer.rx.put_nowait(response(0xEE, bytes.fromhex("0102ABCD55")))
        stop = await stream.stop()
        assert stop.complete and peer.mode == 0 and len(stream.drain()) == 1
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
        "disabled_cfg11": True,
        "disabled_realtime_mask": True,
        "range_control": True,
        "working_mode": True,
        "stop_and_drain": True,
        "readback": True,
        "cancellation": True,
        "leaked_tasks": len(leaked),
    }
