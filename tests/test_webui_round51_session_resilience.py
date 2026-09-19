"""Round-51 regressions for resilient browser sessions and warm re-authentication."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_session_defaults_and_api_surface_idle_expiry():
    sessions = read("src/storage/sessions.py")
    platform = read("src/api/platform.py")

    assert "absolute_ttl_seconds: int = 24 * 60 * 60" in sessions
    assert "idle_ttl_seconds: int = 2 * 60 * 60" in sessions
    assert "idle_expires_at: int" in sessions
    assert "idle_expires_at=idle_expires_at" in sessions

    assert '"idle_expires_at": credentials.idle_expires_at' in platform
    assert '"idle_expires_at": principal.idle_expires_at' in platform
    assert 'touch=(path == "/api/v2/session" or method not in _SAFE_METHODS)' in platform
    assert "def _session(self, headers, *, require_csrf, touch=False):" in platform
    assert "touch=touch" in platform


def test_webui_reauthenticates_in_place_and_retries_pending_request():
    app = read("src/webui/app.js")

    request_start = app.index("async function request(path, options = {})")
    request_end = app.index("function showError(", request_start)
    request_block = app[request_start:request_end]
    assert "await requireReauthentication()" in request_block
    assert "return request(path, { ...options, _reauthRetry: true });" in request_block
    assert 'options.reauthenticate !== false' in request_block
    assert 'path !== "/session"' in request_block
    assert "expireSession()" not in request_block

    assert "function requireReauthentication(" in app
    assert "function submitReauthentication(" in app
    assert 'String(session.user?.id || "") !== String(expectedUserId || "")' in app
    assert 'className: "modal small-modal session-reauth-modal"' in app
    assert 'text: "Your work is still here. Sign in again to continue."' in app
    assert 'text: "Stay signed in"' in app
    assert "SESSION_IDLE_WARNING_MS = 5 * 60 * 1000" in app
    assert "SESSION_KEEPALIVE_MIN_INTERVAL_MS = 5 * 60 * 1000" in app
    assert 'for (const eventName of ["pointerdown", "keydown", "input"])' in app
    assert "void refreshSession();" in app


def test_timeout_preserves_display_cache_but_explicit_signout_purges_it():
    app = read("src/webui/app.js")
    qa = read("src/webui/qa_patch.js")
    dashboard = read("src/webui/operations_dashboard.js")
    routing = read("src/webui/routing_flow.js")
    filtering = read("src/webui/filtering.js")

    assert "expireSession({ preserveCache: error instanceof APIError && error.status === 401 });" in app
    assert "expireSession({ preserveCache: false });" in app

    assert "if (options.preserveCache !== true) qaClearWorkspaceCache();" in qa
    assert "if (options.preserveCache !== true) clearDashboardSnapshots(state.user);" in dashboard
    assert "if (options.preserveCache !== true) state.routingFlowSnapshots = {};" in routing
    assert "if (options.preserveCache !== true) state.filteringOverview = null;" in filtering

    assert "if(response.status===401){expireSession();return;}" not in routing
    assert "await requireReauthentication()" in routing


def test_session_warning_and_reauth_have_dedicated_visual_contract():
    styles = read("src/webui/styles.css")

    assert ".session-warning {" in styles
    assert ".session-warning[hidden]" in styles
    assert ".session-reauth-modal {" in styles
    assert ".session-reauth-copy {" in styles
