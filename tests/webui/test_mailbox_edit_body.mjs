import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../src/webui/email_alerts.js', import.meta.url), 'utf8');
const start = source.indexOf('function emailMailboxEditBody(');
assert.notEqual(start, -1, 'emailMailboxEditBody exists');
const sandboxed = vm.runInNewContext(`${source.slice(start, source.indexOf('\n}', start) + 2)}\nemailMailboxEditBody;`);
// Round-trip through JSON so results from the vm realm compare structurally.
const editBody = (args) => JSON.parse(JSON.stringify(sandboxed(args)));

const original = {folder: 'INBOX', username: 'alerts@example.com', host: 'imap.example.com', port: '993', security: 'ssl'};
const current = {
  name: 'Alerts', shared: false, folder: '', host: 'imap.example.com', port: 993,
  security: 'ssl', username: 'alerts@example.com', password: '',
};
const build = (overrides, provider = 'imap') => editBody({
  provider, original, current: {...current, ...overrides}, ownerCanShare: true,
});

test('IMAP edit without connection changes sends only name and visibility, even without a folder scan', () => {
  assert.deepEqual(build({name: 'Renamed'}), {name: 'Renamed', shared: false});
  assert.deepEqual(build({folder: 'inbox'}), {name: 'Alerts', shared: false});
});

test('IMAP edit with a blank username keeps the stored username', () => {
  assert.deepEqual(build({username: ''}), {name: 'Alerts', shared: false});
});

test('changed IMAP host, port, security, folder, username or password is sent for server verification', () => {
  for (const change of [{host: 'other.example.com'}, {port: 143}, {security: 'starttls'}, {folder: 'Alerts'}]) {
    const body = build(change);
    assert.equal(body.settings.host, change.host || 'imap.example.com');
    assert.equal(body.settings.folder, change.folder || 'INBOX');
    assert.equal(body.credential, undefined);
  }
  assert.deepEqual(build({password: 'new'}).credential, {username: 'alerts@example.com', password: 'new'});
  assert.deepEqual(build({username: 'new@example.com'}).credential, {username: 'new@example.com'});
  assert.ok(build({password: 'new'}).settings);
});

test('non-owner edits never send visibility and OAuth mailboxes only send a changed folder', () => {
  assert.deepEqual(editBody({provider: 'imap', original, current, ownerCanShare: false}), {name: 'Alerts'});
  assert.deepEqual(build({}, 'gmail'), {name: 'Alerts', shared: false});
  assert.deepEqual(build({folder: 'Label_1'}, 'gmail').settings, {label: 'Label_1'});
  assert.deepEqual(build({folder: 'f1'}, 'microsoft_365').settings, {folder: 'f1'});
});
