/** NATION UI service using approved GReaderTool mappings and the native ZK bridge. */
export function toLegacyTag(tag) {
  return {
    epc: tag.epc,
    tid: tag.tid,
    antenna_id: tag.antenna,
    rssi: tag.rssi_dbm,
    frequency: tag.frequency_khz == null ? null : tag.frequency_khz / 1000,
    native: tag, // Keep both phases, raw measurements and conversion metadata.
  };
}

export function createNationInventoryService(reader, onTag, { policy = null } = {}) {
  const listener = ({ detail }) => onTag(toLegacyTag(detail));
  reader.addEventListener("tag", listener);
  let runConfig = { q: 4, session: 0, target: 0, phase: false };
  let policyPromise;
  const requireSuccess = result => {
    if (result.outcome !== "success") {
      throw Object.assign(new Error("Reader operation failed"), { result });
    }
    return result.data;
  };
  const getPolicy = async () => {
    policyPromise ??= policy ? Promise.resolve(policy) : fetch(
      new URL("../mapping/nation_to_zk/rf_choices.json", import.meta.url),
    ).then(response => {
      if (!response.ok) throw new Error("Could not load NATION mapping policy");
      return response.json();
    });
    const choices = await policyPromise;
    if (choices.status !== "approved-application-policy" || choices.selected_baseband_source !== "greader-0.39") {
      throw new Error("Expected approved GReaderTool 0.39 policy");
    }
    return choices;
  };
  const maskFor = antennaIds => {
    if (!Array.isArray(antennaIds) || !antennaIds.length ||
        new Set(antennaIds).size !== antennaIds.length ||
        antennaIds.some(port => !Number.isInteger(port) || port < 1 || port > 16)) {
      throw new Error("Select unique antenna IDs within the reader's port count");
    }
    return antennaIds.reduce((mask, port) => mask | (1 << (port - 1)), 0);
  };
  const checkedWrite = async (operation, args, getter, expected, fields = null) => {
    const written = await reader.call(operation, args);
    requireSuccess(written);
    const verificationError = (actual, cause) => Object.assign(
      new Error(`Write succeeded; ${getter} verification failed`, { cause }), {
        result: { ...written, data: null,
          outcome: actual.outcome === "unknown" ? "unknown" : "partial",
          diagnostics: [...(written.diagnostics || []),
            `Write succeeded; ${getter} verification failed`, ...(actual.diagnostics || [])],
          steps: [written, actual] },
      },
    );
    let actual;
    try {
      actual = await reader.call(getter);
    } catch (cause) {
      // Keep the acknowledged write even when the bridge rejects the Get promise.
      throw verificationError(cause?.result ?? {
        outcome: "unknown", data: null, confirmation: "none",
        diagnostics: [cause?.message || String(cause)],
      }, cause);
    }
    if (actual.outcome !== "success") throw verificationError(actual);
    const matches = fields ? fields.every(key => actual.data?.[key] === expected[key]) : actual.data === expected;
    if (!matches) throw Object.assign(new Error("Configuration read-back mismatch"), {
      result: { ...actual, outcome: "partial", confirmation: "acknowledged",
        diagnostics: [...(actual.diagnostics || []), "Configuration read-back mismatch"], steps: [written, actual] },
    });
    return { ...actual, confirmation: "read_back_verified", steps: [written, actual] };
  };
  return {
    async setAntennas(antennaIds) {
      const mask = maskFor(antennaIds);
      return checkedWrite("set_antennas", { mask, persist: true }, "get_antennas", mask);
    },
    getAntennas() { return reader.call("get_antennas"); },
    async configureBaseband({ speed, q, session, target, persist = false }) {
      if (!Number.isInteger(q) || q < 0 || q > 15 || !Number.isInteger(session) || session < 0 || session > 3 || ![0, 1].includes(target)) {
        throw new Error("Use Q 0..15, Session S0..S3 and Target A=0 or B=1");
      }
      const row = (await getPolicy()).greader_039_baseband_speeds.find(row => row.nation_speed === speed);
      if (!row) throw new Error("Unsupported GReaderTool 0.39 speed");
      const result = row.zk_profile_id == null ? await reader.call("get_profile") : await checkedWrite(
        "set_profile", { profile_id: row.zk_profile_id, persist }, "get_profile", row.zk_profile_id,
      );
      requireSuccess(result);
      runConfig = { ...runConfig, q, session, target };
      return { ...result, diagnostics: [...(result.diagnostics || []), row.difference] };
    },
    async queryBaseband() {
      const result = await reader.call("get_profile");
      const zk_profile_id = requireSuccess(result);
      return { ...result, data: { zk_profile_id, ...runConfig, run_settings_source: "application", baseband_source: "greader-0.39" } };
    },
    async setRfBand(bandCode, persist = false) {
      const row = (await getPolicy()).bands.find(row => row.nation_band === bandCode);
      if (!row || row.kind === "unsupported") throw new Error(row?.difference || "Unsupported NATION band");
      return row.kind === "native" ? checkedWrite(
        "set_region", { region: row.region, persist }, "get_region", row.region, ["band", "min_channel", "max_channel"],
      ) : checkedWrite(
        "set_custom_region", { ...row.centers, persist }, "get_custom_region", row.centers,
        ["start_frequency_khz", "channel_count", "spacing_khz"],
      );
    },
    queryRfBand() { return reader.call("get_region"); },
    async startInventory(antennaIds, options = {}) {
      const antenna_mask = maskFor(antennaIds);
      const { includeTid = false, ...overrides } = options;
      if (typeof includeTid !== "boolean") throw new Error("includeTid must be boolean");
      const config = { ...runConfig, ...overrides, antenna: antennaIds[0], data: includeTid ? "fastid" : "epc" };
      if (includeTid) return reader.startInventory({
        mode: "answer", antenna_sequence: antennaIds, config,
      });
      return reader.startInventory({
        mode: "scenario",
        antenna_mask,
        config,
      });
    },
    async stopInventory() {
      const result = await reader.stopInventory(); // The native bridge drains its consumer.
      if (!result.complete || result.outcome !== "success") {
        throw Object.assign(new Error("Inventory stop is incomplete; inspect the native result"), { result });
      }
      return result;
    },
    dispose() {
      // Call only after Stop/disconnect; removing a listener does not stop RF.
      reader.removeEventListener("tag", listener);
    },
  };
}
