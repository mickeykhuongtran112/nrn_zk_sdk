# Test console

A local browser interface for exercising the SDK through CPython and serial.
It includes a simulated reader for evaluation without hardware. Python owns the
serial port; the browser communicates only with the local HTTP server.

## Run

From the repository root with your virtual environment active:

```sh
python -m pip install -e ".[dev,serial]"
python -m tests.demo_app --port COM3 --baud 115200 --ports 1
```

Open [the console](http://127.0.0.1:8765). Use `--http-port 8766` if the HTTP port
is busy, or `--no-browser` to prevent automatic browser launch.

1. Select **Simulated reader** for a first software-only run, or choose the actual
   port, baud rate, address, and antenna count for hardware.
2. Click **Connect**, then run `get_reader_info` and `get_power`.
3. Run `inventory_once` for a bounded scan. For continuous reading, choose
   `start_inventory` and Scenario mode.
4. Use **Stop inventory**, then **Disconnect** when finished. Press Ctrl+C in the
   terminal to stop the server.

Connect opens the transport without setting RF power or region. A saved working
mode can already be active on the reader; host lifecycle “idle” does not prove RF
is off. Other serial applications must release the port first.

## Commands

The console exposes 74 operations plus connection open/close. Forms convert values
to SDK types; **Advanced JSON arguments** supports nested inputs. Click
**Use this JSON** to apply them. Byte strings are hexadecimal; memory addresses use
16-bit words, while mask addresses use bits.

Select a tag row to fill its EPC/TID target. Tag writes require **Enable this tag
write**. Lock, Kill, and Erase require their action word; single-tag EPC writes
also require confirmation that only one physical tag is in range.

Results retain native `outcome`, `status`, `tag_error`, `confirmation`,
`diagnostics`, and `steps`. “ACCEPTED” means the HTTP server accepted the job.
Only its final result describes device execution.

`start_inventory(mode="real_time")` manages the report iterator and stop.
Calling `set_working_mode` directly selects a mode but does not create that
session; only `persist=True` changes the boot mode. The console attempts to stop a directly selected Real-time/Trigger mode
when requested or disconnected.

## Logs and exports

- **Export CSV** saves retained tag entries with measurement metadata.
- **Export JSONL** saves retained event history; rotating logs are written under
  `local_data/demo_logs/`.
- **Pause view** pauses browser log rendering, not inventory or disk logging.
- Raw trace bytes can contain EPCs, TIDs, and tag passwords. Review exports before sharing.

The server retains 5,000 events in RAM; the UI retains 1,200 and renders up to 200
log rows. Disk logs rotate at 10 MB with three backups, using a 20,000-event queue.
Tag storage retains 5,000 ID/antenna entries and displays the first 1,000. Overflow
and disk errors have explicit counters.

Live tag counts use a separate HTTP stream, coalesced at approximately 33 ms.
A slow client receives current totals. The snapshot fallback runs at roughly
750 ms plus request time. RSSI and phase units are explained in
[measurements](../../docs/phase_and_live_view.md).

## Recovery

After an uncertain operation, reset or resynchronize the reader before selecting
**Module reset / clean wire boundary established** and reconnecting. That checkbox
records an operator assertion; it does not reset the device. Recovery state is
kept per port for the lifetime of the server.

After changing SDK or frontend files, stop/disconnect, restart the Python server,
and reload the page. HTML/JS/CSS are fixed for the lifetime of a server instance.
A page refresh alone cannot reload Python code.

The server binds to loopback and checks Host, Origin, and a session token. It is a
local evaluation tool. Browser heartbeat loss triggers a stop attempt after
30 seconds; closing a tab cannot guarantee cleanup after process or USB failure.

## Simulator

The simulator uses EPC `E20034120123456789000001` and TID
`E280116060000205DEADBEEF`. It exercises the actual codec, parser, and dispatcher.
**Inject once** supplies a native failure, tag error, persistence failure, or
missing response for the next operation.

Simulation covers configuration, inventory, buffers, and memory for software
evaluation. Unsupported simulated commands return native failures. Simulator
timing is not an RF benchmark.

Run its checks with:

```sh
python -m pytest tests/integration/test_demo_app.py tests/integration/test_demo_live.py
node --test tests/browser/demo_client.test.cjs
```

The console is included in the source archive, not the SDK wheel.
