# Danh mục chức năng Python đã triển khai

Sinh từ AST bằng `python tools/export_symbols.py`. Tên, chữ ký và dòng nguồn lấy trực tiếp từ implementation.

Mức chứng cứ: manual V2.25/demo V6.8, unit/integration và runtime CPython/Pyodide. **Chưa nghiệm thu toàn bộ phần cứng.** Người dùng đã báo 3 hardware tests PASS qua ảnh trên COM13/115200; xem [phạm vi chứng cứ](demo_and_parity.md). Các giới hạn ở [ma trận hỗ trợ](supported_devices.md) và [errata](protocol/errata.md).

## API điều khiển ZKReader (77 symbol public)

| Function/property | Chức năng | Implementation |
|---|---|---|
| `ZKReader.state` | Host lifecycle state; IDLE alone does not prove a saved real-time mode is off. | [src/zk_rfid/reader.py:92](../src/zk_rfid/reader.py#L92) |
| `ZKReader.address` | Current wire address; changes only after an acknowledged address update. | [src/zk_rfid/reader.py:106](../src/zk_rfid/reader.py#L106) |
| `ZKReader.is_inventory_running` | Whether this host owns an active or transitioning inventory session. | [src/zk_rfid/reader.py:111](../src/zk_rfid/reader.py#L111) |
| `ZKReader.get_capabilities` | Return declared capabilities and their evidence; no hardware probing. | [src/zk_rfid/reader.py:115](../src/zk_rfid/reader.py#L115) |
| `ZKReader.open` | Open transport and start the single RX task; recover requires a known clean boundary. | [src/zk_rfid/reader.py:154](../src/zk_rfid/reader.py#L154) |
| `ZKReader.close` | Stop owned inventory, close transport and join background tasks. | [src/zk_rfid/reader.py:163](../src/zk_rfid/reader.py#L163) |
| `ZKReader.get_reader_info` | Read native reader identity, RF configuration and antenna-check state (0x21). | [src/zk_rfid/reader.py:271](../src/zk_rfid/reader.py#L271) |
| `ZKReader.get_serial_number` | Read the four-byte reader serial number (0x4C). | [src/zk_rfid/reader.py:279](../src/zk_rfid/reader.py#L279) |
| `ZKReader.get_power` | Read one integer dBm value per declared antenna (0x94). | [src/zk_rfid/reader.py:283](../src/zk_rfid/reader.py#L283) |
| `ZKReader.set_power` | Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F). | [src/zk_rfid/reader.py:287](../src/zk_rfid/reader.py#L287) |
| `ZKReader.get_write_power` | Get write power. Returns native status and confirmation. | [src/zk_rfid/reader.py:295](../src/zk_rfid/reader.py#L295) |
| `ZKReader.set_write_power` | Set separate write power in dBm, or None to disable it (0x79). | [src/zk_rfid/reader.py:299](../src/zk_rfid/reader.py#L299) |
| `ZKReader.get_write_retries` | Get write retries. Returns native status and confirmation. | [src/zk_rfid/reader.py:303](../src/zk_rfid/reader.py#L303) |
| `ZKReader.set_write_retries` | Set the module retry count 0..7; the host never retries writes (0x7B). | [src/zk_rfid/reader.py:307](../src/zk_rfid/reader.py#L307) |
| `ZKReader.set_antennas` | Select antenna mask with bit0=port1; volatile unless persist=True (0x3F). | [src/zk_rfid/reader.py:311](../src/zk_rfid/reader.py#L311) |
| `ZKReader.get_antennas` | Get the native antenna mask; the 16-port getter remains unverified. | [src/zk_rfid/reader.py:317](../src/zk_rfid/reader.py#L317) |
| `ZKReader.set_antenna_check` | Set antenna check. Returns native status and confirmation. | [src/zk_rfid/reader.py:324](../src/zk_rfid/reader.py#L324) |
| `ZKReader.get_antenna_check` | Get antenna check. Returns native status and confirmation. | [src/zk_rfid/reader.py:328](../src/zk_rfid/reader.py#L328) |
| `ZKReader.set_address` | Change reader address after receiving the ACK at the original address (0x24). | [src/zk_rfid/reader.py:333](../src/zk_rfid/reader.py#L333) |
| `ZKReader.set_baudrate` | Receive ACK at the old baud, then switch the transport baud (0x28). | [src/zk_rfid/reader.py:342](../src/zk_rfid/reader.py#L342) |
| `ZKReader.set_inventory_time` | Set native scan time in 100 ms units: 0 or 3..255 (0x25). | [src/zk_rfid/reader.py:362](../src/zk_rfid/reader.py#L362) |
| `ZKReader.set_interface` | Select usb or uart (0x6A); effective after a module power cycle. | [src/zk_rfid/reader.py:366](../src/zk_rfid/reader.py#L366) |
| `ZKReader.get_region` | Get region. Returns native status and confirmation. | [src/zk_rfid/reader.py:370](../src/zk_rfid/reader.py#L370) |
| `ZKReader.set_region` | Set native region and channel indices; no NATION region-ID conversion (0x22). | [src/zk_rfid/reader.py:374](../src/zk_rfid/reader.py#L374) |
| `ZKReader.get_profile` | Read native RF profile ID, including the 16-bit Ex10 format (0x7F). | [src/zk_rfid/reader.py:380](../src/zk_rfid/reader.py#L380) |
| `ZKReader.set_profile` | Set native RF profile ID; no inferred equivalence with NATION profiles (0x7F). | [src/zk_rfid/reader.py:384](../src/zk_rfid/reader.py#L384) |
| `ZKReader.get_drm` | Get drm. Returns native status and confirmation. | [src/zk_rfid/reader.py:392](../src/zk_rfid/reader.py#L392) |
| `ZKReader.set_drm` | Set drm. Returns native status and confirmation. | [src/zk_rfid/reader.py:396](../src/zk_rfid/reader.py#L396) |
| `ZKReader.set_buzzer` | Set buzzer. Returns native status and confirmation. | [src/zk_rfid/reader.py:400](../src/zk_rfid/reader.py#L400) |
| `ZKReader.pulse_indicator` | Pulse LED/buzzer using 50 ms active/silent units (0x33). | [src/zk_rfid/reader.py:404](../src/zk_rfid/reader.py#L404) |
| `ZKReader.get_gpio` | Read input and output bits in the documented GPIO layout (0x47). | [src/zk_rfid/reader.py:410](../src/zk_rfid/reader.py#L410) |
| `ZKReader.set_gpio` | Set the two documented GPO outputs (0x46). | [src/zk_rfid/reader.py:415](../src/zk_rfid/reader.py#L415) |
| `ZKReader.get_temperature` | Read signed integer Celsius using the native sign byte (0x92). | [src/zk_rfid/reader.py:420](../src/zk_rfid/reader.py#L420) |
| `ZKReader.measure_return_loss` | Measure return loss at a documented grid frequency in kHz (0x91). | [src/zk_rfid/reader.py:425](../src/zk_rfid/reader.py#L425) |
| `ZKReader.get_return_loss_threshold` | Get return loss threshold. Returns native status and confirmation. | [src/zk_rfid/reader.py:433](../src/zk_rfid/reader.py#L433) |
| `ZKReader.set_return_loss_threshold` | Set return loss threshold. Returns native status and confirmation. | [src/zk_rfid/reader.py:437](../src/zk_rfid/reader.py#L437) |
| `ZKReader.get_config` | Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB). | [src/zk_rfid/reader.py:441](../src/zk_rfid/reader.py#L441) |
| `ZKReader.set_config` | Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA). | [src/zk_rfid/reader.py:450](../src/zk_rfid/reader.py#L450) |
| `ZKReader.get_scan_parameters` | Get scan parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:466](../src/zk_rfid/reader.py#L466) |
| `ZKReader.set_scan_parameters` | Set scan parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:470](../src/zk_rfid/reader.py#L470) |
| `ZKReader.get_tag_focus` | Get tag focus. Returns native status and confirmation. | [src/zk_rfid/reader.py:476](../src/zk_rfid/reader.py#L476) |
| `ZKReader.set_tag_focus` | Set tag focus. Returns native status and confirmation. | [src/zk_rfid/reader.py:480](../src/zk_rfid/reader.py#L480) |
| `ZKReader.get_query_parameters` | Get query parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:484](../src/zk_rfid/reader.py#L484) |
| `ZKReader.set_query_parameters` | Set query parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:488](../src/zk_rfid/reader.py#L488) |
| `ZKReader.get_tid_parameters` | Get tid parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:494](../src/zk_rfid/reader.py#L494) |
| `ZKReader.set_tid_parameters` | Set tid parameters. Returns native status and confirmation. | [src/zk_rfid/reader.py:498](../src/zk_rfid/reader.py#L498) |
| `ZKReader.get_inventory_mask` | Get inventory mask. Returns native status and confirmation. | [src/zk_rfid/reader.py:504](../src/zk_rfid/reader.py#L504) |
| `ZKReader.set_inventory_mask` | Set inventory mask. Returns native status and confirmation. | [src/zk_rfid/reader.py:508](../src/zk_rfid/reader.py#L508) |
| `ZKReader.get_custom_profiles` | Get custom profiles. Returns native status and confirmation. | [src/zk_rfid/reader.py:515](../src/zk_rfid/reader.py#L515) |
| `ZKReader.set_custom_profiles` | Set custom profiles. Returns native status and confirmation. | [src/zk_rfid/reader.py:519](../src/zk_rfid/reader.py#L519) |
| `ZKReader.set_real_time_config` | Persist the dedicated 0x75 real-time settings; separate from Scenario CFG. | [src/zk_rfid/reader.py:525](../src/zk_rfid/reader.py#L525) |
| `ZKReader.get_working_mode` | Read the 0x77 mode and fixed-width saved real-time configuration. | [src/zk_rfid/reader.py:530](../src/zk_rfid/reader.py#L530) |
| `ZKReader.set_working_mode` | Persistent mode setting. For managed 0xEE delivery use start_inventory(). | [src/zk_rfid/reader.py:537](../src/zk_rfid/reader.py#L537) |
| `ZKReader.get_heartbeat_interval` | Get heartbeat interval. Returns native status and confirmation. | [src/zk_rfid/reader.py:546](../src/zk_rfid/reader.py#L546) |
| `ZKReader.set_heartbeat_interval` | Set heartbeat interval in 30 second units, with 0 disabling it (0x78). | [src/zk_rfid/reader.py:550](../src/zk_rfid/reader.py#L550) |
| `ZKReader.get_buffer_length` | Get buffer length. Returns native status and confirmation. | [src/zk_rfid/reader.py:554](../src/zk_rfid/reader.py#L554) |
| `ZKReader.set_buffer_length` | Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70). | [src/zk_rfid/reader.py:558](../src/zk_rfid/reader.py#L558) |
| `ZKReader.get_buffer_count` | Get buffer count. Returns native status and confirmation. | [src/zk_rfid/reader.py:562](../src/zk_rfid/reader.py#L562) |
| `ZKReader.clear_buffer` | Clear the reader tag buffer (0x73). | [src/zk_rfid/reader.py:566](../src/zk_rfid/reader.py#L566) |
| `ZKReader.inventory_to_buffer` | Run buffered inventory and return counts; this changes reader buffer contents (0x18). | [src/zk_rfid/reader.py:570](../src/zk_rfid/reader.py#L570) |
| `ZKReader.read_buffer` | Collect all 0x72 frames; preserve partial reports and enforce one overall deadline. | [src/zk_rfid/reader.py:582](../src/zk_rfid/reader.py#L582) |
| `ZKReader.inventory_once` | Run one Answer/Mix round, preserving reports on partial completion or timeout. | [src/zk_rfid/reader.py:590](../src/zk_rfid/reader.py#L590) |
| `ZKReader.inventory_single` | Run native single-tag inventory (0x0F). | [src/zk_rfid/reader.py:600](../src/zk_rfid/reader.py#L600) |
| `ZKReader.inventory_matching_epc` | Run native EPC-bit-match inventory with explicit bit offset and length (0x1A). | [src/zk_rfid/reader.py:608](../src/zk_rfid/reader.py#L608) |
| `ZKReader.start_inventory` | Start a managed async report iterator; stop explicitly or use its context manager. | [src/zk_rfid/reader.py:625](../src/zk_rfid/reader.py#L625) |
| `ZKReader.stop_inventory` | Stop by mode-specific semantics; 0x93 has no ACK of its own. | [src/zk_rfid/reader.py:640](../src/zk_rfid/reader.py#L640) |
| `ZKReader.read_memory` | Read 1..120 16-bit words; choose extended address format automatically when needed. | [src/zk_rfid/reader.py:654](../src/zk_rfid/reader.py#L654) |
| `ZKReader.write_memory` | Write 1..32 words once, optionally verify using a stable post-write target. | [src/zk_rfid/reader.py:693](../src/zk_rfid/reader.py#L693) |
| `ZKReader.write_epc` | Read PC, preserve non-length bits, then one targeted PC+EPC write. | [src/zk_rfid/reader.py:774](../src/zk_rfid/reader.py#L774) |
| `ZKReader.write_epc_single` | Native 0x04. Requires exactly one tag physically in the RF field. | [src/zk_rfid/reader.py:846](../src/zk_rfid/reader.py#L846) |
| `ZKReader.set_access_password` | Write the 32-bit Access password, then verify using the new password if requested. | [src/zk_rfid/reader.py:854](../src/zk_rfid/reader.py#L854) |
| `ZKReader.set_kill_password` | Write the 32-bit Kill password; does not execute Kill or Lock. | [src/zk_rfid/reader.py:874](../src/zk_rfid/reader.py#L874) |
| `ZKReader.lock_tag` | Apply native Gen2 protection to a specified target; permanent states are irreversible. | [src/zk_rfid/reader.py:893](../src/zk_rfid/reader.py#L893) |
| `ZKReader.kill_tag` | Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password. | [src/zk_rfid/reader.py:908](../src/zk_rfid/reader.py#L908) |
| `ZKReader.block_write` | Use native BlockWrite within its independent frame budget; tag support is required. | [src/zk_rfid/reader.py:912](../src/zk_rfid/reader.py#L912) |
| `ZKReader.block_erase` | Erase 1..120 words using native BlockErase; tag support is required. | [src/zk_rfid/reader.py:928](../src/zk_rfid/reader.py#L928) |
| `ZKReader.select_tag` | Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask. | [src/zk_rfid/reader.py:944](../src/zk_rfid/reader.py#L944) |

## Chữ ký public ZKReader

```python
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
async ZKReader.read_memory(self, bank: MemoryBank, word_address: int, word_count: int, *, target: TagTarget | None=None, access_password: bytes=tag_access.ZERO_PASSWORD, extended_format: bool | None=None) -> CommandResult[bytes]
async ZKReader.write_memory(self, bank: MemoryBank, word_address: int, data: bytes, *, target: TagTarget | None=None, access_password: bytes=tag_access.ZERO_PASSWORD, extended_format: bool | None=None, verify: bool=False, verification_target: TagTarget | None=None, verification_password: bytes | None=None, timeout: float | None=None) -> CommandResult[bytes | None]
async ZKReader.write_epc(self, epc: bytes, *, target: TagTarget, access_password: bytes=tag_access.ZERO_PASSWORD, verify: bool=True, verification_target: TagTarget | None=None, timeout: float | None=None) -> CommandResult[bytes | None]
async ZKReader.write_epc_single(self, epc: bytes, *, access_password: bytes=tag_access.ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.set_access_password(self, new_password: bytes, *, target: TagTarget, access_password: bytes=tag_access.ZERO_PASSWORD, verify: bool=True) -> CommandResult[bytes | None]
async ZKReader.set_kill_password(self, new_password: bytes, *, target: TagTarget, access_password: bytes=tag_access.ZERO_PASSWORD, verify: bool=True) -> CommandResult[bytes | None]
async ZKReader.lock_tag(self, lock_target: int, protection: int, *, target: TagTarget, access_password: bytes=tag_access.ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.kill_tag(self, kill_password: bytes, *, target: TagTarget) -> CommandResult[None]
async ZKReader.block_write(self, bank: MemoryBank, word_address: int, data: bytes, *, target: TagTarget | None=None, access_password: bytes=tag_access.ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.block_erase(self, bank: MemoryBank, word_address: int, word_count: int, *, target: TagTarget | None=None, access_password: bytes=tag_access.ZERO_PASSWORD) -> CommandResult[None]
async ZKReader.select_tag(self, mask: TagMask, *, antenna_mask: int=1, select_target: int=4, action: int=0, truncate: bool=False) -> CommandResult[None]
```

## Symbols theo tree package

Bao gồm class, method, function và constant; mục vendor-tag được đánh dấu ngoài scope.


### src/zk_rfid/__init__.py

- **constant** [`SDK_NAME`](../src/zk_rfid/__init__.py#L55)
- **constant** [`SDK_VERSION`](../src/zk_rfid/__init__.py#L56)
- **function** [`setup_logging`](../src/zk_rfid/__init__.py#L59)

### src/zk_rfid/capabilities.py

- **class** [`ReaderCapabilities`](../src/zk_rfid/capabilities.py#L9)
- **method** [`ReaderCapabilities.require`](../src/zk_rfid/capabilities.py#L42)

### src/zk_rfid/commands/_common.py

- **constant** [`T`](../src/zk_rfid/commands/_common.py#L8)
- **function** [`raw`](../src/zk_rfid/commands/_common.py#L11)
- **function** [`exact`](../src/zk_rfid/commands/_common.py#L15)
- **function** [`ack`](../src/zk_rfid/commands/_common.py#L21)
- **function** [`u8`](../src/zk_rfid/commands/_common.py#L25)
- **function** [`u16`](../src/zk_rfid/commands/_common.py#L29)
- **function** [`switch`](../src/zk_rfid/commands/_common.py#L33)
- **class** [`Request`](../src/zk_rfid/commands/_common.py#L41)

### src/zk_rfid/commands/antenna.py

- **function** [`set_antennas`](../src/zk_rfid/commands/antenna.py#L8)
- **function** [`set_antenna_check`](../src/zk_rfid/commands/antenna.py#L19)
- **function** [`decode_antenna`](../src/zk_rfid/commands/antenna.py#L23)

### src/zk_rfid/commands/buffer.py

- **function** [`set_buffer_length`](../src/zk_rfid/commands/buffer.py#L10)
- **function** [`get_buffer_length`](../src/zk_rfid/commands/buffer.py#L16)
- **function** [`clear_buffer`](../src/zk_rfid/commands/buffer.py#L26)
- **function** [`get_buffer_count`](../src/zk_rfid/commands/buffer.py#L30)
- **function** [`decode_counts`](../src/zk_rfid/commands/buffer.py#L34)
- **function** [`decode_buffer`](../src/zk_rfid/commands/buffer.py#L39)

### src/zk_rfid/commands/diagnostics.py

- **function** [`decode_temperature`](../src/zk_rfid/commands/diagnostics.py#L8)
- **function** [`get_temperature`](../src/zk_rfid/commands/diagnostics.py#L15)
- **function** [`measure_return_loss`](../src/zk_rfid/commands/diagnostics.py#L19)
- **function** [`return_loss_threshold`](../src/zk_rfid/commands/diagnostics.py#L27)

### src/zk_rfid/commands/extended.py

- **constant** [`SCENARIO_SESSIONS`](../src/zk_rfid/commands/extended.py#L7)
- **function** [`encode_scan`](../src/zk_rfid/commands/extended.py#L10)
- **function** [`encode_query`](../src/zk_rfid/commands/extended.py#L18)
- **function** [`encode_tid`](../src/zk_rfid/commands/extended.py#L26)
- **function** [`encode_profiles`](../src/zk_rfid/commands/extended.py#L35)
- **function** [`decode_mask`](../src/zk_rfid/commands/extended.py#L41)
- **function** [`decode_config`](../src/zk_rfid/commands/extended.py#L50)
- **function** [`get_config`](../src/zk_rfid/commands/extended.py#L78)
- **function** [`set_config`](../src/zk_rfid/commands/extended.py#L85)

### src/zk_rfid/commands/inventory.py

- **function** [`validate_inventory`](../src/zk_rfid/commands/inventory.py#L21)
- **function** [`build_inventory`](../src/zk_rfid/commands/inventory.py#L57)
- **function** [`inventory_epc`](../src/zk_rfid/commands/inventory.py#L80)
- **function** [`fast_start`](../src/zk_rfid/commands/inventory.py#L95)
- **function** [`fast_stop`](../src/zk_rfid/commands/inventory.py#L99)
- **function** [`decode_statistics`](../src/zk_rfid/commands/inventory.py#L103)
- **function** [`decode_answer`](../src/zk_rfid/commands/inventory.py#L138)
- **class** [`MixDecoder`](../src/zk_rfid/commands/inventory.py#L176)
- **method** [`MixDecoder.feed`](../src/zk_rfid/commands/inventory.py#L185)
- **method** [`MixDecoder.flush`](../src/zk_rfid/commands/inventory.py#L234)
- **function** [`decode_stream`](../src/zk_rfid/commands/inventory.py#L243)
- **function** [`decode_heartbeat`](../src/zk_rfid/commands/inventory.py#L273)

### src/zk_rfid/commands/io_control.py

- **function** [`set_buzzer`](../src/zk_rfid/commands/io_control.py#L8)
- **function** [`indicator`](../src/zk_rfid/commands/io_control.py#L12)
- **function** [`set_gpio`](../src/zk_rfid/commands/io_control.py#L27)
- **function** [`decode_gpio`](../src/zk_rfid/commands/io_control.py#L32)
- **function** [`get_gpio`](../src/zk_rfid/commands/io_control.py#L39)

### src/zk_rfid/commands/power.py

- **function** [`set_power`](../src/zk_rfid/commands/power.py#L8)
- **function** [`get_power`](../src/zk_rfid/commands/power.py#L17)
- **function** [`set_write_power`](../src/zk_rfid/commands/power.py#L27)
- **function** [`decode_write_power`](../src/zk_rfid/commands/power.py#L32)
- **function** [`get_write_power`](../src/zk_rfid/commands/power.py#L39)
- **function** [`write_retries`](../src/zk_rfid/commands/power.py#L43)

### src/zk_rfid/commands/reader_config.py

- **constant** [`BAUD_CODES`](../src/zk_rfid/commands/reader_config.py#L7)
- **constant** [`PAUSE_CODES`](../src/zk_rfid/commands/reader_config.py#L8)
- **function** [`set_address`](../src/zk_rfid/commands/reader_config.py#L11)
- **function** [`set_scan_time`](../src/zk_rfid/commands/reader_config.py#L15)
- **function** [`set_baudrate`](../src/zk_rfid/commands/reader_config.py#L22)
- **function** [`set_interface`](../src/zk_rfid/commands/reader_config.py#L29)
- **function** [`set_working_mode`](../src/zk_rfid/commands/reader_config.py#L35)
- **function** [`encode_real_time`](../src/zk_rfid/commands/reader_config.py#L39)
- **function** [`set_real_time`](../src/zk_rfid/commands/reader_config.py#L61)
- **function** [`decode_working_mode`](../src/zk_rfid/commands/reader_config.py#L65)
- **function** [`get_working_mode`](../src/zk_rfid/commands/reader_config.py#L91)
- **function** [`heartbeat`](../src/zk_rfid/commands/reader_config.py#L95)

### src/zk_rfid/commands/reader_info.py

- **function** [`decode_reader_info`](../src/zk_rfid/commands/reader_info.py#L8)
- **function** [`get_reader_info`](../src/zk_rfid/commands/reader_info.py#L27)
- **function** [`get_serial_number`](../src/zk_rfid/commands/reader_info.py#L31)

### src/zk_rfid/commands/rf_config.py

- **constant** [`REGIONS`](../src/zk_rfid/commands/rf_config.py#L8)
- **constant** [`BAND_MAX`](../src/zk_rfid/commands/rf_config.py#L37)
- **function** [`validate_region`](../src/zk_rfid/commands/rf_config.py#L40)
- **function** [`channel_frequency_khz`](../src/zk_rfid/commands/rf_config.py#L49)
- **function** [`set_region`](../src/zk_rfid/commands/rf_config.py#L57)
- **function** [`decode_region`](../src/zk_rfid/commands/rf_config.py#L75)
- **function** [`get_region`](../src/zk_rfid/commands/rf_config.py#L83)
- **function** [`profile`](../src/zk_rfid/commands/rf_config.py#L87)
- **function** [`drm`](../src/zk_rfid/commands/rf_config.py#L100)

### src/zk_rfid/commands/tag_access.py

- **constant** [`ZERO_PASSWORD`](../src/zk_rfid/commands/tag_access.py#L7)
- **function** [`password`](../src/zk_rfid/commands/tag_access.py#L10)
- **function** [`selection`](../src/zk_rfid/commands/tag_access.py#L14)
- **function** [`validate_access`](../src/zk_rfid/commands/tag_access.py#L24)
- **function** [`read_memory`](../src/zk_rfid/commands/tag_access.py#L32)
- **function** [`write_memory`](../src/zk_rfid/commands/tag_access.py#L52)
- **function** [`block_erase`](../src/zk_rfid/commands/tag_access.py#L81)
- **function** [`write_epc_single`](../src/zk_rfid/commands/tag_access.py#L96)
- **function** [`lock_tag`](../src/zk_rfid/commands/tag_access.py#L104)
- **function** [`kill_tag`](../src/zk_rfid/commands/tag_access.py#L121)
- **function** [`select_tag`](../src/zk_rfid/commands/tag_access.py#L131)
- **function** [`pc_with_epc_length`](../src/zk_rfid/commands/tag_access.py#L144)

### src/zk_rfid/commands/tag_features.py

- **constant** [`VENDOR_TAG_COMMANDS`](../src/zk_rfid/commands/tag_features.py#L10) — **unsupported by design**
- **function** [`require_vendor_feature`](../src/zk_rfid/commands/tag_features.py#L18) — **unsupported by design**

### src/zk_rfid/compat/nation/adapter.py

- **class** [`NationAdapter`](../src/zk_rfid/compat/nation/adapter.py#L16)
- **method** [`NationAdapter.open`](../src/zk_rfid/compat/nation/adapter.py#L20)
- **method** [`NationAdapter.close`](../src/zk_rfid/compat/nation/adapter.py#L23)
- **method** [`NationAdapter.get_sdk_info`](../src/zk_rfid/compat/nation/adapter.py#L26)
- **method** [`NationAdapter.Query_Reader_Information`](../src/zk_rfid/compat/nation/adapter.py#L31)
- **method** [`NationAdapter.query_rfid_ability`](../src/zk_rfid/compat/nation/adapter.py#L34)
- **method** [`NationAdapter.query_reader_power`](../src/zk_rfid/compat/nation/adapter.py#L37)
- **method** [`NationAdapter.configure_reader_power`](../src/zk_rfid/compat/nation/adapter.py#L41)
- **method** [`NationAdapter.build_antenna_mask`](../src/zk_rfid/compat/nation/adapter.py#L68)
- **method** [`NationAdapter.save_antenna_mask`](../src/zk_rfid/compat/nation/adapter.py#L75)
- **method** [`NationAdapter.query_enabled_ant_mask`](../src/zk_rfid/compat/nation/adapter.py#L78)
- **method** [`NationAdapter.enable_ant`](../src/zk_rfid/compat/nation/adapter.py#L98)
- **method** [`NationAdapter.disable_ant`](../src/zk_rfid/compat/nation/adapter.py#L101)
- **method** [`NationAdapter.is_inventory_running`](../src/zk_rfid/compat/nation/adapter.py#L104)
- **method** [`NationAdapter.start_inventory_with_mode`](../src/zk_rfid/compat/nation/adapter.py#L107)
- **method** [`NationAdapter.run_inventory`](../src/zk_rfid/compat/nation/adapter.py#L117)
- **method** [`NationAdapter.stop_inventory`](../src/zk_rfid/compat/nation/adapter.py#L140)
- **method** [`NationAdapter.write_epc_to_target_auto`](../src/zk_rfid/compat/nation/adapter.py#L143)
- **method** [`NationAdapter.select_profile`](../src/zk_rfid/compat/nation/adapter.py#L161)
- **method** [`NationAdapter.get_profile`](../src/zk_rfid/compat/nation/adapter.py#L168)
- **method** [`NationAdapter.query_rf_band`](../src/zk_rfid/compat/nation/adapter.py#L172)
- **method** [`NationAdapter.set_rf_band`](../src/zk_rfid/compat/nation/adapter.py#L176) — **unverified mapping; rejected explicitly**
- **method** [`NationAdapter.set_beeper`](../src/zk_rfid/compat/nation/adapter.py#L179)
- **method** [`NationAdapter.get_beeper`](../src/zk_rfid/compat/nation/adapter.py#L185) — **unsupported by design**
- **method** [`NationAdapter.set_filter_settings`](../src/zk_rfid/compat/nation/adapter.py#L188) — **unsupported by design**
- **method** [`NationAdapter.get_session`](../src/zk_rfid/compat/nation/adapter.py#L191)

### src/zk_rfid/compat/nation/mapping.py

- **class** [`Equivalence`](../src/zk_rfid/compat/nation/mapping.py#L9)
- **constant** [`Equivalence.VERIFIED`](../src/zk_rfid/compat/nation/mapping.py#L10)
- **constant** [`Equivalence.CONVERTED`](../src/zk_rfid/compat/nation/mapping.py#L11)
- **constant** [`Equivalence.MULTI_STEP`](../src/zk_rfid/compat/nation/mapping.py#L12)
- **constant** [`Equivalence.APPROXIMATE`](../src/zk_rfid/compat/nation/mapping.py#L13)
- **constant** [`Equivalence.UNSUPPORTED`](../src/zk_rfid/compat/nation/mapping.py#L14)
- **constant** [`Equivalence.UNVERIFIED`](../src/zk_rfid/compat/nation/mapping.py#L15)
- **constant** [`CONTRACT`](../src/zk_rfid/compat/nation/mapping.py#L18)
- **class** [`RFMapping`](../src/zk_rfid/compat/nation/mapping.py#L35)
- **method** [`RFMapping.require`](../src/zk_rfid/compat/nation/mapping.py#L43)
- **function** [`hex_epc`](../src/zk_rfid/compat/nation/mapping.py#L49)
- **function** [`power_dict`](../src/zk_rfid/compat/nation/mapping.py#L60)
- **function** [`tag_dict`](../src/zk_rfid/compat/nation/mapping.py#L64)
- **function** [`unsupported`](../src/zk_rfid/compat/nation/mapping.py#L88)

### src/zk_rfid/dispatcher.py

- **class** [`Dispatcher`](../src/zk_rfid/dispatcher.py#L27)
- **property** [`Dispatcher.pending_command`](../src/zk_rfid/dispatcher.py#L54)
- **method** [`Dispatcher.open`](../src/zk_rfid/dispatcher.py#L57)
- **method** [`Dispatcher.close`](../src/zk_rfid/dispatcher.py#L77)
- **method** [`Dispatcher.exchange`](../src/zk_rfid/dispatcher.py#L132)
- **method** [`Dispatcher.interrupt_answer`](../src/zk_rfid/dispatcher.py#L237)

### src/zk_rfid/errors.py

- **class** [`ZKError`](../src/zk_rfid/errors.py#L4)
- **class** [`ValidationError`](../src/zk_rfid/errors.py#L8)
- **class** [`ProtocolError`](../src/zk_rfid/errors.py#L12)
- **class** [`UnsupportedFeature`](../src/zk_rfid/errors.py#L16)
- **class** [`UnverifiedFeature`](../src/zk_rfid/errors.py#L20)
- **class** [`StateError`](../src/zk_rfid/errors.py#L24)
- **class** [`TransportError`](../src/zk_rfid/errors.py#L28)
- **class** [`ExchangeError`](../src/zk_rfid/errors.py#L32)
- **class** [`RequestTimeout`](../src/zk_rfid/errors.py#L41)
- **class** [`QueueOverflow`](../src/zk_rfid/errors.py#L45)
- **class** [`DeviceError`](../src/zk_rfid/errors.py#L49)
- **class** [`OperationError`](../src/zk_rfid/errors.py#L58)

### src/zk_rfid/events.py

- **class** [`TraceEvent`](../src/zk_rfid/events.py#L10)
- **class** [`TraceEmitter`](../src/zk_rfid/events.py#L24)
- **method** [`TraceEmitter.emit`](../src/zk_rfid/events.py#L33)

### src/zk_rfid/inventory_session.py

- **function** [`collect_answer`](../src/zk_rfid/inventory_session.py#L67)
- **function** [`collect_buffer`](../src/zk_rfid/inventory_session.py#L193)
- **class** [`InventorySession`](../src/zk_rfid/inventory_session.py#L247)
- **method** [`InventorySession.start`](../src/zk_rfid/inventory_session.py#L302)
- **method** [`InventorySession.stop`](../src/zk_rfid/inventory_session.py#L539)

### src/zk_rfid/measurements.py

- **constant** [`PHASE_CONVERSION`](../src/zk_rfid/measurements.py#L6)
- **constant** [`RSSI_SOURCE`](../src/zk_rfid/measurements.py#L7)
- **function** [`rssi_to_dbm`](../src/zk_rfid/measurements.py#L10)
- **function** [`phase_to_degrees`](../src/zk_rfid/measurements.py#L32)
- **function** [`phase_to_radians`](../src/zk_rfid/measurements.py#L47)

### src/zk_rfid/models.py

- **constant** [`T`](../src/zk_rfid/models.py#L8)
- **function** [`integer`](../src/zk_rfid/models.py#L11)
- **function** [`boolean`](../src/zk_rfid/models.py#L17)
- **function** [`octets`](../src/zk_rfid/models.py#L23)
- **class** [`MemoryBank`](../src/zk_rfid/models.py#L29)
- **constant** [`MemoryBank.RESERVED`](../src/zk_rfid/models.py#L30)
- **constant** [`MemoryBank.EPC`](../src/zk_rfid/models.py#L31)
- **constant** [`MemoryBank.TID`](../src/zk_rfid/models.py#L32)
- **constant** [`MemoryBank.USER`](../src/zk_rfid/models.py#L33)
- **class** [`Outcome`](../src/zk_rfid/models.py#L36)
- **constant** [`Outcome.SUCCESS`](../src/zk_rfid/models.py#L37)
- **constant** [`Outcome.FAILURE`](../src/zk_rfid/models.py#L38)
- **constant** [`Outcome.PARTIAL`](../src/zk_rfid/models.py#L39)
- **constant** [`Outcome.UNKNOWN`](../src/zk_rfid/models.py#L40)
- **class** [`Confirmation`](../src/zk_rfid/models.py#L43)
- **constant** [`Confirmation.NONE`](../src/zk_rfid/models.py#L44)
- **constant** [`Confirmation.TRANSMITTED`](../src/zk_rfid/models.py#L45)
- **constant** [`Confirmation.ACKNOWLEDGED`](../src/zk_rfid/models.py#L46)
- **constant** [`Confirmation.READ_BACK`](../src/zk_rfid/models.py#L47)
- **class** [`ReaderState`](../src/zk_rfid/models.py#L50)
- **constant** [`ReaderState.DISCONNECTED`](../src/zk_rfid/models.py#L51)
- **constant** [`ReaderState.IDLE`](../src/zk_rfid/models.py#L52)
- **constant** [`ReaderState.STARTING`](../src/zk_rfid/models.py#L53)
- **constant** [`ReaderState.INVENTORYING`](../src/zk_rfid/models.py#L54)
- **constant** [`ReaderState.STOPPING`](../src/zk_rfid/models.py#L55)
- **constant** [`ReaderState.UNKNOWN`](../src/zk_rfid/models.py#L56)
- **class** [`InventoryMode`](../src/zk_rfid/models.py#L59)
- **constant** [`InventoryMode.ANSWER`](../src/zk_rfid/models.py#L60)
- **constant** [`InventoryMode.SCENARIO`](../src/zk_rfid/models.py#L61)
- **constant** [`InventoryMode.REAL_TIME`](../src/zk_rfid/models.py#L62)
- **class** [`InventoryData`](../src/zk_rfid/models.py#L65)
- **constant** [`InventoryData.EPC`](../src/zk_rfid/models.py#L66)
- **constant** [`InventoryData.TID`](../src/zk_rfid/models.py#L67)
- **constant** [`InventoryData.FAST_ID`](../src/zk_rfid/models.py#L68)
- **constant** [`InventoryData.MIX`](../src/zk_rfid/models.py#L69)
- **class** [`WorkingMode`](../src/zk_rfid/models.py#L72)
- **constant** [`WorkingMode.ANSWER`](../src/zk_rfid/models.py#L73)
- **constant** [`WorkingMode.REAL_TIME`](../src/zk_rfid/models.py#L74)
- **constant** [`WorkingMode.TRIGGER`](../src/zk_rfid/models.py#L75)
- **class** [`LockTarget`](../src/zk_rfid/models.py#L78)
- **constant** [`LockTarget.KILL_PASSWORD`](../src/zk_rfid/models.py#L79)
- **constant** [`LockTarget.ACCESS_PASSWORD`](../src/zk_rfid/models.py#L80)
- **constant** [`LockTarget.EPC`](../src/zk_rfid/models.py#L81)
- **constant** [`LockTarget.TID`](../src/zk_rfid/models.py#L82)
- **constant** [`LockTarget.USER`](../src/zk_rfid/models.py#L83)
- **class** [`LockProtection`](../src/zk_rfid/models.py#L86)
- **constant** [`LockProtection.UNLOCK`](../src/zk_rfid/models.py#L87)
- **constant** [`LockProtection.PERMANENT_UNLOCK`](../src/zk_rfid/models.py#L88)
- **constant** [`LockProtection.PASSWORD`](../src/zk_rfid/models.py#L89)
- **constant** [`LockProtection.PERMANENT_LOCK`](../src/zk_rfid/models.py#L90)
- **class** [`TagMask`](../src/zk_rfid/models.py#L94)
- **method** [`TagMask.encode`](../src/zk_rfid/models.py#L111)
- **class** [`TagTarget`](../src/zk_rfid/models.py#L121)
- **class** [`CommandResult`](../src/zk_rfid/models.py#L139)
- **property** [`CommandResult.ok`](../src/zk_rfid/models.py#L152)
- **method** [`CommandResult.require_success`](../src/zk_rfid/models.py#L155)
- **class** [`ReaderInfo`](../src/zk_rfid/models.py#L162)
- **class** [`InventoryConfig`](../src/zk_rfid/models.py#L177)
- **class** [`TagReport`](../src/zk_rfid/models.py#L197)
- **class** [`InventoryStatistics`](../src/zk_rfid/models.py#L230)
- **class** [`Heartbeat`](../src/zk_rfid/models.py#L237)
- **class** [`InventoryOutcome`](../src/zk_rfid/models.py#L244)
- **property** [`InventoryOutcome.unique_count`](../src/zk_rfid/models.py#L256)
- **class** [`Region`](../src/zk_rfid/models.py#L261)
- **class** [`GPIOState`](../src/zk_rfid/models.py#L268)
- **class** [`RealTimeConfig`](../src/zk_rfid/models.py#L276)
- **class** [`WorkingModeConfig`](../src/zk_rfid/models.py#L288)
- **class** [`BufferCounts`](../src/zk_rfid/models.py#L294)
- **class** [`WritePower`](../src/zk_rfid/models.py#L300)
- **class** [`QueryParameters`](../src/zk_rfid/models.py#L306)
- **class** [`ScanParameters`](../src/zk_rfid/models.py#L313)
- **class** [`TIDParameters`](../src/zk_rfid/models.py#L320)
- **class** [`ParserDiagnostics`](../src/zk_rfid/models.py#L326)

### src/zk_rfid/profiles.py

- **class** [`RFProfile`](../src/zk_rfid/profiles.py#L12)
- **constant** [`PROFILES`](../src/zk_rfid/profiles.py#L22)
- **function** [`get_profile_definition`](../src/zk_rfid/profiles.py#L80)

### src/zk_rfid/protocol/constants.py

- **constant** [`CRC16_INIT`](../src/zk_rfid/protocol/constants.py#L5)
- **constant** [`CRC16_POLY`](../src/zk_rfid/protocol/constants.py#L6)
- **constant** [`MAX_COMMAND_DATA`](../src/zk_rfid/protocol/constants.py#L7)
- **constant** [`MAX_RESPONSE_DATA`](../src/zk_rfid/protocol/constants.py#L8)
- **constant** [`BROADCAST_ADDRESS`](../src/zk_rfid/protocol/constants.py#L9)
- **class** [`Command`](../src/zk_rfid/protocol/constants.py#L12)
- **constant** [`Command.INVENTORY`](../src/zk_rfid/protocol/constants.py#L13)
- **constant** [`Command.READ_MEMORY`](../src/zk_rfid/protocol/constants.py#L14)
- **constant** [`Command.WRITE_MEMORY`](../src/zk_rfid/protocol/constants.py#L15)
- **constant** [`Command.WRITE_EPC`](../src/zk_rfid/protocol/constants.py#L16)
- **constant** [`Command.KILL`](../src/zk_rfid/protocol/constants.py#L17)
- **constant** [`Command.LOCK`](../src/zk_rfid/protocol/constants.py#L18)
- **constant** [`Command.BLOCK_ERASE`](../src/zk_rfid/protocol/constants.py#L19)
- **constant** [`Command.SINGLE_INVENTORY`](../src/zk_rfid/protocol/constants.py#L20)
- **constant** [`Command.BLOCK_WRITE`](../src/zk_rfid/protocol/constants.py#L21)
- **constant** [`Command.READ_MEMORY_EXTENDED`](../src/zk_rfid/protocol/constants.py#L22)
- **constant** [`Command.WRITE_MEMORY_EXTENDED`](../src/zk_rfid/protocol/constants.py#L23)
- **constant** [`Command.BUFFER_INVENTORY`](../src/zk_rfid/protocol/constants.py#L24)
- **constant** [`Command.MIX_INVENTORY`](../src/zk_rfid/protocol/constants.py#L25)
- **constant** [`Command.INVENTORY_EPC`](../src/zk_rfid/protocol/constants.py#L26)
- **constant** [`Command.READER_INFO`](../src/zk_rfid/protocol/constants.py#L27)
- **constant** [`Command.SET_REGION`](../src/zk_rfid/protocol/constants.py#L28)
- **constant** [`Command.SET_ADDRESS`](../src/zk_rfid/protocol/constants.py#L29)
- **constant** [`Command.SET_SCAN_TIME`](../src/zk_rfid/protocol/constants.py#L30)
- **constant** [`Command.SET_BAUDRATE`](../src/zk_rfid/protocol/constants.py#L31)
- **constant** [`Command.SET_POWER`](../src/zk_rfid/protocol/constants.py#L32)
- **constant** [`Command.INDICATOR`](../src/zk_rfid/protocol/constants.py#L33)
- **constant** [`Command.SET_ANTENNAS`](../src/zk_rfid/protocol/constants.py#L34)
- **constant** [`Command.SET_BUZZER`](../src/zk_rfid/protocol/constants.py#L35)
- **constant** [`Command.SET_GPIO`](../src/zk_rfid/protocol/constants.py#L36)
- **constant** [`Command.GET_GPIO`](../src/zk_rfid/protocol/constants.py#L37)
- **constant** [`Command.SERIAL_NUMBER`](../src/zk_rfid/protocol/constants.py#L38)
- **constant** [`Command.FAST_START`](../src/zk_rfid/protocol/constants.py#L39)
- **constant** [`Command.FAST_STOP`](../src/zk_rfid/protocol/constants.py#L40)
- **constant** [`Command.SET_ANTENNA_CHECK`](../src/zk_rfid/protocol/constants.py#L41)
- **constant** [`Command.SET_INTERFACE`](../src/zk_rfid/protocol/constants.py#L42)
- **constant** [`Command.RETURN_LOSS_THRESHOLD`](../src/zk_rfid/protocol/constants.py#L43)
- **constant** [`Command.SET_BUFFER_LENGTH`](../src/zk_rfid/protocol/constants.py#L44)
- **constant** [`Command.GET_BUFFER_LENGTH`](../src/zk_rfid/protocol/constants.py#L45)
- **constant** [`Command.READ_BUFFER`](../src/zk_rfid/protocol/constants.py#L46)
- **constant** [`Command.CLEAR_BUFFER`](../src/zk_rfid/protocol/constants.py#L47)
- **constant** [`Command.BUFFER_COUNT`](../src/zk_rfid/protocol/constants.py#L48)
- **constant** [`Command.SET_REAL_TIME`](../src/zk_rfid/protocol/constants.py#L49)
- **constant** [`Command.SET_WORKING_MODE`](../src/zk_rfid/protocol/constants.py#L50)
- **constant** [`Command.GET_WORKING_MODE`](../src/zk_rfid/protocol/constants.py#L51)
- **constant** [`Command.HEARTBEAT`](../src/zk_rfid/protocol/constants.py#L52)
- **constant** [`Command.SET_WRITE_POWER`](../src/zk_rfid/protocol/constants.py#L53)
- **constant** [`Command.GET_WRITE_POWER`](../src/zk_rfid/protocol/constants.py#L54)
- **constant** [`Command.WRITE_RETRIES`](../src/zk_rfid/protocol/constants.py#L55)
- **constant** [`Command.PROFILE`](../src/zk_rfid/protocol/constants.py#L56)
- **constant** [`Command.DRM`](../src/zk_rfid/protocol/constants.py#L57)
- **constant** [`Command.RETURN_LOSS`](../src/zk_rfid/protocol/constants.py#L58)
- **constant** [`Command.TEMPERATURE`](../src/zk_rfid/protocol/constants.py#L59)
- **constant** [`Command.STOP_INVENTORY`](../src/zk_rfid/protocol/constants.py#L60)
- **constant** [`Command.GET_POWER`](../src/zk_rfid/protocol/constants.py#L61)
- **constant** [`Command.SELECT`](../src/zk_rfid/protocol/constants.py#L62)
- **constant** [`Command.GET_REGION`](../src/zk_rfid/protocol/constants.py#L63)
- **constant** [`Command.SET_CONFIG`](../src/zk_rfid/protocol/constants.py#L64)
- **constant** [`Command.GET_CONFIG`](../src/zk_rfid/protocol/constants.py#L65)
- **constant** [`Command.TAG_REPORT`](../src/zk_rfid/protocol/constants.py#L66)
- **class** [`ConfigID`](../src/zk_rfid/protocol/constants.py#L69)
- **constant** [`ConfigID.SCAN`](../src/zk_rfid/protocol/constants.py#L70)
- **constant** [`ConfigID.TAG_FOCUS`](../src/zk_rfid/protocol/constants.py#L71)
- **constant** [`ConfigID.QUERY`](../src/zk_rfid/protocol/constants.py#L72)
- **constant** [`ConfigID.TID`](../src/zk_rfid/protocol/constants.py#L73)
- **constant** [`ConfigID.MASK`](../src/zk_rfid/protocol/constants.py#L74)
- **constant** [`ConfigID.IMPINJ_SCAN`](../src/zk_rfid/protocol/constants.py#L75)
- **constant** [`ConfigID.IMPINJ_SCAN_ID`](../src/zk_rfid/protocol/constants.py#L76)
- **constant** [`ConfigID.CUSTOM_PROFILES`](../src/zk_rfid/protocol/constants.py#L77)

### src/zk_rfid/protocol/crc.py

- **function** [`crc16`](../src/zk_rfid/protocol/crc.py#L6)
- **function** [`append_crc`](../src/zk_rfid/protocol/crc.py#L15)

### src/zk_rfid/protocol/frame.py

- **class** [`ResponseFrame`](../src/zk_rfid/protocol/frame.py#L10)
- **function** [`encode_command`](../src/zk_rfid/protocol/frame.py#L18)
- **function** [`decode_response`](../src/zk_rfid/protocol/frame.py#L25)

### src/zk_rfid/protocol/parser.py

- **class** [`FrameParser`](../src/zk_rfid/protocol/parser.py#L8)
- **method** [`FrameParser.reset`](../src/zk_rfid/protocol/parser.py#L14)
- **method** [`FrameParser.feed`](../src/zk_rfid/protocol/parser.py#L17)

### src/zk_rfid/protocol/status.py

- **constant** [`STATUS_NAMES`](../src/zk_rfid/protocol/status.py#L6)
- **class** [`StatusInfo`](../src/zk_rfid/protocol/status.py#L35)
- **function** [`interpret_status`](../src/zk_rfid/protocol/status.py#L43)

### src/zk_rfid/reader.py

- **constant** [`T`](../src/zk_rfid/reader.py#L66)
- **class** [`ZKReader`](../src/zk_rfid/reader.py#L69)
- **property** [`ZKReader.state`](../src/zk_rfid/reader.py#L92)
- **property** [`ZKReader.address`](../src/zk_rfid/reader.py#L106)
- **property** [`ZKReader.is_inventory_running`](../src/zk_rfid/reader.py#L111)
- **method** [`ZKReader.get_capabilities`](../src/zk_rfid/reader.py#L115)
- **method** [`ZKReader.open`](../src/zk_rfid/reader.py#L154)
- **method** [`ZKReader.close`](../src/zk_rfid/reader.py#L163)
- **method** [`ZKReader.get_reader_info`](../src/zk_rfid/reader.py#L271)
- **method** [`ZKReader.get_serial_number`](../src/zk_rfid/reader.py#L279)
- **method** [`ZKReader.get_power`](../src/zk_rfid/reader.py#L283)
- **method** [`ZKReader.set_power`](../src/zk_rfid/reader.py#L287)
- **method** [`ZKReader.get_write_power`](../src/zk_rfid/reader.py#L295)
- **method** [`ZKReader.set_write_power`](../src/zk_rfid/reader.py#L299)
- **method** [`ZKReader.get_write_retries`](../src/zk_rfid/reader.py#L303)
- **method** [`ZKReader.set_write_retries`](../src/zk_rfid/reader.py#L307)
- **method** [`ZKReader.set_antennas`](../src/zk_rfid/reader.py#L311)
- **method** [`ZKReader.get_antennas`](../src/zk_rfid/reader.py#L317)
- **method** [`ZKReader.set_antenna_check`](../src/zk_rfid/reader.py#L324)
- **method** [`ZKReader.get_antenna_check`](../src/zk_rfid/reader.py#L328)
- **method** [`ZKReader.set_address`](../src/zk_rfid/reader.py#L333)
- **method** [`ZKReader.set_baudrate`](../src/zk_rfid/reader.py#L342)
- **method** [`ZKReader.set_inventory_time`](../src/zk_rfid/reader.py#L362)
- **method** [`ZKReader.set_interface`](../src/zk_rfid/reader.py#L366)
- **method** [`ZKReader.get_region`](../src/zk_rfid/reader.py#L370)
- **method** [`ZKReader.set_region`](../src/zk_rfid/reader.py#L374)
- **method** [`ZKReader.get_profile`](../src/zk_rfid/reader.py#L380)
- **method** [`ZKReader.set_profile`](../src/zk_rfid/reader.py#L384)
- **method** [`ZKReader.get_drm`](../src/zk_rfid/reader.py#L392)
- **method** [`ZKReader.set_drm`](../src/zk_rfid/reader.py#L396)
- **method** [`ZKReader.set_buzzer`](../src/zk_rfid/reader.py#L400)
- **method** [`ZKReader.pulse_indicator`](../src/zk_rfid/reader.py#L404)
- **method** [`ZKReader.get_gpio`](../src/zk_rfid/reader.py#L410)
- **method** [`ZKReader.set_gpio`](../src/zk_rfid/reader.py#L415)
- **method** [`ZKReader.get_temperature`](../src/zk_rfid/reader.py#L420)
- **method** [`ZKReader.measure_return_loss`](../src/zk_rfid/reader.py#L425)
- **method** [`ZKReader.get_return_loss_threshold`](../src/zk_rfid/reader.py#L433)
- **method** [`ZKReader.set_return_loss_threshold`](../src/zk_rfid/reader.py#L437)
- **method** [`ZKReader.get_config`](../src/zk_rfid/reader.py#L441)
- **method** [`ZKReader.set_config`](../src/zk_rfid/reader.py#L450)
- **method** [`ZKReader.get_scan_parameters`](../src/zk_rfid/reader.py#L466)
- **method** [`ZKReader.set_scan_parameters`](../src/zk_rfid/reader.py#L470)
- **method** [`ZKReader.get_tag_focus`](../src/zk_rfid/reader.py#L476)
- **method** [`ZKReader.set_tag_focus`](../src/zk_rfid/reader.py#L480)
- **method** [`ZKReader.get_query_parameters`](../src/zk_rfid/reader.py#L484)
- **method** [`ZKReader.set_query_parameters`](../src/zk_rfid/reader.py#L488)
- **method** [`ZKReader.get_tid_parameters`](../src/zk_rfid/reader.py#L494)
- **method** [`ZKReader.set_tid_parameters`](../src/zk_rfid/reader.py#L498)
- **method** [`ZKReader.get_inventory_mask`](../src/zk_rfid/reader.py#L504)
- **method** [`ZKReader.set_inventory_mask`](../src/zk_rfid/reader.py#L508)
- **method** [`ZKReader.get_custom_profiles`](../src/zk_rfid/reader.py#L515)
- **method** [`ZKReader.set_custom_profiles`](../src/zk_rfid/reader.py#L519)
- **method** [`ZKReader.set_real_time_config`](../src/zk_rfid/reader.py#L525)
- **method** [`ZKReader.get_working_mode`](../src/zk_rfid/reader.py#L530)
- **method** [`ZKReader.set_working_mode`](../src/zk_rfid/reader.py#L537)
- **method** [`ZKReader.get_heartbeat_interval`](../src/zk_rfid/reader.py#L546)
- **method** [`ZKReader.set_heartbeat_interval`](../src/zk_rfid/reader.py#L550)
- **method** [`ZKReader.get_buffer_length`](../src/zk_rfid/reader.py#L554)
- **method** [`ZKReader.set_buffer_length`](../src/zk_rfid/reader.py#L558)
- **method** [`ZKReader.get_buffer_count`](../src/zk_rfid/reader.py#L562)
- **method** [`ZKReader.clear_buffer`](../src/zk_rfid/reader.py#L566)
- **method** [`ZKReader.inventory_to_buffer`](../src/zk_rfid/reader.py#L570)
- **method** [`ZKReader.read_buffer`](../src/zk_rfid/reader.py#L582)
- **method** [`ZKReader.inventory_once`](../src/zk_rfid/reader.py#L590)
- **method** [`ZKReader.inventory_single`](../src/zk_rfid/reader.py#L600)
- **method** [`ZKReader.inventory_matching_epc`](../src/zk_rfid/reader.py#L608)
- **method** [`ZKReader.start_inventory`](../src/zk_rfid/reader.py#L625)
- **method** [`ZKReader.stop_inventory`](../src/zk_rfid/reader.py#L640)
- **method** [`ZKReader.read_memory`](../src/zk_rfid/reader.py#L654)
- **method** [`ZKReader.write_memory`](../src/zk_rfid/reader.py#L693)
- **method** [`ZKReader.write_epc`](../src/zk_rfid/reader.py#L774)
- **method** [`ZKReader.write_epc_single`](../src/zk_rfid/reader.py#L846)
- **method** [`ZKReader.set_access_password`](../src/zk_rfid/reader.py#L854)
- **method** [`ZKReader.set_kill_password`](../src/zk_rfid/reader.py#L874)
- **method** [`ZKReader.lock_tag`](../src/zk_rfid/reader.py#L893)
- **method** [`ZKReader.kill_tag`](../src/zk_rfid/reader.py#L908)
- **method** [`ZKReader.block_write`](../src/zk_rfid/reader.py#L912)
- **method** [`ZKReader.block_erase`](../src/zk_rfid/reader.py#L928)
- **method** [`ZKReader.select_tag`](../src/zk_rfid/reader.py#L944)

### src/zk_rfid/transports/base.py

- **class** [`AsyncTransport`](../src/zk_rfid/transports/base.py#L7) — **transport interface contract**
- **method** [`AsyncTransport.open`](../src/zk_rfid/transports/base.py#L8) — **transport interface contract**
- **method** [`AsyncTransport.close`](../src/zk_rfid/transports/base.py#L9) — **transport interface contract**
- **method** [`AsyncTransport.read`](../src/zk_rfid/transports/base.py#L10) — **transport interface contract**
- **method** [`AsyncTransport.write`](../src/zk_rfid/transports/base.py#L11) — **transport interface contract**

### src/zk_rfid/transports/serial.py

- **class** [`SerialTransport`](../src/zk_rfid/transports/serial.py#L8)
- **method** [`SerialTransport.open`](../src/zk_rfid/transports/serial.py#L19)
- **method** [`SerialTransport.read`](../src/zk_rfid/transports/serial.py#L52)
- **method** [`SerialTransport.write`](../src/zk_rfid/transports/serial.py#L66)
- **method** [`SerialTransport.set_baudrate`](../src/zk_rfid/transports/serial.py#L74)
- **method** [`SerialTransport.close`](../src/zk_rfid/transports/serial.py#L80)
