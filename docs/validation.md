# Validation

Software checks and physical-reader observations have different scopes. Passing
the software suite does not qualify every model, firmware revision, tag chip, or
RF environment.

## Software checks

The latest full-suite run on 2026-10-13 used CPython 3.14.6 on Windows: **491 passed,
6 hardware tests deselected**. Node 24.16.0 passed **52 tests** across the console client,
Web Serial bridge and NATION service example. The real Pyodide 314.0.7 runtime (Python 3.14.2) passed the
shared harness with eight TX vectors, 2,000 fragmented frames, disabled CFG11 and
Real-time masks, Range Control set/read-back/restore, Work Mode gating, temporary
Real-time Stop and queue draining, cancellation, and zero leaked tasks.

The initial NATION extraction retained the AST of all 159 native definitions and
all seven relocated definitions. Subsequent lifecycle fixes cover unknown Stop
without an owned session, Stop/close during Start, callback timeouts, cancellation,
and Stop/restore failures. Browser checks retain partial outcomes after automatic
cleanup and exercise Start/Stop overlap through real Pyodide.
Four-port regressions select individual ports and multiple-port masks with one
Start, verify mask read-back, preserve tail-report antenna IDs, restore
the previous mask, and test per-port power readback, concurrent partial updates,
and enable/disable without changing other ports. Rejected or mismatched antenna
restoration stays unknown. Disabling the last port is rejected.
These are synthetic protocol tests, not validation on a physical four-port reader.
The mapping checker accounts for 64 public reference callables and 30 command constants;
it validates approved RF choices without device I/O. Core-only isolated
imports, wheel/source archive contents, API indexes and local links passed.
The follow-ups below exercise the adapter on one- and four-port hardware;
cross-reader RF equivalence remains unverified.

Approved-policy regressions cover every GReaderTool speed and full region table,
profile/read-back failures without committing pending run settings, saved antenna
Set/read-back without repeated saved writes at Start, and unsupported plans rejected
before TX. FastID checks cover selected-port order, EPC-only responses, Stop during
a pending round, and cancellation without starting the next port. These additions
were tested synthetically and through Pyodide; no further COM13 commands or
power-cycle persistence checks were performed for the policy update.

Follow-up regressions cover terminal FastID antenna/device errors on declared
one- and four-port readers, including reports received before the error, no next
port/retry, and partial Stop outcomes retaining the status. No-tag and bounded
round endings still advance the sequence. Python bridge and real Pyodide tests
check browser error delivery after cleanup and repeated Stop outcome retention.
Browser configuration tests preserve the acknowledged write when verification
returns failure/partial/unknown or throws, across antenna, profile and both region
setters. Staged run settings remain unchanged; no write is retried.

A COM13/115200 follow-up on 2026-10-12 used the one-port reader at its existing
5 dBm setting. FastID returned 34 reports, all with TID; Scenario returned 51 EPC
reports. Both runs stopped successfully with no dropped/quarantined reports and
returned idle. Before/after snapshots matched for Work Mode, CFG7/8/9/10/11/16/25/29/31,
power, antenna mask, region and profile. The capture contains 75 TX and 160 RX
frames with no CRC errors, discarded bytes or unexpected frames. The only setting
writes were temporary CFG11 apply/restore; no saved, RF or tag writes were sent.
The serial port was closed. Fault regressions use synthetic responses; no antenna
was disconnected and no hardware read-back failure was induced. Raw captures
remain in ignored local lab files. See the subsequent four-port check below.

An initial concurrent run failed the existing continuous post-ACK timing test.
That test passed in isolation, and the full Python suite passed when run separately
from the Node/Pyodide checks. The test relies on host scheduling within its 50 ms
quiet window; it was not relaxed as part of these fixes.

Synthetic checks cover rejected/timed-out Stop, rejected/mismatched restore,
phase output, disabled masks, malformed mask responses and strict outgoing validation.
Range Control tests replay operator-supplied GET/SET frames and cover bounds,
volatile writes, raw reads, malformed responses, and native errors. The reported
CFG25 SET/ACK is also checked against the explicitly selected six-byte layout.

Work Mode checks cover fresh and reopened connections, persistent/temporary
flags, save failures, Stop rejection/timeout/read-back errors, fragmented and
continuous post-ACK streams, bounded quarantine, and cancellation-safe draining.
They also cover direct Answer transitions with delayed/fragmented old reports,
failed interrupt writes, repeat Stop, and repeated consumer cancellation.
Custom Region checks cover V6.8 DLL wire vectors, native/custom response layouts,
validation before TX, error responses, and Web Serial set/read-back/restore.
An operator-supplied SET/GET trace for 918000 kHz, 8 channels and 500 kHz spacing
also has an exact-frame regression, including Save and fragmented RX. This trace
confirms configuration read-back, not measured RF centers or power-cycle retention.
The follow-up Custom Region and reader-configuration subset passed 86 tests.

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
simulator.

[CONTRIBUTING.md](../CONTRIBUTING.md) lists reproducible commands. CI is configured
for Python 3.11/3.14 and Node 22. The local results above do not imply that the
remote workflow or every supported Python/OS combination has been exercised.

The guided-console update adds task-to-API checks for one/four-port EPC, FastID
and single scans, custom-region bounds, and acknowledged writes with failed
read-back. HTTP tests check exact job lookup and session-token enforcement.
Browser inspection exercised the simulator's four-port FastID reports, Start/Stop,
single-port selection, antenna/power, custom region, profiles and All APIs.
These workflow checks used the simulator. The COM17 observations below describe
the hardware session and subsequent read-only connection check.

Final review also verifies that a native band absent from the guided selector
cannot become band 0 through an empty value. Pyodide inventory tests wait for
the required reports with a bounded timeout instead of assuming all antennas
have completed within a fixed delay.

## Four-port check

On 2026-10-12, a user-identified ZK7180M on COM17/115200 returned model code `0x75`
and firmware `02 08`. The Ex10 V6.8 `ReaderType.ini` calls this code `UHF7182M`,
four ports (`0x71` is `UHF7180M`, one port). All four ports had antennas. Tests used the existing region
and profile, with 27 dBm per port during inventory.

| Check | Observation |
|---|---|
| Answer EPC, ANT1–4 separately | Each port returned tags and terminal status `0x01` |
| Scenario, each port separately | Reports identified only the requested port; Stop restored the original mask |
| Scenario, ANT1–4 | 820 reports across all four ports in a four-second consumer window |
| Scenario with phase, ANT2/ANT4 | 725 reports, all with phase, only from the selected ports |
| FastID, ANT1–4 | 327 reports; 322 included TID; TX order repeated 1, 2, 3, 4 |
| FastID, ANT4/ANT2 | 188 reports; 180 included TID; TX order repeated 4, 2 |
| Antenna masks | Volatile Set/Get matched `1`, `2`, `4`, `8`, `5`, `10`, `15` |
| Per-port power | Volatile Set/Get matched `(26, 25, 24, 23)` dBm, then restored `(27, 27, 27, 27)` |

All stream runs stopped successfully, drained their queues and returned idle,
with no dropped or quarantined reports. The main capture contains 3,833 RX frames
with zero CRC errors, discarded bytes, overflows or unexpected frames. Before/after
snapshots matched for Work Mode, CFG7/8/9/10/11/16/25/29/31, power, antenna mask,
region and profile. No saved settings, region/profile changes or tag writes were
sent; the serial port was closed. These short runs establish host-protocol behavior,
not sustained throughput, RF output accuracy, power-cycle retention or NATION RF equivalence.

The console failure was a form-conversion defect: blank optional `antenna_mask`
and `antenna_sequence` fields became empty strings and failed SDK validation
before TX. Typed controls now produce a number / JSON list or `null`; the backend
also accepts blanks from older forms. The corrected console controller was tested
on COM17 with the original blank payload, all-port Scenario and all-port FastID.
Software regressions cover blank/default selection on one/four ports, explicit
selection, invalid inputs before TX, Stop and restoration. Native SDK runtime and
approved RF mappings were unchanged. Raw captures remain in ignored local files.

A subsequent read-only connection check started with a one-port declaration on
COM17. Automatic discovery read `0x21`, `0x77` and `0x94`, resolved four ports, and
updated SDK capabilities before the UI became ready. A subsequent power Get
returned `(27, 27, 27, 27)`; the current antenna mask was `5`. No configuration or
inventory commands were sent, and the port was closed. Regression tests cover
one/four/eight/sixteen-port layouts, unknown model codes, conflicting or malformed
power responses, rejected/timeout queries, manual selection and active Work Mode.
The browser was then connected to COM17 with the same one-port default: both
guided pages displayed ANT1-4 and all four 27 dBm values were read successfully.
Only read commands were sent; Disconnect released the port.

## Hardware coverage

| Record | Coverage | Limit |
|---|---|---|
| [2026-10-09 session](hardware_live_view_check.md) | One-port Scenario, phase/RSSI display, counters, stop; 7,594 reports | Exact model/firmware and tag population absent from the retained summary |
| Three reported hardware tests, 2026-10-09 | Reader info/power, region/profile, Answer round | Reported screenshots; no published raw capture |
| Scenario follow-up, 2026-10-11 | One port, model code `0x71`, firmware bytes `02 08`; four 2-second S0/S-CST runs, phase output, Stop and configuration read-back | One observed EPC at 5 dBm; private serial captures; no RF scheduler or throughput qualification |
| CFG11 follow-up, 2026-10-11 | Same reader; disabled/active/clear mask reads, one-second S0 and masked S-CST runs, exact CFG restore and Real-time mode read-back | One observed EPC; no tag writes or persistence-through-power-cycle check |
| Range Control follow-up, 2026-10-11 | Same reader; CFG16 100 -> volatile 90 -> restored 100, each read back; CFG25/29 read as 6/5 bytes | Configuration only; no RF performance or power-cycle test |
| Work Mode follow-up, 2026-10-11 | Same reader at 5 dBm; reconnect into autonomous mode, blocked Answer/Scenario, temporary mode switches, Real-time, Answer, S-CST phase and queue drain | One tag; post-Stop antenna `0x62` reproduced and quarantined; no Trigger wiring or power-cycle test |
| Start/Stop and adapter follow-up, 2026-10-12 | One port, model `0x71`, firmware `02 08`, 115200 baud; 51 Scenario phase reports, callback timeout cleanup, overlapping Start/Stop, then Answer | Private serial capture; one observed EPC at 5 dBm; no four-port RF or timing qualification |

The Start/Stop follow-up restored the original Answer mode and confirmed unchanged
CFG7/8/9/10/11/16/25/29/31, power, antenna selection, custom region and RF profile.
All 119 frames passed CRC with no discarded bytes or unexpected frames. The
callback's own timeout propagated after cleanup; the port was closed afterward.

The 2026-10-09 session predates the single-file consolidation. The later follow-up
used CPython and serial; physical Web Serial remains unvalidated.
Historical DLL loopback vectors are documented fixtures, not new RF captures.

The Work Mode follow-up sent only temporary `0x76` values `81/80`. Real-time
delivered 63 valid reports plus one CRC-valid post-ACK report with invalid antenna
`0x62`. Stop returned `partial`, retained that frame, and verified Answer mode;
the malformed frame was not delivered as a tag. Answer then returned one report,
and S-CST returned four phase reports with a complete Stop. All decoded queued
reports were consumed. No parser bytes were discarded or CRC failures observed.
One unowned report during autonomous reconnect was retained as unsolicited data.
CFG7/8/9/10/11/16/25/29/31, reader info, region, profile and working-mode settings
matched the baseline afterward. The port was closed in the original Answer mode.

The follow-up verified unchanged CFG9/10/11, CFG31, region, profile and power after
each Scenario run, then restored the initial Real-time working mode. There were
no CRC failures, discarded bytes or queue drops during the check. Two unsolicited
Real-time reports arrived during the initial mode transition, before Scenario Start.
A private read-only probe of an unsupported CFG returned `0xFF` (`parameter_error`);
the next valid read succeeded. Stop/restore failures were tested synthetically,
not induced on hardware.

The CFG11 follow-up confirmed `00000000` and `01002000` as disabled masks, while
`01002010E280` decoded as an active EPC mask. After clear, `0x77` retained `E280`
in its inactive buffer despite a zero mask length. Both disabled forms now decode
successfully as `None`, with wire bytes preserved. Scenario restored the exact
CFG snapshot, and the original Real-time mode/configuration was read back
successfully. The final run had no CRC failures, discarded bytes or queue drops;
one unsolicited Real-time report arrived before Scenario Start. See
[errata](protocol/errata.md) for the source-backed decoder rules.

The CFG16 check began and ended in Answer mode. CFG8/9/10/11/16/25/29/31,
power, region, profile and the full working-mode response matched their snapshots
after restoration. All 30 response frames parsed without CRC failures, discarded
bytes, unexpected frames or observer errors. CFG25 returned `0F0103020300` and
CFG29 returned `0000000000`; neither was changed. This confirms configuration
read-back on this firmware, not Gen2X inventory or alternate identifier reports.

The final runtime follow-up used COM13 at 115200 baud, one port, model code `0x71`,
firmware `02 08`, and the existing 5 dBm power setting. Custom Region was set to
the existing grid (902750 kHz, 50 channels, 500 kHz spacing), read back as
`FF04320DC65E`, and restored to native band 2, channels 0–49. Inventory was not
started while the custom plan was active. Direct Real-time → Answer switching
was read-back verified; the next S-CST/phase session delivered 3 reports and the
Answer round delivered 1. All configuration snapshots matched after cleanup.
The 70 received frames had no CRC errors, discarded bytes, or buffer overflows;
15 autonomous reports before the transition were retained as unsolicited frames.
No post-ACK tail occurred in this run; regression tests inject that condition.
No persistent setting or tag memory was written, and the port was closed.

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
| `ZK_BAUDRATE` | Serial baud; default 115200 |
| `ZK_ANTENNA_PORTS` | Physical port count; default 1 |
| `ZK_MODEL`, `ZK_FIRMWARE` | Deployment metadata |
| `ZK_TEST_TID` | Known scratch-tag TID, hexadecimal |
| `ZK_ALLOW_TAG_WRITE` | Must be `1` to run the User-memory write test |
| `ZK_USER_WORD_ADDRESS` | Scratch User word; default 0 |

Inventory tests emit RF; Scenario tests temporarily change and restore settings.
The User-memory test needs a writable tag and attempts to restore the old word
only while connection state remains known. It does not retry uncertain writes.
The suite never runs Kill or permanent Lock automatically.
