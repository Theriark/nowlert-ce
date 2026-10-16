"""A disabled Route stops delivery; the Destination and fallback rules stay as they were."""

from __future__ import annotations

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.destination_access import SystemRoutingRouteStore
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x42" * 16, iterations=1_000)


def setup(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator", "correct horse battery staple"
    )
    return database, admin.actor


def event(source="checkmk", input_type="http"):
    return Notification(
        source=source,
        title="Synthetic event",
        metadata={"_input_type": input_type},
    )


def test_disabled_route_is_not_matched_and_reenabling_restores_delivery(tmp_path):
    database, actor = setup(tmp_path)
    destination = DestinationStore(database).create(
        actor, actor.user_id, "Enabled Discord", "discord", settings={}, enabled=True
    )
    routes = RouteStore(database)
    route = routes.create(
        actor, actor.user_id, "Imported Checkmk", "checkmk", destination.id, input_type="http"
    )
    system = SystemRoutingRouteStore(database)
    delivery_actor = type(actor)(actor.user_id, "user")

    assert [item.id for item in system.matching(delivery_actor, actor.user_id, event())] == [route.id]

    routes.set_enabled(actor, route.id, False)
    assert system.matching(delivery_actor, actor.user_id, event()) == []

    routes.set_enabled(actor, route.id, True)
    assert [item.id for item in system.matching(delivery_actor, actor.user_id, event())] == [route.id]


def test_disabled_dedicated_route_lets_the_fallback_route_deliver(tmp_path):
    database, actor = setup(tmp_path)
    destinations = DestinationStore(database)
    fallback_destination = destinations.create(
        actor, actor.user_id, "Fallback Discord", "discord", settings={}, enabled=True
    )
    dedicated_destination = destinations.create(
        actor, actor.user_id, "Dedicated Discord", "discord", settings={}, enabled=True
    )
    routes = RouteStore(database)
    fallback = routes.create(
        actor, actor.user_id, "Fallback http", "*", fallback_destination.id,
        input_type="http", priority="lowest",
    )
    dedicated = routes.create(
        actor, actor.user_id, "Dedicated generic http", "generic_http", dedicated_destination.id,
        input_type="http", priority="normal",
    )
    routes.set_enabled(actor, dedicated.id, False)

    system = SystemRoutingRouteStore(database)
    delivery_actor = type(actor)(actor.user_id, "user")
    matched = system.matching(delivery_actor, actor.user_id, event("generic_http"))

    assert [item.id for item in matched] == [fallback.id]
