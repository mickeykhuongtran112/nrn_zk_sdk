"""Shared CLI plumbing; importing examples never opens a COM port."""

import argparse
import asyncio
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from zk_rfid import (
    ZKReader,
    ReaderCapabilities,
    InventoryConfig,
    InventoryData,
    InventoryMode,
    MemoryBank,
    TagMask,
    TagTarget,
)
from zk_rfid.compat.nation import NationAdapter
from zk_rfid.transports.serial import SerialTransport


def json_default(value):
    if isinstance(value, bytes):
        return value.hex().upper()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(type(value).__name__)


def show(value):
    print(json.dumps(value, default=json_default, ensure_ascii=False, indent=2))


def parser_for(name):
    p = argparse.ArgumentParser(description=f"ZK SDK example: {name}")
    p.add_argument("--port", required=True, help="Explicit COM port; no automatic discovery")
    p.add_argument("--baud", type=int, default=57600)
    p.add_argument("--address", type=lambda s: int(s, 0), default=0)
    p.add_argument("--ports", type=int, choices=(1, 4, 8, 16), default=1)
    p.add_argument("--timeout", type=float, default=4.0)
    if name.startswith("inventory"):
        p.add_argument("--antenna", type=int, default=1)
        p.add_argument("--q", type=int, default=4)
        p.add_argument("--session", type=int, default=0)
        p.add_argument(
            "--scan-time", type=int, default=20, help="Units of 100 ms; zero is unlimited"
        )
        p.add_argument("--phase", action="store_true")
        p.add_argument("--seconds", type=float, default=5)
    if name == "inventory_scenario":
        p.add_argument("--tid-words", type=int, default=0)
    if name in ("read_memory", "write_user_memory", "write_epc", "inventory_mix"):
        p.add_argument("--word-address", type=int, default=0)
        p.add_argument("--words", type=int, default=1)
        p.add_argument("--password", default="00000000", help="Access password, 8 hex digits")
    if name in ("read_memory", "write_user_memory", "write_epc"):
        p.add_argument(
            "--tid", required=True, help="Known target TID prefix, hex, mask starts at bit 0"
        )
    if name == "read_memory" or name == "inventory_mix":
        p.add_argument("--bank", type=int, choices=(0, 1, 2, 3), default=3)
    if name in ("write_user_memory", "write_epc"):
        p.add_argument(
            "--data", required=True, help="Hex words to write to the explicitly selected tag"
        )
    if name == "get_set_power":
        p.add_argument("--dbm", type=int, help="Omit to query only")
        p.add_argument("--persist", action="store_true")
    return p


async def run_example(name, args):
    transport = SerialTransport(args.port, args.baud)
    async with ZKReader(
        transport,
        address=args.address,
        timeout=args.timeout,
        capabilities=ReaderCapabilities(antenna_ports=args.ports),
    ) as reader:
        if name == "reader_info":
            show(await reader.get_reader_info())
            show(await reader.get_serial_number())
            show(reader.get_capabilities())
        elif name == "get_set_power":
            show(await reader.get_power())
            if args.dbm is not None:
                result = await reader.set_power(args.dbm, persist=args.persist)
                show(result)
                result.require_success()
                show(await reader.get_power())
        elif name.startswith("inventory"):
            kind = {
                "inventory_fastid": InventoryData.FAST_ID,
                "inventory_mix": InventoryData.MIX,
            }.get(name, InventoryData.EPC)
            tid_words = getattr(args, "tid_words", 0)
            if tid_words:
                kind = InventoryData.TID
            cfg = InventoryConfig(
                data=kind,
                q=args.q,
                session=args.session,
                antenna=args.antenna,
                scan_time_100ms=args.scan_time,
                phase=args.phase,
                tid_word_count=tid_words or 6,
                memory_bank=MemoryBank(getattr(args, "bank", 3)),
                word_address=getattr(args, "word_address", 0),
                word_count=getattr(args, "words", 1),
                access_password=bytes.fromhex(getattr(args, "password", "00000000")),
            )
            if name == "inventory_scenario":
                session = await reader.start_inventory(InventoryMode.SCENARIO, config=cfg)
                try:
                    async with asyncio.timeout(args.seconds):
                        async for report in session:
                            show(report)
                except TimeoutError:
                    pass
                finally:
                    show(await session.stop())
            else:
                show(await reader.inventory_once(cfg))
        elif name in ("read_memory", "write_user_memory", "write_epc"):
            tid = bytes.fromhex(args.tid)
            target = TagTarget(mask=TagMask(MemoryBank.TID, 0, len(tid) * 8, tid))
            password = bytes.fromhex(args.password)
            if name == "read_memory":
                show(
                    await reader.read_memory(
                        MemoryBank(args.bank),
                        args.word_address,
                        args.words,
                        target=target,
                        access_password=password,
                    )
                )
            elif name == "write_user_memory":
                show(
                    await reader.write_memory(
                        MemoryBank.USER,
                        args.word_address,
                        bytes.fromhex(args.data),
                        target=target,
                        access_password=password,
                        verify=True,
                    )
                )
            else:
                show(
                    await reader.write_epc(
                        bytes.fromhex(args.data), target=target, access_password=password
                    )
                )
        elif name == "nation_adapter":
            adapter = NationAdapter(reader)
            show(adapter.get_sdk_info())
            show(await adapter.Query_Reader_Information())
            show(await adapter.query_reader_power())


def main(name):
    args = parser_for(name).parse_args()
    asyncio.run(run_example(name, args))
