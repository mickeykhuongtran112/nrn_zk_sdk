// Run with: node --test tests/browser/demo_client.test.cjs
// Exercise the shipped client with controlled HTTP/timing; DOM painting is
// checked separately in the browser, so no DOM emulation dependency is needed.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../demo_app/static/app.js'), 'utf8');

function client(fetch) {
  const nodes = new Map(), timers = [];
  const context = vm.createContext({
    fetch, AbortController, AbortSignal, TextDecoder,
    document: {getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {textContent: '', className: '', classList: {add() {}, remove() {}}});
      return nodes.get(id);
    }},
    requestAnimationFrame: fn => fn(),
    setTimeout: (fn, ms) => { timers.push({fn, ms}); return timers.length; },
    clearTimeout() {},
  });
  assert.match(source, /boot\(\)\.catch\(fail\);\s*$/);
  vm.runInContext(source.replace(/boot\(\)\.catch\(fail\);\s*$/, ''), context);
  // Rendering/forms are independent of the transport and row reconciliation.
  vm.runInContext('renderTags = () => {}; renderSnapshot = s => { snapshot = s; };', context);
  return {run: code => vm.runInContext(code, context), nodes, timers};
}
const row = (count, first_seen = 1) => ({epc: 'E2001234', antenna_mask: 1, count, first_seen});
const snapshot = (count, generation) => ({
  tags: count ? [row(count)] : [], received_count: count, unique_ids: count ? 1 : 0,
  ...(generation == null ? {} : {tag_generation: generation}),
});
const live = (count, generation = 1) => ({
  rows: count ? [row(count)] : [], received_count: count, unique_ids: count ? 1 : 0,
  cursor: [generation, count], reset: true,
});
const jsonResponse = data => ({ok: true, json: async () => data});

test('old API: missing live endpoint falls back to snapshot, no endless 404 retries', async () => {
  const paths = [];
  let count = 7;
  const c = client(async url => {
    paths.push(url);
    return url === '/api/live'
      ? {ok: false, status: 404, json: async () => ({error: 'Not found'})}
      : jsonResponse(snapshot(count));
  });
  await c.run('streamLive()');
  assert.equal(c.run('liveSupported'), false);
  assert.equal(c.timers.filter(t => t.ms === 1000).length, 0);
  await c.run('poll()');
  assert.match(paths.at(-1), /tags=1/);
  assert.equal(c.nodes.get('reportCount').textContent, '7');
  assert.equal(c.run("liveTags.get('E2001234||1').count"), 7);
  assert.match(c.nodes.get('liveStatus').textContent, /HTTP 404.*restart Python/);
  // Polls must preserve a selected target instead of clearing it every 750 ms.
  c.run("selectedTagKey = 'E2001234||1'; selectedTarget = {epc:'E2001234'};");
  count = 14;
  await c.run('poll()');
  assert.equal(c.run('selectedTarget.epc'), 'E2001234');
  assert.equal(c.nodes.get('reportCount').textContent, '14');
  assert.equal(c.run("liveTags.get('E2001234||1').rssi_dbm"), undefined);
});

test('transient stream error uses snapshots then reconnect replaces with exact live totals', async () => {
  const paths = [];
  const c = client(async url => {
    paths.push(url);
    if (url === '/api/live') throw new TypeError('Network interrupted');
    return jsonResponse(snapshot(9, 1));
  });
  c.run(`receiveLive(${JSON.stringify(live(7))})`);
  await c.run('poll()');
  assert.match(paths.at(-1), /tags=0/);
  await c.run('streamLive()');
  assert.equal(c.run('liveSupported'), true);
  assert.equal(c.timers.filter(t => t.ms === 1000).length, 1);
  await c.run('poll()');
  assert.match(paths.at(-1), /tags=1/);
  assert.equal(c.nodes.get('reportCount').textContent, '9');
  c.run(`receiveLive(${JSON.stringify(live(14))})`);
  assert.equal(c.nodes.get('reportCount').textContent, '14');
  assert.match(c.nodes.get('liveStatus').textContent, /^Live tag stream/);
});

test('snapshot in flight cannot overwrite live data, even after another stream failure', async () => {
  let resolveSnapshot;
  const c = client(url => url === '/api/live'
    ? Promise.reject(new TypeError('Disconnected'))
    : new Promise(resolve => { resolveSnapshot = resolve; }));
  const pending = c.run('poll()');
  c.run(`receiveLive(${JSON.stringify(live(100))})`);
  await c.run('streamLive()');
  resolveSnapshot(jsonResponse(snapshot(2, 1)));
  await pending;
  assert.equal(c.nodes.get('reportCount').textContent, '100');
});

test('replacement snapshots remove absent rows and clear selection on new generation', () => {
  const c = client();
  c.run(`snapshotTagFallback(${JSON.stringify(snapshot(5, 1))}, liveEpoch)`);
  c.run("selectedTagKey = 'E2001234||1'; selectedTarget = {epc:'E2001234'};");
  // Clear followed by the same EPC can happen between browser polls.
  c.run(`snapshotTagFallback(${JSON.stringify(snapshot(10, 2))}, liveEpoch)`);
  assert.equal(c.run('selectedTarget'), null);
  c.run(`snapshotTagFallback(${JSON.stringify(snapshot(0, 3))}, liveEpoch)`);
  assert.equal(c.run('liveTags.size'), 0);
  assert.equal(c.nodes.get('reportCount').textContent, '0');
});

test('legacy snapshot reappearance with new first_seen clears stale selection', () => {
  const c = client();
  c.run(`snapshotTagFallback(${JSON.stringify(snapshot(5))}, liveEpoch)`);
  c.run("selectedTagKey = 'E2001234||1'; selectedTarget = {epc:'E2001234'};");
  const restarted = snapshot(20);
  restarted.tags[0].first_seen = 200;
  c.run(`snapshotTagFallback(${JSON.stringify(restarted)}, liveEpoch)`);
  assert.equal(c.run('selectedTarget'), null);
});

test('HTTP status survives a non-JSON response for unsupported endpoint detection', async () => {
  const c = client(async () => ({
    ok: false, status: 501, statusText: 'Not Implemented', json: async () => { throw new Error('HTML body'); },
  }));
  await c.run('streamLive()');
  assert.equal(c.run('liveSupported'), false);
  assert.match(c.nodes.get('liveStatus').textContent, /HTTP 501/);
});
