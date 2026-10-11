# ZK RFID SDK

Async Python SDK for ZK-7180M/ZK-7182M Ex10 readers using RAIN UHF Gen2 / ISO 18000-6C. Includes reader configuration, inventory, tag memory access, automatic PC calculation for EPC writes, and TX/RX tracing. No vendor DLL required.

Requires **Python 3.11+**. The entire SDK is in [src/zk_rfid.py](src/zk_rfid.py).

## Integrate

Copy `src/zk_rfid.py` into your application and install the serial dependency:

```sh
python -m pip install pyserial
```

Import everything directly from `zk_rfid`. No other project files are needed.

```python
import asyncio
from zk_rfid import ZKReader, SerialTransport, ReaderCapabilities, InventoryConfig


async def main():
    async with ZKReader(
        SerialTransport("COM13", 115200),
        capabilities=ReaderCapabilities(antenna_ports=1),
    ) as reader:
        info = (await reader.get_reader_info()).require_success()
        print(info)

        result = await reader.inventory_once(
            InventoryConfig(antenna=1, scan_time_100ms=3)
        )
        for tag in result.reports:
            print(tag.epc, tag.antenna, tag.rssi_raw)
        print(result.termination_reason, result.complete)


asyncio.run(main())
```

Set `antenna_ports=4` for a four-port module, then select `antenna=1` through `4`. Answer uses one antenna per round; Scenario uses one antenna per session. Port count is configured explicitly, not detected automatically.

Use `ZKReader` methods for device I/O. For custom transports or Pyodide, implement `AsyncTransport` instead of using `SerialTransport`.

## Run the web demo

From the repository root, in Windows CMD:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,serial]"
.venv\Scripts\python.exe -m tests.demo_app --port COM13 --baud 115200 --ports 1
```

Open [localhost:8765](http://127.0.0.1:8765), click **Connect**, then select an operation. Use **Simulated reader** to test without hardware. For continuous reading, select **Inventory → start_inventory → scenario**.

- Use `--ports 4` for a four-port module or `--http-port 8766` if the web port is busy.
- Release COM13 in other applications before connecting.
- Tag writes require **Enable this tag write**. Use **Stop inventory → Disconnect** when finished.
- Restart the Python server after SDK updates; reloading the browser is not enough.

## Tests

```bat
.venv\Scripts\python.exe -m pytest -q
```

Hardware tests are excluded by default. Hardware validation is partial; see [validation](docs/validation.md) and [supported features](docs/supported_devices.md).

## Reference

- [API and result handling](docs/api.md)
- [Function index](docs/functions_implemented.md)
- [Tag memory and EPC writes](docs/tag_memory.md)
- [Web demo guide](tests/demo_app/README.md)
- [Examples](examples)

A project license has not been selected yet. See [LICENSE](LICENSE).
