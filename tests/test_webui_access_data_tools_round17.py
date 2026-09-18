from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _function(script: str, signature: str) -> str:
    start = script.index(signature)
    next_async = script.find("\nasync function ", start + len(signature))
    next_plain = script.find("\nfunction ", start + len(signature))
    candidates = [value for value in (next_async, next_plain) if value >= 0]
    end = min(candidates) if candidates else len(script)
    return script[start:end]


def test_round17_normal_user_navigation_hides_admin_pages_but_keeps_settings():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    shell = (ROOT / "src" / "webui" / "source_ui_retirement.js").read_text(encoding="utf-8")

    assert 'id="audit-nav" class="nav-item" type="button" data-view="audit" hidden' in markup
    assert 'id="backups-nav" class="nav-item" type="button" data-view="backups" hidden' in markup
    assert 'id="users-nav" class="nav-item" type="button" data-view="users" hidden' in markup
    assert 'id="settings-nav" class="nav-item" type="button" data-view="settings">' in markup

    requested = _function(app, "function requestedAppView()")
    navigate = _function(app, "function navigate(")
    for source in (requested, navigate):
        assert '"audit"' in source
        assert '"users"' in source
        assert '"backups"' in source
        assert '"settings"' not in source

    assert 'byId("audit-nav").hidden = !isAdmin();' in app
    assert 'byId("settings-nav").hidden = false;' in app

    admin_views = shell[shell.index("const ADMIN_ONLY_VIEWS"):shell.index("]);", shell.index("const ADMIN_ONLY_VIEWS"))]
    assert '"audit"' in admin_views
    assert '"backups"' in admin_views
    assert '"users"' in admin_views
    assert '"settings"' not in admin_views
    assert shell.count("if (settingsNav) settingsNav.hidden = false;") == 2
    assert 'if (settingsUpdates) settingsUpdates.hidden = !admin;' in shell
    assert 'if (housekeeping) housekeeping.hidden = !admin;' in shell


def test_round17_data_tools_matches_reference_and_has_explicit_json_preview():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    assert 'id="backup-data-tools-panel" class="panel backup-dashboard-panel data-tools-reference-panel"' in markup
    assert "Export user configuration" in markup
    assert "Import user configuration" in markup
    assert "Download safe JSON" in markup
    assert 'id="backup-portable-file"' in markup
    assert 'data-action="preview-backup-portable-import"' in markup
    assert "Preview JSON import" in markup

    assert 'action === "preview-backup-portable-import"' in app
    assert 'await previewImport("portable", "backup-portable-file");' in app
    bind = _function(app, "function bindEvents()")
    assert 'portableInput?.addEventListener("change"' not in bind

    marker = "/* 2026-09-18 round-17 user navigation and Data tools reference. */"
    assert marker in styles
    final = styles[styles.index(marker):]
    assert "#backup-data-tools-panel.data-tools-reference-panel" in final
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in final
    assert ".data-tools-reference-preview" in final
    assert 'input[type="file"]::file-selector-button' in final


def test_round17_login_owl_is_larger_than_round16_reference():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 round-17 user navigation and Data tools reference. */"
    final = styles[styles.index(marker):]

    assert "#login-view .login-reference-owl {" in final
    assert "height: 132px;" in final
    assert "width: 132px;" in final
    assert "#login-view .login-reference-owl img {" in final
    assert "height: 128px;" in final
    assert "width: 128px;" in final
