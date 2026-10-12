# Web controls

The [test console](../tests/demo_app/README.md) offers task-based controls for
inventory, antenna/power and RF settings. **All APIs** keeps the native command
forms, JSON arguments and diagnostics. The console uses CPython over local HTTP;
production browser integrations can use the [Web Serial bridge](../web/README.md).

## Reading

The console detects antenna count on Connect by default. It reads model code
(`0x21`) and Work Mode (`0x77`), then verifies the per-port power payload (`0x94`)
in Answer mode. The result updates both SDK capabilities and all antenna controls.
Four-port capability does not automatically select four antennas.

The Ex10 V6.8 demo resolves model codes through `ReaderType.ini`: `0x71` is
`UHF7180M` with one port; `0x75` is `UHF7182M` with four. The enabled antenna mask
is a selection, not the physical port count. Product labels and USB/COM names do
not override the wire response. The connection summary shows the resolved model
and whether its port count is detected or manual.

Unknown models can use a valid 1/4/8/16-byte power response. Conflicting counts,
malformed replies and failed discovery close the connection instead of assuming
one port. In Real-time/Trigger, a known model table is used without sending a power
query or changing Work Mode. To use a confirmed layout manually, uncheck
**Detect antenna ports automatically**, select **Manual / simulator ports**, and
connect again. This option also sets the simulated hardware layout.

Discovery belongs to the console; native SDK callers still pass
`ReaderCapabilities(antenna_ports=...)`. HTTP connection arguments accept
`detect_ports: true` (default) or `false`; the latter sends no automatic queries.

| UI task | Native operation | Port selection | Ends when |
|---|---|---|---|
| Continuous EPC | `start_inventory(mode=SCENARIO)` | `antenna_mask` | Stop is confirmed |
| EPC + TID / FastID | `start_inventory(mode=ANSWER, config.data=FAST_ID)` | `antenna_sequence` | Stop interrupts the repeating rounds |
| Single scan | `inventory_once(config)` | `config.antenna` | One round completes |

The guided UI builds these arguments; it never sends a Scenario mask to Answer
mode or asks Scenario to produce FastID. Changing tasks retains compatible
Q/Session/Target settings. Single scan reduces the selection to one port.
FastID keeps `tid` optional: an EPC report can arrive without TID.

For example, the native browser bridge reads FastID on four ports with:

```javascript
await reader.startInventory({
  mode: "answer",
  antenna_sequence: [1, 2, 3, 4],
  config: { data: "fastid", q: 4, session: 0, target: 0, scan_time_100ms: 10 }
});
// Consume tag/error events, then stop and inspect the returned outcome.
const outcome = await reader.stopInventory();
```

For Scenario EPC, use `mode: "scenario"`, `config.data: "epc"` and
`antenna_mask: 15`; omit `antenna_sequence`. Mask bit 0 selects ANT1.
The guided FastID sequence uses selected ports in ascending order. Custom ordering,
S-CST, masks and other selectors remain available in All APIs.

Round limit uses 100 ms units: `10` means at most one second per Answer round.
A round can finish earlier. It is not Scenario dwell time or total run duration.
The guided UI uses bounded rounds (`3..255`); full SDK options are in
[Inventory](inventory_modes.md).

## Antenna and power

**Read from reader** loads the enabled-port mask and every port's current power.
Edits remain local until a button is pressed.

| UI action | Native API | Persistence and verification |
|---|---|---|
| Save antenna selection | `set_antennas(mask, persist=True)` | Always saved; verify with `get_antennas()` |
| Apply power | `set_power((p1, p2, ...), persist=...)` | Temporary by default; verify every value with `get_power()` |
| Use reader selection | `get_antennas()` | Copy enabled ports into the run form; no write |

After a verified antenna Save, the run form uses those ports. Its checkboxes may
then choose a temporary subset. Start does not save again; Scenario restores the
pre-run antenna mask after Stop. Power uses a full array matching the declared
port count, including disabled ports. No default power is written on Connect.

Set success and Get failure are different outcomes. Keep the acknowledged write,
show that verification failed, and read again before another write. Do not
automatically retry Set. Stop reading before configuration changes; disable
configuration controls during Start, reading and cleanup.

## RF settings

Reader presets use native band IDs and inclusive channel indices. Custom plans
use the first channel center in kHz, channel count (`1..61`) and spacing in kHz
(a multiple of 125; positive when more than one channel is selected).

- Native plan: `set_region(Region(band, first, last), persist=...)`.
- Custom plan: `set_custom_region(start_frequency_khz, channel_count, spacing_khz, persist=...)`.
- Read either layout with `get_region()` and compare the returned fields.
- Profile: `set_profile(profile_id, persist=...)`, then `get_profile()`.

The last custom center is `first + (count - 1) * spacing`. Values such as spacing
`500` are kHz, not the demo DLL's multiplier `4`. Frequency/profile changes are
temporary unless Save is checked. Bands 21/29 have no verified frequency formula
in the guided selector; use All APIs for their native indices.

These are native ZK controls. When preserving an existing NATION UI, use the
[approved adapter mappings](../mapping/nation_to_zk/web_integration.md) for
baseband and region; do not equate profile IDs with NATION speed codes.
