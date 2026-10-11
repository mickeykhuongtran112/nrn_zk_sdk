# RF profiles

Known native Ex10 IDs from the SDK's `PROFILES` table. See [RF settings](rf_settings.md)
for selection and [Inventory](inventory_modes.md#s-cst) for S-CST slots.

Generated with `python tools/export_symbols.py`; edit source metadata to update it.
Availability depends on reader firmware and tag support. Encoding labels are retained
from the manual; these entries are not measured performance or detected capabilities.

| ID | Modulation | PIE | Tari (us) | BLF (kHz) | Encoding |
|---:|---|---:|---:|---:|---|
| 1 | PR_ASK | 2.0 | 7.5 | 640 | Miller2 |
| 3 | PR_ASK | 2.0 | 20.0 | 320 | Miller2 |
| 5 | PR_ASK | 2.0 | 20.0 | 320 | Miller4 |
| 7 | PR_ASK | 2.0 | 20.0 | 250 | Miller4 |
| 11 | PR_ASK | 2.0 | 7.5 | 640 | FM0 |
| 12 | PR_ASK | 2.0 | 15.0 | 320 | Miller2 |
| 13 | PR_ASK | 2.0 | 20.0 | 160 | Miller8 |
| 15 | PR_ASK | 2.0 | 7.5 | 640 | Miller4 |
| 102 | PR_ASK | 2.0 | 7.5 | 640 | FM0 |
| 103 | DSB | 1.5 | 6.25 | 640 | FM0 |
| 104 | DSB | 1.5 | 6.25 | 320 | FM0 |
| 120 | DSB | 1.5 | 6.25 | 640 | Miller2 |
| 123 | PR_ASK | 2.0 | 20.0 | 320 | Miller2 |
| 124 | PR_ASK | 2.0 | 7.5 | 640 | Miller2 |
| 125 | PR_ASK | 2.0 | 15.0 | 320 | Miller2 |
| 126 | PR_ASK | 1.5 | 12.5 | 320 | Miller2 |
| 141 | PR_ASK | 2.0 | 20.0 | 320 | Miller4 |
| 146 | PR_ASK | 2.0 | 20.0 | 250 | Miller4 |
| 147 | PR_ASK | 2.0 | 7.5 | 640 | Miller4 |
| 148 | PR_ASK | 1.5 | 7.5 | 640 | Miller4 |
| 185 | PR_ASK | 2.0 | 20.0 | 160 | Miller8 |
| 202 | PR_ASK | 2.0 | 15.0 | 426 | FM0 |
| 203 | PR_ASK | 1.5 | 12.5 | 426 | FM0 |
| 205 | PR_ASK | 2.0 | 20.0 | 50 | FM0 |
| 222 | PR_ASK | 2.0 | 20.0 | 320 | Miller2 |
| 223 | PR_ASK | 2.0 | 15.0 | 320 | Miller2 |
| 224 | PR_ASK | 1.5 | 12.5 | 320 | Miller2 |
| 225 | PR_ASK | 2.0 | 15.0 | 426 | Miller2 |
| 226 | PR_ASK | 1.5 | 12.5 | 426 | Miller2 |
| 241 | PR_ASK | 2.0 | 20.0 | 320 | Miller4 |
| 244 | PR_ASK | 2.0 | 20.0 | 250 | Miller4 |
| 285 | PR_ASK | 2.0 | 20.0 | 160 | Miller8 |
| 302 | PR_ASK | 2.0 | 7.5 | 640 | FM0 |
| 323 | PR_ASK | 2.0 | 7.5 | 640 | Miller2 |
| 324 | PR_ASK | 2.0 | 20.0 | 320 | Miller2 |
| 325 | PR_ASK | 2.0 | 15.0 | 320 | Miller2 |
| 326 | PR_ASK | 1.5 | 12.5 | 320 | Miller2 |
| 342 | PR_ASK | 2.0 | 20.0 | 320 | Miller4 |
| 343 | PR_ASK | 2.0 | 20.0 | 250 | Miller4 |
| 344 | PR_ASK | 2.0 | 7.5 | 640 | Miller4 |
| 345 | PR_ASK | 1.5 | 7.5 | 640 | Miller4 |
| 382 | PR_ASK | 2.0 | 20.0 | 160 | Miller8 |
| 4123 | PR_ASK | 2.0 | 20.0 | 320 | PSK2 |
| 4124 | PR_ASK | 2.0 | 7.5 | 640 | BPSK2 |
| 4141 | PR_ASK | 2.0 | 20.0 | 320 | BPSK4 |
| 4146 | PR_ASK | 2.0 | 20.0 | 250 | BPSK4 |
| 4148 | PR_ASK | 1.5 | 7.5 | 640 | BPSK4 |
| 4185 | PR_ASK | 2.0 | 20.0 | 160 | BPSK8 |
| 5123 | PR_ASK | 2.0 | 20.0 | 320 | M+B2 |
| 5124 | PR_ASK | 2.0 | 7.5 | 640 | M+B2 |
| 5141 | PR_ASK | 2.0 | 20.0 | 320 | M+B4 |
| 5146 | PR_ASK | 2.0 | 20.0 | 250 | M+B4 |
| 5148 | PR_ASK | 1.5 | 7.5 | 640 | M+B4 |
| 5185 | PR_ASK | 2.0 | 20.0 | 160 | M+B8 |
