# Hardware session: 2026-10-09

This record summarizes a limited read-only tag session on a physical one-port
module. It covers Scenario inventory, phase/RSSI display, live counters, and stop.
It does not qualify all SDK operations or a complete model/firmware family.

## Setup

| Parameter | Recorded value |
|---|---|
| SDK version | 0.1.0.dev1, before the single-file consolidation |
| Serial link | COM13, 115200 baud |
| Antenna layout | One port, ANT1 |
| Inventory | Scenario, EPC, Q=4, session=0, phase enabled |
| Model / firmware / tag population | Not identified in the retained summary |

The console used the updated live-stream server after an older process was found
to lack `/api/live`. Personal process IDs and workstation maintenance steps are
kept in local notes.

## Observations

- 7,594 reports and 14 distinct ID/antenna entries by the end of the session.
- Stop completed successfully with `complete=true` and zero dropped reports.
- During an approximately three-second HTTP observation window: 74 updates,
  median interval 40.21 ms, maximum 56.72 ms.
- The same window reported zero SDK queue drops, CRC failures, discarded bytes,
  parser overflows, and unexpected frames.
- UI and CSV exposed RSSI raw/estimated dBm and begin/end phase values.

HTTP update intervals measure delivery to the browser client, not RF acquisition
latency or display frame rate. Distinct ID/antenna entries do not establish the
number of physical tags.

The original JSONL, probe data, CSV, and screenshots are retained privately under
`local_data/` and `artifacts/`. They are not public test fixtures. RSSI remains
the [project-defined estimate](phase_and_live_view.md); no absolute RF calibration,
tag-memory writes, or power-cycle persistence tests were performed in this session.
