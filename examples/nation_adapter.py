"""Read identity and power through the optional adapter from a source checkout."""

import asyncio
import sys
from pathlib import Path

from _common import parser_for, show
from zk_rfid import ReaderCapabilities, SerialTransport, ZKReader

# The optional mapping package is shipped in the source archive, not the wheel.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mapping.nation_to_zk import NationAdapter


async def run(args):
    async with ZKReader(
        SerialTransport(args.port, args.baud),
        address=args.address,
        timeout=args.timeout,
        capabilities=ReaderCapabilities(antenna_ports=args.ports),
    ) as reader:
        adapter = NationAdapter(reader)
        show(adapter.get_sdk_info())
        show(await adapter.Query_Reader_Information())
        show(await adapter.query_reader_power())


if __name__ == "__main__":
    asyncio.run(run(parser_for("nation_adapter").parse_args()))
