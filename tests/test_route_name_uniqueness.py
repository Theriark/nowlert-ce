"""Route names are unique across all accounts for every writer."""

from __future__ import annotations

import pytest

from api.security import hash_password
from storage.database import Database
from storage.default_routes import seed_default_routes
from storage.routes import RouteStore, available_route_name, deduplicate_route_names
from storage.users import UserStore
from storage.validation import ConflictError


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x09" * 16, iterations=1_000)


@pytest.fixture()
def accounts(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    alice = users.create("alice-user", "alice secure password", role="user")
    bob = users.create("bob-user", "bob secure password", role="user")
    return database, admin, alice, bob


def insert_route(database, route_id, owner_id, name, created_at, source="grafana"):
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO routes(
                id, owner_user_id, name, name_normalized, source,
                input_type, filters_json, priority, enabled,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'http', '{}', 50, 1, ?, ?)
            """,
            (route_id, owner_id, name, name.casefold(), source, created_at, created_at),
        )


def names(database):
    with database.connect() as connection:
        return [
            str(row["name"])
            for row in connection.execute("SELECT name FROM routes ORDER BY created_at, id")
        ]


def test_route_store_refuses_a_name_another_account_uses(accounts):
    database, admin, alice, _bob = accounts
    routes = RouteStore(database)
    routes.create(admin.actor, admin.id, "Core switches", "grafana", input_type="http")

    with pytest.raises(ConflictError) as error:
        routes.create(alice.actor, alice.id, "CORE switches", "zabbix", input_type="http")

    assert str(error.value) == "A route named CORE switches already exists. Choose another name."
    assert names(database) == ["Core switches"]


def test_route_store_rename_refuses_a_duplicate_but_keeps_its_own_name(accounts):
    database, admin, alice, _bob = accounts
    routes = RouteStore(database)
    routes.create(admin.actor, admin.id, "Core switches", "grafana", input_type="http")
    edge = routes.create(alice.actor, alice.id, "Edge routers", "zabbix", input_type="http")

    with pytest.raises(ConflictError):
        routes.update(alice.actor, edge.id, name="core switches")

    assert routes.update(alice.actor, edge.id, priority=10).name == "Edge routers"
    assert routes.update(alice.actor, edge.id, name="EDGE routers").name == "EDGE routers"


def test_each_account_keeps_its_own_editable_seeded_routes_with_unique_names(accounts):
    database, admin, alice, bob = accounts

    seed_default_routes(database, admin.id, admin.role)
    seed_default_routes(database, alice.id, alice.role)
    seed_default_routes(database, bob.id, bob.role)

    every_name = [name.casefold() for name in names(database)]
    assert len(every_name) == len(set(every_name))
    routes = RouteStore(database)
    alice_names = {item.name for item in routes.list_for_owner(alice.actor, alice.id)}
    bob_names = {item.name for item in routes.list_for_owner(bob.actor, bob.id)}
    assert "Checkmk HTTP" in {
        item.name for item in routes.list_for_owner(admin.actor, admin.id)
    }
    assert "Checkmk HTTP (2)" in alice_names
    assert "Checkmk HTTP (3)" in bob_names

    copy = next(
        item for item in routes.list_for_owner(alice.actor, alice.id)
        if item.name == "Checkmk HTTP (2)"
    )
    renamed = routes.update(alice.actor, copy.id, name="Alice Checkmk", priority=10)
    assert (renamed.name, renamed.priority) == ("Alice Checkmk", 10)


def test_startup_cleanup_renames_later_duplicates_and_is_idempotent(accounts):
    database, admin, alice, bob = accounts
    insert_route(database, "r1", admin.id, "Checkmk HTTP", 100)
    insert_route(database, "r2", alice.id, "checkmk http", 200)
    insert_route(database, "r3", bob.id, "Checkmk HTTP", 300)
    insert_route(database, "r4", bob.id, "Checkmk HTTP (2)", 50)
    insert_route(database, "r5", alice.id, "Unique route", 400)

    renamed = deduplicate_route_names(database, clock=lambda: 1000)

    assert [(item["id"], item["to"]) for item in renamed] == [
        ("r2", "checkmk http (3)"),
        ("r3", "Checkmk HTTP (4)"),
    ]
    with database.connect() as connection:
        rows = {
            str(row["id"]): (str(row["owner_user_id"]), str(row["name"]))
            for row in connection.execute("SELECT id, owner_user_id, name FROM routes")
        }
    assert rows == {
        "r1": (admin.id, "Checkmk HTTP"),
        "r2": (alice.id, "checkmk http (3)"),
        "r3": (bob.id, "Checkmk HTTP (4)"),
        "r4": (bob.id, "Checkmk HTTP (2)"),
        "r5": (alice.id, "Unique route"),
    }
    assert deduplicate_route_names(database) == []
    assert RouteStore(database).update(alice.actor, "r2", name="Alice Checkmk").name == "Alice Checkmk"


def test_available_route_name_keeps_the_limit_and_skips_taken_numbers(accounts):
    database, *_users = accounts
    long_name = "x" * 128
    with database.connect() as connection:
        assert available_route_name(connection, "Free name") == ("Free name", "free name")
        display, normalized = available_route_name(
            connection, long_name, taken={long_name, long_name[:124] + " (2)"}
        )
    assert display == "x" * 124 + " (3)"
    assert len(display) == 128
    assert normalized == display
