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
| WriteEPC `0x04`: ENum < 15 versus 31-word field, pp.21–22 | Limits `0x04` to 1–14 words; targeted PC + EPC write supports up to 31 EPC words |
| Extended `0x16` heading says reading | Uses the write frame and payload definition |
| `0x50/0x51` also assigned to 6B commands | Uses Ex10 Gen2 context; 6B is not implemented |
| Stop `0x93`, p.98 | Interrupts pending `0x01`; waits for original inventory completion, not an ACK93 |
| CFG9 demo sessions/phase exceed manual table | Explicit scene-session values 128/252/253/254 and phase bit 4; no inferred Gen2 mapping |
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
