"""Destination-owned filtering regression tests."""

from __future__ import annotations

import json

import pytest

from api.security import hash_password
from integrations.filtering import filter_schema, filter_schemas
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult
from storage.destinations import DestinationStore
from storage.filtering import (
    DestinationFilterStore,
    FilteredPlatformDeliveryService,
    RoutingOnlyRouteStore,
)
from storage.migrations import LATEST_SCHEMA_VERSION
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0b" * 16, iterations=1_000)


@pytest.fixture
def filtering_platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    secrets = SecretStore(database)
    destinations = DestinationStore(database)
    routes = RoutingOnlyRouteStore(database)
    filters = DestinationFilterStore(database)
    history = DeliveryHistoryStore(database)
    return {
        "database": database,
        "users": users,
        "admin": admin,
        "owner": owner,
        "secrets": secrets,
        "destinations": destinations,
        "routes": routes,
        "filters": filters,
        "history": history,
    }


def destination(platform, name="Operations", output_type="webhook"):
    owner = platform["owner"]
    secret = platform["secrets"].create(
        owner.actor,
        owner.id,
        f"{name} credential",
        output_type,
        f"secret-for-{name}",
    )
    return platform["destinations"].create(
        owner.actor,
        owner.id,
        name,
        output_type,
        secret_id=secret.id,
        settings={},
    )


def route(platform, target, source, *, input_type="http", enabled=True, name=None):
    owner = platform["owner"]
    actor = platform["admin"].actor if source == "*" else owner.actor
    return platform["routes"].create(
        actor,
        owner.id,
        name or f"{source}-{target.name}",
        source,
        target.id,
        input_type=input_type,
        enabled=enabled,
    )


def test_schema_11_adds_destination_filter_storage(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    assert database.migrate() == 14
    assert LATEST_SCHEMA_VERSION == 14
    with database.connect() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "destination_filters" in tables
    assert "route_destinations" in tables


def test_every_builtin_integration_has_a_declared_safe_filter_schema():
    schemas = filter_schemas()
    assert len(schemas) == 15
    assert len({item["source"] for item in schemas}) == 15
    assert all(item["fields"] for item in schemas)
    for schema in schemas:
        for field in schema["fields"]:
            assert field["kind"] in {"enum", "text"}
            assert field["paths"]
            assert all("source_fields" not in path for path in field["paths"])


def test_available_sources_follow_enabled_destination_routes_only(filtering_platform):
    target = destination(filtering_platform)
    route(filtering_platform, target, "xo", input_type="smtp")
    route(
        filtering_platform,
        target,
        "zabbix",
        input_type="smtp",
        enabled=False,
        name="disabled-zabbix",
    )
    route(
        filtering_platform,
        target,
        "*",
        input_type="redfish",
        name="hardware-fallback",
    )

    sources = filtering_platform["filters"].available_sources(
        filtering_platform["owner"].actor,
        target.id,
    )

    assert "xo" in sources
    assert "zabbix" not in sources
    assert {"supermicro", "hpe_ilo", "dell_idrac"} <= set(sources)


def test_unavailable_integration_cannot_be_configured(filtering_platform):
    target = destination(filtering_platform)
    route(filtering_platform, target, "xo", input_type="smtp")

    with pytest.raises(ValueError, match="not enabled"):
        filtering_platform["filters"].set_rules(
            filtering_platform["owner"].actor,
            target.id,
            "zabbix",
            {"severity": ["high"]},
        )


def test_all_or_zero_enum_values_are_unrestricted_but_subset_is_configured(
    filtering_platform,
):
    target = destination(filtering_platform)
    route(filtering_platform, target, "zabbix", input_type="smtp")
    owner = filtering_platform["owner"]
    filters = filtering_platform["filters"]
    severities = filter_schema("zabbix")["fields"][0]["values"]

    assert filters.set_rules(
        owner.actor,
        target.id,
        "zabbix",
        {"severity": severities},
    ) is None
    assert filters.set_rules(
        owner.actor,
        target.id,
        "zabbix",
        {"severity": []},
    ) is None

    policy = filters.set_rules(
        owner.actor,
        target.id,
        "zabbix",
        {"severity": ["high", "disaster"]},
    )
    assert policy is not None
    assert filters.matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", metadata={"severity": "high"}),
    )
    assert not filters.matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", metadata={"severity": "information"}),
    )


def test_declared_text_fields_support_shell_style_patterns(filtering_platform):
    target = destination(filtering_platform)
    route(filtering_platform, target, "zabbix", input_type="smtp")
    owner = filtering_platform["owner"]
    filters = filtering_platform["filters"]

    filters.set_rules(
        owner.actor,
        target.id,
        "zabbix",
        {"host": ["prod-*"]},
    )

    assert filters.matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", metadata={"host": "prod-db-01"}),
    )
    assert not filters.matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", metadata={"host": "lab-db-01"}),
    )


def test_legacy_route_filters_migrate_once_and_are_cleared(filtering_platform):
    platform = filtering_platform
    target = destination(platform)
    owner = platform["owner"]
    legacy_routes = RouteStore(platform["database"])
    legacy = legacy_routes.create(
        owner.actor,
        owner.id,
        "Legacy Zabbix",
        "zabbix",
        target.id,
        input_type="smtp",
        filters={"statuses": ["failure"]},
    )

    assert platform["filters"].migrate_legacy_route_filters(force=True) == 1
    assert platform["filters"].migrate_legacy_route_filters() == 0

    with platform["database"].connect() as connection:
        row = connection.execute(
            "SELECT filters_json FROM routes WHERE id = ?",
            (legacy.id,),
        ).fetchone()
        policy = connection.execute(
            "SELECT clauses_json FROM destination_filters "
            "WHERE destination_id = ? AND source = 'zabbix'",
            (target.id,),
        ).fetchone()
    assert row["filters_json"] == "{}"
    assert json.loads(policy["clauses_json"]) == [{"statuses": ["failure"]}]
    assert platform["filters"].matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", status="failure"),
    )
    assert not platform["filters"].matches(
        owner.actor,
        target.id,
        Notification(source="zabbix", status="success"),
    )


def test_destination_filter_blocks_transport_and_allows_matching_event(
    filtering_platform,
):
    platform = filtering_platform
    target = destination(platform)
    route(platform, target, "grafana", input_type="http")
    owner = platform["owner"]
    platform["filters"].set_rules(
        owner.actor,
        target.id,
        "grafana",
        {"severity": ["critical"]},
    )
    observed = []

    def adapter(delivery_target, _secret, notification):
        observed.append((delivery_target.id, notification.title))
        return DeliveryResult(True, response_status=204)

    service = FilteredPlatformDeliveryService(
        platform["routes"],
        platform["destinations"],
        platform["secrets"],
        platform["history"],
        {"webhook": adapter},
        filters=platform["filters"],
        sleeper=lambda _delay: None,
    )

    blocked = service.deliver(
        owner.actor,
        Notification(
            source="grafana",
            title="Warning",
            metadata={"severity": "warning", "_input_type": "http"},
        ),
    )
    allowed = service.deliver(
        owner.actor,
        Notification(
            source="grafana",
            title="Critical",
            metadata={"severity": "critical", "_input_type": "http"},
        ),
    )

    assert blocked.matched_routes == 0
    assert allowed.matched_routes == 1
    assert observed == [(target.id, "Critical")]


def test_filtered_specific_route_can_fall_back_to_wildcard_destination(
    filtering_platform,
):
    platform = filtering_platform
    owner = platform["owner"]
    specific = destination(platform, "Grafana critical")
    fallback = destination(platform, "HTTP fallback")
    route(platform, specific, "grafana", input_type="http", name="Grafana specific")
    route(platform, fallback, "*", input_type="http", name="HTTP fallback")
    platform["filters"].set_rules(
        owner.actor,
        specific.id,
        "grafana",
        {"severity": ["critical"]},
    )
    delivered_to = []

    def adapter(delivery_target, _secret, _notification):
        delivered_to.append(delivery_target.id)
        return DeliveryResult(True, response_status=204)

    service = FilteredPlatformDeliveryService(
        platform["routes"],
        platform["destinations"],
        platform["secrets"],
        platform["history"],
        {"webhook": adapter},
        filters=platform["filters"],
        sleeper=lambda _delay: None,
    )
    summary = service.deliver(
        owner.actor,
        Notification(
            source="grafana",
            title="Warning",
            metadata={"severity": "warning", "_input_type": "http"},
        ),
    )

    assert summary.matched_routes == 1
    assert delivered_to == [fallback.id]
