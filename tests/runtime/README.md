# Runtime checks

The shared harness also checks Work Mode gating, temporary Real-time Start/Stop,
and draining queued reports in CPython and Pyodide.

The same `src/zk_rfid.py` runs on CPython and Pyodide. The harness covers eight
reference TX vectors, 2,000 byte-fragmented RX frames, disabled CFG11 masks, inventory, phase/RSSI,
Range Control set/read-back/restore, memory write/read-back, cancellation after TX,
and task cleanup.

```sh
python -m pytest tests/runtime -q
npm install --prefix local_data/pyodide pyodide@314.0.7
node tests/runtime/run_pyodide.mjs local_data/pyodide/node_modules/pyodide/pyodide.mjs
```

`test_standalone.py` copies the SDK to a temporary directory and runs Python with
`-I -S`, excluding site packages and `PYTHONPATH`. It checks imports, type hints,
pickling, and the optional serial dependency. It also blocks imports of mapping
and reference packages and checks that NATION adapter types are absent from core.

The Node harness copies the same module into Pyodide and provides an in-memory
async transport. It opens no serial port. Browser/Web Serial lifecycle checks are
separate under [tests/browser](../browser/README.md).

These finite software checks do not measure RF throughput or long-duration memory
stability. Runtime versions and hardware coverage are listed in
[validation](../../docs/validation.md).
