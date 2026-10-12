const {test} = require('node:test');
const assert = require('node:assert/strict');
const {inventoryRequest, verifiedWrite, Workspace} = require('../demo_app/static/workflows.js');
const defaults = {task:'epc', ports:[1], q:4, session:0, target:0, phase:false, scan:10, data:'epc', tidWords:6};

for (const count of [1,4]) test(`guided reading uses legal Scenario / FastID requests on ${count} ports`, () => {
  const values = {...defaults, ports: count === 1 ? [1] : [1,2,3,4]};
  const epc = inventoryRequest(values,count);
  assert.equal(epc.arguments.mode, 'scenario');
  assert.equal(epc.arguments.antenna_mask, count === 1 ? 1 : 15);
  assert.equal(epc.arguments.antenna_sequence, undefined);
  const fastid = inventoryRequest({...values, task:'fastid'},count);
  assert.equal(fastid.arguments.mode, 'answer');
  assert.equal(fastid.arguments.config.data, 'fastid');
  assert.deepEqual(fastid.arguments.antenna_sequence, values.ports);
  assert.equal(fastid.arguments.antenna_mask, undefined);
  assert.equal(fastid.arguments.config.scan_time_100ms,10);
  assert.deepEqual(inventoryRequest(values,count),epc); // switching back retains no FastID fields
});
test('single scan uses one port, supports TID and does not send stream selectors', () => {
  const request = inventoryRequest({...defaults, task:'once', ports:[4], data:'tid'},4);
  assert.equal(request.operation,'inventory_once');
  assert.equal(request.arguments.config.tid_word_count,6);
  assert.equal(request.arguments.config.antenna,4);
  assert.equal(request.arguments.mode,undefined);
  assert.throws(() => inventoryRequest({...defaults,task:'once',ports:[1,2]},4),/one antenna/);
});
test('guided validation rejects zero ports, duplicates, invalid bounds and unsupported restore', () => {
  for (const ports of [[],[0],[5],[1,1]]) assert.throws(() => inventoryRequest({...defaults,ports},4));
  for (const scan of ['',0,1,2,256,1.5]) assert.throws(() => inventoryRequest({...defaults,task:'fastid',scan},4));
  assert.throws(() => inventoryRequest(defaults,16),/not verified/);
  assert.throws(() => inventoryRequest({...defaults,session:128},4),/Session/);
});
test('Set/Get verification preserves write acknowledgement and never retries', async () => {
  for (const mode of ['get_reject','mismatch']) {
    const calls=[], written={outcome:'success',status:0};
    const call=async name => {calls.push(name); if (name==='set') return written; if (mode==='get_reject') throw new Error('Get failed'); return {data:3};};
    await assert.rejects(verifiedWrite(call,'set',{},'get',value=>value===15), error => {
      assert.equal(error.written,written); assert.match(error.message,/Write acknowledged; verification failed/);return true;
    });
    assert.deepEqual(calls,['set','get']);
  }
  const calls=[];
  await assert.rejects(verifiedWrite(async name=>{calls.push(name);throw new Error('Set rejected');},'set',{},'get',()=>true),/Set rejected/);
  assert.deepEqual(calls,['set']);
  assert.equal(await verifiedWrite(async name=>name==='get'?{data:15}:{status:0},'set',{},'get',value=>value===15),15);
});
test('custom channel plan fields match the SDK bounds and center convention', () => {
  const values={plan:'custom',frequency:'918000',channels:'8',spacing:'500'};
  const fake={el:id=>({value:values[id]})};
  const build=()=>Workspace.prototype.regionValue.call(fake);
  assert.deepEqual(build(),{start_frequency_khz:918000,channel_count:8,spacing_khz:500});
  for (const channels of ['0','62','']) {values.channels=channels;assert.throws(build);}
  values.channels='8';values.spacing='100';assert.throws(build,/125/);
  values.spacing='0';assert.throws(build,/positive/);
  values.channels='1';assert.equal(build().spacing_khz,0);
});

test('a missing native band never falls back to ALL band zero', () => {
  const values={plan:'native',band:'',min:'0',max:'3'};
  const allBand={band:0,max_channel:60};
  const fake={config:{regions:[allBand]},el:id=>({value:values[id]})};
  fake.band=()=>Workspace.prototype.band.call(fake);
  const build=()=>Workspace.prototype.regionValue.call(fake);
  for (const band of ['', '21', '29']) {
    values.band=band;
    assert.equal(fake.band(),undefined);
    assert.throws(build,/Choose a supported band/);
  }
  values.band='0';
  assert.equal(fake.band(),allBand);
  assert.deepEqual(build(),{band:0,min_channel:0,max_channel:3});
});
