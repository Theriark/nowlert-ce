from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _function(script: str, signature: str) -> str:
    start = script.index(signature)
    next_async = script.find("\nasync function ", start + len(signature))
    next_plain = script.find("\nfunction ", start + len(signature))
    candidates = [value for value in (next_async, next_plain) if value >= 0]
    end = min(candidates) if candidates else len(script)
    return script[start:end]


def test_round16_login_matches_requested_reference_surface():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    assert 'id="login-reference-card"' in markup
    assert 'class="login-reference-tagline"' in markup
    assert ">MONITOR</span>" in markup
    assert ">MANAGE</span>" in markup
    assert ">STAY AHEAD</span>" in markup
    assert 'placeholder="Enter your username"' in markup
    assert 'placeholder="Enter your password"' in markup
    assert 'id="login-remember"' in markup
    assert 'id="login-password-toggle"' in markup
    assert "Secure access to your infrastructure" in markup
    assert 'class="button primary full login-reference-submit"' in markup

    assert "function toggleLoginPasswordVisibility()" in app
    assert 'byId("login-password-toggle")?.addEventListener("click", toggleLoginPasswordVisibility);' in app
    toggle = _function(app, "function toggleLoginPasswordVisibility()")
    assert 'input.type = visible ? "text" : "password";' in toggle
    assert 'button.classList.toggle("is-visible", visible);' in toggle

    marker = "/* 2026-09-18 reference login page and round-16 follow-up. */"
    assert marker in styles
    final = styles[styles.index(marker):]
    assert "#login-view.login-reference" in final
    assert "background-size: 52px 52px;" in final
    assert "width: min(570px, calc(100vw - 48px));" in final
    assert "min-height: 668px;" in final
    assert "#login-view .login-input-shell" in final
    assert "#login-view .login-reference-submit" in final
    assert "linear-gradient(180deg, #ffd03a, #ffbd16)" in final


def test_round16_backup_first_paint_keeps_session_snapshot_and_never_claims_disabled_while_loading():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    assert "QA_WORKSPACE_CACHE_TTL_MS" not in patch
    hydrate = _function(patch, "function qaHydrateWorkspaceCache(")
    assert "Date.now() - Number(cached.saved_at)" not in hydrate
    assert "window.sessionStorage.getItem(" in hydrate
    assert 'id="backup-summary-schedule-note">Loading…</small>' in markup
    assert 'id="backup-time-display">Next run: Loading…</small>' in markup


def test_round16_backup_data_tools_fill_panel_height_and_file_picker_fills_import_card():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 reference login page and round-16 follow-up. */"
    final = styles[styles.index(marker):]

    assert "#backup-data-tools-panel {" in final
    assert "display: flex;" in final
    assert "flex-direction: column;" in final
    assert "#backup-data-tools-panel > .backup-data-tools-grid {" in final
    assert "flex: 1 1 auto;" in final
    assert "#backup-data-tools-panel .backup-tool-box {" in final
    assert "height: 100%;" in final
    assert "#backup-data-tools-panel .backup-tool-box .file-field {" in final
    assert "min-height: 72px;" in final
    assert 'input[type="file"]::file-selector-button' in final
    assert "min-height: 58px;" in final


def test_round16_housekeeping_main_status_uses_check_and_pause_icons():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert 'id="housekeeping-status-icon"' in markup
    assert "M5 12l4 4L19 6" in markup
    assert 'pause: ["M9 6v12", "M15 6v12"]' in app

    render = _function(app, "function renderHousekeepingSettings()")
    assert 'backupSvgIcon(enabled ? "check" : "pause", "housekeeping-symbol")' in render
    assert 'backupSvgIcon("broom", "housekeeping-symbol")' not in render
