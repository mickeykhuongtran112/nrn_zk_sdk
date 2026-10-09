"use strict";
const $ = id => document.getElementById(id);
const make = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) if (child != null) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return node;
};
const iconPaths = {
  reader: ['M8 3h8v18H8z', 'M11 7h2M11 11h2M5 7H3m2 5H3m2 5H3m16-10h2m-2 5h2m-2 5h2'],
  antenna: ['M12 13v8m-4 0h8M8 10a6 6 0 0 1 8 0M5 7a10 10 0 0 1 14 0', 'M12 10v.01'],
  scan: ['M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M4 12h16'],
  tag: ['M3 4h8l10 10-7 7L3 10z', 'M7 8h.01'],
  settings: ['M4 6h4m4 0h8M4 12h10m4 0h2M4 18h2m4 0h10', 'M8 3v6m6 0v6M6 15v6'],
  pulse: ['M2 12h5l3-8 4 16 3-8h5'],
  buffer: ['M4 4h16v5H4zM4 15h16v5H4zM7 6.5h.01M7 17.5h.01'],
  diagnostics: ['M4 20V4m0 16h16M8 15l4-6 4 3 4-7'],
  grid: ['M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'],
  info: ['M12 16v-4m0-4h.01', 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0'],
  refresh: ['M20 7V3l-3 3a8 8 0 1 0 3 9M20 7h-5'],
  stop: ['M6 6h12v12H6z'],
  arrow: ['M4 12h16m-5-5 5 5-5 5'],
  download: ['M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5'],
};
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key, value] of Object.entries({class:'icon', viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':'1.6', 'stroke-linecap':'round', 'stroke-linejoin':'round', 'aria-hidden':'true', focusable:'false'})) svg.setAttribute(key, value);
  for (const d of iconPaths[name] || iconPaths.grid) {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path'); path.setAttribute('d', d); svg.append(path);
  }
  return svg;
}
const groupIcons = {Reader:'reader', 'RF & antenna':'antenna', Inventory:'scan', 'Tag memory':'tag', 'Ex10 config':'settings', 'Real-time':'pulse', Buffer:'buffer', 'I/O & diagnostics':'diagnostics', 'All APIs':'grid'};
let token, catalog = [], group = "Reader", selected, readers = {}, cursor = 0, events = [], paused = false;
let snapshot = null, lastResultKey = "", advancedOverride = null, selectedTarget = null, source = false, polling = false;
let selectedTagKey = null, lastEventsView = '';
const liveTags = new Map(), tagNodes = new Map();
let liveSummary = null, paintPending = false, lastResultId = '';
let liveConnected = false, liveSupported = true, liveEpoch = 0, tagGeneration;
let liveFailure = 'Waiting for live stream';
const titles = {
  "Reader": "Read identity and configure the connected module.",
  "RF & antenna": "Native power, antenna masks, channel tables and RF profiles.",
  "Inventory": "Observe EPC / TID reports and control the complete inventory lifecycle.",
  "Tag memory": "Explicit tag selection, word addressing and verified memory operations.",
  "Ex10 config": "Read and write native extended configuration; persistence is explicit.",
  "Real-time": "Saved 0x75 configuration, working modes and heartbeat.",
  "Buffer": "Manage the reader's EPC / TID inventory buffer.",
  "I/O & diagnostics": "GPIO, indicators, temperature and antenna return loss.",
  "All APIs": "Every public reader operation, with typed argument conversion.",
};
const hex = value => value == null ? "—" : "0x" + Number(value).toString(16).toUpperCase().padStart(2, "0");
const clock = value => value ? new Date(value * 1000).toLocaleTimeString("en-GB", {hour12: false}) : "—";
const stringify = value => JSON.stringify(value, null, 2);
function fail(error) { $("alert").textContent = error.message || String(error); $("alert").classList.remove("hidden"); $("alert").focus(); }
function clearError() { $("alert").classList.add("hidden"); }
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: {"X-Demo-Token": token, ...(options.headers || {})} });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error('HTTP ' + response.status + ' · ' + (body.message || body.error || response.statusText));
    error.status = response.status;
    throw error;
  }
  return response;
}
async function action(operation, args = {}, intent = null) {
  clearError();
  const response = await api("/api/operation", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({operation, arguments: args, intent})});
  const accepted = await response.json();
  $("resultBadge").className = "badge running"; $("resultBadge").textContent = "ACCEPTED";
  $("resultMeta").textContent = "Job " + accepted.job_id + " · " + operation + " · waiting for SDK result";
  return accepted;
}
function labelChoice(name, value) {
  const maps = {bank: ["0 · Reserved", "1 · EPC", "2 · TID", "3 · User"],
    lock_target: ["0 · Kill password", "1 · Access password", "2 · EPC", "3 · TID", "4 · User"],
    protection: ["0 · Unlock", "1 · Permanent unlock", "2 · Password lock", "3 · Permanent lock"]};
  return maps[name]?.[value] || String(value);
}
function control(type, value, choices, name = "") {
  let node;
  if (type === "bool") { node = make("input", {type: "checkbox"}); node.checked = !!value; }
  else if (type === "nullable_bool") {
    node = make("select", {}, make("option", {value: ""}, "Auto"), make("option", {value: "true"}, "Extended"), make("option", {value: "false"}, "Normal"));
    node.value = value == null ? "" : String(value);
  } else if (choices) {
    node = make("select");
    for (const v of choices) node.append(make("option", {value: v}, labelChoice(name, v)));
    node.value = String(value);
  } else if (type === "json") { node = make("textarea", {rows: typeof value === "object" && value !== null ? "4" : "2", spellcheck: "false"}); node.value = stringify(value); }
  else {
    node = make("input", {type: type === "number" ? "text" : "text", spellcheck: "false"});
    node.value = value == null ? "" : String(value);
    if (type === "number") node.inputMode = "decimal";
    if (type === "hex") node.placeholder = "Hex bytes";
  }
  const read = () => {
    if (type === "bool") return node.checked;
    if (type === "nullable_bool") return node.value === "" ? null : node.value === "true";
    if (type === "json") return JSON.parse(node.value || "null");
    if (type === "number" || choices && typeof choices[0] === "number") {
      if (node.value.trim() === "") return null;
      const number = Number(node.value);
      if (!Number.isFinite(number)) throw new Error(name + " must be a finite number");
      return number;
    }
    if (name === "verification_password" && !node.value.trim()) return null;
    return node.value.trim();
  };
  return {node, read};
}
function targetControl(value, name) {
  const box = make("div", {class: "target-controls"});
  const select = make("select", { "aria-label": name + " selection type" },
    make("option", {value: "none"}, "No target"), make("option", {value: "epc"}, "Full EPC"),
    make("option", {value: "tid"}, "TID mask"), make("option", {value: "mask"}, "Custom mask JSON"));
  const input = make("textarea", {rows: "2", spellcheck: "false", "aria-label": name + " identifier"});
  const assign = value => {
    if (value?.epc) { select.value = "epc"; input.value = value.epc; }
    else if (value?.mask?.bank === 2 && value.mask.bit_address === 0) { select.value = "tid"; input.value = value.mask.data; }
    else if (value?.mask) { select.value = "mask"; input.value = stringify(value.mask); }
    else { select.value = "none"; input.value = ""; }
    input.disabled = select.value === "none";
    input.placeholder = select.value === "mask" ? '{"bank":2,"bit_address":0,"bit_length":16,"data":"E280"}' : "EPC / TID hex";
  };
  select.onchange = () => { input.disabled = select.value === "none"; syncArguments(); };
  assign(value);
  box.append(select, input);
  return {node: box, assign, read: () => {
    if (select.value === "none") return null;
    if (select.value === "mask") return {mask: JSON.parse(input.value)};
    const data = input.value.replace(/\s/g, "");
    if (!data || !/^[0-9a-fA-F]+$/.test(data) || data.length % 2) throw new Error(name + " requires whole hex bytes");
    return select.value === "epc" ? {epc: data} : {mask: {bank: 2, bit_address: 0, bit_length: data.length * 4, data}};
  }};
}
function inventoryControl(value) {
  const outer = make("div", {class: "model-fields"});
  const defs = [
    ["data", "Data", ["epc", "tid", "fastid", "mix"]], ["q", "Q", null], ["session", "Session", null],
    ["target", "Target", [0, 1]], ["antenna", "Antenna", null], ["scan_time_100ms", "Scan · 100 ms", null],
    ["phase", "Phase", null], ["statistics", "Statistics", null], ["special_strategy", "Special strategy", null]
  ];
  const advanced = make("details", {class: "full"}, make("summary", {}, "TID / Mix / mask parameters"));
  const advancedGrid = make("div", {class: "model-fields"});
  const extra = [
    ["tid_word_address", "TID start · word"], ["tid_word_count", "TID length · word"],
    ["memory_bank", "Mix bank", [0, 1, 2, 3]], ["word_address", "Mix start · word"],
    ["word_count", "Mix length · word"], ["access_password", "Access password"],
    ["mask", "Inventory mask JSON"]
  ];
  const parts = {};
  for (const [key, label, choices] of [...defs, ...extra]) {
    const type = typeof value[key] === "boolean" ? "bool" : key === "mask" ? "json" : key === "access_password" ? "hex" : key === "data" ? "text" : "number";
    const c = control(type, value[key], choices, key);
    c.node.setAttribute("aria-label", "Inventory " + label);
    const wrap = make("label", {class: key === "mask" ? "full" : type === "bool" ? "check" : ""}, label, c.node);
    (defs.some(d => d[0] === key) ? outer : advancedGrid).append(wrap);
    parts[key] = c.read;
  }
  advanced.append(advancedGrid); outer.append(advanced);
  return {node: outer, read: () => Object.fromEntries(Object.entries(parts).map(([k, fn]) => [k, fn()]))};
}
function getArguments() { return advancedOverride === null ? Object.fromEntries(Object.entries(readers).map(([k, v]) => [k, v.read()])) : advancedOverride; }
function syncArguments() {
  if (advancedOverride !== null) return;
  try { $("jsonArguments").value = stringify(getArguments()); } catch (_) { /* editable intermediate input */ }
}
function renderOperation() {
  selected = catalog.find(c => c.name === $("operation").value);
  readers = {}; advancedOverride = null;
  $("fields").replaceChildren();
  $("allowWrite").checked = false; $("singleTag").checked = false; $("confirmation").value = "";
  $("operationHelp").textContent = selected.description;
  for (const field of selected.fields) {
    const wrap = make("div", {class: "field" + (["json", "target", "inventory"].includes(field.type) ? " full" : "")});
    const c = field.type === "target" ? targetControl(selectedTarget && field.name === "target" ? selectedTarget : field.default, field.name) :
      field.type === "inventory" ? inventoryControl(field.default) :
      control(field.type, field.default, field.choices, field.name);
    if (field.type === "bool") wrap.append(make("label", {class: "check"}, c.node, field.label));
    else {
      const label = make("label", {}, make("span", {class: "field-name"}, field.label + (field.required ? " *" : "")));
      c.node.setAttribute("aria-label", field.label);
      label.append(c.node); wrap.append(label);
    }
    if (field.help) wrap.append(make("small", {}, field.help));
    $("fields").append(wrap); readers[field.name] = c;
  }
  $("writeGuard").classList.toggle("hidden", !selected.tag_write);
  $("singleTagLabel").classList.toggle("hidden", selected.name !== "write_epc_single");
  $("confirmLabel").classList.toggle("hidden", !selected.confirmation);
  $("confirmation").placeholder = selected.confirmation || "";
  $("commandEffect").textContent = selected.tag_write ? "Changes tag memory / state" : selected.mutation ? "Changes reader configuration / state" : selected.group === "Inventory" ? "RF operation" : "Native SDK result";
  $("commandForm").oninput = syncArguments;
  syncArguments(); updateButtons();
}
function chooseGroup(name) {
  group = name;
  $("coveragePanel").classList.toggle("hidden", name !== "Support & evidence");
  $("workspace").classList.toggle("hidden", name === "Support & evidence");
  $("groupTitle").textContent = name;
  $("groupSubtitle").textContent = titles[name] || "Implementation coverage and known boundaries.";
  document.querySelectorAll(".nav-button").forEach(b => {
    const active = b.dataset.group === name;
    b.classList.toggle("active", active);
    if (active) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  if (name === "Support & evidence") return;
  const commands = catalog.filter(c => name === "All APIs" || c.group === name);
  $("operation").replaceChildren(...commands.map(c => make("option", {value: c.name}, c.name)));
  $("commandCount").textContent = commands.length + " operations";
  renderOperation();
}
function updateButtons() {
  const connected = !!snapshot?.connected, busy = !!snapshot?.busy, bad = !!snapshot?.fault || !!snapshot?.recovery_required;
  $("connectBtn").disabled = connected || busy; $("disconnectBtn").disabled = !connected || !!snapshot.control_busy;
  for (const id of ["port", "baud", "ports", "address", "timeout", "simulate", "refreshPorts", "model", "firmware", "cfg25", "cfg29", "bufferWidth"]) $(id).disabled = connected || busy;
  $("runBtn").disabled = !connected || (busy && selected?.name !== "stop_inventory") || bad;
  $("stopBtn").disabled = !connected || bad || !!snapshot.control_busy || !(["starting", "inventorying", "stopping"].includes(snapshot.state) || [1, 2].includes(snapshot.working_mode));
}
function renderSnapshot(s) {
  if (!snapshot?.connected && s.connected) {
    selectedTarget = null;
    selectedTagKey = null;
    if (readers.target?.assign) { readers.target.assign(null); advancedOverride = null; syncArguments(); }
    $("selectedTag").textContent = "No target selected. Tag writes require an explicit target.";
  }
  snapshot = s; source = !!s.connection?.simulate;
  if (s.connected) {
    $("simulate").checked = source;
    $("port").value = s.connection.port; $("ports").value = s.connection.ports;
    $("baud").value = s.baud || s.connection.baud; $("address").value = s.address;
  }
  $("sourceBadge").className = "badge " + (s.connected ? source ? "simulated" : "success" : "neutral");
  $("sourceBadge").textContent = s.connected ? source ? "SIMULATED READER" : "SERIAL · " + s.connection.port : "DISCONNECTED";
  $("connectionDot").className = "dot" + (s.connected ? source ? " sim" : " online" : "");
  $("simBanner").classList.toggle("hidden", !s.connected || !source);
  $("simFaults").classList.toggle("hidden", !s.connected || !source);
  $("stateValue").textContent = s.state.replaceAll("_", " ");
  $("modeValue").textContent = "Saved mode: " + (s.working_mode === null ? "unknown" : ["Answer", "Real-time", "Trigger"][s.working_mode]) + (s.pending_command !== null ? " · pending " + hex(s.pending_command) : "");
  $("sessionValue").textContent = "Active session: " + ({scenario: "Scenario · 0x50 / 0xEE", answer: "Answer · repeated rounds", real_time: "Real-time · 0x76 / 0xEE"}[s.session] || "none");
  const loss = (s.diagnostics.discarded_bytes || 0) + s.tag_overflow + s.observer_errors + (s.stream_health?.dropped || 0);
  $("healthValue").textContent = s.fault ? "Unknown" : loss || s.stream_health?.error ? "Attention" : s.connected ? "Healthy" : "—";
  $("healthDetail").textContent = s.fault || s.stream_health?.error || (s.connected ? (s.diagnostics.frames || 0) + " frames · " + (s.diagnostics.discarded_bytes || 0) + " discarded bytes · " + (s.stream_health?.dropped || 0) + " dropped reports" : "No connection");
  $("healthDetail").title = stringify(s.diagnostics);
  $("logPath").textContent = s.log_path || "Request → TX → RX → decoded frame → result";
  const key = stringify(s.last_result);
  if (s.last_result && key !== lastResultKey) {
    lastResultKey = key;
    lastResultId = s.last_result.job_id || '';
    const lastJob = [...s.jobs].reverse().find(j => j.finished);
    const state = s.last_result.result?.outcome || s.last_result.outcome || lastJob?.state || "success";
    $("resultBadge").textContent = state.toUpperCase(); $("resultBadge").className = "badge " + state;
    const result = s.last_result.result;
    $("resultMeta").textContent = s.last_result.operation + " · " +
      (result?.command != null ? "cmd " + hex(result.command) + " · " : "") +
      (result?.status != null ? "status " + hex(result.status) + " · " : "") +
      (result?.confirmation || result?.termination_reason || "completed");
    $("resultJson").textContent = stringify(s.last_result);
  }
  if (s.tag_overflow) { $("logLoss").textContent = "Host tag capacity reached; " + s.tag_overflow + " new entries not retained. See trace log."; $("logLoss").classList.remove("hidden"); }
  updateButtons();
}
const tagKey = r => [r.epc, r.tid, r.antenna_mask].join('|');
function applyTagRows(rows, summary, replace = false, generation) {
  const reset = generation != null && tagGeneration != null && generation !== tagGeneration;
  if (generation != null) tagGeneration = generation;
  const previousTarget = liveTags.get(selectedTagKey);
  if (replace) liveTags.clear();
  for (const row of rows) liveTags.set(tagKey(row), row);
  if (replace) for (const [key, node] of tagNodes) {
    if (!liveTags.has(key)) { node.remove(); tagNodes.delete(key); }
  }
  const currentTarget = liveTags.get(selectedTagKey);
  if (reset || selectedTagKey && (!currentTarget || previousTarget?.first_seen !== currentTarget.first_seen)) {
    selectedTagKey = null; selectedTarget = null;
    $("selectedTag").textContent = "No target selected. Tag writes require an explicit target.";
    if (readers.target?.assign) { readers.target.assign(null); advancedOverride = null; syncArguments(); }
  }
  liveSummary = summary;
  if (!paintPending) {
    paintPending = true;
    requestAnimationFrame(() => {
      paintPending = false;
      $("reportCount").textContent = liveSummary.received_count.toLocaleString();
      $("uniqueCount").textContent = liveSummary.unique_ids.toLocaleString();
      renderTags();
    });
  }
}
function receiveLive(packet) {
  liveConnected = true;
  liveEpoch++;
  applyTagRows(packet.rows, packet, packet.reset, packet.cursor[0]);
  $("liveStatus").textContent = "Live tag stream · up to 30 updates/s";
  $("liveStatus").className = 'table-note';
  $("pollStatus").textContent = "Live · " + new Date().toLocaleTimeString(); $("pollStatus").className = "";
}
function snapshotTagFallback(s, requestEpoch) {
  // A delayed snapshot must never replace newer live data, even if that stream
  // has disconnected again while this HTTP request was in flight.
  if (liveConnected || liveEpoch !== requestEpoch || !Array.isArray(s.tags)) return;
  applyTagRows(s.tags, s, true, s.tag_generation);
  $("liveStatus").textContent = "Snapshot tag view · refresh every 750 ms · " + liveFailure +
    (liveSupported ? ' · reconnecting live stream' : ' · restart Python server, then reload this page for live updates and current RSSI/phase conversions');
  $("liveStatus").className = 'table-note';
  $("pollStatus").textContent = "Snapshot · " + new Date().toLocaleTimeString(); $("pollStatus").className = "";
}
function phaseText(row, edge) {
  const unit = $("phaseUnit").value;
  const value = row['phase_' + edge + '_' + unit];
  return value == null ? "—" : unit === 'raw' ? String(value) : value.toFixed(unit === 'degrees' ? 3 : 6);
}
function renderTags() {
  const text = $("tagSearch").value.toUpperCase();
  const unit = {degrees:'°', radians:'rad', raw:'uint16'}[$("phaseUnit").value];
  $("phaseBeginHeader").textContent = 'PHASE BEGIN · ' + unit;
  $("phaseEndHeader").textContent = 'PHASE END · ' + unit;
  $("tagCounter").textContent = liveSummary?.unique_ids > 1000 ? "1,000 shown / " + liveSummary.unique_ids + " retained" : liveSummary?.unique_ids || 0;
  if (liveTags.size) $("tagRows").querySelector('.empty')?.closest('tr').remove();
  let visible = 0;
  for (const [key, r] of liveTags) {
    let tr = tagNodes.get(key);
    if (!tr) {
      const id = make("td", {class: "id-cell"}, r.epc || "TID " + r.tid);
      if (r.epc && r.tid) id.append(make("small", {}, "TID " + r.tid));
      tr = make("tr", {tabindex: "0", 'data-tag-key': key, title: "Select this tag as the memory-operation target"}, id, ...Array.from({length:9}, () => make('td')));
      const select = () => {
        const current = liveTags.get(key);
        selectedTagKey = key;
        selectedTarget = current.tid ? {mask: {bank: 2, bit_address: 0, bit_length: current.tid.length * 4, data: current.tid}} : {epc: current.epc};
        $("selectedTag").textContent = "Selected target: " + (current.tid ? "TID " + current.tid : "EPC " + current.epc);
        if (readers.target?.assign) { readers.target.assign(selectedTarget); advancedOverride = null; syncArguments(); }
        renderTags();
      };
      tr.onclick = select; tr.onkeydown = e => { if (e.key === "Enter" || e.key === ' ') { e.preventDefault(); select(); } };
      tagNodes.set(key, tr); $("tagRows").append(tr);
    }
    tr.hidden = !((r.epc || '').includes(text) || (r.tid || '').includes(text));
    if (tr.hidden) continue;
    visible++;
    tr.classList.toggle('selected', selectedTagKey === key); tr.setAttribute('aria-selected', String(selectedTagKey === key));
    const mappedRssi = r.rssi_dbm == null ? "—" : r.rssi_dbm.toFixed(0) + (r.rssi_in_calibration_range === false ? " *" : "");
    const values = [r.antenna ?? "—", r.count, r.rssi_raw ?? "—", mappedRssi, phaseText(r, 'begin'), phaseText(r, 'end'), r.frequency_khz ?? "—", r.memory_data || "—", clock(r.last_seen)];
    values.forEach((value, i) => { const cell = tr.cells[i + 1]; if (cell.textContent !== String(value)) cell.textContent = value; });
    tr.cells[4].title = r.rssi_dbm == null ? 'RSSI unavailable' : r.rssi_source + (r.rssi_in_calibration_range === false ? ' · extrapolated outside raw 60..110' : ' · raw 60..110 maps to -75..-25 dBm');
    tr.cells[5].title = tr.cells[6].title = r.phase_raw ? 'Raw hex: ' + r.phase_raw + ' · ' + r.phase_conversion : 'Phase not present in this report';
  }
  if (!visible && !$("tagRows").querySelector('.empty')) $("tagRows").append(make("tr", {}, make("td", {colspan: 10, class: "empty"}, "No matching tag reports. Inventory completion alone does not prove a tag was read.")));
}
function renderEvents() {
  if (paused) return;
  const filter = $("logFilter").value, search = $("logSearch").value.toLowerCase();
  const selected = events.filter(e => {
    const allowed = filter === "all" || filter === "wire" && ["tx", "rx", "frame", "request"].includes(e.kind) ||
      filter === "results" && e.kind.startsWith("operation") ||
      filter === "errors" && /error|fault|timeout|state|unexpected|loss|cancel/.test(e.kind);
    return allowed && (!search || JSON.stringify(e).toLowerCase().includes(search));
  }).slice(-200);
  $("eventCounter").textContent = cursor.toLocaleString();
  const view = stringify([filter, search, selected.map(e => e.id)]);
  if (view === lastEventsView) return;
  lastEventsView = view;
  const focused = document.activeElement?.dataset.eventId;
  const scroll = document.querySelector('.log-scroll');
  const atBottom = scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 40;
  const elements = selected.map(e => {
    const trace = e.trace || {};
    const detail = trace.raw || trace.detail || e.operation || e.error?.message || e.detail || (e.report ? (e.report.epc || e.report.tid || "heartbeat") + " · RSSI raw " + (e.report.rssi_raw ?? "—") + (e.report.rssi_dbm == null ? "" : " · " + e.report.rssi_dbm + " dBm (user mapping)") : "");
    const row = make("tr", {}, make("td", {}, clock(e.wall_time)),
      make("td", {}, make("span", {class: "event-label event-" + e.kind}, e.kind)),
      make("td", {}, trace.exchange_id == null ? e.job_id ? "job " + e.job_id : "—" : "#" + trace.exchange_id),
      make("td", {}, hex(trace.command)), make("td", {}, trace.status == null ? e.outcome || "—" : hex(trace.status)),
      make("td", {}, make('button', {class:'log-detail-button', title:detail, 'aria-label':'Inspect ' + e.kind + ' event ' + e.id, 'data-event-id':e.id}, detail || 'View detail')));
    row.onclick = () => { $("eventDetail").textContent = stringify(e); document.querySelector(".log-inspector").open = true; };
    return row;
  });
  $("logRows").replaceChildren(...elements);
  if (focused) elements.flatMap(e => [...e.querySelectorAll('button')]).find(e => e.dataset.eventId === focused)?.focus({preventScroll:true});
  if (atBottom && !focused) scroll.scrollTop = scroll.scrollHeight;
}
async function download(path, filename) {
  const response = await api(path);
  const url = URL.createObjectURL(await response.blob());
  const link = make("a", {href: url, download: filename}); link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function poll() {
  if (polling) return; polling = true;
  const requestEpoch = liveEpoch;
  try {
    const s = await (await api("/api/snapshot?tags=" + (liveConnected ? '0' : '1') + "&result_after=" + encodeURIComponent(lastResultId), {signal: AbortSignal.timeout(8000)})).json();
    renderSnapshot(s);
    snapshotTagFallback(s, requestEpoch);
  } catch (error) {
    $("pollStatus").textContent = "State unavailable · " + error.message; $("pollStatus").className = "offline";
    if (!liveConnected) {
      $("liveStatus").textContent = "Tag updates unavailable · " + error.message + " · showing last received values";
      $("liveStatus").className = 'table-note offline';
    }
    $("runBtn").disabled = true; $("stopBtn").disabled = true;
  } finally { polling = false; setTimeout(poll, 750); }
}
async function pollLogs() {
  let delay = 750;
  try {
    if (paused) return;
    const log = await (await api("/api/events?after=" + cursor, {signal: AbortSignal.timeout(8000)})).json();
    events.push(...log.events); events = events.slice(-1200); cursor = log.next;
    if (log.missed || log.disk_dropped || log.disk_error) {
      $("logLoss").textContent = "Log retention: missed " + log.missed + "; disk queue drops " + log.disk_dropped + ". " + (log.disk_error || "");
      $("logLoss").classList.remove("hidden");
    }
    renderEvents();
    if (log.latest > cursor) delay = 250;
  } catch (error) {
    $("logLoss").textContent = "Log view unavailable · " + error.message; $("logLoss").classList.remove("hidden");
  } finally { setTimeout(pollLogs, delay); }
}
async function streamLive() {
  if (!liveSupported) return;
  const abort = new AbortController();
  let reader, timer;
  const heartbeat = () => { clearTimeout(timer); timer = setTimeout(() => abort.abort(), 8000); };
  try {
    heartbeat();
    const response = await api('/api/live', {signal: abort.signal});
    reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) throw new Error('Live connection ended');
      heartbeat(); buffer += decoder.decode(chunk.value, {stream:true});
      let end;
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
        if (line) receiveLive(JSON.parse(line));
      }
      if (buffer.length > 8 * 1024 * 1024) throw new Error('Invalid live packet size');
    }
  } catch (error) {
    liveConnected = false; liveEpoch++;
    liveFailure = '/api/live: ' + error.message;
    if ([404, 405, 501].includes(error.status)) liveSupported = false;
    $("liveStatus").textContent = liveFailure + " · switching to snapshot tag view";
    $("liveStatus").className = 'table-note offline';
  } finally {
    clearTimeout(timer); abort.abort();
    if (reader) { try { await reader.cancel(); } catch (_) {} reader.releaseLock(); }
    if (liveSupported) setTimeout(streamLive, 1000);
  }
}
const guarded = fn => async event => { try { await fn(event); } catch (error) { fail(error); } };
async function boot() {
  const config = await (await fetch("/api/bootstrap")).json();
  token = config.token; catalog = config.catalogue;
  liveSupported = config.features?.live_tags !== false;
  if (!liveSupported) liveFailure = 'Server does not provide live tags';
  if (config.api_revision !== 2) {
    $("serverNotice").textContent = "The Python server and this page use different API versions. Stop inventory, Disconnect, restart the Python server, then reload this page. Tag data uses the available server fields until restart.";
    $("serverNotice").classList.remove('hidden');
  }
  $("version").textContent = config.version;
  document.querySelectorAll('[data-icon]').forEach(node => node.prepend(icon(node.dataset.icon)));
  for (const id of ["port", "baud", "ports", "address", "timeout"]) $(id).value = config.defaults[id];
  for (const name of [...new Set(catalog.map(c => c.group)), "All APIs"]) {
    const count = name === "All APIs" ? catalog.length : catalog.filter(c => c.group === name).length;
    const button = make("button", {class: "nav-button", "data-group": name}, icon(groupIcons[name]), make('span', {class:'nav-label'}, name), make("span", {class:'nav-count'}, count));
    button.onclick = () => chooseGroup(name); $("nav").append(button);
  }
  $("coverageNav").dataset.group = "Support & evidence";
  $("coverageNav").onclick = () => chooseGroup("Support & evidence");
  $("coverageContent").replaceChildren(...config.limitations.map(r =>
    make("div", {class: "coverage-row"}, make("b", {}, r.feature), make("span", {}, make("span", {class: "badge partial"}, r.status)), make("p", {}, r.reason))));
  $("operation").onchange = renderOperation;
  $("connectBtn").onclick = guarded(async () => {
    const args = {port: $("port").value.trim(), baud: Number($("baud").value), ports: Number($("ports").value),
      address: Number($("address").value), timeout: Number($("timeout").value), simulate: $("simulate").checked,
      clean_boundary: $("cleanBoundary").checked, model: $("model").value || null, firmware: $("firmware").value || null,
      cfg25_length: $("cfg25").value ? Number($("cfg25").value) : null,
      cfg29_length: $("cfg29").value ? Number($("cfg29").value) : null,
      buffer_antenna_bytes: $("bufferWidth").value ? Number($("bufferWidth").value) : null};
    await action("connect", args); $("cleanBoundary").checked = false;
  });
  $("disconnectBtn").onclick = guarded(() => action("disconnect"));
  $("refreshPorts").onclick = guarded(async () => {
    const ports = await (await api("/api/ports")).json();
    $("portList").replaceChildren(...ports.map(p => make("option", {value: p.port}, p.description)));
    if (ports.length && !ports.some(p => p.port === $("port").value)) $("port").value = ports[0].port;
  });
  $("commandForm").onsubmit = guarded(async event => {
    event.preventDefault();
    const args = getArguments();
    await action(selected.name, args, {allow_tag_write: $("allowWrite").checked,
      confirmation: $("confirmation").value.trim(), single_tag: $("singleTag").checked});
    $("allowWrite").checked = false; $("singleTag").checked = false; $("confirmation").value = "";
  });
  $("applyJson").onclick = guarded(() => {
    const args = JSON.parse($("jsonArguments").value);
    if (!args || typeof args !== "object" || Array.isArray(args)) throw new Error("Arguments must be a JSON object");
    advancedOverride = args; $("commandEffect").textContent = "Using advanced JSON arguments";
  });
  $("stopBtn").onclick = guarded(() => action("stop_inventory"));
  $("clearTags").onclick = guarded(() => action("clear_tags"));
  $("exportTags").onclick = guarded(() => download("/api/tags.csv", "zk-tags.csv"));
  $("exportLog").onclick = guarded(() => download("/api/logs", "zk-events.jsonl"));
  $("pauseLog").onclick = () => { paused = !paused; $("pauseLog").textContent = paused ? "Resume view" : "Pause view"; renderEvents(); };
  $("injectBtn").onclick = guarded(() => action("inject", {error: $("faultType").value}));
  $("tagSearch").oninput = renderTags; $("phaseUnit").onchange = renderTags;
  $("logSearch").oninput = renderEvents; $("logFilter").onchange = renderEvents;
  chooseGroup("Reader"); poll(); pollLogs(); streamLive();
}
boot().catch(fail);
