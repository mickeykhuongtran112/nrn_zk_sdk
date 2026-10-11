# ZK RFID SDK

An async Python SDK for ZK-7180M and ZK-7182M Ex10 UHF RFID readers. Read tags,
configure the reader, and access Gen2 tag memory through a single Python module.
The SDK implements the reader protocol directly and requires no vendor DLL.

**Python 3.11+ · CPython and Pyodide · MIT license**

[Getting started](docs/getting_started.md) · [Examples](examples/README.md) ·
[Python API](docs/api.md) · [Browser integration](web/README.md) ·
[Compatibility](docs/supported_devices.md)

## Install

From a checkout or extracted source archive:

```sh
python -m pip install ".[serial]"
```

For applications that vendor their dependencies, copy
[`src/zk_rfid.py`](src/zk_rfid.py) and [LICENSE](LICENSE) into your project, then
install `pyserial`. The SDK has no other runtime dependencies. Custom transports
and browser applications do not need `pyserial`.

## Read tags

Connect an antenna and set the port, baud rate, and antenna count for your reader.
This example uses `COM3` at 115200 baud; on Linux, use a path such as `/dev/ttyUSB0`.

```python
import asyncio

from zk_rfid import InventoryConfig, ReaderCapabilities, SerialTransport, ZKReader


async def main():
    async with ZKReader(
        SerialTransport("COM3", 115200),
        capabilities=ReaderCapabilities(antenna_ports=1),
    ) as reader:
        info = (await reader.get_reader_info()).require_success()
        print("Firmware:", info.firmware)

        result = await reader.inventory_once(
            InventoryConfig(antenna=1, scan_time_100ms=3)
        )
        for tag in result.reports:
            print(tag.epc.hex().upper() if tag.epc else None, tag.antenna, tag.rssi_raw)
        print("Round:", result.termination_reason, "complete:", result.complete)


asyncio.run(main())
```

Set `antenna_ports` to the physical port count. Antenna IDs start at 1; Answer
inventory reads one antenna per round. A completed round describes the protocol
transaction, not a guarantee that every tag in the RF field was read.

## Choose an integration

| Application | Start here |
|---|---|
| Python service, desktop app, or test system | [Python guide](docs/getting_started.md) and [runnable examples](examples/README.md) |
| JavaScript or TypeScript frontend | [Web Serial bridge](web/README.md), using the same Python SDK in Pyodide |
| Reader evaluation without application code | [Local test console](tests/demo_app/README.md), with a built-in simulator |
| Existing NATION application | [Adapter guide](docs/nation_comparison.md) |

The browser example runs from a static server:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open [the Web Serial example](http://localhost:8000/examples/webserial/) in Chrome
or Edge, click **Connect**, and select your reader. The first load downloads the
pinned Pyodide runtime; see the bridge guide for offline hosting.

## Documentation

- [Inventory](docs/inventory_modes.md): Answer, Scenario, Real-time, FastID, and Mix.
- [Tag memory](docs/tag_memory.md): memory map, targeting, EPC writes, and read-back.
- [Results and recovery](docs/api.md): native errors, timeouts, and connection state.
- [RSSI and phase](docs/phase_and_live_view.md): units and conversion conventions.
- [Protocol reference](docs/protocol/zk_frame.md): framing, commands, and errata.

This is a development release. Software checks cover the protocol and lifecycle;
hardware validation is limited to the sessions recorded in
[validation](docs/validation.md). Check [compatibility](docs/supported_devices.md)
for firmware-dependent features before integrating them.

## Development

```sh
python -m pip install -e ".[dev,serial]"
python -m pytest
```

Hardware tests are opt-in. See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete
checks and repository conventions, and [CHANGELOG.md](CHANGELOG.md) for changes.

## License

The SDK is independently maintained and released under the [MIT license](LICENSE).
The NATION reference driver retains its [upstream license](compat/nation/LICENSE).
Vendor manuals and binaries are not distributed with this project.
