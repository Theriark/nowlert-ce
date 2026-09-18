from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_round11_restores_requested_view_before_authenticated_shell_is_visible():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    show_start = app.index("function showApp(session)")
    show_end = app.index("async function restoreSession", show_start)
    show = app[show_start:show_end]
    assert "navigate(requestedAppView(), \"replace\");" in show
    assert show.index('navigate(requestedAppView(), "replace");') < show.index(
        'byId("app-shell").hidden = false;'
    )

    workspace_start = app.index("async function loadWorkspace()")
    workspace_end = app.index("function renderAll()", workspace_start)
    workspace = app[workspace_start:workspace_end]
    assert "const requestedView = requestedAppView();" in workspace
    assert "if (state.currentView !== requestedView)" in workspace


def test_round11_sidebar_is_larger_and_collapses_with_real_transitions():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    start = styles.index("/* 2026-09-18 sidebar reference lock.")
    end = styles.index("/* NCE-35 final unified pagination row */", start)
    sidebar = styles[start:end]

    assert "font-size: 14px !important;" in sidebar
    assert "height: 92px !important;" in sidebar
    assert "width: 92px !important;" in sidebar
    assert "height: 24px !important;" in sidebar
    assert "width: 24px !important;" in sidebar
    assert "font-size: 12px !important;" in sidebar
    assert "grid-template-columns 240ms" not in sidebar
    assert "will-change: width, opacity, transform;" in sidebar

    collapsed_label = sidebar[
        sidebar.index(".app-shell.sidebar-collapsed .nav-label"):
        sidebar.index(".app-shell.sidebar-collapsed .profile-chip")
    ]
    assert "display: block !important;" in collapsed_label
    assert "max-width: 145px !important;" in collapsed_label
    assert "opacity: 0 !important;" in collapsed_label
    assert "display: none !important;" not in collapsed_label


def test_round11_housekeeping_data_tools_and_external_restore_are_present():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    platform = (ROOT / "src" / "api" / "platform.py").read_text(encoding="utf-8")

    assert 'id="housekeeping-form"' in markup
    assert 'id="housekeeping-delivery-days"' in markup
    assert 'data-action="run-housekeeping"' not in markup
    assert "destination filtering policies" in markup
    assert 'id="external-backup-list"' in markup
    assert 'data-action="create-remote-backup"' in markup
    assert 'data-action="refresh-external-backups"' not in markup

    assert 'request("/housekeeping")' in app
    assert 'request("/housekeeping/run"' not in app
    assert "async function loadExternalBackups" in app
    assert "async function restoreExternalBackup" in app
    assert "/backup-targets/${targetId}/backups/${backupId}/restore" in app

    assert 'if path == "/api/v2/housekeeping":' in platform
    assert 'if path == "/api/v2/housekeeping/run":' not in platform
    assert 'r"/api/v2/backup-targets/([0-9a-f]{32})/backups/"' in platform
    assert "self.backups.restore_external(" in platform
