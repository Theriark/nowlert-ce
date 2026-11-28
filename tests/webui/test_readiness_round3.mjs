import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';

// WebUI fixes of the third v27.0.0 readiness check.
const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function fn(file, name) {
  const source = read(file);
  let start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists in ${file}`);
  if (source.slice(start - 6, start) === 'async ') start -= 6;
  const end = source.indexOf('\n}', start);
  return source.slice(start, end + 2);
}
function apiErrorContext() {
  const source = read('app.js');
  const start = source.indexOf('class APIError extends Error');
  const end = source.indexOf('\nasync function request(', start);
  return vm.createContext({Error, source: source.slice(start, end)});
}

test('short server validation phrases become sentences that say what to do', () => {
  const ctx = apiErrorContext();
  vm.runInContext(`${ctx.source}\nglobalThis.check = text => uiErrorMessage(new APIError(400, text), 'fallback');`, ctx);
  const message = text => ctx.check(text);
  assert.equal(message('invalid credentials'), 'The username or password is not correct. Check both and try again.');
  assert.equal(message('password must contain at least 12 characters'), 'The password must contain at least 12 characters. Choose a longer password.');
  assert.equal(message('username is already configured'), 'That username is already in use. Choose another username.');
  assert.equal(message('token name is already configured for this owner'), 'An Event API token with this name already exists. Choose another name.');
  assert.equal(message('backup target name is already configured'), 'A backup destination with this name already exists. Choose another name.');
  // Every other message is shown unchanged.
  assert.equal(message('Filter values must not exceed 256 characters.'), 'Filter values must not exceed 256 characters.');
});

test('the route picker says whose copy a route is', () => {
  const require = createRequire(import.meta.url);
  const {routeOwnerSuffix} = require('../../src/webui/destination_routes.js');
  const user = {id: 'u1'};
  assert.equal(routeOwnerSuffix({owner_user_id: 'u1', owner_username: 'alice'}, user), ' · Owner: you');
  assert.equal(routeOwnerSuffix({owner_user_id: 'u2', owner_username: 'administrator'}, user), ' · Owner: administrator');
  assert.equal(routeOwnerSuffix({owner_user_id: 'u2'}, user), '');
  assert.equal(routeOwnerSuffix({}, user), '');
});

function navigateContext(url, view) {
  const location = new URL(url);
  const calls = [];
  const node = {classList: {remove() {}, toggle() {}, contains: () => false}, setAttribute() {}, removeAttribute() {}, focus() {}, dataset: {}, textContent: ''};
  const context = {
    VIEW_TITLES: {dashboard: 'Dashboard', settings: 'Settings', 'email-alerts': 'Email Alerts'},
    state: {user: {id: 'u1'}, currentView: ''},
    isAdmin: () => true,
    renderCurrentView() {},
    closeProfileMenu() {},
    byId: () => node,
    queueMicrotask() {},
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init?.detail; } },
    URL,
    document: {querySelectorAll: () => [], dispatchEvent() {}},
    window: {
      location,
      history: {
        state: null,
        replaceState(_state, _title, next) { calls.push(['replace', String(next)]); },
        pushState(_state, _title, next) { calls.push(['push', String(next)]); },
      },
    },
  };
  vm.runInNewContext(`${fn('app.js', 'navigate')}\nnavigate(${JSON.stringify(view)});`, context);
  return calls;
}

test('leaving Email Alerts drops its ?emailTab= from the address', () => {
  assert.deepEqual(navigateContext('https://nowlert.example/?emailTab=groups#email-alerts', 'settings'), [
    ['push', 'https://nowlert.example/#settings'],
  ]);
  assert.deepEqual(navigateContext('https://nowlert.example/?emailTab=groups#settings', 'settings'), [
    ['push', 'https://nowlert.example/#settings'],
  ]);
  assert.deepEqual(navigateContext('https://nowlert.example/?emailTab=groups#dashboard', 'email-alerts'), [
    ['push', 'https://nowlert.example/?emailTab=groups#email-alerts'],
  ]);
});

test('creating a user closes the dialog before the confirmation toast', async () => {
  const events = [];
  const values = {'user-name': ' new-user ', 'user-password': 'long enough password', 'user-role': 'user'};
  const form = {dataset: {mode: 'create'}};
  const context = {
    byId: id => (id === 'user-form' ? form : id === 'user-dialog' ? {close: () => events.push('close')} : {value: values[id]}),
    clearError() {},
    showError(_id, error) { throw error; },
    request: async (path, options) => { events.push(['request', path, options.body.username]); return {}; },
    toast: message => events.push(['toast', message]),
    loadWorkspace: async () => events.push('reload'),
  };
  vm.runInNewContext(fn('app.js', 'saveUser'), context);
  await context.saveUser({preventDefault() {}});
  assert.deepEqual(events, [
    ['request', '/users', 'new-user'],
    'close',
    ['toast', 'User new-user created.'],
    'reload',
  ]);
});

test('the Email Alerts cards count the enabled rules of each classification', () => {
  const context = {};
  vm.runInNewContext(`${fn('email_alerts.js', 'emailEnabledRuleCounts')}\n${fn('email_alerts.js', 'emailEnabledRuleCaption')}`, context);
  const counts = context.emailEnabledRuleCounts([
    {classification: 'warning', enabled: true},
    {classification: 'warning', enabled: false},
    {classification: 'urgent', enabled: true},
    {classification: 'urgent', enabled: true},
  ]);
  assert.equal(JSON.stringify(counts), JSON.stringify({warning: 1, urgent: 2}));
  assert.equal(context.emailEnabledRuleCaption(1), 'enabled rule');
  assert.equal(context.emailEnabledRuleCaption(0), 'enabled rules');
});

test('Remove is offered only when the account has a profile picture', () => {
  const remove = {hidden: false};
  const avatar = {classList: {contains: () => true}, replaceWith() {}};
  const context = {
    byId: () => avatar,
    element: () => ({}),
    initials: () => "N",
    document: {querySelector: () => remove},
  };
  vm.runInNewContext(`${fn('app.js', 'avatarElement')}\n${fn('app.js', 'applyAvatar')}`, context);
  context.applyAvatar('account-avatar', {username: 'nowlert-admin'});
  assert.equal(remove.hidden, true);
  context.applyAvatar('account-avatar', {username: 'nowlert-admin', avatar_data: 'data:image/png;base64,AA=='});
  assert.equal(remove.hidden, false);
});

test('the new token dialog does not repeat the word token', () => {
  const nodes = {'secret-title': {}, 'secret-value': {}, 'secret-dialog': {showModal() {}}};
  const context = {byId: id => nodes[id]};
  vm.runInNewContext(fn('app.js', 'revealSecret'), context);
  context.revealSecret('value', 'Grafana token');
  assert.equal(nodes['secret-title'].textContent, 'Event API token: Grafana token');
});
