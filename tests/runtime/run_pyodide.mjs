// Pure runtime harness, no UI/WebSerial bridge or hardware access.
import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const entry = process.argv[2];
const { loadPyodide } = entry
  ? await import(pathToFileURL(path.resolve(entry)).href)
  : await import("pyodide");
const pyodide = await loadPyodide();
pyodide.FS.mkdirTree("/sdk");
pyodide.FS.writeFile("/sdk/zk_rfid.py", await readFile(path.join(root, "src/zk_rfid.py")));
pyodide.FS.writeFile("/vectors.json", await readFile(path.join(root, "fixtures/zk/documented/frames.json")));
const checks = await readFile(path.join(root, "tests/runtime/runtime_checks.py"), "utf8");
const result = await pyodide.runPythonAsync(
  'import sys\nsys.path.insert(0, "/sdk")\n' + checks +
  '\njson.dumps(await run_checks("/vectors.json"))');
console.log(JSON.stringify({ pyodide: pyodide.version, ...JSON.parse(result) }, null, 2));
