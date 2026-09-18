from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_housekeeping_ui_is_scheduled_only_and_uses_recommended_selects():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert '<select id="housekeeping-enabled">' in markup
    assert '<option value="true">Enabled</option>' in markup
    assert '<option value="false">Disabled</option>' in markup
    assert '<select id="housekeeping-time"' in markup
    assert 'type="time"' not in markup[markup.index('id="housekeeping-form"'):markup.index("</form>", markup.index('id="housekeeping-form"'))]
    assert '<select id="housekeeping-delivery-days">' in markup
    assert '<select id="housekeeping-audit-days">' in markup
    assert '<select id="housekeeping-backup-run-days">' in markup
    assert 'value="0">Keep forever</option>' in markup
    assert 'data-action="run-housekeeping"' not in markup
    assert "async function runHousekeepingNow" not in app
    assert 'action === "run-housekeeping"' not in app
    assert 'request("/housekeeping/run"' not in app
    assert "function renderHousekeepingTimeOptions()" in app
    assert 'state.preferences.time_format === "12"' in app


def test_backups_page_matches_management_dashboard_reference_structure():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    for identifier in (
        "backup-overview-strip",
        "backup-summary-destinations",
        "backup-summary-snapshots",
        "backup-summary-schedule",
        "backup-summary-health",
        "backup-last-backup",
        "backup-system-status",
        "backup-destinations-panel",
        "backup-schedule-panel",
        "backup-data-tools-panel",
        "backup-recovery-panel",
        "backup-stored-panel",
        "backup-recovery-table",
        "backup-stored-table",
        "backup-portable-file",
    ):
        assert f'id="{identifier}"' in markup

    assert "<th>Last test</th>" in markup
    assert 'data-action="view-all-backups"' in markup
    assert 'data-action="view-all-stored-backups"' in markup
    assert 'data-action="preview-backup-portable"' in markup

    assert "function renderBackupOverview()" in app
    assert "function renderBackupRecoveryTable()" in app
    assert "function renderStoredBackupTable()" in app
    assert "function backupScheduleSummary()" in app
    assert "function backupSystemHealth()" in app
    assert "state.showAllBackups" in app
    assert "state.showAllStoredBackups" in app


def test_sidebar_expansion_avoids_non_interpolable_grid_layout_transition():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    start = styles.index("/* 2026-09-18 sidebar reference lock.")
    end = styles.index("/* NCE-35 final unified pagination row */", start)
    sidebar = styles[start:end]

    assert "grid-template-columns 240ms" not in sidebar
    assert "grid-template-columns: 24px minmax(0, 1fr) !important;" in sidebar
    assert "contain: layout paint;" in sidebar
    assert "will-change: width, opacity, transform;" in sidebar
