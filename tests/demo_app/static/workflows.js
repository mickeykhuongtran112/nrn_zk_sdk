/* Task-oriented controls for the native SDK console. No reader protocol logic. */
((root) => {
  'use strict';
  const integer = (value, low, high, label) => {
    const n = typeof value === 'string' && value.trim() ? Number(value) : value;
    if (!Number.isInteger(n) || n < low || n > high) throw new Error(`${label}: enter ${low}–${high}.`);
    return n;
  };
  function selectedPorts(ports, count) {
    if (!Array.isArray(ports) || !ports.length) throw new Error('Select at least one antenna.');
    const values = ports.map(p => integer(p, 1, count, 'Antenna'));
    if (new Set(values).size !== values.length) throw new Error('Each antenna can only appear once.');
    return values;
  }
  const maskOf = ports => ports.reduce((mask, port) => mask | (1 << (port - 1)), 0);
  function inventoryRequest(v, count) {
    const ports = selectedPorts(v.ports, count);
    if (!['epc', 'fastid', 'once'].includes(v.task)) throw new Error('Choose a reading task.');
    if (v.task === 'epc' && count === 16) throw new Error('Scenario restore is not verified for 16 ports. Use All APIs for supported Answer operations.');
    if (v.task === 'once' && ports.length !== 1) throw new Error('Single scan uses one antenna.');
    const data = v.task === 'once' ? v.data : v.task;
    if (!['epc', 'fastid', 'tid'].includes(data)) throw new Error('Unsupported tag data.');
    const config = {
      data, antenna: ports[0], q: integer(v.q, 0, 15, 'Q'),
      session: integer(v.session, 0, 3, 'Session'), target: integer(v.target, 0, 1, 'Target'),
      phase: !!v.phase,
    };
    if (v.task !== 'epc') config.scan_time_100ms = integer(v.scan, 3, 255, 'Round limit (100 ms)');
    if (data === 'tid') config.tid_word_count = integer(v.tidWords, 1, 15, 'TID words');
    if (v.task === 'once') return {operation: 'inventory_once', arguments: {config}};
    return {operation: 'start_inventory', arguments: v.task === 'epc'
      ? {mode: 'scenario', config, antenna_mask: maskOf(ports)}
      : {mode: 'answer', config, antenna_sequence: ports}};
  }
  async function verifiedWrite(call, operation, args, getter, matches) {
    const written = await call(operation, args);
    try {
      const read = await call(getter, {});
      if (!matches(read.data)) throw new Error('read-back does not match the requested value');
      return read.data;
    } catch (cause) {
      const error = new Error(`Write acknowledged; verification failed: ${cause.message}. Read the setting again before another write.`);
      error.written = written; error.cause = cause;
      throw error;
    }
  }

  class Workspace {
    constructor({element, config, call, stop, refresh}) {
      Object.assign(this, {element, config, call, stop, refresh});
      this.busy = false; this.count = 0; this.connectionKey = ''; this.state = null;
      this.antennaLoaded = false; this.powerLoaded = false;
      this.draw();
    }
    el(id) { return this.element.querySelector('#g-' + id); }
    draw() {
      this.element.innerHTML = `
<div id="g-status" class="workflow-status" role="status" aria-live="polite">Connect a reader or choose the simulator to begin.</div>
<section data-page="Inventory">
  <div class="card workflow-card">
    <div class="card-header"><div><span class="eyebrow">READ TAGS</span><h2>What would you like to read?</h2></div><span class="badge neutral">THIS RUN</span></div>
    <fieldset id="g-inventory-controls" class="plain-fieldset">
      <div class="task-options" role="radiogroup" aria-label="Reading task">
        <label class="task-option"><input type="radio" name="reading-task" value="epc" checked><span><b>Continuous EPC</b><small>Read identifiers until you stop.</small></span></label>
        <label class="task-option"><input type="radio" name="reading-task" value="fastid"><span><b>EPC + TID · FastID</b><small>Repeat rounds across selected antennas.</small></span></label>
        <label class="task-option"><input type="radio" name="reading-task" value="once"><span><b>Single scan</b><small>One bounded round on one antenna.</small></span></label>
      </div>
      <div class="run-layout">
        <div><div class="block-heading"><h3>Antennas for this run</h3><button type="button" id="g-use-selection">Use reader selection</button></div><div id="g-run-antennas" class="antenna-picks"></div><p class="hint">Only select ports with antennas attached. Run selection does not save reader settings.</p></div>
        <div class="run-options"><label id="g-once-data" class="hidden">Tag data<select id="g-data"><option value="epc">EPC</option><option value="fastid">EPC + TID (FastID)</option><option value="tid">TID only</option></select></label><label id="g-round-field" class="hidden">Round limit · 100 ms<input id="g-scan" type="number" min="3" max="255" value="10"><small>A maximum per antenna round, not a fixed dwell time.</small></label><label id="g-tid-field" class="hidden">TID length · words<input id="g-tid-words" type="number" min="1" max="15" value="6"></label><label class="check phase-option"><input id="g-phase" type="checkbox"> Include phase measurements</label></div>
      </div>
      <details class="workflow-details"><summary>Query settings</summary><div class="query-grid"><label>Q<input id="g-q" type="number" min="0" max="15" value="4"></label><label>Session<select id="g-session"><option value="0">S0</option><option value="1">S1</option><option value="2">S2</option><option value="3">S3</option></select></label><label>Target<select id="g-target"><option value="0">A</option><option value="1">B</option></select></label></div><p class="hint">Scenario selectors S-CST / S-PRO and custom masks are available in All APIs.</p></details>
    </fieldset>
    <div class="run-footer"><div><b id="g-run-summary"></b><p id="g-run-help" class="hint"></p><small id="g-gate"></small></div><div class="tools"><button id="g-stop" class="stop">Stop reading</button><button id="g-start" class="primary">Start reading</button></div></div>
    <details class="workflow-details"><summary>SDK request preview</summary><pre id="g-preview"></pre></details>
  </div>
</section>
<section data-page="Antenna & power" class="hidden">
  <div class="card workflow-card"><div class="card-header"><div><span class="eyebrow">READER CONFIGURATION</span><h2>Antenna selection & transmit power</h2><small>Read current values before making changes.</small></div><button id="g-read-antennas">Read from reader</button></div>
    <fieldset id="g-antenna-controls" class="plain-fieldset"><div id="g-port-rows" class="port-rows"></div><div class="settings-actions"><div><button id="g-save-antennas">Save antenna selection</button><p class="hint">Saved on the module. At least one port must remain enabled.</p></div><div><label class="check"><input id="g-power-save" type="checkbox"> Save power after power-off</label><button id="g-save-power">Apply power</button><p class="hint">Unchecked: temporary power settings. All port values are read back.</p></div></div></fieldset>
    <p id="g-antenna-note" class="setting-note">Current antenna selection and power have not been read.</p>
  </div>
</section>
<section data-page="RF settings" class="hidden settings-grid">
  <div class="card workflow-card"><div class="card-header"><div><span class="eyebrow">FREQUENCY PLAN</span><h2>Region</h2></div><button id="g-read-region">Read region</button></div><fieldset id="g-region-controls" class="plain-fieldset"><label>Plan type<select id="g-plan"><option value="native">Reader preset</option><option value="custom">Custom channel plan</option></select></label><div id="g-native-region"><label>Band<select id="g-band"></select></label><div class="query-grid two"><label>First channel<input id="g-min" type="number" min="0" value="0"></label><label>Last channel<input id="g-max" type="number" min="0" value="49"></label></div></div><div id="g-custom-region" class="hidden"><label>First channel · kHz<input id="g-frequency" type="number" placeholder="e.g. 918000"></label><div class="query-grid two"><label>Channel count<input id="g-channels" type="number" min="1" max="61" placeholder="e.g. 8"></label><label>Spacing · kHz<input id="g-spacing" type="number" min="0" step="125" placeholder="e.g. 500"></label></div></div><p id="g-frequency-summary" class="setting-note"></p><p class="hint">Use a frequency plan approved for your deployment. Preset names identify ZK tables, not regional operating permission.</p><label class="check"><input id="g-region-save" type="checkbox"> Save after power-off</label><button id="g-apply-region" class="primary">Apply region</button></fieldset><p id="g-region-note" class="hint">Not read from reader.</p></div>
  <div class="card workflow-card"><div class="card-header"><div><span class="eyebrow">AIR INTERFACE</span><h2>RF profile</h2></div><button id="g-read-profile">Read profile</button></div><fieldset id="g-profile-controls" class="plain-fieldset"><label>Reader profile<select id="g-profile"></select></label><p class="hint">Native ZK profiles. The NATION adapter's approved baseband mapping is separate.</p><label class="check"><input id="g-profile-save" type="checkbox"> Save after power-off</label><button id="g-apply-profile" class="primary">Apply profile</button></fieldset><p id="g-profile-note" class="hint">Not read from reader.</p><div class="settings-tip"><b>Need a specific command?</b><p>S-CST profiles, Range Control, TagFocus and raw configuration remain in All APIs and Ex10 config.</p></div></div>
</section>`;
      const bands = {0:'ALL band', 1:'Chinese band2', 2:'US band', 3:'Korean band', 4:'EU band', 8:'Chinese band1', 9:'EU3 band', 12:'US band3', 31:'Japan band'};
      for (const r of this.config.regions) this.el('band').add(new Option(`${r.band} · ${bands[r.band] || 'Native band'} · ${r.base_khz / 1000} MHz`, r.band));
      this.el('band').value = '2';
      for (const p of this.config.profiles) this.el('profile').add(new Option(`${p.id} · ${p.encoding} · BLF ${p.blf_khz} kHz · Tari ${p.tari_us} µs`, p.id));
      this.el('profile').value = '';
      this.element.querySelectorAll('[name="reading-task"]').forEach(n => n.onchange = () => {
        if (this.task() === 'once') this.selectRun([this.runPorts()[0] || 1]);
        this.preview();
      });
      this.el('inventory-controls').oninput = () => this.preview();
      this.el('data').onchange = () => this.preview();
      this.el('start').onclick = () => this.run(async () => {
        const request = this.request();
        await this.call(request.operation, request.arguments);
        return request.operation === 'inventory_once' ? 'Scan complete. Results are in Tag observations.' : 'Reading started. Use Stop reading to end this session.';
      });
      this.el('stop').onclick = async () => {
        this.message('Stopping…');
        try { await this.stop(); this.message('Reading stopped. Review the final outcome below.', true); }
        catch (e) { this.message(e.message, false); }
      };
      this.el('use-selection').onclick = () => this.run(async () => {
        const read = await this.call('get_antennas', {});
        this.selectRun(this.portsFromMask(read.data)); this.preview();
        return 'Run antennas loaded from the reader.';
      });
      this.el('read-antennas').onclick = () => this.readAntennas();
      this.el('save-antennas').onclick = () => this.saveAntennas();
      this.el('save-power').onclick = () => this.savePower();
      this.el('antenna-controls').oninput = () => this.el('antenna-note').textContent = 'Unapplied edits. Use Save antenna selection / Apply power to change the reader.';
      this.el('plan').onchange = () => this.frequencyPreview();
      this.el('band').onchange = () => {
        const band = this.band(); this.el('min').value = 0; this.el('max').value = band.max_channel; this.frequencyPreview();
      };
      this.el('region-controls').oninput = () => {
        this.frequencyPreview(); this.el('region-note').textContent = 'Unapplied edits. Use Apply region to change the reader.';
      };
      this.el('profile-controls').oninput = () => this.el('profile-note').textContent = 'Unapplied edits. Use Apply profile to change the reader.';
      this.el('read-region').onclick = () => this.readRegion();
      this.el('apply-region').onclick = () => this.applyRegion();
      this.el('read-profile').onclick = () => this.readProfile();
      this.el('apply-profile').onclick = () => this.applyProfile();
      this.frequencyPreview();
    }
    task() { return this.element.querySelector('[name="reading-task"]:checked').value; }
    runPorts() { return [...this.el('run-antennas').querySelectorAll('input:checked')].map(n => Number(n.value)); }
    selectRun(ports) {
      if (this.task() === 'once') ports = ports.slice(0, 1);
      this.el('run-antennas').querySelectorAll('input').forEach(n => n.checked = ports.includes(Number(n.value)));
    }
    portsFromMask(mask) { return Array.from({length: this.count}, (_, i) => i + 1).filter(p => mask & (1 << (p - 1))); }
    request() {
      return inventoryRequest({task: this.task(), data: this.el('data').value, ports: this.runPorts(),
        q: this.el('q').value, session: this.el('session').value, target: this.el('target').value,
        phase: this.el('phase').checked, scan: this.el('scan').value, tidWords: this.el('tid-words').value}, this.count);
    }
    preview() {
      const task = this.task();
      this.el('once-data').classList.toggle('hidden', task !== 'once');
      this.el('tid-field').classList.toggle('hidden', task !== 'once' || this.el('data').value !== 'tid');
      this.el('round-field').classList.toggle('hidden', task === 'epc');
      this.el('start').textContent = task === 'once' ? 'Run single scan' : 'Start reading';
      this.el('run-help').textContent = task === 'fastid'
        ? 'EPC + TID where available. Some reports can contain EPC only. Selected ports repeat in ascending order.'
        : task === 'epc' ? 'Reader-managed Scenario stream. Antennas and query settings are restored after Stop.' : 'Answer mode: the reader completes one round, then returns idle.';
      try {
        const req = this.request(); this.valid = true;
        this.el('run-summary').textContent = `${task === 'epc' ? 'Scenario' : 'Answer'} · ${this.runPorts().map(p => 'ANT' + p).join(' → ')}`;
        this.el('preview').textContent = JSON.stringify(req, null, 2);
      } catch (e) { this.valid = false; this.el('run-summary').textContent = e.message; this.el('preview').textContent = e.message; }
      this.update(this.state);
    }
    show(page) { this.element.querySelectorAll('[data-page]').forEach(n => n.classList.toggle('hidden', n.dataset.page !== page)); }
    update(state) {
      this.state = state;
      const count = Number(state?.connection?.ports || this.config.defaults.ports);
      const key = state?.connected ? JSON.stringify(state.connection) : '';
      if (count !== this.count || key !== this.connectionKey) {
        this.connectionKey = key; this.count = count; this.antennaLoaded = false; this.powerLoaded = false;
        this.el('run-antennas').replaceChildren(); this.el('port-rows').replaceChildren();
        for (let p = 1; p <= count; p++) {
          const label = document.createElement('label'); label.className = 'antenna-pick';
          label.innerHTML = `<input type="checkbox" value="${p}" ${p === 1 ? 'checked' : ''}><span>ANT ${p}</span>`;
          label.querySelector('input').onchange = e => { if (this.task() === 'once' && e.target.checked) this.selectRun([p]); this.preview(); };
          this.el('run-antennas').append(label);
          const row = document.createElement('div'); row.className = 'port-row';
          row.innerHTML = `<b>ANT ${p}</b><label class="check"><input type="checkbox" id="g-enabled-${p}"> Enabled</label><label>Power · dBm<input id="g-power-${p}" type="number" min="0" max="30" placeholder="Not read"></label>`;
          this.el('port-rows').append(row);
        }
        this.el('antenna-note').textContent = 'Current antenna selection and power have not been read.';
        this.el('region-note').textContent = 'Not read from reader.'; this.el('profile-note').textContent = 'Not read from reader.';
        this.message(state?.connected ? 'Ready. Choose a reading task or read the current settings.' : 'Connect a reader or choose the simulator to begin.');
        this.preview(); return;
      }
      const healthy = !!state?.connected && !state.fault && !state.recovery_required;
      const active = ['starting', 'inventorying', 'stopping'].includes(state?.state);
      const locked = !healthy || this.busy || !!state?.busy || active || [1, 2].includes(state?.working_mode);
      for (const id of ['inventory-controls', 'antenna-controls', 'region-controls', 'profile-controls', 'read-antennas', 'read-region', 'read-profile']) this.el(id).disabled = locked;
      this.el('save-antennas').disabled = locked || !this.antennaLoaded;
      this.el('save-power').disabled = locked || !this.powerLoaded;
      this.el('start').disabled = locked || !this.valid;
      this.el('stop').disabled = !healthy || !!state?.control_busy || !(active || [1, 2].includes(state?.working_mode));
      this.el('gate').textContent = !state?.connected ? 'Connect to enable reading.' : state.recovery_required || state.fault ? 'Connection recovery required. See the last operation.' : active ? 'Reading active. Stop before changing configuration.' : [1, 2].includes(state.working_mode) ? 'Reader is in Real-time/Trigger mode. Stop reading to return to Answer.' : '';
    }
    async run(fn) {
      if (this.busy) return;
      this.busy = true; this.refresh(); this.message('Working…');
      try { this.message(await fn(), true); }
      catch (e) { this.message(e.message, false); }
      finally { this.busy = false; this.refresh(); }
    }
    message(text, ok) { const n = this.el('status'); n.textContent = text; n.className = 'workflow-status' + (ok === true ? ' success' : ok === false ? ' failure' : ''); }
    async readAntennas() {
      return this.run(async () => {
        this.antennaLoaded = false; this.powerLoaded = false;
        const selection = await this.call('get_antennas', {});
        for (let p = 1; p <= this.count; p++) this.el('enabled-' + p).checked = !!(selection.data & (1 << (p - 1)));
        this.antennaLoaded = true;
        const power = await this.call('get_power', {});
        if (power.data.length !== this.count) throw new Error('Unexpected port count in power response.');
        power.data.forEach((v, i) => this.el('power-' + (i + 1)).value = v);
        this.powerLoaded = true; this.el('antenna-note').textContent = 'Current values read from the reader. Edits are not applied until you press Save / Apply.';
        return 'Antenna selection and per-port power loaded.';
      });
    }
    async saveAntennas() {
      return this.run(async () => {
        const ports = Array.from({length: this.count}, (_, i) => i + 1).filter(p => this.el('enabled-' + p).checked);
        const mask = maskOf(selectedPorts(ports, this.count));
        this.antennaLoaded = false;
        await verifiedWrite(this.call, 'set_antennas', {mask, persist: true}, 'get_antennas', v => v === mask);
        this.antennaLoaded = true; this.selectRun(ports); this.preview();
        return 'Antenna selection saved and read back. Inventory now uses these ports.';
      });
    }
    async savePower() {
      return this.run(async () => {
        const values = Array.from({length: this.count}, (_, i) => integer(this.el('power-' + (i + 1)).value, 0, 30, 'ANT' + (i + 1) + ' power'));
        const persist = this.el('power-save').checked;
        this.powerLoaded = false;
        await verifiedWrite(this.call, 'set_power', {power_dbm: values, persist}, 'get_power', v => JSON.stringify(v) === JSON.stringify(values));
        this.powerLoaded = true;
        return `Power ${persist ? 'saved' : 'applied temporarily'} and read back on every port.`;
      });
    }
    band() {
      const value = this.el('band').value;
      return value === '' ? undefined : this.config.regions.find(r => r.band === Number(value));
    }
    regionValue() {
      if (this.el('plan').value === 'native') {
        const band = this.band(); if (!band) throw new Error('Choose a supported band.');
        const min = integer(this.el('min').value, 0, band.max_channel, 'First channel');
        return {band: band.band, min_channel: min, max_channel: integer(this.el('max').value, min, band.max_channel, 'Last channel')};
      }
      const region = {start_frequency_khz: integer(this.el('frequency').value, 1, 0xFFFFFF, 'First frequency'),
        channel_count: integer(this.el('channels').value, 1, 61, 'Channel count'),
        spacing_khz: integer(this.el('spacing').value, 0, 255 * 125, 'Spacing')};
      if (region.spacing_khz % 125 || (region.channel_count > 1 && !region.spacing_khz)) throw new Error('Spacing must be a multiple of 125 kHz and positive for multiple channels.');
      integer(region.start_frequency_khz + (region.channel_count - 1) * region.spacing_khz, 1, 0xFFFFFF, 'Last channel frequency');
      return region;
    }
    frequencyPreview() {
      const custom = this.el('plan').value === 'custom';
      this.el('native-region').classList.toggle('hidden', custom); this.el('custom-region').classList.toggle('hidden', !custom);
      try {
        const r = this.regionValue(), band = this.band();
        const first = custom ? r.start_frequency_khz : band.base_khz + r.min_channel * band.spacing_khz;
        const last = custom ? first + (r.channel_count - 1) * r.spacing_khz : band.base_khz + r.max_channel * band.spacing_khz;
        this.el('frequency-summary').textContent = `${(first / 1000).toFixed(3)}–${(last / 1000).toFixed(3)} MHz · channel centers`;
      } catch (e) { this.el('frequency-summary').textContent = e.message; }
    }
    async readRegion() {
      return this.run(async () => {
        const {data: r} = await this.call('get_region', {});
        if ('band' in r) {
          this.el('plan').value = 'native'; this.el('band').value = r.band;
          this.el('min').value = r.min_channel; this.el('max').value = r.max_channel;
          if (!this.band()) {
            this.frequencyPreview();
            this.el('region-note').textContent = `Current band ${r.band} is not editable in this form.`;
            throw new Error(`Band ${r.band} is available through All APIs; its frequency formula is unverified.`);
          }
        } else {
          this.el('plan').value = 'custom'; this.el('frequency').value = r.start_frequency_khz;
          this.el('channels').value = r.channel_count; this.el('spacing').value = r.spacing_khz;
        }
        this.frequencyPreview(); this.el('region-note').textContent = 'Current region read from the reader.';
        return 'Region loaded. Editing the form does not change the reader.';
      });
    }
    async applyRegion() {
      return this.run(async () => {
        const region = this.regionValue(), persist = this.el('region-save').checked;
        this.el('region-note').textContent = 'New values have not been verified.';
        const operation = this.el('plan').value === 'custom' ? 'set_custom_region' : 'set_region';
        const args = operation === 'set_custom_region' ? {...region, persist} : {region, persist};
        await verifiedWrite(this.call, operation, args, 'get_region', v => Object.entries(region).every(([k, x]) => v[k] === x));
        this.el('region-note').textContent = 'Applied and verified by read-back.';
        return `Region ${persist ? 'saved' : 'applied temporarily'} and read back.`;
      });
    }
    async readProfile() {
      return this.run(async () => {
        const {data} = await this.call('get_profile', {});
        if (![...this.el('profile').options].some(o => o.value === String(data))) this.el('profile').add(new Option(`${data} · Reported by reader (parameters unknown)`, data));
        this.el('profile').value = data; this.el('profile-note').textContent = `Current reader profile: ${data}.`;
        return 'RF profile loaded.';
      });
    }
    async applyProfile() {
      return this.run(async () => {
        const profile_id = integer(this.el('profile').value, 0, 65535, 'Profile'), persist = this.el('profile-save').checked;
        this.el('profile-note').textContent = 'New profile has not been verified.';
        await verifiedWrite(this.call, 'set_profile', {profile_id, persist}, 'get_profile', v => v === profile_id);
        this.el('profile-note').textContent = `Profile ${profile_id} verified by read-back.`;
        return `RF profile ${persist ? 'saved' : 'applied temporarily'} and read back.`;
      });
    }
  }
  const api = {integer, maskOf, selectedPorts, inventoryRequest, verifiedWrite, Workspace};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ZKWorkflows = api;
})(globalThis);
