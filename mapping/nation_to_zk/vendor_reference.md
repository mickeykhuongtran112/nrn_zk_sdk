# NATION source notes

Use the deployed web's actual settings and command payloads when choosing a mapping.
The supplied protocol PDF, GReaderTool 0.39 and the pinned Nextwaves driver are
different sources; their numeric IDs are not interchangeable. The [RF worksheet](rf_mapping.md)
keeps their differences explicit. The project selected GReaderTool 0.39; the adapter
applies its approved choices on explicit configuration calls only.

## Evidence

Reviewed from SDK-EN-20250828 on 2026-10-11:

| Source | Relevant locations |
|---|---|
| RFID Reader Data Communication Protocol, 81 pages | pp.10–12: framing; pp.50–62: configuration; pp.64–67: EPC inventory and reports; p.78: Stop |
| RFID Demo Operation Manual-C#, 74 pages | pp.52–54: baseband controls; pp.56–59: frequency selection |
| GReaderTool.exe, file version 0.39.0.0, folder Demo_0.39.0.0_20250307 | `FrmRfidSettings.InitBase`, baseband/frequency Get/Set handlers; `FrmBaseDialog.InitFrequency`; `MainForm.GetReadParam` and Start/Stop handlers |
| GReaderApi.dll bundled with that demo | `MsgBaseSetBaseband`, `MsgBaseInventoryEpc`, `MsgBaseStop`, `MsgBaseSetFrequency`, `MsgBaseGetCapabilities`, report decoders |
| Supplied C# example `Example.cs` | One continuous EPC+TID Start, asynchronous tag/end events, explicit Stop |

PDF tables and embedded UI screenshots were inspected. The demo's controls and
handlers were inspected by decompiling the supplied .NET binaries; original demo
source was not included in that folder. Live GUI inspection was unavailable because
the desktop helper failed to initialize. No NATION device was queried, and a menu
entry does not establish support on every N701 firmware. Vendor PDFs, binaries and
decompiled files remain outside the public package.

SHA-256 identifies the inspected copies:

| File | SHA-256 |
|---|---|
| Protocol PDF | `6f111e8aaa9def8b7b2c9a1c3d59d25a654826748b7c9131628cfa558b713dc8` |
| Demo manual PDF | `ac04d41dfb01960d7366382f31e0cd7b322cc2f8f1cbeb8693976dd80712d621` |
| GReaderTool.exe | `7508532d33b10d5cbc6b24dfbec188cad0487f9aafe1a42a387ca2ec424b823b` |
| GReaderApi.dll | `079d6b59848b52707e216b69296a6791d6a93c30f9fcd156ce915d2450b46613` |

## Inventory

Protocol p.64 defines mode 0 as one pass over the enabled antennas, then idle;
mode 1 continues until Stop. The demo uses `MsgBaseInventoryEpc` with an antenna
bitmask and the selected `InventoryMode`. The supplied C# example sets
`eInventoryMode.Inventory` (1), subscribes to EPC tag/end events, sends Start once,
then sends `MsgBaseStop`. NATION therefore supports single reads too; the pinned
driver's public Start chooses continuous reads.

Use ZK Scenario for the existing continuous EPC workflow. For single reads use
Answer explicitly. Both continuous paths accept selected antennas, but switching
timing is not established as equivalent. Continuous combined EPC+TID needs a
separate ZK workflow; see the [API map](api_map.md). Keep confirmed Stop and queue drain
even if a demo handler sends Stop asynchronously and immediately updates its UI.

## Baseband and frequency

Protocol p.60 and the older demo manual describe speed 4 as 25 us / Miller4 /
320 kHz. Protocol p.61 inconsistently marks 4–254 reserved. GReaderTool 0.39
`InitBase` instead defines speed 4 as 20 us / Miller2 / 320 kHz, and adds speeds
5, 6, 7, 10, 11, 12 and 13. These require a versioned mapping, not a merged lookup.
The demo labels speeds 1 and 3 as Dense/Fast; their physical values in the worksheet
come from protocol p.60 and the cached web labels, not an N701 RF measurement.

The demo sends speed/Q/Session/Target through `MsgBaseSetBaseband` (RFID MID 0x0B),
with parameter IDs 0x01/0x02/0x03/0x04. Session is 0–3; Target is A/B/alternating.
Optional PIDs 0x05–0x0B cover Tari, DR, RTcal, TRcal, PW, modulation depth and Miller.
Do not copy those selector bytes to ZK; the current ZK API offers fixed profiles,
not independently writable values for all these controls. Manual baseband overrides
can make a speed ID alone insufficient to describe the active RF settings.

The demo initializes persistence to save; unchecking its save control emits
`IsPersistence=0` (baseband PID 0xFF). Pass ZK `persist` explicitly; its default is
volatile. This policy does not belong in the profile-number translation.

Frequency band and selected channels are separate NATION commands: MID 0x03/0x04
select/query the band, while 0x05/0x06 select/query auto mode and channel indices.
Protocol pp.57–58 permits sparse lists. Resolve indices using the correct band,
then compare the entire center list against ZK. A range from the first to last
selected channel would silently add channels to a sparse selection.

The demo contains 17 band tables, beyond the pinned driver's 0–8. Band 4 generates
five centers, 865.7 through 868.1 MHz at 600 kHz, despite its `ETSI866_868` label.
Band 7 uses nine centers at 250 kHz; band 8 uses five at 200 kHz. These are demo
table facts, not regional operating permissions. See [RF choices](rf_mapping.md)
for exact representations and unsupported sets. Band 13's Set Frequency handler
converts list position `i` to NATION wire index `3*i+1`; never reuse UI positions
as native ZK indices. Its Get handler indexes the displayed list directly, so
round-trip index interpretation needs device evidence.

## Reference conflicts

The API map inventories the pinned Python source faithfully; it is not a validated
NATION protocol implementation. The supplied manual identifies these conflicts:

| Pinned source claim | Supplied protocol / demo | Migration decision |
|---|---|---|
| `select_profile(0..2)` sends 0x020A | RFID MID 0x0A queries tag-upload filters, pp.59–60; demo uses `MsgBaseGetTagLog` | Treat generic P0/P1/P2 as proposed application presets, not recovered NATION firmware profiles. |
| `QUERY_RFID_ABILITY = 0x1000` | RFID MID 0x00, pp.50–52; demo `MsgBaseGetCapabilities`. Protocol p.11 makes bit 12 a notification flag. | Do not construct a host capability request from that constant. ZK capabilities remain explicitly configured. |
| Antenna constants alias RF-band/power opcodes | Command list p.51 assigns antenna configure/query MID 0x07/0x08 | Map antenna intent, never forward the aliased numbers. |
| `PHASE_INVENTORY = 0x0214` | p.51 reserves MID 0x14; demo exposes phase in EPC reports | No verified dedicated phase command from this manual. Use native ZK phase configuration. |
| `READ_END = 0x1231` | pp.51,67 define EPC-end notification MID 0x01 in the RFID class, with the notification flag set | Use native lifecycle events; do not carry the Python constant into the ZK parser. |

Keep the licensed reference unchanged so these differences remain reviewable.
The complete 64-callable/30-constant coverage applies to that pinned driver, not
to every API in the much larger vendor DLL.
