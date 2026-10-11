# Tag reports

Decoding depends on the command, mode, and requested data. The SDK does not guess
whether an identifier is EPC or TID from its contents.

| Report | Layout |
|---|---|
| Answer `0x01/0x0F/0x1A` | Ant + Num + records of LenFlags, ID, RSSI, optional phase/frequency |
| FastID `0x01` | Len bit 7; ID contains EPC followed by a 12-byte TID |
| TID `0x01` | ID interpreted as TID according to the request |
| Mix `0x19` | Ant + Num + sequence/type records; pair EPC and memory by antenna and consecutive sequence, wrapping at 127 |
| Scenario `0xEE` | Ant + LenFlags + EPC or TID + RSSI + optional phase/frequency |
| Real-time `0xEE` | Basic report interpreted using stored `0x75` configuration |
| Heartbeat `0xEE`, status `0x28` | Separate `Heartbeat` event |
| Statistics, status `0x26` | Ant + rate BE16 + total BE32 |
| Buffer `0x72` | Num + records of antenna mask, length, ID, RSSI, and read count |

The low six Len bits give ID length in bytes; bit 6 indicates phase, and bit 7
indicates FastID where supported. The extension has four phase bytes and a
big-endian 24-bit frequency in kHz. See [RSSI and phase](../phase_and_live_view.md)
for conversion conventions.

`TagReport` retains raw bytes, EPC/TID/memory data, the requested bank and word
address, antenna information, and timestamp source. `received_at` is the host's
monotonic frame-receipt time, not an RF timestamp. Missing fields remain `None`.
PC is not reconstructed from EPC length.

Malformed records, missing Mix memory, queue overflow, parser loss, and timeouts
are reflected in diagnostics and outcomes. Valid EPC records are retained even
when their Mix memory record is missing. Counts of distinct reported IDs cannot
distinguish physical tags sharing an EPC.

Sources: V2.25 inventory tables and Ex10 V6.8 `RWDev.cs` / `ParamSetting.cs`.
Mix above 31 words and unconfirmed 16-port buffer layouts remain restricted by
[errata](errata.md).
