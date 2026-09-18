"""Regression coverage for deterministic Filtering and simplified Settings."""

from __future__ import annotations

import json
from pathlib import Path

from api.security import hash_password
from integrations.filtering import filter_schema
from models import Notification
from storage.database import Database
from storage.destinations import DestinationStore
from storage.filtering import RoutingOnlyRouteStore
from storage.secrets import SecretStore
from storage.settings import SettingsStore
from storage.system_filtering import SystemDestinationFilterStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0c" * 16, iterations=1_000)


def platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    secrets = SecretStore(database)
    destinations = DestinationStore(database)
    routes = RoutingOnlyRouteStore(database)
    secret = secrets.create(
        owner.actor,
        owner.id,
        "Operations credential",
        "webhook",
        "secret-value",
    )
    destination = destinations.create(
        owner.actor,
        owner.id,
        "Operations",
        "webhook",
        secret_id=secret.id,
        settings={},
    )
    routes.create(
        owner.actor,
        owner.id,
        "Dell Redfish",
        "dell_idrac",
        destination.id,
        input_type="redfish",
    )
    return database, admin, owner, destination



def test_system_filtering_only_exposes_explicit_routes_assigned_to_destination(tmp_path):
    database, admin, owner, destination = platform(tmp_path)
    routes = RoutingOnlyRouteStore(database)
    routes.create(
        owner.actor,
        owner.id,
        "Grafana HTTP",
        "grafana",
        destination.id,
        input_type="http",
    )
    routes.create(
        admin.actor,
        owner.id,
        "SMTP fallback",
        "*",
        destination.id,
        input_type="smtp",
    )

    filters = SystemDestinationFilterStore(database)

    # Filtering must follow the exact routes selected on this destination.
    # A wildcard/fallback route is routing plumbing and must not expand into
    # every integration supported by that input type.
    assert set(filters.available_sources(owner.actor, destination.id)) == {
        "dell_idrac",
        "grafana",
    }


def test_allow_and_block_policy_has_deterministic_precedence(tmp_path):
    database, _admin, owner, destination = platform(tmp_path)
    filters = SystemDestinationFilterStore(database)
    filters.set_rules(
        owner.actor,
        destination.id,
        "dell_idrac",
        {
            "policy": [
                {
                    "action": "allow",
                    "conditions": {"message_id": ["USR0030"]},
                },
                {
                    "action": "block",
                    "conditions": {"source_ip": ["192.0.2.10"]},
                },
            ]
        },
    )

    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(
            source="dell_idrac",
            metadata={"message_id": "USR0030", "source_ip": "192.0.2.10"},
        ),
    )
    assert filters.matches(
        owner.actor,
        destination.id,
        Notification(
            source="dell_idrac",
            metadata={"message_id": "USR0030", "source_ip": "192.0.2.11"},
        ),
    )
    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(
            source="dell_idrac",
            metadata={"message_id": "SYS1000", "source_ip": "192.0.2.11"},
        ),
    )


def test_selected_single_rule_is_a_block_policy(tmp_path):
    database, _admin, owner, destination = platform(tmp_path)
    filters = SystemDestinationFilterStore(database)
    filters.set_rules(
        owner.actor,
        destination.id,
        "dell_idrac",
        {"message_id": ["USR0030"]},
    )

    view = filters.destination_view(owner.actor, destination.id)
    dell = next(item for item in view["integrations"] if item["source"] == "dell_idrac")
    assert dell["policy_rules"] == [
        {"action": "block", "conditions": {"message_id": ["usr0030"]}}
    ]
    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(source="dell_idrac", metadata={"message_id": "USR0030"}),
    )
    assert filters.matches(
        owner.actor,
        destination.id,
        Notification(source="dell_idrac", metadata={"message_id": "SYS1000"}),
    )



def test_selecting_every_enum_value_blocks_every_supported_value(tmp_path):
    database, _admin, owner, destination = platform(tmp_path)
    filters = SystemDestinationFilterStore(database)
    severities = next(
        field["values"]
        for field in filter_schema("dell_idrac")["fields"]
        if field["key"] == "severity"
    )

    policy = filters.set_rules(
        owner.actor,
        destination.id,
        "dell_idrac",
        {"severity": severities},
    )

    assert policy is not None
    view = filters.destination_view(owner.actor, destination.id)
    dell = next(item for item in view["integrations"] if item["source"] == "dell_idrac")
    assert dell["policy_rules"] == [
        {"action": "block", "conditions": {"severity": severities}}
    ]
    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(source="dell_idrac", metadata={"severity": "critical"}),
    )
    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(source="dell_idrac", metadata={"severity": "information"}),
    )


def test_legacy_dell_trusted_clients_migrate_to_destination_block_policy(tmp_path):
    database, admin, owner, destination = platform(tmp_path)
    SettingsStore(database).set(
        admin.actor,
        "integration",
        "dell_idrac",
        {"suppress_ipmi_session_audit_from": ["192.0.2.164"]},
    )

    filters = SystemDestinationFilterStore(database)
    view = filters.destination_view(owner.actor, destination.id)
    dell = next(item for item in view["integrations"] if item["source"] == "dell_idrac")
    assert dell["policy_rules"] == [
        {
            "action": "block",
            "conditions": {
                "message_id": ["usr0030", "usr0032"],
                "source_ip": ["192.0.2.164"],
            },
        }
    ]
    assert not filters.matches(
        owner.actor,
        destination.id,
        Notification(
            source="dell_idrac",
            metadata={"message_id": "USR0030", "source_ip": "192.0.2.164"},
        ),
    )
    assert filters.matches(
        owner.actor,
        destination.id,
        Notification(
            source="dell_idrac",
            metadata={"message_id": "USR0031", "source_ip": "192.0.2.164"},
        ),
    )
    with database.connect() as connection:
        row = connection.execute(
            "SELECT value_json FROM settings_records "
            "WHERE namespace = 'integration' AND setting_key = 'dell_idrac'"
        ).fetchone()
        stored = connection.execute(
            "SELECT clauses_json FROM destination_filters "
            "WHERE destination_id = ? AND source = 'dell_idrac'",
            (destination.id,),
        ).fetchone()
    assert row is None
    assert json.loads(stored["clauses_json"])["version"] == 2

    filters = SystemDestinationFilterStore(database)
    view = filters.destination_view(owner.actor, destination.id)
    dell = next(item for item in view["integrations"] if item["source"] == "dell_idrac")
    assert len(dell["policy_rules"]) == 1


def test_policy_webui_simplifies_settings_and_restores_native_filter_editor():
    script = (ROOT / "src" / "webui" / "policy_simplification.js").read_text(encoding="utf-8")
    css = (ROOT / "src" / "webui" / "policy_simplification.css").read_text(encoding="utf-8")
    filtering = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")

    assert 'const ADMIN_VIEWS = ["users", "settings", "updates", "data"]' in script
    assert 'document.getElementById("profile-settings")?.remove()' in script
    assert 'profileRow(document.getElementById("profile-api-access"), "◇", "API access")' in script
    assert 'container.classList.remove("resource-grid")' in script
    assert 'home_assistant: "Map Home Assistant endpoints and components to readable device names."' in script
    assert '"Aliases & normalization"' in script
    assert '"Event processing"' in script
    assert '"xo"' not in script.split("const SETTING_GROUPS", 1)[1].split("const SETTING_LABELS", 1)[0]
    assert '"dell_idrac"' not in script.split("const SETTING_GROUPS", 1)[1].split("const SETTING_LABELS", 1)[0]
    assert '"zabbix"' not in script.split("const SETTING_GROUPS", 1)[1].split("const SETTING_LABELS", 1)[0]

    assert 'policy-filter-dialog' not in script
    assert 'data-policy=' not in script
    assert "BLOCK wins." not in script
    assert 'if (action === "configure-integration") return openIntegrationEditor(id);' in filtering
    assert 'if (!integration.configured && enabled)' in filtering
    assert 'id: "filter-dell-trusted-ips"' in script
    assert 'Session audit suppression' in script

    assert ".administration-tabs" in css
    assert "margin-bottom: 1rem" in css
    assert ".settings-subsection-grid" in css
    assert "#filter-destination-help" in css
    assert '/ui/policy_simplification.js' in service
    assert '/ui/policy_simplification.css' in service
