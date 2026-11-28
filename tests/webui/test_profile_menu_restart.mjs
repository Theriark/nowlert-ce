import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Restart Nowlert is one admin-only item in the profile
// (user icon) menu. It opens the existing restart confirmation dialog through
// the app.js click dispatcher, closes the menu on selection, and the Security
// page carries no restart control of its own, visible or hidden.
const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function functionSource(file, name, indent = '') {
  const source = read(file);
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists in ${file}`);
  const end = source.indexOf(`\n${indent}}`, start);
  return source.slice(source.slice(start - 6, start) === 'async ' ? start - 6 : start, end + indent.length + 2);
}

function fakeButton(id, dataset = {}) {
  const listeners = [];
  return {
    id, dataset: {...dataset}, hidden: true, listeners,
    closest(selector) { return selector === 'button' ? this : null; },
    addEventListener(type, listener) { listeners.push({type, listener}); },
    click(event = {target: this}) { for (const entry of listeners) if (entry.type === 'click') entry.listener(event); return event; },
  };
}

function profileMenuContext(role) {
  const restart = fakeButton('platform-restart', {action: 'restart-platform'});
  const popover = {hidden: false};
  const chip = {attributes: {}, setAttribute(name, value) { this.attributes[name] = value; }};
  const dialog = {opened: 0, showModal() { this.opened += 1; }};
  const form = {resets: 0, reset() { this.resets += 1; }};
  const nodes = {
    'platform-restart': restart,
    'profile-menu-popover': popover,
    'profile-menu-button': chip,
    'restart-dialog': dialog,
    'restart-form': form,
    'platform-menu': {hidden: true},
  };
  const context = {
    state: {user: {id: 'qa', role}},
    byId: id => nodes[id] || null,
    installHeaderMenu() {},
    clearError() {},
    updateRestartDialogContext() {},
    navigate() { throw new Error('restart must not navigate'); },
  };
  vm.runInNewContext(`${functionSource('app.js', 'isAdmin')}\n${functionSource('app.js', 'closeProfileMenu')}\n${functionSource('app.js', 'handleClick')}\n${functionSource('app.js', 'resourceAction')}\n${functionSource('enhancements.js', 'installProfileRestart', '  ')}\n${functionSource('enhancements.js', 'syncHeaderMenu', '  ')}`, context);
  return {context, restart, popover, chip, dialog, form};
}

test('the profile menu shows Restart Nowlert to administrators only', () => {
  const admin = profileMenuContext('admin');
  admin.context.syncHeaderMenu();
  assert.equal(admin.restart.hidden, false);

  const user = profileMenuContext('user');
  user.context.syncHeaderMenu();
  assert.equal(user.restart.hidden, true);
});

test('selecting Restart Nowlert closes the profile menu and opens the restart dialog', async () => {
  const {context, restart, popover, chip, dialog, form} = profileMenuContext('admin');
  context.syncHeaderMenu();
  // The item's own listener (enhancements.js) runs before the document-level
  // app.js dispatcher, exactly as the browser orders target and bubble phase.
  const event = restart.click();
  await context.handleClick(event);
  assert.equal(popover.hidden, true);
  assert.equal(chip.attributes['aria-expanded'], 'false');
  assert.equal(form.resets, 1);
  assert.equal(dialog.opened, 1);
});

test('the restart binding is installed once even when the menu is synced repeatedly', () => {
  const {context, restart} = profileMenuContext('admin');
  context.syncHeaderMenu();
  context.syncHeaderMenu();
  context.installProfileRestart();
  assert.equal(restart.listeners.length, 1);
});

test('the Security page has no restart control and the menu item is the only one', () => {
  const markup = read('index.html');
  const popover = markup.slice(markup.indexOf('id="profile-menu-popover"'), markup.indexOf('</div>', markup.indexOf('id="profile-menu-popover"')));
  assert.match(popover, /id="platform-restart"[^>]*role="menuitem"[^>]*data-action="restart-platform"[^>]*hidden/);
  assert.ok(popover.includes('Restart Nowlert'));
  assert.ok(popover.indexOf('data-view="account"') < popover.indexOf('id="platform-restart"'));
  assert.ok(popover.indexOf('id="platform-restart"') < popover.indexOf('data-action="logout"'));

  const accountStart = markup.indexOf('<section id="view-account"');
  const account = markup.slice(accountStart, markup.indexOf('</section>', accountStart));
  for (const marker of ['restart-platform', 'platform-restart', 'Restart Nowlert', 'restart-header-button']) {
    assert.ok(!account.includes(marker), `Security view must not contain ${marker}`);
  }
  assert.equal(markup.split('data-action="restart-platform"').length - 1, 1);
  assert.ok(!markup.includes('restart-header-button'));

  // No script re-creates a second restart control or parks one in the Security toolbar.
  const enhancements = read('enhancements.js');
  assert.ok(!enhancements.includes('restartButton.id = "platform-restart"'));
  const cleanup = read('acceptance_cleanup.js');
  assert.ok(!cleanup.includes('platform-restart'));
  assert.ok(!cleanup.includes('#view-account .section-toolbar'));
});
