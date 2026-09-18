from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _panel(markup: str, panel_id: str) -> str:
    marker = f'id="{panel_id}"'
    position = markup.index(marker)
    start = markup.rfind("<article", 0, position)
    end = markup.index("</article>", position)
    return markup[start:end]


def _function(script: str, signature: str) -> str:
    start = script.index(signature)
    next_async = script.find("\nasync function ", start + len(signature))
    next_plain = script.find("\nfunction ", start + len(signature))
    candidates = [value for value in (next_async, next_plain) if value >= 0]
    end = min(candidates) if candidates else len(script)
    return script[start:end]


def test_round15_backup_first_paint_and_stored_copy_deduplication_are_cached():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    show = _function(app, "function showApp(session)")
    assert "renderAll();" in show
    assert show.index("renderAll();") < show.index('byId("app-shell").hidden = false;')
    assert '"externalBackups",' in patch
    assert '"externalBackupErrors",' in patch
    assert "function deduplicateExternalBackups(backups)" in app
    loader = _function(app, "async function loadExternalBackups(")
    assert "state.externalBackups = deduplicateExternalBackups(backups);" in loader
    assert 'typeof qaSaveWorkspaceCache === "function"' in loader


def test_round15_backup_primary_actions_match_requested_copy():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    recovery = _panel(markup, "backup-recovery-panel")
    stored = _panel(markup, "backup-stored-panel")
    create_local = _function(app, "async function createBackup()")
    create_remote = _function(app, "async function createRemoteBackup()")

    assert ">Create local</span>" in recovery
    assert "confirmAction(" not in create_local
    assert 'data-action="create-remote-backup"' in stored
    assert "button primary backup-icon-button" in stored
    assert ">Create remote</span>" in stored
    assert "Run scheduled now" not in stored
    assert "Refresh</span>" not in stored
    assert 'data-action="refresh-external-backups"' not in stored
    assert 'toast("Select a remote backup destination first.", "error");' in create_remote


def test_round15_portable_import_uses_explicit_server_validation_preview():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert "Preview JSON import" in markup
    assert 'data-action="preview-backup-portable-import"' in markup
    assert 'await previewImport("portable", "backup-portable-file");' in app
    assert 'for (const portableFileId of ["portable-file", "backup-portable-file"])' not in app
    assert 'void previewImport("portable", portableFileId);' not in app

    preview = _function(app, "async function previewImport(")
    assert '"/portability/preview"' in preview
    assert "portable && !response.preview.valid" not in preview
    assert 'byId("import-apply").disabled = !response.preview.valid;' in preview
    assert 'byId("import-dialog").showModal();' in preview
    assert '"Import user configuration"' in preview


def test_round15_housekeeping_has_spacing_short_copy_and_real_svg_icons():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    assert "Housekeeping runs once per day when enabled." not in markup
    assert "Housekeeping runs once per day." in markup
    assert ">Ⅱ<" not in markup
    assert 'class="housekeeping-symbol"' in markup
    render = _function(app, "function renderHousekeepingSettings()")
    assert 'backupSvgIcon(enabled ? "check" : "pause", "housekeeping-symbol")' in render
    assert 'backupSvgIcon("clock", "housekeeping-symbol")' in render
    assert 'backupSvgIcon("broom", "housekeeping-symbol")' not in render
    assert '"Housekeeping runs once per day."' in render

    marker = "/* 2026-09-18 round-15 backups/data-tools/housekeeping polish. */"
    assert marker in styles
    final = styles[styles.index(marker):]
    assert "#view-settings .housekeeping-workspace" in final
    assert "margin-top: 22px !important;" in final
    assert "#backup-data-tools-panel .backup-tool-box > p" in final
    assert ".housekeeping-symbol" in final
