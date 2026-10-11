# Inventory

Use Answer for a bounded scan, Scenario for a managed Ex10 stream, and Real-time
when the reader should use its stored autonomous or trigger configuration.

| Mode | Start and stop | Configuration |
|---|---|---|
| Answer round | `inventory_once()`; finishes on the terminal response | `InventoryConfig` for each round |
| Answer session | `start_inventory(InventoryMode.ANSWER)`; host repeats rounds | One antenna per round |
| Scenario | `start_inventory(InventoryMode.SCENARIO)`; `0x50 → 0xEE → 0x51` | Temporary query, TID, mask, and antenna configuration |
| Real-time | `start_inventory(InventoryMode.REAL_TIME)`; `0x76=1`, stop with `0x76=0` | Stored `RealTimeConfig` set with `set_real_time_config()` |
| Trigger | Real-time session with `trigger=True`; `0x76=2` | Reader input wiring and stored configuration |
| Buffered | `inventory_to_buffer()`, then `read_buffer()` | Caller specifies the stored data kind |
| Single / EPC match | `inventory_single()` / `inventory_matching_epc()` | Native `0x0F` / `0x1A` |

## Continuous reading

With an open `reader`, this session reads for five seconds and then stops:

```python
import asyncio
from zk_rfid import InventoryConfig, InventoryMode, TagReport

session = await reader.start_inventory(
    InventoryMode.SCENARIO,
    config=InventoryConfig(antenna=1, phase=True),
)
try:
    async with asyncio.timeout(5):
        async for event in session:
            if isinstance(event, TagReport):
                print(event.epc, event.rssi_raw)
except TimeoutError:
    pass
finally:
    outcome = await session.stop()
    print(outcome.termination_reason, outcome.dropped_count)
```

Scenario snapshots CFG9/10/11 and antenna selection, applies volatile settings,
and reads them back before starting. After a stop ACK, it restores and verifies
the snapshot. Automatic antenna restoration is available for 1-, 4-, and 8-port
layouts; the 16-port getter remains unresolved.

A session selects one antenna. To scan multiple ports, schedule separate sessions
and inspect each stop result before starting the next. The SDK does not silently
cycle all antennas.

## Tag data

| Data | Behavior |
|---|---|
| EPC | Returns the reported EPC; does not fabricate PC or TID |
| TID | Answer uses the requested TID word range; Scenario uses CFG10, 1–15 words |
| FastID | Answer `0x01`; compatible tags append a 96-bit TID; other tags may return EPC only |
| Mix | `0x19`; pairs EPC and memory records using sequence and antenna; up to 31 memory words |
| Phase | Supported report layouts retain begin/end values and frequency; see [measurements](phase_and_live_view.md) |

Scenario supports EPC or TID-only data. FastID and Mix are not defined for its
managed session contract. Mix records without their matching memory data remain
visible and make the outcome partial.

Real-time uses the reader's current `0x75` configuration. The SDK reads `0x77`
to interpret EPC/TID reports and rejects unsupported phase/statistics requests.
Other Answer fields in `InventoryConfig` do not reconfigure Real-time mode.
Both Real-time configuration and working-mode changes are persistent.

## Completion and stopping

Answer status `0x03` means more frames, `0x01` means completion, `0x02` means
device timeout, and `0x04` means buffer full. Statistics requests also wait for
`0x26`. Status `0xFB` means no tag. Completion confirms the protocol exchange;
it does not establish that all physical tags were found.

- Answer `0x01` stops with `0x93`, which has no independent ACK.
- Mix `0x19` has no asynchronous stop command; it finishes the current round.
- Scenario stops with `0x51` and restores configuration after its ACK.
- Real-time stops by storing Answer mode with `0x76=0`.

Cancelling the host task is not a device stop. Always clean up the session and
inspect its result. A report after a stop ACK faults the connection so stale
data cannot enter the next session. See [recovery](api.md#recovery).

## Timing and throughput

`scan_time_100ms` is in 100 ms units. Use a finite scan time unless your application
explicitly manages interruption and deadlines; zero requests an unlimited scan.
The default deadline accounts for the requested scan time with a 250 ms margin.
An explicit timeout covers the entire operation, including waiting for the lock.

The dispatcher has one RX consumer and each session has a bounded event queue.
Overflow raises `QueueOverflow` and increments `dropped_count`. Heartbeats are
separate events and do not count as tags. Keep processing lightweight or hand
reports to an application queue.

For RF performance comparisons, use the [benchmark procedure](inventory_benchmark.md).
Report rate alone is not a measure of tag completeness.
