# NATION migration

The native SDK is `src/zk_rfid.py`. NATION reference code and compatibility logic
are separate from it:

| Location | Purpose |
|---|---|
| [compat/nation](../compat/nation/README.md) | Pinned reference driver and license |
| [mapping/nation_to_zk](../mapping/nation_to_zk/README.md) | Optional adapter and reviewable integration choices |
| [API map](../mapping/nation_to_zk/api_map.md) | NATION functions, commands and ZK replacements |
| [RF choices](../mapping/nation_to_zk/rf_mapping.md) | Baseband/profile candidates and native/custom channel plans |
| [Web integration](../mapping/nation_to_zk/web_integration.md) | Reuse the existing UI through its reader service |

Continuous EPC maps to Scenario; EPC+TID maps to repeating Answer FastID rounds.
Antenna configuration always uses SAVE in the mapping layer. Numeric RF IDs are
not interchangeable: explicit baseband/region calls apply the approved GReaderTool
0.39 choices with read-back. Differences remain documented; RF equivalence is unverified.

The optional Python adapter now uses:

```python
from mapping.nation_to_zk import NationAdapter

adapter = NationAdapter(reader)
powers = (await adapter.query_reader_power()).require_success()
```

Use a checkout/source archive for the optional adapter. It is not included in the
native wheel and is not a drop-in replacement for blocking `NRNReader` or the
browser's JavaScript API. See the mapping guide for preserved behavior and limits.
