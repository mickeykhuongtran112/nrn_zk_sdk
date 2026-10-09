# Danh mục chức năng Python đã triển khai

Sinh từ AST bằng `python tools/export_symbols.py`. Tên, chữ ký và dòng nguồn lấy trực tiếp từ implementation.

Mức chứng cứ: manual V2.25/demo V6.8, unit/integration và runtime CPython/Pyodide. **Chưa nghiệm thu toàn bộ phần cứng.** Người dùng đã báo 3 hardware tests PASS qua ảnh trên COM13/115200; xem [phạm vi chứng cứ](demo_and_parity.md). Các giới hạn ở [ma trận hỗ trợ](supported_devices.md) và [errata](protocol/errata.md).

## API điều khiển ZKReader (77 symbol public)

| Function/property | Chức năng | Implementation |
|---|---|---|
| `ZKReader.state` | Host lifecycle state; IDLE alone does not prove a saved real-time mode is off. | [src/zk_rfid.py:3104](../src/zk_rfid.py#L3104) |
| `ZKReader.address` | Current wire address; changes only after an acknowledged address update. | [src/zk_rfid.py:3118](../src/zk_rfid.py#L3118) |
| `ZKReader.is_inventory_running` | Whether this host owns an active or transitioning inventory session. | [src/zk_rfid.py:3123](../src/zk_rfid.py#L3123) |
| `ZKReader.get_capabilities` | Return declared capabilities and their evidence; no hardware probing. | [src/zk_rfid.py:3127](../src/zk_rfid.py#L3127) |
| `ZKReader.open` | Open transport and start the single RX task; recover requires a known clean boundary. | [src/zk_rfid.py:3166](../src/zk_rfid.py#L3166) |
| `ZKReader.close` | Stop owned inventory, close transport and join background tasks. | [src/zk_rfid.py:3175](../src/zk_rfid.py#L3175) |
| `ZKReader.get_reader_info` | Read native reader identity, RF configuration and antenna-check state (0x21). | [src/zk_rfid.py:3283](../src/zk_rfid.py#L3283) |
| `ZKReader.get_serial_number` | Read the four-byte reader serial number (0x4C). | [src/zk_rfid.py:3291](../src/zk_rfid.py#L3291) |
| `ZKReader.get_power` | Read one integer dBm value per declared antenna (0x94). | [src/zk_rfid.py:3295](../src/zk_rfid.py#L3295) |
| `ZKReader.set_power` | Set 0..30 dBm globally or per antenna; volatile unless persist=True (0x2F). | [src/zk_rfid.py:3299](../src/zk_rfid.py#L3299) |
| `ZKReader.get_write_power` | Get write power. Returns native status and confirmation. | [src/zk_rfid.py:3307](../src/zk_rfid.py#L3307) |
| `ZKReader.set_write_power` | Set separate write power in dBm, or None to disable it (0x79). | [src/zk_rfid.py:3311](../src/zk_rfid.py#L3311) |
| `ZKReader.get_write_retries` | Get write retries. Returns native status and confirmation. | [src/zk_rfid.py:3315](../src/zk_rfid.py#L3315) |
| `ZKReader.set_write_retries` | Set the module retry count 0..7; the host never retries writes (0x7B). | [src/zk_rfid.py:3319](../src/zk_rfid.py#L3319) |
| `ZKReader.set_antennas` | Select antenna mask with bit0=port1; volatile unless persist=True (0x3F). | [src/zk_rfid.py:3323](../src/zk_rfid.py#L3323) |
| `ZKReader.get_antennas` | Get the native antenna mask; the 16-port getter remains unverified. | [src/zk_rfid.py:3329](../src/zk_rfid.py#L3329) |
| `ZKReader.set_antenna_check` | Set antenna check. Returns native status and confirmation. | [src/zk_rfid.py:3336](../src/zk_rfid.py#L3336) |
| `ZKReader.get_antenna_check` | Get antenna check. Returns native status and confirmation. | [src/zk_rfid.py:3340](../src/zk_rfid.py#L3340) |
| `ZKReader.set_address` | Change reader address after receiving the ACK at the original address (0x24). | [src/zk_rfid.py:3345](../src/zk_rfid.py#L3345) |
| `ZKReader.set_baudrate` | Receive ACK at the old baud, then switch the transport baud (0x28). | [src/zk_rfid.py:3354](../src/zk_rfid.py#L3354) |
| `ZKReader.set_inventory_time` | Set native scan time in 100 ms units: 0 or 3..255 (0x25). | [src/zk_rfid.py:3374](../src/zk_rfid.py#L3374) |
| `ZKReader.set_interface` | Select usb or uart (0x6A); effective after a module power cycle. | [src/zk_rfid.py:3378](../src/zk_rfid.py#L3378) |
| `ZKReader.get_region` | Get region. Returns native status and confirmation. | [src/zk_rfid.py:3382](../src/zk_rfid.py#L3382) |
| `ZKReader.set_region` | Set native region and channel indices; no NATION region-ID conversion (0x22). | [src/zk_rfid.py:3386](../src/zk_rfid.py#L3386) |
| `ZKReader.get_profile` | Read native RF profile ID, including the 16-bit Ex10 format (0x7F). | [src/zk_rfid.py:3392](../src/zk_rfid.py#L3392) |
| `ZKReader.set_profile` | Set native RF profile ID; no inferred equivalence with NATION profiles (0x7F). | [src/zk_rfid.py:3396](../src/zk_rfid.py#L3396) |
| `ZKReader.get_drm` | Get drm. Returns native status and confirmation. | [src/zk_rfid.py:3402](../src/zk_rfid.py#L3402) |
| `ZKReader.set_drm` | Set drm. Returns native status and confirmation. | [src/zk_rfid.py:3406](../src/zk_rfid.py#L3406) |
| `ZKReader.set_buzzer` | Set buzzer. Returns native status and confirmation. | [src/zk_rfid.py:3410](../src/zk_rfid.py#L3410) |
| `ZKReader.pulse_indicator` | Pulse LED/buzzer using 50 ms active/silent units (0x33). | [src/zk_rfid.py:3414](../src/zk_rfid.py#L3414) |
| `ZKReader.get_gpio` | Read input and output bits in the documented GPIO layout (0x47). | [src/zk_rfid.py:3420](../src/zk_rfid.py#L3420) |
| `ZKReader.set_gpio` | Set the two documented GPO outputs (0x46). | [src/zk_rfid.py:3425](../src/zk_rfid.py#L3425) |
| `ZKReader.get_temperature` | Read signed integer Celsius using the native sign byte (0x92). | [src/zk_rfid.py:3430](../src/zk_rfid.py#L3430) |
| `ZKReader.measure_return_loss` | Measure return loss at a documented grid frequency in kHz (0x91). | [src/zk_rfid.py:3435](../src/zk_rfid.py#L3435) |
| `ZKReader.get_return_loss_threshold` | Get return loss threshold. Returns native status and confirmation. | [src/zk_rfid.py:3441](../src/zk_rfid.py#L3441) |
| `ZKReader.set_return_loss_threshold` | Set return loss threshold. Returns native status and confirmation. | [src/zk_rfid.py:3445](../src/zk_rfid.py#L3445) |
| `ZKReader.get_config` | Read an Ex10 CFG value; decoded=False preserves the exact native bytes (0xEB). | [src/zk_rfid.py:3449](../src/zk_rfid.py#L3449) |
| `ZKReader.set_config` | Validate and set Ex10 CFG; ambiguous CFG25/29 require an explicit dialect (0xEA). | [src/zk_rfid.py:3458](../src/zk_rfid.py#L3458) |
| `ZKReader.get_scan_parameters` | Get scan parameters. Returns native status and confirmation. | [src/zk_rfid.py:3474](../src/zk_rfid.py#L3474) |
| `ZKReader.set_scan_parameters` | Set scan parameters. Returns native status and confirmation. | [src/zk_rfid.py:3478](../src/zk_rfid.py#L3478) |
| `ZKReader.get_tag_focus` | Get tag focus. Returns native status and confirmation. | [src/zk_rfid.py:3484](../src/zk_rfid.py#L3484) |
| `ZKReader.set_tag_focus` | Set tag focus. Returns native status and confirmation. | [src/zk_rfid.py:3488](../src/zk_rfid.py#L3488) |
| `ZKReader.get_query_parameters` | Get query parameters. Returns native status and confirmation. | [src/zk_rfid.py:3492](../src/zk_rfid.py#L3492) |
| `ZKReader.set_query_parameters` | Set query parameters. Returns native status and confirmation. | [src/zk_rfid.py:3496](../src/zk_rfid.py#L3496) |
| `ZKReader.get_tid_parameters` | Get tid parameters. Returns native status and confirmation. | [src/zk_rfid.py:3502](../src/zk_rfid.py#L3502) |
| `ZKReader.set_tid_parameters` | Set tid parameters. Returns native status and confirmation. | [src/zk_rfid.py:3506](../src/zk_rfid.py#L3506) |
| `ZKReader.get_inventory_mask` | Get inventory mask. Returns native status and confirmation. | [src/zk_rfid.py:3512](../src/zk_rfid.py#L3512) |
| `ZKReader.set_inventory_mask` | Set inventory mask. Returns native status and confirmation. | [src/zk_rfid.py:3516](../src/zk_rfid.py#L3516) |
| `ZKReader.get_custom_profiles` | Get custom profiles. Returns native status and confirmation. | [src/zk_rfid.py:3523](../src/zk_rfid.py#L3523) |
| `ZKReader.set_custom_profiles` | Set custom profiles. Returns native status and confirmation. | [src/zk_rfid.py:3527](../src/zk_rfid.py#L3527) |
| `ZKReader.set_real_time_config` | Persist the dedicated 0x75 real-time settings; separate from Scenario CFG. | [src/zk_rfid.py:3533](../src/zk_rfid.py#L3533) |
| `ZKReader.get_working_mode` | Read the 0x77 mode and fixed-width saved real-time configuration. | [src/zk_rfid.py:3538](../src/zk_rfid.py#L3538) |
| `ZKReader.set_working_mode` | Persistent mode setting. For managed 0xEE delivery use start_inventory(). | [src/zk_rfid.py:3545](../src/zk_rfid.py#L3545) |
| `ZKReader.get_heartbeat_interval` | Get heartbeat interval. Returns native status and confirmation. | [src/zk_rfid.py:3554](../src/zk_rfid.py#L3554) |
| `ZKReader.set_heartbeat_interval` | Set heartbeat interval in 30 second units, with 0 disabling it (0x78). | [src/zk_rfid.py:3558](../src/zk_rfid.py#L3558) |
| `ZKReader.get_buffer_length` | Get buffer length. Returns native status and confirmation. | [src/zk_rfid.py:3562](../src/zk_rfid.py#L3562) |
| `ZKReader.set_buffer_length` | Set maximum stored EPC/TID length to 16 or 62 bytes; clears the buffer (0x70). | [src/zk_rfid.py:3566](../src/zk_rfid.py#L3566) |
| `ZKReader.get_buffer_count` | Get buffer count. Returns native status and confirmation. | [src/zk_rfid.py:3570](../src/zk_rfid.py#L3570) |
| `ZKReader.clear_buffer` | Clear the reader tag buffer (0x73). | [src/zk_rfid.py:3574](../src/zk_rfid.py#L3574) |
| `ZKReader.inventory_to_buffer` | Run buffered inventory and return counts; this changes reader buffer contents (0x18). | [src/zk_rfid.py:3578](../src/zk_rfid.py#L3578) |
| `ZKReader.read_buffer` | Collect all 0x72 frames; preserve partial reports and enforce one overall deadline. | [src/zk_rfid.py:3588](../src/zk_rfid.py#L3588) |
| `ZKReader.inventory_once` | Run one Answer/Mix round, preserving reports on partial completion or timeout. | [src/zk_rfid.py:3595](../src/zk_rfid.py#L3595) |
| `ZKReader.inventory_single` | Run native single-tag inventory (0x0F). | [src/zk_rfid.py:3604](../src/zk_rfid.py#L3604) |
| `ZKReader.inventory_matching_epc` | Run native EPC-bit-match inventory with explicit bit offset and length (0x1A). | [src/zk_rfid.py:3611](../src/zk_rfid.py#L3611) |
| `ZKReader.start_inventory` | Start a managed async report iterator; stop explicitly or use its context manager. | [src/zk_rfid.py:3627](../src/zk_rfid.py#L3627) |
| `ZKReader.stop_inventory` | Stop by mode-specific semantics; 0x93 has no ACK of its own. | [src/zk_rfid.py:3641](../src/zk_rfid.py#L3641) |
| `ZKReader.read_memory` | Read 1..120 16-bit words; choose extended address format automatically when needed. | [src/zk_rfid.py:3655](../src/zk_rfid.py#L3655) |
| `ZKReader.write_memory` | Write 1..32 words once, optionally verify using a stable post-write target. | [src/zk_rfid.py:3694](../src/zk_rfid.py#L3694) |
| `ZKReader.write_epc` | Read PC, preserve non-length bits, then one targeted PC+EPC write. | [src/zk_rfid.py:3775](../src/zk_rfid.py#L3775) |
| `ZKReader.write_epc_single` | Native 0x04. Requires exactly one tag physically in the RF field. | [src/zk_rfid.py:3845](../src/zk_rfid.py#L3845) |
| `ZKReader.set_access_password` | Write the 32-bit Access password, then verify using the new password if requested. | [src/zk_rfid.py:3851](../src/zk_rfid.py#L3851) |
| `ZKReader.set_kill_password` | Write the 32-bit Kill password; does not execute Kill or Lock. | [src/zk_rfid.py:3871](../src/zk_rfid.py#L3871) |
| `ZKReader.lock_tag` | Apply native Gen2 protection to a specified target; permanent states are irreversible. | [src/zk_rfid.py:3890](../src/zk_rfid.py#L3890) |
| `ZKReader.kill_tag` | Execute irreversible Gen2 Kill on an explicit target with a nonzero 32-bit password. | [src/zk_rfid.py:3903](../src/zk_rfid.py#L3903) |
| `ZKReader.block_write` | Use native BlockWrite within its independent frame budget; tag support is required. | [src/zk_rfid.py:3907](../src/zk_rfid.py#L3907) |
| `ZKReader.block_erase` | Erase 1..120 words using native BlockErase; tag support is required. | [src/zk_rfid.py:3923](../src/zk_rfid.py#L3923) |
| `ZKReader.select_tag` | Apply native Gen2 Select using a bit-addressed mask, target, action and antenna mask. | [src/zk_rfid.py:3939](../src/zk_rfid.py#L3939) |

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

## Symbols trong file SDK duy nhất

Bao gồm class, method, function và constant; mục vendor-tag được đánh dấu ngoài scope.


### src/zk_rfid.py

- **constant** [`SDK_NAME`](../src/zk_rfid.py#L34)
- **constant** [`SDK_VERSION`](../src/zk_rfid.py#L35)
- **function** [`setup_logging`](../src/zk_rfid.py#L38)
- **class** [`ZKError`](../src/zk_rfid.py#L56)
- **class** [`ValidationError`](../src/zk_rfid.py#L60)
- **class** [`ProtocolError`](../src/zk_rfid.py#L64)
- **class** [`UnsupportedFeature`](../src/zk_rfid.py#L68)
- **class** [`UnverifiedFeature`](../src/zk_rfid.py#L72)
- **class** [`StateError`](../src/zk_rfid.py#L76)
- **class** [`TransportError`](../src/zk_rfid.py#L80)
- **class** [`ExchangeError`](../src/zk_rfid.py#L84)
- **class** [`RequestTimeout`](../src/zk_rfid.py#L93)
- **class** [`QueueOverflow`](../src/zk_rfid.py#L97)
- **class** [`DeviceError`](../src/zk_rfid.py#L101)
- **class** [`OperationError`](../src/zk_rfid.py#L110)
- **constant** [`T`](../src/zk_rfid.py#L125)
- **function** [`integer`](../src/zk_rfid.py#L128)
- **function** [`boolean`](../src/zk_rfid.py#L134)
- **function** [`octets`](../src/zk_rfid.py#L140)
- **class** [`MemoryBank`](../src/zk_rfid.py#L146)
- **constant** [`MemoryBank.RESERVED`](../src/zk_rfid.py#L147)
- **constant** [`MemoryBank.EPC`](../src/zk_rfid.py#L148)
- **constant** [`MemoryBank.TID`](../src/zk_rfid.py#L149)
- **constant** [`MemoryBank.USER`](../src/zk_rfid.py#L150)
- **class** [`Outcome`](../src/zk_rfid.py#L153)
- **constant** [`Outcome.SUCCESS`](../src/zk_rfid.py#L154)
- **constant** [`Outcome.FAILURE`](../src/zk_rfid.py#L155)
- **constant** [`Outcome.PARTIAL`](../src/zk_rfid.py#L156)
- **constant** [`Outcome.UNKNOWN`](../src/zk_rfid.py#L157)
- **class** [`Confirmation`](../src/zk_rfid.py#L160)
- **constant** [`Confirmation.NONE`](../src/zk_rfid.py#L161)
- **constant** [`Confirmation.TRANSMITTED`](../src/zk_rfid.py#L162)
- **constant** [`Confirmation.ACKNOWLEDGED`](../src/zk_rfid.py#L163)
- **constant** [`Confirmation.READ_BACK`](../src/zk_rfid.py#L164)
- **class** [`ReaderState`](../src/zk_rfid.py#L167)
- **constant** [`ReaderState.DISCONNECTED`](../src/zk_rfid.py#L168)
- **constant** [`ReaderState.IDLE`](../src/zk_rfid.py#L169)
- **constant** [`ReaderState.STARTING`](../src/zk_rfid.py#L170)
- **constant** [`ReaderState.INVENTORYING`](../src/zk_rfid.py#L171)
- **constant** [`ReaderState.STOPPING`](../src/zk_rfid.py#L172)
- **constant** [`ReaderState.UNKNOWN`](../src/zk_rfid.py#L173)
- **class** [`InventoryMode`](../src/zk_rfid.py#L176)
- **constant** [`InventoryMode.ANSWER`](../src/zk_rfid.py#L177)
- **constant** [`InventoryMode.SCENARIO`](../src/zk_rfid.py#L178)
- **constant** [`InventoryMode.REAL_TIME`](../src/zk_rfid.py#L179)
- **class** [`InventoryData`](../src/zk_rfid.py#L182)
- **constant** [`InventoryData.EPC`](../src/zk_rfid.py#L183)
- **constant** [`InventoryData.TID`](../src/zk_rfid.py#L184)
- **constant** [`InventoryData.FAST_ID`](../src/zk_rfid.py#L185)
- **constant** [`InventoryData.MIX`](../src/zk_rfid.py#L186)
- **class** [`WorkingMode`](../src/zk_rfid.py#L189)
- **constant** [`WorkingMode.ANSWER`](../src/zk_rfid.py#L190)
- **constant** [`WorkingMode.REAL_TIME`](../src/zk_rfid.py#L191)
- **constant** [`WorkingMode.TRIGGER`](../src/zk_rfid.py#L192)
- **class** [`LockTarget`](../src/zk_rfid.py#L195)
- **constant** [`LockTarget.KILL_PASSWORD`](../src/zk_rfid.py#L196)
- **constant** [`LockTarget.ACCESS_PASSWORD`](../src/zk_rfid.py#L197)
- **constant** [`LockTarget.EPC`](../src/zk_rfid.py#L198)
- **constant** [`LockTarget.TID`](../src/zk_rfid.py#L199)
- **constant** [`LockTarget.USER`](../src/zk_rfid.py#L200)
- **class** [`LockProtection`](../src/zk_rfid.py#L203)
- **constant** [`LockProtection.UNLOCK`](../src/zk_rfid.py#L204)
- **constant** [`LockProtection.PERMANENT_UNLOCK`](../src/zk_rfid.py#L205)
- **constant** [`LockProtection.PASSWORD`](../src/zk_rfid.py#L206)
- **constant** [`LockProtection.PERMANENT_LOCK`](../src/zk_rfid.py#L207)
- **class** [`TagMask`](../src/zk_rfid.py#L211)
- **method** [`TagMask.encode`](../src/zk_rfid.py#L228)
- **class** [`TagTarget`](../src/zk_rfid.py#L238)
- **class** [`CommandResult`](../src/zk_rfid.py#L256)
- **property** [`CommandResult.ok`](../src/zk_rfid.py#L269)
- **method** [`CommandResult.require_success`](../src/zk_rfid.py#L272)
- **class** [`ReaderInfo`](../src/zk_rfid.py#L279)
- **class** [`InventoryConfig`](../src/zk_rfid.py#L294)
- **class** [`TagReport`](../src/zk_rfid.py#L314)
- **class** [`InventoryStatistics`](../src/zk_rfid.py#L347)
- **class** [`Heartbeat`](../src/zk_rfid.py#L354)
- **class** [`InventoryOutcome`](../src/zk_rfid.py#L361)
- **property** [`InventoryOutcome.unique_count`](../src/zk_rfid.py#L373)
- **class** [`Region`](../src/zk_rfid.py#L378)
- **class** [`GPIOState`](../src/zk_rfid.py#L385)
- **class** [`RealTimeConfig`](../src/zk_rfid.py#L393)
- **class** [`WorkingModeConfig`](../src/zk_rfid.py#L405)
- **class** [`BufferCounts`](../src/zk_rfid.py#L411)
- **class** [`WritePower`](../src/zk_rfid.py#L417)
- **class** [`QueryParameters`](../src/zk_rfid.py#L423)
- **class** [`ScanParameters`](../src/zk_rfid.py#L430)
- **class** [`TIDParameters`](../src/zk_rfid.py#L437)
- **class** [`ParserDiagnostics`](../src/zk_rfid.py#L443)
- **class** [`ReaderCapabilities`](../src/zk_rfid.py#L459)
- **method** [`ReaderCapabilities.require`](../src/zk_rfid.py#L492)
- **constant** [`PHASE_CONVERSION`](../src/zk_rfid.py#L506)
- **constant** [`RSSI_SOURCE`](../src/zk_rfid.py#L507)
- **function** [`rssi_to_dbm`](../src/zk_rfid.py#L510)
- **function** [`phase_to_degrees`](../src/zk_rfid.py#L532)
- **function** [`phase_to_radians`](../src/zk_rfid.py#L547)
- **class** [`TraceEvent`](../src/zk_rfid.py#L560)
- **class** [`TraceEmitter`](../src/zk_rfid.py#L574)
- **method** [`TraceEmitter.emit`](../src/zk_rfid.py#L583)
- **class** [`RFProfile`](../src/zk_rfid.py#L615)
- **constant** [`PROFILES`](../src/zk_rfid.py#L625)
- **function** [`get_profile_definition`](../src/zk_rfid.py#L683)
- **constant** [`CRC16_INIT`](../src/zk_rfid.py#L699)
- **constant** [`CRC16_POLY`](../src/zk_rfid.py#L700)
- **constant** [`MAX_COMMAND_DATA`](../src/zk_rfid.py#L701)
- **constant** [`MAX_RESPONSE_DATA`](../src/zk_rfid.py#L702)
- **constant** [`BROADCAST_ADDRESS`](../src/zk_rfid.py#L703)
- **class** [`Command`](../src/zk_rfid.py#L706)
- **constant** [`Command.INVENTORY`](../src/zk_rfid.py#L707)
- **constant** [`Command.READ_MEMORY`](../src/zk_rfid.py#L708)
- **constant** [`Command.WRITE_MEMORY`](../src/zk_rfid.py#L709)
- **constant** [`Command.WRITE_EPC`](../src/zk_rfid.py#L710)
- **constant** [`Command.KILL`](../src/zk_rfid.py#L711)
- **constant** [`Command.LOCK`](../src/zk_rfid.py#L712)
- **constant** [`Command.BLOCK_ERASE`](../src/zk_rfid.py#L713)
- **constant** [`Command.SINGLE_INVENTORY`](../src/zk_rfid.py#L714)
- **constant** [`Command.BLOCK_WRITE`](../src/zk_rfid.py#L715)
- **constant** [`Command.READ_MEMORY_EXTENDED`](../src/zk_rfid.py#L716)
- **constant** [`Command.WRITE_MEMORY_EXTENDED`](../src/zk_rfid.py#L717)
- **constant** [`Command.BUFFER_INVENTORY`](../src/zk_rfid.py#L718)
- **constant** [`Command.MIX_INVENTORY`](../src/zk_rfid.py#L719)
- **constant** [`Command.INVENTORY_EPC`](../src/zk_rfid.py#L720)
- **constant** [`Command.READER_INFO`](../src/zk_rfid.py#L721)
- **constant** [`Command.SET_REGION`](../src/zk_rfid.py#L722)
- **constant** [`Command.SET_ADDRESS`](../src/zk_rfid.py#L723)
- **constant** [`Command.SET_SCAN_TIME`](../src/zk_rfid.py#L724)
- **constant** [`Command.SET_BAUDRATE`](../src/zk_rfid.py#L725)
- **constant** [`Command.SET_POWER`](../src/zk_rfid.py#L726)
- **constant** [`Command.INDICATOR`](../src/zk_rfid.py#L727)
- **constant** [`Command.SET_ANTENNAS`](../src/zk_rfid.py#L728)
- **constant** [`Command.SET_BUZZER`](../src/zk_rfid.py#L729)
- **constant** [`Command.SET_GPIO`](../src/zk_rfid.py#L730)
- **constant** [`Command.GET_GPIO`](../src/zk_rfid.py#L731)
- **constant** [`Command.SERIAL_NUMBER`](../src/zk_rfid.py#L732)
- **constant** [`Command.FAST_START`](../src/zk_rfid.py#L733)
- **constant** [`Command.FAST_STOP`](../src/zk_rfid.py#L734)
- **constant** [`Command.SET_ANTENNA_CHECK`](../src/zk_rfid.py#L735)
- **constant** [`Command.SET_INTERFACE`](../src/zk_rfid.py#L736)
- **constant** [`Command.RETURN_LOSS_THRESHOLD`](../src/zk_rfid.py#L737)
- **constant** [`Command.SET_BUFFER_LENGTH`](../src/zk_rfid.py#L738)
- **constant** [`Command.GET_BUFFER_LENGTH`](../src/zk_rfid.py#L739)
- **constant** [`Command.READ_BUFFER`](../src/zk_rfid.py#L740)
- **constant** [`Command.CLEAR_BUFFER`](../src/zk_rfid.py#L741)
- **constant** [`Command.BUFFER_COUNT`](../src/zk_rfid.py#L742)
- **constant** [`Command.SET_REAL_TIME`](../src/zk_rfid.py#L743)
- **constant** [`Command.SET_WORKING_MODE`](../src/zk_rfid.py#L744)
- **constant** [`Command.GET_WORKING_MODE`](../src/zk_rfid.py#L745)
- **constant** [`Command.HEARTBEAT`](../src/zk_rfid.py#L746)
- **constant** [`Command.SET_WRITE_POWER`](../src/zk_rfid.py#L747)
- **constant** [`Command.GET_WRITE_POWER`](../src/zk_rfid.py#L748)
- **constant** [`Command.WRITE_RETRIES`](../src/zk_rfid.py#L749)
- **constant** [`Command.PROFILE`](../src/zk_rfid.py#L750)
- **constant** [`Command.DRM`](../src/zk_rfid.py#L751)
- **constant** [`Command.RETURN_LOSS`](../src/zk_rfid.py#L752)
- **constant** [`Command.TEMPERATURE`](../src/zk_rfid.py#L753)
- **constant** [`Command.STOP_INVENTORY`](../src/zk_rfid.py#L754)
- **constant** [`Command.GET_POWER`](../src/zk_rfid.py#L755)
- **constant** [`Command.SELECT`](../src/zk_rfid.py#L756)
- **constant** [`Command.GET_REGION`](../src/zk_rfid.py#L757)
- **constant** [`Command.SET_CONFIG`](../src/zk_rfid.py#L758)
- **constant** [`Command.GET_CONFIG`](../src/zk_rfid.py#L759)
- **constant** [`Command.TAG_REPORT`](../src/zk_rfid.py#L760)
- **class** [`ConfigID`](../src/zk_rfid.py#L763)
- **constant** [`ConfigID.SCAN`](../src/zk_rfid.py#L764)
- **constant** [`ConfigID.TAG_FOCUS`](../src/zk_rfid.py#L765)
- **constant** [`ConfigID.QUERY`](../src/zk_rfid.py#L766)
- **constant** [`ConfigID.TID`](../src/zk_rfid.py#L767)
- **constant** [`ConfigID.MASK`](../src/zk_rfid.py#L768)
- **constant** [`ConfigID.IMPINJ_SCAN`](../src/zk_rfid.py#L769)
- **constant** [`ConfigID.IMPINJ_SCAN_ID`](../src/zk_rfid.py#L770)
- **constant** [`ConfigID.CUSTOM_PROFILES`](../src/zk_rfid.py#L771)
- **function** [`crc16`](../src/zk_rfid.py#L781)
- **function** [`append_crc`](../src/zk_rfid.py#L790)
- **class** [`ResponseFrame`](../src/zk_rfid.py#L802)
- **function** [`encode_command`](../src/zk_rfid.py#L810)
- **function** [`decode_response`](../src/zk_rfid.py#L817)
- **class** [`FrameParser`](../src/zk_rfid.py#L832)
- **method** [`FrameParser.reset`](../src/zk_rfid.py#L838)
- **method** [`FrameParser.feed`](../src/zk_rfid.py#L841)
- **constant** [`STATUS_NAMES`](../src/zk_rfid.py#L888)
- **class** [`StatusInfo`](../src/zk_rfid.py#L917)
- **function** [`interpret_status`](../src/zk_rfid.py#L925)
- **class** [`AsyncTransport`](../src/zk_rfid.py#L950) — **transport interface contract**
- **method** [`AsyncTransport.open`](../src/zk_rfid.py#L951) — **transport interface contract**
- **method** [`AsyncTransport.close`](../src/zk_rfid.py#L952) — **transport interface contract**
- **method** [`AsyncTransport.read`](../src/zk_rfid.py#L953) — **transport interface contract**
- **method** [`AsyncTransport.write`](../src/zk_rfid.py#L954) — **transport interface contract**
- **class** [`SerialTransport`](../src/zk_rfid.py#L966)
- **method** [`SerialTransport.open`](../src/zk_rfid.py#L977)
- **method** [`SerialTransport.read`](../src/zk_rfid.py#L1012)
- **method** [`SerialTransport.write`](../src/zk_rfid.py#L1026)
- **method** [`SerialTransport.set_baudrate`](../src/zk_rfid.py#L1034)
- **method** [`SerialTransport.close`](../src/zk_rfid.py#L1040)
- **function** [`raw`](../src/zk_rfid.py#L1061)
- **function** [`exact`](../src/zk_rfid.py#L1065)
- **function** [`ack`](../src/zk_rfid.py#L1071)
- **function** [`u8`](../src/zk_rfid.py#L1075)
- **function** [`u16`](../src/zk_rfid.py#L1079)
- **function** [`switch`](../src/zk_rfid.py#L1083)
- **class** [`Request`](../src/zk_rfid.py#L1091)
- **function** [`decode_reader_info`](../src/zk_rfid.py#L1108)
- **function** [`get_reader_info`](../src/zk_rfid.py#L1127)
- **function** [`get_serial_number`](../src/zk_rfid.py#L1131)
- **constant** [`BAUD_CODES`](../src/zk_rfid.py#L1142)
- **constant** [`PAUSE_CODES`](../src/zk_rfid.py#L1143)
- **function** [`set_address`](../src/zk_rfid.py#L1146)
- **function** [`set_scan_time`](../src/zk_rfid.py#L1150)
- **function** [`set_baudrate`](../src/zk_rfid.py#L1157)
- **function** [`set_interface`](../src/zk_rfid.py#L1164)
- **function** [`set_working_mode`](../src/zk_rfid.py#L1170)
- **function** [`encode_real_time`](../src/zk_rfid.py#L1174)
- **function** [`set_real_time`](../src/zk_rfid.py#L1196)
- **function** [`decode_working_mode`](../src/zk_rfid.py#L1200)
- **function** [`get_working_mode`](../src/zk_rfid.py#L1226)
- **function** [`heartbeat`](../src/zk_rfid.py#L1230)
- **function** [`set_power`](../src/zk_rfid.py#L1249)
- **function** [`get_power`](../src/zk_rfid.py#L1258)
- **function** [`set_write_power`](../src/zk_rfid.py#L1268)
- **function** [`decode_write_power`](../src/zk_rfid.py#L1273)
- **function** [`get_write_power`](../src/zk_rfid.py#L1280)
- **function** [`write_retries`](../src/zk_rfid.py#L1284)
- **function** [`set_antennas`](../src/zk_rfid.py#L1303)
- **function** [`set_antenna_check`](../src/zk_rfid.py#L1314)
- **function** [`decode_antenna`](../src/zk_rfid.py#L1318)
- **constant** [`REGIONS`](../src/zk_rfid.py#L1340)
- **constant** [`BAND_MAX`](../src/zk_rfid.py#L1369)
- **function** [`validate_region`](../src/zk_rfid.py#L1372)
- **function** [`channel_frequency_khz`](../src/zk_rfid.py#L1381)
- **function** [`set_region`](../src/zk_rfid.py#L1389)
- **function** [`decode_region`](../src/zk_rfid.py#L1407)
- **function** [`get_region`](../src/zk_rfid.py#L1415)
- **function** [`profile`](../src/zk_rfid.py#L1419)
- **function** [`drm`](../src/zk_rfid.py#L1432)
- **constant** [`SCENARIO_SESSIONS`](../src/zk_rfid.py#L1444)
- **function** [`encode_scan`](../src/zk_rfid.py#L1447)
- **function** [`encode_query`](../src/zk_rfid.py#L1455)
- **function** [`encode_tid`](../src/zk_rfid.py#L1463)
- **function** [`encode_profiles`](../src/zk_rfid.py#L1472)
- **function** [`decode_mask`](../src/zk_rfid.py#L1478)
- **function** [`decode_config`](../src/zk_rfid.py#L1487)
- **function** [`get_config`](../src/zk_rfid.py#L1515)
- **function** [`set_config`](../src/zk_rfid.py#L1522)
- **constant** [`ZERO_PASSWORD`](../src/zk_rfid.py#L1554)
- **function** [`password`](../src/zk_rfid.py#L1557)
- **function** [`selection`](../src/zk_rfid.py#L1561)
- **function** [`validate_access`](../src/zk_rfid.py#L1571)
- **function** [`read_memory`](../src/zk_rfid.py#L1579)
- **function** [`write_memory`](../src/zk_rfid.py#L1599)
- **function** [`block_erase`](../src/zk_rfid.py#L1628)
- **function** [`write_epc_single`](../src/zk_rfid.py#L1643)
- **function** [`lock_tag`](../src/zk_rfid.py#L1651)
- **function** [`kill_tag`](../src/zk_rfid.py#L1668)
- **function** [`select_tag`](../src/zk_rfid.py#L1678)
- **function** [`pc_with_epc_length`](../src/zk_rfid.py#L1691)
- **constant** [`VENDOR_TAG_COMMANDS`](../src/zk_rfid.py#L1711) — **unsupported by design**
- **function** [`require_vendor_feature`](../src/zk_rfid.py#L1719) — **unsupported by design**
- **function** [`validate_inventory`](../src/zk_rfid.py#L1732)
- **function** [`build_inventory`](../src/zk_rfid.py#L1768)
- **function** [`inventory_epc`](../src/zk_rfid.py#L1791)
- **function** [`fast_start`](../src/zk_rfid.py#L1806)
- **function** [`fast_stop`](../src/zk_rfid.py#L1810)
- **function** [`decode_statistics`](../src/zk_rfid.py#L1814)
- **function** [`decode_answer`](../src/zk_rfid.py#L1848)
- **class** [`MixDecoder`](../src/zk_rfid.py#L1886)
- **method** [`MixDecoder.feed`](../src/zk_rfid.py#L1895)
- **method** [`MixDecoder.flush`](../src/zk_rfid.py#L1944)
- **function** [`decode_stream`](../src/zk_rfid.py#L1953)
- **function** [`decode_heartbeat`](../src/zk_rfid.py#L1983)
- **function** [`set_buffer_length`](../src/zk_rfid.py#L1999)
- **function** [`get_buffer_length`](../src/zk_rfid.py#L2005)
- **function** [`clear_buffer`](../src/zk_rfid.py#L2015)
- **function** [`get_buffer_count`](../src/zk_rfid.py#L2019)
- **function** [`decode_counts`](../src/zk_rfid.py#L2023)
- **function** [`decode_buffer`](../src/zk_rfid.py#L2028)
- **function** [`set_buzzer`](../src/zk_rfid.py#L2076)
- **function** [`indicator`](../src/zk_rfid.py#L2080)
- **function** [`set_gpio`](../src/zk_rfid.py#L2095)
- **function** [`decode_gpio`](../src/zk_rfid.py#L2100)
- **function** [`get_gpio`](../src/zk_rfid.py#L2107)
- **function** [`decode_temperature`](../src/zk_rfid.py#L2118)
- **function** [`get_temperature`](../src/zk_rfid.py#L2125)
- **function** [`measure_return_loss`](../src/zk_rfid.py#L2129)
- **function** [`return_loss_threshold`](../src/zk_rfid.py#L2137)
- **class** [`Dispatcher`](../src/zk_rfid.py#L2167)
- **property** [`Dispatcher.pending_command`](../src/zk_rfid.py#L2194)
- **method** [`Dispatcher.open`](../src/zk_rfid.py#L2197)
- **method** [`Dispatcher.close`](../src/zk_rfid.py#L2217)
- **method** [`Dispatcher.exchange`](../src/zk_rfid.py#L2272)
- **method** [`Dispatcher.interrupt_answer`](../src/zk_rfid.py#L2377)
- **function** [`collect_answer`](../src/zk_rfid.py#L2523)
- **function** [`collect_buffer`](../src/zk_rfid.py#L2649)
- **class** [`InventorySession`](../src/zk_rfid.py#L2703)
- **method** [`InventorySession.start`](../src/zk_rfid.py#L2758)
- **method** [`InventorySession.stop`](../src/zk_rfid.py#L2985)
- **class** [`ZKReader`](../src/zk_rfid.py#L3081)
- **property** [`ZKReader.state`](../src/zk_rfid.py#L3104)
- **property** [`ZKReader.address`](../src/zk_rfid.py#L3118)
- **property** [`ZKReader.is_inventory_running`](../src/zk_rfid.py#L3123)
- **method** [`ZKReader.get_capabilities`](../src/zk_rfid.py#L3127)
- **method** [`ZKReader.open`](../src/zk_rfid.py#L3166)
- **method** [`ZKReader.close`](../src/zk_rfid.py#L3175)
- **method** [`ZKReader.get_reader_info`](../src/zk_rfid.py#L3283)
- **method** [`ZKReader.get_serial_number`](../src/zk_rfid.py#L3291)
- **method** [`ZKReader.get_power`](../src/zk_rfid.py#L3295)
- **method** [`ZKReader.set_power`](../src/zk_rfid.py#L3299)
- **method** [`ZKReader.get_write_power`](../src/zk_rfid.py#L3307)
- **method** [`ZKReader.set_write_power`](../src/zk_rfid.py#L3311)
- **method** [`ZKReader.get_write_retries`](../src/zk_rfid.py#L3315)
- **method** [`ZKReader.set_write_retries`](../src/zk_rfid.py#L3319)
- **method** [`ZKReader.set_antennas`](../src/zk_rfid.py#L3323)
- **method** [`ZKReader.get_antennas`](../src/zk_rfid.py#L3329)
- **method** [`ZKReader.set_antenna_check`](../src/zk_rfid.py#L3336)
- **method** [`ZKReader.get_antenna_check`](../src/zk_rfid.py#L3340)
- **method** [`ZKReader.set_address`](../src/zk_rfid.py#L3345)
- **method** [`ZKReader.set_baudrate`](../src/zk_rfid.py#L3354)
- **method** [`ZKReader.set_inventory_time`](../src/zk_rfid.py#L3374)
- **method** [`ZKReader.set_interface`](../src/zk_rfid.py#L3378)
- **method** [`ZKReader.get_region`](../src/zk_rfid.py#L3382)
- **method** [`ZKReader.set_region`](../src/zk_rfid.py#L3386)
- **method** [`ZKReader.get_profile`](../src/zk_rfid.py#L3392)
- **method** [`ZKReader.set_profile`](../src/zk_rfid.py#L3396)
- **method** [`ZKReader.get_drm`](../src/zk_rfid.py#L3402)
- **method** [`ZKReader.set_drm`](../src/zk_rfid.py#L3406)
- **method** [`ZKReader.set_buzzer`](../src/zk_rfid.py#L3410)
- **method** [`ZKReader.pulse_indicator`](../src/zk_rfid.py#L3414)
- **method** [`ZKReader.get_gpio`](../src/zk_rfid.py#L3420)
- **method** [`ZKReader.set_gpio`](../src/zk_rfid.py#L3425)
- **method** [`ZKReader.get_temperature`](../src/zk_rfid.py#L3430)
- **method** [`ZKReader.measure_return_loss`](../src/zk_rfid.py#L3435)
- **method** [`ZKReader.get_return_loss_threshold`](../src/zk_rfid.py#L3441)
- **method** [`ZKReader.set_return_loss_threshold`](../src/zk_rfid.py#L3445)
- **method** [`ZKReader.get_config`](../src/zk_rfid.py#L3449)
- **method** [`ZKReader.set_config`](../src/zk_rfid.py#L3458)
- **method** [`ZKReader.get_scan_parameters`](../src/zk_rfid.py#L3474)
- **method** [`ZKReader.set_scan_parameters`](../src/zk_rfid.py#L3478)
- **method** [`ZKReader.get_tag_focus`](../src/zk_rfid.py#L3484)
- **method** [`ZKReader.set_tag_focus`](../src/zk_rfid.py#L3488)
- **method** [`ZKReader.get_query_parameters`](../src/zk_rfid.py#L3492)
- **method** [`ZKReader.set_query_parameters`](../src/zk_rfid.py#L3496)
- **method** [`ZKReader.get_tid_parameters`](../src/zk_rfid.py#L3502)
- **method** [`ZKReader.set_tid_parameters`](../src/zk_rfid.py#L3506)
- **method** [`ZKReader.get_inventory_mask`](../src/zk_rfid.py#L3512)
- **method** [`ZKReader.set_inventory_mask`](../src/zk_rfid.py#L3516)
- **method** [`ZKReader.get_custom_profiles`](../src/zk_rfid.py#L3523)
- **method** [`ZKReader.set_custom_profiles`](../src/zk_rfid.py#L3527)
- **method** [`ZKReader.set_real_time_config`](../src/zk_rfid.py#L3533)
- **method** [`ZKReader.get_working_mode`](../src/zk_rfid.py#L3538)
- **method** [`ZKReader.set_working_mode`](../src/zk_rfid.py#L3545)
- **method** [`ZKReader.get_heartbeat_interval`](../src/zk_rfid.py#L3554)
- **method** [`ZKReader.set_heartbeat_interval`](../src/zk_rfid.py#L3558)
- **method** [`ZKReader.get_buffer_length`](../src/zk_rfid.py#L3562)
- **method** [`ZKReader.set_buffer_length`](../src/zk_rfid.py#L3566)
- **method** [`ZKReader.get_buffer_count`](../src/zk_rfid.py#L3570)
- **method** [`ZKReader.clear_buffer`](../src/zk_rfid.py#L3574)
- **method** [`ZKReader.inventory_to_buffer`](../src/zk_rfid.py#L3578)
- **method** [`ZKReader.read_buffer`](../src/zk_rfid.py#L3588)
- **method** [`ZKReader.inventory_once`](../src/zk_rfid.py#L3595)
- **method** [`ZKReader.inventory_single`](../src/zk_rfid.py#L3604)
- **method** [`ZKReader.inventory_matching_epc`](../src/zk_rfid.py#L3611)
- **method** [`ZKReader.start_inventory`](../src/zk_rfid.py#L3627)
- **method** [`ZKReader.stop_inventory`](../src/zk_rfid.py#L3641)
- **method** [`ZKReader.read_memory`](../src/zk_rfid.py#L3655)
- **method** [`ZKReader.write_memory`](../src/zk_rfid.py#L3694)
- **method** [`ZKReader.write_epc`](../src/zk_rfid.py#L3775)
- **method** [`ZKReader.write_epc_single`](../src/zk_rfid.py#L3845)
- **method** [`ZKReader.set_access_password`](../src/zk_rfid.py#L3851)
- **method** [`ZKReader.set_kill_password`](../src/zk_rfid.py#L3871)
- **method** [`ZKReader.lock_tag`](../src/zk_rfid.py#L3890)
- **method** [`ZKReader.kill_tag`](../src/zk_rfid.py#L3903)
- **method** [`ZKReader.block_write`](../src/zk_rfid.py#L3907)
- **method** [`ZKReader.block_erase`](../src/zk_rfid.py#L3923)
- **method** [`ZKReader.select_tag`](../src/zk_rfid.py#L3939)
- **class** [`Equivalence`](../src/zk_rfid.py#L3968)
- **constant** [`Equivalence.VERIFIED`](../src/zk_rfid.py#L3969)
- **constant** [`Equivalence.CONVERTED`](../src/zk_rfid.py#L3970)
- **constant** [`Equivalence.MULTI_STEP`](../src/zk_rfid.py#L3971)
- **constant** [`Equivalence.APPROXIMATE`](../src/zk_rfid.py#L3972)
- **constant** [`Equivalence.UNSUPPORTED`](../src/zk_rfid.py#L3973)
- **constant** [`Equivalence.UNVERIFIED`](../src/zk_rfid.py#L3974)
- **constant** [`CONTRACT`](../src/zk_rfid.py#L3977)
- **class** [`RFMapping`](../src/zk_rfid.py#L3994)
- **method** [`RFMapping.require`](../src/zk_rfid.py#L4002)
- **function** [`hex_epc`](../src/zk_rfid.py#L4008)
- **function** [`power_dict`](../src/zk_rfid.py#L4019)
- **function** [`tag_dict`](../src/zk_rfid.py#L4023)
- **function** [`unsupported`](../src/zk_rfid.py#L4047)
- **class** [`NationAdapter`](../src/zk_rfid.py#L4064)
- **method** [`NationAdapter.open`](../src/zk_rfid.py#L4068)
- **method** [`NationAdapter.close`](../src/zk_rfid.py#L4071)
- **method** [`NationAdapter.get_sdk_info`](../src/zk_rfid.py#L4074)
- **method** [`NationAdapter.Query_Reader_Information`](../src/zk_rfid.py#L4078)
- **method** [`NationAdapter.query_rfid_ability`](../src/zk_rfid.py#L4081)
- **method** [`NationAdapter.query_reader_power`](../src/zk_rfid.py#L4084)
- **method** [`NationAdapter.configure_reader_power`](../src/zk_rfid.py#L4088)
- **method** [`NationAdapter.build_antenna_mask`](../src/zk_rfid.py#L4115)
- **method** [`NationAdapter.save_antenna_mask`](../src/zk_rfid.py#L4122)
- **method** [`NationAdapter.query_enabled_ant_mask`](../src/zk_rfid.py#L4125)
- **method** [`NationAdapter.enable_ant`](../src/zk_rfid.py#L4145)
- **method** [`NationAdapter.disable_ant`](../src/zk_rfid.py#L4148)
- **method** [`NationAdapter.is_inventory_running`](../src/zk_rfid.py#L4151)
- **method** [`NationAdapter.start_inventory_with_mode`](../src/zk_rfid.py#L4154)
- **method** [`NationAdapter.run_inventory`](../src/zk_rfid.py#L4164)
- **method** [`NationAdapter.stop_inventory`](../src/zk_rfid.py#L4185)
- **method** [`NationAdapter.write_epc_to_target_auto`](../src/zk_rfid.py#L4188)
- **method** [`NationAdapter.select_profile`](../src/zk_rfid.py#L4206)
- **method** [`NationAdapter.get_profile`](../src/zk_rfid.py#L4213)
- **method** [`NationAdapter.query_rf_band`](../src/zk_rfid.py#L4217)
- **method** [`NationAdapter.set_rf_band`](../src/zk_rfid.py#L4221) — **unverified mapping; rejected explicitly**
- **method** [`NationAdapter.set_beeper`](../src/zk_rfid.py#L4224)
- **method** [`NationAdapter.get_beeper`](../src/zk_rfid.py#L4230) — **unsupported by design**
- **method** [`NationAdapter.set_filter_settings`](../src/zk_rfid.py#L4233) — **unsupported by design**
- **method** [`NationAdapter.get_session`](../src/zk_rfid.py#L4236)
