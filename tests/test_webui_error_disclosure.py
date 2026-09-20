"""Regression tests for safe Web UI error rendering."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_show_error_never_renders_server_details_but_keeps_local_validation():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    api_error = app[app.index("class APIError"):app.index("async function request(")]
    renderers = app[app.index("function showError("):app.index("function clearError(")]
    program = f"""
const assert = require("node:assert/strict");
const API = "/api/v2";
const elements = new Map();
function byId(id) {{
  if (!elements.has(id)) elements.set(id, {{textContent: "", hidden: true}});
  return elements.get(id);
}}
{api_error}
{renderers}

const serverError = new APIError(
  500,
  "database connection failed for admin:secret@db.internal",
  "/private/users/42",
  "database_error",
  "internal-reference-123",
);
serverError.stack = "Error: database failure\\n    at /srv/nowlert/database.js:42:7";
showError("server-error", serverError);

const rendered = byId("server-error").textContent;
assert.equal(rendered, "The request could not be completed.");
for (const secret of [
  serverError.message,
  serverError.stack,
  serverError.path,
  serverError.reference,
  "admin:secret@db.internal",
  "/srv/nowlert/database.js:42:7",
]) {{
  assert.equal(rendered.includes(secret), false);
}}

showValidationError("validation-error", "The passwords do not match.");
assert.equal(byId("validation-error").textContent, "The passwords do not match.");
"""
    subprocess.run(["node", "-e", program], cwd=ROOT, check=True)

    assert "error.message" not in renderers
    assert "error.stack" not in renderers
