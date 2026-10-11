# Getting started

You need Python 3.11 or later, a compatible reader, its serial driver, and an antenna
connected to the port you intend to use. Check the reader's power supply, interface
voltage, regional RF settings, and baud rate before starting inventory.

## Install

Run these commands from the repository root. A virtual environment keeps the SDK's
development tools separate from your other Python applications.

```sh
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on Linux and macOS:

```sh
source .venv/bin/activate
```

Then install the SDK:

```sh
python -m pip install ".[serial]"
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python`; activation is optional. For SDK development, install `".[dev,serial]"`
with `-e` instead.

You can also copy `src/zk_rfid.py` and the project license into an application and
install `pyserial` separately. Both installation methods use `from zk_rfid import ...`.
The wheel contains the Python module; examples, browser assets, and test tools are
provided in the repository and source archive.

## Connect

Find the port in your operating system or run:

```sh
python -m serial.tools.list_ports
python examples/reader_info.py --port COM3 --baud 115200 --ports 1
```

Replace `COM3` with the actual port. Use `/dev/ttyUSB0` or the appropriate device
path on Linux. Close other applications using that port first.

The SDK does not autodetect the baud rate, module model, or antenna layout.
`--ports` accepts 1, 4, 8, or 16. Examples default to 115200 baud when `--baud` is
omitted; always pass the configured baud explicitly during initial setup.
The default reader address is 0; use `--address` if yours differs.

## Read tags

Answer and Scenario require Answer working mode. The SDK checks before inventory
and raises a clear error if the reader is running Real-time/Trigger. On an open
reader, explicitly call
`set_working_mode(WorkingMode.ANSWER, persist=False)` to switch without changing
the saved boot mode. No automatic mode write occurs when connecting.

```sh
python examples/inventory_answer.py --port COM3 --baud 115200 --ports 1 --antenna 1 --scan-time 3
```

This runs one Answer round on ANT1 for a nominal 300 ms scan. Output includes tag
reports, termination status, and any diagnostics. A successful exchange with no
reports means the reader answered but found no matching tags.

For a continuous Scenario session:

```sh
python examples/inventory_scenario.py --port COM3 --baud 115200 --ports 1 --antenna 1 --seconds 5
```

Scenario temporarily applies and verifies its query configuration, then restores
it after a successful stop. `--seconds` controls this example's run time; Answer's
`--scan-time` does not apply. See [Inventory](inventory_modes.md) for S-CST and
cleanup, and [RF settings](rf_settings.md) for region and profile configuration.

## Integrate

Create one `ZKReader` per physical connection and keep it inside an async context
manager. Use `ZKReader` methods for device I/O; module-level functions such as
`read_memory()` build requests without sending them.

Every application should handle these separately:

- Local exceptions, such as invalid arguments or conflicting operations.
- Reader results with `success`, `failure`, `partial`, or `unknown` outcomes.
- Inventory completion, received reports, and dropped-report counts.

Call `require_success()` when an operation must succeed before the next step.
After a timeout following transmission, inspect the result and recover the device
before sending another command. See [Results and recovery](api.md).

The SDK does not load `.env` files. Pass connection settings explicitly. Environment
variables under `ZK_*` are used only by the opt-in [hardware tests](validation.md#hardware-tests).

## Troubleshooting

| Symptom | Check |
|---|---|
| Port cannot open | Device path, driver, permissions, and other serial applications |
| Reader-info timeout | Baud rate, reader address, wiring, interface, and power supply |
| Reader answers but no tags appear | Antenna selection, region, RF power, tag frequency, orientation, and masks |
| `partial` after a setter | Native status and diagnostics; status `0x13` means persistence failed |
| `unknown` or recovery required | Reset/resynchronize the reader, then explicitly recover the connection |
| Test console shows stale fields | Stop, disconnect, restart the Python server, and reload the page |

Keep raw traces in `local_data/` while debugging. They may contain tag identifiers
and passwords; review their contents before attaching them to an issue.
