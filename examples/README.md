# Examples

Start with Answer or Scenario. Both require Answer working mode; the SDK checks
before inventory and does not change it automatically. To switch explicitly,
use `set_working_mode(WorkingMode.ANSWER, persist=False)` on an open reader.
After a stream, call `stop()`, process `session.drain()`, and inspect the outcome.

`inventory_realtime.py` is optional for autonomous/trigger applications. It uses
the reader's existing configuration and does not save Work Mode changes:

```sh
python examples/inventory_realtime.py --port COM3 --baud 115200 --seconds 5
```

Install the SDK with `python -m pip install ".[serial]"` from the repository root.
All Python hardware examples take an explicit port; none opens hardware when imported or when
called with `--help`.

```sh
python examples/reader_info.py --port COM3 --baud 115200 --ports 1
python examples/inventory_answer.py --port COM3 --baud 115200 --antenna 1 --scan-time 3
```

Replace the port and baud rate with your reader's configuration. Antennas are
numbered from 1. Examples default to 115200 baud and one port when omitted.

| Example | Task |
|---|---|
| [reader_info.py](reader_info.py) | Read identification and capabilities |
| [get_set_power.py](get_set_power.py) | Read power; add `--dbm` to change it, `--persist` to save |
| [inventory_answer.py](inventory_answer.py) | One EPC inventory round |
| [inventory_fastid.py](inventory_fastid.py) | EPC + TID from compatible FastID tags |
| [inventory_mix.py](inventory_mix.py) | EPC + selected memory words |
| [inventory_scenario.py](inventory_scenario.py) | Standalone Scenario/S-CST stream with explicit stop |
| [read_memory.py](read_memory.py) | Read a bank using a known TID target |
| [write_user_memory.py](write_user_memory.py) | Write User words and verify |
| [write_epc.py](write_epc.py) | Update PC/EPC and verify using a stable TID |
| [nation_adapter.py](nation_adapter.py) | Optional NATION-style adapter; requires the source checkout's `mapping/` directory |
| [nation_web_service.js](nation_web_service.js) | Browser service example: existing UI callback shape, Scenario Start/Stop |

For NATION migration, start with the [mapping manual](../mapping/nation_to_zk/README.md).
The browser service applies approved GReaderTool baseband/region choices only on
explicit configuration calls. Antenna Set always uses SAVE. Its `includeTid` option
selects Answer FastID across the selected ports; see the mapping manual for limits.
Device errors end FastID and reach the browser `error` event after cleanup.
When Set succeeds but Get fails, the service error retains both steps; configuration
may already be saved. Read back after recovery rather than retrying the write.

## Scenario

Select a session by name or native integer. This example supports 1-, 4-, and
8-port readers, where the SDK can restore antenna selection after Stop.
Start from Answer working mode; switching from saved Real-time/Trigger mode with
`set_working_mode(WorkingMode.ANSWER, persist=False)` is an explicit temporary change.

```sh
python examples/inventory_scenario.py --port COM3 --baud 115200 --session S1 --target A --seconds 5
python examples/inventory_scenario.py --port COM3 --ports 4 --antenna-mask 0xD --seconds 5
python examples/inventory_scenario.py --port COM3 --baud 115200 --session S-CST --profiles 103 241 285 --seconds 5
```

Use `--antenna` for one port or `--antenna-mask` for a selection (`0xD` = ANT1/3/4).
Scenario sends one Start and restores the previous antenna mask after Stop.
The four-port command requires a four-port reader; hardware validation is pending.

Omit `--profiles` to use existing CFG31 slots. Supplying it writes and reads back
three slots before Start. The write is volatile, but **the slots remain set after
Stop**; session cleanup only restores changed CFG9/10/11 and antenna settings.
The example does not add the vendor demo's preparatory Select commands.

`--seconds` controls the application run time. `--timeout` is the command timeout;
Answer's `--scan-time` does not apply here. Use `--tid-words 6` for a TID-only
stream or omit it for EPC. For selector support and limits, see
[Inventory](../docs/inventory_modes.md#session-and-target).

Add `--phase` to request begin/end phase and RF frequency. The output retains
raw phase values alongside degrees; absent measurements are omitted, not zeroed.
Stop diagnostics go to stderr. The CLI exits with status 1 if inventory or
cleanup is incomplete, including a rejected Stop or failed configuration restore.

## Memory examples

Use a writable test tag and replace the example TID with a known unique identifier.
Read addresses/counts are in words; `--data` and `--password` are hex bytes.

```sh
python examples/read_memory.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --bank 3 --word-address 0 --words 2
python examples/write_user_memory.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --word-address 0 --data 1234ABCD
python examples/write_epc.py --port COM3 --baud 115200 --tid E280116060000205DEADBEEF --data E20034120123456789000002
```

The write examples execute the requested write. A TID prefix that matches multiple
tags is not a unique target. See [Tag memory](../docs/tag_memory.md) before writing.

For JavaScript/TypeScript, use the [Web Serial example](webserial/README.md).
