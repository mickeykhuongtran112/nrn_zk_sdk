# API index

Use `ZKReader` for device I/O. See [Python API](api.md) for results and lifecycle,
[compatibility](supported_devices.md) for deployment limits, and [examples](../examples/README.md) for common tasks.

Generated from source with `python tools/export_symbols.py`; edit source docstrings to update descriptions.

## ZKReader

| Method / property | Purpose | Source |
|---|---|---|
| `ZKReader.state` | Host lifecycle state; IDLE alone does not prove a saved real-time mode is off. | [src/zk_rfid.py:3362](../src/zk_rfid.py#L3362) |
| `ZKReader.address` | Current wire address; changes only after an acknowledged address update. | [src/zk_rfid.py:3376](../src/zk_rfid.py#L3376) |
| `ZKReader.is_inventory_running` | Whether this host owns an active or transitioning inventory session. | [src/zk_rfid.py:3381](../src/zk_rfid.py#L3381) |
| `ZKReader.get_capabilities` | Return declared capabilities and their evidence; no hardware probing. | [src/zk_rfid.py:3385](../src/zk_rfid.py#L3385) |
| `ZKReader.open` | Open transport and start the single RX task; recover requires a known clean boundary. | [src/zk_rfid.py:3424](../src/zk_rfid.py#L3424) |
| `ZKReader.close` | Stop owned inventory, close transport and join background tasks. | [src/zk_rfid.py:3437](../src/zk_rfid.py#L3437) |
| `ZKReader.get_reader_info` | Read native reader identity, RF configuration and antenna-check state (0x21). | [src/zk_rfid.py:3551](../src/zk_rfid.py#L3551) |
| `ZKReader.get_serial_number` | Read the four-byte reader serial number (0x4C). | [src/zk_rfid.py:3559](../src/zk_rfid.py#L3559) |
| `ZKReader.get_power` | Read one integer dBm value per declared antenna (0x94). | [src/zk_rfid.py:3563](../src/zk_rfid.py#L3563) |
| `ZKReader.set_power` | Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F). | [src/zk_rfid.py:3567](../src/zk_rfid.py#L3567) |
| `ZKReader.get_write_power` | Read the separate write-power enable flag and dBm value (0x7A). | [src/zk_rfid.py:3575](../src/zk_rfid.py#L3575) |
| `ZKReader.set_write_power` | Set separate write power in dBm, or None to disable it (0x79). | [src/zk_rfid.py:3579](../src/zk_rfid.py#L3579) |
| `ZKReader.get_write_retries` | Read the reader's write-retry count, 0..7 (0x7B). | [src/zk_rfid.py:3583](../src/zk_rfid.py#L3583) |
| `ZKReader.set_write_retries` | Set the module retry count 0..7; the host never retries writes (0x7B). | [src/zk_rfid.py:3587](../src/zk_rfid.py#L3587) |
| `ZKReader.set_antennas` | Select antenna mask with bit0=port1; volatile unless persist=True (0x3F). | [src/zk_rfid.py:3591](../src/zk_rfid.py#L3591) |
| `ZKReader.get_antennas` | Get the native antenna mask; the 16-port getter remains unverified. | [src/zk_rfid.py:3597](../src/zk_rfid.py#L3597) |
| `ZKReader.set_antenna_check` | Enable or disable the reader's antenna connection check (0x66). | [src/zk_rfid.py:3604](../src/zk_rfid.py#L3604) |
| `ZKReader.get_antenna_check` | Read the antenna-check flag from reader information (0x21). | [src/zk_rfid.py:3608](../src/zk_rfid.py#L3608) |
| `ZKReader.set_address` | Change reader address after receiving the ACK at the original address (0x24). | [src/zk_rfid.py:3613](../src/zk_rfid.py#L3613) |
| `ZKReader.set_baudrate` | Receive ACK at the old baud, then switch the transport baud (0x28). | [src/zk_rfid.py:3622](../src/zk_rfid.py#L3622) |
| `ZKReader.set_inventory_time` | Set native scan time in 100 ms units: 0 or 3..255 (0x25). | [src/zk_rfid.py:3642](../src/zk_rfid.py#L3642) |
| `ZKReader.set_interface` | Select usb or uart (0x6A); effective after a module power cycle. | [src/zk_rfid.py:3646](../src/zk_rfid.py#L3646) |
| `ZKReader.get_region` | Read the active native region or CustomRegion (0x9E). | [src/zk_rfid.py:3650](../src/zk_rfid.py#L3650) |
| `ZKReader.set_region` | Set a native band and inclusive channel limits (0x22). | [src/zk_rfid.py:3654](../src/zk_rfid.py#L3654) |
| `ZKReader.get_custom_region` | Read active custom channels, or None when a native region is active (0x9E). | [src/zk_rfid.py:3665](../src/zk_rfid.py#L3665) |
| `ZKReader.set_custom_region` | Set custom channel centers (0x22, band 0xFF); volatile by default. | [src/zk_rfid.py:3669](../src/zk_rfid.py#L3669) |
| `ZKReader.get_profile` | Read native RF profile ID, including the 16-bit Ex10 format (0x7F). | [src/zk_rfid.py:3687](../src/zk_rfid.py#L3687) |
| `ZKReader.set_profile` | Select one native RF profile (0x7F); this does not configure S-CST slots. | [src/zk_rfid.py:3691](../src/zk_rfid.py#L3691) |
| `ZKReader.get_drm` | Read whether dense-reader mode is enabled (0x90). | [src/zk_rfid.py:3701](../src/zk_rfid.py#L3701) |
| `ZKReader.set_drm` | Enable or disable dense-reader mode (0x90). | [src/zk_rfid.py:3705](../src/zk_rfid.py#L3705) |
| `ZKReader.set_buzzer` | Enable or disable the reader's tag-read buzzer (0x40). | [src/zk_rfid.py:3709](../src/zk_rfid.py#L3709) |
| `ZKReader.pulse_indicator` | Pulse LED/buzzer using 50 ms active/silent units (0x33). | [src/zk_rfid.py:3713](../src/zk_rfid.py#L3713) |
| `ZKReader.get_gpio` | Read input and output bits in the documented GPIO layout (0x47). | [src/zk_rfid.py:3719](../src/zk_rfid.py#L3719) |
| `ZKReader.set_gpio` | Set the two documented GPO outputs (0x46). | [src/zk_rfid.py:3724](../src/zk_rfid.py#L3724) |
| `ZKReader.get_temperature` | Read signed integer Celsius using the native sign byte (0x92). | [src/zk_rfid.py:3729](../src/zk_rfid.py#L3729) |
| `ZKReader.measure_return_loss` | Measure return loss at a documented grid frequency in kHz (0x91). | [src/zk_rfid.py:3734](../src/zk_rfid.py#L3734) |
| `ZKReader.get_return_loss_threshold` | Read the antenna return-loss threshold in dB (0x6E). | [src/zk_rfid.py:3740](../src/zk_rfid.py#L3740) |
| `ZKReader.set_return_loss_threshold` | Set the antenna return-loss threshold to 0..20 dB (0x6E). | [src/zk_rfid.py:3744](../src/zk_rfid.py#L3744) |
| `ZKReader.get_config` | Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB). | [src/zk_rfid.py:3748](../src/zk_rfid.py#L3748) |
| `ZKReader.set_config` | Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA). | [src/zk_rfid.py:3765](../src/zk_rfid.py#L3765) |
| `ZKReader.get_scan_parameters` | Read scan interval, antenna dwell, and count (CFG7). | [src/zk_rfid.py:3781](../src/zk_rfid.py#L3781) |
| `ZKReader.set_scan_parameters` | Set scan interval in 10 ms units, dwell in 100 ms units, and count (CFG7). | [src/zk_rfid.py:3785](../src/zk_rfid.py#L3785) |
| `ZKReader.get_tag_focus` | Read the TagFocus enable flag (CFG8). | [src/zk_rfid.py:3791](../src/zk_rfid.py#L3791) |
| `ZKReader.set_tag_focus` | Enable or disable TagFocus for compatible tags (CFG8). | [src/zk_rfid.py:3795](../src/zk_rfid.py#L3795) |
| `ZKReader.get_range_control` | Read the native Range Control value, 0..100 (CFG16); no distance/dB conversion. | [src/zk_rfid.py:3799](../src/zk_rfid.py#L3799) |
| `ZKReader.set_range_control` | Set native Range Control to 0..100 (CFG16); volatile unless persist=True. | [src/zk_rfid.py:3803](../src/zk_rfid.py#L3803) |
| `ZKReader.get_query_parameters` | Read Scenario Q, session/mode selector, and phase reporting (CFG9). | [src/zk_rfid.py:3812](../src/zk_rfid.py#L3812) |
| `ZKReader.set_query_parameters` | Set Scenario Q, session/mode selector, and phase reporting (CFG9). | [src/zk_rfid.py:3816](../src/zk_rfid.py#L3816) |
| `ZKReader.get_tid_parameters` | Read the Scenario TID word address and count (CFG10). | [src/zk_rfid.py:3826](../src/zk_rfid.py#L3826) |
| `ZKReader.set_tid_parameters` | Set Scenario TID selection; word_count=0 selects EPC instead (CFG10). | [src/zk_rfid.py:3830](../src/zk_rfid.py#L3830) |
| `ZKReader.get_inventory_mask` | Read CFG11 as TagMask, or None when disabled; raw_data retains the wire payload. | [src/zk_rfid.py:3836](../src/zk_rfid.py#L3836) |
| `ZKReader.set_inventory_mask` | Set the inventory selection mask, or pass None to clear it (CFG11). | [src/zk_rfid.py:3840](../src/zk_rfid.py#L3840) |
| `ZKReader.get_custom_profiles` | Read the three ordered S-CST RF profile slots (CFG31). | [src/zk_rfid.py:3847](../src/zk_rfid.py#L3847) |
| `ZKReader.set_custom_profiles` | Set three ordered S-CST profile IDs (CFG31); repeated IDs are allowed. | [src/zk_rfid.py:3851](../src/zk_rfid.py#L3851) |
| `ZKReader.set_real_time_config` | Persist the dedicated 0x75 real-time settings; separate from Scenario CFG. | [src/zk_rfid.py:3863](../src/zk_rfid.py#L3863) |
| `ZKReader.get_working_mode` | Read the current mode and real-time configuration (0x77), not the boot mode. | [src/zk_rfid.py:3868](../src/zk_rfid.py#L3868) |
| `ZKReader.set_working_mode` | Set the current mode; persist=True also changes the mode used at boot. | [src/zk_rfid.py:3908](../src/zk_rfid.py#L3908) |
| `ZKReader.get_heartbeat_interval` | Read the heartbeat interval in 30 s units; zero means disabled (0x78). | [src/zk_rfid.py:3978](../src/zk_rfid.py#L3978) |
| `ZKReader.set_heartbeat_interval` | Set heartbeat interval in 30 second units, with 0 disabling it (0x78). | [src/zk_rfid.py:3982](../src/zk_rfid.py#L3982) |
| `ZKReader.get_buffer_length` | Read the maximum stored ID length, 16 or 62 bytes (0x71). | [src/zk_rfid.py:3986](../src/zk_rfid.py#L3986) |
| `ZKReader.set_buffer_length` | Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70). | [src/zk_rfid.py:3990](../src/zk_rfid.py#L3990) |
| `ZKReader.get_buffer_count` | Read the number of tag records in the reader buffer (0x74). | [src/zk_rfid.py:3994](../src/zk_rfid.py#L3994) |
| `ZKReader.clear_buffer` | Clear the reader tag buffer (0x73). | [src/zk_rfid.py:3998](../src/zk_rfid.py#L3998) |
| `ZKReader.inventory_to_buffer` | Run buffered inventory and return counts; this changes reader buffer contents (0x18). | [src/zk_rfid.py:4002](../src/zk_rfid.py#L4002) |
| `ZKReader.read_buffer` | Collect all 0x72 frames; preserve partial reports and enforce one overall deadline. | [src/zk_rfid.py:4012](../src/zk_rfid.py#L4012) |
| `ZKReader.inventory_once` | Run one Answer/Mix round, preserving reports on partial completion or timeout. | [src/zk_rfid.py:4019](../src/zk_rfid.py#L4019) |
| `ZKReader.inventory_single` | Run native single-tag inventory (0x0F). | [src/zk_rfid.py:4028](../src/zk_rfid.py#L4028) |
| `ZKReader.inventory_matching_epc` | Run native EPC-bit-match inventory with explicit bit offset and length (0x1A). | [src/zk_rfid.py:4035](../src/zk_rfid.py#L4035) |
| `ZKReader.start_inventory` | Start a managed report stream; stop explicitly or use its context manager. | [src/zk_rfid.py:4051](../src/zk_rfid.py#L4051) |
| `ZKReader.stop_inventory` | Stop by mode-specific semantics; 0x93 has no ACK of its own. | [src/zk_rfid.py:4088](../src/zk_rfid.py#L4088) |
| `ZKReader.read_memory` | Read 1..120 16-bit words; choose extended address format automatically when needed. | [src/zk_rfid.py:4123](../src/zk_rfid.py#L4123) |
| `ZKReader.write_memory` | Write 1..32 words once, optionally verify using a stable post-write target. | [src/zk_rfid.py:4162](../src/zk_rfid.py#L4162) |
| `ZKReader.write_epc` | Read PC, preserve non-length bits, then one targeted PC+EPC write. | [src/zk_rfid.py:4243](../src/zk_rfid.py#L4243) |
| `ZKReader.write_epc_single` | Native 0x04. Requires exactly one tag physically in the RF field. | [src/zk_rfid.py:4313](../src/zk_rfid.py#L4313) |
| `ZKReader.set_access_password` | Write the 32-bit Access password, then verify using the new password if requested. | [src/zk_rfid.py:4319](../src/zk_rfid.py#L4319) |
| `ZKReader.set_kill_password` | Write the 32-bit Kill password; does not execute Kill or Lock. | [src/zk_rfid.py:4339](../src/zk_rfid.py#L4339) |
| `ZKReader.lock_tag` | Apply native Gen2 protection to a specified target; permanent states are irreversible. | [src/zk_rfid.py:4358](../src/zk_rfid.py#L4358) |
| `ZKReader.kill_tag` | Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password. | [src/zk_rfid.py:4371](../src/zk_rfid.py#L4371) |
| `ZKReader.block_write` | Use native BlockWrite within its independent frame budget; tag support is required. | [src/zk_rfid.py:4375](../src/zk_rfid.py#L4375) |
| `ZKReader.block_erase` | Erase 1..120 words using native BlockErase; tag support is required. | [src/zk_rfid.py:4391](../src/zk_rfid.py#L4391) |
| `ZKReader.select_tag` | Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask. | [src/zk_rfid.py:4407](../src/zk_rfid.py#L4407) |

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
async ZKReader.get_region(self) -> CommandResult[Region | CustomRegion]
async ZKReader.set_region(self, region: Region, *, persist: bool=False, legacy: bool=False) -> CommandResult[None]
async ZKReader.get_custom_region(self) -> CommandResult[CustomRegion | None]
async ZKReader.set_custom_region(self, start_frequency_khz: int, channel_count: int, spacing_khz: int, *, persist: bool=False) -> CommandResult[None]
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
async ZKReader.get_config(self, number: int, *, decoded: bool=True) -> CommandResult[ScanParameters | QueryParameters | TIDParameters | TagMask | tuple[int, ...] | int | bool | bytes | None]
async ZKReader.set_config(self, number: int, data: bytes, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_scan_parameters(self) -> CommandResult[ScanParameters]
async ZKReader.set_scan_parameters(self, parameters: ScanParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_tag_focus(self) -> CommandResult[bool]
async ZKReader.set_tag_focus(self, enabled: bool, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_range_control(self) -> CommandResult[int]
async ZKReader.set_range_control(self, value: int, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_query_parameters(self) -> CommandResult[QueryParameters]
async ZKReader.set_query_parameters(self, parameters: QueryParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_tid_parameters(self) -> CommandResult[TIDParameters]
async ZKReader.set_tid_parameters(self, parameters: TIDParameters, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_inventory_mask(self) -> CommandResult[TagMask | None]
async ZKReader.set_inventory_mask(self, mask: TagMask | None, *, persist: bool=False) -> CommandResult[None]
async ZKReader.get_custom_profiles(self) -> CommandResult[tuple[int, ...]]
async ZKReader.set_custom_profiles(self, profile_ids: tuple[int, int, int], *, persist: bool=False) -> CommandResult[None]
async ZKReader.set_real_time_config(self, config: RealTimeConfig) -> CommandResult[None]
async ZKReader.get_working_mode(self) -> CommandResult[WorkingModeConfig]
async ZKReader.set_working_mode(self, mode: WorkingMode, *, persist: bool=False) -> CommandResult[None]
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
async ZKReader.start_inventory(self, mode: InventoryMode=InventoryMode.SCENARIO, *, config: InventoryConfig=InventoryConfig(), queue_size: int=1024, trigger: bool=False, antenna_mask: int | None=None, antenna_sequence: tuple[int, ...] | None=None) -> InventorySession
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

Native types, transport interfaces, command builders, and decoders.
Module-level command builders return `Request` values without device I/O.
Hardware coverage is recorded in [validation](validation.md).

<details>
<summary>All source symbols</summary>


### src/zk_rfid.py

- **constant** [`SDK_NAME`](../src/zk_rfid.py#L36)
- **constant** [`SDK_VERSION`](../src/zk_rfid.py#L37)
- **function** [`setup_logging`](../src/zk_rfid.py#L40)
- **class** [`ZKError`](../src/zk_rfid.py#L58)
- **class** [`ValidationError`](../src/zk_rfid.py#L62)
- **class** [`ProtocolError`](../src/zk_rfid.py#L66)
- **class** [`UnsupportedFeature`](../src/zk_rfid.py#L70)
- **class** [`UnverifiedFeature`](../src/zk_rfid.py#L74)
- **class** [`StateError`](../src/zk_rfid.py#L78)
- **class** [`TransportError`](../src/zk_rfid.py#L82)
- **class** [`ExchangeError`](../src/zk_rfid.py#L86)
- **class** [`RequestTimeout`](../src/zk_rfid.py#L95)
- **class** [`QueueOverflow`](../src/zk_rfid.py#L99)
- **class** [`DeviceError`](../src/zk_rfid.py#L103)
- **class** [`OperationError`](../src/zk_rfid.py#L112)
- **constant** [`T`](../src/zk_rfid.py#L127)
- **function** [`integer`](../src/zk_rfid.py#L130)
- **function** [`boolean`](../src/zk_rfid.py#L136)
- **function** [`octets`](../src/zk_rfid.py#L142)
- **class** [`MemoryBank`](../src/zk_rfid.py#L148)
- **constant** [`MemoryBank.RESERVED`](../src/zk_rfid.py#L149)
- **constant** [`MemoryBank.EPC`](../src/zk_rfid.py#L150)
- **constant** [`MemoryBank.TID`](../src/zk_rfid.py#L151)
- **constant** [`MemoryBank.USER`](../src/zk_rfid.py#L152)
- **class** [`Outcome`](../src/zk_rfid.py#L155)
- **constant** [`Outcome.SUCCESS`](../src/zk_rfid.py#L156)
- **constant** [`Outcome.FAILURE`](../src/zk_rfid.py#L157)
- **constant** [`Outcome.PARTIAL`](../src/zk_rfid.py#L158)
- **constant** [`Outcome.UNKNOWN`](../src/zk_rfid.py#L159)
- **class** [`Confirmation`](../src/zk_rfid.py#L162)
- **constant** [`Confirmation.NONE`](../src/zk_rfid.py#L163)
- **constant** [`Confirmation.TRANSMITTED`](../src/zk_rfid.py#L164)
- **constant** [`Confirmation.ACKNOWLEDGED`](../src/zk_rfid.py#L165)
- **constant** [`Confirmation.READ_BACK`](../src/zk_rfid.py#L166)
- **class** [`ReaderState`](../src/zk_rfid.py#L169)
- **constant** [`ReaderState.DISCONNECTED`](../src/zk_rfid.py#L170)
- **constant** [`ReaderState.IDLE`](../src/zk_rfid.py#L171)
- **constant** [`ReaderState.STARTING`](../src/zk_rfid.py#L172)
- **constant** [`ReaderState.INVENTORYING`](../src/zk_rfid.py#L173)
- **constant** [`ReaderState.STOPPING`](../src/zk_rfid.py#L174)
- **constant** [`ReaderState.UNKNOWN`](../src/zk_rfid.py#L175)
- **class** [`InventoryMode`](../src/zk_rfid.py#L178)
- **constant** [`InventoryMode.ANSWER`](../src/zk_rfid.py#L179)
- **constant** [`InventoryMode.SCENARIO`](../src/zk_rfid.py#L180)
- **constant** [`InventoryMode.REAL_TIME`](../src/zk_rfid.py#L181)
- **class** [`ScenarioSession`](../src/zk_rfid.py#L184)
- **constant** [`ScenarioSession.S0`](../src/zk_rfid.py#L192)
- **constant** [`ScenarioSession.S1`](../src/zk_rfid.py#L193)
- **constant** [`ScenarioSession.S2`](../src/zk_rfid.py#L194)
- **constant** [`ScenarioSession.S3`](../src/zk_rfid.py#L195)
- **constant** [`ScenarioSession.S_CST`](../src/zk_rfid.py#L196)
- **constant** [`ScenarioSession.S_CTP`](../src/zk_rfid.py#L197)
- **constant** [`ScenarioSession.S_RPT`](../src/zk_rfid.py#L198)
- **constant** [`ScenarioSession.S_PRO`](../src/zk_rfid.py#L199)
- **constant** [`ScenarioSession.AUTO`](../src/zk_rfid.py#L200)
- **class** [`InventoryData`](../src/zk_rfid.py#L203)
- **constant** [`InventoryData.EPC`](../src/zk_rfid.py#L204)
- **constant** [`InventoryData.TID`](../src/zk_rfid.py#L205)
- **constant** [`InventoryData.FAST_ID`](../src/zk_rfid.py#L206)
- **constant** [`InventoryData.MIX`](../src/zk_rfid.py#L207)
- **class** [`WorkingMode`](../src/zk_rfid.py#L210)
- **constant** [`WorkingMode.ANSWER`](../src/zk_rfid.py#L211)
- **constant** [`WorkingMode.REAL_TIME`](../src/zk_rfid.py#L212)
- **constant** [`WorkingMode.TRIGGER`](../src/zk_rfid.py#L213)
- **class** [`LockTarget`](../src/zk_rfid.py#L216)
- **constant** [`LockTarget.KILL_PASSWORD`](../src/zk_rfid.py#L217)
- **constant** [`LockTarget.ACCESS_PASSWORD`](../src/zk_rfid.py#L218)
- **constant** [`LockTarget.EPC`](../src/zk_rfid.py#L219)
- **constant** [`LockTarget.TID`](../src/zk_rfid.py#L220)
- **constant** [`LockTarget.USER`](../src/zk_rfid.py#L221)
- **class** [`LockProtection`](../src/zk_rfid.py#L224)
- **constant** [`LockProtection.UNLOCK`](../src/zk_rfid.py#L225)
- **constant** [`LockProtection.PERMANENT_UNLOCK`](../src/zk_rfid.py#L226)
- **constant** [`LockProtection.PASSWORD`](../src/zk_rfid.py#L227)
- **constant** [`LockProtection.PERMANENT_LOCK`](../src/zk_rfid.py#L228)
- **class** [`TagMask`](../src/zk_rfid.py#L232)
- **method** [`TagMask.encode`](../src/zk_rfid.py#L249)
- **class** [`TagTarget`](../src/zk_rfid.py#L259)
- **class** [`CommandResult`](../src/zk_rfid.py#L277)
- **property** [`CommandResult.ok`](../src/zk_rfid.py#L290)
- **method** [`CommandResult.require_success`](../src/zk_rfid.py#L293)
- **class** [`ReaderInfo`](../src/zk_rfid.py#L300)
- **class** [`InventoryConfig`](../src/zk_rfid.py#L315)
- **class** [`TagReport`](../src/zk_rfid.py#L343)
- **class** [`InventoryStatistics`](../src/zk_rfid.py#L376)
- **class** [`Heartbeat`](../src/zk_rfid.py#L383)
- **class** [`InventoryOutcome`](../src/zk_rfid.py#L390)
- **property** [`InventoryOutcome.unique_count`](../src/zk_rfid.py#L404)
- **class** [`Region`](../src/zk_rfid.py#L409)
- **class** [`CustomRegion`](../src/zk_rfid.py#L422)
- **property** [`CustomRegion.last_frequency_khz`](../src/zk_rfid.py#L440)
- **class** [`GPIOState`](../src/zk_rfid.py#L445)
- **class** [`RealTimeConfig`](../src/zk_rfid.py#L453)
- **class** [`WorkingModeConfig`](../src/zk_rfid.py#L465)
- **class** [`BufferCounts`](../src/zk_rfid.py#L471)
- **class** [`WritePower`](../src/zk_rfid.py#L477)
- **class** [`QueryParameters`](../src/zk_rfid.py#L483)
- **class** [`ScanParameters`](../src/zk_rfid.py#L496)
- **class** [`TIDParameters`](../src/zk_rfid.py#L503)
- **class** [`ParserDiagnostics`](../src/zk_rfid.py#L509)
- **class** [`ReaderCapabilities`](../src/zk_rfid.py#L525)
- **method** [`ReaderCapabilities.require`](../src/zk_rfid.py#L558)
- **constant** [`PHASE_CONVERSION`](../src/zk_rfid.py#L572)
- **constant** [`RSSI_SOURCE`](../src/zk_rfid.py#L573)
- **function** [`rssi_to_dbm`](../src/zk_rfid.py#L576)
- **function** [`phase_to_degrees`](../src/zk_rfid.py#L598)
- **function** [`phase_to_radians`](../src/zk_rfid.py#L613)
- **class** [`TraceEvent`](../src/zk_rfid.py#L626)
- **class** [`TraceEmitter`](../src/zk_rfid.py#L640)
- **method** [`TraceEmitter.emit`](../src/zk_rfid.py#L649)
- **class** [`RFProfile`](../src/zk_rfid.py#L681)
- **constant** [`PROFILES`](../src/zk_rfid.py#L698)
- **function** [`get_profile_definition`](../src/zk_rfid.py#L756)
- **constant** [`CRC16_INIT`](../src/zk_rfid.py#L772)
- **constant** [`CRC16_POLY`](../src/zk_rfid.py#L773)
- **constant** [`MAX_COMMAND_DATA`](../src/zk_rfid.py#L774)
- **constant** [`MAX_RESPONSE_DATA`](../src/zk_rfid.py#L775)
- **constant** [`BROADCAST_ADDRESS`](../src/zk_rfid.py#L776)
- **class** [`Command`](../src/zk_rfid.py#L779)
- **constant** [`Command.INVENTORY`](../src/zk_rfid.py#L780)
- **constant** [`Command.READ_MEMORY`](../src/zk_rfid.py#L781)
- **constant** [`Command.WRITE_MEMORY`](../src/zk_rfid.py#L782)
- **constant** [`Command.WRITE_EPC`](../src/zk_rfid.py#L783)
- **constant** [`Command.KILL`](../src/zk_rfid.py#L784)
- **constant** [`Command.LOCK`](../src/zk_rfid.py#L785)
- **constant** [`Command.BLOCK_ERASE`](../src/zk_rfid.py#L786)
- **constant** [`Command.SINGLE_INVENTORY`](../src/zk_rfid.py#L787)
- **constant** [`Command.BLOCK_WRITE`](../src/zk_rfid.py#L788)
- **constant** [`Command.READ_MEMORY_EXTENDED`](../src/zk_rfid.py#L789)
- **constant** [`Command.WRITE_MEMORY_EXTENDED`](../src/zk_rfid.py#L790)
- **constant** [`Command.BUFFER_INVENTORY`](../src/zk_rfid.py#L791)
- **constant** [`Command.MIX_INVENTORY`](../src/zk_rfid.py#L792)
- **constant** [`Command.INVENTORY_EPC`](../src/zk_rfid.py#L793)
- **constant** [`Command.READER_INFO`](../src/zk_rfid.py#L794)
- **constant** [`Command.SET_REGION`](../src/zk_rfid.py#L795)
- **constant** [`Command.SET_ADDRESS`](../src/zk_rfid.py#L796)
- **constant** [`Command.SET_SCAN_TIME`](../src/zk_rfid.py#L797)
- **constant** [`Command.SET_BAUDRATE`](../src/zk_rfid.py#L798)
- **constant** [`Command.SET_POWER`](../src/zk_rfid.py#L799)
- **constant** [`Command.INDICATOR`](../src/zk_rfid.py#L800)
- **constant** [`Command.SET_ANTENNAS`](../src/zk_rfid.py#L801)
- **constant** [`Command.SET_BUZZER`](../src/zk_rfid.py#L802)
- **constant** [`Command.SET_GPIO`](../src/zk_rfid.py#L803)
- **constant** [`Command.GET_GPIO`](../src/zk_rfid.py#L804)
- **constant** [`Command.SERIAL_NUMBER`](../src/zk_rfid.py#L805)
- **constant** [`Command.FAST_START`](../src/zk_rfid.py#L806)
- **constant** [`Command.FAST_STOP`](../src/zk_rfid.py#L807)
- **constant** [`Command.SET_ANTENNA_CHECK`](../src/zk_rfid.py#L808)
- **constant** [`Command.SET_INTERFACE`](../src/zk_rfid.py#L809)
- **constant** [`Command.RETURN_LOSS_THRESHOLD`](../src/zk_rfid.py#L810)
- **constant** [`Command.SET_BUFFER_LENGTH`](../src/zk_rfid.py#L811)
- **constant** [`Command.GET_BUFFER_LENGTH`](../src/zk_rfid.py#L812)
- **constant** [`Command.READ_BUFFER`](../src/zk_rfid.py#L813)
- **constant** [`Command.CLEAR_BUFFER`](../src/zk_rfid.py#L814)
- **constant** [`Command.BUFFER_COUNT`](../src/zk_rfid.py#L815)
- **constant** [`Command.SET_REAL_TIME`](../src/zk_rfid.py#L816)
- **constant** [`Command.SET_WORKING_MODE`](../src/zk_rfid.py#L817)
- **constant** [`Command.GET_WORKING_MODE`](../src/zk_rfid.py#L818)
- **constant** [`Command.HEARTBEAT`](../src/zk_rfid.py#L819)
- **constant** [`Command.SET_WRITE_POWER`](../src/zk_rfid.py#L820)
- **constant** [`Command.GET_WRITE_POWER`](../src/zk_rfid.py#L821)
- **constant** [`Command.WRITE_RETRIES`](../src/zk_rfid.py#L822)
- **constant** [`Command.PROFILE`](../src/zk_rfid.py#L823)
- **constant** [`Command.DRM`](../src/zk_rfid.py#L824)
- **constant** [`Command.RETURN_LOSS`](../src/zk_rfid.py#L825)
- **constant** [`Command.TEMPERATURE`](../src/zk_rfid.py#L826)
- **constant** [`Command.STOP_INVENTORY`](../src/zk_rfid.py#L827)
- **constant** [`Command.GET_POWER`](../src/zk_rfid.py#L828)
- **constant** [`Command.SELECT`](../src/zk_rfid.py#L829)
- **constant** [`Command.GET_REGION`](../src/zk_rfid.py#L830)
- **constant** [`Command.SET_CONFIG`](../src/zk_rfid.py#L831)
- **constant** [`Command.GET_CONFIG`](../src/zk_rfid.py#L832)
- **constant** [`Command.TAG_REPORT`](../src/zk_rfid.py#L833)
- **class** [`ConfigID`](../src/zk_rfid.py#L836)
- **constant** [`ConfigID.SCAN`](../src/zk_rfid.py#L837)
- **constant** [`ConfigID.TAG_FOCUS`](../src/zk_rfid.py#L838)
- **constant** [`ConfigID.QUERY`](../src/zk_rfid.py#L839)
- **constant** [`ConfigID.TID`](../src/zk_rfid.py#L840)
- **constant** [`ConfigID.MASK`](../src/zk_rfid.py#L841)
- **constant** [`ConfigID.IMPINJ_SCAN`](../src/zk_rfid.py#L842)
- **constant** [`ConfigID.IMPINJ_SCAN_ID`](../src/zk_rfid.py#L843)
- **constant** [`ConfigID.CUSTOM_PROFILES`](../src/zk_rfid.py#L844)
- **function** [`crc16`](../src/zk_rfid.py#L854)
- **function** [`append_crc`](../src/zk_rfid.py#L863)
- **class** [`ResponseFrame`](../src/zk_rfid.py#L875)
- **function** [`encode_command`](../src/zk_rfid.py#L883)
- **function** [`decode_response`](../src/zk_rfid.py#L890)
- **class** [`FrameParser`](../src/zk_rfid.py#L905)
- **method** [`FrameParser.reset`](../src/zk_rfid.py#L911)
- **method** [`FrameParser.feed`](../src/zk_rfid.py#L914)
- **constant** [`STATUS_NAMES`](../src/zk_rfid.py#L961)
- **class** [`StatusInfo`](../src/zk_rfid.py#L990)
- **function** [`interpret_status`](../src/zk_rfid.py#L998)
- **class** [`AsyncTransport`](../src/zk_rfid.py#L1023) â€” **transport interface contract**
- **method** [`AsyncTransport.open`](../src/zk_rfid.py#L1024) â€” **transport interface contract**
- **method** [`AsyncTransport.close`](../src/zk_rfid.py#L1025) â€” **transport interface contract**
- **method** [`AsyncTransport.read`](../src/zk_rfid.py#L1026) â€” **transport interface contract**
- **method** [`AsyncTransport.write`](../src/zk_rfid.py#L1027) â€” **transport interface contract**
- **class** [`SerialTransport`](../src/zk_rfid.py#L1039)
- **method** [`SerialTransport.open`](../src/zk_rfid.py#L1050)
- **method** [`SerialTransport.read`](../src/zk_rfid.py#L1085)
- **method** [`SerialTransport.write`](../src/zk_rfid.py#L1099)
- **method** [`SerialTransport.set_baudrate`](../src/zk_rfid.py#L1107)
- **method** [`SerialTransport.close`](../src/zk_rfid.py#L1113)
- **function** [`raw`](../src/zk_rfid.py#L1134)
- **function** [`exact`](../src/zk_rfid.py#L1138)
- **function** [`ack`](../src/zk_rfid.py#L1144)
- **function** [`u8`](../src/zk_rfid.py#L1148)
- **function** [`u16`](../src/zk_rfid.py#L1152)
- **function** [`switch`](../src/zk_rfid.py#L1156)
- **class** [`Request`](../src/zk_rfid.py#L1164)
- **function** [`decode_reader_info`](../src/zk_rfid.py#L1181)
- **function** [`get_reader_info`](../src/zk_rfid.py#L1200)
- **function** [`get_serial_number`](../src/zk_rfid.py#L1204)
- **constant** [`BAUD_CODES`](../src/zk_rfid.py#L1215)
- **constant** [`PAUSE_CODES`](../src/zk_rfid.py#L1216)
- **function** [`set_address`](../src/zk_rfid.py#L1219)
- **function** [`set_scan_time`](../src/zk_rfid.py#L1223)
- **function** [`set_baudrate`](../src/zk_rfid.py#L1230)
- **function** [`set_interface`](../src/zk_rfid.py#L1237)
- **function** [`set_working_mode`](../src/zk_rfid.py#L1243)
- **function** [`encode_real_time`](../src/zk_rfid.py#L1248)
- **function** [`set_real_time`](../src/zk_rfid.py#L1270)
- **function** [`decode_working_mode`](../src/zk_rfid.py#L1274)
- **function** [`get_working_mode`](../src/zk_rfid.py#L1302)
- **function** [`heartbeat`](../src/zk_rfid.py#L1306)
- **function** [`set_power`](../src/zk_rfid.py#L1325)
- **function** [`get_power`](../src/zk_rfid.py#L1334)
- **function** [`set_write_power`](../src/zk_rfid.py#L1344)
- **function** [`decode_write_power`](../src/zk_rfid.py#L1349)
- **function** [`get_write_power`](../src/zk_rfid.py#L1356)
- **function** [`write_retries`](../src/zk_rfid.py#L1360)
- **function** [`set_antennas`](../src/zk_rfid.py#L1379)
- **function** [`set_antenna_check`](../src/zk_rfid.py#L1390)
- **function** [`decode_antenna`](../src/zk_rfid.py#L1394)
- **constant** [`REGIONS`](../src/zk_rfid.py#L1419)
- **constant** [`BAND_MAX`](../src/zk_rfid.py#L1448)
- **function** [`validate_region`](../src/zk_rfid.py#L1451)
- **function** [`channel_frequency_khz`](../src/zk_rfid.py#L1460)
- **function** [`set_region`](../src/zk_rfid.py#L1469)
- **function** [`decode_region`](../src/zk_rfid.py#L1487)
- **function** [`get_region`](../src/zk_rfid.py#L1499)
- **function** [`set_custom_region`](../src/zk_rfid.py#L1503)
- **function** [`decode_custom_region`](../src/zk_rfid.py#L1511)
- **function** [`get_custom_region`](../src/zk_rfid.py#L1516)
- **function** [`profile`](../src/zk_rfid.py#L1520)
- **function** [`drm`](../src/zk_rfid.py#L1533)
- **constant** [`SCENARIO_SESSIONS`](../src/zk_rfid.py#L1547)
- **function** [`encode_scan`](../src/zk_rfid.py#L1550)
- **function** [`encode_query`](../src/zk_rfid.py#L1558)
- **function** [`encode_tid`](../src/zk_rfid.py#L1566)
- **function** [`encode_profiles`](../src/zk_rfid.py#L1575)
- **function** [`decode_mask`](../src/zk_rfid.py#L1582)
- **function** [`decode_config`](../src/zk_rfid.py#L1597)
- **function** [`get_config`](../src/zk_rfid.py#L1628)
- **function** [`set_config`](../src/zk_rfid.py#L1635)
- **constant** [`ZERO_PASSWORD`](../src/zk_rfid.py#L1674)
- **function** [`password`](../src/zk_rfid.py#L1677)
- **function** [`selection`](../src/zk_rfid.py#L1681)
- **function** [`validate_access`](../src/zk_rfid.py#L1691)
- **function** [`read_memory`](../src/zk_rfid.py#L1699)
- **function** [`write_memory`](../src/zk_rfid.py#L1719)
- **function** [`block_erase`](../src/zk_rfid.py#L1748)
- **function** [`write_epc_single`](../src/zk_rfid.py#L1763)
- **function** [`lock_tag`](../src/zk_rfid.py#L1771)
- **function** [`kill_tag`](../src/zk_rfid.py#L1788)
- **function** [`select_tag`](../src/zk_rfid.py#L1798)
- **function** [`pc_with_epc_length`](../src/zk_rfid.py#L1811)
- **constant** [`VENDOR_TAG_COMMANDS`](../src/zk_rfid.py#L1831) â€” **unsupported by design**
- **function** [`require_vendor_feature`](../src/zk_rfid.py#L1839) â€” **unsupported by design**
- **function** [`validate_inventory`](../src/zk_rfid.py#L1852)
- **function** [`build_inventory`](../src/zk_rfid.py#L1888)
- **function** [`inventory_epc`](../src/zk_rfid.py#L1911)
- **function** [`fast_start`](../src/zk_rfid.py#L1926)
- **function** [`fast_stop`](../src/zk_rfid.py#L1930)
- **function** [`decode_statistics`](../src/zk_rfid.py#L1934)
- **function** [`decode_answer`](../src/zk_rfid.py#L1968)
- **class** [`MixDecoder`](../src/zk_rfid.py#L2006)
- **method** [`MixDecoder.feed`](../src/zk_rfid.py#L2015)
- **method** [`MixDecoder.flush`](../src/zk_rfid.py#L2064)
- **function** [`decode_stream`](../src/zk_rfid.py#L2073)
- **function** [`decode_heartbeat`](../src/zk_rfid.py#L2103)
- **function** [`set_buffer_length`](../src/zk_rfid.py#L2119)
- **function** [`get_buffer_length`](../src/zk_rfid.py#L2125)
- **function** [`clear_buffer`](../src/zk_rfid.py#L2135)
- **function** [`get_buffer_count`](../src/zk_rfid.py#L2139)
- **function** [`decode_counts`](../src/zk_rfid.py#L2143)
- **function** [`decode_buffer`](../src/zk_rfid.py#L2148)
- **function** [`set_buzzer`](../src/zk_rfid.py#L2196)
- **function** [`indicator`](../src/zk_rfid.py#L2200)
- **function** [`set_gpio`](../src/zk_rfid.py#L2215)
- **function** [`decode_gpio`](../src/zk_rfid.py#L2220)
- **function** [`get_gpio`](../src/zk_rfid.py#L2227)
- **function** [`decode_temperature`](../src/zk_rfid.py#L2238)
- **function** [`get_temperature`](../src/zk_rfid.py#L2245)
- **function** [`measure_return_loss`](../src/zk_rfid.py#L2249)
- **function** [`return_loss_threshold`](../src/zk_rfid.py#L2257)
- **class** [`Dispatcher`](../src/zk_rfid.py#L2287)
- **property** [`Dispatcher.pending_command`](../src/zk_rfid.py#L2315)
- **method** [`Dispatcher.open`](../src/zk_rfid.py#L2318)
- **method** [`Dispatcher.close`](../src/zk_rfid.py#L2338)
- **method** [`Dispatcher.exchange`](../src/zk_rfid.py#L2393)
- **method** [`Dispatcher.interrupt_answer`](../src/zk_rfid.py#L2498)
- **function** [`collect_answer`](../src/zk_rfid.py#L2645)
- **function** [`collect_buffer`](../src/zk_rfid.py#L2772)
- **class** [`InventorySession`](../src/zk_rfid.py#L2842)
- **method** [`InventorySession.start`](../src/zk_rfid.py#L2930)
- **method** [`InventorySession.stop`](../src/zk_rfid.py#L3188)
- **method** [`InventorySession.drain`](../src/zk_rfid.py#L3298)
- **class** [`ZKReader`](../src/zk_rfid.py#L3338)
- **property** [`ZKReader.state`](../src/zk_rfid.py#L3362)
- **property** [`ZKReader.address`](../src/zk_rfid.py#L3376)
- **property** [`ZKReader.is_inventory_running`](../src/zk_rfid.py#L3381)
- **method** [`ZKReader.get_capabilities`](../src/zk_rfid.py#L3385)
- **method** [`ZKReader.open`](../src/zk_rfid.py#L3424)
- **method** [`ZKReader.close`](../src/zk_rfid.py#L3437)
- **method** [`ZKReader.get_reader_info`](../src/zk_rfid.py#L3551)
- **method** [`ZKReader.get_serial_number`](../src/zk_rfid.py#L3559)
- **method** [`ZKReader.get_power`](../src/zk_rfid.py#L3563)
- **method** [`ZKReader.set_power`](../src/zk_rfid.py#L3567)
- **method** [`ZKReader.get_write_power`](../src/zk_rfid.py#L3575)
- **method** [`ZKReader.set_write_power`](../src/zk_rfid.py#L3579)
- **method** [`ZKReader.get_write_retries`](../src/zk_rfid.py#L3583)
- **method** [`ZKReader.set_write_retries`](../src/zk_rfid.py#L3587)
- **method** [`ZKReader.set_antennas`](../src/zk_rfid.py#L3591)
- **method** [`ZKReader.get_antennas`](../src/zk_rfid.py#L3597)
- **method** [`ZKReader.set_antenna_check`](../src/zk_rfid.py#L3604)
- **method** [`ZKReader.get_antenna_check`](../src/zk_rfid.py#L3608)
- **method** [`ZKReader.set_address`](../src/zk_rfid.py#L3613)
- **method** [`ZKReader.set_baudrate`](../src/zk_rfid.py#L3622)
- **method** [`ZKReader.set_inventory_time`](../src/zk_rfid.py#L3642)
- **method** [`ZKReader.set_interface`](../src/zk_rfid.py#L3646)
- **method** [`ZKReader.get_region`](../src/zk_rfid.py#L3650)
- **method** [`ZKReader.set_region`](../src/zk_rfid.py#L3654)
- **method** [`ZKReader.get_custom_region`](../src/zk_rfid.py#L3665)
- **method** [`ZKReader.set_custom_region`](../src/zk_rfid.py#L3669)
- **method** [`ZKReader.get_profile`](../src/zk_rfid.py#L3687)
- **method** [`ZKReader.set_profile`](../src/zk_rfid.py#L3691)
- **method** [`ZKReader.get_drm`](../src/zk_rfid.py#L3701)
- **method** [`ZKReader.set_drm`](../src/zk_rfid.py#L3705)
- **method** [`ZKReader.set_buzzer`](../src/zk_rfid.py#L3709)
- **method** [`ZKReader.pulse_indicator`](../src/zk_rfid.py#L3713)
- **method** [`ZKReader.get_gpio`](../src/zk_rfid.py#L3719)
- **method** [`ZKReader.set_gpio`](../src/zk_rfid.py#L3724)
- **method** [`ZKReader.get_temperature`](../src/zk_rfid.py#L3729)
- **method** [`ZKReader.measure_return_loss`](../src/zk_rfid.py#L3734)
- **method** [`ZKReader.get_return_loss_threshold`](../src/zk_rfid.py#L3740)
- **method** [`ZKReader.set_return_loss_threshold`](../src/zk_rfid.py#L3744)
- **method** [`ZKReader.get_config`](../src/zk_rfid.py#L3748)
- **method** [`ZKReader.set_config`](../src/zk_rfid.py#L3765)
- **method** [`ZKReader.get_scan_parameters`](../src/zk_rfid.py#L3781)
- **method** [`ZKReader.set_scan_parameters`](../src/zk_rfid.py#L3785)
- **method** [`ZKReader.get_tag_focus`](../src/zk_rfid.py#L3791)
- **method** [`ZKReader.set_tag_focus`](../src/zk_rfid.py#L3795)
- **method** [`ZKReader.get_range_control`](../src/zk_rfid.py#L3799)
- **method** [`ZKReader.set_range_control`](../src/zk_rfid.py#L3803)
- **method** [`ZKReader.get_query_parameters`](../src/zk_rfid.py#L3812)
- **method** [`ZKReader.set_query_parameters`](../src/zk_rfid.py#L3816)
- **method** [`ZKReader.get_tid_parameters`](../src/zk_rfid.py#L3826)
- **method** [`ZKReader.set_tid_parameters`](../src/zk_rfid.py#L3830)
- **method** [`ZKReader.get_inventory_mask`](../src/zk_rfid.py#L3836)
- **method** [`ZKReader.set_inventory_mask`](../src/zk_rfid.py#L3840)
- **method** [`ZKReader.get_custom_profiles`](../src/zk_rfid.py#L3847)
- **method** [`ZKReader.set_custom_profiles`](../src/zk_rfid.py#L3851)
- **method** [`ZKReader.set_real_time_config`](../src/zk_rfid.py#L3863)
- **method** [`ZKReader.get_working_mode`](../src/zk_rfid.py#L3868)
- **method** [`ZKReader.set_working_mode`](../src/zk_rfid.py#L3908)
- **method** [`ZKReader.get_heartbeat_interval`](../src/zk_rfid.py#L3978)
- **method** [`ZKReader.set_heartbeat_interval`](../src/zk_rfid.py#L3982)
- **method** [`ZKReader.get_buffer_length`](../src/zk_rfid.py#L3986)
- **method** [`ZKReader.set_buffer_length`](../src/zk_rfid.py#L3990)
- **method** [`ZKReader.get_buffer_count`](../src/zk_rfid.py#L3994)
- **method** [`ZKReader.clear_buffer`](../src/zk_rfid.py#L3998)
- **method** [`ZKReader.inventory_to_buffer`](../src/zk_rfid.py#L4002)
- **method** [`ZKReader.read_buffer`](../src/zk_rfid.py#L4012)
- **method** [`ZKReader.inventory_once`](../src/zk_rfid.py#L4019)
- **method** [`ZKReader.inventory_single`](../src/zk_rfid.py#L4028)
- **method** [`ZKReader.inventory_matching_epc`](../src/zk_rfid.py#L4035)
- **method** [`ZKReader.start_inventory`](../src/zk_rfid.py#L4051)
- **method** [`ZKReader.stop_inventory`](../src/zk_rfid.py#L4088)
- **method** [`ZKReader.read_memory`](../src/zk_rfid.py#L4123)
- **method** [`ZKReader.write_memory`](../src/zk_rfid.py#L4162)
- **method** [`ZKReader.write_epc`](../src/zk_rfid.py#L4243)
- **method** [`ZKReader.write_epc_single`](../src/zk_rfid.py#L4313)
- **method** [`ZKReader.set_access_password`](../src/zk_rfid.py#L4319)
- **method** [`ZKReader.set_kill_password`](../src/zk_rfid.py#L4339)
- **method** [`ZKReader.lock_tag`](../src/zk_rfid.py#L4358)
- **method** [`ZKReader.kill_tag`](../src/zk_rfid.py#L4371)
- **method** [`ZKReader.block_write`](../src/zk_rfid.py#L4375)
- **method** [`ZKReader.block_erase`](../src/zk_rfid.py#L4391)
- **method** [`ZKReader.select_tag`](../src/zk_rfid.py#L4407)

</details>
