"""Imports must use the runtime's owner-private destination access policy."""
from dataclasses import replace

import pytest

from api.access_acceptance import AcceptanceDestinationAccessStore, AcceptanceDestinationStore, AcceptanceRouteDestinationStore
from api.security import hash_password
from storage.database import Database
from storage.portability import PlatformPortabilityService
from storage.users import UserStore


@pytest.fixture
def runtime(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=lambda p: hash_password(p, salt=b"\x18" * 16, iterations=1000))
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner", "owner secure password")
    service = PlatformPortabilityService(database)
    access = AcceptanceDestinationAccessStore(database)
    service.destinations = AcceptanceDestinationStore(database, access=access)
    service.relationships = AcceptanceRouteDestinationStore(database, access=access)
    document = {"schema": "nowlert.platform.v2", "destinations": [], "routes": []}
    for index, (user, shared) in enumerate(((admin, False), (owner, True), (owner, False))):
        document["destinations"].append({
            "ref": f"d{index}", "owner": user.username, "name": f"Imported destination {index}",
            "output_type": "webhook", "settings": {"method": "POST", "allow_private_network": True},
            "shared": shared, "enabled": True, "secret_required": True, "route_refs": [f"r{index}"],
            "filters": [{"source": "grafana", "policy": {"version": 2, "rules": []}, "enabled": False}],
            "filtering_enabled": False,
        })
        document["routes"].append({"ref": f"r{index}", "owner": user.username, "name": f"Imported route {index}",
                                   "source": "grafana", "input_type": "http", "priority": 50, "enabled": True})
    return database, service, admin, owner, document


def counts(database):
    with database.connect() as connection:
        return {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("destinations", "routes", "route_destinations", "secret_records", "destination_filters")}


def test_multi_owner_import_preserves_relationships_and_private_access(runtime):
    database, service, admin, owner, document = runtime
    plan = service.preview_document(admin.actor, document)
    assert plan.valid, plan.errors
    result = service.apply_document(admin.actor, document, plan.fingerprint)
    assert result["destinations_created"] == result["routes_created"] == result["filters_created"] == 3
    assert counts(database) == {"destinations": 3, "routes": 3, "route_destinations": 3, "secret_records": 0, "destination_filters": 3}
    own = service.destinations.list_visible(owner.actor)
    private = next(item for item in own if not item.shared)
    assert private.enabled is False and private.secret_configured is False
    with pytest.raises(PermissionError):
        service.destinations.get(admin.actor, private.id)
    with pytest.raises(PermissionError):
        service.destinations.set_enabled(admin.actor, private.id, True)


def test_import_remains_admin_only(runtime):
    database, service, admin, owner, document = runtime
    plan = service.preview_document(admin.actor, document)
    with pytest.raises(PermissionError):
        service.apply_document(owner.actor, document, plan.fingerprint)
    assert not any(counts(database).values())


@pytest.mark.parametrize("failure_call", [1, 3])
def test_late_import_failure_removes_all_owners_resources_and_secret_files(runtime, monkeypatch, failure_call):
    database, service, admin, _owner, document = runtime
    plan = service.preview_document(admin.actor, document)
    # Local YAML migration plans can carry credentials; exercise their shared apply/cleanup path too.
    plan = replace(plan, destinations=tuple({**item, "secret_value": b"qa-only-import-secret"} for item in plan.destinations))
    before_files = {str(path) for path in database.path.parent.rglob("*") if path.is_file()}
    install = service._install_portable_filters
    calls = 0
    def fail_late(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise RuntimeError("injected late import failure")
        return install(*args, **kwargs)
    monkeypatch.setattr(service, "_install_portable_filters", fail_late)
    with pytest.raises(RuntimeError, match="injected late import failure"):
        service._apply(admin.actor, plan, plan.fingerprint)
    assert not any(counts(database).values())
    assert {str(path) for path in database.path.parent.rglob("*") if path.is_file()} == before_files
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM settings_records WHERE namespace LIKE 'destination_filter_%'").fetchone()[0] == 0


def test_local_migration_resource_rollback_uses_destination_owner(runtime):
    database, service, admin, owner, document = runtime
    plan = service.preview_document(admin.actor, document)
    plan = replace(plan, destinations=tuple({**item, "secret_value": b"qa-only-migration-secret"} for item in plan.destinations))
    result = service._apply_plan(admin.actor, plan, include_resources=True)
    with pytest.raises(PermissionError):
        service.rollback_resources(owner.actor, result["resources"])
    assert counts(database)["destinations"] == 3
    service.rollback_resources(admin.actor, result["resources"])
    assert not any(counts(database).values())
    assert not list(service.secrets.directory.glob("*.v*"))
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM settings_records WHERE namespace LIKE 'destination_filter_%'").fetchone()[0] == 0
