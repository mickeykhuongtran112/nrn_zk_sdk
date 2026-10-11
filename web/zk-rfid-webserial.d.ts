export const PYODIDE_INDEX_URL: string;
export type Outcome = "success" | "failure" | "partial" | "unknown";
export interface CommandResult<T = unknown> {
  outcome: Outcome;
  data: T | null;
  command: number | null;
  status: number | null;
  tag_error: number | null;
  raw_data: string;
  confirmation: "none" | "transmitted" | "acknowledged" | "read_back_verified";
  diagnostics: string[];
  steps: CommandResult[];
  evidence: string;
}
export interface TagReport {
  epc: string | null;
  tid: string | null;
  antenna: number | null;
  antenna_mask: number | null;
  rssi_raw: number | null;
  rssi_dbm: number | null;
  rssi_source: string | null;
  rssi_in_calibration_range: boolean | null;
  phase_begin_degrees: number | null;
  phase_end_degrees: number | null;
  phase_begin_radians: number | null;
  phase_end_radians: number | null;
  phase_raw: string | null;
  frequency_khz: number | null;
  read_count: number | null;
  [key: string]: unknown;
}
export interface InventoryOutcome {
  outcome: Outcome;
  reports: TagReport[];
  complete: boolean;
  termination_reason: string;
  received_count: number;
  dropped_count: number;
  [key: string]: unknown;
}
export interface TagMask { bank: 1 | 2 | 3; bit_address: number; bit_length: number; data: string; }
export interface InventoryConfig {
  antenna?: number;
  data?: "epc" | "tid" | "fastid" | "mix";
  q?: number;
  session?: number;
  target?: number;
  scan_time_100ms?: number;
  phase?: boolean;
  statistics?: boolean;
  special_strategy?: boolean;
  mask?: TagMask | null;
  tid_word_address?: number;
  tid_word_count?: number;
  memory_bank?: number;
  word_address?: number;
  word_count?: number;
  access_password?: string;
}
export interface SerialPortLike {
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
  open(options: { baudRate: number; dataBits: 8; stopBits: 1; parity: "none"; flowControl: "none" }): Promise<void>;
  close(): Promise<void>;
}
export interface ReaderOptions {
  baudRate?: number;
  antennaPorts?: 1 | 4 | 8 | 16;
  address?: number;
  timeout?: number;
  capabilities?: Record<string, unknown>;
  pyodide?: object;
  sdkURL?: string;
  bridgeURL?: string;
}
export interface ReaderEvents {
  tag: TagReport;
  trace: { kind: string; [key: string]: unknown };
  state: { state: string };
  error: { type: string; message: string };
  heartbeat: Record<string, unknown>;
}
export class ZKSDKError extends Error {
  constructor(error: { type?: string; message: string; result?: CommandResult | null; transmitted?: boolean | null }, state: string);
  state: string;
  result: CommandResult | null;
  transmitted: boolean | null;
}
export class WebSerialTransport {
  constructor(port: SerialPortLike, options?: { baudRate?: number });
  open(): Promise<void>;
  close(): Promise<void>;
  read(size?: number): Promise<Uint8Array>;
  write(data: Uint8Array): Promise<number>;
}
export class ZKWebSerialReader extends EventTarget {
  constructor(options?: ReaderOptions);
  readonly state: string;
  initialize(): Promise<this>;
  connect(options?: { port?: SerialPortLike; recover?: boolean; filters?: Array<{ usbVendorId: number; usbProductId?: number }> }): Promise<Record<string, unknown>>;
  disconnect(): Promise<{ inventory_outcome: InventoryOutcome | null; fault: string | null } | null>;
  call<T = unknown>(operation: string, args?: Record<string, unknown>): Promise<T>;
  getReaderInfo(): Promise<CommandResult<Record<string, unknown>>>;
  getPower(): Promise<CommandResult<number[]>>;
  setPower(power: number | number[], persist?: boolean): Promise<CommandResult<null>>;
  inventoryOnce(config?: InventoryConfig): Promise<InventoryOutcome>;
  startInventory(options?: { mode?: "answer" | "scenario" | "real_time"; config?: InventoryConfig; queue_size?: number; trigger?: boolean }): Promise<{ started: true; mode: string }>;
  stopInventory(): Promise<InventoryOutcome>;
  writeEpc(options: { targetEpc: string; newEpc: string; accessPassword?: string; verify?: boolean }): Promise<CommandResult<string>>;
  addEventListener<K extends keyof ReaderEvents>(type: K, listener: (event: CustomEvent<ReaderEvents[K]>) => void, options?: boolean | AddEventListenerOptions): void;
  addEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions): void;
}
export function createZKReader(options?: ReaderOptions): ZKWebSerialReader;
