"""Reference Filtering UI and non-destructive enable switch regression tests."""

from __future__ import annotations

from pathlib import Path

from api.security import hash_password
from integrations.filtering import filter_schema
from models import Notification
from storage.database import Database
from storage.destinations import DestinationStore
from storage.filtering import RoutingOnlyRouteStore
from storage.filtering_toggle import DestinationFilterStore
from storage.secrets import SecretStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0d" * 16, iterations=1_000)


def test_filter_enable_switch_preserves_rules_while_bypassing_matching(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    secrets = SecretStore(database)
    destinations = DestinationStore(database)
    routes = RoutingOnlyRouteStore(database)
    filters = DestinationFilterStore(database)

    secret = secrets.create(
        admin.actor,
        admin.id,
        "Discord credential",
        "discord",
        "https://discord.com/api/webhooks/123/token",
    )
    target = destinations.create(
        admin.actor,
        admin.id,
        "CE Development - Discord",
        "discord",
        secret_id=secret.id,
        settings={},
    )
    routes.create(
        admin.actor,
        admin.id,
        "Zabbix",
        "zabbix",
        target.id,
        input_type="smtp",
        enabled=True,
    )
    filters.set_rules(
        admin.actor,
        target.id,
        "zabbix",
        {"severity": ["high", "disaster"], "host": ["prod-*"]},
    )

    blocked = Notification(
        source="zabbix",
        metadata={"severity": "warning", "host": "prod-01"},
    )
    assert filters.matches(admin.actor, target.id, blocked) is False

    filters.set_enabled(admin.actor, target.id, "zabbix", False)
    disabled_view = filters.destination_view(admin.actor, target.id)
    zabbix = next(
        item for item in disabled_view["integrations"] if item["source"] == "zabbix"
    )
    assert zabbix["configured"] is True
    assert zabbix["filter_enabled"] is False
    assert zabbix["rules"] == {
        "severity": ["high", "disaster"],
        "host": ["prod-*"],
    }
    assert filters.matches(admin.actor, target.id, blocked) is True
    assert filters.list_visible(admin.actor) == []

    filters.set_enabled(admin.actor, target.id, "zabbix", True)
    enabled_view = filters.destination_view(admin.actor, target.id)
    zabbix = next(
        item for item in enabled_view["integrations"] if item["source"] == "zabbix"
    )
    assert zabbix["filter_enabled"] is True
    assert zabbix["rules"] == {
        "severity": ["high", "disaster"],
        "host": ["prod-*"],
    }
    assert filters.matches(admin.actor, target.id, blocked) is False


def test_redfish_filter_editors_expose_every_supported_severity():
    expected = [
        "critical",
        "fatal",
        "emergency",
        "alert",
        "warning",
        "caution",
        "ok",
        "normal",
        "cleared",
        "informational",
        "information",
        "info",
    ]
    for source in ("supermicro", "hpe_ilo", "dell_idrac"):
        schema = filter_schema(source)
        severity = next(field for field in schema["fields"] if field["key"] == "severity")
        assert severity["values"] == expected

    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    assert "for (const value of field.values || [])" in script


def test_filtering_webui_matches_reference_controls_and_icons():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")
    api = (ROOT / "src" / "api" / "filtering.py").read_text(encoding="utf-8")

    assert "sourceIcon(integration.source)" in script
    assert "outputIcon(policy.output_type)" in script
    assert "filtering-switch" in script
    assert "filter_enabled" in script
    assert "Configure filter — ${integration.name" in script
    assert "matches wildcard" in script
    assert "filtering-overview-chip" in script
    assert "filtering-integration-mark" not in script
    assert "grid-template-columns: repeat(auto-fit, minmax(220px, 280px));" in styles
    assert "justify-content: start;" in styles
    assert ".filtering-editor-identity" in styles
    assert "max-height: min(calc(100vh - 8rem), 860px);" in styles
    assert "max-height: min(92vh, 860px);" not in styles
    assert '{"rules", "enabled"}' in api
