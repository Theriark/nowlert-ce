from api.security import hash_password
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.housekeeping import HousekeepingService
from storage.users import UserStore


PASSWORD = "correct horse battery staple"


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\\x07" * 16, iterations=1_000)


def test_housekeeping_defaults_and_bounded_history_retention(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    assert database.migrate() == 13
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", PASSWORD)
    service = HousekeepingService(
        database,
        audit=AuditEventStore(database),
        clock=lambda: now,
    )

    assert service.settings() == {
        "enabled": True,
        "time": "03:15",
        "delivery_history_days": 90,
        "audit_history_days": 365,
        "backup_run_history_days": 180,
    }

    old_delivery = now - 91 * 86400
    recent_delivery = now - 10 * 86400
    old_audit = now - 366 * 86400
    recent_audit = now - 20 * 86400
    with database.transaction() as connection:
        for suffix, created in (("old", old_delivery), ("recent", recent_delivery)):
            connection.execute(
                """
                INSERT INTO delivery_attempts(
                    id, delivery_id, owner_user_id, route_id, destination_id,
                    source, title, severity, outcome, attempt_number, retryable,
                    response_status, error_code, safe_error, created_at,
                    completed_at, input_type, device_name, event_name,
                    event_description, event_status
                ) VALUES (?, ?, ?, NULL, NULL, 'grafana', ?, 'warning',
                          'delivered', 1, 0, 204, NULL, NULL, ?, ?, 'http',
                          'monitor-01', 'test', '', 'active')
                """,
                (
                    f"attempt-{suffix}",
                    f"delivery-{suffix}",
                    admin.id,
                    suffix,
                    created,
                    created,
                ),
            )
        connection.execute(
            """
            INSERT INTO audit_events(
                actor_user_id, action, resource_type, resource_id,
                outcome, details_json, created_at
            ) VALUES (?, 'old.audit', 'test', NULL, 'success', '{}', ?)
            """,
            (admin.id, old_audit),
        )
        connection.execute(
            """
            INSERT INTO audit_events(
                actor_user_id, action, resource_type, resource_id,
                outcome, details_json, created_at
            ) VALUES (?, 'recent.audit', 'test', NULL, 'success', '{}', ?)
            """,
            (admin.id, recent_audit),
        )
        connection.execute(
            """
            INSERT INTO backup_schedule_runs(
                period_key, started_at, completed_at, outcome
            ) VALUES ('old-backup', ?, ?, 'success')
            """,
            (now - 181 * 86400, now - 181 * 86400 + 10),
        )

    result = service.run(admin.actor)

    assert result["deliveries_deleted"] == 1
    assert result["audit_deleted"] == 1
    assert result["backup_runs_deleted"] == 1
    with database.connect() as connection:
        delivery_ids = {
            row["id"] for row in connection.execute("SELECT id FROM delivery_attempts")
        }
        audit_actions = {
            row["action"] for row in connection.execute("SELECT action FROM audit_events")
        }
    assert delivery_ids == {"attempt-recent"}
    assert "old.audit" not in audit_actions
    assert "recent.audit" in audit_actions
    assert "housekeeping.run" in audit_actions


def test_housekeeping_zero_days_keeps_history_forever(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", PASSWORD)
    service = HousekeepingService(database, clock=lambda: now)
    service.update_settings(
        admin.actor,
        {
            "enabled": True,
            "time": "03:15",
            "delivery_history_days": 0,
            "audit_history_days": 0,
            "backup_run_history_days": 0,
        },
    )
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO audit_events(
                actor_user_id, action, resource_type, resource_id,
                outcome, details_json, created_at
            ) VALUES (?, 'keep.audit', 'test', NULL, 'success', '{}', 1)
            """,
            (admin.id,),
        )

    service.run(admin.actor)

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE action = 'keep.audit'"
        ).fetchone()[0] == 1
