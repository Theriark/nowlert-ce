from pathlib import Path

from api.security import hash_password
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0b" * 16, iterations=1_000)


def test_audit_request_scope_records_only_bounded_safe_request_metadata(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    audit = AuditEventStore(database)

    with audit.request_scope(
        method="post",
        path="/api/v2/destinations/example?access_token=must-not-be-recorded",
        client="192.0.2.44",
        user_agent="Nowlert QA/1.0",
    ):
        audit.write(
            admin.actor,
            "destination.test",
            "destination",
            "example",
            "failed",
            {
                "response_status": 200,
                "retryable": False,
                "password": "must-not-be-recorded",
            },
        )

    event = audit.list_visible(admin.actor, limit=1)[0]
    assert event.details["request_method"] == "POST"
    assert event.details["request_path"] == "/api/v2/destinations/example"
    assert event.details["request_client"] == "192.0.2.44"
    assert event.details["request_user_agent"] == "Nowlert QA/1.0"
    assert "access_token" not in str(event.details)
    assert event.details["password"] == "<redacted>"
    assert event.details["response_status"] == 200
    assert event.details["retryable"] is False


def test_v2_api_service_wraps_platform_requests_in_audit_request_scope():
    service = (ROOT / "src" / "api" / "service.py").read_text(encoding="utf-8")

    assert "with self.platform.audit.request_scope(" in service
    assert "method=method" in service
    assert "path=path" in service
    assert "client=client" in service
    assert "user_agent=user_agent" in service
