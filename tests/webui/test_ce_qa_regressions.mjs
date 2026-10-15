import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function functionSource(file, name, indent = '') {
  const source = read(file);
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1);
  const end = source.indexOf(`\n${indent}}`, start);
  return source.slice(source.slice(start - 6, start) === 'async ' ? start - 6 : start, end + indent.length + 2);
}

test('security page refresh redraws tokens after a workspace mutation', () => {
  let rendered = 0;
  const context = {
    state: {currentView: 'account'}, renderWorkspaceErrors() {}, applyLanguage() {},
    document: {querySelector() { return {}; }, body: {}},
    renderTokens() { rendered++; },
  };
  vm.runInNewContext(`${functionSource('app.js', 'renderCurrentView')}\nrenderCurrentView();`, context);
  assert.equal(rendered, 1);
});

test('repeated destination field refresh installs only one style control', () => {
  const wrappers = [];
  const native = {checked: true, closest: () => ({classList: {add() {}}})};
  const settings = {
    querySelector(selector) {
      if (selector.includes('components_v2')) return native;
      if (selector.includes('destination-discord-style')) return wrappers[0] || null;
      return null;
    },
    append(wrapper) { wrappers.push(wrapper); },
  };
  const context = {
    byId: id => id === 'destination-settings' ? settings : {value: 'discord'},
    element() { return {append() {}, addEventListener() {}}; },
  };
  vm.runInNewContext(`${functionSource('destination_routes.js', 'destinationEditorInstallDiscordStyleControl', '  ')}\ndestinationEditorInstallDiscordStyleControl(); destinationEditorInstallDiscordStyleControl();`, context);
  assert.equal(wrappers.length, 1);
});

test('filter validation errors are placed in the modal top layer', () => {
  const outside = [], inside = [];
  const context = {
    element: () => ({remove() {}, setAttribute() {}}),
    byId: () => ({append: item => outside.push(item)}),
    document: {querySelector: () => ({append: item => inside.push(item)})},
    window: {setTimeout() {}},
  };
  vm.runInNewContext(`${functionSource('app.js', 'toast')}\ntoast('Invalid field', 'error');`, context);
  assert.equal(inside.length, 1);
  assert.equal(outside.length, 0);
});

test('dashboard uses complete server totals instead of its recent activity page', () => {
  const context = {state: {metrics: {history: {total: 250, delivered: 245, failed: 5, retry: 0, successRate: 98}}}};
  const result = vm.runInNewContext(`${functionSource('operations_dashboard.js', 'successStats', '  ')}\nsuccessStats([]);`, context);
  assert.equal(result.total, 250);
  assert.equal(result.successRate, 98);
});

test('history forwards search and sort to the server and ignores an older response', async () => {
  const requests = [];
  const applied = [];
  const context = {
    state: {user: {id: 'qa-a'}},
    qaDeliveryRequestId: 0, qaDeliveryPageSize: 25, URLSearchParams,
    window: {nowlertDeliveryQuery: () => ({search: 'host & backup', sort: 'oldest', range: 'all'})},
    request: path => new Promise(resolve => requests.push({path, resolve})),
    qaApplyDeliveryPage: response => {applied.push(response); return response;},
  };
  vm.runInNewContext(functionSource('qa_patch.js', 'qaFetchDeliveryPage'), context);
  const first = context.qaFetchDeliveryPage(1), second = context.qaFetchDeliveryPage(2);
  const url = new URL(requests[1].path, 'https://example.invalid');
  assert.equal(url.pathname, '/deliveries/page/2/size/25');
  assert.equal(url.searchParams.get('search'), 'host & backup');
  assert.equal(url.searchParams.get('sort'), 'oldest');
  requests[1].resolve({page: 2}); await second;
  requests[0].resolve({page: 1}); await first;
  assert.equal(applied.length, 1);
  assert.equal(applied[0].page, 2);
});

test('history discards a response belonging to the previous account', async () => {
  let resolve, applied = false;
  const context = {
    state: {user: {id: 'qa-a'}}, qaDeliveryRequestId: 0, qaDeliveryPageSize: 25, URLSearchParams,
    window: {}, request: () => new Promise(done => {resolve = done;}),
    qaApplyDeliveryPage: () => {applied = true;},
  };
  vm.runInNewContext(functionSource('qa_patch.js', 'qaFetchDeliveryPage'), context);
  const pending = context.qaFetchDeliveryPage(1);
  context.state.user = {id: 'qa-b'};
  resolve({deliveries: [{title: 'Private A'}]});
  await pending;
  assert.equal(applied, false);
});

test('dashboard discards an in-flight batch after an account switch', async () => {
  const jobs = [];
  let painted = false;
  const context = {
    state: {user: {id: 'qa-a'}, historyRange: '1h', currentView: 'dashboard'},
    DASHBOARD_VIEW: 'dashboard', refreshBusy: false, refreshPending: false, refreshGeneration: 0,
    dashboardSnapshotIdentity: () => context.state.user?.id,
    request: () => new Promise(resolve => jobs.push(resolve)),
    renderOperationsDashboard: () => {painted = true;}, saveDashboardSnapshot() {},
    window: {queueMicrotask() {}},
  };
  vm.runInNewContext(functionSource('operations_dashboard.js', 'refreshDashboardData', '  '), context);
  const pending = context.refreshDashboardData(true);
  context.state.user = {id: 'qa-b'};
  jobs.forEach(resolve => resolve({metrics: {privateOwner: 'qa-a'}, deliveries: [], audit_events: []}));
  await pending;
  assert.equal(painted, false);
  assert.equal(context.state.metrics, undefined);
});

test('MFA disable response cannot replace a different signed-in user', async () => {
  let resolve;
  const context = {
    state: {user: {id: 'qa-a'}}, mfaDialogVersion: 1,
    clearError() {}, byId: () => ({value: 'test'}),
    request: () => new Promise(done => {resolve = done;}),
    closeMfaDialog() {}, document: {dispatchEvent() {}}, Event: class {}, toast() {}, showError() {},
  };
  vm.runInNewContext(functionSource('app.js', 'disableMfa'), context);
  const pending = context.disableMfa({preventDefault() {}});
  context.state.user = {id: 'qa-b'};
  resolve({user: {id: 'qa-a'}});
  await pending;
  assert.equal(context.state.user.id, 'qa-b');
});

test('destination selection preserves actual disabled route without adding its grouped representative', () => {
  const context = {Set};
  const result = vm.runInNewContext(`${functionSource('destination_routes.js', 'destinationRouteSelectionForItem')}\ndestinationRouteSelectionForItem({id:'dest',route_ids:['grouped'],actual_route_ids:['disabled']},[{id:'disabled',enabled:false,destination_ids:['dest']}]);`, context);
  assert.deepEqual([...result], ['disabled']);
});
