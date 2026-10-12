# Reuse the web UI

Keep screens, tag tables and business rules. Add a `zk` backend to the existing
reader service and use the [native browser bridge](../../web/README.md) underneath.
Keep the NATION backend and configure its antenna Set command to SAVE as well.
Its pinned `save_antenna_mask()` only caches a value; it is not a hardware Set.

See [Web controls](../../docs/web_controls.md) for the console's task selector,
antenna checkboxes, power fields and the corresponding native API arguments.

```text
Existing UI -> Reader service -> NATION SDK -> N701
                             -> ZK bridge  -> ZKReader -> ZK7182
```

This SDK does not emulate NATION wire frames. If the old web calls
`MessageBuilder.make()` and parses UART bytes itself, replace those calls at the
reader-service boundary. The old codec/read loop must not continue owning the ZK
port. If the web already calls high-level methods, preserve those method names in
its service and implement them with the [API map](api_map.md).

## Start and Stop

The [service example](../../examples/nation_web_service.js) shows the main path:
one Scenario Start, tag events, confirmed Stop. It accepts an already connected
native reader, applies RF settings only on explicit configuration calls, and maps
selected port IDs to a Scenario mask. It is an
integration example, not a complete replacement for `NRNWebSerial`.

```javascript
import { createZKReader } from "./web/zk-rfid-webserial.js";
import { createNationInventoryService } from "./examples/nation_web_service.js";

const native = createZKReader({ baudRate: 115200, antennaPorts: 1 });
const service = createNationInventoryService(native, tag => updateTagTable(tag));

// Call connect from the user's button click; it owns the Web Serial picker.
connectButton.onclick = () => native.connect();
setAntennasButton.onclick = () => service.setAntennas([1]); // SAVE and read-back.
startButton.onclick = () => service.startInventory([1], { q: 4, session: 0, target: 0 });
stopButton.onclick = () => service.stopInventory();
```

Handle rejected promises in the real UI and show their native result/diagnostics.
Check Work Mode before enabling Start. If the application takes over an autonomous
reader, explicitly apply `set_working_mode` with `mode: 0, persist: false`, check
the result, then Start. Do not change the saved boot mode in Connect.

The UI should transition Starting -> Running only after Start succeeds, and
Stopping -> Idle only after Stop is complete and successful. Keep the tag listener
active while Stop drains the final reports. Disable new Start/configuration while
Stop is pending. Stop/disconnect before page navigation; closing a tab cannot
guarantee an RF stop. An unknown outcome requires recovery, not an automatic retry.
After a lost Start ACK, Stop can return `unknown`/`stop_unconfirmed` even without
an active host session. Keep the UI in a fault state until recovery completes.
Stop during Starting waits for Start and then stops it. If the browser consumer
fails, its `error` event includes `inventory_outcome` after cleanup; a later Stop
returns that outcome, including dropped reports or restoration errors.

For bounded inventory use `inventoryOnce()`. For the existing continuous EPC
button use `startInventory({mode: "scenario", config})`; do not add Answer polling
or select autonomous Real-time simply because the screen says "real time".
For the approved EPC+TID option, call
`service.startInventory(selectedPorts, { includeTid: true })`. It selects native
Answer FastID and repeats rounds over all selected ports in order. Tags without
FastID support can return EPC with `tid: null`; do not fabricate a TID or discard
the EPC. The default round bound is 20 x 100 ms; `scan_time_100ms` can change it.
Multi-port rounds must be bounded. Target A/B alternation remains unsupported.

FastID antenna/device errors stop the sequence; the browser emits `error` after
cleanup, with the native status in `event.detail.inventory_outcome`. Keep received
tags, show the error, and require an explicit restart after resolving it. A later
Stop retains that failed run outcome, even when the reader is already idle.

## Four-port readers

Declare `antennaPorts: 4` at connection setup; the default is one port. The same
service can select any of ports 1–4. For example, with an idle reader in Answer mode:

```javascript
const native = createZKReader({ baudRate: 115200, antennaPorts: 4 });
const service = createNationInventoryService(native, tag => updateTagTable(tag));
await native.connect(); // Run from a user gesture.
function requireSuccess(result) {
  if (result.outcome !== "success") throw Object.assign(new Error("Reader command failed"), { result });
  return result.data;
}

requireSuccess(await native.setPower([18, 19, 20, 21], false)); // ANT1, ANT2, ANT3, ANT4; dBm.
const powers = requireSuccess(await native.getPower());
await service.setAntennas([1, 3, 4]); // Disable ANT2; always SAVE, then read back.
const mask = requireSuccess(await service.getAntennas());
await service.startInventory([1, 3, 4]); // One Start, selected ports; ANT2 stays excluded.
// Later, from the Stop button:
await service.stopInventory(); // Saved selection stays 0b1101; Start/Stop do not save again.
```

Power arrays contain all four values; a scalar applies to every port. For a UI
editing one port, serialize the entire Get/merge/Set sequence in the reader service
to preserve other ports. The Python adapter already locks that sequence; see
[power and antennas](api_map.md#power-and-antennas). Antenna masks use bit `port-1`;
any individual port can be disabled while another remains enabled. Zero power is
0 dBm, not disabled. A zero antenna mask is rejected; use Stop to stop inventory.

Scenario applies exactly the requested port list, even if a port was disabled in
the pre-run mask. Apply checkbox changes with Set/SAVE before Start, then pass
the same selection. Disable Start while there are unapplied checkbox edits.
On reconnect, populate checkboxes from `getAntennas()`. Native callers can pass
`startInventory({mode: "scenario", antenna_mask: 0b1101, config})`; the mask
overrides `config.antenna`. Stop restores the pre-run selection. Changes to power
or masks require stopping first. The reader controls switching after one Start;
exact switching order/dwell remains firmware-controlled. Four-port EPC/FastID,
selected masks and Stop/restore have been [checked on hardware](../../docs/validation.md#four-port-check).

## Settings

Store the user's pending Q/Session/Target/phase in the service and pass them at
Start. Calling CFG9 Set followed by a Start with default config will not preserve
the intended run settings. A CFG9 getter describes Scenario settings; it does not
read the application's Target or every possible inventory mode.

The adapter and service use approved **GReaderTool 0.39** mappings from
[rf_choices.json](rf_choices.json); speed 4 selects ZK profile 123 (Miller2).
Serve that JSON alongside the example, preserving its relative URL, or pass a
loaded object as the optional third argument `{ policy }`. The native bridge
remains independent of this mapping layer. With an idle connected reader:

```javascript
await service.configureBaseband({ speed: 4, q: 6, session: 1, target: 0 });
const baseband = await service.queryBaseband(); // Profile from device; Q/Session/Target from service.
await service.setRfBand(6); // Full TW table: 922250 kHz, 12 channels, 500 kHz; read-back checked.
await service.startInventory([1, 3, 4]); // Uses the staged Q/Session/Target; no RF preset writes.
```

Power/baseband/region remain volatile unless explicitly saved. Antenna Set always
saves. A read-back confirms current configuration, not retention across a power
cycle. Do not allow concurrent configuration/Start operations in the UI.

The region setter applies a **complete band table**. When the UI has selected a
subset of channels, resolve those actual centers and call native APIs with that
exact plan. A sparse list must not become a min/max range. For a native plan:

```javascript
// Example shape only: select reviewed values for the deployment before calling.
const result = await native.call("set_region", {
  region: { band: 2, min_channel: 0, max_channel: 49 }, persist: false,
});
if (result.outcome !== "success") throw Object.assign(new Error("Set region failed"), { result });
const actual = await native.call("get_region");
if (actual.outcome !== "success" || actual.data.band !== 2 ||
    actual.data.min_channel !== 0 || actual.data.max_channel !== 49) {
  throw Object.assign(new Error("Region read-back mismatch"), { result: actual });
}
```

For a custom uniform grid, call `setCustomRegion({start_frequency_khz,
channel_count, spacing_khz}, persist)` and `getCustomRegion()`; see the complete
[custom-region example](../../web/README.md#custom-region). The spacing is kHz,
not the demo multiplier. Native/custom getters return actual configuration, not
a legacy band hint.

The generic `call()` accepts native `ZKReader` names only. For example,
`call("get_power")` works and `call("query_reader_power")` does not. The optional
Python `NationAdapter` is separate and is not automatically available to JS.
Both the Python adapter and JS service read the same policy JSON. Generic P0/P1/P2
profile presets remain unapproved; `select_profile()` still needs explicit evidence.

## Reports and results

| Existing field | Mapping |
|---|---|
| `epc`, `tid` | Native uppercase hex; preserve leading zeros and missing data |
| `antenna_id` | Native one-based `antenna` |
| `rssi` | Native `rssi_dbm` plus retained provenance; never reapply NATION scaling |
| `frequency` | `frequency_khz / 1000`, or missing |
| `pc` | Missing unless obtained by a separate supported operation |
| `phase` | No default singular value; expose native begin/end values with units |

The example retains the original tag under `native` for phase, raw measurements,
timestamp source and diagnostics. If the old UI assumes every tag has EPC/PC or
a numeric RSSI, make those fields optional before enabling TID-only modes. Keep
report count separate from unique-tag count and from throttled DOM refreshes.

Promises can resolve with a native `failure`, `partial` or `unknown` outcome.
Preserve the result and show an appropriate error. Do not map any ACK or resolved
promise to unconditional success, particularly for writes and Stop restoration.

If Set succeeds but its verification Get fails, the service rejects with
`error.result.steps = [written, actual]`. The write may already be saved. A rejected
Get produces `partial`; an uncertain Get or unstructured exception produces
`unknown`. The original exception remains in `error.cause` when present. Keep the
UI unverified until a successful read-back; do not restore old checkbox values or
automatically retry Set. Failed baseband verification leaves staged Q/Session/Target
unchanged even though the reader may have accepted the new RF profile.

## Additional ZK features

Add a separate advanced panel for S-CST profile slots, phase, Range Control and
other supported native settings after the legacy workflow is validated. Capability
flags should describe the tested reader/firmware/transport, not merely the E710
chip name. Leave unresolved S-PRO/S-RPT/S-CTP algorithms out of legacy mappings.

Review connection, no-tag reading, Start/Stop/restart, partial settings, unplug,
timeouts, write verification and native/custom region readback before rollout.
Compare RF results separately; software tests do not establish N701/ZK equivalence.
