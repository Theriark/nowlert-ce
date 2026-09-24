"""Phase 5 Email Alerts durable foundation and data-contract regressions."""

from __future__ import annotations

import sqlite3

import pytest

from models import EmailAlertEvent
from storage.database import Database
from storage.email_alerts import EmailAlertStore, email_message_identity
from storage.migrations import LATEST_SCHEMA_VERSION
from storage.ownership import Actor


def create_user(database, user_id, username, role="user"):
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users(
                id, username, username_normalized, password_hash,
                role, enabled, created_at, updated_at
            ) VALUES (?, ?, ?, 'hash', ?, 1, 1, 1)
            """,
            (user_id, username, username.casefold(), role),
        )
    return Actor(user_id, role)


def test_schema_15_adds_email_alert_foundation_tables(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")

    assert database.migrate() == 15
    assert LATEST_SCHEMA_VERSION == 15

    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        migration = connection.execute(
            """
            SELECT name
            FROM schema_migrations
            WHERE version = 15
            """
        ).fetchone()
        message_indexes = {
            row["name"]
            for row in connection.execute(
                "PRAGMA index_list(email_messages)"
            )
        }

    assert {
        "email_mailboxes",
        "email_groups",
        "email_rules",
        "email_messages",
        "email_message_contents",
        "email_processing_history",
    } <= tables
    assert migration["name"] == "email alerts foundation"
    assert "email_messages_metadata_expiry" in message_indexes


def test_message_identity_is_mailbox_scoped_and_prefers_provider_id():
    one = email_message_identity(
        "mailbox-a",
        provider_message_id="provider-123",
        internet_message_id="<internet-ignored@example.invalid>",
    )
    same = email_message_identity(
        "mailbox-a",
        provider_message_id="provider-123",
        internet_message_id="<different@example.invalid>",
    )
    other_mailbox = email_message_identity(
        "mailbox-b",
        provider_message_id="provider-123",
    )
    fallback = email_message_identity(
        "mailbox-a",
        internet_message_id="<message@example.invalid>",
    )

    assert one == same
    assert one != other_mailbox
    assert one != fallback
    assert len(one) == 64

    with pytest.raises(ValueError, match="required for deduplication"):
        email_message_identity("mailbox-a")


def test_mailbox_group_rule_and_event_contract_are_owner_scoped(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "o" * 32, "owner")
    other = create_user(database, "x" * 32, "other")
    store = EmailAlertStore(database, clock=lambda: now)

    mailbox = store.create_mailbox(
        owner,
        owner.user_id,
        "gmail",
        "alerts@example.com",
        name="Operations mailbox",
        settings={"folder": "INBOX"},
    )
    group = store.create_group(
        owner,
        owner.user_id,
        "Database operations",
        description="Database alerts from trusted senders",
    )
    rule = store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "PostgreSQL sender",
        "urgent",
        [
            {
                "field": "sender_domain",
                "operator": "equals",
                "value": "monitoring.example.com",
            }
        ],
    )
    message, created = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="gmail-123",
        internet_message_id="<message-123@example.com>",
        sender="zabbix@monitoring.example.com",
        recipients=["alerts@example.com"],
        subject="PostgreSQL replication lag exceeded",
        received_at=now - 30,
        folder="INBOX",
        labels=["IMPORTANT"],
        provider_deep_link=(
            "https://mail.google.com/mail/u/0/#inbox/gmail-123"
        ),
        metadata={"thread_id": "thread-123"},
    )
    processing = store.record_processing(
        owner,
        message.id,
        "matched",
        classification="urgent",
        group_id=group.id,
        rule_id=rule.id,
        details={
            "condition": "sender_domain=monitoring.example.com",
            "access_token": "must-not-be-recorded",
        },
    )
    event = store.build_event(
        owner,
        message.id,
        "urgent",
        group_id=group.id,
        rule_id=rule.id,
    )

    assert created is True
    assert mailbox.provider == "gmail"
    assert rule.conditions[0]["field"] == "sender_domain"
    assert processing.details["access_token"] == "<redacted>"

    assert isinstance(event, EmailAlertEvent)
    assert event.source == "email"
    assert event.mailbox == "alerts@example.com"
    assert event.sender_domain == "monitoring.example.com"
    assert event.recipient == "alerts@example.com"
    assert event.group == "Database operations"
    assert event.rule == "PostgreSQL sender"
    assert event.classification == "urgent"
    assert event.filter_metadata() == {
        "mailbox": "alerts@example.com",
        "mailbox_id": mailbox.id,
        "sender": "zabbix@monitoring.example.com",
        "sender_domain": "monitoring.example.com",
        "recipient": "alerts@example.com",
        "recipients": ["alerts@example.com"],
        "subject": "PostgreSQL replication lag exceeded",
        "group": "Database operations",
        "group_id": group.id,
        "rule": "PostgreSQL sender",
        "rule_id": rule.id,
        "provider": "gmail",
        "provider_message_id": "gmail-123",
        "internet_message_id": "<message-123@example.com>",
        "message_id": message.id,
        "classification": "urgent",
        "provider_deep_link": (
            "https://mail.google.com/mail/u/0/#inbox/gmail-123"
        ),
        "received_at": now - 30,
    }

    with pytest.raises(PermissionError):
        store.get_mailbox(other, mailbox.id)
    with pytest.raises(PermissionError):
        store.get_message(other, message.id)


def test_message_deduplication_is_within_mailbox_scope(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database, "u" * 32, "user")
    store = EmailAlertStore(database, clock=lambda: 1000)
    first_mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "one@example.com",
        name="One",
    )
    second_mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "two@example.com",
        name="Two",
    )

    first, first_created = store.record_message(
        actor,
        first_mailbox.id,
        internet_message_id="<same@example.invalid>",
        sender="sender@example.invalid",
        recipients=["one@example.com"],
        subject="First",
    )
    duplicate, duplicate_created = store.record_message(
        actor,
        first_mailbox.id,
        internet_message_id="same@example.invalid",
        sender="sender@example.invalid",
        recipients=["one@example.com"],
        subject="Changed subject must not duplicate",
    )
    other, other_created = store.record_message(
        actor,
        second_mailbox.id,
        internet_message_id="<same@example.invalid>",
        sender="sender@example.invalid",
        recipients=["two@example.com"],
        subject="Second mailbox",
    )

    assert first_created is True
    assert duplicate_created is False
    assert duplicate.id == first.id
    assert duplicate.subject == "First"
    assert other_created is True
    assert other.id != first.id

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM email_messages"
        ).fetchone()[0] == 2


def test_message_deduplication_crosses_providers_for_same_address(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database, "u" * 32, "user")
    store = EmailAlertStore(database, clock=lambda: 1000)

    gmail = store.create_mailbox(
        actor,
        actor.user_id,
        "gmail",
        "alerts@example.com",
        name="Gmail",
    )
    imap = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="IMAP",
    )

    first, first_created = store.record_message(
        actor,
        gmail.id,
        provider_message_id="gmail-provider-id",
        internet_message_id="<shared-message@example.invalid>",
        sender="sender@example.invalid",
        recipients=["alerts@example.com"],
        subject="Provider-native copy",
    )
    duplicate, duplicate_created = store.record_message(
        actor,
        imap.id,
        provider_message_id="imap:777:42",
        internet_message_id="shared-message@example.invalid",
        sender="sender@example.invalid",
        recipients=["alerts@example.com"],
        subject="Same physical email through IMAP",
    )

    assert first_created is True
    assert duplicate_created is False
    assert duplicate.id == first.id
    assert duplicate.mailbox_id == gmail.id
    assert duplicate.subject == "Provider-native copy"

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM email_messages"
        ).fetchone()[0] == 1


def test_raw_content_is_separate_and_expires_before_metadata(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database, "u" * 32, "user")
    store = EmailAlertStore(database, clock=lambda: now)
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "microsoft_365",
        "alerts@example.com",
        name="Microsoft 365",
    )
    message, _created = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="graph-123",
        sender="sender@example.invalid",
        recipients=["alerts@example.com"],
        subject="Sensitive email",
        metadata_retention_days=90,
    )
    content = store.store_raw_content(
        actor,
        message.id,
        "From: sender@example.invalid\n\nprivate body",
        retention_days=1,
    )
    store.record_processing(
        actor,
        message.id,
        "matched",
        classification="warning",
        retention_days=1,
    )

    assert "raw_content" not in message.__dict__
    assert content["size_bytes"] > 0
    assert store.read_raw_content(actor, message.id).endswith(
        b"private body"
    )

    first = store.purge_expired(now=now + 86401)
    assert first == {
        "raw_content_deleted": 1,
        "processing_history_deleted": 1,
        "message_metadata_deleted": 0,
    }
    assert store.get_message(actor, message.id).id == message.id
    with pytest.raises(KeyError, match="raw email content"):
        store.read_raw_content(actor, message.id)

    second = store.purge_expired(now=now + 91 * 86400)
    assert second["message_metadata_deleted"] == 1
    with pytest.raises(KeyError, match="email message"):
        store.get_message(actor, message.id)


def test_foundation_rejects_inline_secrets_and_unsafe_provider_links(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database, "u" * 32, "user")
    store = EmailAlertStore(database)

    with pytest.raises(ValueError, match="secret store"):
        store.create_mailbox(
            actor,
            actor.user_id,
            "imap",
            "alerts@example.com",
            settings={"password": "do-not-store-here"},
        )

    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Safe mailbox",
        settings={"host": "imap.example.com", "port": 993},
    )
    with pytest.raises(ValueError, match="safe HTTPS"):
        store.record_message(
            actor,
            mailbox.id,
            provider_message_id="imap-1",
            sender="sender@example.invalid",
            recipients=["alerts@example.com"],
            provider_deep_link="http://mail.example.com/message/1",
        )


def test_schema_foreign_keys_remove_sensitive_mail_state_with_mailbox(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = create_user(database, "u" * 32, "user")
    store = EmailAlertStore(database, clock=lambda: 1000)
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    message, _created = store.record_message(
        actor,
        mailbox.id,
        provider_message_id="imap-42",
        sender="sender@example.invalid",
        recipients=["alerts@example.com"],
    )
    store.store_raw_content(actor, message.id, b"private")
    store.record_processing(
        actor,
        message.id,
        "matched",
        classification="information",
    )

    with database.transaction() as connection:
        connection.execute(
            "DELETE FROM email_mailboxes WHERE id = ?",
            (mailbox.id,),
        )

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM email_messages"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM email_message_contents"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM email_processing_history"
        ).fetchone()[0] == 0


def test_cross_owner_email_rule_is_rejected_and_content_fk_is_enforced(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    first = create_user(database, "a" * 32, "first")
    second = create_user(database, "b" * 32, "second")
    store = EmailAlertStore(database)
    group = store.create_group(first, first.user_id, "First group")

    with pytest.raises(PermissionError, match="same owner"):
        store.create_rule(
            second,
            second.user_id,
            group.id,
            "Foreign rule",
            "warning",
            [{"field": "subject", "operator": "contains", "value": "alert"}],
        )

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO email_message_contents(
                    message_id, content_type, raw_content,
                    content_sha256, stored_at
                ) VALUES ('missing', 'text/plain', x'00', ?, 1)
                """,
                ("0" * 64,),
            )
