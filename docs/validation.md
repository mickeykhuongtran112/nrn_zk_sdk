# Validation

Software checks and physical-reader observations have different scopes. Passing
the software suite does not qualify every model, firmware revision, tag chip, or
RF environment.

## Software checks

The release audit on 2026-10-11 used CPython 3.14.6 on Windows: **184 passed,
6 hardware tests deselected**. Node 24.16.0 passed **10 tests** across the console client
and Web Serial bridge. The real Pyodide 314.0.7 runtime (Python 3.14.2) passed the
shared harness with eight TX vectors, 2,000 fragmented frames, read-back,
cancellation, and zero leaked tasks.

The suite covers:

- CRC, framing, chunk boundaries, malformed data, and bounded parser recovery.
- Single RX ownership, serialized commands, response matching, short writes,
  timeouts, cancellation, EOF, and recovery gates.
- Native results, persistence failure, nested tag errors, and malformed success payloads.
- Inventory completion, statistics, FastID/TID/Mix, Scenario restore,
  Real-time mode, stop semantics, late reports, and queue overflow.
- Memory bounds, EPC/PC preservation, changed targets/passwords, read-back,
  partial verification, and uncertain writes without retries.
- Standalone imports without site packages, wheel installation, and the shared
  CPython/Pyodide implementation.
- Console forms, simulation, live-stream recovery, exports, and browser transport lifecycle.

The release audit also checks tracked/ignored paths, English content, local links,
common secret patterns, MIT metadata, and wheel/source contents. The wheel was
installed in a fresh environment without runtime dependencies and passed the
shared harness. README and memory examples were executed against the byte-level
simulator. No protocol behavior was changed by the documentation rewrite.

[CONTRIBUTING.md](../CONTRIBUTING.md) lists reproducible commands. CI is configured
for Python 3.11/3.14 and Node 22. The local results above do not imply that the
remote workflow or every supported Python/OS combination has been exercised.

## Hardware coverage

| Record | Coverage | Limit |
|---|---|---|
| [2026-10-09 session](hardware_live_view_check.md) | One-port Scenario, phase/RSSI display, counters, stop; 7,594 reports | Exact model/firmware and tag population absent from the retained summary |
| Three reported hardware tests, 2026-10-09 | Reader info/power, region/profile, Answer round | Reported screenshots; no published raw capture |

The session predates the single-file consolidation. No new hardware session was
run for the documentation/release audit. Physical Web Serial remains unvalidated.
Historical DLL loopback vectors are documented fixtures, not new RF captures.

Further qualification needs model/firmware-specific traces, memory read-back on
the intended tag, persistence across power cycles, stop/late-report timing,
CFG25/29 dialects, and 16-port layouts. Use the [RF benchmark](inventory_benchmark.md)
to assess completeness, stray reads, latency, and repeatability.

## Hardware tests

Hardware tests are excluded by default. To run reader configuration checks in
PowerShell, select the actual device explicitly:

```powershell
$env:ZK_HARDWARE_PORT = "COM3"
$env:ZK_BAUDRATE = "115200"
$env:ZK_ANTENNA_PORTS = "1"
$env:ZK_MODEL = "your-reader-model"
$env:ZK_FIRMWARE = "your-firmware-revision"
python -m pytest -m hardware tests/hardware/test_reader_config.py
```

In a POSIX shell, use `export ZK_HARDWARE_PORT=/dev/ttyUSB0` and export the other
variables before running the same pytest command. The SDK does not load `.env`
automatically.

| Variable | Use / default |
|---|---|
| `ZK_HARDWARE_PORT` | Required; no device opened if absent |
| `ZK_BAUDRATE` | Serial baud; default 57600 |
| `ZK_ANTENNA_PORTS` | Physical port count; default 1 |
| `ZK_MODEL`, `ZK_FIRMWARE` | Deployment metadata |
| `ZK_TEST_TID` | Known scratch-tag TID, hexadecimal |
| `ZK_ALLOW_TAG_WRITE` | Must be `1` to run the User-memory write test |
| `ZK_USER_WORD_ADDRESS` | Scratch User word; default 0 |

Inventory tests emit RF; Scenario tests temporarily change and restore settings.
The User-memory test needs a writable tag and attempts to restore the old word
only while connection state remains known. It does not retry uncertain writes.
The suite never runs Kill or permanent Lock automatically.
