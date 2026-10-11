# Web Serial example

Browser-only demo using [ZK Web Serial](../../web/README.md) and the same `src/zk_rfid.py` as the Python SDK.

From the repository root:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open **http://localhost:8000/examples/webserial/** in Chrome or Edge. This command only serves static files; it does not open COM or run an SDK backend. Any static web server can replace it. Pyodide loads from a pinned CDN on first use.

1. Set baud rate and antenna port count. Click **Connect**, then select your reader's port.
2. Choose Scenario or Answer and an antenna, then **Start reading**. **Stop** ends the session.
3. To change EPC, stop inventory, click a tag, enter its new EPC and Access password, check **Enable this tag write**, then **Write and verify**. PC is calculated automatically.
4. Use **Disconnect** before closing the tab. Other serial applications, including the CPython web demo, must release the same COM port first.

`main.js` shows connection, events, configuration and EPC writes. For other operations, use `reader.call("native_method_name", args)` as described in the [JavaScript API](../../web/README.md).

This example reads one antenna per session. Four-port hardware is selected with **Antenna ports = 4**, then **Antenna = 1–4**; it does not automatically cycle all four ports.
