"""Exercise browser CSRF state without access to readable cookies."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_session_json_supplies_csrf_for_reload_refresh_and_reauthentication():
    app = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    assert "readCsrfCookie" not in app
    assert "document.cookie" not in app
    # Execute the real request/metadata/refresh functions with mocked browser I/O.
    blocks = [
        app[app.index("class APIError"):app.index("function showError(")],
        app[app.index("function applySessionMetadata("):app.index("function finishReauthentication(")],
        app[app.index("async function refreshSession("):app.index("function updateSessionWarning(")],
    ]
    program = r'''
const assert = require("node:assert/strict");
const API = "/api/v2";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const state = {csrf: "", user: null};
const calls = [];
const responses = [];
const document = {get cookie() {throw new Error("Cookie access is forbidden");}};
function renderSessionExpiryLabel() {}
function updateSessionWarning() {}
async function fetch(url, options) {
  calls.push({url, ...options});
  const {status = 200, payload = {}} = responses.shift();
  return {status, ok: status < 400, text: async () => JSON.stringify(payload)};
}
async function requireReauthentication() {
  applySessionMetadata({csrf_token: "reauthenticated-token", user: {id: "user"}});
  return true;
}
''' + "\n".join(blocks) + r'''
(async () => {
  // Both initial authentication flows supply their token through JSON.
  for (const path of ["/session", "/bootstrap"]) {
    state.csrf = "";
    responses.push({payload: {csrf_token: "initial-token", user: {id: "user"}}});
    applySessionMetadata(await request(path, {method: "POST", body: {}}));
    responses.push({});
    await request("/tokens", {method: "POST", body: {}});
    assert.equal(calls.at(-1).headers["X-CSRF-Token"], "initial-token");
  }
  // A page reload starts with no in-memory CSRF token; GET restores it.
  state.csrf = "";
  responses.push({payload: {
    csrf_token: "restored-token", user: {id: "user"},
    expires_at: 2000, idle_expires_at: 1000,
  }});
  applySessionMetadata(await request("/session"));
  assert.equal(calls.at(-1).headers["X-CSRF-Token"], undefined);
  assert.equal(state.csrf, "restored-token");
  responses.push({payload: {
    csrf_token: "restored-token", expires_at: 2000, idle_expires_at: 1500,
  }});
  assert.equal(await refreshSession(), true);
  assert.equal(state.sessionIdleExpiresAt, 1500);
  assert.equal(state.sessionExpiresAt, 2000);
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    responses.push({});
    await request("/tokens", {method});
    assert.equal(calls.at(-1).headers["X-CSRF-Token"], "restored-token");
    assert.equal(calls.at(-1).credentials, "same-origin");
    assert.equal(calls.at(-1).cache, "no-store");
  }
  // The existing warm reauthentication retry uses the replacement token.
  responses.push({status: 401}, {});
  await request("/tokens", {method: "POST"});
  assert.equal(calls.at(-1).headers["X-CSRF-Token"], "reauthenticated-token");
})().catch(error => {console.error(error); process.exitCode = 1;});
'''
    result = subprocess.run(
        ["node", "-e", program], cwd=ROOT, capture_output=True, text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
