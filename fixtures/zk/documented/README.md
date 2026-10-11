# Documented ZK vectors

[frames.json](frames.json) contains eight expected TX frames imported on 2026-10-09
from the historical `nation-zk-python` reference's `test_vendor_golden_frames`
and protocol notes. Their original source was Ex10 V6.8 `UHFReader288.dll`
operating against a loopback.

These bytes provide an independent CRC/format reference. They do not validate RF
behavior or the currently connected firmware. Tests require neither that earlier
project nor the DLL. The additional CRC check is `123456789 → 0x6F91`.

See the [fixture conventions](../../README.md).
