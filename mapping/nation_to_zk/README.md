# NATION to ZK

Keep the existing web screens and business logic. Replace their reader service
with calls to the native ZK SDK, using these mappings to preserve the intended
behavior. Continuous EPC reading maps to **Scenario**: one Start, reports until
Stop. EPC+TID maps to Answer FastID, repeating rounds over selected ports; a tag
without FastID support may report EPC without TID.

The same adapter handles one or four declared ports: pass `[1]` or a selected
list such as `[1, 3, 4]` to Scenario Start. Power values follow port order and
partial power updates preserve other ports. See the [four-port example](web_integration.md#four-port-readers).

- [API map](api_map.md): every public callable in the pinned NATION Python source,
  its command constants, and the ZK replacement or remaining integration work.
- [RF choices](rf_mapping.md): approved GReaderTool 0.39 choices and retained alternatives.
- [NATION source notes](vendor_reference.md): supplied manual/demo evidence and conflicts.
- [Web integration](web_integration.md): service boundary, events and lifecycle.
- [Reference provenance](../../compat/nation/UPSTREAM.md): the NATION source being compared.

## Review and edit

| File | Change here |
|---|---|
| [api_map.md](api_map.md) | API decisions, parameter conversions and exceptions |
| [rf_choices.json](rf_choices.json) | Approved GReaderTool speed/region policy; generic presets remain unapproved |
| [rf_mapping.md](rf_mapping.md) | RF reasoning, differences and review procedure |
| [adapter.py](adapter.py) | Executable Python compatibility methods |
| [policy.py](policy.py) | Resolve approved speeds and full channel plans without I/O |
| [values.py](values.py) | Existing value conversions and explicit RF confirmation |
| [mapping_cases.json](mapping_cases.json) | Independent conversion test cases |

The adapter and browser service load **GReaderTool 0.39** choices from this JSON
when explicitly configuring baseband or region. Connect and Start never apply
RF presets. These are approved engineering mappings, not measured RF equivalence.
Run `python tools/check_nation_mapping.py` after editing to check API coverage,
profile definitions and exact channel plans.
To print proposed calls, add `--show --baseband-source nextwaves` or
`--show --baseband-source greader-0.39`. Speed 4 means different RF settings in
those two sources; the checker deliberately has no default for this selection.

A proposed replacement is not a claim of identical RF performance. Review the
listed differences, choose the policy, then implement it in the application's
reader service or this optional adapter and add a regression in
[`tests/compat/nation`](../../tests/compat/nation/).
Keep ZK protocol changes in `src/zk_rfid.py` and application mapping decisions here.

## Python adapter

From the repository root, after installing the SDK:

```python
from mapping.nation_to_zk import NationAdapter

adapter = NationAdapter(reader)  # An open ZKReader.
powers = (await adapter.query_reader_power()).require_success()
```

The adapter is async and returns native ZK results. It does not implement the
entire NATION API, emulate NATION frames, or import `nrn.py`. Methods marked **proposed** in the API map
require application work. `configure_baseband()` applies the approved speed map;
`set_rf_band()` applies complete approved channel plans and rejects unrepresentable
bands. `select_profile()` refers to separate generic presets and still requires
an explicit confirmed `RFMapping`.
Do not mark a proposed or approximate choice as measured evidence to bypass it.

The native wheel contains only `zk_rfid.py`. The source archive also contains this
optional package. To vendor it, copy the `mapping/` directory and the root MIT
license alongside your application; make its parent importable. The new import
replaces `from zk_rfid import NationAdapter, RFMapping, Equivalence`. No compatibility
re-export is retained in core. Existing pickles referring to those old module
paths need migration; native ZK imports remain unchanged.

Power and antenna read-modify-write methods retain their existing internal
transaction lock usage. Keep the adapter and core from the same revision; replacing
these calls with separate public Get/Set calls would change concurrency behavior.

`run_inventory()` stops and restores managed settings before propagating callback
errors, including `TimeoutError`. Only its own duration expiry is normal completion.
Inspect the returned Stop outcome, or reader state after an exception. An unknown
reader requires recovery even when `is_inventory_running()` is false.

Checkbox antenna configuration uses `save_antenna_mask()` with SAVE and read-back.
`enable_ant()`/`disable_ant()` also require `save=True`. Apply checkbox changes before
Start and pass that same selection; Start does not save again. Power and RF settings
remain volatile unless explicitly saved. `configure_baseband()` stages Q/Session/Target
for subsequent Start calls on this adapter; those fields are application state.

## Browser

The [native browser bridge](../../web/README.md) exposes `ZKReader`, not this Python
adapter. A call such as `reader.call("query_reader_power")` is therefore invalid.
Use the native methods behind the web app's existing service interface, following
the [web guide](web_integration.md). The reference driver is not needed in the browser.
