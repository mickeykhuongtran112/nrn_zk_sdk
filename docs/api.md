# Python API

Import the SDK directly from `zk_rfid`. The [API index](functions_implemented.md)
lists every public method and its signature.

```python
from zk_rfid import (
    InventoryConfig, MemoryBank, OperationError, ReaderCapabilities,
    SerialTransport, TagMask, TagTarget, ZKReader,
)
```

## Connection

```python
reader = ZKReader(
    SerialTransport("COM3", 115200),
    address=0,
    capabilities=ReaderCapabilities(antenna_ports=1),
    timeout=3.0,
)

async with reader:
    info = (await reader.get_reader_info()).require_success()
```

The constructor performs no I/O. `open()`, `close()`, and the async context manager
own the transport lifecycle. One dispatcher receives all bytes and serializes
ordinary requests. Do not read from the transport independently while it belongs
to a reader. Broadcast address `0xFF` is supported on a connection to one reader;
simultaneous responses from multiple readers are not supported.

`ReaderCapabilities` declares the configured layout and firmware-specific options.
It does not discover or verify hardware. The port count defaults to 1.

## Results

Reader and tag commands return `CommandResult[T]`:

| Field | Meaning |
|---|---|
| `outcome` | `success`, `failure`, `partial`, or `unknown` |
| `data`, `raw_data` | Decoded result and original response payload |
| `command`, `status`, `tag_error` | Native opcode, reader status, and nested tag error |
| `confirmation` | `none`, `transmitted`, `acknowledged`, or `read_back_verified` |
| `steps`, `diagnostics` | Results of a multi-step operation and reasons for its outcome |

```python
result = await reader.get_power()
try:
    powers = result.require_success()
except OperationError as error:
    print(error.result.outcome, error.result.status, error.result.diagnostics)
```

`require_success()` returns decoded data or raises `OperationError` with the full
result. An ACK confirms the command response; it does not prove persistence through
a power cycle. Status `0x13` is partial because applying a setting and saving it
are separate outcomes. `0xFC` retains the tag's error code, such as `0x04` for locked memory.

Input validation, unsupported features, state conflicts, and a deadline while
waiting for the operation lock can raise before transmission. A timeout or
disconnect after transmission leaves the operation uncertain and faults the
connection. Writes are not retried automatically.

## Inventory

`inventory_once()`, `inventory_single()`, and `inventory_matching_epc()` return an
`InventoryOutcome`. Inspect `reports`, `complete`, `termination_reason`,
`received_count`, `dropped_count`, and diagnostics. Completion describes the
transaction, not the number of physical tags successfully identified.

`start_inventory()` returns an `InventorySession`, an async iterator yielding
`TagReport` or `Heartbeat`. Stop the session in `finally` or use its async context
manager. A bounded queue reports overflow explicitly. Stream consumers retain
their own reports; the session outcome provides counters.

Scenario accepts `antenna_mask` as a Start keyword: `0b1101` selects ANT1/3/4 on
a declared four-port reader. It overrides `config.antenna`, is verified before
Start, and the previous mask is restored after confirmed Stop. Without a mask,
the session selects `config.antenna`. Other modes reject the keyword.
Answer accepts `antenna_sequence=(1, 3, 4)` to repeat rounds in that order, including
FastID. Each round selects one port; this is host scheduling and does not change
saved antenna configuration. Multiple ports require a nonzero `scan_time_100ms`.
`reader.stop_inventory()` waits for an in-progress Start before stopping;
cancelling Stop still waits for cleanup before propagating cancellation.

After `stop()`, use `session.drain()` to take queued events with the same consumer.
Stop quarantines trailing `0xEE` frames separately: `quarantined_count` is the
total and `quarantined_frames` holds up to 32 raw frames. Such a run is partial,
even when stopping and restoring configuration succeeded.

A failed Answer interrupt still finalizes the session with an unknown outcome
and permits `drain()`. Recovery is required before issuing further commands.

If no session remains but the reader is `unknown`, `stop_inventory()` returns
`outcome="unknown"`, `complete=False`, and `termination_reason="stop_unconfirmed"`.
It sends no guessed Stop command. This also applies after a lost Start ACK or an
earlier failed Stop. `is_inventory_running=False` only describes host ownership;
it does not confirm RF has stopped. Follow [recovery](#recovery) before reuse.

See [Inventory](inventory_modes.md) for mode-specific configuration and stop behavior.
For Scenario, `InventoryConfig` overrides CFG9/10/11 for the run; use
`ScenarioSession.S_CST` in `config.session` to select custom profiles. CFG31 is
configured separately and is not restored by `InventorySession.stop()`.

`get_inventory_mask()` and decoded `get_config(11)` return `None` for a disabled
mask. This is a successful result, not a decoding failure; `raw_data` still holds
the CFG11 payload. Active masks return `TagMask`.

## Tag access

Memory addresses and lengths use **16-bit words**; selection masks use **bits**.
Data and passwords use `bytes`. Use [Tag memory](tag_memory.md) for complete examples.

| Method | Contract |
|---|---|
| `read_memory()` | 1–120 words; normal or extended address format |
| `write_memory()` | 1–32 words; even byte count; optional read-back |
| `write_epc()` | Read PC, preserve its lower 11 bits, write PC + EPC, optionally verify |
| `write_epc_single()` | Native `0x04`; exactly one physical tag; 1–14 EPC words |
| `set_access_password()`, `set_kill_password()` | Write a 32-bit password; do not lock or kill |
| `select_tag()`, `lock_tag()`, `kill_tag()` | Explicit Gen2 selection and protection operations |
| `block_write()`, `block_erase()` | Optional chip-dependent commands with their own size limits |

Read-back requires a target that still identifies the same tag after the write.
Changing an EPC-selected tag requires `verification_target`. Changing the Access
password through `write_memory()` also requires `verification_password` when
verification is enabled.

## Recovery

A timeout after TX, cancellation, EOF, or a late report can leave the reader
operating even though the host has stopped waiting. `CancelledError` propagates;
inspect `last_result`, `last_inventory_outcome`, and `state` for retained progress.

1. Close the connection and stop/reset the old reader operation.
2. Establish a clean transport boundary so stale responses cannot arrive.
3. Call `await reader.open(recover=True)`.

`recover=True` records the application's assertion that the boundary is clean. It
does not reset hardware. Closing and reopening a COM port alone does not establish
that the reader stopped RF activity.

Deadlines use monotonic time and cover lock acquisition and complete multi-step
operations, including read/write/verify. A short transport write continues only
the remaining bytes; it does not restart the command.

## Configuration and units

| Setting | Units or behavior |
|---|---|
| Read/write power | Integer dBm, 0–30; per-port values follow antenna order |
| Region | Native band, inclusive zero-based channel limits; see [RF settings](rf_settings.md) |
| Custom Region | `set_custom_region(start_frequency_khz, channel_count, spacing_khz)`; frequencies in kHz, spacing a multiple of 125; volatile by default |
| RF profile | Native ID; extended 16-bit format by default; see [profile table](rf_profiles.md) |
| Custom profiles | Three ordered CFG31 slots for S-CST; separate from the single RF profile |
| Range Control | Native integer 0-100, CFG16; no distance/dB conversion; see [RF settings](rf_settings.md#range-control) |
| Inventory scan time | 100 ms per unit for Answer rounds; does not time-limit Scenario |
| Indicator pulse | 50 ms per unit |
| Heartbeat interval | 30 s per unit |
| Real-time pause | One of 10, 20, 30, 50, or 100 ms |
| Baud rate | ACK at the old baud, then transport changes baud if supported |
| Reader interface | Takes effect after a power cycle |

Methods with `persist=False` default to volatile changes. Do not apply that rule
to setters without a `persist` argument: `set_real_time_config()` stores its
settings. Work Mode now defaults to temporary; pass `persist=True` explicitly
to change startup behavior. See [Commands](protocol/zk_commands.md).

Reports retain raw RSSI and phase alongside conversion metadata. The dBm estimate
and phase convention are described in [RSSI and phase](phase_and_live_view.md).

## Custom transports and tracing

Implement `AsyncTransport` for another byte transport or runtime. `read()` returns
`bytes`; `b""` means EOF. Absorb ordinary serial polling timeouts inside the
transport. `SerialTransport` imports `pyserial` only when opened.

Pass `on_event` to `ZKReader` to receive `TraceEvent` records, or configure the
`zk_rfid.trace` logger. Callbacks must be short and nonblocking; observer failures
are counted without interrupting RX. Trace data includes raw bytes and can expose
tag identifiers and passwords. See the [test console](../tests/demo_app/README.md)
for an example of queued file logging.

## Migration from 0.1

Version 0.2 consolidates the SDK into one file. Replace imports from
`zk_rfid.<module>` with imports from `zk_rfid`. Reader method names and async
semantics are retained. Pickles containing old class paths are not compatible;
use explicit JSON or another application-owned storage format for persisted data.
