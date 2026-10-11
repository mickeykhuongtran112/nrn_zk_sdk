# RF choices

The project uses the **GReaderTool 0.39** speed table and exact region choices in
[rf_choices.json](rf_choices.json). The adapter and web service apply them only on
explicit configuration calls, with read-back. Approval does not establish measured
RF equivalence. The older Nextwaves table remains reference-only; generic P0/P1/P2
presets are not enabled. The [checker](../../tools/check_nation_mapping.py) validates
both retained dialects without opening a port. To inspect calls, choose one:

```sh
python tools/check_nation_mapping.py --show --baseband-source nextwaves
python tools/check_nation_mapping.py --show --baseband-source greader-0.39
```

The supplied NATION manual and demo were reviewed together; their conflicts and
source identifiers are recorded in [source notes](vendor_reference.md).

## Baseband

Prefer the same FM0/Miller encoding,
then the closest available BLF, then the closest Tari. This is a selection policy,
not an RF-performance formula. Receiver filtering, PIE, modulation and firmware
algorithms can still differ. Where NATION does not specify them, leave them unknown.

### Nextwaves / protocol Set table

This is the cached Nextwaves menu and protocol p.60 definition. The pinned Python
driver accepts these speed codes. This is not the selected runtime dialect.

| NATION speed | NATION label: Tari / encoding / BLF | Proposed ZK ID | ZK Tari / encoding / BLF | Decision |
|---:|---|---:|---|---|
| 0 | 25 us / FM0 / 40 kHz | 205 | 20 us / FM0 / 50 kHz | Lowest known FM0 BLF; +25% BLF, not an exact low-rate replacement. |
| 1 | 25 us / Miller4 / 250 kHz | 146 | 20 us / Miller4 / 250 kHz | Preserve BLF/encoding; shorter Tari. |
| 2 | 25 us / Miller4 / 300 kHz | 141 | 20 us / Miller4 / 320 kHz | +6.67% BLF is closer than 250 kHz. |
| 3 | 6.25 us / FM0 / 400 kHz | 203 | 12.5 us / FM0 / 426 kHz | Closest BLF, but Tari doubles. ID104 keeps 6.25 us with 320 kHz if downlink timing matters more. |
| 4 | 25 us / Miller4 / 320 kHz | 141 | 20 us / Miller4 / 320 kHz | Preserve this UI's encoding/BLF. |
| 255 | Automatic setup | Keep current | Read native profile | Explicit fallback; does not implement automatic adaptation. |

IDs 141 and 241, or 146 and 244, share displayed physical labels in the ZK table;
this does not prove identical firmware behavior. The choices above select explicit
IDs for review, not arbitrary interchangeable aliases. See the full
[native definitions](../../docs/rf_profiles.md).

Apply a selected fixed profile while idle using `set_profile(id, persist=False)`,
check its command result and read it back. Keep Q/Session/Target in the application
configuration and pass them to Scenario Start. Session S0–S3 maps directly as a
selector; Q remains 0–15. Do not map NATION Auto to S-CST/S-PRO or infer equivalent
automatic algorithms.

NATION Target 2 means A/B alternation in the cached UI. ZK's current public
contract accepts only A or B. A host could alternate targets between confirmed
Scenario stops, but that is a new scheduling policy with gaps and a different
round cadence. It is not implemented by this refactor.

### GReaderTool 0.39

This is the approved runtime dialect for the deployed web. The same integers in
an older Nextwaves payload can mean different settings.
Speeds 1/3 use Dense/Fast labels in the demo; physical values below follow p.60.

| NATION speed | Tari / encoding / BLF (us / kHz) | ZK ID | Difference |
|---:|---|---:|---|
| 0 | 25 / FM0 / 40 | 205 | BLF 50, Tari 20; approximate. |
| 1 | 25 / Miller4 / 250 | 146 | Tari 20. |
| 2 | 25 / Miller4 / 300 | 141 | BLF 320, Tari 20. |
| 3 | 6.25 / FM0 / 400 | 203 | BLF 426, Tari 12.5. |
| 4 | 20 / Miller2 / 320 | 123 | Same three displayed parameters; differs from older speed 4. |
| 5 | 6.25 / FM0 / 640 | 103 | Same three displayed parameters. |
| 6 | 20 / Miller4 / 320 | 141 | Same three displayed parameters. |
| 7 | 6.25 / Miller4 / 400 | 141 | BLF 320, Tari 20; no exact match. |
| 10 | 12.5 / Miller4 / 250 | 146 | Tari 20. |
| 11 | 6.25 / Miller4 / 250 | 146 | Tari 20. |
| 12 | 12.5 / Miller4 / 300 | 141 | BLF 320, Tari 20. |
| 13 | 6.25 / Miller4 / 300 | 141 | BLF 320, Tari 20. |
| 255 | Auto | Keep current | Explicit fallback, not automatic adaptation. |

No row proves identical modulation, PIE, receiver filtering or RF performance.
If the demo's separate timing/encoding overrides were used, read those too;
the speed number alone is insufficient. Those overrides have no direct ZK setters.

Use `adapter.configure_baseband(speed, q_value, session, inventory_flag, persist=False)`.
It writes and checks the RF profile, then stages Q/Session/Target for future Start
calls. A failed write/read-back leaves staged run settings unchanged, but the device
may already have accepted a write; inspect the result. Speed 255 reads the existing
profile without changing it: show **Keep current**, not automatic adaptation.
`query_baseband_profile()` combines native profile read-back with application-owned
run settings. Target 2 remains rejected; neither S-CST nor host A/B toggling is implied.

## Profile buttons

Keep three namespaces separate: NATION `select_profile(0..2)`, NATION Baseband
Speed, and the actual web's P0/P1/P2 buttons. The reference driver gives its three
profiles only generic descriptions. The JSON proposes application presets for
those descriptions: P0 balanced (141), P1 short-airtime (103), P2 conservative
Miller4 (146). These are design choices, not recovered N701 RF settings.

The cached web initializes its P1 label to Tari 25 us / Miller4 / 250 kHz, which
instead suggests ID146. Use that choice if retaining that label/intent. Do not
route that button through the generic P1=103 proposal without changing the label
and obtaining a review decision. The supplied GReaderTool 0.39 defines speed 4 as
Miller2 and therefore suggests ID123, while the older web definition suggests
ID141. Record the actual UI build and namespace with each decision.

The reference's `select_profile()` sends 0x020A, which the supplied manual/demo
identify as Get Tag Upload Settings. Its generic profiles are not a verified vendor
feature. Keep these three proposals as application-owned presets only.

S-CST remains a separate optional ZK feature using three CFG31 slots. It is not
required to preserve NATION's continuous Start/Stop contract. The current core
does not establish its internal switching timing or actual per-round Session.

## Frequency

Use integer kHz and **channel centers**, not band edges. Prefer a native `Region`
only when its full selected center list matches the intended plan. Otherwise use
`CustomRegion(start_frequency_khz, channel_count, spacing_khz)` if representable.
There is no nearest-frequency policy: changing channel centers is a new plan.

The approved table below preserves the full center lists generated by GReaderTool 0.39,
not just its band labels. JSON `source_segments` records those lists compactly;
`centers` is the proposed ZK plan. The checker rejects channel additions/removals.
Bands 9–16 extend beyond the pinned Python driver's accepted band IDs.

| NATION band | ZK choice | Demo centers (MHz) | Count / spacing (kHz) |
|---:|---|---|---|
| 0 CN 920–925 | Native band1, channels2–17 | 920.625–924.375 | 16 / 250 |
| 1 CN 840–845 | Native band8, channels2–17 | 840.625–844.375 | 16 / 250 |
| 2 Dual band | No exact mapping | 840.625–924.375 (segmented) | 32 / mixed / segmented |
| 3 FCC | Native band2, channels0–49 | 902.750–927.250 | 50 / 500 |
| 4 ETSI (demo table) | No exact mapping | 865.700–868.100 | 5 / 600 |
| 5 JP | Native band31, channels0–3 | 916.800–920.400 | 4 / 1200 |
| 6 TW | Custom | 922.250–927.750 | 12 / 500 |
| 7 ID | Custom | 923.125–925.125 | 9 / 250 |
| 8 RUS | No exact mapping | 866.600–867.400 | 5 / 200 |
| 9 TEST | No exact mapping | 802.750–998.750 | 197 / 1000 |
| 10 JP LBT | No exact mapping | 916.800–920.800 (segmented) | 6 / mixed / segmented |
| 11 AUS | Native band26, channels4–19 | 918.250–925.750 | 16 / 500 |
| 12 KR | Native band3, channels0–31 | 917.100–923.300 | 32 / 200 |
| 13 RUS1 | Native band9, channels1–3 | 866.300–867.500 | 3 / 600 |
| 14 TL | Custom | 910.100–914.100 | 3 / 2000 |
| 15 CN4 | Native band1, channels0–19 | 920.125–924.875 | 20 / 250 |
| 16 JP LBT LP | No exact mapping | 916.800–923.000 (segmented) | 17 / mixed / segmented |

Band 7 contains nine channels at 250 kHz. Band 4 includes 865.7 and 868.1 MHz
in the demo despite its label; ZK EU3 has only four centers. Band 8 requires 200 kHz
steps at a base that no current native grid matches. Neither band gets a silent
subset or rounded custom replacement. An explicitly selected smaller set may be
representable; evaluate that set separately. Band 9 exceeds the 61-channel custom
limit. Segmented bands 2/10/16 cannot be one uniform custom range.

These are demo-table matches, not N701 hardware verification, hopping/LBT
equivalence or current regional operating permissions. Read both NATION band and
selected channel list before migration: a sparse selection must stay sparse.
Band 13 remaps UI positions to NATION wire indices; resolve centers before mapping.

Custom Region accepts 1–61 channels and spacing in multiples of 125 kHz. For one
channel, zero spacing is allowed. It cannot represent separated bands, arbitrary
sparse channel lists, or every native spacing (for example 600 or 1200 kHz).
Keep native plans with those spacings native; never round an exact requested grid
just to make Custom Region accept it. Check both hardware support and readback.

For the approved band6 plan, the native call is:

```python
result = await reader.set_custom_region(922250, 12, 500, persist=False)
result.require_success()
actual = (await reader.get_custom_region()).require_success()
if actual is None or (actual.start_frequency_khz, actual.channel_count, actual.spacing_khz) != (
    922250,
    12,
    500,
):
    raise RuntimeError("Custom Region read-back mismatch")
```

The ZK demo's Space multiplier is `spacing_khz / 125`, not the SDK argument itself.
`adapter.set_rf_band(code, persist=False)` and browser `service.setRfBand(code)`
apply the entire approved band table and verify it. They do not accept selected
channel indices. If the UI selected a subset, resolve its actual centers and use
native `set_region()` or `set_custom_region()` with that exact plan; never pass only
the band ID and silently expand the selection. Unsupported full bands fail before TX.
On Get, preserve native/custom data and expose possible legacy matches. A saved
UI hint cannot replace hardware readback after reconnect. If several presets
match, return candidates; if none match, show Custom/native rather than an invented
legacy ID. Configuration changes require idle; `persist=False` is temporary but
does not imply automatic restoration after inventory.

## Review criteria

For each choice record the source UI/firmware, intended use, chosen ZK settings,
differences and test outcome. Compare under the same antenna, tag population,
power and channel plan: unique tags found within a fixed window, time to first
read, missed tags, duplicate reports and Stop responsiveness. Use repeatable trials;
an ACK/profile readback only proves configuration acceptance. Do not assume that
a larger BLF or a newer chip improves every deployment.

## Sources

- [Supplied NATION protocol and GReaderTool 0.39 review](vendor_reference.md):
  PDF pages, decompiled handler names, conflicts and file hashes.

- [Pinned NATION source and provenance](../../compat/nation/UPSTREAM.md): API behavior,
  accepted speed codes, band labels, generic profile descriptions.
- [Nextwaves reader UI](https://app.nextwaves.com/reader), cached asset
  [0dv97g72me5ox.js](https://app.nextwaves.com/_next/static/chunks/0dv97g72me5ox.js),
  inspected 2026-10-11; SHA-256
  `09cd204f29fb7a7f29b5b8eb7c5394b8a35a6ed33d1590f344a745353103b0a7`:
  speed0–4/255 labels, A/B/alternating Target labels and P1 display text.
  This identifies the cached build, not a claim about the current deployed build.
- ZK V2.25 / Ex10 V6.8 physical definitions retained in
  [native RF profiles](../../docs/rf_profiles.md) and
  [region definitions](../../docs/rf_settings.md). Local channel/profile acceptance
  is separate from cross-reader RF equivalence.

The [current Nextwaves API reference](https://docs.nextwaves.com/en/sdk/sdk-reference)
is useful for integration concepts; use the pinned source for this map because
vendor releases and web dialects can differ.
