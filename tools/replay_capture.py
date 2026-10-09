"""Replay saved chunks into the native parser without opening hardware."""

import argparse
import json
from pathlib import Path
from zk_rfid.protocol import FrameParser, crc16
from zk_rfid.protocol.status import interpret_status
from _common import emit


def replay(path):
    parser = FrameParser()
    tx_buffer = bytearray()
    summary = dict(tx_frames=0, rx_frames=0, tx_crc_errors=0, metadata=None)
    with Path(path).open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            item = json.loads(line)
            direction = item.get("direction", "").lower()
            if direction == "metadata":
                summary["metadata"] = item.get("metadata")
                continue
            if direction not in ("tx", "rx"):
                continue
            data = bytes.fromhex(item["hex"])
            if direction == "tx":
                tx_buffer.extend(data)
                while tx_buffer and len(tx_buffer) >= tx_buffer[0] + 1:
                    length = tx_buffer[0] + 1
                    wire = bytes(tx_buffer[:length])
                    del tx_buffer[:length]
                    summary["tx_frames"] += 1
                    if len(wire) < 5 or crc16(wire):
                        summary["tx_crc_errors"] += 1
                    else:
                        emit(
                            dict(
                                line=lineno,
                                direction="tx",
                                command=wire[2],
                                data=wire[3:-2],
                                raw=wire,
                            )
                        )
            else:
                for frame in parser.feed(data):
                    summary["rx_frames"] += 1
                    emit(
                        dict(
                            line=lineno,
                            direction="rx",
                            frame=frame,
                            status=interpret_status(frame.command, frame.status, frame.data),
                        )
                    )
    summary.update(
        parser=parser.diagnostics,
        rx_incomplete_bytes=len(parser.buffer),
        tx_incomplete_bytes=len(tx_buffer),
    )
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture")
    args = p.parse_args()
    summary = replay(args.capture)
    emit(summary)
    if (
        summary["tx_crc_errors"]
        or summary["rx_incomplete_bytes"]
        or summary["tx_incomplete_bytes"]
        or summary["parser"].discarded_bytes
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
