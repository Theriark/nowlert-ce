"""One-pass delivery route resolution regression tests."""

from __future__ import annotations

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult, PlatformDeliveryService
from storage.destinations import DestinationStore
from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x28" * 16, iterations=1_000)


def build_platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    relationships = RouteDestinationStore(database)
    return {
        "database": database,
        "users": users,
        "admin": admin,
        "owner": owner,
        "destinations": destinations,
        "routes": routes,
        "relationships": relationships,
    }


def signature(candidates):
    return [
        (
            candidate.route.id,
            tuple(candidate.route.destination_ids),
            candidate.destination_id,
            candidate.target.destination.id if candidate.target is not None else None,
            candidate.target.secret_id if candidate.target is not None else None,
        )
        for candidate in candidates
    ]


def legacy_candidates(platform, actor, notification):
    routes = platform["routes"].matching(actor, actor.user_id, notification)
    return platform["relationships"].expand(actor, routes)


def test_resolve_matching_matches_two_stage_route_order_and_destination_state(tmp_path):
    platform = build_platform(tmp_path)
    owner = platform["owner"]

    first = platform["routes"].create(
        owner.actor,
        owner.id,
        "First",
        "grafana",
        priority=10,
    )
    second = platform["routes"].create(
        owner.actor,
        owner.id,
        "Second",
        "grafana",
        priority=50,
    )

    alpha = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Alpha",
        "webhook",
        settings={},
    )
    beta = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Beta",
        "webhook",
        settings={},
    )
    disabled = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Disabled",
        "webhook",
        settings={},
        enabled=False,
    )

    platform["relationships"].replace_for_destination(
        owner.actor,
        alpha.id,
        [first.id, second.id],
    )
    platform["relationships"].replace_for_destination(
        owner.actor,
        beta.id,
        [second.id],
    )
    platform["relationships"].replace_for_destination(
        owner.actor,
        disabled.id,
        [first.id],
    )

    notification = Notification(
        source="grafana",
        status="warning",
        title="Resolver parity",
        metadata={"severity": "warning"},
    )

    legacy = legacy_candidates(platform, owner.actor, notification)
    combined = platform["relationships"].resolve_matching(
        owner.actor,
        owner.id,
        notification,
    )

    assert signature(combined) == signature(legacy)
    assert [candidate.destination_id for candidate in combined] == [
        alpha.id,
        beta.id,
    ]
    assert combined[0].route.destination_ids == (
        alpha.id,
        disabled.id,
    )
    assert all(candidate.target is not None for candidate in combined)


def test_resolve_matching_preserves_specific_route_wildcard_fallback(tmp_path):
    platform = build_platform(tmp_path)
    admin = platform["admin"]

    specific = platform["routes"].create(
        admin.actor,
        admin.id,
        "Specific",
        "grafana",
        priority=10,
    )
    wildcard = platform["routes"].create(
        admin.actor,
        admin.id,
        "Wildcard",
        "*",
        priority=50,
    )

    specific_destination = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Specific destination",
        "webhook",
        settings={},
    )
    fallback_destination = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Fallback destination",
        "webhook",
        settings={},
    )

    platform["relationships"].replace_for_destination(
        admin.actor,
        specific_destination.id,
        [specific.id],
    )
    platform["relationships"].replace_for_destination(
        admin.actor,
        fallback_destination.id,
        [wildcard.id],
    )

    grafana = Notification(source="grafana", title="Specific")
    other = Notification(source="zabbix", title="Fallback")

    for notification in (grafana, other):
        legacy = legacy_candidates(platform, admin.actor, notification)
        combined = platform["relationships"].resolve_matching(
            admin.actor,
            admin.id,
            notification,
        )
        assert signature(combined) == signature(legacy)

    assert [
        candidate.destination_id
        for candidate in platform["relationships"].resolve_matching(
            admin.actor,
            admin.id,
            grafana,
        )
    ] == [specific_destination.id]

    assert [
        candidate.destination_id
        for candidate in platform["relationships"].resolve_matching(
            admin.actor,
            admin.id,
            other,
        )
    ] == [fallback_destination.id]


def test_platform_delivery_uses_one_pass_resolver_not_legacy_matching_or_expand(
    tmp_path,
):
    platform = build_platform(tmp_path)
    owner = platform["owner"]

    route = platform["routes"].create(
        owner.actor,
        owner.id,
        "Grafana",
        "grafana",
    )
    destination = platform["destinations"].create(
        owner.actor,
        owner.id,
        "Webhook",
        "webhook",
        settings={},
    )
    platform["relationships"].replace_for_destination(
        owner.actor,
        destination.id,
        [route.id],
    )

    def legacy_path_called(*_args, **_kwargs):
        raise AssertionError("legacy two-stage routing path must not be used")

    platform["routes"].matching = legacy_path_called
    platform["relationships"].expand = legacy_path_called
    platform["destinations"].for_delivery = legacy_path_called

    observed = []
    service = PlatformDeliveryService(
        platform["routes"],
        platform["destinations"],
        SecretStore(platform["database"]),
        DeliveryHistoryStore(platform["database"]),
        {
            "webhook": lambda target, _secret, _notification: (
                observed.append(target.id)
                or DeliveryResult(True, response_status=204)
            )
        },
        relationships=platform["relationships"],
        sleeper=lambda _delay: None,
    )

    summary = service.deliver(
        owner.actor,
        Notification(source="grafana", title="One-pass resolver"),
    )

    assert summary.delivered == 1
    assert summary.failed == 0
    assert observed == [destination.id]
