# API map

This map covers every public callable and every `MID` constant in the
[pinned NATION Python driver](../../compat/nation/nrn.py). Private implementation
helpers are excluded. It is a migration contract, not a NATION wire emulator.
The [supplied manual/demo review](vendor_reference.md) identifies discrepancies in
that reference, including speed 4 and several command constants. Coverage here is
the pinned Python driver, not the entire GReaderApi DLL. The native targets are documented in the [ZK API index](../../docs/functions_implemented.md).

**Existing** means the optional adapter already implements the listed conversion;
it does not mean signatures, results or RF behavior are identical. **Proposed**
means the native ZK API exists but the application/adapter workflow remains to be
implemented. **Replace** means use the ZK facility, not the NATION byte format.
**Unsupported** means no matching contract is currently available.

## Connection and identity

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `create_reader` | `ZKReader(SerialTransport(...), capabilities=...)` | Replace. Baud 115200; timeout in seconds. Explicit antenna-port layout, no RF configuration on construction. |
| `NRNReader.__init__` | `ZKReader(...)` | Replace. Supply transport/address/capabilities; NATION RS485 PCW flags do not carry over. |
| `NRNReader.set_uart_defaults` | Application connection settings | Proposed. Keep settings per reader rather than mutable class defaults. |
| `NRNReader.get_sdk_info` | `NationAdapter.get_sdk_info()` | Existing. Identifies the ZK SDK and adapter, not NATION firmware. |
| `NRNReader.get_reader_info` | Application connection settings | Proposed. This NATION method returns cached port/baud/timeout/RS485/mask, unlike ZK `get_reader_info()` which queries hardware. |
| `NRNReader.open` | `NationAdapter.open()` | Existing. Async; opening does not apply presets or start RF. Browser uses `connect()`. |
| `NRNReader.close` | `NationAdapter.close()` | Existing. Native cleanup; inspect stop/fault information. Browser uses `disconnect()`. |
| `NRNReader.Connect_Reader_And_Initialize` | Open, inspect `get_working_mode()`, then `get_reader_info()` | Proposed. For host-controlled use, explicitly switch to `WorkingMode.ANSWER` with `persist=False` when needed. Do not blindly send NATION STOP or overwrite saved startup mode. |
| `NRNReader.Query_Reader_Information` | `NationAdapter.Query_Reader_Information()` / native `get_reader_info()` + `get_serial_number()` | Existing adapter returns native reader info only. Proposed UI conversion adds serial via a second call; unsupported uptime/OS/build fields stay absent. Serial is four raw bytes, not a fabricated ASCII identity. |
| `NRNReader.query_rfid_ability` | `NationAdapter.query_rfid_ability()` | Existing, **different semantics**: returns configured `ReaderCapabilities`, not a hardware discovery response. Restrict UI using configured port count and SDK limits; do not claim detected firmware features. |
| `setup_logging` | `zk_rfid.setup_logging()` | Replace. Logging is opt-in; logger-name contract differs. |
| `NRNReader.set_log_level` | Application logger / `setup_logging()` | Proposed. Use native trace events for TX/RX, not a second serial reader. |

## Power and antennas

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `NRNReader.query_reader_power` | `NationAdapter.query_reader_power()` | Existing. `CommandResult.data` contains one-based `{port: dBm}`; do not treat the result object itself as that dictionary. |
| `NRNReader.configure_reader_power` | `NationAdapter.configure_reader_power()` | Existing. Read/merge/write under one operation lock; preserves unmentioned ports. Integers 0–30 dBm. `persistence=False` by default, unlike NATION's `None` reader default. No clipping of unsupported values. |
| `NRNReader.parse_reader_power_response` | `power_dict()` / native `get_power()` | Replace. Do not parse ZK bytes as NATION `(port,power)` pairs. |
| `NRNReader.build_antenna_mask` | `NationAdapter.build_antenna_mask()` | Existing. Bit `port-1`, unique nonempty port list within declared capabilities. |
| `NRNReader.save_antenna_mask` | `NationAdapter.save_antenna_mask()`; browser `service.setAntennas(port_ids)` | Approved configuration policy: always SAVE to reader, then read back. Deliberately differs from the pinned NATION method's host cache. Apply checkbox selection before Start and pass the same selected ports; Start does not save again. |
| `NRNReader.query_enabled_ant_mask` | `NationAdapter.query_enabled_ant_mask()` | Existing native readback; 16-port getter remains restricted. Do not confuse enabled ports with a currently active single-port scan. |
| `NRNReader.enable_ant` | `NationAdapter.enable_ant()` | Read/modify/write and read-back. Approved NATION policy requires `save=True` (default); `False` is rejected. Native ZK APIs still offer volatile configuration. |
| `NRNReader.disable_ant` | `NationAdapter.disable_ant()` | Same SAVE policy as enable. Disabling the last antenna is rejected; use Stop, not a zero mask. |

For four ports, construct the native reader with
`ReaderCapabilities(antenna_ports=4)`. With an open, idle `reader` in Answer mode:

```python
adapter = NationAdapter(reader)
(await adapter.configure_reader_power({2: 18, 4: 20})).require_success()
powers = (await adapter.query_reader_power()).require_success()  # All four ports.
(await adapter.enable_ant(1)).require_success()  # Keep at least one port enabled.
(await adapter.disable_ant(3)).require_success()  # Other mask bits are preserved.
mask = (await adapter.query_enabled_ant_mask()).require_success()
```

Power writes are volatile by default; antenna configuration always uses SAVE.
Power zero means 0 dBm, not port disabled.
Pass selected port IDs at Start, for example
`await adapter.start_inventory_with_mode([1, 3, 4])`. Scenario applies that mask
with one Start and restores the previous mask after confirmed Stop. Declaring
four ports alone does not select all four.

## Inventory

Default migration choice: **Scenario, EPC, Q=4, S0, Target A, ANT1**, with phase
off until requested. Preserve the user's Q/Session/Target instead of resetting
them on each Start. Power, region and RF profile stay unchanged unless configured.

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `NRNReader.start_inventory_with_mode` | `NationAdapter.start_inventory_with_mode()` | Async `InventorySession`, not bool/callback. EPC defaults to Scenario with a port mask. `include_tid=True` uses Answer FastID with an ordered antenna sequence. No saved writes at Start; apply antenna configuration separately. |
| `NRNReader.is_inventory_running` | `NationAdapter.is_inventory_running()` | Existing host-session state. False does not confirm RF stopped; inspect `reader.state` and the Stop outcome. |
| `NRNReader.stop_inventory` | `NationAdapter.stop_inventory()` | Existing. Returns `InventoryOutcome`; await Stop, drain remaining Python events, check `complete` and `outcome`. An unknown reader without a session returns incomplete `stop_unconfirmed` without sending a guessed command. Browser bridge waits for its tag consumer. |
| `NRNReader.build_epc_read_payload` | `InventoryConfig` + Start/`inventory_once()` | Continuous EPC uses Scenario. Approved EPC+TID uses FastID, not TID-only. Answer sends one command per round; multi-port continuous FastID repeats those rounds in selected order. |
| `NRNReader.all_read_end_mids` | `InventoryOutcome` / session completion | Replace. ZK terminal responses have mode-specific semantics. |
| `NRNReader.receive_response` | Await the native operation | Replace. Only the SDK dispatcher reads physical RX. Do not create a competing read loop. |
| `NRNReader.is_idle` | `reader.state` after confirmed Stop/readback | Proposed. Host state is not proof of RF silence after an uncertain exchange; use the documented recovery path, not sleep-and-assume-idle. |
| `NRNReader.set_filter_settings` | Application deduplication and RSSI policy | Unsupported by existing adapter. Proposed host filtering preserves the display/business contract but does not reduce radio traffic or UART bandwidth. No substitution with Range Control or TagFocus. |
| `NRNReader.query_filter_settings` | Application-owned filter state | Proposed. Label host filters as host settings, not device readback. NATION repeat time is in 10 ms units on wire. |

The approved EPC+TID option is **Answer FastID**, selected explicitly with
`include_tid=True` (browser `includeTid: true`). It repeats one round per selected
port using `antenna_sequence`; the default round bound is 20 x 100 ms, not a fixed
port dwell. Stop ends the loop. Compatible tags append a 96-bit TID; other tags can
return EPC with `tid=None`. Keep the TID field optional. This is not NATION's
autonomous stream or a guarantee of TID for every tag. Scenario stays EPC-only
for this migration path; native TID-only and Mix remain separate choices.

Terminal device errors (including antenna error `0xF8`) end the FastID sequence
and raise `DeviceError`; no further antenna round is sent. Python callers must
Stop in `finally` and inspect the partial outcome/status. The browser cleans up
automatically and includes that outcome in its `error` event. Received tags remain
available; a device rejection does not itself fault the serial connection.

For multiple antennas, Scenario sets native antenna selection (`0x3F`), verifies
read-back (`0x21`), then sends one Start (`0x50`). The reader controls switching;
there is no host Start/Stop loop per port. This follows the ZK demo's mask + Start
path. Four-port reports and Stop/restore have been [checked on hardware](../../docs/validation.md#four-port-check);
exact switching order/dwell and RF equivalence to NATION remain unqualified.
No-tag completion is distinct from a transport fault.

Stop waits for an in-progress Start, including its initial Work Mode check. The
browser retains the session outcome after automatic cleanup; a later Stop does
not hide queue loss behind an `already_idle` success.

`run_inventory()` is an adapter-only convenience with sync/async callbacks and a
duration in seconds. Duration expiry returns the Stop outcome. Callback exceptions,
including their own timeouts, propagate after Stop/restore cleanup; cancellation
also waits for cleanup. Check reader state after an exception because cleanup can
fail independently. Use an explicit session and drain when the application must
process every queued tail report after a timed stop.

## Baseband and frequency

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `NRNReader.configure_baseband` | `NationAdapter.configure_baseband()`; browser `service.configureBaseband()` | Approved GReaderTool 0.39 speed map; RF profile write/read-back, then staged Q/Session/Target. Q 0–15, S0–S3, A=0/B=1; Target 2 rejected. Speed 255 keeps current profile, not Auto. |
| `NRNReader.query_baseband_profile` | `NationAdapter.query_baseband_profile()`; browser `service.queryBaseband()` | Native RF profile plus application-owned Q/Session/Target. Explicit `run_settings_source`; no fabricated NATION speed or hardware Target read-back. |
| `NRNReader.select_profile` | `NationAdapter.select_profile(profile_id, mapping=...)` | Existing only with explicit confirmed `RFMapping`. NATION profile IDs 0/1/2 and baseband speed IDs are separate namespaces. The reference's profile command conflicts with the vendor filter query; treat its generic presets as application proposals only. Review-only candidate presets are not auto-enabled. |
| `NRNReader.get_profile` | `NationAdapter.get_profile()` | Existing returns a native ZK ID. It does not reconstruct a unique legacy preset or NATION's dict result. |
| `NRNReader.get_session` | `NationAdapter.get_session()` | Existing returns Scenario CFG9 selector. Extended values are firmware modes, not Gen2 sessions; an Answer run instead uses its own config. |
| `NRNReader.set_rf_band` | `NationAdapter.set_rf_band()`; browser `service.setRfBand()` | Approved complete GReaderTool channel table, native/custom selection and read-back; volatile by default. Unsupported full bands reject before TX. For a selected subset, supply its exact centers via native APIs instead of calling this full-band setter. |
| `NRNReader.query_rf_band` | `NationAdapter.query_rf_band()` | Existing returns native `Region` or `CustomRegion`, not NATION band code/name. Reverse-map only an unambiguous reviewed match; otherwise show native/custom. |
| `NRNReader.query_working_frequency` | `get_region()` / `get_custom_region()` | Proposed. Describe allowed channel centers, not an instantaneous RF measurement. Neither API reproduces an arbitrary sparse NATION channel list or hopping order. Use report frequency when provided for the actual report channel. |

Changing CFG9 before Start is not sufficient: managed Scenario applies its
`InventoryConfig` for the run and restores its snapshot after a confirmed Stop.
Keep pending UI settings in the reader service and pass them at Start. CFG7 timing,
RF profile, region, power and CFG31 are not restored by that session. Saving those
settings and restoring them later are separate policies.

## Tags and results

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `NRNReader.parse_epc` | Native `TagReport`; optional `tag_dict()` | Replace. `tag_dict()` keeps native measurement names and a `native` object; it is not the old callback schema. Browser receives JSON tag events directly. |
| `NRNReader.calculate_rssi` | `TagReport.rssi_dbm` and provenance | Replace. Do not apply the NATION formula to ZK raw bytes. ZK's current project estimate is not a cross-reader calibration. |
| `NRNReader.calculate_frequency` | Report `frequency_khz`; region channel calculation for configured centers | Replace. Do not reuse the NATION helper's hard-coded `920 + index*0.5` MHz formula for other bands. |
| `NRNReader.write_epc_tag` | `write_memory(EPC, word_address=..., ...)` for raw bank writes; `write_epc()` for whole EPC replacement | Proposed. Preserve the meaning of `start_word`; stop first, set/restore antenna selection, use an explicit target and password. Native writes do not automatically retry. |
| `NRNReader.write_epc_tag_auto` | `write_epc()` | Proposed. Native helper reads/preserves non-length PC bits and verifies; the reference rebuilds PC and may pad EPC. Reject unaligned EPC or request explicit padding instead of silently changing identity. |
| `NRNReader.write_epc_to_target_auto` | `NationAdapter.write_epc_to_target_auto()` | Existing, different signature: password default 0, timeout 3 s; no `scan_timeout`, `overwrite_pc`, `prefix_words`, or preliminary scan. Full-EPC target 1–15 words; use native stable TID mask for longer targets. `verify` retained. |
| `NRNReader.check_write_epc` | Native readback/`write_epc(verify=True)` result | Proposed. The pinned implementation returns True after starting inventory; callback return is not a synchronous verification result. Do not preserve this as proof of a successful write. |
| `NRNReader.validate_epc_hex` | `values.hex_epc()` / native byte validation | Replace. Existing conversion is strict, whole 16-bit words, no separators/padding; NATION strips spaces and pads an odd byte count. |
| `NRNReader.calculate_start_word` | Explicit `word_address` for raw writes; `write_epc()` owns PC/EPC layout | Proposed. NATION calculation is `(1 if overwrite_pc else 2) + prefix_words`; do not feed a prebuilt PC into native `write_epc()`. |
| `NRNReader.set_beeper` | `NationAdapter.set_beeper()` / native `set_buzzer()` | Existing partial conversion: 0 disables, 2 enables beep-per-report; 1 rejected. Reference implementation treats 1 as immediate continuous buzz despite the constant name `BEEP_AFTER_INVENTORY`; mode 2 is host event policy, not necessarily every report. |
| `NRNReader.get_beeper` | Application preference | Unsupported by adapter. NATION reads cached state; no native ZK buzzer getter is implemented. |

For the old UI schema, explicitly rename `antenna` to `antenna_id`, convert kHz to
MHz, retain leading EPC zeros, and allow missing fields. Never invent PC, TID or
frequency. Keep begin/end phase separately; selecting one as legacy `phase` is an
application decision. Do not reuse the NATION phase scaling on ZK words. Host
monotonic timestamps are not UTC/device timestamps.

Native results retain `outcome`, `status`, `tag_error`, `confirmation` and `steps`.
Only `success` maps to a legacy success indication; retain partial/unknown details
and do not retry uncertain writes. Configuration ACK is not RF equivalence or
proof of nonvolatile retention. Reverse mappings can be one-to-many; cached UI
choices are not hardware readback after reconnect.

## Transport and protocol utilities

These helpers remain useful only for NATION frames. Move web integration above
the command builder/parser; feeding ZK bytes into the old parser will not work.

| NATION API | ZK route | Status and integration decision |
|---|---|---|
| `UARTConnection.__init__` | `SerialTransport()` / browser Web Serial transport | Replace. No port opens during construction. |
| `UARTConnection.open` | Reader `open()` / browser `connect()` | Replace. Let one SDK own the port lifecycle. |
| `UARTConnection.close` | Reader `close()` / browser `disconnect()` | Replace. Stop and cleanup through the reader. |
| `UARTConnection.send` | Native reader method | Replace. Never send NATION frame bytes to ZK. |
| `UARTConnection.receive` | Native dispatcher and tag events | Replace. No competing RX task. |
| `UARTConnection.send_raw_bytes` | Native reader method | Replace. No public raw NATION passthrough; keep frame builders for offline protocol tooling. |
| `UARTConnection.flush_input` | Native stop/settle/recovery | Replace. Flushing alone discards data and does not resynchronize the device. |
| `UARTConnection.is_open` | Application connection state | Replace. An open port does not imply confirmed reader idle. |
| `NRNReader.send` | Native reader method | Replace. No NATION frame tunnel. |
| `NRNReader.receive` | Native dispatcher and tag events | Replace. No NATION frame tunnel. |
| `NRNReader.crc16_ccitt` | Native `crc16()` for ZK data | Replace, not equivalent CRC conventions. Do not carry the NATION polynomial/header/byte order into ZK. |
| `NRNReader.build_frame` | Native builders / `encode_command()` | Replace. Low-level ZK builders return a Request and do not transmit. |
| `NRNReader.build_pcw` | No PCW in ZK framing | Unsupported. Reader address is a native frame field. |
| `NRNReader.parse_frame` | `decode_response()` / `FrameParser` | Replace. Native results and reports normally remove this need. |
| `NRNReader.extract_valid_frames` | `FrameParser` | Replace. Keep fragmentation/CRC handling inside the native transport path. |
| `MID.all_read_end_mids` | Native session/outcome completion | Replace. Do not compare ZK commands with NATION terminal MID lists. |

Exception families map by meaning: `NextwavesSDKError` to `ZKError`, connection
errors to `TransportError`/exchange failures, malformed frames to `ProtocolError`,
invalid inputs to `ValidationError`, and failed tag operations to their native
`CommandResult`/`OperationError`. Browser exceptions use `ZKSDKError`; a resolved
Promise can still contain a failed command result. Keep the original native detail.

## Commands

All values below are hexadecimal. This is the full named `MID` inventory, including
aliases and constants without Python methods. A shared number is not evidence of
equivalent payloads. Entries describe migration routes, not a wire bridge.

| NATION constant | Value | Native ZK route / decision |
|---|---|---|
| `MID.QUERY_INFO` | 0100 | `get_reader_info()` 21 plus `get_serial_number()` 4C when needed. |
| `MID.CONFIRM_CONNECTION` | 0012 | Proposed native reader-info probe; no direct opcode mapping. |
| `MID.READ_EPC_TAG` | 0210 | Continuous EPC: Scenario 50; stream EE; Stop 51. Bounded mode: Answer API. |
| `MID.PHASE_INVENTORY` | 0214 | Scenario `config.phase=True`, CFG9 + 50; supported report fields only. |
| `MID.STOP_INVENTORY` | 02FF | SDK Stop by mode, not always 93. |
| `MID.STOP_OPERATION` | 00FF | Same host stop intent; NATION alias/context is not a ZK byte. |
| `MID.READ_END` | 1231 | Native terminal outcome/event, no fabricated NATION notification. |
| `MID.WRITE_EPC_TAG` | 0211 | `write_epc()` or explicit EPC-bank `write_memory()` according to payload intent. |
| `MID.ERROR_NOTIFICATION` | 0000 | Native command errors and trace/fault events. |
| `MID.CONFIG_BASEBAND` | 020B | Profile 7F + Scenario CFG9 + application Target. Preserve namespace/dialect. |
| `MID.QUERY_BASEBAND` | 020C | Profile 7F + CFG9, with target provenance and ambiguous reverse mapping. |
| `MID.SESSION` | 0003 | Parameter identifier, not a standalone ZK command; use inventory config. |
| `MID.CONFIGURE_READER_POWER` | 0201 | `set_power()` 2F. |
| `MID.QUERY_READER_POWER` | 0202 | `get_power()` 94. |
| `MID.READER_POWER_CALIBRATION` | 0103 | Unsupported calibration contract; normal power setting is not calibration. |
| `MID.QUERY_POWER_CALIBRATION` | 0104 | Unsupported. |
| `MID.SET_FILTER_SETTINGS` | 0209 | Proposed host filtering; no matching native adapter contract. |
| `MID.QUERY_FILTER_SETTINGS` | 020A | Proposed host-state query; source also uses 020A for profile selection. |
| `MID.SET_RF_BAND` | 0203 | Native/custom region 22. |
| `MID.QUERY_RF_BAND` | 0204 | Native/custom region 9E. |
| `MID.SET_WORKING_FREQUENCY` | 0205 | Proposed channel-plan selection; constant only, no corresponding Python setter. Sparse lists may be unrepresentable. |
| `MID.QUERY_WORKING_FREQUENCY` | 0206 | 9E channel plan; no generic NATION hopping-mode equivalent. |
| `MID.QUERY_RFID_ABILITY` | 1000 | Configured `ReaderCapabilities` plus native info, not an equivalent capability discovery command. |
| `MID.CONFIGURE_ANTENNA_ENABLE` | 0203 | Proposed antenna 3F; conflicts numerically with RF band. Confirm caller payload, not just name/value. |
| `MID.QUERY_ANTENNA_ENABLE` | 0202 | Native antenna readback via reader info 21; NATION value also means Get Power. |
| `MID.BUZZER_SWITCH` | 011E | Partial mapping to native buzzer 40; no duration/continuous-buzz equivalence. |
| `MID.CONFIGURE_GPO` | 0109 | Proposed `set_gpio(output1, output2)` 46; preserve the other output and map numbering/electrical levels. No NATION Python method. |
| `MID.QUERY_GPI` | 010A | Proposed `get_gpio()` 47; ZK model has input1 and two outputs. |
| `MID.CONFIGURE_GPI_TRIGGER` | 010B | No generic trigger-condition/action mapping. Optional ZK trigger Work Mode is a separate workflow, not the default inventory replacement. |
| `MID.QUERY_GPI_TRIGGER` | 010C | No equivalent trigger rule getter; Work Mode 77 describes only ZK's mode/config. |

The supplied manual/demo confirms that 020A is Get Tag Upload Settings, not
profile selection; its RFID capability query uses MID00 with the host-command
flags, while 1000 sets the notification bit. Its antenna
command list uses MID07/08, while the reference aliases band/power commands.
MID14 is reserved in that manual, so the named phase constant is not verified.
See [source notes](vendor_reference.md) before using any legacy command value.

The reference contains conflicting opcode comments/aliases and a target-write
helper that calls Start with an unsupported `mode` keyword. Preserve the reference
as evidence; do not copy these defects into the ZK API or silently repair the
reference as part of this migration. Newer vendor SDKs or web dialects may differ;
add them as explicitly versioned mappings after inspecting actual call sites.
