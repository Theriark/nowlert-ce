"""Prometheus routing and destination-filtering parity."""

from __future__ import annotations

from api.security import hash_password
from integrations.catalog import route_options
from integrations.filtering import filter_schema
from models import Notification
from storage.database import Database
from storage.destination_access import SystemRoutingRouteStore
from storage.destinations import DestinationStore
from storage.filtering import DestinationFilterStore, RoutingOnlyRouteStore
from storage.users import UserStore


def _fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x19" * 16, iterations=1_000)


def _platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=_fast_hash)
    admin = users.bootstrap_admin(
        "administrator",
        "correct horse battery staple",
    )
    return database, admin


def _route_name(option: dict, suffix: str = "") -> str:
    return (
        f"{option['integration_name']} {option['input_name']}{suffix}"
    ).strip()


def test_complete_pre_prometheus_matrix_adds_only_prometheus_route(tmp_path):
    database, admin = _platform(tmp_path)
    routes = SystemRoutingRouteStore(database)
    options = route_options()
    previous = [
        option
        for option in options
        if option["source"] != "prometheus"
    ]

    for option in previous:
        routes.create(
            admin.actor,
            admin.id,
            _route_name(option, " CE Development"),
            option["source"],
            input_type=option["input_type"],
        )

    before = routes.list_visible_safe(admin.actor)[0]
    prometheus = [
        route
        for route in before
        if route.source == "prometheus"
        and route.input_type == "http"
    ]

    assert len(before) == len(options)
    assert len(prometheus) == 1
    assert prometheus[0].name == "Prometheus HTTP CE Development"
    assert prometheus[0].destination_ids == ()

    after = routes.list_visible_safe(admin.actor)[0]
    assert len(after) == len(options)
    assert len(
        [
            route
            for route in after
            if route.source == "prometheus"
            and route.input_type == "http"
        ]
    ) == 1


def test_partial_custom_route_set_is_not_expanded(tmp_path):
    database, admin = _platform(tmp_path)
    routes = SystemRoutingRouteStore(database)
    routes.create(
        admin.actor,
        admin.id,
        "Grafana only",
        "grafana",
        input_type="http",
    )

    visible, errors = routes.list_visible_safe(admin.actor)

    assert errors == []
    assert [(route.source, route.input_type) for route in visible] == [
        ("grafana", "http")
    ]


def test_prometheus_filter_schema_exposes_alertmanager_fields():
    schema = filter_schema("prometheus")
    assert schema is not None
    assert schema["name"] == "Prometheus"
    assert schema["inputs"] == [{"id": "http", "name": "HTTP"}]

    fields = {field["key"]: field for field in schema["fields"]}
    assert fields["severity"]["values"] == [
        "info",
        "information",
        "notice",
        "warning",
        "warn",
        "error",
        "critical",
        "fatal",
        "emergency",
    ]
    assert fields["status"]["values"] == ["firing", "resolved"]
    assert {
        "alert_name",
        "receiver",
        "instance",
        "service",
        "job",
        "namespace",
        "pod",
        "node",
        "summary",
        "description",
        "labels",
        "group_key",
        "fingerprint",
    } <= set(fields)
    assert fields["alert_name"]["paths"] == [
        "metadata.alert_name",
        "title",
    ]
    assert fields["instance"]["paths"] == [
        "metadata.instance",
        "metadata.host",
    ]
    assert fields["group_key"]["paths"] == [
        "metadata.group_key",
        "metadata.deduplication_key",
    ]


def test_prometheus_filter_rules_match_normalized_alertmanager_metadata(tmp_path):
    database, admin = _platform(tmp_path)
    destination = DestinationStore(database).create(
        admin.actor,
        admin.id,
        "Prometheus Discord",
        "discord",
        settings={"channel_name": "prometheus"},
    )
    RoutingOnlyRouteStore(database).create(
        admin.actor,
        admin.id,
        "Prometheus HTTP",
        "prometheus",
        destination.id,
        input_type="http",
    )
    filters = DestinationFilterStore(database)
    filters.set_rules(
        admin.actor,
        destination.id,
        "prometheus",
        {
            "status": ["firing"],
            "severity": ["critical"],
            "job": ["api-*"],
            "receiver": ["nowlert-*"],
            "namespace": ["production"],
        },
    )

    matched = Notification(
        source="prometheus",
        title="HighRequestLatency",
        status="failure",
        metadata={
            "state": "firing",
            "severity": "critical",
            "job": "api-server",
            "receiver": "nowlert-critical",
            "namespace": "production",
        },
    )
    wrong_job = Notification(
        source="prometheus",
        title="HighRequestLatency",
        status="failure",
        metadata={
            "state": "firing",
            "severity": "critical",
            "job": "worker",
            "receiver": "nowlert-critical",
            "namespace": "production",
        },
    )

    assert filters.matches(admin.actor, destination.id, matched)
    assert not filters.matches(admin.actor, destination.id, wrong_job)
