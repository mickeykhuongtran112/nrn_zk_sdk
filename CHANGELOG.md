# Changelog

## Unreleased

- End repeating Answer/FastID sessions on terminal device errors, including antenna
  error 0xF8. Preserve queued tags and the error status through Stop and browser cleanup.
- Retain acknowledged Set results when browser configuration read-back fails or
  throws; report partial/unknown verification without retrying saved writes.
- Apply approved GReaderTool 0.39 speed and full-region mappings in the optional
  adapter and browser service, with read-back; keep generic profile presets gated.
- Use saved antenna configuration for the NATION UI, with explicit Set/read-back
  and no repeated saved writes at Start. Native volatile APIs remain available.
- Map EPC+TID to Answer FastID. Add native `antenna_sequence` for ordered repeating
  Answer rounds across selected ports; incompatible tags may report EPC only.
- Serialize Start/Stop/close so Stop during Start's Work Mode check cannot leave
  a new stream running. Preserve cancellation-safe cleanup.
- Retain browser session outcomes after automatic Stop, including queue loss,
  final reports and restoration failures; emit the resulting state and outcome.
- Add Scenario `antenna_mask` through the native SDK, browser bridge and NATION
  adapter. Selected ports share one native Start, with mask read-back and restoration.
- Keep Stop incomplete when the reader is unknown and no session remains; do not
  report idle after a lost Start ACK or a failed Stop.
- Propagate `NationAdapter.run_inventory()` callback timeouts after Stop/restore;
  only expiry of the requested run duration is normal completion.
- Cover four-port selection, mask restoration, individual power updates and
  enable/disable operations in regressions and integration examples. RF mapping
  choices are unchanged. Four-port hardware validation is pending.

- Reconcile NATION mapping proposals with the supplied protocol and GReaderTool
  0.39: separate speed-code dialects, preserve exact demo channel lists, and mark
  unrepresentable plans and reference-command conflicts. Runtime is unchanged.

- Move NATION value conversions and the optional async adapter to
  `mapping/nation_to_zk`; native ZK operations and adapter behavior are unchanged.
  Import adapter types from `mapping.nation_to_zk` instead of `zk_rfid`.
- Add a complete pinned-reference API/command map, browser migration guide and
  review-only RF choices. These proposals do not change active adapter mappings.

- Set all connection defaults to 115200 baud; other supported rates remain selectable.
- Settle and verify direct transitions to Answer before accepting another session.
  Finalize failed Answer interrupts so queued reports remain drainable.
- Add Custom Region set/get, typed native/custom region reads, and Web Serial methods.
  Channel plans remain application-owned; writes default to volatile.

- Check Work Mode before Answer/Scenario inventory and reject incompatible
  autonomous modes before scan commands or Scenario configuration writes.
- Add `persist` to Work Mode setters, defaulting to `False`. Managed Real-time
  Start/Stop uses temporary changes; use `persist=True` to change boot behavior.
- Settle Stop boundaries, retain bounded post-ACK diagnostics, and verify
  Real-time returns to Answer. Add `InventorySession.drain()` and preserve queued
  reports when timed consumers are cancelled.
- Keep Answer/Scenario as the main paths; document optional autonomous/trigger
  reading with a separate Real-time example.

- Add CFG16 Range Control get/set with native 0-100 validation, volatile writes
  by default, raw response preservation, and operator-provided wire regressions.
- Document Impinj Scan/ScanID options, configuration support, and RF limits.
- Decode zero-length CFG11 masks as `None`, including all-zero responses; retain
  raw bytes and strict validation of active masks and outgoing commands.
- Ignore retained mask-buffer bytes in Real-time `0x77` responses when the mask
  length is zero; active-mask padding checks remain unchanged.
- Add optional `ScenarioSession` names for existing CFG9 values; integer inputs
  and inventory behavior are unchanged.
- Explain region/channel selection, RF profiles, Scenario configuration ownership,
  and S-CST limits; add diagrams and a standalone Scenario CLI example.
- Show phase/frequency and cleanup diagnostics in the Scenario example; return
  a failing exit status for incomplete sessions.
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
