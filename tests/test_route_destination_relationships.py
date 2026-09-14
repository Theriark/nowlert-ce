"""Independent-route and many-to-many destination relationship acceptance tests."""

from __future__ import annotations

import pytest

from api.security import hash_password
from models import Notification
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult, PlatformDeliveryService
from storage.destinations import DestinationStore
from storage.migrations import MIGRATIONS
from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0c" * 16, iterations=1_000)


@pytest.fixture
def platform(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    another = users.create("another-user", "another secure password")
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    relationships = RouteDestinationStore(database)
    return {
        "database": database,
        "admin": admin,
        "owner": owner,
        "another": another,
        "destinations": destinations,
        "routes": routes,
        "relationships": relationships,
    }


def schema_11_database(path):
    database = Database(path)
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at INTEGER NOT NULL DEFAULT (unixepoch())
            )
            """
        )
        for version, name, statements in MIGRATIONS:
            if version > 11:
                break
            for statement in statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                (version, name),
            )
            connection.execute(f"PRAGMA user_version = {version}")
        connection.commit()
    return database


def test_schema_11_to_12_preserves_topology_history_and_filters(tmp_path):
    database = schema_11_database(tmp_path / "state" / "nowlert.db")
    user_id = "1" * 32
    destination_id = "2" * 32
    route_id = "3" * 32
    attempt_id = "4" * 32
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users(
                id, username, username_normalized, password_hash,
                role, enabled, created_at, updated_at
            ) VALUES (?, 'owner', 'owner', 'hash', 'user', 1, 10, 10)
            """,
            (user_id,),
        )
        connection.execute(
            """
            INSERT INTO destinations(
                id, owner_user_id, name, name_normalized, output_type,
                settings_json, shared, enabled, created_at, updated_at
            ) VALUES (?, ?, 'Discord', 'discord', 'discord', '{}', 0, 1, 11, 11)
            """,
            (destination_id, user_id),
        )
        connection.execute(
            """
            INSERT INTO routes(
                id, owner_user_id, destination_id, name, name_normalized,
                source, filters_json, priority, enabled, created_at, updated_at,
                input_type
            ) VALUES (?, ?, ?, 'XO', 'xo', 'xen_orchestra', '{}', 25, 1, 12, 12, 'http')
            """,
            (route_id, user_id, destination_id),
        )
        connection.execute(
            """
            INSERT INTO delivery_attempts(
                id, delivery_id, owner_user_id, route_id, destination_id,
                source, title, severity, outcome, attempt_number, retryable,
                created_at, completed_at, input_type, device_name,
                event_name, event_description, event_status
            ) VALUES (?, 'delivery-1', ?, ?, ?, 'xen_orchestra', 'Test',
                      'warning', 'delivered', 1, 0, 13, 13, 'http', 'host',
                      'event', 'description', 'active')
            """,
            (attempt_id, user_id, route_id, destination_id),
        )
        connection.execute(
            """
            INSERT INTO destination_filters(
                destination_id, source, clauses_json, created_at, updated_at
            ) VALUES (?, 'xen_orchestra', '[{"statuses":["failure"]}]', 14, 14)
            """,
            (destination_id,),
        )

    assert database.migrate() == 12

    with database.connect() as connection:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(routes)")
        }
        assert "destination_id" not in columns
        binding = connection.execute(
            "SELECT route_id, destination_id FROM route_destinations"
        ).fetchone()
        assert (binding["route_id"], binding["destination_id"]) == (
            route_id,
            destination_id,
        )
        attempt = connection.execute(
            "SELECT id, route_id, destination_id FROM delivery_attempts"
        ).fetchone()
        assert (attempt["id"], attempt["route_id"], attempt["destination_id"]) == (
            attempt_id,
            route_id,
            destination_id,
        )
        policy = connection.execute(
            "SELECT clauses_json FROM destination_filters WHERE destination_id = ?",
            (destination_id,),
        ).fetchone()
        assert policy["clauses_json"] == '[{"statuses":["failure"]}]'
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_route_can_exist_without_destination(platform):
    owner = platform["owner"]
    route = platform["routes"].create(
        owner.actor,
        owner.id,
        "Reusable Grafana",
        "grafana",
        input_type="http",
    )

    assert route.destination_ids == ()
    assert platform["relationships"].destination_ids_for_route(owner.actor, route.id) == ()


def test_destination_can_select_multiple_routes(platform):
    owner = platform["owner"]
    destination = platform["destinations"].create(
        owner.actor, owner.id, "Discord", "discord", settings={"channel_name": "alerts"}
    )
    route_a = platform["routes"].create(owner.actor, owner.id, "Grafana", "grafana")
    route_b = platform["routes"].create(owner.actor, owner.id, "Zabbix", "zabbix")

    selected = platform["relationships"].replace_for_destination(
        owner.actor, destination.id, [route_a.id, route_b.id]
    )

    assert selected == (route_a.id, route_b.id)
    assert platform["relationships"].route_ids_for_destination(
        owner.actor, destination.id
    ) == (route_a.id, route_b.id)


def test_one_route_can_feed_multiple_destinations(platform):
    owner = platform["owner"]
    route = platform["routes"].create(owner.actor, owner.id, "Grafana", "grafana")
    first = platform["destinations"].create(owner.actor, owner.id, "First", "ntfy")
    second = platform["destinations"].create(owner.actor, owner.id, "Second", "ntfy")

    platform["relationships"].replace_for_destination(owner.actor, first.id, [route.id])
    platform["relationships"].replace_for_destination(owner.actor, second.id, [route.id])

    assert platform["relationships"].destination_ids_for_route(owner.actor, route.id) == (
        first.id,
        second.id,
    )


def test_assignment_replacement_is_atomic(platform):
    owner = platform["owner"]
    destination = platform["destinations"].create(owner.actor, owner.id, "Target", "ntfy")
    route = platform["routes"].create(owner.actor, owner.id, "Grafana", "grafana")
    platform["relationships"].replace_for_destination(owner.actor, destination.id, [route.id])

    with pytest.raises(KeyError, match="route not found"):
        platform["relationships"].replace_for_destination(
            owner.actor, destination.id, ["0" * 32]
        )

    assert platform["relationships"].route_ids_for_destination(
        owner.actor, destination.id
    ) == (route.id,)


def test_private_foreign_destination_cannot_bind_route(platform):
    owner = platform["owner"]
    another = platform["another"]
    route = platform["routes"].create(owner.actor, owner.id, "Owner route", "grafana")
    destination = platform["destinations"].create(
        another.actor, another.id, "Private", "ntfy", shared=False
    )

    with pytest.raises(PermissionError):
        platform["relationships"].replace_for_destination(
            platform["admin"].actor, destination.id, [route.id]
        )


def test_expand_deduplicates_destination_by_route_order(platform):
    owner = platform["owner"]
    destination = platform["destinations"].create(owner.actor, owner.id, "Target", "ntfy")
    first = platform["routes"].create(
        owner.actor, owner.id, "First", "grafana", priority=10
    )
    second = platform["routes"].create(
        owner.actor, owner.id, "Second", "grafana", priority=50
    )
    platform["relationships"].replace_for_destination(
        owner.actor, destination.id, [first.id, second.id]
    )

    candidates = platform["relationships"].expand(owner.actor, [first, second])

    assert len(candidates) == 1
    assert candidates[0].route.id == first.id
    assert candidates[0].destination_id == destination.id


def test_one_route_delivers_once_to_each_bound_destination(platform):
    owner = platform["owner"]
    route = platform["routes"].create(owner.actor, owner.id, "Grafana", "grafana")
    first = platform["destinations"].create(owner.actor, owner.id, "First", "ntfy")
    second = platform["destinations"].create(owner.actor, owner.id, "Second", "ntfy")
    platform["relationships"].replace_for_destination(owner.actor, first.id, [route.id])
    platform["relationships"].replace_for_destination(owner.actor, second.id, [route.id])
    history = DeliveryHistoryStore(platform["database"])
    calls = []
    service = PlatformDeliveryService(
        platform["routes"],
        platform["destinations"],
        SecretStore(platform["database"]),
        history,
        {"ntfy": lambda target, *_args: calls.append(target.id) or DeliveryResult(True)},
        relationships=platform["relationships"],
    )

    summary = service.deliver(owner.actor, Notification(source="grafana", title="Test"))

    assert summary.matched_routes == 2
    assert summary.delivered == 2
    assert set(calls) == {first.id, second.id}
    assert {item.destination_id for item in history.list_visible(owner.actor)} == {
        first.id,
        second.id,
    }


def test_deleting_destination_leaves_route_intact(platform):
    owner = platform["owner"]
    route = platform["routes"].create(owner.actor, owner.id, "Grafana", "grafana")
    destination = platform["destinations"].create(owner.actor, owner.id, "Target", "ntfy")
    platform["relationships"].replace_for_destination(owner.actor, destination.id, [route.id])

    platform["destinations"].delete(owner.actor, destination.id)

    assert platform["routes"].get(owner.actor, route.id).id == route.id
    assert platform["relationships"].destination_ids_for_route(owner.actor, route.id) == ()


def test_schema_12_has_independent_routes_and_relationship_table(platform):
    with platform["database"].connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
        route_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(routes)").fetchall()
        }
        assert "destination_id" not in route_columns
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert "route_destinations" in tables
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
