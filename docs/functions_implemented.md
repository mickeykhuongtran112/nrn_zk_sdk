# API index

Use `ZKReader` for device I/O. See [Python API](api.md) for results and lifecycle,
[compatibility](supported_devices.md) for deployment limits, and [examples](../examples/README.md) for common tasks.

Generated from source with `python tools/export_symbols.py`; edit source docstrings to update descriptions.

## ZKReader

| Method / property | Purpose | Source |
|---|---|---|
| `ZKReader.state` | Host lifecycle state; IDLE alone does not prove a saved real-time mode is off. | [src/zk_rfid.py:3107](../src/zk_rfid.py#L3107) |
| `ZKReader.address` | Current wire address; changes only after an acknowledged address update. | [src/zk_rfid.py:3121](../src/zk_rfid.py#L3121) |
| `ZKReader.is_inventory_running` | Whether this host owns an active or transitioning inventory session. | [src/zk_rfid.py:3126](../src/zk_rfid.py#L3126) |
| `ZKReader.get_capabilities` | Return declared capabilities and their evidence; no hardware probing. | [src/zk_rfid.py:3130](../src/zk_rfid.py#L3130) |
| `ZKReader.open` | Open transport and start the single RX task; recover requires a known clean boundary. | [src/zk_rfid.py:3169](../src/zk_rfid.py#L3169) |
| `ZKReader.close` | Stop owned inventory, close transport and join background tasks. | [src/zk_rfid.py:3178](../src/zk_rfid.py#L3178) |
| `ZKReader.get_reader_info` | Read native reader identity, RF configuration and antenna-check state (0x21). | [src/zk_rfid.py:3286](../src/zk_rfid.py#L3286) |
| `ZKReader.get_serial_number` | Read the four-byte reader serial number (0x4C). | [src/zk_rfid.py:3294](../src/zk_rfid.py#L3294) |
| `ZKReader.get_power` | Read one integer dBm value per declared antenna (0x94). | [src/zk_rfid.py:3298](../src/zk_rfid.py#L3298) |
| `ZKReader.set_power` | Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F). | [src/zk_rfid.py:3302](../src/zk_rfid.py#L3302) |
| `ZKReader.get_write_power` | Read the separate write-power enable flag and dBm value (0x7A). | [src/zk_rfid.py:3310](../src/zk_rfid.py#L3310) |
| `ZKReader.set_write_power` | Set separate write power in dBm, or None to disable it (0x79). | [src/zk_rfid.py:3314](../src/zk_rfid.py#L3314) |
| `ZKReader.get_write_retries` | Read the reader's write-retry count, 0..7 (0x7B). | [src/zk_rfid.py:3318](../src/zk_rfid.py#L3318) |
| `ZKReader.set_write_retries` | Set the module retry count 0..7; the host never retries writes (0x7B). | [src/zk_rfid.py:3322](../src/zk_rfid.py#L3322) |
| `ZKReader.set_antennas` | Select antenna mask with bit0=port1; volatile unless persist=True (0x3F). | [src/zk_rfid.py:3326](../src/zk_rfid.py#L3326) |
| `ZKReader.get_antennas` | Get the native antenna mask; the 16-port getter remains unverified. | [src/zk_rfid.py:3332](../src/zk_rfid.py#L3332) |
| `ZKReader.set_antenna_check` | Enable or disable the reader's antenna connection check (0x66). | [src/zk_rfid.py:3339](../src/zk_rfid.py#L3339) |
| `ZKReader.get_antenna_check` | Read the antenna-check flag from reader information (0x21). | [src/zk_rfid.py:3343](../src/zk_rfid.py#L3343) |
| `ZKReader.set_address` | Change reader address after receiving the ACK at the original address (0x24). | [src/zk_rfid.py:3348](../src/zk_rfid.py#L3348) |
| `ZKReader.set_baudrate` | Receive ACK at the old baud, then switch the transport baud (0x28). | [src/zk_rfid.py:3357](../src/zk_rfid.py#L3357) |
| `ZKReader.set_inventory_time` | Set native scan time in 100 ms units: 0 or 3..255 (0x25). | [src/zk_rfid.py:3377](../src/zk_rfid.py#L3377) |
| `ZKReader.set_interface` | Select usb or uart (0x6A); effective after a module power cycle. | [src/zk_rfid.py:3381](../src/zk_rfid.py#L3381) |
| `ZKReader.get_region` | Read the native band ID and minimum/maximum channel indices (0x9E). | [src/zk_rfid.py:3385](../src/zk_rfid.py#L3385) |
| `ZKReader.set_region` | Set native region and channel indices; no NATION region-ID conversion (0x22). | [src/zk_rfid.py:3389](../src/zk_rfid.py#L3389) |
| `ZKReader.get_profile` | Read native RF profile ID, including the 16-bit Ex10 format (0x7F). | [src/zk_rfid.py:3395](../src/zk_rfid.py#L3395) |
| `ZKReader.set_profile` | Set native RF profile ID; no inferred equivalence with NATION profiles (0x7F). | [src/zk_rfid.py:3399](../src/zk_rfid.py#L3399) |
| `ZKReader.get_drm` | Read whether dense-reader mode is enabled (0x90). | [src/zk_rfid.py:3405](../src/zk_rfid.py#L3405) |
| `ZKReader.set_drm` | Enable or disable dense-reader mode (0x90). | [src/zk_rfid.py:3409](../src/zk_rfid.py#L3409) |
| `ZKReader.set_buzzer` | Enable or disable the reader's tag-read buzzer (0x40). | [src/zk_rfid.py:3413](../src/zk_rfid.py#L3413) |
| `ZKReader.pulse_indicator` | Pulse LED/buzzer using 50 ms active/silent units (0x33). | [src/zk_rfid.py:3417](../src/zk_rfid.py#L3417) |
| `ZKReader.get_gpio` | Read input and output bits in the documented GPIO layout (0x47). | [src/zk_rfid.py:3423](../src/zk_rfid.py#L3423) |
| `ZKReader.set_gpio` | Set the two documented GPO outputs (0x46). | [src/zk_rfid.py:3428](../src/zk_rfid.py#L3428) |
| `ZKReader.get_temperature` | Read signed integer Celsius using the native sign byte (0x92). | [src/zk_rfid.py:3433](../src/zk_rfid.py#L3433) |
| `ZKReader.measure_return_loss` | Measure return loss at a documented grid frequency in kHz (0x91). | [src/zk_rfid.py:3438](../src/zk_rfid.py#L3438) |
| `ZKReader.get_return_loss_threshold` | Read the antenna return-loss threshold in dB (0x6E). | [src/zk_rfid.py:3444](../src/zk_rfid.py#L3444) |
| `ZKReader.set_return_loss_threshold` | Set the antenna return-loss threshold to 0..20 dB (0x6E). | [src/zk_rfid.py:3448](../src/zk_rfid.py#L3448) |
| `ZKReader.get_config` | Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB). | [src/zk_rfid.py:3452](../src/zk_rfid.py#L3452) |
| `ZKReader.set_config` | Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA). | [src/zk_rfid.py:3461](../src/zk_rfid.py#L3461) |
| `ZKReader.get_scan_parameters` | Read scan interval, antenna dwell, and count (CFG7). | [src/zk_rfid.py:3477](../src/zk_rfid.py#L3477) |
| `ZKReader.set_scan_parameters` | Set scan interval in 10 ms units, dwell in 100 ms units, and count (CFG7). | [src/zk_rfid.py:3481](../src/zk_rfid.py#L3481) |
| `ZKReader.get_tag_focus` | Read the TagFocus enable flag (CFG8). | [src/zk_rfid.py:3487](../src/zk_rfid.py#L3487) |
| `ZKReader.set_tag_focus` | Enable or disable TagFocus for compatible tags (CFG8). | [src/zk_rfid.py:3491](../src/zk_rfid.py#L3491) |
| `ZKReader.get_query_parameters` | Read Q, session, and phase settings for Scenario inventory (CFG9). | [src/zk_rfid.py:3495](../src/zk_rfid.py#L3495) |
| `ZKReader.set_query_parameters` | Set Q, session, and phase for Scenario inventory (CFG9). | [src/zk_rfid.py:3499](../src/zk_rfid.py#L3499) |
| `ZKReader.get_tid_parameters` | Read the Scenario TID word address and count (CFG10). | [src/zk_rfid.py:3505](../src/zk_rfid.py#L3505) |
| `ZKReader.set_tid_parameters` | Set Scenario TID selection; word_count=0 selects EPC instead (CFG10). | [src/zk_rfid.py:3509](../src/zk_rfid.py#L3509) |
| `ZKReader.get_inventory_mask` | Read the bank, bit address, length, and data of the inventory mask (CFG11). | [src/zk_rfid.py:3515](../src/zk_rfid.py#L3515) |
| `ZKReader.set_inventory_mask` | Set the inventory selection mask, or pass None to clear it (CFG11). | [src/zk_rfid.py:3519](../src/zk_rfid.py#L3519) |
| `ZKReader.get_custom_profiles` | Read the three custom RF profile IDs (CFG31). | [src/zk_rfid.py:3526](../src/zk_rfid.py#L3526) |
| `ZKReader.set_custom_profiles` | Set three native 16-bit RF profile IDs (CFG31). | [src/zk_rfid.py:3530](../src/zk_rfid.py#L3530) |
| `ZKReader.set_real_time_config` | Persist the dedicated 0x75 real-time settings; separate from Scenario CFG. | [src/zk_rfid.py:3536](../src/zk_rfid.py#L3536) |
| `ZKReader.get_working_mode` | Read the 0x77 mode and fixed-width saved real-time configuration. | [src/zk_rfid.py:3541](../src/zk_rfid.py#L3541) |
| `ZKReader.set_working_mode` | Persistent mode setting. For managed 0xEE delivery use start_inventory(). | [src/zk_rfid.py:3548](../src/zk_rfid.py#L3548) |
| `ZKReader.get_heartbeat_interval` | Read the heartbeat interval in 30 s units; zero means disabled (0x78). | [src/zk_rfid.py:3557](../src/zk_rfid.py#L3557) |
| `ZKReader.set_heartbeat_interval` | Set heartbeat interval in 30 second units, with 0 disabling it (0x78). | [src/zk_rfid.py:3561](../src/zk_rfid.py#L3561) |
| `ZKReader.get_buffer_length` | Read the maximum stored ID length, 16 or 62 bytes (0x71). | [src/zk_rfid.py:3565](../src/zk_rfid.py#L3565) |
| `ZKReader.set_buffer_length` | Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70). | [src/zk_rfid.py:3569](../src/zk_rfid.py#L3569) |
| `ZKReader.get_buffer_count` | Read the number of tag records in the reader buffer (0x74). | [src/zk_rfid.py:3573](../src/zk_rfid.py#L3573) |
| `ZKReader.clear_buffer` | Clear the reader tag buffer (0x73). | [src/zk_rfid.py:3577](../src/zk_rfid.py#L3577) |
| `ZKReader.inventory_to_buffer` | Run buffered inventory and return counts; this changes reader buffer contents (0x18). | [src/zk_rfid.py:3581](../src/zk_rfid.py#L3581) |
| `ZKReader.read_buffer` | Collect all 0x72 frames; preserve partial reports and enforce one overall deadline. | [src/zk_rfid.py:3591](../src/zk_rfid.py#L3591) |
| `ZKReader.inventory_once` | Run one Answer/Mix round, preserving reports on partial completion or timeout. | [src/zk_rfid.py:3598](../src/zk_rfid.py#L3598) |
| `ZKReader.inventory_single` | Run native single-tag inventory (0x0F). | [src/zk_rfid.py:3607](../src/zk_rfid.py#L3607) |
| `ZKReader.inventory_matching_epc` | Run native EPC-bit-match inventory with explicit bit offset and length (0x1A). | [src/zk_rfid.py:3614](../src/zk_rfid.py#L3614) |
| `ZKReader.start_inventory` | Start a managed async report iterator; stop explicitly or use its context manager. | [src/zk_rfid.py:3630](../src/zk_rfid.py#L3630) |
| `ZKReader.stop_inventory` | Stop by mode-specific semantics; 0x93 has no ACK of its own. | [src/zk_rfid.py:3644](../src/zk_rfid.py#L3644) |
| `ZKReader.read_memory` | Read 1..120 16-bit words; choose extended address format automatically when needed. | [src/zk_rfid.py:3658](../src/zk_rfid.py#L3658) |
| `ZKReader.write_memory` | Write 1..32 words once, optionally verify using a stable post-write target. | [src/zk_rfid.py:3697](../src/zk_rfid.py#L3697) |
| `ZKReader.write_epc` | Read PC, preserve non-length bits, then one targeted PC+EPC write. | [src/zk_rfid.py:3778](../src/zk_rfid.py#L3778) |
| `ZKReader.write_epc_single` | Native 0x04. Requires exactly one tag physically in the RF field. | [src/zk_rfid.py:3848](../src/zk_rfid.py#L3848) |
| `ZKReader.set_access_password` | Write the 32-bit Access password, then verify using the new password if requested. | [src/zk_rfid.py:3854](../src/zk_rfid.py#L3854) |
| `ZKReader.set_kill_password` | Write the 32-bit Kill password; does not execute Kill or Lock. | [src/zk_rfid.py:3874](../src/zk_rfid.py#L3874) |
| `ZKReader.lock_tag` | Apply native Gen2 protection to a specified target; permanent states are irreversible. | [src/zk_rfid.py:3893](../src/zk_rfid.py#L3893) |
| `ZKReader.kill_tag` | Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password. | [src/zk_rfid.py:3906](../src/zk_rfid.py#L3906) |
| `ZKReader.block_write` | Use native BlockWrite within its independent frame budget; tag support is required. | [src/zk_rfid.py:3910](../src/zk_rfid.py#L3910) |
| `ZKReader.block_erase` | Erase 1..120 words using native BlockErase; tag support is required. | [src/zk_rfid.py:3926](../src/zk_rfid.py#L3926) |
| `ZKReader.select_tag` | Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask. | [src/zk_rfid.py:3942](../src/zk_rfid.py#L3942) |

<details>
<summary>Method signatures</summary>

```text
ZKReader.state(self) -> ReaderState
ZKReader.address(self) -> int
ZKReader.is_inventory_running(self) -> bool
ZKReader.get_capabilities(self) -> ReaderCapabilities
async ZKReader.open(self, *, recover: bool=False) -> 'ZKReader'
async ZKReader.close(self) -> None
async ZKReader.get_reader_info(self) -> CommandResult[ReaderInfo]
async ZKReader.get_serial_number(self) -> CommandResult[bytes]
async ZKReader.get_power(self) -> CommandResult[tuple[int, ...]]
async ZKReader.set_power(self, power_dbm: int | tuple[int, ...], *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_write_power(self) -> CommandResult[WritePower]
async ZKReader.set_write_power(self, power_dbm: int | None) -> CommandResult[None]
async ZKReader.get_write_retries(self) -> CommandResult[int]
async ZKReader.set_write_retries(self, count: int) -> CommandResult[int]
async ZKReader.set_antennas(self, mask: int, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_antennas(self) -> CommandResult[int]
async ZKReader.set_antenna_check(self, enabled: bool) -> CommandResult[None]
async ZKReader.get_antenna_check(self) -> CommandResult[bool]
async ZKReader.set_address(self, address: int) -> CommandResult[None]
async ZKReader.set_baudrate(self, baudrate: int) -> CommandResult[None]
async ZKReader.set_inventory_time(self, scan_time_100ms: int) -> CommandResult[None]
async ZKReader.set_interface(self, interface: str) -> CommandResult[None]
async ZKReader.get_region(self) -> CommandResult[Region]
async ZKReader.set_region(self, region: Region, *, persist: bool=False, legacy: bool=False) -> CommandResult[None]
async ZKReader.get_profile(self, *, extended_format: bool=True) -> CommandResult[int]
async ZKReader.set_profile(self, profile_id: int, *, persist: bool=False, extended_format: bool=True) -> CommandResult[int]
async ZKReader.get_drm(self) -> CommandResult[bool]
async ZKReader.set_drm(self, enabled: bool) -> CommandResult[bool]
async ZKReader.set_buzzer(self, enabled: bool) -> CommandResult[None]
async ZKReader.pulse_indicator(self, active_50ms: int, silent_50ms: int, count: int) -> CommandResult[None]
async ZKReader.get_gpio(self) -> CommandResult[GPIOState]
async ZKReader.set_gpio(self, output1: bool, output2: bool) -> CommandResult[None]
async ZKReader.get_temperature(self) -> CommandResult[int]
async ZKReader.measure_return_loss(self, frequency_khz: int, antenna: int=1) -> CommandResult[int]
async ZKReader.get_return_loss_threshold(self) -> CommandResult[int]
async ZKReader.set_return_loss_threshold(self, threshold_db: int) -> CommandResult[int]
async ZKReader.get_config(self, number: int, *, decoded: bool=True) -> CommandResult[ScanParameters | QueryParameters | TIDParameters | TagMask | tuple[int, ...] | bool | bytes]
async ZKReader.set_config(self, number: int, data: bytes, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_scan_parameters(self) -> CommandResult[ScanParameters]
async ZKReader.set_scan_parameters(self, parameters: ScanParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_tag_focus(self) -> CommandResult[bool]
async ZKReader.set_tag_focus(self, enabled: bool, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_query_parameters(self) -> CommandResult[QueryParameters]
async ZKReader.set_query_parameters(self, parameters: QueryParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_tid_parameters(self) -> CommandResult[TIDParameters]
async ZKReader.set_tid_parameters(self, parameters: TIDParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_inventory_mask(self) -> CommandResult[TagMask]
async ZKReader.set_inventory_mask(self, mask: TagMask | None, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_custom_profiles(self) -> CommandResult[tuple[int, ...]]
async ZKReader.set_custom_profiles(self, profile_ids: tuple[int, int, int], *, persist: bool=False) -> CommandResult[None]
async ZKReader.set_real_time_config(self, config: RealTimeConfig) -> CommandResult[None]
async ZKReader.get_working_mode(self) -> CommandResult[WorkingModeConfig]
async ZKReader.set_working_mode(self, mode: WorkingMode) -> CommandResult[None]
async ZKReader.get_heartbeat_interval(self) -> CommandResult[int]
async ZKReader.set_heartbeat_interval(self, interval_30s: int) -> CommandResult[int]
async ZKReader.get_buffer_length(self) -> CommandResult[int]
async ZKReader.set_buffer_length(self, max_bytes: int) -> CommandResult[None]
async ZKReader.get_buffer_count(self) -> CommandResult[int]
async ZKReader.clear_buffer(self) -> CommandResult[None]
async ZKReader.inventory_to_buffer(self, config: InventoryConfig=InventoryConfig(), *, timeout: float | None=None) -> CommandResult[BufferCounts]
async ZKReader.read_buffer(self, *, data_kind: InventoryData=InventoryData.EPC, timeout: float | None=None) -> InventoryOutcome
async ZKReader.inventory_once(self, config: InventoryConfig=InventoryConfig(), *, timeout: float | None=None) -> InventoryOutcome
async ZKReader.inventory_single(self, *, timeout: float | None=None) -> InventoryOutcome
async ZKReader.inventory_matching_epc(self, data: bytes, bit_length: int, *, bit_offset: int=0, exclude: bool=False, timeout: float | None=None) -> InventoryOutcome
async ZKReader.start_inventory(self, mode: InventoryMode=InventoryMode.SCENARIO, *, config: InventoryConfig=InventoryConfig(), queue_size: int=1024, trigger: bool=False) -> InventorySession
async ZKReader.stop_inventory(self) -> InventoryOutcome
async ZKReader.read_memory(self, bank: MemoryBank, word_address: int, word_count: int, *, target: TagTarget | None=None, access_password: bytes=ZERO_PASSWORD, extended_format: bool | None=None) -> CommandResult[bytes]
async ZKReader.write_memory(self, bank: MemoryBank, word_address: int, data: bytes, *, target: TagTarget | None=None, access_password: bytes=ZERO_PASSWORD, extended_format: bool | None=None, verify: bool=False, verification_target: TagTarget | None=None, verification_password: bytes | None=None, timeout: float | None=None) -> CommandResult[bytes | None]
async ZKReader.write_epc(self, epc: bytes, *, target: TagTarget, access_password: bytes=ZERO_PASSWORD, verify: bool=True, verification_target: TagTarget | None=None, timeout: float | None=None) -> CommandResult[bytes | None]
async ZKReader.write_epc_single(self, epc: bytes, *, access_password: bytes=ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.set_access_password(self, new_password: bytes, *, target: TagTarget, access_password: bytes=ZERO_PASSWORD, verify: bool=True) -> CommandResult[bytes | None]
async ZKReader.set_kill_password(self, new_password: bytes, *, target: TagTarget, access_password: bytes=ZERO_PASSWORD, verify: bool=True) -> CommandResult[bytes | None]
async ZKReader.lock_tag(self, lock_target: int, protection: int, *, target: TagTarget, access_password: bytes=ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.kill_tag(self, kill_password: bytes, *, target: TagTarget) -> CommandResult[None]
async ZKReader.block_write(self, bank: MemoryBank, word_address: int, data: bytes, *, target: TagTarget | None=None, access_password: bytes=ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.block_erase(self, bank: MemoryBank, word_address: int, word_count: int, *, target: TagTarget | None=None, access_password: bytes=ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.select_tag(self, mask: TagMask, *, antenna_mask: int=1, select_target: int=4, action: int=0, truncate: bool=False) -> CommandResult[None]
```

</details>

## Supporting symbols

Types, transport interfaces, command builders, decoders, and adapter methods.
Module-level command builders return `Request` values without device I/O.
Hardware coverage is recorded in [validation](validation.md).

<details>
<summary>All source symbols</summary>


### src/zk_rfid.py

- **constant** [`SDK_NAME`](../src/zk_rfid.py#L37)
- **constant** [`SDK_VERSION`](../src/zk_rfid.py#L38)
- **function** [`setup_logging`](../src/zk_rfid.py#L41)
- **class** [`ZKError`](../src/zk_rfid.py#L59)
- **class** [`ValidationError`](../src/zk_rfid.py#L63)
- **class** [`ProtocolError`](../src/zk_rfid.py#L67)
- **class** [`UnsupportedFeature`](../src/zk_rfid.py#L71)
- **class** [`UnverifiedFeature`](../src/zk_rfid.py#L75)
- **class** [`StateError`](../src/zk_rfid.py#L79)
- **class** [`TransportError`](../src/zk_rfid.py#L83)
- **class** [`ExchangeError`](../src/zk_rfid.py#L87)
- **class** [`RequestTimeout`](../src/zk_rfid.py#L96)
- **class** [`QueueOverflow`](../src/zk_rfid.py#L100)
- **class** [`DeviceError`](../src/zk_rfid.py#L104)
- **class** [`OperationError`](../src/zk_rfid.py#L113)
- **constant** [`T`](../src/zk_rfid.py#L128)
- **function** [`integer`](../src/zk_rfid.py#L131)
- **function** [`boolean`](../src/zk_rfid.py#L137)
- **function** [`octets`](../src/zk_rfid.py#L143)
- **class** [`MemoryBank`](../src/zk_rfid.py#L149)
- **constant** [`MemoryBank.RESERVED`](../src/zk_rfid.py#L150)
- **constant** [`MemoryBank.EPC`](../src/zk_rfid.py#L151)
- **constant** [`MemoryBank.TID`](../src/zk_rfid.py#L152)
- **constant** [`MemoryBank.USER`](../src/zk_rfid.py#L153)
- **class** [`Outcome`](../src/zk_rfid.py#L156)
- **constant** [`Outcome.SUCCESS`](../src/zk_rfid.py#L157)
- **constant** [`Outcome.FAILURE`](../src/zk_rfid.py#L158)
- **constant** [`Outcome.PARTIAL`](../src/zk_rfid.py#L159)
- **constant** [`Outcome.UNKNOWN`](../src/zk_rfid.py#L160)
- **class** [`Confirmation`](../src/zk_rfid.py#L163)
- **constant** [`Confirmation.NONE`](../src/zk_rfid.py#L164)
- **constant** [`Confirmation.TRANSMITTED`](../src/zk_rfid.py#L165)
- **constant** [`Confirmation.ACKNOWLEDGED`](../src/zk_rfid.py#L166)
- **constant** [`Confirmation.READ_BACK`](../src/zk_rfid.py#L167)
- **class** [`ReaderState`](../src/zk_rfid.py#L170)
- **constant** [`ReaderState.DISCONNECTED`](../src/zk_rfid.py#L171)
- **constant** [`ReaderState.IDLE`](../src/zk_rfid.py#L172)
- **constant** [`ReaderState.STARTING`](../src/zk_rfid.py#L173)
- **constant** [`ReaderState.INVENTORYING`](../src/zk_rfid.py#L174)
- **constant** [`ReaderState.STOPPING`](../src/zk_rfid.py#L175)
- **constant** [`ReaderState.UNKNOWN`](../src/zk_rfid.py#L176)
- **class** [`InventoryMode`](../src/zk_rfid.py#L179)
- **constant** [`InventoryMode.ANSWER`](../src/zk_rfid.py#L180)
- **constant** [`InventoryMode.SCENARIO`](../src/zk_rfid.py#L181)
- **constant** [`InventoryMode.REAL_TIME`](../src/zk_rfid.py#L182)
- **class** [`InventoryData`](../src/zk_rfid.py#L185)
- **constant** [`InventoryData.EPC`](../src/zk_rfid.py#L186)
- **constant** [`InventoryData.TID`](../src/zk_rfid.py#L187)
- **constant** [`InventoryData.FAST_ID`](../src/zk_rfid.py#L188)
- **constant** [`InventoryData.MIX`](../src/zk_rfid.py#L189)
- **class** [`WorkingMode`](../src/zk_rfid.py#L192)
- **constant** [`WorkingMode.ANSWER`](../src/zk_rfid.py#L193)
- **constant** [`WorkingMode.REAL_TIME`](../src/zk_rfid.py#L194)
- **constant** [`WorkingMode.TRIGGER`](../src/zk_rfid.py#L195)
- **class** [`LockTarget`](../src/zk_rfid.py#L198)
- **constant** [`LockTarget.KILL_PASSWORD`](../src/zk_rfid.py#L199)
- **constant** [`LockTarget.ACCESS_PASSWORD`](../src/zk_rfid.py#L200)
- **constant** [`LockTarget.EPC`](../src/zk_rfid.py#L201)
- **constant** [`LockTarget.TID`](../src/zk_rfid.py#L202)
- **constant** [`LockTarget.USER`](../src/zk_rfid.py#L203)
- **class** [`LockProtection`](../src/zk_rfid.py#L206)
- **constant** [`LockProtection.UNLOCK`](../src/zk_rfid.py#L207)
- **constant** [`LockProtection.PERMANENT_UNLOCK`](../src/zk_rfid.py#L208)
- **constant** [`LockProtection.PASSWORD`](../src/zk_rfid.py#L209)
- **constant** [`LockProtection.PERMANENT_LOCK`](../src/zk_rfid.py#L210)
- **class** [`TagMask`](../src/zk_rfid.py#L214)
- **method** [`TagMask.encode`](../src/zk_rfid.py#L231)
- **class** [`TagTarget`](../src/zk_rfid.py#L241)
- **class** [`CommandResult`](../src/zk_rfid.py#L259)
- **property** [`CommandResult.ok`](../src/zk_rfid.py#L272)
- **method** [`CommandResult.require_success`](../src/zk_rfid.py#L275)
- **class** [`ReaderInfo`](../src/zk_rfid.py#L282)
- **class** [`InventoryConfig`](../src/zk_rfid.py#L297)
- **class** [`TagReport`](../src/zk_rfid.py#L317)
- **class** [`InventoryStatistics`](../src/zk_rfid.py#L350)
- **class** [`Heartbeat`](../src/zk_rfid.py#L357)
- **class** [`InventoryOutcome`](../src/zk_rfid.py#L364)
- **property** [`InventoryOutcome.unique_count`](../src/zk_rfid.py#L376)
- **class** [`Region`](../src/zk_rfid.py#L381)
- **class** [`GPIOState`](../src/zk_rfid.py#L388)
- **class** [`RealTimeConfig`](../src/zk_rfid.py#L396)
- **class** [`WorkingModeConfig`](../src/zk_rfid.py#L408)
- **class** [`BufferCounts`](../src/zk_rfid.py#L414)
- **class** [`WritePower`](../src/zk_rfid.py#L420)
- **class** [`QueryParameters`](../src/zk_rfid.py#L426)
- **class** [`ScanParameters`](../src/zk_rfid.py#L433)
- **class** [`TIDParameters`](../src/zk_rfid.py#L440)
- **class** [`ParserDiagnostics`](../src/zk_rfid.py#L446)
- **class** [`ReaderCapabilities`](../src/zk_rfid.py#L462)
- **method** [`ReaderCapabilities.require`](../src/zk_rfid.py#L495)
- **constant** [`PHASE_CONVERSION`](../src/zk_rfid.py#L509)
- **constant** [`RSSI_SOURCE`](../src/zk_rfid.py#L510)
- **function** [`rssi_to_dbm`](../src/zk_rfid.py#L513)
- **function** [`phase_to_degrees`](../src/zk_rfid.py#L535)
- **function** [`phase_to_radians`](../src/zk_rfid.py#L550)
- **class** [`TraceEvent`](../src/zk_rfid.py#L563)
- **class** [`TraceEmitter`](../src/zk_rfid.py#L577)
- **method** [`TraceEmitter.emit`](../src/zk_rfid.py#L586)
- **class** [`RFProfile`](../src/zk_rfid.py#L618)
- **constant** [`PROFILES`](../src/zk_rfid.py#L628)
- **function** [`get_profile_definition`](../src/zk_rfid.py#L686)
- **constant** [`CRC16_INIT`](../src/zk_rfid.py#L702)
- **constant** [`CRC16_POLY`](../src/zk_rfid.py#L703)
- **constant** [`MAX_COMMAND_DATA`](../src/zk_rfid.py#L704)
- **constant** [`MAX_RESPONSE_DATA`](../src/zk_rfid.py#L705)
- **constant** [`BROADCAST_ADDRESS`](../src/zk_rfid.py#L706)
- **class** [`Command`](../src/zk_rfid.py#L709)
- **constant** [`Command.INVENTORY`](../src/zk_rfid.py#L710)
- **constant** [`Command.READ_MEMORY`](../src/zk_rfid.py#L711)
- **constant** [`Command.WRITE_MEMORY`](../src/zk_rfid.py#L712)
- **constant** [`Command.WRITE_EPC`](../src/zk_rfid.py#L713)
- **constant** [`Command.KILL`](../src/zk_rfid.py#L714)
- **constant** [`Command.LOCK`](../src/zk_rfid.py#L715)
- **constant** [`Command.BLOCK_ERASE`](../src/zk_rfid.py#L716)
- **constant** [`Command.SINGLE_INVENTORY`](../src/zk_rfid.py#L717)
- **constant** [`Command.BLOCK_WRITE`](../src/zk_rfid.py#L718)
- **constant** [`Command.READ_MEMORY_EXTENDED`](../src/zk_rfid.py#L719)
- **constant** [`Command.WRITE_MEMORY_EXTENDED`](../src/zk_rfid.py#L720)
- **constant** [`Command.BUFFER_INVENTORY`](../src/zk_rfid.py#L721)
- **constant** [`Command.MIX_INVENTORY`](../src/zk_rfid.py#L722)
- **constant** [`Command.INVENTORY_EPC`](../src/zk_rfid.py#L723)
- **constant** [`Command.READER_INFO`](../src/zk_rfid.py#L724)
- **constant** [`Command.SET_REGION`](../src/zk_rfid.py#L725)
- **constant** [`Command.SET_ADDRESS`](../src/zk_rfid.py#L726)
- **constant** [`Command.SET_SCAN_TIME`](../src/zk_rfid.py#L727)
- **constant** [`Command.SET_BAUDRATE`](../src/zk_rfid.py#L728)
- **constant** [`Command.SET_POWER`](../src/zk_rfid.py#L729)
- **constant** [`Command.INDICATOR`](../src/zk_rfid.py#L730)
- **constant** [`Command.SET_ANTENNAS`](../src/zk_rfid.py#L731)
- **constant** [`Command.SET_BUZZER`](../src/zk_rfid.py#L732)
- **constant** [`Command.SET_GPIO`](../src/zk_rfid.py#L733)
- **constant** [`Command.GET_GPIO`](../src/zk_rfid.py#L734)
- **constant** [`Command.SERIAL_NUMBER`](../src/zk_rfid.py#L735)
- **constant** [`Command.FAST_START`](../src/zk_rfid.py#L736)
- **constant** [`Command.FAST_STOP`](../src/zk_rfid.py#L737)
- **constant** [`Command.SET_ANTENNA_CHECK`](../src/zk_rfid.py#L738)
- **constant** [`Command.SET_INTERFACE`](../src/zk_rfid.py#L739)
- **constant** [`Command.RETURN_LOSS_THRESHOLD`](../src/zk_rfid.py#L740)
- **constant** [`Command.SET_BUFFER_LENGTH`](../src/zk_rfid.py#L741)
- **constant** [`Command.GET_BUFFER_LENGTH`](../src/zk_rfid.py#L742)
- **constant** [`Command.READ_BUFFER`](../src/zk_rfid.py#L743)
- **constant** [`Command.CLEAR_BUFFER`](../src/zk_rfid.py#L744)
- **constant** [`Command.BUFFER_COUNT`](../src/zk_rfid.py#L745)
- **constant** [`Command.SET_REAL_TIME`](../src/zk_rfid.py#L746)
- **constant** [`Command.SET_WORKING_MODE`](../src/zk_rfid.py#L747)
- **constant** [`Command.GET_WORKING_MODE`](../src/zk_rfid.py#L748)
- **constant** [`Command.HEARTBEAT`](../src/zk_rfid.py#L749)
- **constant** [`Command.SET_WRITE_POWER`](../src/zk_rfid.py#L750)
- **constant** [`Command.GET_WRITE_POWER`](../src/zk_rfid.py#L751)
- **constant** [`Command.WRITE_RETRIES`](../src/zk_rfid.py#L752)
- **constant** [`Command.PROFILE`](../src/zk_rfid.py#L753)
- **constant** [`Command.DRM`](../src/zk_rfid.py#L754)
- **constant** [`Command.RETURN_LOSS`](../src/zk_rfid.py#L755)
- **constant** [`Command.TEMPERATURE`](../src/zk_rfid.py#L756)
- **constant** [`Command.STOP_INVENTORY`](../src/zk_rfid.py#L757)
- **constant** [`Command.GET_POWER`](../src/zk_rfid.py#L758)
- **constant** [`Command.SELECT`](../src/zk_rfid.py#L759)
- **constant** [`Command.GET_REGION`](../src/zk_rfid.py#L760)
- **constant** [`Command.SET_CONFIG`](../src/zk_rfid.py#L761)
- **constant** [`Command.GET_CONFIG`](../src/zk_rfid.py#L762)
- **constant** [`Command.TAG_REPORT`](../src/zk_rfid.py#L763)
- **class** [`ConfigID`](../src/zk_rfid.py#L766)
- **constant** [`ConfigID.SCAN`](../src/zk_rfid.py#L767)
- **constant** [`ConfigID.TAG_FOCUS`](../src/zk_rfid.py#L768)
- **constant** [`ConfigID.QUERY`](../src/zk_rfid.py#L769)
- **constant** [`ConfigID.TID`](../src/zk_rfid.py#L770)
- **constant** [`ConfigID.MASK`](../src/zk_rfid.py#L771)
- **constant** [`ConfigID.IMPINJ_SCAN`](../src/zk_rfid.py#L772)
- **constant** [`ConfigID.IMPINJ_SCAN_ID`](../src/zk_rfid.py#L773)
- **constant** [`ConfigID.CUSTOM_PROFILES`](../src/zk_rfid.py#L774)
- **function** [`crc16`](../src/zk_rfid.py#L784)
- **function** [`append_crc`](../src/zk_rfid.py#L793)
- **class** [`ResponseFrame`](../src/zk_rfid.py#L805)
- **function** [`encode_command`](../src/zk_rfid.py#L813)
- **function** [`decode_response`](../src/zk_rfid.py#L820)
- **class** [`FrameParser`](../src/zk_rfid.py#L835)
- **method** [`FrameParser.reset`](../src/zk_rfid.py#L841)
- **method** [`FrameParser.feed`](../src/zk_rfid.py#L844)
- **constant** [`STATUS_NAMES`](../src/zk_rfid.py#L891)
- **class** [`StatusInfo`](../src/zk_rfid.py#L920)
- **function** [`interpret_status`](../src/zk_rfid.py#L928)
- **class** [`AsyncTransport`](../src/zk_rfid.py#L953) — **transport interface contract**
- **method** [`AsyncTransport.open`](../src/zk_rfid.py#L954) — **transport interface contract**
- **method** [`AsyncTransport.close`](../src/zk_rfid.py#L955) — **transport interface contract**
- **method** [`AsyncTransport.read`](../src/zk_rfid.py#L956) — **transport interface contract**
- **method** [`AsyncTransport.write`](../src/zk_rfid.py#L957) — **transport interface contract**
- **class** [`SerialTransport`](../src/zk_rfid.py#L969)
- **method** [`SerialTransport.open`](../src/zk_rfid.py#L980)
- **method** [`SerialTransport.read`](../src/zk_rfid.py#L1015)
- **method** [`SerialTransport.write`](../src/zk_rfid.py#L1029)
- **method** [`SerialTransport.set_baudrate`](../src/zk_rfid.py#L1037)
- **method** [`SerialTransport.close`](../src/zk_rfid.py#L1043)
- **function** [`raw`](../src/zk_rfid.py#L1064)
- **function** [`exact`](../src/zk_rfid.py#L1068)
- **function** [`ack`](../src/zk_rfid.py#L1074)
- **function** [`u8`](../src/zk_rfid.py#L1078)
- **function** [`u16`](../src/zk_rfid.py#L1082)
- **function** [`switch`](../src/zk_rfid.py#L1086)
- **class** [`Request`](../src/zk_rfid.py#L1094)
- **function** [`decode_reader_info`](../src/zk_rfid.py#L1111)
- **function** [`get_reader_info`](../src/zk_rfid.py#L1130)
- **function** [`get_serial_number`](../src/zk_rfid.py#L1134)
- **constant** [`BAUD_CODES`](../src/zk_rfid.py#L1145)
- **constant** [`PAUSE_CODES`](../src/zk_rfid.py#L1146)
- **function** [`set_address`](../src/zk_rfid.py#L1149)
- **function** [`set_scan_time`](../src/zk_rfid.py#L1153)
- **function** [`set_baudrate`](../src/zk_rfid.py#L1160)
- **function** [`set_interface`](../src/zk_rfid.py#L1167)
- **function** [`set_working_mode`](../src/zk_rfid.py#L1173)
- **function** [`encode_real_time`](../src/zk_rfid.py#L1177)
- **function** [`set_real_time`](../src/zk_rfid.py#L1199)
- **function** [`decode_working_mode`](../src/zk_rfid.py#L1203)
- **function** [`get_working_mode`](../src/zk_rfid.py#L1229)
- **function** [`heartbeat`](../src/zk_rfid.py#L1233)
- **function** [`set_power`](../src/zk_rfid.py#L1252)
- **function** [`get_power`](../src/zk_rfid.py#L1261)
- **function** [`set_write_power`](../src/zk_rfid.py#L1271)
- **function** [`decode_write_power`](../src/zk_rfid.py#L1276)
- **function** [`get_write_power`](../src/zk_rfid.py#L1283)
- **function** [`write_retries`](../src/zk_rfid.py#L1287)
- **function** [`set_antennas`](../src/zk_rfid.py#L1306)
- **function** [`set_antenna_check`](../src/zk_rfid.py#L1317)
- **function** [`decode_antenna`](../src/zk_rfid.py#L1321)
- **constant** [`REGIONS`](../src/zk_rfid.py#L1343)
- **constant** [`BAND_MAX`](../src/zk_rfid.py#L1372)
- **function** [`validate_region`](../src/zk_rfid.py#L1375)
- **function** [`channel_frequency_khz`](../src/zk_rfid.py#L1384)
- **function** [`set_region`](../src/zk_rfid.py#L1392)
- **function** [`decode_region`](../src/zk_rfid.py#L1410)
- **function** [`get_region`](../src/zk_rfid.py#L1418)
- **function** [`profile`](../src/zk_rfid.py#L1422)
- **function** [`drm`](../src/zk_rfid.py#L1435)
- **constant** [`SCENARIO_SESSIONS`](../src/zk_rfid.py#L1447)
- **function** [`encode_scan`](../src/zk_rfid.py#L1450)
- **function** [`encode_query`](../src/zk_rfid.py#L1458)
- **function** [`encode_tid`](../src/zk_rfid.py#L1466)
- **function** [`encode_profiles`](../src/zk_rfid.py#L1475)
- **function** [`decode_mask`](../src/zk_rfid.py#L1481)
- **function** [`decode_config`](../src/zk_rfid.py#L1490)
- **function** [`get_config`](../src/zk_rfid.py#L1518)
- **function** [`set_config`](../src/zk_rfid.py#L1525)
- **constant** [`ZERO_PASSWORD`](../src/zk_rfid.py#L1557)
- **function** [`password`](../src/zk_rfid.py#L1560)
- **function** [`selection`](../src/zk_rfid.py#L1564)
- **function** [`validate_access`](../src/zk_rfid.py#L1574)
- **function** [`read_memory`](../src/zk_rfid.py#L1582)
- **function** [`write_memory`](../src/zk_rfid.py#L1602)
- **function** [`block_erase`](../src/zk_rfid.py#L1631)
- **function** [`write_epc_single`](../src/zk_rfid.py#L1646)
- **function** [`lock_tag`](../src/zk_rfid.py#L1654)
- **function** [`kill_tag`](../src/zk_rfid.py#L1671)
- **function** [`select_tag`](../src/zk_rfid.py#L1681)
- **function** [`pc_with_epc_length`](../src/zk_rfid.py#L1694)
- **constant** [`VENDOR_TAG_COMMANDS`](../src/zk_rfid.py#L1714) — **unsupported by design**
- **function** [`require_vendor_feature`](../src/zk_rfid.py#L1722) — **unsupported by design**
- **function** [`validate_inventory`](../src/zk_rfid.py#L1735)
- **function** [`build_inventory`](../src/zk_rfid.py#L1771)
- **function** [`inventory_epc`](../src/zk_rfid.py#L1794)
- **function** [`fast_start`](../src/zk_rfid.py#L1809)
- **function** [`fast_stop`](../src/zk_rfid.py#L1813)
- **function** [`decode_statistics`](../src/zk_rfid.py#L1817)
- **function** [`decode_answer`](../src/zk_rfid.py#L1851)
- **class** [`MixDecoder`](../src/zk_rfid.py#L1889)
- **method** [`MixDecoder.feed`](../src/zk_rfid.py#L1898)
- **method** [`MixDecoder.flush`](../src/zk_rfid.py#L1947)
- **function** [`decode_stream`](../src/zk_rfid.py#L1956)
- **function** [`decode_heartbeat`](../src/zk_rfid.py#L1986)
- **function** [`set_buffer_length`](../src/zk_rfid.py#L2002)
- **function** [`get_buffer_length`](../src/zk_rfid.py#L2008)
- **function** [`clear_buffer`](../src/zk_rfid.py#L2018)
- **function** [`get_buffer_count`](../src/zk_rfid.py#L2022)
- **function** [`decode_counts`](../src/zk_rfid.py#L2026)
- **function** [`decode_buffer`](../src/zk_rfid.py#L2031)
- **function** [`set_buzzer`](../src/zk_rfid.py#L2079)
- **function** [`indicator`](../src/zk_rfid.py#L2083)
- **function** [`set_gpio`](../src/zk_rfid.py#L2098)
- **function** [`decode_gpio`](../src/zk_rfid.py#L2103)
- **function** [`get_gpio`](../src/zk_rfid.py#L2110)
- **function** [`decode_temperature`](../src/zk_rfid.py#L2121)
- **function** [`get_temperature`](../src/zk_rfid.py#L2128)
- **function** [`measure_return_loss`](../src/zk_rfid.py#L2132)
- **function** [`return_loss_threshold`](../src/zk_rfid.py#L2140)
- **class** [`Dispatcher`](../src/zk_rfid.py#L2170)
- **property** [`Dispatcher.pending_command`](../src/zk_rfid.py#L2197)
- **method** [`Dispatcher.open`](../src/zk_rfid.py#L2200)
- **method** [`Dispatcher.close`](../src/zk_rfid.py#L2220)
- **method** [`Dispatcher.exchange`](../src/zk_rfid.py#L2275)
- **method** [`Dispatcher.interrupt_answer`](../src/zk_rfid.py#L2380)
- **function** [`collect_answer`](../src/zk_rfid.py#L2526)
- **function** [`collect_buffer`](../src/zk_rfid.py#L2652)
- **class** [`InventorySession`](../src/zk_rfid.py#L2706)
- **method** [`InventorySession.start`](../src/zk_rfid.py#L2761)
- **method** [`InventorySession.stop`](../src/zk_rfid.py#L2988)
- **class** [`ZKReader`](../src/zk_rfid.py#L3084)
- **property** [`ZKReader.state`](../src/zk_rfid.py#L3107)
- **property** [`ZKReader.address`](../src/zk_rfid.py#L3121)
- **property** [`ZKReader.is_inventory_running`](../src/zk_rfid.py#L3126)
- **method** [`ZKReader.get_capabilities`](../src/zk_rfid.py#L3130)
- **method** [`ZKReader.open`](../src/zk_rfid.py#L3169)
- **method** [`ZKReader.close`](../src/zk_rfid.py#L3178)
- **method** [`ZKReader.get_reader_info`](../src/zk_rfid.py#L3286)
- **method** [`ZKReader.get_serial_number`](../src/zk_rfid.py#L3294)
- **method** [`ZKReader.get_power`](../src/zk_rfid.py#L3298)
- **method** [`ZKReader.set_power`](../src/zk_rfid.py#L3302)
- **method** [`ZKReader.get_write_power`](../src/zk_rfid.py#L3310)
- **method** [`ZKReader.set_write_power`](../src/zk_rfid.py#L3314)
- **method** [`ZKReader.get_write_retries`](../src/zk_rfid.py#L3318)
- **method** [`ZKReader.set_write_retries`](../src/zk_rfid.py#L3322)
- **method** [`ZKReader.set_antennas`](../src/zk_rfid.py#L3326)
- **method** [`ZKReader.get_antennas`](../src/zk_rfid.py#L3332)
- **method** [`ZKReader.set_antenna_check`](../src/zk_rfid.py#L3339)
- **method** [`ZKReader.get_antenna_check`](../src/zk_rfid.py#L3343)
- **method** [`ZKReader.set_address`](../src/zk_rfid.py#L3348)
- **method** [`ZKReader.set_baudrate`](../src/zk_rfid.py#L3357)
- **method** [`ZKReader.set_inventory_time`](../src/zk_rfid.py#L3377)
- **method** [`ZKReader.set_interface`](../src/zk_rfid.py#L3381)
- **method** [`ZKReader.get_region`](../src/zk_rfid.py#L3385)
- **method** [`ZKReader.set_region`](../src/zk_rfid.py#L3389)
- **method** [`ZKReader.get_profile`](../src/zk_rfid.py#L3395)
- **method** [`ZKReader.set_profile`](../src/zk_rfid.py#L3399)
- **method** [`ZKReader.get_drm`](../src/zk_rfid.py#L3405)
- **method** [`ZKReader.set_drm`](../src/zk_rfid.py#L3409)
- **method** [`ZKReader.set_buzzer`](../src/zk_rfid.py#L3413)
- **method** [`ZKReader.pulse_indicator`](../src/zk_rfid.py#L3417)
- **method** [`ZKReader.get_gpio`](../src/zk_rfid.py#L3423)
- **method** [`ZKReader.set_gpio`](../src/zk_rfid.py#L3428)
- **method** [`ZKReader.get_temperature`](../src/zk_rfid.py#L3433)
- **method** [`ZKReader.measure_return_loss`](../src/zk_rfid.py#L3438)
- **method** [`ZKReader.get_return_loss_threshold`](../src/zk_rfid.py#L3444)
- **method** [`ZKReader.set_return_loss_threshold`](../src/zk_rfid.py#L3448)
- **method** [`ZKReader.get_config`](../src/zk_rfid.py#L3452)
- **method** [`ZKReader.set_config`](../src/zk_rfid.py#L3461)
- **method** [`ZKReader.get_scan_parameters`](../src/zk_rfid.py#L3477)
- **method** [`ZKReader.set_scan_parameters`](../src/zk_rfid.py#L3481)
- **method** [`ZKReader.get_tag_focus`](../src/zk_rfid.py#L3487)
- **method** [`ZKReader.set_tag_focus`](../src/zk_rfid.py#L3491)
- **method** [`ZKReader.get_query_parameters`](../src/zk_rfid.py#L3495)
- **method** [`ZKReader.set_query_parameters`](../src/zk_rfid.py#L3499)
- **method** [`ZKReader.get_tid_parameters`](../src/zk_rfid.py#L3505)
- **method** [`ZKReader.set_tid_parameters`](../src/zk_rfid.py#L3509)
- **method** [`ZKReader.get_inventory_mask`](../src/zk_rfid.py#L3515)
- **method** [`ZKReader.set_inventory_mask`](../src/zk_rfid.py#L3519)
- **method** [`ZKReader.get_custom_profiles`](../src/zk_rfid.py#L3526)
- **method** [`ZKReader.set_custom_profiles`](../src/zk_rfid.py#L3530)
- **method** [`ZKReader.set_real_time_config`](../src/zk_rfid.py#L3536)
- **method** [`ZKReader.get_working_mode`](../src/zk_rfid.py#L3541)
- **method** [`ZKReader.set_working_mode`](../src/zk_rfid.py#L3548)
- **method** [`ZKReader.get_heartbeat_interval`](../src/zk_rfid.py#L3557)
- **method** [`ZKReader.set_heartbeat_interval`](../src/zk_rfid.py#L3561)
- **method** [`ZKReader.get_buffer_length`](../src/zk_rfid.py#L3565)
- **method** [`ZKReader.set_buffer_length`](../src/zk_rfid.py#L3569)
- **method** [`ZKReader.get_buffer_count`](../src/zk_rfid.py#L3573)
- **method** [`ZKReader.clear_buffer`](../src/zk_rfid.py#L3577)
- **method** [`ZKReader.inventory_to_buffer`](../src/zk_rfid.py#L3581)
- **method** [`ZKReader.read_buffer`](../src/zk_rfid.py#L3591)
- **method** [`ZKReader.inventory_once`](../src/zk_rfid.py#L3598)
- **method** [`ZKReader.inventory_single`](../src/zk_rfid.py#L3607)
- **method** [`ZKReader.inventory_matching_epc`](../src/zk_rfid.py#L3614)
- **method** [`ZKReader.start_inventory`](../src/zk_rfid.py#L3630)
- **method** [`ZKReader.stop_inventory`](../src/zk_rfid.py#L3644)
- **method** [`ZKReader.read_memory`](../src/zk_rfid.py#L3658)
- **method** [`ZKReader.write_memory`](../src/zk_rfid.py#L3697)
- **method** [`ZKReader.write_epc`](../src/zk_rfid.py#L3778)
- **method** [`ZKReader.write_epc_single`](../src/zk_rfid.py#L3848)
- **method** [`ZKReader.set_access_password`](../src/zk_rfid.py#L3854)
- **method** [`ZKReader.set_kill_password`](../src/zk_rfid.py#L3874)
- **method** [`ZKReader.lock_tag`](../src/zk_rfid.py#L3893)
- **method** [`ZKReader.kill_tag`](../src/zk_rfid.py#L3906)
- **method** [`ZKReader.block_write`](../src/zk_rfid.py#L3910)
- **method** [`ZKReader.block_erase`](../src/zk_rfid.py#L3926)
- **method** [`ZKReader.select_tag`](../src/zk_rfid.py#L3942)
- **class** [`Equivalence`](../src/zk_rfid.py#L3971)
- **constant** [`Equivalence.VERIFIED`](../src/zk_rfid.py#L3972)
- **constant** [`Equivalence.CONVERTED`](../src/zk_rfid.py#L3973)
- **constant** [`Equivalence.MULTI_STEP`](../src/zk_rfid.py#L3974)
- **constant** [`Equivalence.APPROXIMATE`](../src/zk_rfid.py#L3975)
- **constant** [`Equivalence.UNSUPPORTED`](../src/zk_rfid.py#L3976)
- **constant** [`Equivalence.UNVERIFIED`](../src/zk_rfid.py#L3977)
- **constant** [`CONTRACT`](../src/zk_rfid.py#L3980)
- **class** [`RFMapping`](../src/zk_rfid.py#L3997)
- **method** [`RFMapping.require`](../src/zk_rfid.py#L4005)
- **function** [`hex_epc`](../src/zk_rfid.py#L4011)
- **function** [`power_dict`](../src/zk_rfid.py#L4022)
- **function** [`tag_dict`](../src/zk_rfid.py#L4026)
- **function** [`unsupported`](../src/zk_rfid.py#L4050)
- **class** [`NationAdapter`](../src/zk_rfid.py#L4067)
- **method** [`NationAdapter.open`](../src/zk_rfid.py#L4071)
- **method** [`NationAdapter.close`](../src/zk_rfid.py#L4074)
- **method** [`NationAdapter.get_sdk_info`](../src/zk_rfid.py#L4077)
- **method** [`NationAdapter.Query_Reader_Information`](../src/zk_rfid.py#L4081)
- **method** [`NationAdapter.query_rfid_ability`](../src/zk_rfid.py#L4084)
- **method** [`NationAdapter.query_reader_power`](../src/zk_rfid.py#L4087)
- **method** [`NationAdapter.configure_reader_power`](../src/zk_rfid.py#L4091)
- **method** [`NationAdapter.build_antenna_mask`](../src/zk_rfid.py#L4118)
- **method** [`NationAdapter.save_antenna_mask`](../src/zk_rfid.py#L4125)
- **method** [`NationAdapter.query_enabled_ant_mask`](../src/zk_rfid.py#L4128)
- **method** [`NationAdapter.enable_ant`](../src/zk_rfid.py#L4148)
- **method** [`NationAdapter.disable_ant`](../src/zk_rfid.py#L4151)
- **method** [`NationAdapter.is_inventory_running`](../src/zk_rfid.py#L4154)
- **method** [`NationAdapter.start_inventory_with_mode`](../src/zk_rfid.py#L4157)
- **method** [`NationAdapter.run_inventory`](../src/zk_rfid.py#L4167)
- **method** [`NationAdapter.stop_inventory`](../src/zk_rfid.py#L4188)
- **method** [`NationAdapter.write_epc_to_target_auto`](../src/zk_rfid.py#L4191)
- **method** [`NationAdapter.select_profile`](../src/zk_rfid.py#L4209)
- **method** [`NationAdapter.get_profile`](../src/zk_rfid.py#L4216)
- **method** [`NationAdapter.query_rf_band`](../src/zk_rfid.py#L4220)
- **method** [`NationAdapter.set_rf_band`](../src/zk_rfid.py#L4224) — **unverified mapping; rejected explicitly**
- **method** [`NationAdapter.set_beeper`](../src/zk_rfid.py#L4227)
- **method** [`NationAdapter.get_beeper`](../src/zk_rfid.py#L4233) — **unsupported by design**
- **method** [`NationAdapter.set_filter_settings`](../src/zk_rfid.py#L4236) — **unsupported by design**
- **method** [`NationAdapter.get_session`](../src/zk_rfid.py#L4239)

</details>
