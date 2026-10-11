import { createZKReader } from "../../web/zk-rfid-webserial.js";

const $ = id => document.getElementById(id);
let reader, connected = false, running = false, busy = false, ready = false;
const rows = new Map(), logs = [];
let total = 0, paintPending = false, logPending = false;

function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}

function controls() {
  $("connect").disabled = !ready || busy || connected || !navigator.serial;
  $("disconnect").disabled = busy || !connected;
  for (const id of ["start", "once", "getPower", "setPower", "info", "region", "profile", "write"])
    $(id).disabled = busy || !connected || running || reader?.state === "unknown";
  $("stop").disabled = !connected || !running;
  for (const id of ["baud", "ports", "address"]) $(id).disabled = connected || busy;
  for (const id of ["mode", "antenna", "phase"]) $(id).disabled = running || busy;
  $("state").textContent = !ready ? "Loading SDK…" : reader?.state ?? "disconnected";
}

function log(kind, value) {
  logs.push(`${new Date().toLocaleTimeString()} ${kind} ${JSON.stringify(value)}`);
  if (logs.length > 200) logs.shift();
  if (!logPending) {
    logPending = true;
    setTimeout(() => { $("log").textContent = logs.join("\n"); logPending = false; }, 100);
  }
}

function tag(report) {
  total += report.read_count ?? 1;
  const key = `${report.epc || ""}/${report.tid || ""}/${report.antenna_mask}`;
  let row = rows.get(key);
  if (!row) {
    if (rows.size >= 1000) { const oldest = rows.keys().next().value; rows.get(oldest).element.remove(); rows.delete(oldest); }
    if (rows.size === 0) $("tags").replaceChildren();
    const element = document.createElement("tr");
    element.dataset.key = key;
    for (let i = 0; i < 6; i++) element.appendChild(document.createElement("td"));
    const button = document.createElement("button");
    button.textContent = report.epc || report.tid;
    button.disabled = !report.epc;
    button.addEventListener("click", () => { $("targetEpc").value = report.epc; notice("Tag selected. Enter a new EPC, then enable the write."); });
    element.children[0].appendChild(button);
    $("tags").appendChild(element);
    row = { element, count: 0 };
    rows.set(key, row);
  }
  row.count += report.read_count ?? 1;
  row.report = report;
  row.dirty = true;
  if (!paintPending) {
    paintPending = true;
    requestAnimationFrame(() => {
      for (const row of rows.values()) {
        if (!row.dirty) continue;
        const r = row.report, cells = row.element.children;
        const angle = n => n == null ? "—" : n.toFixed(2);
        const values = [r.antenna ?? `mask ${r.antenna_mask}`, row.count, r.rssi_raw ?? "—", r.rssi_dbm ?? "—", `${angle(r.phase_begin_degrees)} / ${angle(r.phase_end_degrees)}`];
        values.forEach((value, i) => { cells[i + 1].textContent = value; });
        row.dirty = false;
      }
      $("total").textContent = total.toLocaleString();
      $("unique").textContent = rows.size;
      paintPending = false;
    });
  }
}

function makeReader() {
  const value = createZKReader({ baudRate: Number($("baud").value), antennaPorts: Number($("ports").value), address: Number($("address").value) });
  value.addEventListener("tag", event => tag(event.detail));
  value.addEventListener("trace", event => { if ($("trace").checked) log(event.detail.kind, event.detail); });
  value.addEventListener("error", event => { notice(event.detail.message, true); log("error", event.detail); });
  value.addEventListener("state", () => controls());
  return value;
}

async function run(operation, action) {
  busy = true; controls();
  try {
    const result = await action();
    $("result").textContent = JSON.stringify(result, null, 2);
    const failed = result?.outcome && result.outcome !== "success";
    notice(`${operation}: ${result?.confirmation || result?.outcome || "complete"}`, failed);
    log(operation, result);
    return result;
  } catch (error) {
    notice(error.message, true);
    $("result").textContent = JSON.stringify({ type: error.name, message: error.message, state: error.state, result: error.result }, null, 2);
    log("error", { operation, message: error.message });
  } finally { busy = false; controls(); }
}

$("connect").addEventListener("click", () => run("Connect", async () => {
  reader = makeReader();
  const result = await reader.connect({ recover: $("recover").checked });
  connected = true; $("recover").checked = false;
  return result;
}));
$("disconnect").addEventListener("click", () => run("Disconnect", async () => {
  try { return await reader.disconnect(); }
  finally { connected = running = false; }
}));
const config = () => ({ antenna: Number($("antenna").value), phase: $("phase").checked, scan_time_100ms: 3 });
$("start").addEventListener("click", () => run("Start inventory", async () => {
  const result = await reader.startInventory({ mode: $("mode").value, config: config() });
  running = true;
  return result;
}));
$("stop").addEventListener("click", () => run("Stop inventory", async () => {
  const result = await reader.stopInventory(); running = false; return result;
}));
$("once").addEventListener("click", () => run("Inventory once", async () => {
  const result = await reader.inventoryOnce(config()); result.reports.forEach(tag); return result;
}));
$("info").addEventListener("click", () => run("Reader info", () => reader.getReaderInfo()));
$("getPower").addEventListener("click", () => run("Get power", () => reader.getPower()));
$("setPower").addEventListener("click", () => run("Set power", () => reader.setPower(Number($("power").value))));
$("region").addEventListener("click", () => run("Get region", () => reader.call("get_region")));
$("profile").addEventListener("click", () => run("Get profile", () => reader.call("get_profile")));
$("write").addEventListener("click", () => run("Write EPC", async () => {
  if (!$("allowWrite").checked) throw new Error("Enable this tag write before sending.");
  $("allowWrite").checked = false;
  const antenna = await reader.call("set_antennas", { mask: 1 << (Number($("antenna").value) - 1) });
  if (antenna.outcome !== "success") return antenna;
  const result = await reader.writeEpc({ targetEpc: $("targetEpc").value.trim(), newEpc: $("newEpc").value.trim(), accessPassword: $("password").value.trim() });
  if (result.confirmation === "read_back_verified") $("targetEpc").value = $("newEpc").value.trim();
  return result;
}));
$("ports").addEventListener("change", () => {
  $("antenna").replaceChildren(...Array.from({ length: Number($("ports").value) }, (_, i) => new Option(String(i + 1), String(i + 1))));
});
$("clear").addEventListener("click", () => { rows.clear(); total = 0; $("tags").replaceChildren(); $("total").textContent = $("unique").textContent = "0"; });
// unload cannot reliably await RF stop or stream cleanup. Keep this explicit.
window.addEventListener("beforeunload", event => { if (connected) { event.preventDefault(); event.returnValue = ""; } });

reader = makeReader();
try {
  await reader.initialize(); ready = true;
  notice(navigator.serial ? "SDK ready. Connect and select your reader's COM port." : "SDK loaded. Open this page in Chrome or Edge with Web Serial support.", !navigator.serial);
} catch (error) { notice(`SDK load failed: ${error.message}. Check your connection or self-host Pyodide.`, true); }
controls();
