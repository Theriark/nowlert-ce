"""Regression coverage for preserving filters when Destination integrations are removed."""

from api.security import hash_password
from storage.database import Database
from storage.destination_access import (
    AccessControlledDestinationStore,
    AccessControlledRouteDestinationStore,
    DestinationAccessStore,
    SystemRoutingRouteStore,
)
from storage.system_filtering import SystemDestinationFilterStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0f" * 16, iterations=1_000)


def test_removing_last_route_disables_filter_without_deleting_rules(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    owner = users.create("owner-user", "owner secure password")
    access = DestinationAccessStore(database)
    destinations = AccessControlledDestinationStore(database, access=access)
    routes = SystemRoutingRouteStore(database)
    relationships = AccessControlledRouteDestinationStore(database, access=access)
    filters = SystemDestinationFilterStore(database, access=access)

    destination = destinations.create(
        owner.actor,
        owner.id,
        "Owner Discord",
        "discord",
        settings={},
        shared=False,
    )
    route = routes.create(
        admin.actor,
        admin.id,
        "Zabbix system route",
        "zabbix",
        input_type="smtp",
    )
    relationships.replace_for_destination(owner.actor, destination.id, [route.id])
    filters.set_rules(
        owner.actor,
        destination.id,
        "zabbix",
        {"severity": ["high"]},
    )
    assert filters.filter_enabled(destination.id, "zabbix") is True

    relationships.replace_for_destination(owner.actor, destination.id, [])

    with database.connect() as connection:
        stored = connection.execute(
            "SELECT clauses_json FROM destination_filters "
            "WHERE destination_id = ? AND source = 'zabbix'",
            (destination.id,),
        ).fetchone()
    assert stored is not None
    assert filters.filter_enabled(destination.id, "zabbix") is False

    relationships.replace_for_destination(owner.actor, destination.id, [route.id])
    view = filters.destination_view(owner.actor, destination.id)
    zabbix = next(item for item in view["integrations"] if item["source"] == "zabbix")
    assert zabbix["configured"] is True
    assert zabbix["filter_enabled"] is False
    assert zabbix["rules"] == {"severity": ["high"]}
