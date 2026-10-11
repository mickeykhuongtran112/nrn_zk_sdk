# Compatibility

The SDK targets ZK-7180M and ZK-7182M Ex10 readers using the Gen2/6C host protocol
described in the UHF RFID Reader Series manual V2.25. Firmware options and tag-chip
support affect which commands are usable.

Hardware coverage is partial: a one-port Scenario/phase session and three reported
hardware checks are recorded in [validation](validation.md). The retained session
summary does not identify an exact model/firmware pair, so it is not a model-wide
certification.

## Reader configuration

Set `ReaderCapabilities(antenna_ports=...)` to 1, 4, 8, or 16 for the attached
module. This selects wire layouts; it does not autodetect the model or validate
firmware. `ReaderInfo` preserves model code and firmware bytes as returned.

| Feature | Implementation | Conditions |
|---|---|---|
| Framing, CRC, dispatcher | Available | One reader per connection; recovery required after uncertain exchanges |
| Reader info, serial, address, baud, interface | Available | Transport must support baud changes; interface change needs power cycle |
| Read/write power and retries | Available | 0–30 dBm; per-port arrays match the declared count |
| Antenna selection and check | Set: 1/4/8/16 ports | Full-mask getter is limited to 8 ports |
| Answer EPC, TID, FastID, phase, statistics | Available; optional ordered antenna rounds | FastID TID requires a compatible tag; multi-port RF validation pending |
| Single, EPC-match, buffered inventory | Available | EPC match: 1–196 bits, offset + length at most 496 |
| Mix EPC + memory | Available | Up to 31 words; use memory reads for longer ranges |
| Scenario EPC / TID | Start, stream, stop, restore; single/multiple antenna mask | Automatic antenna restore limited to 1/4/8 ports; multi-port hardware validation pending |
| Scenario selectors and phase | CFG9 encoding available | S-PRO/S-RPT/S-CTP algorithms unresolved; verify deployed firmware |
| S-CST custom profiles | CFG31 get/set | Ordered slots; no automatic CFG31 restore or verified switching schedule |
| Real-time, trigger, heartbeat (optional) | Available | Temporary session mode changes; stored `0x75` configuration; only info/mode operations while active |
| Normal / extended memory | Available | Read 1–120 words; ordinary write 1–32 words |
| EPC, passwords, read-back | Available | Stable or updated verification target; writes are not atomic |
| Native WriteEPC `0x04` | Available | Exactly one physical tag; 1–14 words |
| Select, Lock, Kill, BlockWrite, Erase | Available | Tag chip, capacity, protection, and available RF power |
| CFG7/8/9/10/11/31 | Available | TagFocus requires a compatible tag |
| Range Control (CFG16) | Native 0-100 get/set | Four-byte layout from demo and reader traces; RF effect is unspecified |
| CFG25/29 | Raw read; gated write | Explicitly select 6-/5-byte layouts after firmware confirmation |
| Custom Region | Set/get available | V6.8 DLL contract and one-port configuration read-back; application supplies the plan |
| Region, profile, DRM | Available | See [RF settings](rf_settings.md); no frequency conversion for bands 21/29 |
| Buffer length, count, clear, read | Available | 16-port reports require explicit antenna-field width |
| GPIO, indicator, buzzer | Available | Pins and functions must be exposed by the module |
| Temperature, return loss | Available | Sensor support; return loss limited to ANT1–4 and 100/125 kHz grids |

## Not implemented

NXP Privacy/EAS, Monza QT, EM4325, MarginRead, U9 batch lock, and tag-LED extensions
do not have a supported command contract. Relay/OUT1–4 notification controls,
a dedicated Ex10 version query, network-module
configuration, ISO 18000-6B, and NATION wire emulation are also outside the current
implementation.

See [vendor comparison](demo_and_parity.md) for the feature boundary and
[errata](protocol/errata.md) for layout decisions. The `hardware_verified` capability
is supplied by the integrator; software tests never enable it automatically.
