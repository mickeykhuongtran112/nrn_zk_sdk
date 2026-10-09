"""One explicit diagnostic command; continuous modes belong to session APIs."""

import argparse
import asyncio

from _common import emit

from zk_rfid import Dispatcher, SerialTransport


async def run(args):
    if args.command in (0x50, 0x51, 0x76, 0x93):
        raise ValueError("Use inventory session APIs for start/stop/mode lifecycle")
    if args.command not in (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        15,
        16,
        21,
        22,
        24,
        25,
        26,
        0x21,
        0x22,
        0x24,
        0x25,
        0x28,
        0x2F,
        0x33,
        0x3F,
        0x40,
        0x46,
        0x47,
        0x4C,
        0x66,
        0x6A,
        0x6E,
        0x70,
        0x71,
        0x72,
        0x73,
        0x74,
        0x75,
        0x77,
        0x78,
        0x79,
        0x7A,
        0x7B,
        0x7F,
        0x90,
        0x91,
        0x92,
        0x94,
        0x9A,
        0x9E,
        0xEA,
        0xEB,
    ):
        raise ValueError("Command is outside this SDK's Gen2 scope")
    dispatcher = Dispatcher(SerialTransport(args.port, args.baud), address=args.address)
    await dispatcher.open()
    try:
        payload = bytes.fromhex(args.data)
        multi = args.command in (1, 0x0F, 0x19, 0x1A, 0x72)
        statistics = args.command in (1, 0x19) and payload and bool(payload[0] & 128)

        def terminal(frame):
            return not (multi and (frame.status == 3 or statistics and frame.status in (1, 2, 4)))

        frames = await dispatcher.exchange(
            args.command, payload, timeout=args.timeout, terminal=terminal
        )
        for frame in frames:
            emit(frame)
        emit(dispatcher.parser.diagnostics)
    finally:
        await dispatcher.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=57600)
    p.add_argument("--address", type=lambda s: int(s, 0), default=0)
    p.add_argument("--command", type=lambda s: int(s, 0), required=True)
    p.add_argument(
        "--data", default="", help="Raw command payload hex; mutations execute exactly as entered"
    )
    p.add_argument("--timeout", type=float, default=4)
    asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    main()
