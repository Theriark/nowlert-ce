"""System-routing fallback precedence for deliverable destinations."""

from __future__ import annotations

import pytest

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.destination_access import SystemRoutingRouteStore
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.users import UserStore


PASSWORD = "correct horse battery staple"


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\\x42" * 16, iterations=1_000)


def database_with_admin(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator",
        PASSWORD,
    )
    return database, admin.actor


def notification(source: str, input_type: str) -> Notification:
    return Notification(
        source=source,
        title="Synthetic fallback event",
        metadata={"_input_type": input_type},
    )


@pytest.mark.parametrize(
    ("source", "input_type"),
    (
        ("generic_http", "http"),
        ("redfish", "redfish"),
    ),
)
def test_disabled_dedicated_destination_does_not_suppress_fallback(
    tmp_path,
    source,
    input_type,
):
    database, actor = database_with_admin(tmp_path)
    destinations = DestinationStore(database)
    enabled = destinations.create(
        actor,
        actor.user_id,
        "Fallback Discord",
        "discord",
        settings={},
        enabled=True,
    )
    disabled = destinations.create(
        actor,
        actor.user_id,
        "Disabled dedicated Discord",
        "discord",
        settings={},
        enabled=False,
    )
    routes = RouteStore(database)
    fallback = routes.create(
        actor,
        actor.user_id,
        f"Fallback {input_type}",
        "*",
        enabled.id,
        input_type=input_type,
        priority="lowest",
    )
    routes.create(
        actor,
        actor.user_id,
        f"Dedicated {source}",
        source,
        disabled.id,
        input_type=input_type,
        priority="normal",
    )

    system_routes = SystemRoutingRouteStore(database)
    delivery_actor = type(actor)(actor.user_id, "user")
    matched = system_routes.matching(
        delivery_actor,
        actor.user_id,
        notification(source, input_type),
    )

    assert [route.id for route in matched] == [fallback.id]
    assert matched[0].destination_ids == (enabled.id,)


@pytest.mark.parametrize(
    ("source", "input_type"),
    (
        ("generic_http", "http"),
        ("redfish", "redfish"),
    ),
)
def test_enabled_dedicated_destination_still_wins_before_fallback(
    tmp_path,
    source,
    input_type,
):
    database, actor = database_with_admin(tmp_path)
    destination = DestinationStore(database).create(
        actor,
        actor.user_id,
        "Discord",
        "discord",
        settings={},
        enabled=True,
    )
    routes = RouteStore(database)
    routes.create(
        actor,
        actor.user_id,
        f"Fallback {input_type}",
        "*",
        destination.id,
        input_type=input_type,
        priority="lowest",
    )
    dedicated = routes.create(
        actor,
        actor.user_id,
        f"Dedicated {source}",
        source,
        destination.id,
        input_type=input_type,
        priority="normal",
    )

    system_routes = SystemRoutingRouteStore(database)
    delivery_actor = type(actor)(actor.user_id, "user")
    matched = system_routes.matching(
        delivery_actor,
        actor.user_id,
        notification(source, input_type),
    )

    assert [route.id for route in matched] == [dedicated.id]
    assert matched[0].destination_ids == (destination.id,)
