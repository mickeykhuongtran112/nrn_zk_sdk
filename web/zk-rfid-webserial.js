/** Web Serial + Pyodide integration. All RFID protocol handling is in zk_rfid.py. */
export const PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const dirtyPorts = new WeakSet();
const claimedPorts = new WeakSet();
let defaultRuntime;
const bridgeLoads = new WeakMap();

function yieldBrowserTask() {
  // A posted task avoids the nested/background timer delay of setTimeout(0).
  return new Promise(resolve => {
    const channel = new MessageChannel();
    channel.port1.onmessage = () => {
      channel.port1.close(); channel.port2.close(); resolve();
    };
    channel.port2.postMessage(null);
  });
}

export class ZKSDKError extends Error {
  constructor(error, state) {
    super(error.message);
    this.name = error.type || "ZKSDKError";
    this.state = state;
    this.result = error.result ?? null;
    this.transmitted = error.transmitted ?? null;
  }
}

/** Owns one reader and one writer lock. Does not parse frames or buffer tags. */
export class WebSerialTransport {
  constructor(port, { baudRate = 115200 } = {}) {
    this.port = port;
    this.baudRate = baudRate;
    this.reader = null;
    this.writer = null;
    this.opened = false;
    this.closing = null;
    this.pendingRead = null;
    this.remainder = new Uint8Array();
    this.claimed = false;
    this.lastYield = 0;
  }

  async open() {
    if (this.opened) return;
    if (claimedPorts.has(this.port)) throw new Error("Serial port is already owned by a ZK reader");
    claimedPorts.add(this.port);
    this.claimed = true;
    try {
      await this.port.open({ baudRate: this.baudRate, dataBits: 8, stopBits: 1, parity: "none", flowControl: "none" });
      this.opened = true;
      this.reader = this.port.readable.getReader();
      this.writer = this.port.writable.getWriter();
    } catch (error) {
      await this.close().catch(() => {});
      throw error;
    }
  }

  async read(size = 4096) {
    if (!Number.isInteger(size) || size < 1) throw new Error("Read size must be a positive integer");
    if (this.pendingRead) throw new Error("Concurrent serial reads are not allowed");
    this.pendingRead = this._read(size);
    try { return await this.pendingRead; }
    finally { this.pendingRead = null; }
  }

  async _read(size) {
    while (this.opened && !this.closing) {
      // Buffered replies can form an endless microtask chain in Answer mode.
      // Yield a task so Stop/rendering can run, also when empty chunks repeat.
      if (performance.now() - this.lastYield >= 8) {
        await yieldBrowserTask();
        this.lastYield = performance.now();
        if (!this.opened || this.closing) break;
      }
      if (this.remainder.length) {
        const value = this.remainder.slice(0, size);
        this.remainder = this.remainder.slice(size);
        return value;
      }
      const { value, done } = await this.reader.read();
      if (done) return new Uint8Array(); // True EOF, never an empty timeout chunk.
      if (value?.length) this.remainder = Uint8Array.from(value);
    }
    return new Uint8Array();
  }

  async write(value) {
    if (!this.opened || this.closing) throw new Error("Serial port is closed");
    // Copy out of the WASM view before awaiting or passing ownership to the stream.
    const bytes = Uint8Array.from(value);
    await this.writer.write(bytes);
    return bytes.length;
  }

  async close() {
    if (this.closing) return this.closing;
    this.closing = this._close();
    try { return await this.closing; }
    finally { this.closing = null; }
  }

  async _close() {
    const errors = [];
    const reader = this.reader, writer = this.writer;
    this.reader = this.writer = null;
    if (reader) {
      try { await reader.cancel(); } catch (error) { errors.push(error); }
      if (this.pendingRead) await this.pendingRead.catch(() => {});
      reader.releaseLock();
    }
    if (writer) {
      try { await writer.abort(); } catch (error) { errors.push(error); }
      writer.releaseLock();
    }
    if (this.opened) {
      try { await this.port.close(); } catch (error) { errors.push(error); }
    }
    this.opened = false;
    this.remainder = new Uint8Array();
    if (this.claimed) claimedPorts.delete(this.port);
    this.claimed = false;
    if (errors.length) throw new AggregateError(errors, "Could not fully close the serial port");
  }
}

async function fetchSource(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Cannot load ${url}: HTTP ${response.status}`);
  return response.text();
}

async function runtime() {
  if (!defaultRuntime) {
    defaultRuntime = import(`${PYODIDE_INDEX_URL}pyodide.mjs`)
      .then(({ loadPyodide }) => loadPyodide({ indexURL: PYODIDE_INDEX_URL }))
      .catch(error => { defaultRuntime = null; throw error; });
  }
  return defaultRuntime;
}

async function loadBridge(pyodide, sdkURL, bridgeURL) {
  // One canonical SDK version per interpreter. Never silently replace a live SDK.
  const identity = `${sdkURL}\n${bridgeURL}`;
  if (bridgeLoads.has(pyodide)) {
    const loaded = bridgeLoads.get(pyodide);
    if (loaded.identity !== identity) throw new Error("Use a separate Pyodide runtime for a different SDK source");
    return loaded.promise;
  }
  const promise = (async () => {
    const [sdk, bridge] = await Promise.all([fetchSource(sdkURL), fetchSource(bridgeURL)]);
    pyodide.FS.mkdirTree("/zk_web");
    pyodide.FS.writeFile("/zk_web/zk_rfid.py", sdk);
    pyodide.FS.writeFile("/zk_web/zk_browser.py", bridge);
    await pyodide.runPythonAsync('import sys\nif "zk_rfid" in sys.modules or "zk_browser" in sys.modules:\n    raise RuntimeError("SDK already imported outside this bridge; use a fresh Pyodide runtime")\nsys.path.insert(0, "/zk_web")\nimport zk_browser');
  })();
  bridgeLoads.set(pyodide, { identity, promise });
  try { return await promise; }
  catch (error) { bridgeLoads.delete(pyodide); throw error; }
}

export class ZKWebSerialReader extends EventTarget {
  constructor({ baudRate = 115200, antennaPorts = 1, address = 0, timeout = 3,
    capabilities = {}, pyodide = null,
    sdkURL = new URL("../src/zk_rfid.py", import.meta.url).href,
    bridgeURL = new URL("./zk_browser.py", import.meta.url).href } = {}) {
    super();
    this.options = { baudRate, antennaPorts, address, timeout, capabilities, sdkURL, bridgeURL };
    this.pyodide = pyodide;
    this.state = "disconnected";
    this._driver = null;
    this._transport = null;
    this._port = null;
    this._busy = false;
    this._closing = null;
    this._calls = new Set();
    this._faulted = false;
  }

  async initialize() {
    this.pyodide ??= await runtime();
    await loadBridge(this.pyodide, this.options.sdkURL, this.options.bridgeURL);
    return this;
  }

  _emit(kind, data) { this.dispatchEvent(new CustomEvent(kind, { detail: data })); }

  _receive(kind, dataJSON) {
    const data = JSON.parse(dataJSON);
    if (kind === "trace" && data.kind === "fault") this._markFault();
    if (kind === "state") this.state = data.state;
    this._emit(kind, data);
  }

  _markFault() {
    this._faulted = true;
    if (this._port) dirtyPorts.add(this._port);
    this.state = "unknown";
    this._emit("state", { state: this.state });
  }

  _unwrap(text) {
    const envelope = JSON.parse(text);
    this.state = envelope.state;
    if (this.state === "unknown") this._markFault();
    this._emit("state", { state: this.state });
    if (!envelope.ok) throw new ZKSDKError(envelope.error, envelope.state);
    return envelope.data;
  }

  async connect({ port = null, recover = false, filters = [] } = {}) {
    if (this._driver || this._busy || this._closing) throw new Error("Reader is already connected or changing connection");
    this._busy = true;
    try {
      // Keep requestPort inside the click's user activation, before loading WASM.
      if (!port) {
        if (!globalThis.navigator?.serial) throw new Error("Web Serial requires a supported browser on HTTPS or localhost");
        port = await navigator.serial.requestPort({ filters });
      }
      if (dirtyPorts.has(port) && !recover) throw new Error("Reset/resynchronize the module, then connect with recover: true");
      await this.initialize();
      this._port = port;
      this._faulted = false;
      this._transport = new WebSerialTransport(port, this.options);
      const module = this.pyodide.pyimport("zk_browser");
      const factory = module.BrowserReader;
      try {
        this._driver = factory(this._transport, JSON.stringify({
          address: this.options.address, timeout: this.options.timeout,
          capabilities: { ...this.options.capabilities, antenna_ports: this.options.antennaPorts },
        }), (kind, data) => this._receive(kind, data));
        this._methods = Object.fromEntries(["open", "call", "close"].map(name => [name, this._driver[name]]));
      } finally { factory.destroy(); module.destroy(); }
      const result = this._unwrap(await this._methods.open(recover));
      if (recover) dirtyPorts.delete(port);
      return result;
    } catch (error) {
      try { if (this._transport) await this._transport.close(); }
      finally { this._dispose(); this._transport = null; this.state = "disconnected"; }
      throw error;
    } finally { this._busy = false; }
  }

  async call(operation, args = {}) {
    if (!this._driver || this._busy || this._closing) throw new Error("Connect the reader first");
    const pending = this._methods.call(operation, JSON.stringify(args));
    this._calls.add(pending);
    try { return this._unwrap(await pending); }
    finally { this._calls.delete(pending); }
  }

  async disconnect() {
    if (this._closing) return this._closing;
    if (this._busy) throw new Error("Wait for connect to finish before disconnecting");
    if (!this._driver) return null;
    this._closing = this._disconnect();
    try { return await this._closing; }
    finally { this._closing = null; }
  }

  async _disconnect() {
    let result, failure;
    try {
      result = this._unwrap(await this._methods.close());
      if (result.fault || result.inventory_outcome?.outcome === "unknown") this._markFault();
    } catch (error) { this._markFault(); failure = error; }
    // Also release streams if Python close failed partway through cleanup.
    try { await this._transport.close(); }
    catch (error) { this._markFault(); failure ??= error; }
    finally {
      await Promise.allSettled([...this._calls]);
      this._dispose();
      this._transport = null;
      this.state = "disconnected";
      this._emit("state", { state: this.state });
    }
    if (failure) throw failure;
    return result;
  }

  _dispose() {
    for (const method of Object.values(this._methods || {})) method.destroy();
    this._methods = null;
    this._driver?.destroy();
    this._driver = null;
  }

  getReaderInfo() { return this.call("get_reader_info"); }
  getPower() { return this.call("get_power"); }
  setPower(power_dbm, persist = false) { return this.call("set_power", { power_dbm, persist }); }
  getCustomRegion() { return this.call("get_custom_region"); }
  setCustomRegion(region, persist = false) {
    return this.call("set_custom_region", { ...region, persist });
  }
  inventoryOnce(config = {}) { return this.call("inventory_once", { config }); }
  startInventory({ mode = "scenario", config = {}, queue_size = 1024, trigger = false, antenna_mask = null, antenna_sequence = null } = {}) {
    return this.call("start_inventory", { mode, config, queue_size, trigger, antenna_mask, antenna_sequence });
  }
  stopInventory() { return this.call("stop_inventory"); }
  writeEpc({ targetEpc, newEpc, accessPassword = "00000000", verify = true }) {
    return this.call("write_epc", { epc: newEpc, target: { epc: targetEpc },
      access_password: accessPassword, verify, verification_target: { epc: newEpc } });
  }
}

export function createZKReader(options) { return new ZKWebSerialReader(options); }
