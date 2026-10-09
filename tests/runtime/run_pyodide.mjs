// Pure runtime harness, no UI/WebSerial bridge or hardware access.
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const entry = process.argv[2];
const { loadPyodide } = entry
  ? await import(pathToFileURL(path.resolve(entry)).href)
  : await import("pyodide");
const pyodide = await loadPyodide();
async function copy(source, destination) {
  pyodide.FS.mkdirTree(destination);
  for (const item of await readdir(source, { withFileTypes: true })) {
    if (item.name === "__pycache__") continue;
    const local = path.join(source, item.name);
    const target = destination + "/" + item.name;
    if (item.isDirectory()) await copy(local, target);
    else if (item.name.endsWith(".py")) pyodide.FS.writeFile(target, await readFile(local));
  }
}
await copy(path.join(root, "src/zk_rfid"), "/sdk/zk_rfid");
pyodide.FS.writeFile("/vectors.json", await readFile(path.join(root, "fixtures/zk/documented/frames.json")));
const checks = await readFile(path.join(root, "tests/runtime/runtime_checks.py"), "utf8");
const result = await pyodide.runPythonAsync(
  'import sys\nsys.path.insert(0, "/sdk")\n' + checks +
  '\njson.dumps(await run_checks("/vectors.json"))');
console.log(JSON.stringify({ pyodide: pyodide.version, ...JSON.parse(result) }, null, 2));
