# Protocol errata

These decisions resolve contradictions in the UHF RFID Reader Series User Manual
V2.25 and Ex10 Module SDK V6.8. They form part of the SDK contract.

Page numbers refer to printed manual pages; PDF page numbers are usually four
higher. The source manual has 106 PDF pages and SHA-256
`5f4675a61bcab11a214422c70d3aa24e2ace3d7ac10ab888e958b21636d5d0be`.
Vendor manuals, DLLs, and demo source are not distributed here.

| Item | SDK behavior |
|---|---|
| Password length, p.12 | Kill and Access passwords are each 32 bits, following the command definitions |
| Reader-info `0x21` example length | Requires the 12-byte data layout from the field table |
| Power `0x94` response shown as `0x51`, p.97 | Matches `0x94`, consistent with historical traces; `0x51` belongs to Scenario stop |
| CFG25/29 summary says 10 bytes; detail says 6/5, pp.99/101 | Raw getters; setters require explicit `cfg25_length=6` / `cfg29_length=5` |
| CFG16 absent from V2.25 table | Implements V6.8 Range Control as `00 00 00 value`, 0-100; operator traces confirm GET 100 and SET/read-back 90. No RF-unit conversion |
| WriteEPC `0x04`: ENum < 15 versus 31-word field, pp.21–22 | Limits `0x04` to 1–14 words; targeted PC + EPC write supports up to 31 EPC words |
| Extended `0x16` heading says reading | Uses the write frame and payload definition |
| `0x50/0x51` also assigned to 6B commands | Uses Ex10 Gen2 context; 6B is not implemented |
| Stop `0x93`, p.98 | Interrupts pending `0x01`; waits for original inventory completion, not an ACK93 |
| CFG9 names differ across manuals/demo | `ScenarioSession` names preserve native values; see source notes below |
| Scenario Target A\|B in C# demo | SDK accepts 0 (A) and 1 (B); value 2 remains unresolved |
| Scenario pre-Select differs from demo | SDK sends no preparatory Select; no claim of identical initial tag state |
| CFG31 custom profiles | Three ordered slots; no activation by setter, automatic session restore, or assumed dwell schedule |
| CFG11 disabled mask | Zero bit length returns `None`, including `00000000` observed on model code `0x71`, firmware bytes `02 08`. Raw bytes are preserved; active masks and outgoing fields remain validated |
| Real-time `0x77` after clearing a mask | A zero mask length disables selection even if the fixed 32-byte buffer retains old data; raw bytes are preserved and active-mask padding is still validated |
| Work Mode `0x76` Save flag omitted by V2.25 | V6.8 `btSetMmode_Click` sets bit 7 when Save is unchecked. SDK defaults to temporary writes; one-port firmware `02 08` accepted `81/80` and returned modes `1/0`. Power-cycle retention remains untested |
| Post-Stop `0xEE` in an operator capture | CRC-valid frame with invalid antenna `0x62` followed the mode ACK; reproduced on one-port firmware `02 08` during follow-up. Stop retains bounded trailing frames separately and reports partial; active report validation stays strict |
| CFG7 default dwell 0 versus range 2–255 | Accepts 0 or 2–255; rejects 1 |
| Mix length 120 words versus six length bits plus phase flag | Limits Mix to 31 words; longer reads use `read_memory()` |
| Phase conversion differs between demo branches | Keeps raw begin/end; defaults to `raw × 0.087 mod 180`; see [measurements](../phase_and_live_view.md) |
| Inconsistent GPIO pin/bit descriptions | Two output bits 0/1; getter input bit 0 and output bits 4/5; confirm physical pins |
| 16-port buffer antenna field: one or two bytes | Requires explicit `buffer_antenna_bytes` |
| Reader-info antenna mask is one byte | Full-mask getter and automatic Scenario restore are not supported for 16 ports |
| Discontinuous frequencies in bands 21/29 | Native set/get supported; frequency-conversion helper rejects these bands |
| Buffer `0x70` “length” | Maximum EPC/TID record length, 16 or 62 bytes, not buffer capacity in kB; manual gives 528/160 tags respectively |
| Return-loss `0x91` antenna range 0–3 | Diagnostic API is limited to ANT1–4 |

A firmware-specific resolution needs the model, firmware revision, raw request
and response, relevant RF/tag conditions, and a regression vector. The SDK does
not silently switch layouts after a command has already been transmitted.

## Scenario sources

| Source | What it establishes |
|---|---|
| Reader manual V2.25, CFG9 / CFG31 | Basic session selectors, Auto=255, three custom profile slots; defaults 103/241/285 |
| Windows VC DLL manual V3.5, sections 3.8.2.3 / 3.8.2.11 | S-PRO=254, S-RPT=253; calls 128 S-CTM in CFG9 and S-CST in CFG31 |
| Linux C library manual V1.5, sections 4.2.3 / 4.2.8 | Calls 128 Custom-Profile; explicitly describes CFG31 as profile order |
| C# demo V6.8, `ParamSetting.cs` | S-CST=128, S-CTP=252, S-RPT=253, S-PRO=254; phase at CFG9 bit 4 |
| C# demo V6.8, `Form1.cs`, Scenario Start | Prepares S2 then S3 with Select for S-PRO/S-CST; passes the selected Target to Start |
| Android demo V3.82, `ScanMode.java` | Uses selector 128 for presets; allows repeated profile IDs and separate Gen2X presets |
| Java `CReader_Uhf.jar`, `BaseReader.StartSceneMode` | Sends command 0x50 with Target; no host profile scheduler in that call |

These sources establish host configuration, not the firmware's per-round Session,
Target, profile dwell, or switching conditions. The Answer AUTO-2/AUTO-3 scheduler
in the demo belongs to a separate code path. No S-PRO/S-RPT/S-CTP algorithm is
asserted by this SDK, and S-CTM (128) must not be confused with S-CTP (252).

Region names and demo controls follow V2.25 pp.61-62 and V6.8 `Form1.cs` /
`Form1.Designer.cs`. RF profile metadata follows V2.25 pp.85-86; it is retained as
documented, including encoding labels. Neither table is firmware autodetection.

Custom Region follows V6.8 `Form1.cs` and the x64 `UHFReader288.dll` exercised over
localhost. Set uses `0x22: flag FF spacing count start[3]`; Get uses `0x9E` and
returns `FF spacing count start[3]`. Start is big-endian kHz; spacing is in 125 kHz
units. Native regions retain the three-byte band/max/min response. The demo offers
counts 1–61. Loopback verifies the DLL wire contract, not RF tuning or compliance.

For CFG11, Linux C manual V1.5 section 4.2.5 explicitly defines zero bit length as
masking disabled. V2.25 pp.100-101 gives the four-byte header and data-length rule.
V6.8 `ParamSetting.cs` clears the displayed mask data when length is zero and
does not reject an inactive bank value in a successful response. The SDK therefore
returns `None` for an exact four-byte, zero-length response, regardless of its
unused bank/address fields. Extra bytes and malformed active masks remain errors.
This does not allow reserved banks in outgoing mask commands.

The same reader retained old mask data in the fixed `0x77` buffer after clearing
CFG11. V6.8 `Form1.cs`, `btMGetParameter_Click`, displays only the byte count
derived from MaskLen, so zero length displays no data. The SDK ignores this
inactive buffer when decoding a disabled mask; the 44-byte frame layout and
validation of active masks remain unchanged.
