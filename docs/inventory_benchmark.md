# RF benchmarking

No comparative RF benchmark is published yet. Use this procedure to measure
application performance without confusing reader reports, distinct IDs, and
physical tag coverage.

## Setup

Record reader model and firmware, antenna layout and dwell, region/frequency,
power, RF profile, Q/session/target, TagFocus/FastID, data type and length, baud,
filter/report policy, tag chips, known tag population, position, orientation,
and nearby materials.

Compare modes with equivalent settings. Separate RF acquisition, UART throughput,
host scheduling, parser behavior, and UI update rate. Manage tag inventoried state
between runs so one mode does not inherit an advantage.

## Measurements

| Metric | Purpose |
|---|---|
| Correct IDs / ground-truth IDs within the time window | Identification completeness |
| Unexpected IDs | Stray reads outside the intended zone |
| First-read and last-required-tag latency | Responsiveness and time to completion |
| EPC + TID coverage | Completeness when both identifiers are required |
| Repeated runs and tag arrangements | Repeatability |
| Queue depth, drops, CPU, memory, UART rate | Host and transport limits |

Report distributions across repeated trials rather than a single best result.
A quiet interval is only a stopping heuristic. An expected count cannot replace
matching the actual IDs, and duplicated EPCs prevent physical-tag counting by EPC
alone.

## Application cases

| Case | Starting point for evaluation |
|---|---|
| Dense inventory | Scenario EPC; compare session/target settings and repeated reads |
| Checkout surface | Bounded reads, stray-read control, items added or removed |
| Walk-through identification | Latency, body shadowing, duplicate events, zone boundary |
| Enclosed read chamber | Antenna/profile schedule and known-list reconciliation |
| Conveyor / tunnel | Sensor or encoder window; available time ≈ effective zone length / speed |

These are measurement scenarios. Business decisions and event reconciliation
belong in the application, outside the SDK.
