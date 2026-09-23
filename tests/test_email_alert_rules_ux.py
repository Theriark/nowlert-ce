"""Phase 7 Email Alerts Groups, Rules, Activity, and normal-user UX."""

from __future__ import annotations

from pathlib import Path

import pytest

from dispatcher import Dispatcher
from email_rules import EmailRuleEngine
from api.platform import PlatformAPI
from storage.database import Database
from storage.email_alerts import EmailAlertStore
from storage.ownership import Actor
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


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


def test_email_group_rule_and_mailbox_crud_are_owner_scoped(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    other = create_user(database, "b" * 32, "other")
    store = EmailAlertStore(database, clock=lambda: 2_000_000_000)

    mailbox = store.create_mailbox(
        owner,
        owner.user_id,
        "imap",
        "alerts@example.com",
        name="Operations",
        settings={
            "host": "imap.example.com",
            "port": 993,
            "security": "ssl",
            "folder": "INBOX",
        },
    )
    mailbox = store.update_mailbox(
        owner,
        mailbox.id,
        name="Operations alerts",
        enabled=False,
    )
    assert mailbox.name == "Operations alerts"
    assert mailbox.enabled is False

    group = store.create_group(
        owner,
        owner.user_id,
        "Infrastructure",
        description="Infrastructure monitoring email",
    )
    group = store.update_group(
        owner,
        group.id,
        description="Infrastructure and platform alerts",
        quiet_window_seconds=900,
    )
    assert group.description == "Infrastructure and platform alerts"
    assert group.quiet_window_seconds == 900

    rule = store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Database sender",
        "warning",
        [
            {
                "field": "sender_domain",
                "operator": "equals",
                "value": "MONITORING.EXAMPLE.COM",
            },
            {
                "field": "subject",
                "operator": "contains",
                "value": "database",
            },
        ],
        match_mode="all",
        priority=20,
    )
    assert rule.conditions[0]["value"] == "monitoring.example.com"

    rule = store.update_rule(
        owner,
        rule.id,
        classification="urgent",
        match_mode="any",
        priority=10,
    )
    assert rule.classification == "urgent"
    assert rule.match_mode == "any"
    assert rule.priority == 10

    with pytest.raises(PermissionError):
        store.update_group(other, group.id, name="Not allowed")
    with pytest.raises(PermissionError):
        store.update_rule(other, rule.id, enabled=False)
    with pytest.raises(PermissionError):
        store.update_mailbox(other, mailbox.id, enabled=True)

    store.delete_rule(owner, rule.id)
    with pytest.raises(KeyError, match="email rule"):
        store.get_rule(owner, rule.id)

    secret_id = store.delete_mailbox(owner, mailbox.id)
    assert secret_id is None
    with pytest.raises(KeyError, match="email mailbox"):
        store.get_mailbox(owner, mailbox.id)


@pytest.mark.parametrize(
    ("condition", "message"),
    [
        (
            {"field": "regex", "operator": "equals", "value": "x"},
            "field",
        ),
        (
            {"field": "subject", "operator": "regex", "value": "x"},
            "operator",
        ),
        (
            {"field": "subject", "operator": "contains", "value": ""},
            "value",
        ),
        (
            {
                "field": "subject",
                "operator": "contains",
                "value": "x",
                "case_sensitive": True,
            },
            "unsupported",
        ),
    ],
)
def test_email_rule_conditions_are_simple_and_bounded(
    tmp_path,
    condition,
    message,
):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store = EmailAlertStore(database)
    group = store.create_group(owner, owner.user_id, "Rules")

    with pytest.raises(ValueError, match=message):
        store.create_rule(
            owner,
            owner.user_id,
            group.id,
            "Invalid",
            "warning",
            [condition],
        )


def test_rule_engine_supports_and_or_body_mailbox_and_priority(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    store = EmailAlertStore(database, clock=lambda: 2_000_000_000)
    mailbox = store.create_mailbox(
        owner,
        owner.user_id,
        "gmail",
        "alerts@example.com",
        name="Operations Inbox",
    )
    message, _created = store.record_message(
        owner,
        mailbox.id,
        provider_message_id="gmail-1",
        sender="zabbix@monitoring.example.com",
        recipients=["alerts@example.com", "oncall@example.com"],
        subject="Database replication latency",
    )
    group = store.create_group(owner, owner.user_id, "Infrastructure")

    body_rule = store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Body panic",
        "urgent",
        [
            {
                "field": "body",
                "operator": "contains",
                "value": "PANIC: replication stopped",
            }
        ],
        priority=5,
    )
    metadata_rule = store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Database monitoring",
        "warning",
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
            {
                "field": "recipient",
                "operator": "equals",
                "value": "ONCALL@example.com",
            },
            {
                "field": "mailbox",
                "operator": "equals",
                "value": "OPERATIONS INBOX",
            },
        ],
        match_mode="all",
        priority=10,
    )
    store.create_rule(
        owner,
        owner.user_id,
        group.id,
        "Fallback",
        "information",
        [
            {
                "field": "subject",
                "operator": "contains",
                "value": "database",
            },
            {
                "field": "sender",
                "operator": "ends_with",
                "value": "@other.example.com",
            },
        ],
        match_mode="any",
        priority=20,
    )

    engine = EmailRuleEngine(store)

    without_body = engine.evaluate_message(owner, message.id)
    assert without_body.matched is True
    assert without_body.rule_id == metadata_rule.id
    assert without_body.classification == "warning"
    assert all(item.matched for item in without_body.conditions)

    with_body = engine.evaluate_message(
        owner,
        message.id,
        body="Host reports PANIC: replication stopped immediately.",
    )
    assert with_body.rule_id == body_rule.id
    assert with_body.classification == "urgent"

    store.update_group(owner, group.id, enabled=False)
    disabled = engine.evaluate_message(owner, message.id, body="PANIC")
    assert disabled.matched is False


def test_rule_engine_does_not_cross_owner_boundary_for_admin(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    admin = create_user(database, "f" * 32, "admin", "admin")
    first = create_user(database, "a" * 32, "first")
    second = create_user(database, "b" * 32, "second")
    store = EmailAlertStore(database)

    first_mailbox = store.create_mailbox(
        first,
        first.user_id,
        "imap",
        "first@example.com",
        name="First",
    )
    message, _created = store.record_message(
        first,
        first_mailbox.id,
        provider_message_id="first-message",
        sender="sender@example.com",
        recipients=["first@example.com"],
        subject="Shared subject",
    )
    first_group = store.create_group(first, first.user_id, "First group")
    first_rule = store.create_rule(
        first,
        first.user_id,
        first_group.id,
        "First rule",
        "warning",
        [{"field": "subject", "operator": "equals", "value": "Shared subject"}],
        priority=50,
    )

    second_group = store.create_group(second, second.user_id, "Second group")
    store.create_rule(
        second,
        second.user_id,
        second_group.id,
        "Foreign higher-priority rule",
        "urgent",
        [{"field": "subject", "operator": "equals", "value": "Shared subject"}],
        priority=1,
    )

    result = EmailRuleEngine(store).evaluate_message(admin, message.id)
    assert result.rule_id == first_rule.id
    assert result.classification == "warning"


def test_phase7_platform_api_exposes_groups_rules_activity_and_overview(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = create_user(database, "a" * 32, "owner")
    api = PlatformAPI(
        database,
        Dispatcher(),
        Configuration(),
    )

    created_group = api._email_groups_endpoint(
        "POST",
        {
            "name": "Operations",
            "description": "Operational alerts",
            "quiet_window_seconds": 300,
            "enabled": True,
        },
        owner,
    )
    assert created_group.status == 201
    group_id = created_group.payload["group"]["id"]

    created_rule = api._email_rules_endpoint(
        "POST",
        {
            "group_id": group_id,
            "name": "Urgent subject",
            "classification": "urgent",
            "match_mode": "all",
            "conditions": [
                {
                    "field": "subject",
                    "operator": "contains",
                    "value": "critical",
                }
            ],
            "priority": 10,
            "enabled": True,
        },
        owner,
    )
    assert created_rule.status == 201

    groups = api._email_groups_endpoint("GET", None, owner)
    rules = api._email_rules_endpoint("GET", None, owner)
    overview = api._email_overview_endpoint("GET", owner)
    activity = api._email_activity_endpoint("GET", owner)

    assert [item["name"] for item in groups.payload["groups"]] == ["Operations"]
    assert [item["classification"] for item in rules.payload["rules"]] == ["urgent"]
    assert overview.payload["overview"]["groups"] == 1
    assert overview.payload["overview"]["rules"] == 1
    assert activity.payload == {"messages": [], "processing": []}


def test_phase7_email_alerts_webui_is_packaged_and_normal_user_visible(tmp_path):
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    script = (ROOT / "src" / "webui" / "email_alerts.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "email_alerts.css").read_text(encoding="utf-8")

    assert 'id="email-alerts-nav"' in markup
    assert 'data-view="email-alerts"' in markup
    assert 'id="view-email-alerts"' in markup
    for tab in ("overview", "groups", "rules", "mailboxes", "activity"):
        assert f'data-email-tab="{tab}"' in markup
    assert '"email-alerts": "Email Alerts"' in app

    for endpoint in (
        "/email-overview",
        "/email-groups",
        "/email-rules",
        "/email-mailboxes",
        "/email-mailbox-providers",
        "/email-activity",
        "/email-mailboxes/oauth-complete",
    ):
        assert endpoint in script

    for classification in ("urgent", "warning", "information", "ignore"):
        assert f'["{classification}",' in script
    for field in (
        "sender",
        "sender_domain",
        "recipient",
        "subject",
        "body",
        "mailbox",
    ):
        assert f'["{field}",' in script

    assert "innerHTML" not in script
    assert "localStorage" not in script
    assert "eval(" not in script
    assert ".email-alert-tabs" in styles

    service = WebUIService(
        Configuration(
            {
                "http": {"enabled": True},
                "api": {"enabled": True},
                "platform": {"enabled": True},
                "webui": {"enabled": True},
            }
        ),
        root=ROOT,
    )
    assert service.response("/ui/email_alerts.js").status == 200
    assert service.response("/ui/email_alerts.css").status == 200
    page = service.response("/").body.decode("utf-8")
    assert "/ui/email_alerts.js?v=" in page
    assert "/ui/email_alerts.css?v=" in page



def test_email_alerts_mailbox_connect_ux_exposes_provider_login_paths():
    script = (ROOT / "src" / "webui" / "email_alerts.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "email_alerts.css").read_text(encoding="utf-8")

    assert '["Connect mailbox", "new-mailbox"]' in script
    assert 'emailMailboxConnectButton("gmail", "Connect Gmail", true)' in script
    assert 'emailMailboxConnectButton("microsoft_365", "Connect Microsoft 365")' in script
    assert 'emailMailboxConnectButton("imap", "Connect IMAP / IMAPS")' in script
    assert 'node?.dataset.provider || ""' in script
    assert 'request("/email-mailbox-providers")' in script
    assert '"Continue to Google"' in script
    assert '"Continue to Microsoft"' in script
    assert 'id: "email-mailbox-provider-hint"' in script
    assert 'input.required = provider === "imap"' in script
    assert "email-oauth-client-id" not in script
    assert "email-oauth-client-secret" not in script
    assert "email-oauth-redirect" not in script
    assert "client_id:" not in script
    assert "client_secret:" not in script
    assert "OAuth application credentials are configured once" in script
    assert ".email-mailbox-connect-actions" in styles
    assert ".email-mailbox-connect-empty" in styles
