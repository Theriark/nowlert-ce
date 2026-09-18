from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _panel(markup: str, panel_id: str) -> str:
    start = markup.index(f'id="{panel_id}"')
    article_start = markup.rfind("<article", 0, start)
    end = markup.index("</article>", start)
    return markup[article_start:end]


def test_backup_sections_have_one_title_only_and_reference_icons():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    for panel_id, title in (
        ("backup-destinations-panel", "Backup destinations"),
        ("backup-schedule-panel", "Scheduled backups"),
        ("backup-data-tools-panel", "Data tools"),
        ("backup-recovery-panel", "Recovery snapshots"),
        ("backup-stored-panel", "Stored copies"),
    ):
        panel = _panel(markup, panel_id)
        assert panel.count(f">{title}<") == 1
        heading = panel[:panel.index("</div>", panel.index("panel-heading")) + len("</div>")]
        assert 'class="eyebrow"' not in heading
        assert "<p>" not in heading
        assert 'class="backup-section-icon"' in heading

    assert 'id="backup-last-run-badge"' not in markup


def test_backup_reference_controls_and_tables_use_icons_and_fit_classes():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    for field_id in (
        "backup-schedule",
        "backup-weekday",
        "backup-time",
        "backup-day",
        "backup-target",
    ):
        field_at = markup.index(f'id="{field_id}"')
        field_block = markup[max(0, field_at - 350):field_at + 300]
        assert 'class="backup-field-icon"' in field_block

    assert 'class="backup-tool-icon"' in markup
    assert 'class="backup-action-icon"' in markup
    assert "backup-test-check" in app
    assert '"Edit", "edit-backup-target"' not in app
    assert '"Delete", "delete-backup-target"' not in app
    assert 'id="backup-view-all-status"' in markup
    assert 'id="backup-stored-view-all-status"' in markup

    assert "table-layout: fixed;" in styles
    assert ".backup-recovery-table" in styles
    assert ".backup-stored-table" in styles
    assert "overflow-x: clip;" in styles


def test_workspace_uses_available_width_and_expands_when_sidebar_collapses():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 wide workspace utilization. */"
    assert marker in styles
    final = styles[styles.index(marker):]

    assert ".content {" in final
    assert "max-width: none !important;" in final
    assert "margin: 0 !important;" in final
    assert "width: 100% !important;" in final
    assert "box-sizing: border-box !important;" in final
    assert ".app-shell.sidebar-collapsed .workspace" in final
    assert "min-width: 0;" in final
