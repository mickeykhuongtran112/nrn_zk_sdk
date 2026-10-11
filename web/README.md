# ZK Web Serial integration

JavaScript API for the **same [zk_rfid.py](../src/zk_rfid.py)** used by the Python SDK. Pyodide runs Python in the browser; Web Serial supplies bytes. CRC, commands, responses, inventory, PC calculation and measurements remain in the Python SDK.

No Python backend, pyserial, vendor DLL or NATION runtime is used. The default loader downloads Pyodide **314.0.7** from jsDelivr. Use Chrome/Edge with Web Serial on HTTPS or localhost.

## Connect and read

```js
import { createZKReader } from "./web/zk-rfid-webserial.js";

const reader = createZKReader({ baudRate: 115200, antennaPorts: 1 });
await reader.initialize(); // Optional preload before enabling your Connect button.

reader.addEventListener("tag", ({ detail: tag }) => {
  console.log(tag.epc, tag.antenna, tag.rssi_raw, tag.rssi_dbm);
});
reader.addEventListener("error", ({ detail }) => console.error(detail));
reader.addEventListener("trace", ({ detail }) => console.debug(detail));

connectButton.onclick = async () => {
  await reader.connect(); // Keep this call inside a user click: opens the port picker.
  console.log(await reader.getReaderInfo());
  await reader.startInventory({ mode: "scenario", config: { antenna: 1, phase: true } });
};
stopButton.onclick = () => reader.stopInventory();
disconnectButton.onclick = () => reader.disconnect();
```

Set `antennaPorts: 4` for a four-port module. Select one antenna per Answer round / Scenario session. `inventoryOnce(config)` returns an outcome with `reports`; continuous inventory emits `tag` events. Stop/disconnect explicitly before leaving the page: tab closure cannot guarantee an RF stop.

## Configuration and EPC write

```js
await reader.setPower(20); // Global power. On a 4-port reader, [20, 20, 20, 20] sets each port.
const profile = await reader.call("get_profile");
await reader.call("set_antennas", { mask: 1 }); // ANT1, volatile by default.

const result = await reader.writeEpc({
  targetEpc: "11111111", // Current EPC.
  newEpc: "E2801111222233334444555566667777",
  accessPassword: "00000000",
});
console.log(result.outcome, result.confirmation); // success / read_back_verified
```

`writeEpc()` reads PC, preserves its non-length bits, writes PC + EPC, and verifies by selecting the new EPC. It uses the reader's enabled antennas; stop inventory first. The helper uses full-EPC targets (up to 15 words); use `call("write_epc", ...)` with a stable TID mask for longer EPCs.

## Other native operations

`call(name, args)` exposes the 72 public `ZKReader` operations other than `open`/`close`, which are handled by `connect`/`disconnect`. Names and arguments match the [Python API](../docs/functions_implemented.md).

```js
const result = await reader.call("read_memory", {
  bank: 3, word_address: 0, word_count: 2,
  target: { epc: "E2801111222233334444555566667777" },
  access_password: "00000000",
});
```

- Bytes are hex strings; dataclasses are objects; enums use their string/integer values.
- Results preserve `outcome`, `status`, `tag_error`, `raw_data`, `confirmation` and `steps`. A resolved Promise can contain `failure`, `partial` or `unknown`; inspect the result.
- Python exceptions reject with `ZKSDKError`, preserving the native exception name, reader state, transmitted flag and result when available. Writes are never retried automatically.
- `tag` reports retain RSSI raw, the user-defined dBm estimate, phase units and conversion metadata. Throttle DOM painting, not the report counter.
- The transport yields to browser tasks periodically when RX is already buffered, keeping Stop and rendering responsive without discarding reports.
- `set_baudrate` is rejected before TX on this transport. Configure both reader and browser baud beforehand; Web Serial does not change baud on an open port.
- After timeout/unplug, reset or resynchronize the module before `connect({ recover: true })`. This flag asserts recovery; it does not reset hardware. The in-memory recovery guard cannot survive a page reload.
- All Python SDK model/firmware limitations still apply. This bridge does not add multi-antenna scheduling or new device commands.

## Add to an existing frontend

Serve these files as static assets, keeping their relative layout or supplying explicit URLs:

```text
src/zk_rfid.py
web/zk_browser.py
web/zk-rfid-webserial.js
web/zk-rfid-webserial.d.ts   # TypeScript declarations, optional at runtime.
```

```js
const reader = createZKReader({
  sdkURL: "/assets/zk_rfid.py",
  bridgeURL: "/assets/zk_browser.py",
  // pyodide: yourPreloadedPyodide, // Optional self-hosted runtime.
});
```

For Vite/React/Next.js, copy the Python files into public assets and use explicit URLs; run this module client-side. Load one SDK version per Pyodide interpreter. For offline deployments, self-host the Pyodide runtime and pass its loaded instance. Allow its script/WASM/assets in your CSP and grant `serial` permission if embedding in an iframe.

The Python source is loaded directly; there is no generated or copied protocol implementation in JavaScript. The local HTTP demo under `tests/demo_app` continues to use CPython + pyserial and is a separate way to run the same SDK.

## Checks

```sh
npm install --prefix local_data/pyodide pyodide@314.0.7
node --test tests/browser/webserial.test.mjs
```

The integration test uses real Pyodide, Web Streams and the ZK simulator with fragmented bytes. It checks commands, tag reports, phase/RSSI, PC + EPC readback, errors and connection cleanup. Physical Web Serial hardware validation remains pending.

References: [Nextwaves NW SDK layout](https://github.com/Nextwaves-Industries/nextwaves-sdk/tree/d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b/sdk/nw_sdk), [Nextwaves browser example](https://github.com/Nextwaves-Industries/nextwaves-sdk/tree/d416b0d3bd5a103cf6b1833b13f0c88e9dfbe24b/examples/webserial), [Web Serial API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Serial_API), [Pyodide type conversion](https://pyodide.org/en/stable/usage/type-conversions.html). The bridge is implemented for this project's API; no upstream driver code is included.
