"""Read a Scenario stream; optionally configure the three S-CST profile slots."""

import argparse
import asyncio
import math
import sys

from zk_rfid import (
    InventoryConfig,
    InventoryData,
    InventoryMode,
    ReaderCapabilities,
    ScenarioSession,
    SerialTransport,
    TagReport,
    WorkingMode,
    ZKReader,
)


def session_selector(value):
    try:
        return ScenarioSession[value.upper().replace("-", "_")]
    except KeyError:
        try:
            return ScenarioSession(int(value, 0))
        except ValueError:
            raise argparse.ArgumentTypeError(
                "Use S0, S1, S2, S3, S-CST, S-PRO, S-RPT, S-CTP, AUTO, or a native value"
            ) from None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument(
        "--baud", type=int, default=115200, help="Reader baud rate (default: 115200)"
    )
    parser.add_argument("--address", type=lambda v: int(v, 0), default=0)
    parser.add_argument("--ports", type=int, choices=(1, 4, 8), default=1)
    antennas = parser.add_mutually_exclusive_group()
    antennas.add_argument("--antenna", type=int, default=1)
    antennas.add_argument(
        "--antenna-mask",
        type=lambda value: int(value, 0),
        help="Scenario antenna mask, e.g. 0xD for ANT1/3/4; overrides --antenna",
    )
    parser.add_argument("--q", type=int, choices=range(16), default=4, metavar="0..15")
    parser.add_argument(
        "--session",
        type=session_selector,
        default=ScenarioSession.S0,
        metavar="SELECTOR",
        help="S0-S3, S-CST, S-PRO, S-RPT, S-CTP, AUTO, or native integer (default: S0)",
    )
    parser.add_argument("--target", type=str.upper, choices=("A", "B"), default="A")
    parser.add_argument("--phase", action="store_true")
    parser.add_argument(
        "--tid-words",
        type=int,
        choices=range(16),
        default=0,
        metavar="0..15",
        help="0 reads EPC; 1-15 reads that many TID words from word 0",
    )
    parser.add_argument(
        "--seconds", type=float, default=5, help="Application run time (default: 5)"
    )
    parser.add_argument("--timeout", type=float, default=4, help="Command timeout (default: 4 s)")
    parser.add_argument(
        "--profiles",
        nargs=3,
        type=lambda v: int(v, 0),
        metavar=("FIRST", "SECOND", "THIRD"),
        help="S-CST only: write CFG31 without saving; values remain set after Stop",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.antenna <= args.ports:
        parser.error("--antenna must be between 1 and --ports")
    if args.antenna_mask is not None and not 1 <= args.antenna_mask < (1 << args.ports):
        parser.error("--antenna-mask must select at least one port within --ports")
    if any(not math.isfinite(v) or v <= 0 for v in (args.seconds, args.timeout)):
        parser.error("--seconds and --timeout must be positive finite values")
    if args.profiles is not None:
        if args.session is not ScenarioSession.S_CST:
            parser.error("--profiles requires --session S-CST")
        if any(not 0 <= v <= 65535 for v in args.profiles):
            parser.error("--profiles values must be 16-bit native IDs (0-65535)")
    return args


def print_report(event):
    if not isinstance(event, TagReport):
        return
    identifier = event.epc if event.epc is not None else event.tid
    fields = [
        "EPC" if event.epc is not None else "TID",
        identifier.hex().upper() if identifier is not None else "-",
        f"antenna={event.antenna}",
        f"rssi_raw={event.rssi_raw}",
    ]
    for name in (
        "phase_begin_raw",
        "phase_end_raw",
        "phase_begin_degrees",
        "phase_end_degrees",
        "frequency_khz",
    ):
        value = getattr(event, name)
        if value is not None:
            display = f"{value:.3f}" if name.endswith("_degrees") else value
            fields.append(f"{name}={display}")
    print(" ".join(fields))


async def read_tags(reader, args):
    mode = (await reader.get_working_mode()).require_success().mode
    if mode is not WorkingMode.ANSWER:
        raise RuntimeError(
            "Reader is in Real-time/Trigger mode. Switch explicitly with "
            "set_working_mode(WorkingMode.ANSWER, persist=False) before running this example."
        )
    # CFG31 is caller-managed. No profile write occurs unless explicitly requested.
    if args.profiles is not None:
        profiles = tuple(args.profiles)
        (await reader.set_custom_profiles(profiles, persist=False)).require_success()
        actual = (await reader.get_custom_profiles()).require_success()
        if actual != profiles:
            raise RuntimeError("Custom profile read-back mismatch; inventory was not started")
        print("CFG31 updated:", actual, "(volatile; remains set after Stop)")
    elif args.session is ScenarioSession.S_CST:
        print("Using existing CFG31:", (await reader.get_custom_profiles()).require_success())

    config = InventoryConfig(
        session=args.session,
        target=0 if args.target == "A" else 1,
        antenna=args.antenna,
        q=args.q,
        phase=args.phase,
        data=InventoryData.TID if args.tid_words else InventoryData.EPC,
        tid_word_count=args.tid_words or 6,
    )
    session = await reader.start_inventory(
        InventoryMode.SCENARIO, config=config, antenna_mask=args.antenna_mask
    )
    try:
        async with asyncio.timeout(args.seconds):
            async for event in session:
                print_report(event)
    except TimeoutError:
        pass
    finally:
        outcome = await session.stop()
        for event in session.drain():
            print_report(event)
        print("Stop:", outcome.termination_reason, "complete=", outcome.complete)
        print("Reports:", outcome.received_count, "dropped:", outcome.dropped_count)
        for diagnostic in outcome.diagnostics:
            print("Diagnostic:", diagnostic, file=sys.stderr)
    return outcome


async def main(args):
    async with ZKReader(
        SerialTransport(args.port, args.baud),
        address=args.address,
        timeout=args.timeout,
        capabilities=ReaderCapabilities(antenna_ports=args.ports),
    ) as reader:
        outcome = await read_tags(reader, args)
    return 0 if outcome.complete else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(parse_args())))
