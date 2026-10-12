# Vendor feature comparison

This comparison covers the ZK manual V2.25, Ex10 C# demo V6.8, and the pinned
[NATION reference](../compat/nation/UPSTREAM.md). The SDK implements the main
Gen2 reader workflows; it does not implement every vendor-demo control.

## Coverage

| Vendor feature | SDK equivalent or limit |
|---|---|
| Serial connection, info, serial number, address, baud | Native reader methods |
| Region, power, write power/retries, DRM | Native configuration; no automatic NATION RF mapping |
| Antenna control, temperature, return loss | Implemented with [layout limits](supported_devices.md) |
| Buzzer, GPIO, reader indicator | Implemented; reader indicator is not a tag-LED command |
| Answer EPC/TID/FastID/Mix and phase | Implemented; Mix limited to 31 words |
| Scenario query/TID/mask | Managed start/stop; changed CFG9/10/11 and antenna settings restored after confirmed stop |
| Scenario custom profiles | CFG31 get/set; three ordered slots, separate from session cleanup |
| S-PRO/S-RPT/S-CST/S-CTP selectors | Native CFG9 encoding; no emulation of firmware scheduling or demo pre-Select sequence |
| Scenario A\|B target | Demo option; SDK accepts only A or B pending firmware confirmation |
| Real-time/trigger configuration | Implemented; trigger requires suitable wiring/firmware |
| Buffer inventory, read, clear, count | Implemented; 16-port format requires confirmation |
| Memory, EPC/PC, passwords, BlockWrite/Erase | Implemented with explicit targeting and optional read-back |
| Gen2 Lock and Kill | Implemented; irreversible operations require deliberate tag selection |
| Range Control | CFG16 get/set, native 0-100; RF scale unspecified |
| Relay, OUT1–4 notification pulse | No corresponding API |
| Custom frequency start/count/spacing | `set_custom_region()` / `get_custom_region()`; Web Serial methods available |
| Dedicated Ex10 version query | No corresponding API |
| MarginRead, U9 batch lock, tag LED | Not implemented |
| NXP Privacy/EAS, Monza QT, EM4325 | No supported tag-specific contract |
| Network module configuration, ISO 18000-6B | Outside scope |

The [test console](../tests/demo_app/README.md) exposes public reader operations plus connection
open/close. That coverage is checked against public `ZKReader` methods; it is not
a claim that every vendor control or firmware feature is supported.

## Interpreting results

| Response | Meaning |
|---|---|
| Setter `0x00` | Acknowledged; persistence still requires a power-cycle check |
| Getter `0x00` with valid payload | Decoded native data |
| `0xF9` | Native command failure |
| `0xFC` with data `04` | Tag error: memory locked |
| `0x13` | Partial outcome: saving failed |
| Deadline after TX | Unknown outcome; command is not retried |
| Validation exception before TX | Local argument error; no new command sent |
| Answer `0x03/01/02/04/26` | More frames / completion / timeout / buffer full / statistics |
| Write followed by matching read-back | `read_back_verified` with the individual steps retained |

See [validation](validation.md) for the evidence behind implemented behavior and
[errata](protocol/errata.md) for firmware-specific restrictions.
