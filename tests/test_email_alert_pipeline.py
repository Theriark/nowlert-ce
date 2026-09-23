"""Phase 8 Email Alerts conversion, suppression, replay, and routing."""

from __future__ import annotations

from pathlib import Path

from api.platform import PlatformAPI
from dispatcher import Dispatcher
from email_alert_pipeline import EmailAlertProcessor, email_message_text
from email_rules import EmailRuleEngine
from inputs.email_mailboxes import (
    MailboxConnectionService,
    MailboxProviderMessage,
    MailboxSyncBatch,
)
from integrations.catalog import infer_input_type, integration, route_options
from integrations.filtering import filter_schema
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryResult, DeliverySummary
from storage.destinations import DestinationStore
from storage.email_alerts import EmailAlertStore
from storage.ownership import Actor
from storage.routes import Route, RouteStore
from storage.routing_bridge import PlatformRoutingBridge
from storage.system_filtering import SystemDestinationFilterStore


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def get(self, *_keys, default=None):
        return default


class FakeDelivery:
    def __init__(self, summary=None):
        self.summary = summary or DeliverySummary(1, 1, 0, 1)
        self.calls = []

    def deliver(self, actor, notification):
        self.calls.append((actor, notification))
        return self.summary


class CapturingAdapter:
    def __init__(self):
        self.calls = []

    def __call__(self, destination, secret_value, notification):
        self.calls.append((destination, secret_value, notification))
        return DeliveryResult(True, response_status=200)


class Registry:
    def __init__(self, adapter):
        self.adapter = adapter

    def delivery_adapters(self):
        return {"discord": self.adapter}


def create_user(
    database,
    identifier,
    username,
    role="user",
):
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


def setup_email(
    database,
    actor,
    *,
    subject="Database replication warning",
    sender="monitor@monitoring.example.com",
    provider_message_id="message-1",
    group_name="Infrastructure",
    classification="warning",
    conditions=None,
    quiet_window_seconds=0,
    priority=10,
):
    store = EmailAlertStore(database)
    mailbox = store.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="Operations Inbox",
    )
    message, created = store.record_message(
        actor,
        mailbox.id,
        provider_message_id=provider_message_id,
        sender=sender,
        recipients=["alerts@example.com", "oncall@example.com"],
        subject=subject,
        provider_deep_link="https://mail.example.com/message/1",
    )
    assert created is True
    group = store.create_group(
        actor,
        actor.user_id,
        group_name,
        quiet_window_seconds=quiet_window_seconds,
    )
    rule = store.create_rule(
        actor,
        actor.user_id,
        group.id,
        "Email classification",
        classification,
        conditions
        or [
            {
                "field": "subject",
                "operator": "contains",
                "value": "database",
            }
        ],
        priority=priority,
    )
    return store, mailbox, message, group, rule


def test_email_is_a_first_class_route_and_filter_source():
    item = integration("email")
    assert item is not None
    assert item["name"] == "Email Alerts"
    assert item["inputs"] == [{"id": "email", "name": "Email Alerts"}]
    assert infer_input_type("email") == "email"
    assert ("email", "email") in {
        (option["source"], option["input_type"])
        for option in route_options()
    }
    assert RouteStore._input_type("email") == "email"

    schema = filter_schema("email")
    assert schema is not None
    fields = {field["key"]: field for field in schema["fields"]}
    assert {
        "severity",
        "mailbox",
        "sender",
        "sender_domain",
        "recipient",
        "subject",
        "group",
        "rule",
        "classification",
        "provider",
    } <= set(fields)
    assert fields["classification"]["paths"] == ["metadata.classification"]

    route = Route(
        id="a" * 32,
        owner_user_id="b" * 32,
        name="Email Alerts",
        source="email",
        filters={},
        priority=50,
        enabled=True,
        created_at=1,
        updated_at=1,
        input_type="email",
    )
    assert RouteStore.matches(
        route,
        Notification(
            source="email",
            title="Mail alert",
            metadata={"_input_type": "email"},
        ),
    )
    assert not RouteStore.matches(
        route,
        Notification(
            source="email",
            title="Wrong input",
            metadata={"_input_type": "http"},
        ),
    )


def test_metadata_rule_promotes_one_normal_nowlert_notification_and_deduplicates(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store, mailbox, message, group, rule = setup_email(
        database,
        owner,
        classification="urgent",
    )
    delivery = FakeDelivery()
    raw_calls = []
    processor = EmailAlertProcessor(
        database,
        store=store,
        rules=EmailRuleEngine(store),
        delivery=delivery,
        raw_loader=lambda actor, message_id: raw_calls.append(
            (actor, message_id)
        ),
    )

    result = processor.process(owner, message.id)

    assert result.action == "promoted"
    assert result.reason == "routed"
    assert result.classification == "urgent"
    assert result.delivered == 1
    assert len(delivery.calls) == 1
    assert raw_calls == []

    delivery_actor, notification = delivery.calls[0]
    assert delivery_actor == owner
    assert notification.source == "email"
    assert notification.category == group.name
    assert notification.status == "critical"
    assert notification.title == message.subject
    assert notification.sender == message.sender
    assert notification.metadata["_input_type"] == "email"
    assert notification.metadata["severity"] == "critical"
    assert notification.metadata["classification"] == "urgent"
    assert notification.metadata["mailbox"] == mailbox.address
    assert notification.metadata["sender_domain"] == "monitoring.example.com"
    assert notification.metadata["group_id"] == group.id
    assert notification.metadata["rule_id"] == rule.id
    assert notification.metadata["provider"] == "imap"
    assert notification.metadata["provider_deep_link"].startswith("https://")

    latest = store.latest_processing(owner, message.id)
    assert latest is not None
    assert latest.action == "promoted"
    assert latest.event_id == result.event_id
    assert latest.details["delivered"] == 1
    assert latest.details["matched_routes"] == 1

    second = processor.process(owner, message.id)
    third = processor.process(owner, message.id)
    assert second.action == "duplicate"
    assert second.reason == "already_processed"
    assert third.action == "duplicate"
    assert third.reason == "already_processed"
    assert len(delivery.calls) == 1


def test_ignore_and_unmatched_email_never_enter_delivery(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store, mailbox, ignored, group, rule = setup_email(
        database,
        owner,
        subject="Newsletter digest",
        classification="ignore",
        conditions=[
            {
                "field": "subject",
                "operator": "contains",
                "value": "newsletter",
            }
        ],
    )
    unmatched, created = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="message-2",
        sender="monitor@monitoring.example.com",
        recipients=["alerts@example.com"],
        subject="Completely unrelated mail",
    )
    assert created is True
    delivery = FakeDelivery()
    processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=delivery,
    )

    ignored_result = processor.process(owner, ignored.id)
    unmatched_result = processor.process(owner, unmatched.id)

    assert ignored_result.action == "ignored"
    assert ignored_result.matched is True
    assert ignored_result.reason == "classification_ignore"
    assert ignored_result.rule_id == rule.id
    assert unmatched_result.action == "ignored"
    assert unmatched_result.matched is False
    assert unmatched_result.reason == "no_matching_rule"
    assert delivery.calls == []


def test_quiet_window_suppresses_then_force_replay_bypasses_it(tmp_path):
    now = [2_000_000_000]
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store = EmailAlertStore(database, clock=lambda: now[0])
    mailbox = store.create_mailbox(
        owner,
        owner.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    group = store.create_group(
        owner,
        owner.user_id,
        "Database",
        quiet_window_seconds=600,
    )
    store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Database warnings",
        "warning",
        [
            {
                "field": "subject",
                "operator": "contains",
                "value": "database",
            }
        ],
    )
    first, _ = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="message-1",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Database warning one",
    )
    second, _ = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="message-2",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Database warning two",
    )
    delivery = FakeDelivery()
    processor = EmailAlertProcessor(
        database,
        store=store,
        rules=EmailRuleEngine(store),
        delivery=delivery,
        clock=lambda: now[0],
    )

    first_result = processor.process(owner, first.id)
    assert first_result.action == "promoted"
    assert len(delivery.calls) == 1

    now[0] += 30
    second_result = processor.process(owner, second.id)
    assert second_result.action == "suppressed"
    assert second_result.reason == "quiet_window"
    assert len(delivery.calls) == 1

    normal_replay = processor.process(owner, second.id, replay=True)
    assert normal_replay.action == "suppressed"
    assert normal_replay.replay is True
    assert len(delivery.calls) == 1

    forced = processor.process(
        owner,
        second.id,
        replay=True,
        bypass_quiet_window=True,
    )
    assert forced.action == "reprocessed"
    assert forced.reason == "routed"
    assert forced.replay is True
    assert len(delivery.calls) == 2


def test_body_content_is_loaded_only_for_enabled_body_rules_and_attachments_ignored(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store, mailbox, metadata_message, group, metadata_rule = setup_email(
        database,
        owner,
        subject="Database metadata match",
        classification="information",
    )
    disabled_body_rule = store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Disabled body rule",
        "urgent",
        [
            {
                "field": "body",
                "operator": "contains",
                "value": "panic",
            }
        ],
        priority=1,
        enabled=False,
    )
    raw_calls = []
    delivery = FakeDelivery()
    processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=delivery,
        raw_loader=lambda actor, message_id: raw_calls.append(message_id),
    )

    metadata_result = processor.process(owner, metadata_message.id)
    assert metadata_result.rule_id == metadata_rule.id
    assert raw_calls == []

    body_message, _ = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="message-body",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Body-only signal",
    )
    store.update_rule(owner, disabled_body_rule.id, enabled=True)
    raw = (
        b"MIME-Version: 1.0\r\n"
        b"Content-Type: multipart/mixed; boundary=phase8\r\n\r\n"
        b"--phase8\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n\r\n"
        b"<html><body>PANIC: <b>replication stopped</b></body></html>\r\n"
        b"--phase8\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"Content-Disposition: attachment; filename=secret.txt\r\n\r\n"
        b"ATTACHMENT-SECRET-MUST-NOT-ROUTE\r\n"
        b"--phase8--\r\n"
    )
    body_calls = []

    body_processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=delivery,
        raw_loader=lambda actor, message_id: (
            body_calls.append((actor.user_id, message_id)),
            raw,
        )[1],
    )
    body_result = body_processor.process(owner, body_message.id)

    assert body_result.rule_id == disabled_body_rule.id
    assert body_result.classification == "urgent"
    assert body_calls == [(owner.user_id, body_message.id)]
    _actor, notification = delivery.calls[-1]
    assert "PANIC" in notification.body
    assert "replication stopped" in notification.body
    assert "ATTACHMENT-SECRET-MUST-NOT-ROUTE" not in notification.body
    assert "ATTACHMENT-SECRET-MUST-NOT-ROUTE" not in email_message_text(raw)


def test_admin_reprocess_routes_as_message_owner_not_administrator(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    admin = create_user(database, "f" * 32, "admin", role="admin")
    store, _mailbox, message, _group, _rule = setup_email(
        database,
        owner,
        classification="warning",
    )
    delivery = FakeDelivery()
    processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=delivery,
    )

    result = processor.process(admin, message.id, replay=True)

    assert result.action == "reprocessed"
    assert len(delivery.calls) == 1
    delivery_actor, notification = delivery.calls[0]
    assert delivery_actor.user_id == owner.user_id
    assert delivery_actor.role == "user"
    assert notification.source == "email"


def test_real_platform_routing_and_destination_filtering_receive_email_events(
    tmp_path,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")

    destination = DestinationStore(database).create(
        owner,
        owner.user_id,
        "Email Discord",
        "discord",
        settings={},
        enabled=True,
    )
    RouteStore(database).create(
        owner,
        owner.user_id,
        "Email Alerts Email",
        "email",
        destination.id,
        input_type="email",
        priority=50,
    )

    filters = SystemDestinationFilterStore(database)
    filters.set_rules(
        owner,
        destination.id,
        "email",
        {"classification": ["urgent"]},
    )

    adapter = CapturingAdapter()
    bridge = PlatformRoutingBridge(database, registry=Registry(adapter))
    store, mailbox, first, group, rule = setup_email(
        database,
        owner,
        subject="Database alert one",
        provider_message_id="pipeline-message-1",
        group_name="Routed Email",
        classification="urgent",
    )
    processor = EmailAlertProcessor(
        database,
        store=store,
        delivery=bridge.delivery,
    )

    blocked = processor.process(owner, first.id)
    assert blocked.action == "promoted"
    assert blocked.reason == "no_matching_route"
    assert blocked.delivered == 0
    assert adapter.calls == []

    filters.clear_source(owner, destination.id, "email")
    second, _ = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="pipeline-message-2",
        sender="monitor@monitoring.example.com",
        recipients=["alerts@example.com"],
        subject="Database alert two",
    )
    delivered = processor.process(owner, second.id)

    assert delivered.reason == "routed"
    assert delivered.matched_routes == 1
    assert delivered.delivered == 1
    assert len(adapter.calls) == 1
    _destination, _secret, notification = adapter.calls[0]
    assert notification.source == "email"
    assert notification.metadata["_input_type"] == "email"
    assert notification.metadata["classification"] == "urgent"


def test_mailbox_sync_processes_only_newly_inserted_messages(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    service = MailboxConnectionService(
        database,
        clock=lambda: now,
    )
    mailbox = service.create_mailbox(
        owner,
        owner.user_id,
        "imap",
        "alerts@example.com",
        settings={
            "host": "imap.example.com",
            "port": 993,
            "security": "ssl",
            "folder": "INBOX",
        },
        credential={
            "username": "alerts@example.com",
            "password": "private-password",
        },
    )

    item = MailboxProviderMessage(
        provider_message_id="imap-provider-1",
        internet_message_id="<imap-provider-1@example.com>",
        sender="monitor@example.com",
        recipients=("alerts@example.com",),
        subject="Database warning",
        received_at=now,
    )
    service.imap.sync = lambda _mailbox, _credentials: MailboxSyncBatch(
        (item,),
        "checkpoint-1",
    )

    class Recorder:
        def __init__(self):
            self.calls = []

        def process(self, actor, message_id):
            self.calls.append((actor.user_id, message_id))

    recorder = Recorder()
    service.processor = recorder

    first = service.sync_mailbox(owner, mailbox.id)
    second = service.sync_mailbox(owner, mailbox.id)

    assert first.created == 1
    assert first.duplicates == 0
    assert second.created == 0
    assert second.duplicates == 1
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == owner.user_id


def test_reprocess_api_and_webui_expose_controlled_replay(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    api = PlatformAPI(
        database,
        Dispatcher(),
        Configuration(),
    )
    store = api.email_connections.store
    mailbox = store.create_mailbox(
        owner,
        owner.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
    )
    group = store.create_group(owner, owner.user_id, "Operations")
    store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Warnings",
        "warning",
        [{"field": "subject", "operator": "contains", "value": "warning"}],
    )
    message, _ = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="api-message",
        sender="monitor@example.com",
        recipients=["alerts@example.com"],
        subject="Service warning",
    )
    delivery = FakeDelivery()
    api.email_pipeline._delivery = delivery

    response = api._email_message_action(
        "POST",
        {"bypass_quiet_window": True},
        owner,
        message.id,
        "reprocess",
    )

    assert response.status == 200
    assert response.payload["result"]["action"] == "reprocessed"
    assert response.payload["result"]["replay"] is True
    assert response.payload["result"]["delivered"] == 1

    script = (ROOT / "src" / "webui" / "email_alerts.js").read_text(
        encoding="utf-8"
    )
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    assert '/email-messages/${id}/reprocess' in script
    assert 'emailAction: "reprocess-message"' in script
    assert 'emailAction: "force-reprocess-message"' in script
    assert "bypass_quiet_window: force" in script
    assert "Force replay bypasses the Email Alert group quiet window." in script
    assert "Attachments are never used for matching." in script
    assert 'email: "Email Alerts"' in app
    for forbidden in (
        "innerHTML",
        "localStorage",
        "eval(",
    ):
        assert forbidden not in script
