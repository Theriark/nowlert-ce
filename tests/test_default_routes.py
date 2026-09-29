"""Shipped default route definitions for fresh platform accounts."""

from __future__ import annotations

from api.security import hash_password
from integrations.catalog import route_options
from storage.bootstrap import BootstrapStore
from storage.database import Database
from storage.routes import RouteStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x08" * 16, iterations=1_000)


def test_bootstrap_admin_receives_shipped_route_catalog(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    bootstrap = BootstrapStore(
        database,
        users=UserStore(database, password_hasher=fast_hash),
        token_factory=lambda _size: "first-setup-token",
    )
    bootstrap.rotate_for_startup()

    admin = bootstrap.consume(
        "first-setup-token",
        "administrator",
        "correct horse battery staple",
    )
    routes = RouteStore(database).list_visible(admin.actor)

    expected = {(item["source"], item["input_type"]) for item in route_options()}
    assert {(item.source, item.input_type) for item in routes} == expected
    assert len(routes) == len(expected) == 22
    assert all(not item.destination_ids for item in routes)
    assert all(item.enabled for item in routes)


def test_default_routes_are_seeded_once_and_not_restored_after_deletion(tmp_path):
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator",
        "correct horse battery staple",
    )

    assert seed_default_routes(database, admin.id, admin.role) == 22
    assert seed_default_routes(database, admin.id, admin.role) == 0
    with database.transaction() as connection:
        connection.execute("DELETE FROM routes WHERE owner_user_id = ?", (admin.id,))

    assert seed_default_routes(database, admin.id, admin.role) == 0
    assert RouteStore(database).list_visible(admin.actor) == []


def test_existing_empty_accounts_are_seeded_on_upgrade_but_existing_routes_are_preserved(tmp_path):
    from storage.default_routes import seed_missing_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    empty = users.bootstrap_admin("administrator", "correct horse battery staple")
    populated = users.create("operator-user", "operator secure password")
    RouteStore(database).create(
        populated.actor,
        populated.id,
        "Custom",
        "grafana",
        input_type="http",
    )

    created = seed_missing_default_routes(database)
    assert created == 22
    assert len(RouteStore(database).list_for_owner(empty.actor, empty.id)) == 22
    assert [item.name for item in RouteStore(database).list_for_owner(populated.actor, populated.id)] == ["Custom"]


def test_regular_user_receives_assignable_integration_routes_without_admin_fallbacks(tmp_path):
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    users.bootstrap_admin("administrator", "correct horse battery staple")
    regular = users.create("operator-user", "operator secure password", role="user")

    assert seed_default_routes(database, regular.id, regular.role) == 19
    routes = RouteStore(database).list_for_owner(regular.actor, regular.id)
    expected = {
        (item["source"], item["input_type"])
        for item in route_options()
        if item["source"] != "*"
    }
    assert {(item.source, item.input_type) for item in routes} == expected
