import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Opening /#routing-flow in a full page load (for example from a URL that
// carries ?emailTab=) must open Routing Flow, not the page the session showed
// last. enhancements.js loads before routing_flow.js registers its view, so it
// must keep the requested hash until showApp resolves it.
const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function functionSource(file, name, indent = '') {
  const source = read(file);
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists in ${file}`);
  const end = source.indexOf(`\n${indent}}`, start);
  return source.slice(start, end + indent.length + 2);
}

function viewContext(url, storedView) {
  const store = new Map([['nowlert.active-view', storedView]]);
  const location = new URL(url);
  const navigated = [];
  const context = {
    VIEW_STORAGE_KEY: 'nowlert.active-view',
    VIEW_TITLES: {dashboard: 'Dashboard', backups: 'Backups', 'email-alerts': 'Email Alerts'},
    state: {currentView: ''},
    window: {
      location,
      sessionStorage: {getItem: key => store.get(key) || null, setItem: (key, value) => store.set(key, value)},
      history: {replaceState(_state, _title, next) { const resolved = new URL(next, location.href); location.hash = resolved.hash; }},
    },
    navigate(view) { navigated.push(view); context.state.currentView = view; },
  };
  const names = ['storageRead', 'storageWrite', 'desiredView', 'persistDesiredView', 'restorePersistedView', 'ensureRequestedView'];
  vm.runInNewContext(names.map(name => functionSource('enhancements.js', name, '  ')).join('\n'), context);
  return {context, store, location, navigated};
}

test('a deep link to a later-installed view survives the early view restore', () => {
  const {context, store, location, navigated} = viewContext('https://nowlert.example/#routing-flow', 'backups');

  context.restorePersistedView();
  assert.equal(location.hash, '#routing-flow');

  // routing_flow.js registers its page after enhancements.js has loaded.
  context.VIEW_TITLES['routing-flow'] = 'Routing Flow';
  context.ensureRequestedView();

  assert.deepEqual(navigated, ['routing-flow']);
  assert.equal(location.hash, '#routing-flow');
  assert.equal(store.get('nowlert.active-view'), 'routing-flow');
});

test('without a hash the last page of the session is restored', () => {
  const {context, location} = viewContext('https://nowlert.example/?emailTab=groups', 'backups');

  context.restorePersistedView();

  assert.equal(location.hash, '#backups');
});

test('an unknown hash still falls back to the last page once every view is installed', () => {
  const {context, navigated} = viewContext('https://nowlert.example/#not-a-page', 'backups');

  context.restorePersistedView();
  context.ensureRequestedView();

  assert.deepEqual(navigated, ['backups']);
});
