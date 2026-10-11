import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import { createNationInventoryService, toLegacyTag } from "../../examples/nation_web_service.js";

const policy = JSON.parse(await readFile(new URL("../../mapping/nation_to_zk/rf_choices.json", import.meta.url), "utf8"));

class Reader extends EventTarget {
  calls = [];
  commands = [];
  registers = { antennas: 1, profile: 125, region: { band: 2, min_channel: 0, max_channel: 49 }, custom_region: null };
  async call(name, args = {}) {
    this.commands.push({ name, args });
    if (this.fail) return this.fail;
    if (name.startsWith("set_")) {
      const key = name.slice(4);
      this.registers[key] = key === "antennas" ? args.mask : key === "profile" ? args.profile_id : key === "region" ? args.region : {
        start_frequency_khz: args.start_frequency_khz, channel_count: args.channel_count, spacing_khz: args.spacing_khz,
      };
      return { outcome: "success", data: null };
    }
    return { outcome: "success", data: this.readOverride ?? this.registers[name.slice(4)] };
  }
  outcome = { complete: true, outcome: "success" };
  async startInventory(args) { this.calls.push(args); return { started: true, mode: args.mode }; }
  async stopInventory() {
    this.dispatchEvent(new CustomEvent("tag", { detail: { epc: "0001", antenna: 1 } }));
    return this.outcome;
  }
}

test("legacy continuous reading sends one Scenario Start with user settings", async () => {
  const reader = new Reader();
  const received = [];
  const service = createNationInventoryService(reader, tag => received.push(tag));
  await service.startInventory([1], { q: 6, session: 2, target: 1, phase: true });
  assert.deepEqual(reader.calls, [{ mode: "scenario", antenna_mask: 1, config: {
    antenna: 1, data: "epc", q: 6, session: 2, target: 1, phase: true,
  } }]);
  await service.stopInventory();
  assert.equal(received[0].epc, "0001"); // Tail event is delivered before Stop resolves.
  service.dispose();
  await reader.stopInventory();
  assert.equal(received.length, 1);
});

test("antenna Set always saves and reads back; Start never saves again", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {}, { policy });
  const result = await service.setAntennas([1, 3, 4]);
  assert.equal(result.confirmation, "read_back_verified");
  assert.deepEqual(reader.commands, [
    { name: "set_antennas", args: { mask: 13, persist: true } },
    { name: "get_antennas", args: {} },
  ]);
  await service.startInventory([1, 3, 4]);
  await service.stopInventory();
  assert.equal(reader.commands.length, 2);
});

test("EPC+TID uses Answer FastID over every selected port", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {}, { policy });
  await service.startInventory([4, 1], { includeTid: true, q: 7, session: 2, target: 1 });
  assert.deepEqual(reader.calls[0], { mode: "answer", antenna_sequence: [4, 1], config: {
    q: 7, session: 2, target: 1, phase: false, antenna: 4, data: "fastid",
  } });
  assert.equal(reader.commands.length, 0);
});

test("all approved GReaderTool speeds use the shared policy and stage run parameters", async () => {
  for (const row of policy.greader_039_baseband_speeds) {
    const reader = new Reader();
    const service = createNationInventoryService(reader, () => {}, { policy });
    const result = await service.configureBaseband({ speed: row.nation_speed, q: 6, session: 1, target: 1 });
    assert.equal(result.data, row.zk_profile_id ?? 125);
    assert.deepEqual(reader.commands.map(c => c.name), row.zk_profile_id == null ? ["get_profile"] : ["set_profile", "get_profile"]);
    await service.startInventory([1]);
    assert.equal(reader.calls[0].config.q, 6);
    assert.equal(reader.calls[0].config.session, 1);
    assert.equal(reader.calls[0].config.target, 1);
    assert.equal((await service.queryBaseband()).data.run_settings_source, "application");
  }
});

test("all full region plans are read back or rejected before device I/O", async () => {
  for (const row of policy.bands) {
    const reader = new Reader();
    const service = createNationInventoryService(reader, () => {}, { policy });
    if (row.kind === "unsupported") {
      await assert.rejects(service.setRfBand(row.nation_band));
      assert.equal(reader.commands.length, 0);
    } else {
      const result = await service.setRfBand(row.nation_band);
      assert.deepEqual(result.data, row.kind === "native" ? row.region : row.centers);
      assert.equal(result.confirmation, "read_back_verified");
      assert.equal(reader.commands[0].args.persist, false);
    }
  }
});

test("failed save and mismatched read-back do not become success or update run settings", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {}, { policy });
  reader.fail = { outcome: "partial", status: 0x13 };
  await assert.rejects(service.setAntennas([1]), error => error.result === reader.fail);
  assert.equal(reader.commands.length, 1);
  await assert.rejects(service.configureBaseband({ speed: 4, q: 7, session: 2, target: 1 }));
  reader.fail = null;
  reader.readOverride = 999;
  await assert.rejects(service.configureBaseband({ speed: 4, q: 7, session: 2, target: 1 }), /read-back mismatch/);
  await service.startInventory([1]);
  assert.equal(reader.calls[0].config.q, 4);
});

for (const setting of [
  { name: "antenna SAVE", get: "get_antennas", register: "antennas", expected: 13,
    apply: service => service.setAntennas([1, 3, 4]) },
  { name: "baseband", get: "get_profile", register: "profile", expected: 123,
    apply: service => service.configureBaseband({ speed: 4, q: 7, session: 2, target: 1 }) },
  { name: "native region", get: "get_region", register: "region", expected: policy.bands[0].region,
    apply: service => service.setRfBand(0) },
  { name: "custom region", get: "get_custom_region", register: "custom_region", expected: policy.bands[6].centers,
    apply: service => service.setRfBand(6) },
]) {
  for (const failure of ["failure", "partial", "unknown", "throw", "throw_result"]) {
    test(`${setting.name}: acknowledged Set survives Get ${failure}`, async () => {
      const reader = new Reader();
      const readResult = { outcome: failure === "throw_result" ? "unknown" : failure,
        command: 0x21, status: null, data: null, confirmation: "none", diagnostics: ["Get failed"] };
      const cause = new Error("Bridge rejected Get");
      if (failure === "throw_result") cause.result = readResult;
      const call = reader.call.bind(reader);
      reader.call = async (name, args) => {
        const actual = await call(name, args);
        if (name !== setting.get) return { ...actual, confirmation: "acknowledged" };
        if (failure.startsWith("throw")) throw cause;
        return readResult;
      };
      const service = createNationInventoryService(reader, () => {}, { policy });
      await assert.rejects(setting.apply(service), error => {
        assert.match(error.message, /Write succeeded; .* verification failed/);
        assert.equal(error.result.outcome, ["unknown", "throw", "throw_result"].includes(failure) ? "unknown" : "partial");
        assert.equal(error.result.data, null);
        assert.equal(error.result.confirmation, "acknowledged");
        assert.equal(error.result.steps.length, 2);
        assert.equal(error.result.steps[0].outcome, "success");
        if (failure === "throw") {
          assert.equal(error.result.steps[1].outcome, "unknown");
          assert.deepEqual(error.result.steps[1].diagnostics, [cause.message]);
        } else assert.equal(error.result.steps[1], readResult);
        if (failure.startsWith("throw")) assert.equal(error.cause, cause);
        return true;
      });
      assert.deepEqual(reader.registers[setting.register], setting.expected);
      assert.equal(reader.commands.length, 2); // No automatic retry or rollback.
      await service.startInventory([1]);
      assert.equal(reader.calls[0].config.q, 4);
      assert.equal(reader.calls[0].config.session, 0);
      assert.equal(reader.calls[0].config.target, 0);
      service.dispose();
    });
  }
}

test("invalid antenna selection and uncertain Stop stay visible", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {});
  for (const ids of [[], [1, 1], [0], [17], [1.5]]) {
    await assert.rejects(service.startInventory(ids), /unique antenna IDs/);
  }
  assert.equal(reader.calls.length, 0);
  reader.outcome = { complete: false, outcome: "unknown", diagnostics: ["Stop timeout"] };
  await assert.rejects(service.stopInventory(), error => error.result === reader.outcome);
  service.dispose();
});

test("legacy service forwards each selected port of a four-port reader", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {});
  for (const antenna of [1, 2, 3, 4]) {
    await service.startInventory([antenna]);
    assert.equal(reader.calls.at(-1).config.antenna, antenna);
    assert.equal(reader.calls.at(-1).antenna_mask, 1 << (antenna - 1));
    assert.equal(reader.calls.at(-1).mode, "scenario");
    await service.stopInventory();
  }
  service.dispose();
});

test("four-port checkbox selection becomes one Scenario Start mask", async () => {
  const reader = new Reader();
  const service = createNationInventoryService(reader, () => {});
  await service.startInventory([1, 3, 4]);
  assert.equal(reader.calls.length, 1);
  assert.equal(reader.calls[0].antenna_mask, 0b1101);
  await service.stopInventory();
  service.dispose();
});

test("tag conversion preserves nulls, units and phase provenance without inventing PC", () => {
  const tag = { epc: "000000AB", tid: null, antenna: 1, rssi_dbm: -50,
    frequency_khz: 918750, phase_begin_degrees: 10, phase_end_degrees: 20 };
  const converted = toLegacyTag(tag);
  assert.equal(converted.epc, "000000AB");
  assert.equal(converted.frequency, 918.75);
  assert.equal(converted.native, tag);
  assert.equal(converted.rssi, -50);
  assert.equal("pc" in converted, false);
  assert.equal("phase" in converted, false);
  assert.equal(toLegacyTag({ epc: null, frequency_khz: null }).frequency, null);
});
