# Commands

Opcodes below are hexadecimal; CFG identifiers are decimal.
Methods send commands through `ZKReader`; inventory sessions own their start,
notification, and stop lifecycle. See the [API index](../functions_implemented.md)
for signatures and [compatibility](../supported_devices.md) for deployment limits.

| Opcode | API |
|---|---|
| 01 | `inventory_once`; Answer sessions |
| 02 / 15 | `read_memory`, normal / extended |
| 03 / 16 | `write_memory`, normal / extended; targeted EPC and password writes |
| 04 | `write_epc_single` |
| 05 / 06 | `kill_tag` / `lock_tag` |
| 07 / 10 | `block_erase` / `block_write` |
| 0F | `inventory_single` |
| 18 | `inventory_to_buffer` |
| 19 | Mix inventory |
| 1A | `inventory_matching_epc` |
| 21 / 4C | `get_reader_info` / `get_serial_number` |
| 22 / 9E | `set_region` / `get_region` |
| 24 / 25 / 28 | `set_address` / `set_inventory_time` / `set_baudrate` |
| 2F / 94 | `set_power` / `get_power` |
| 33 / 40 | `pulse_indicator` / `set_buzzer` |
| 3F / 66 | `set_antennas` / `set_antenna_check`; getters use 21 |
| 46 / 47 | `set_gpio` / `get_gpio` |
| 50 / 51 | Scenario start / stop |
| 6A | `set_interface` |
| 6E | Get/set return-loss threshold |
| 70 / 71 | Set/get buffer maximum ID length: 16 or 62 bytes |
| 72 / 73 / 74 | `read_buffer` / `clear_buffer` / `get_buffer_count` |
| 75 / 76 / 77 | `set_real_time_config` / `set_working_mode` / `get_working_mode` |
| 78 | Get/set heartbeat interval, in 30 s units |
| 79 / 7A | Set/get write power |
| 7B | Get/set write retries |
| 7F | Get/set RF profile, legacy or extended 16-bit |
| 90 | Get/set DRM |
| 91 / 92 | `measure_return_loss` / `get_temperature` |
| 93 | Interrupt pending Answer 01; no separate ACK |
| 9A | `select_tag` |
| EA / EB | Set/get extended configuration |
| EE | Tag/heartbeat notification; never a host request |

## Extended configuration

| CFG | Typed API | Contents |
|---|---|---|
| 7 | Get/set scan parameters | Interval in 10 ms, dwell in 100 ms, count |
| 8 | Get/set TagFocus | Boolean, tag-dependent |
| 9 | Get/set query parameters | Q, session, phase |
| 10 | Get/set TID parameters | Word address/count; zero count selects EPC |
| 11 | Get/set inventory mask | Bit mask; `None` clears it |
| 25 | `get_config` / `set_config` | Raw getter; confirmed 6-byte setter |
| 29 | `get_config` / `set_config` | Raw getter; confirmed 5-byte setter |
| 31 | Get/set custom profiles | Three big-endian 16-bit profile IDs |

The native RF profile table in [the source](../../src/zk_rfid.py) contains 54
records with Tari, BLF, and encoding from the manual. Availability still depends
on firmware.

## Side effects

Power, antenna, region, profile, and CFG APIs with `persist=False` default to
volatile changes. Encoding of the persistence flag differs between commands.
Setters without that argument are not necessarily volatile: `0x75/0x76` save
Real-time configuration/mode, and `0x6A` requires a power cycle.

Inventory emits RF and affects tag inventoried state and the reader buffer.
Changing maximum buffer ID length clears the buffer. Tag writes, Lock, Kill, and
Erase modify the tag. The SDK preserves persistence-failure status `0x13` and
nested tag errors rather than reporting unconditional success.

See [errata](errata.md) before using ambiguous firmware options.
