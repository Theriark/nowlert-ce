from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from api.security import hash_password
from storage.backup_targets import BackupTargetStore
from storage.database import Database
from storage.housekeeping import HousekeepingService
from storage.settings import DEFAULT_BACKUP_SETTINGS, SettingsStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def __init__(self, data):
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


def _panel(markup: str, panel_id: str) -> str:
    start = markup.index(f'id="{panel_id}"')
    article_start = markup.rfind("<article", 0, start)
    end = markup.index("</article>", start)
    return markup[article_start:end]


def _function(script: str, signature: str) -> str:
    start = script.index(signature)
    next_function = script.find("\nasync function ", start + len(signature))
    next_plain = script.find("\nfunction ", start + len(signature))
    candidates = [value for value in (next_function, next_plain) if value >= 0]
    end = min(candidates) if candidates else len(script)
    return script[start:end]


def _fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x31" * 16, iterations=1_000)


def test_backup_actions_refresh_both_panels_without_local_confirmation_and_retire_stale_time_input():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    enhancements = (ROOT / "src" / "webui" / "enhancements.js").read_text(encoding="utf-8")

    create = _function(app, "async function createBackup()")
    run = _function(app, "async function createRemoteBackup()")

    assert "confirmAction(" not in create
    assert 'request("/backups", { method: "POST", body: {} })' in create
    assert "await refreshBackupPanels();" in create
    assert "await refreshBackupPanels();" in run
    assert "async function refreshBackupPanels()" in app
    refresh = _function(app, "async function refreshBackupPanels()")
    assert "await loadWorkspace();" in refresh
    assert "await loadExternalBackups({ silent: true });" in refresh
    assert "renderBackupRecoveryTable();" in refresh
    assert "renderStoredBackupTable();" in refresh

    assert "const originalRenderBackupSettings = renderBackupSettings;" not in enhancements
    assert 'if (backupTime) backupTime.type = "text";' not in enhancements


def test_backup_controls_move_to_stored_copies_mounts_are_automatic_and_tables_align():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    recovery = _panel(markup, "backup-recovery-panel")
    stored = _panel(markup, "backup-stored-panel")

    assert 'data-action="create-backup"' in recovery
    assert 'data-action="create-remote-backup"' not in recovery
    assert 'data-action="refresh-external-backups"' not in recovery
    assert '>Create local</span>' in recovery
    assert 'data-action="create-remote-backup"' in stored
    assert '>Create remote</span>' in stored
    assert 'data-action="refresh-external-backups"' not in stored

    assert 'id="backup-managed-mounts"' not in markup
    save = _function(app, "async function saveBackupSettings(event)")
    assert "managed_mounts: true" in save

    marker = "/* 2026-09-18 backup follow-up alignment and controls. */"
    assert marker in styles
    final = styles[styles.index(marker):]
    assert "#backup-recovery-panel," in final
    assert "#backup-stored-panel" in final
    assert "display: flex;" in final
    assert "flex-direction: column;" in final
    assert ".backup-table-footer" in final
    assert "margin-top: auto;" in final


def test_backup_selects_match_the_existing_operational_control_style():
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 backup follow-up alignment and controls. */"
    assert marker in styles
    final = styles[styles.index(marker):]

    assert ".backup-field-control select" in final
    assert "background: #0f151b !important;" in final
    assert "border: 1px solid rgba(148, 163, 184, 0.24) !important;" in final
    assert "border-radius: 9px !important;" in final
    assert "color-scheme: dark;" in final


def test_managed_backup_mounting_is_always_enabled(tmp_path):
    values = {**DEFAULT_BACKUP_SETTINGS, "managed_mounts": False}
    normalized = SettingsStore.validate("platform", "backups", values)
    assert DEFAULT_BACKUP_SETTINGS["managed_mounts"] is True
    assert normalized["managed_mounts"] is True

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    store = BackupTargetStore(
        database,
        Configuration({"platform": {"backups": {"managed_mounts": False}}}),
    )
    assert store.managed_mounts is True


def test_housekeeping_reference_workspace_uses_clickable_status_and_recent_runs():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")

    assert 'id="housekeeping-toggle"' in markup
    assert 'data-action="toggle-housekeeping"' in markup
    assert 'id="housekeeping-enabled"' not in markup
    assert 'id="housekeeping-next-run"' in markup
    assert 'id="housekeeping-recent-runs"' in markup
    assert 'id="housekeeping-schedule-note"' in markup

    assert "async function toggleHousekeeping()" in app
    assert 'action === "toggle-housekeeping"' in app
    assert "status.recent_runs" in app
    assert "status.next_run_at" in app
    save = _function(app, "async function saveHousekeepingSettings(event)")
    assert "enabled: state.housekeepingSettings.enabled === true" in save

    marker = "/* 2026-09-18 Housekeeping reference workspace. */"
    assert marker in styles
    final = styles[styles.index(marker):]
    assert ".housekeeping-status-card" in final
    assert ".housekeeping-body-grid" in final
    assert "grid-template-columns:" in final
    assert ".housekeeping-status-card.is-enabled" in final
    assert ".housekeeping-status-card.is-disabled" in final


def test_housekeeping_status_exposes_three_recent_runs_and_next_schedule(tmp_path):
    zone = ZoneInfo("Europe/Lisbon")
    now = int(datetime(2026, 9, 18, 10, 0, tzinfo=zone).timestamp())

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=_fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    service = HousekeepingService(database, clock=lambda: now)

    service.settings_store.set(
        admin.actor,
        "platform",
        "regional",
        {"timezone": "Europe/Lisbon", "language": "en-GB", "time_format": "24"},
    )
    service.update_settings(
        admin.actor,
        {
            "enabled": True,
            "time": "09:00",
            "delivery_history_days": 7,
            "audit_history_days": 90,
            "backup_run_history_days": 30,
        },
    )

    with database.transaction() as connection:
        for index in range(4):
            started = now - ((index + 1) * 86400)
            connection.execute(
                """
                INSERT INTO housekeeping_runs(
                    period_key, started_at, completed_at, outcome,
                    deliveries_deleted, audit_deleted, backup_runs_deleted,
                    sessions_deleted
                ) VALUES (?, ?, ?, 'success', ?, ?, ?, 0)
                """,
                (
                    f"daily:2026-09-{17-index:02d}",
                    started,
                    started + 120 + index,
                    1000 - index,
                    300 - index,
                    10 - index,
                ),
            )

    status = service.status()
    assert len(status["recent_runs"]) == 3
    assert status["recent_runs"][0]["deliveries_deleted"] == 1000
    assert status["recent_runs"][2]["deliveries_deleted"] == 998
    assert status["next_run_at"] == int(
        datetime(2026, 9, 19, 9, 0, tzinfo=zone).timestamp()
    )

    service.update_settings(
        admin.actor,
        {
            "enabled": False,
            "time": "09:00",
            "delivery_history_days": 7,
            "audit_history_days": 90,
            "backup_run_history_days": 30,
        },
    )
    assert service.status()["next_run_at"] is None
