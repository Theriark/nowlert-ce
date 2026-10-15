"""Recovery credentials remain usable in the UI and never survive its dialog."""
from pathlib import Path
import subprocess
import json


ROOT = Path(__file__).resolve().parents[1]


def test_mfa_ui_displays_codes_then_clears_credentials_and_rejects_late_results():
    source = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    helpers = source[source.index("function mfaDigitInputs()"):
                     source.index("async function bootstrapAdministrator(")]
    expiry = source[source.index("function expireSession("):
                    source.index("function showBootstrap(")]
    program = r'''
const assert = require('node:assert/strict');
const nodes = new Map();
const byId = id => {
  if (!nodes.has(id)) nodes.set(id, {
    value: '', textContent: '', hidden: false, open: true,
    classList: {remove() {}, toggle() {}},
    focus() {}, setAttribute() {}, removeAttribute(name) {delete this[name];},
    close() {this.open = false;}, showModal() {this.open = true;},
  });
  return nodes.get(id);
};
const digits = Array.from({length: 6}, () => ({value: '1'}));
const document = {querySelectorAll: () => digits, dispatchEvent() {}};
const state = {user: {id: 'owner', mfa_enabled: false}};
const window = {clearTimeout() {}};
let sessionActivityTimer = null;
let reauthPromise = null;
const Event = class {};
const clearError = () => {};
const toast = () => {};
const showError = (_id, error) => {throw error;};
const showValidationError = (_id, error) => {throw new Error(error);};
const codes = ['abcd-1234-abcd-1234-abcd-1234-abcd-1234'];
let lastRequest;
let request = async (path, options) => {
  lastRequest = {path, ...options};
  return {user: {id: 'owner', mfa_enabled: true}, recovery_codes: codes};
};
''' + helpers + expiry + r'''
(async () => {
  const event = {preventDefault() {}, submitter: {disabled: false}};
  await confirmMfaSetup(event);
  assert.equal(byId('mfa-dialog').open, true, 'Enrollment must show codes before closing');
  assert.equal(byId('mfa-recovery-panel').hidden, false);
  assert.equal(byId('mfa-recovery-codes').value, codes.join('\n'));
  assert.equal(byId('mfa-setup-panel').hidden, true);
  byId('mfa-disable-password').value = 'password';
  byId('mfa-disable-code').value = '111111';
  byId('mfa-recovery-password').value = 'password';
  byId('mfa-recovery-code').value = '111111';
  closeMfaDialog();
  assert.equal(byId('mfa-recovery-codes').value, '');
  assert.equal(byId('mfa-recovery-password').value, '');
  assert.equal(byId('mfa-disable-password').value, '');
  assert.equal(byId('mfa-secret-value').textContent, '');
  byId('mfa-dialog').open = true;
  byId('mfa-recovery-password').value = 'password';
  byId('mfa-recovery-code').value = '123456';
  await regenerateMfaRecoveryCodes(event);
  assert.equal(lastRequest.path, '/account/mfa/recovery-codes');
  assert.deepEqual(lastRequest.body, {password: 'password', code: '123456'});
  assert.equal(byId('mfa-recovery-password').value, '');
  assert.equal(byId('mfa-recovery-codes').value, codes.join('\n'));
  let resolve;
  request = () => new Promise(done => {resolve = done;});
  const pending = regenerateMfaRecoveryCodes(event);
  closeMfaDialog();
  resolve({user: {id: 'owner', mfa_enabled: true}, recovery_codes: codes});
  await pending;
  assert.equal(byId('mfa-recovery-codes').value, '', 'Late responses cannot restore secrets');
  assert.equal(byId('mfa-dialog').open, false);
  byId('mfa-dialog').open = true;
  byId('mfa-recovery-codes').value = codes.join('\n');
  expireSession({preserveCache: false});
  assert.equal(state.user, null);
  assert.equal(byId('mfa-recovery-codes').value, '', 'Sign-out must clear visible codes');
  assert.equal(byId('mfa-dialog').open, false);
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
    result = subprocess.run(["node", "-e", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_login_and_disable_fields_accept_authenticator_and_recovery_codes():
    from html.parser import HTMLParser

    class Inputs(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inputs = {}

        def handle_starttag(self, tag, attrs):
            if tag == "input":
                values = dict(attrs)
                self.inputs[values.get("id")] = values

    parser = Inputs()
    parser.feed((ROOT / "src/webui/index.html").read_text(encoding="utf-8"))
    program = r'''
const assert = require('node:assert/strict');
const fields = ''' + json.dumps([parser.inputs["login-otp"], parser.inputs["mfa-disable-code"]]) + r''';
for (const field of fields) {
  const pattern = new RegExp('^(?:' + field.pattern + ')$', 'u');
  assert.equal(pattern.test('123456'), true);
  assert.equal(pattern.test('abcd-1234-abcd-1234-abcd-1234-abcd-1234'), true);
  assert.equal(pattern.test('ABCD1234ABCD1234ABCD1234ABCD1234'), true);
  assert.equal(pattern.test('invalid-code'), false);
  assert.ok(Number(field.maxlength) >= 39);
  assert.notEqual(field.inputmode, 'numeric');
}
'''
    result = subprocess.run(["node", "-e", program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
