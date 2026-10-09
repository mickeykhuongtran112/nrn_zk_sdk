"""Capture Answer inventory TX/RX; emits RF and changes the reader inventory buffer."""

import argparse
import asyncio
import json
from pathlib import Path

from _common import CaptureTransport, emit, json_default

from zk_rfid import InventoryConfig, ReaderCapabilities, SerialTransport, ZKReader


async def run(args):
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting a lab trace.
    with path.open("x", encoding="utf-8") as stream:
        transport = CaptureTransport(
            SerialTransport(args.port, args.baud),
            stream,
            dict(
                source="captured",
                model=args.model,
                firmware=args.firmware,
                port=args.port,
                baud=args.baud,
                antenna_ports=args.ports,
                operator_notes=args.notes,
            ),
        )
        async with ZKReader(
            transport,
            timeout=args.timeout,
            capabilities=ReaderCapabilities(
                antenna_ports=args.ports, model=args.model, firmware=args.firmware
            ),
        ) as reader:
            info = await reader.get_reader_info()
            emit(info)
            end = asyncio.get_running_loop().time() + args.seconds
            while asyncio.get_running_loop().time() < end:
                outcome = await reader.inventory_once(
                    InventoryConfig(antenna=args.antenna, scan_time_100ms=args.scan_time)
                )
                stream.write(
                    json.dumps(dict(direction="outcome", result=outcome), default=json_default)
                    + "\n"
                )
                emit(outcome)
                if reader.dispatcher.fault:
                    break


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("port", "model", "firmware", "output"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--baud", type=int, default=57600)
    p.add_argument("--ports", type=int, choices=(1, 4, 8, 16), default=1)
    p.add_argument("--antenna", type=int, default=1)
    p.add_argument("--seconds", type=float, default=10)
    p.add_argument("--scan-time", type=int, default=3)
    p.add_argument("--timeout", type=float, default=3)
    p.add_argument("--notes", default="")
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
