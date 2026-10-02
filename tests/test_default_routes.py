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
    assert len(routes) == len(expected) == 28
    assert all(not item.destination_ids for item in routes)
    assert all(item.enabled for item in routes)


def test_upgrade_adds_only_new_application_routes_and_preserves_existing_state(tmp_path):
    import json
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator", "correct horse battery staple"
    )
    original = RouteStore(database).create(owner.actor, owner.id, "Custom Grafana", "grafana", input_type="http", enabled=False)
    existing_sonarr = RouteStore(database).create(owner.actor, owner.id, "My Sonarr", "sonarr", input_type="http")
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO settings_records(namespace, setting_key, value_json, updated_at) VALUES (?, ?, ?, ?)",
            ("platform.default_routes", owner.id, json.dumps({"version": 1}), 1),
        )
    assert seed_default_routes(database, owner.id, owner.role) == 5
    routes = RouteStore(database).list_for_owner(owner.actor, owner.id)
    assert len(routes) == 7
    preserved = next(item for item in routes if item.id == original.id)
    assert not preserved.enabled and preserved.name == "Custom Grafana"
    assert [item.id for item in routes if item.source == "sonarr"] == [existing_sonarr.id]
    assert not any(item.source == "*" for item in routes)
    assert seed_default_routes(database, owner.id, owner.role) == 0


def test_default_routes_are_seeded_once_and_not_restored_after_deletion(tmp_path):
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator",
        "correct horse battery staple",
    )

    assert seed_default_routes(database, admin.id, admin.role) == 28
    assert seed_default_routes(database, admin.id, admin.role) == 0
    with database.transaction() as connection:
        connection.execute("DELETE FROM routes WHERE owner_user_id = ?", (admin.id,))

    assert seed_default_routes(database, admin.id, admin.role) == 0
    assert RouteStore(database).list_visible(admin.actor) == []


def test_upgrade_does_not_restore_old_routes_deleted_before_upgrade(tmp_path):
    import json
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    owner = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator", "correct horse battery staple"
    )
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO settings_records(namespace, setting_key, value_json, updated_at) VALUES (?, ?, ?, ?)",
            ("platform.default_routes", owner.id, json.dumps({"version": 1}), 1),
        )
    assert seed_default_routes(database, owner.id, owner.role) == 6
    assert {route.source for route in RouteStore(database).list_visible(owner.actor)} == {
        "semaphore", "sonarr", "radarr", "metabase", "github_actions"
    }
    assert seed_default_routes(database, owner.id, owner.role) == 0


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
    assert created == 28
    assert len(RouteStore(database).list_for_owner(empty.actor, empty.id)) == 28
    assert [item.name for item in RouteStore(database).list_for_owner(populated.actor, populated.id)] == ["Custom"]


def test_regular_user_receives_assignable_integration_routes_without_admin_fallbacks(tmp_path):
    from storage.default_routes import seed_default_routes

    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    users.bootstrap_admin("administrator", "correct horse battery staple")
    regular = users.create("operator-user", "operator secure password", role="user")

    assert seed_default_routes(database, regular.id, regular.role) == 25
    routes = RouteStore(database).list_for_owner(regular.actor, regular.id)
    expected = {
        (item["source"], item["input_type"])
        for item in route_options()
        if item["source"] != "*"
    }
    assert {(item.source, item.input_type) for item in routes} == expected
