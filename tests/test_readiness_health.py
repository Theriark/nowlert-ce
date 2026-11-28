"""Health checks reflect mailbox synchronization and the real backup target."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.security import hash_password
from storage.backup_targets import BackupTargetStore
from storage.database import Database
from storage.health import HealthCheckService
from storage.settings import DEFAULT_BACKUP_SETTINGS
from storage.users import UserStore


NOW = 1_800_000_000


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x31" * 16, iterations=1_000)


class FakeConfigurationSync:
    def __init__(self, **backups):
        self.backups = {**DEFAULT_BACKUP_SETTINGS, **backups}

    def synchronize(self):
        return SimpleNamespace(ready=True, errors=[])

    def backup_settings(self):
        return dict(self.backups)


@pytest.fixture
def state(tmp_path, monkeypatch):
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text("")
    monkeypatch.setattr("storage.backup_targets._MOUNTINFO", mountinfo)
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    return database, admin


def check(database, key, configuration_sync=None):
    checks = HealthCheckService(database, configuration_sync, clock=lambda: NOW).run()
    return next(item for item in checks if item["key"] == key)


def add_mailbox(database, owner_id, name, connection_state):
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO email_mailboxes(
                id, owner_user_id, provider, name, name_normalized, address,
                address_normalized, connection_state, created_at, updated_at
            ) VALUES (?, ?, 'imap', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name.replace(" ", "-") + "0" * 20,
                owner_id,
                name,
                name.casefold(),
                f"{name.replace(' ', '.')}@example.com",
                f"{name.replace(' ', '.')}@example.com".casefold(),
                connection_state,
                NOW,
                NOW,
            ),
        )


def add_sync_audit(database, outcome, count, created_at=NOW - 60):
    with database.transaction() as connection:
        for _ in range(count):
            connection.execute(
                """
                INSERT INTO audit_events(
                    action, resource_type, outcome, details_json, created_at
                ) VALUES ('email.mailbox.sync', 'email_mailbox', ?, '{}', ?)
                """,
                (outcome, created_at),
            )


def test_mailbox_health_is_healthy_without_mailboxes(state):
    database, _admin = state

    result = check(database, "mailbox_sync")

    assert result["status"] == "healthy"
    assert result["detail"] == "no mailboxes connected"


def test_repeated_mailbox_sync_failures_are_a_warning(state):
    database, admin = state
    add_mailbox(database, admin.id, "Operations inbox", "healthy")
    add_sync_audit(database, "failed", 249)
    add_sync_audit(database, "success", 251)

    result = check(database, "mailbox_sync")

    assert result["status"] == "warning"
    assert result["name"] == "Mailbox synchronization"
    assert "249 failed synchronization(s) in the last 24 hours" in result["detail"]


def test_mailbox_in_error_state_is_a_warning_with_guidance(state):
    database, admin = state
    add_mailbox(database, admin.id, "Operations inbox", "healthy")
    add_mailbox(database, admin.id, "Security inbox", "error")
    add_sync_audit(database, "failed", 1)

    result = check(database, "mailbox_sync")

    assert result["status"] == "warning"
    assert "1 of 2 mailbox(es) cannot synchronize" in result["detail"]
    assert "Email Alerts" in result["detail"]
    # Mailbox names stay private to their owners.
    assert "Security inbox" not in result["detail"]


def test_old_or_occasional_mailbox_failures_stay_healthy(state):
    database, admin = state
    add_mailbox(database, admin.id, "Operations inbox", "healthy")
    add_sync_audit(database, "failed", 40, created_at=NOW - 3 * 86400)
    add_sync_audit(database, "failed", 2)

    result = check(database, "mailbox_sync")

    assert result["status"] == "healthy"
    assert result["detail"] == "1 mailbox(es) synchronizing; 2 failed attempt(s) in the last 24 hours"


def test_scheduled_backup_to_a_named_target_is_not_reported_disabled(state, tmp_path):
    database, admin = state
    target = BackupTargetStore(database).create(
        admin.actor,
        {
            "name": "Weekly archive",
            "type": "local",
            "local_path": str(tmp_path / "archive"),
            "enabled": True,
        },
    )

    result = check(
        database,
        "external_backup",
        FakeConfigurationSync(schedule="weekly", target_id=target.id),
    )

    assert result["status"] == "healthy"
    assert result["name"] == "Local backup target"
    assert result["detail"] == "weekly backups to Weekly archive"
    assert "disabled" not in result["detail"]


def test_scheduled_backup_to_an_unmounted_nas_target_is_an_error(state, tmp_path):
    database, admin = state
    target = BackupTargetStore(database).create(
        admin.actor,
        {
            "name": "NAS archive",
            "type": "nfs",
            "host": "nas.example.invalid",
            "remote_path": "/exports/nowlert",
            "local_path": str(tmp_path / "nfs"),
            "enabled": True,
        },
    )

    result = check(
        database,
        "external_backup",
        FakeConfigurationSync(schedule="weekly", target_id=target.id),
    )

    assert result["status"] == "error"
    assert result["name"] == "NFS backup target"
    assert result["detail"] == "weekly backups to NAS archive: mounted path is unavailable"


def test_failed_last_scheduled_backup_is_a_warning(state, tmp_path):
    database, admin = state
    target = BackupTargetStore(database).create(
        admin.actor,
        {
            "name": "Weekly archive",
            "type": "local",
            "local_path": str(tmp_path / "archive"),
            "enabled": True,
        },
    )
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO backup_schedule_runs(period_key, started_at, completed_at, outcome)
            VALUES ('weekly:2027-W02', ?, ?, 'failed')
            """,
            (NOW - 600, NOW - 590),
        )

    result = check(
        database,
        "external_backup",
        FakeConfigurationSync(schedule="weekly", target_id=target.id),
    )

    assert result["status"] == "warning"
    assert result["detail"] == "weekly backups to Weekly archive: the last scheduled backup failed"


def test_schedule_without_external_target_explains_local_only_backups(state):
    database, _admin = state

    result = check(database, "external_backup", FakeConfigurationSync(schedule="daily"))

    assert result["status"] == "healthy"
    assert "daily backups are kept in local state only" in result["detail"]


def test_editing_a_backup_target_clears_its_last_test_time(state, tmp_path):
    database, admin = state
    targets = BackupTargetStore(database)
    target = targets.create(
        admin.actor,
        {
            "name": "Local archive",
            "type": "local",
            "local_path": str(tmp_path / "archive"),
            "enabled": True,
        },
    )
    tested = targets.test(admin.actor, target.id)
    assert tested.last_test_at is not None

    edited = targets.update(
        admin.actor, target.id, {"local_path": str(tmp_path / "moved")}
    )

    assert edited.last_test_outcome is None
    assert edited.last_test_at is None
    assert edited.public()["last_test_at"] is None
