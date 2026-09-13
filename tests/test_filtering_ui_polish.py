"""Filtering overview and modal presentation regression tests."""

from __future__ import annotations

from pathlib import Path

from api.filtering import PlatformAPI
from api.security import hash_password
from storage.database import Database
from storage.destinations import DestinationStore
from storage.filtering import DestinationFilterStore, RoutingOnlyRouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0c" * 16, iterations=1_000)


def test_filtering_overview_api_exposes_active_configured_rule_details(tmp_path):
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
        settings={"channel_name": "Development"},
    )
    routes.create(
        admin.actor,
        admin.id,
        "Zabbix Development",
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

    api = PlatformAPI.__new__(PlatformAPI)
    api.filters = filters
    api.destinations = destinations
    response = api._resource_endpoint("GET", "/api/v2/filters", None, admin.actor)

    assert response.status == 200
    assert len(response.payload["filters"]) == 1
    policy = response.payload["filters"][0]
    assert policy["destination_id"] == target.id
    assert policy["sources"] == ["zabbix"]
    assert len(policy["integrations"]) == 1
    integration = policy["integrations"][0]
    assert integration["source"] == "zabbix"
    assert integration["name"] == "Zabbix"
    assert integration["configured"] is True
    assert integration["rules"] == {
        "severity": ["high", "disaster"],
        "host": ["prod-*"],
    }
    labels = {field["key"]: field["label"] for field in integration["fields"]}
    assert labels["severity"] == "Severity"
    assert labels["host"] == "Host"


def test_filtering_webui_shows_rule_details_and_uses_current_modal_surface():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert "<th>Filters</th>" in script
    assert "filtering-overview-list" in script
    assert "filtering-overview-rule" in script
    assert 'byId("page-title").textContent = VIEW_TITLES.filtering;' in script
    assert ".filtering-modal > section" in styles
    assert "background: var(--surface-solid);" in styles
    assert ".filtering-add-field-row .button" in styles
    assert "white-space: nowrap;" in styles
