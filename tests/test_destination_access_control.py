"""Delegated Destination access, privacy, and system Route acceptance tests."""

from __future__ import annotations

import pytest

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryResult
from storage.destination_access import (
    AccessControlledDeliveryHistoryStore,
    AccessControlledDestinationStore,
    AccessControlledRouteDestinationStore,
    DestinationAccessStore,
    SystemRoutingRouteStore,
)
from storage.system_filtering import SystemDestinationFilterStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0e" * 16, iterations=1_000)


@pytest.fixture
def access_platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    alice = users.create("alice-user", "alice secure password")
    bob = users.create("bob-user", "bob secure password")
    access = DestinationAccessStore(database)
    destinations = AccessControlledDestinationStore(database, access=access)
    routes = SystemRoutingRouteStore(database)
    relationships = AccessControlledRouteDestinationStore(database, access=access)
    filters = SystemDestinationFilterStore(database, access=access)
    history = AccessControlledDeliveryHistoryStore(database)
    return {
        "database": database,
        "users": users,
        "admin": admin,
        "alice": alice,
        "bob": bob,
        "access": access,
        "destinations": destinations,
        "routes": routes,
        "relationships": relationships,
        "filters": filters,
        "history": history,
    }


def test_private_user_destination_is_hidden_from_admin_but_owned_by_user(access_platform):
    platform = access_platform
    admin = platform["admin"]
    alice = platform["alice"]
    destinations = platform["destinations"]

    shared = destinations.create(
        admin.actor,
        admin.id,
        "Company Teams",
        "teams",
        settings={},
        shared=True,
    )
    private = destinations.create(
        alice.actor,
        alice.id,
        "Alice mail",
        "discord",
        settings={},
        shared=False,
    )

    assert {item.id for item in destinations.list_visible(admin.actor)} == {shared.id}
    assert {item.id for item in destinations.list_visible(alice.actor)} == {
        shared.id,
        private.id,
    }
    assert destinations.get(alice.actor, private.id).id == private.id
    with pytest.raises(PermissionError):
        destinations.get(admin.actor, private.id)
    alice_shared = destinations.create(
        alice.actor,
        alice.id,
        "Alice shared",
        "discord",
        settings={},
        shared=True,
    )
    assert alice_shared.owner_user_id == alice.id
    assert alice_shared.shared is True
    assert platform["access"].private_destination_count(alice.id) == 1


def test_destination_edit_and_filter_permissions_are_independent(access_platform):
    platform = access_platform
    admin = platform["admin"]
    alice = platform["alice"]
    access = platform["access"]
    destinations = platform["destinations"]
    shared = destinations.create(
        admin.actor,
        admin.id,
        "Shared Discord",
        "discord",
        settings={},
        shared=True,
    )
    route = platform["routes"].create(
        admin.actor,
        admin.id,
        "Grafana",
        "grafana",
        input_type="http",
    )
    platform["relationships"].replace_for_destination(
        admin.actor,
        shared.id,
        [route.id],
    )

    with pytest.raises(PermissionError):
        destinations.update(alice.actor, shared.id, name="No access")
    with pytest.raises(PermissionError):
        platform["filters"].set_rules(
            alice.actor,
            shared.id,
            "grafana",
            {"severity": ["critical"]},
        )

    access.set_for_user(
        admin.actor,
        alice.id,
        shared.id,
        can_edit_destination=True,
        can_manage_filters=False,
    )
    assert destinations.update(alice.actor, shared.id, name="Shared Discord Edited").name == "Shared Discord Edited"
    with pytest.raises(PermissionError):
        platform["filters"].set_rules(
            alice.actor,
            shared.id,
            "grafana",
            {"severity": ["critical"]},
        )

    access.set_for_user(
        admin.actor,
        alice.id,
        shared.id,
        can_edit_destination=False,
        can_manage_filters=True,
    )
    with pytest.raises(PermissionError):
        destinations.update(alice.actor, shared.id, name="Still read only")
    policy = platform["filters"].set_rules(
        alice.actor,
        shared.id,
        "grafana",
        {"severity": ["critical"]},
    )
    assert policy is not None
    with pytest.raises(PermissionError):
        destinations.set_shared(alice.actor, shared.id, False)


def test_private_destination_can_select_system_route_and_manage_own_filters(access_platform):
    platform = access_platform
    admin = platform["admin"]
    alice = platform["alice"]
    private = platform["destinations"].create(
        alice.actor,
        alice.id,
        "Alice Discord",
        "discord",
        settings={},
    )
    route = platform["routes"].create(
        admin.actor,
        admin.id,
        "Zabbix system route",
        "zabbix",
        input_type="smtp",
        enabled=False,
    )

    selected = platform["relationships"].replace_for_destination(
        alice.actor,
        private.id,
        [route.id],
    )
    visible_routes, errors = platform["routes"].list_visible_safe(alice.actor)

    assert selected == (route.id,)
    assert errors == []
    visible = next(item for item in visible_routes if item.id == route.id)
    assert visible.enabled is True
    assert visible.destination_ids == (private.id,)

    policy = platform["filters"].set_rules(
        alice.actor,
        private.id,
        "zabbix",
        {"severity": ["high"]},
    )
    assert policy is not None
    with pytest.raises(PermissionError):
        platform["filters"].destination_view(admin.actor, private.id)


def test_admin_delivery_history_excludes_private_user_destination_contents(access_platform):
    platform = access_platform
    admin = platform["admin"]
    alice = platform["alice"]
    shared = platform["destinations"].create(
        admin.actor,
        admin.id,
        "Shared webhook",
        "webhook",
        settings={},
        shared=True,
    )
    private = platform["destinations"].create(
        alice.actor,
        alice.id,
        "Alice webhook",
        "webhook",
        settings={},
    )
    route = platform["routes"].create(
        admin.actor,
        admin.id,
        "Generic HTTP",
        "grafana",
        input_type="http",
    )
    notification = Notification(
        source="grafana",
        title="Private event",
        metadata={"severity": "critical", "_input_type": "http"},
    )

    platform["history"].record(
        alice.id,
        "private-delivery",
        route,
        notification,
        1,
        "delivered",
        DeliveryResult(True, response_status=204),
        destination_id=private.id,
    )
    platform["history"].record(
        admin.id,
        "shared-delivery",
        route,
        notification,
        1,
        "delivered",
        DeliveryResult(True, response_status=204),
        destination_id=shared.id,
    )

    admin_visible = platform["history"].list_visible(admin.actor)
    alice_visible = platform["history"].list_visible(alice.actor)
    assert {item.destination_id for item in admin_visible} == {shared.id}
    assert {item.destination_id for item in alice_visible} == {private.id, shared.id}


def test_system_route_choices_merge_account_copies_without_losing_assignments(access_platform):
    platform = access_platform
    routes = platform["routes"]
    destinations = platform["destinations"]
    relationships = platform["relationships"]
    admin, alice, bob = (platform[key] for key in ("admin", "alice", "bob"))
    first = routes.create(admin.actor, admin.id, "Sonarr HTTP", "sonarr", input_type="http")
    duplicate = routes.create(alice.actor, alice.id, "Sonarr HTTP", "sonarr", input_type="http")
    smtp = routes.create(admin.actor, admin.id, "Semaphore SMTP", "semaphore", input_type="smtp")
    http = routes.create(admin.actor, admin.id, "Semaphore HTTP", "semaphore", input_type="http")
    shared = destinations.create(admin.actor, admin.id, "Company Discord", "discord", settings={}, shared=True)
    private = destinations.create(alice.actor, alice.id, "Private Discord", "discord", settings={}, shared=False)
    relationships.replace_for_destination(admin.actor, shared.id, [first.id])
    relationships.replace_for_destination(alice.actor, private.id, [duplicate.id])

    choices = routes.list_visible(alice.actor)
    sonarr = [route for route in choices if route.source == "sonarr"]
    assert len(sonarr) == 1
    assert set(sonarr[0].destination_ids) == {shared.id, private.id}
    assert {route.input_type for route in choices if route.source == "semaphore"} == {"http", "smtp"}
    assert relationships.route_ids_for_destination(alice.actor, private.id) == (sonarr[0].id,)
    assert [route.destination_ids for route in routes.list_visible(bob.actor) if route.source == "sonarr"] == [(shared.id,)]

    # Saving the checked representative migrates only this destination's links.
    relationships.replace_for_destination(alice.actor, private.id, [sonarr[0].id])
    assert relationships.route_ids_for_destination(alice.actor, private.id) == (sonarr[0].id,)
    relationships.replace_for_destination(alice.actor, private.id, [])
    assert relationships.route_ids_for_destination(alice.actor, private.id) == ()
    assert relationships.route_ids_for_destination(admin.actor, shared.id) == (sonarr[0].id,)
    with platform["database"].connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM routes").fetchone()[0] == 4


def test_seeded_accounts_share_one_system_catalogue_in_selector(access_platform):
    from integrations.catalog import route_options
    from storage.default_routes import seed_default_routes

    platform = access_platform
    for key in ("admin", "alice", "bob"):
        user = platform[key]
        seed_default_routes(platform["database"], user.id, user.role)
    expected = {(item["source"], item["input_type"]) for item in route_options()}
    for key in ("admin", "alice", "bob"):
        choices = platform["routes"].list_visible(platform[key].actor)
        assert len(choices) == len(expected)
        assert {(route.source, route.input_type) for route in choices} == expected


def test_system_route_projection_batches_database_reads_across_account_copies(access_platform, monkeypatch):
    from contextlib import contextmanager
    from storage.default_routes import seed_default_routes

    platform = access_platform
    for index in range(12):
        user = platform["users"].create(f"operator-{index}", "operator secure password")
        seed_default_routes(platform["database"], user.id, user.role)
    database = platform["database"]
    original_connect = database.connect
    reads = []

    @contextmanager
    def count_connections():
        reads.append(1)
        with original_connect() as connection:
            yield connection

    monkeypatch.setattr(database, "connect", count_connections)
    choices = platform["routes"].list_visible(platform["admin"].actor)
    assert len(choices) == 25
    # Hundreds of backing records must not require hundreds of connections.
    assert len(reads) <= 6
