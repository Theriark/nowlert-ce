import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Opening Routing Flow fired GET /api/v2/filters three times at once from
// separate panels; each waited on the others on the server. Identical plain GETs
// that are already in flight now share one call, and each caller gets its own copy.

const appSource = readFileSync(new URL('../../src/webui/app.js', import.meta.url), 'utf8');

function block(startMarker) {
  const start = appSource.indexOf(startMarker);
  assert.notEqual(start, -1, `${startMarker} not found`);
  const end = appSource.indexOf('\n}\n', start);
  return appSource.slice(start, end + 3);
}

function sandbox(fetchImpl) {
  const context = {
    API: '/api/v2', SAFE_METHODS: new Set(['GET', 'HEAD', 'OPTIONS']), state: {csrf: 'c'},
    fetch: fetchImpl, structuredClone, Map, JSON, Object, String, Promise,
    APIError: class extends Error {}, requireReauthentication: async () => false,
  };
  vm.createContext(context);
  const source = ['const inflightGets = new Map();', block('async function request('), block('async function sendRequest(')].join('\n');
  vm.runInContext(source, context);
  return context;
}

function jsonResponse(payload) {
  return {ok: true, status: 200, text: async () => JSON.stringify(payload)};
}

test('concurrent plain GETs of the same path share one network call', async () => {
  let calls = 0;
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  const context = sandbox(async () => { calls += 1; await gate; return jsonResponse({items: [1]}); });
  const pending = [context.request('/filters'), context.request('/filters'), context.request('/filters')];
  release();
  const [a, b, c] = await Promise.all(pending);
  assert.equal(calls, 1);
  assert.deepEqual(a, {items: [1]});
  a.items.push(2);
  assert.deepEqual(b, {items: [1]}, 'each caller gets its own copy');
  assert.notEqual(b, c);
  await context.request('/filters');
  assert.equal(calls, 2, 'a later call fetches fresh data');
});

test('writes and GETs with options are never shared', async () => {
  let calls = 0;
  const context = sandbox(async () => { calls += 1; return jsonResponse({ok: true}); });
  await Promise.all([
    context.request('/filters', {method: 'POST', body: {}}),
    context.request('/filters', {method: 'POST', body: {}}),
    context.request('/filters', {dashboardFeed: true}),
    context.request('/filters', {dashboardFeed: true}),
  ]);
  assert.equal(calls, 4);
});
