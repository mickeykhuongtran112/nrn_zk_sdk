# Browser checks

From the repository root:

```sh
node --test tests/browser/demo_client.test.cjs
npm install --prefix local_data/pyodide pyodide@314.0.7
node --test tests/browser/webserial.test.mjs
```

`webserial.test.mjs` runs real Pyodide with a Web Streams port and the Python reader simulator. It covers byte conversion, native results, reports, verified EPC writes, uncertain writes without retry, USB loss, stream locks and recovery.

For an interactive UI smoke check:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open `/tests/browser/webserial_smoke.html`. This fixture loads the production example UI with a simulated four-port reader; **Connect never opens hardware**. Check Start/Stop, tag selection, phase/RSSI, write verification and Disconnect. The real-device example is `/examples/webserial/`.
