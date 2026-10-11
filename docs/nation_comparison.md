# NATION adapter

`NationAdapter` provides familiar NATION-style method names over the native ZK
reader. It is asynchronous and is not a drop-in replacement for the blocking
upstream `NRNReader`.

```python
from zk_rfid import NationAdapter

adapter = NationAdapter(reader)  # An open ZKReader.
powers = (await adapter.query_reader_power()).require_success()
print(powers)  # {1: 20, ...}
```

The reference driver is kept under [compat/nation](../compat/nation/README.md).
The runtime adapter neither imports it nor emulates NATION wire frames.

## Mappings

| Operation | Behavior |
|---|---|
| SDK / reader information | Preserves native data and capability metadata |
| Power dictionary | Converts port → dBm; partial updates preserve other ports |
| Antenna IDs / masks | Converts masks and enable/disable operations; 16-port getter remains restricted |
| Inventory | Async session; sync or async callbacks run outside the RX task |
| EPC strings and writes | Lossless hex conversion; native PC/read/write/verify sequence |
| Memory access | Use `ZKReader` directly |
| Profile / band getters | Return native ZK IDs and regions |
| Profile setter | Requires an explicit, confirmed `RFMapping` with supporting evidence |
| RF band setter | Rejected because no verified mapping is defined |
| RSSI / phase | Preserves ZK raw values and [conversion metadata](phase_and_live_view.md) |
| Beeper | Quiet and beep-per-tag supported; beep-after-inventory and getter unsupported |
| NATION filter settings | Unsupported |

Results retain native status, nested tag errors, and multi-step outcomes. A
callback failure triggers session cleanup; callback runner durations are seconds.

Equal profile numbers do not establish equivalent Tari, BLF, encoding, receiver
behavior, or RF performance across reader families. Confirm mappings on the
deployed hardware under the same tag and antenna conditions.

## Offline comparison

```sh
python tools/compare_results.py
```

The [mapping cases](../compat/nation/mapping_cases.json) include three independently
specified conversions (hex, power, and ZK TX) and two unverified RF/RSSI mappings.
Passing this comparison validates conversion behavior, not RF equivalence.
