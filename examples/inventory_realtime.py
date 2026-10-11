"""Optional autonomous/trigger inventory using the reader's existing 0x75 settings."""

import argparse
import asyncio
import math

from zk_rfid import (
    InventoryConfig,
    InventoryData,
    InventoryMode,
    ReaderCapabilities,
    SerialTransport,
    ZKReader,
)


async def read_tags(reader, *, seconds=5, trigger=False):
    saved = (await reader.get_working_mode()).require_success()
    kind = InventoryData.TID if saved.config.tid_word_count else InventoryData.EPC
    session = await reader.start_inventory(
        InventoryMode.REAL_TIME, config=InventoryConfig(data=kind), trigger=trigger
    )
    try:
        async with asyncio.timeout(seconds):
            async for event in session:
                print(event)
    except TimeoutError:
        pass
    finally:
        outcome = await session.stop()  # Leaves current mode Answer; boot mode is unchanged.
        for event in session.drain():
            print(event)
        print("Stop:", outcome.termination_reason, "complete=", outcome.complete)
        for diagnostic in outcome.diagnostics:
            print("Diagnostic:", diagnostic)
    return outcome


async def main(args):
    async with ZKReader(
        SerialTransport(args.port, args.baud),
        address=args.address,
        capabilities=ReaderCapabilities(antenna_ports=args.ports),
    ) as reader:
        outcome = await read_tags(reader, seconds=args.seconds, trigger=args.trigger)
    return 0 if outcome.complete else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--address", type=lambda value: int(value, 0), default=0)
    parser.add_argument("--ports", type=int, choices=(1, 4, 8, 16), default=1)
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--trigger", action="store_true", help="Use the configured GPI trigger")
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("--seconds must be positive and finite")
    raise SystemExit(asyncio.run(main(args)))
