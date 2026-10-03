"""Email editors stay modal without occupying the browser top layer."""
from pathlib import Path
import subprocess


def test_email_editor_preserves_escape_focus_and_background_isolation():
    source = (Path(__file__).resolve().parents[1] / 'src/webui/email_alerts.js').read_text(encoding='utf-8')
    assert 'function emailShowEditor(' in source
    helper = source[source.index('function emailShowEditor('):source.index('\nfunction emailEnsureDialogs(')]
    program = r'''
const assert = require('node:assert/strict');
const handlers = {};
let restored = false;
const opener = {isConnected: true, focus() {restored = true;}};
const shell = {inert: false};
const reauth = {hidden: true};
const document = {activeElement: opener, body: {append(node) {this.overlay = node;}}};
const byId = (id) => id === 'app-shell' ? shell : reauth;
const element = () => ({hidden: true, append(node) {this.child = node;}});
const first = {getClientRects() {return [1];}, focus() {document.activeElement = this;}};
const last = {getClientRects() {return [1];}, focus() {document.activeElement = this;}};
const dialog = {
  show() {this.open = true;},
  showModal() {throw Error('Native modal would trigger Bitwarden conflict');},
  close() {this.open = false; handlers.close();},
  setAttribute() {},
  addEventListener(event, callback) {handlers[event] = callback;},
  querySelectorAll() {return [first, last];},
};
''' + helper + r'''
emailShowEditor(dialog);
assert.equal(dialog.open, true);
assert.equal(shell.inert, true);
assert.equal(document.body.overlay.hidden, false);
let prevented = false;
document.activeElement = last;
handlers.keydown({key: 'Tab', shiftKey: false, preventDefault() {prevented = true;}});
assert.equal(prevented, true);
assert.equal(document.activeElement, first);
handlers.keydown({key: 'Escape', preventDefault() {}});
assert.equal(dialog.open, false);
assert.equal(shell.inert, false);
assert.equal(document.body.overlay.hidden, true);
assert.equal(restored, true);
emailShowEditor(dialog);
assert.equal(dialog.open, true);
dialog.close();
assert.equal(shell.inert, false);
emailShowEditor(dialog);
reauth.hidden = false;
restored = false;
dialog.close();
assert.equal(shell.inert, true);
assert.equal(restored, false);
'''
    result = subprocess.run(['node', '-e', program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_reauthentication_keeps_open_email_editor_isolated():
    root = Path(__file__).resolve().parents[1]
    app = (root / 'src/webui/app.js').read_text(encoding='utf-8')
    helper = app[app.index('function finishReauthentication('):app.index('\nasync function submitReauthentication(')]
    program = r'''
const assert = require('node:assert/strict');
let editorOpen = true;
const shell = {inert: true, removeAttribute() {this.inert = false;}};
const dialog = {hidden: false};
const byId = (id) => id === 'app-shell' ? shell : dialog;
const document = {querySelector() {return editorOpen ? {} : null;}, body: {classList: {remove() {}}}};
let reauthResolve, reauthPromise, reauthUserId;
''' + helper + r'''
finishReauthentication(true);
assert.equal(shell.inert, true);
assert.equal(dialog.hidden, true);
editorOpen = false;
finishReauthentication(true);
assert.equal(shell.inert, false);
'''
    result = subprocess.run(['node', '-e', program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
