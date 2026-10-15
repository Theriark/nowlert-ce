import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../src/webui/app.js', import.meta.url), 'utf8');
function functionSource(name) {
  const start = source.indexOf(`function ${name}(`);
  const end = source.indexOf('\n}', start);
  return source.slice(source.slice(start - 6, start) === 'async ' ? start - 6 : start, end + 2);
}

for (const type of ['nfs', 'smb']) {
  test(`editing a legacy ${type} destination retains its mounted path`, () => {
    const controls = new Map();
    const byId = id => {
      if (!controls.has(id)) controls.set(id, {reset() {}, showModal() {}});
      return controls.get(id);
    };
    const context = {byId, clearError() {}, state: {backupTargets: [
      {id: 'nas', type, name: 'Archive', enabled: true, local_path: '/nowlert/backup-mounts/nas'},
    ]}};
    vm.runInNewContext(`${functionSource('openBackupTarget')}\nopenBackupTarget('nas');`, context);
    assert.equal(byId('backup-target-local-path').value, '/nowlert/backup-mounts/nas');
  });
}

test('saving a host-mounted destination sends only its identity and mounted path', async () => {
  let saved, message;
  const values = {'backup-target-id': 'nas', 'backup-target-type': 'smb', 'backup-target-name': ' Archive ', 'backup-target-local-path': ' /nowlert/backup-mounts/nas '};
  const context = {
    byId: id => ({value: values[id] ?? '', checked: true, close() {}}), clearError() {},
    request: async (path, options) => { saved = {path, ...options}; },
    loadWorkspace: async () => {}, state: {}, toast: text => { message = text; },
    showError: (_id, error) => { throw error; },
  };
  vm.runInNewContext(functionSource('saveBackupTarget'), context);
  await context.saveBackupTarget({preventDefault() {}});
  assert.equal(saved.path, '/backup-targets/nas');
  assert.deepEqual(JSON.parse(JSON.stringify(saved.body)), {
    name: 'Archive', type: 'smb', local_path: '/nowlert/backup-mounts/nas', enabled: true,
  });
  assert.equal(message, 'Backup destination updated.');
});

test('destination table reports a missing host mount even after a successful test', () => {
  const rows = [];
  const context = {
    byId: () => ({replaceChildren() {}, append: item => rows.push(item)}),
    state: {backupTargets: [{id: 'nas', name: 'Archive', type: 'nfs', enabled: true, mounted: false, local_path: '/nowlert/backup-mounts/nas', last_test_outcome: 'success'}]},
    element: (tag, props = {}, children = []) => ({tag, ...props, children}),
    badge: (text, style) => ({text, style}), backupIconAction() {}, backupTargetLastTest() {}, renderBackupOverview() {},
  };
  vm.runInNewContext(`${functionSource('renderBackupTargets')}\nrenderBackupTargets();`, context);
  assert.equal(rows[0].children[3].children.text, '/nowlert/backup-mounts/nas');
  assert.equal(rows[0].children[4].children.text, 'Mount unavailable');
});
