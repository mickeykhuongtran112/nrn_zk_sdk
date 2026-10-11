# Browser checks

From the repository root:

```sh
node --test tests/browser/demo_client.test.cjs
node --test tests/browser/nation_service.test.mjs
npm install --prefix local_data/pyodide pyodide@314.0.7
node --test tests/browser/webserial.test.mjs
```

`webserial.test.mjs` runs real Pyodide with a Web Streams port and the Python reader simulator. It covers byte conversion, native results, reports, single/multiple antenna selection and restoration, Stop during Start, verified EPC writes, uncertain writes without retry, USB loss, stream locks and recovery.

`nation_service.test.mjs` checks the migration example: one continuous Scenario
Start, user Q/Session/Target, final reports before Stop resolves, uncertain Stop,
single/multiple antenna selection and tag units without fabricated PC/phase fields.
It also checks saved antenna Set/read-back, approved baseband/region calls from the
shared policy JSON, failed writes/read-back, and EPC+TID routing to Answer FastID.
Read-back regressions retain an acknowledged Set for failed/uncertain results and
rejected Get promises, without advancing staged settings or retrying writes.
The Pyodide test injects FastID antenna error `0xF8`, checks automatic cleanup and
the JS error event, and confirms that a later Stop preserves the partial outcome.

For an interactive UI smoke check:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

Open `/tests/browser/webserial_smoke.html`. This fixture loads the production example UI with a simulated four-port reader; **Connect never opens hardware**. Check Start/Stop, tag selection, phase/RSSI, write verification and Disconnect. The real-device example is `/examples/webserial/`.
