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
    with pytest.raises(PermissionError):
        destinations.create(
            alice.actor,
            alice.id,
            "Alice shared",
            "discord",
            settings={},
            shared=True,
        )
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
