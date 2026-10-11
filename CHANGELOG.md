# Changelog

## Unreleased

- Add JavaScript/TypeScript integration through Web Serial and Pyodide, with a
  static browser example for inventory, configuration, tracing, and verified EPC writes.
- Preserve native results and errors across the browser bridge; handle fragmented
  RX, stream ownership, USB loss, and explicit recovery.
- Rework integration guides in English, add memory/frame/write diagrams, and
  separate setup, API reference, compatibility, and validation.
- Adopt the MIT license, add package metadata, and check repository and archive
  contents for private files and broken documentation links.
- Translate NATION reference comments and diagnostics; retain its upstream license
  and record the modified-source provenance.

## 0.2.0.dev1 — 2026-10-09

- Consolidate the runtime into `src/zk_rfid.py` for single-file integration.
- Retain 74 reader methods, three properties, async behavior, command formats,
  native results, inventory lifecycle, and trace events.
- Export `SerialTransport` and `NationAdapter` from the top-level module.
- Replace submodule imports with `from zk_rfid import ...`. Pickles with old
  module paths are incompatible.
- Add standalone checks with isolated Python and a wheel containing one SDK module.

## 0.1.0.dev1 — 2026-10-09

- Implement native framing, CRC, parsing, asynchronous dispatch, and recovery.
- Add reader/RF/antenna configuration, buffers, GPIO, and diagnostics.
- Add Answer, TID, FastID, Mix, statistics, Scenario, Real-time, trigger, and heartbeat handling.
- Add normal/extended memory access, EPC/PC helpers, passwords, verification,
  Select, Lock, Kill, BlockWrite, and Erase.
- Add the NATION API adapter, reference driver, examples, capture/replay tools, and
  unit, integration, runtime, and opt-in hardware tests.
- Add the local test console, simulator, typed command forms, trace correlation,
  rotating JSONL logs, and CSV exports.
- Add raw RSSI with the project-defined `raw - 135` estimate and begin/end phase
  conversion using the Ex10 display convention.
- Stream cumulative tag counts independently of logs; preserve selection and
  recover from unavailable live endpoints or stale snapshots.
- Record a limited hardware Scenario/phase session; broader firmware validation
  and RF benchmarking remain open.

## 0.1.0.dev0 — 2026-10-09

- Create the initial SDK structure and pin the NATION reference.
