from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _function(script: str, signature: str) -> str:
    start = script.index(signature)
    next_async = script.find("\nasync function ", start + len(signature))
    next_plain = script.find("\nfunction ", start + len(signature))
    candidates = [value for value in (next_async, next_plain) if value >= 0]
    end = min(candidates) if candidates else len(script)
    return script[start:end]


def _round18_styles() -> str:
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 round-18 acceptance corrections. */"
    assert marker in styles
    return styles[styles.index(marker):]


def test_round18_login_owl_scales_visible_artwork_not_only_canvas():
    final = _round18_styles()

    assert "#login-view .login-reference-owl {" in final
    assert "height: 154px !important;" in final
    assert "width: 154px !important;" in final
    assert "#login-view .login-reference-owl img {" in final
    assert "height: 150px !important;" in final
    assert "transform: scale(1.65);" in final
    assert "width: 150px !important;" in final


def test_round18_invalid_portable_document_still_opens_preview_dialog():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    preview = _function(app, "async function previewImport(")

    assert '"/portability/preview"' in preview
    assert "portable && !response.preview.valid" not in preview
    assert "selectedInput.value = \"\"" not in preview
    assert 'byId("import-result").textContent = JSON.stringify(response.preview, null, 2);' in preview
    assert 'byId("import-apply").disabled = !response.preview.valid;' in preview
    assert 'byId("import-dialog").showModal();' in preview
    assert "Preview completed." in preview


def test_round18_data_tools_is_full_width_and_matches_reference_scale():
    final = _round18_styles()

    assert ".backup-dashboard-grid-top {" in final
    assert "grid-template-columns: minmax(0, 1fr) !important;" in final
    assert "#backup-schedule-panel," in final
    assert "#backup-data-tools-panel {" in final
    assert "grid-column: 1 / -1 !important;" in final
    assert "min-height: 470px;" in final
    assert "font-size: 32px !important;" in final
    assert "font-size: 25px !important;" in final
    assert "font-size: 18px !important;" in final
    assert "height: 92px !important;" in final
    assert "min-height: 68px !important;" in final


def test_round18_hidden_admin_navigation_wins_over_grid_important_rule():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    final = _round18_styles()

    assert 'id="audit-nav" class="nav-item" type="button" data-view="audit" hidden' in markup
    assert 'id="backups-nav" class="nav-item" type="button" data-view="backups" hidden' in markup
    assert 'id="users-nav" class="nav-item" type="button" data-view="users" hidden' in markup
    assert 'id="settings-nav" class="nav-item" type="button" data-view="settings">' in markup

    assert "#primary-nav .nav-item[hidden] {" in final
    assert "display: none !important;" in final


def test_round18_workspace_scrolls_without_moving_sidebar_or_topbar():
    final = _round18_styles()

    assert "#app-shell.app-shell {" in final
    assert "height: 100dvh !important;" in final
    assert "overflow: hidden !important;" in final
    assert "#app-shell .workspace {" in final
    assert "overflow-y: auto !important;" in final
    assert "#app-shell .sidebar {" in final
    assert "position: sticky !important;" in final
    assert "height: calc(100dvh - 28px) !important;" in final
    assert "#app-shell .topbar {" in final
    assert "position: sticky !important;" in final
    assert "z-index: 80 !important;" in final
