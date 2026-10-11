# RSSI and phase

Reports preserve wire values alongside converted fields. Keep the raw values and
frequency when comparing readers, developing phase algorithms, or calibrating a
measurement setup.

## RSSI

The reader supplies an unsigned byte. This SDK uses the project-defined estimate:

```text
rssi_dbm = rssi_raw - 135
```

| Raw | Estimated dBm |
|---:|---:|
| 60 | -75 |
| 85 | -50 |
| 100 | -35 |
| 110 | -25 |

This mapping uses reference points 60 → -75 dBm and 110 → -25 dBm. It is not a
vendor calibration or a verified conversion to absolute received power.
Values outside 60–110 are extrapolated without clamping.

`TagReport` exposes `rssi_raw`, `rssi_dbm`, `rssi_source`, and
`rssi_in_calibration_range`. The source string remains
`user_linear_raw_minus_135` for API compatibility. The range flag only indicates
whether the raw value lies between the two reference points; it does not certify
calibration.

All native report decoders use the same mapping. Manually constructing a
`TagReport` does not calculate measurement fields automatically; call
`rssi_to_dbm(raw)` when needed.

## Phase

The extension contains two unsigned big-endian 16-bit values: begin and end.
The SDK follows the normal inventory display convention in Ex10 V6.8:

```text
degrees = (raw × 0.087) mod 180
radians = degrees × pi / 180
```

```python
from zk_rfid import phase_to_degrees, phase_to_radians

phase_to_degrees(0x018F)              # 34.713 degrees
phase_to_radians(0x018F)              # approximately 0.605856 radians
phase_to_degrees(0x0E8F)              # 144.249 degrees
phase_to_degrees(0x0E8F, wrap=False)  # 324.249 degrees, without folding
```

| Fields | Meaning |
|---|---|
| `phase_raw` | Original four bytes |
| `phase_begin_raw`, `phase_end_raw` | Unsigned 16-bit integers |
| `phase_begin_degrees`, `phase_end_degrees` | Scaled and folded angles |
| `phase_begin_radians`, `phase_end_radians` | Corresponding radians |
| `phase_conversion` | `ex10_v6_8_demo_0.087deg_mod180` |
| `frequency_khz` | Reported RF frequency, when present |

Missing values remain `None`; zero phase is valid. The older singular
`phase_radians` field remains `None` because neither begin nor end is selected
implicitly.

The source manual describes four phase bytes on printed p.17 and begin/end words
on p.48. Ex10 V6.8 `RWDev.cs` decodes the words big-endian;
`Form1.cs` uses the formula above in its normal display path, while one FastID
branch omits folding. Raw fields and `wrap=False` preserve that distinction.
Vendor source is retained privately and is not a runtime dependency.

These angles are a display convention, not calibrated absolute phase. Folding at
180 degrees removes branch information. Validate the convention on your firmware
before using it for motion estimation, ranging, or multipath analysis; do not
substitute a different phase scale based on another reader family.

## Live display

The Python test console streams cumulative tag counts through `/api/live` using
NDJSON. Display updates are coalesced at roughly 33 ms and drawn with
`requestAnimationFrame`. RX, logging, and UI rendering are separate; an increment
larger than one can simply mean several reports arrived between redraws.

A slow or reconnected browser receives the current totals. The console retains up
to 5,000 ID/antenna entries for export and displays the first 1,000. SDK queue loss,
parser loss, and log drops have separate counters. Pausing the log view does not
stop inventory.

If live streaming is unavailable, the UI falls back to snapshots at approximately
750 ms plus HTTP time. After code updates, stop and disconnect, restart the Python
server, then reload the browser. See [console setup](../tests/demo_app/README.md)
and the [recorded hardware session](hardware_live_view_check.md).
