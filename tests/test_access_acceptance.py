"""Acceptance regression coverage for shared Destination and private Filtering access."""

import pytest

from api.access_acceptance import (
    AcceptanceDestinationAccessStore,
    AcceptanceDestinationStore,
)
from api.security import hash_password
from storage.database import Database
from storage.destination_access import (
    AccessControlledRouteDestinationStore,
    SystemRoutingRouteStore,
)
from storage.system_filtering import SystemDestinationFilterStore
from storage.users import UserStore


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x17" * 16, iterations=1_000)


def test_shared_destination_is_operable_while_filters_remain_owner_private(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    user = users.create("normal-user", "normal user secure password")
    access = AcceptanceDestinationAccessStore(database)
    destinations = AcceptanceDestinationStore(database, access=access)
    routes = SystemRoutingRouteStore(database)
    relationships = AccessControlledRouteDestinationStore(database, access=access)
    filters = SystemDestinationFilterStore(database, access=access)

    shared = destinations.create(
        admin.actor,
        admin.id,
        "Shared Discord",
        "discord",
        settings={},
        shared=True,
    )
    row = access.destination_row(shared.id)
    assert access.can_view(user.actor, row) is True
    assert access.can_edit_destination(user.actor, row) is True
    assert access.can_manage_filters(user.actor, row) is False

    destinations.set_enabled(user.actor, shared.id, False)
    assert destinations.get(user.actor, shared.id).enabled is False

    route = routes.create(
        admin.actor,
        admin.id,
        "Zabbix system route",
        "zabbix",
        input_type="smtp",
    )
    relationships.replace_for_destination(user.actor, shared.id, [route.id])
    with pytest.raises(PermissionError):
        filters.set_rules(
            user.actor,
            shared.id,
            "zabbix",
            {"severity": ["high"]},
        )


def test_admin_gets_private_resource_metadata_without_private_configuration(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    user = users.create("private-owner", "private owner secure password")
    access = AcceptanceDestinationAccessStore(database)
    destinations = AcceptanceDestinationStore(database, access=access)
    routes = SystemRoutingRouteStore(database)
    relationships = AccessControlledRouteDestinationStore(database, access=access)
    filters = SystemDestinationFilterStore(database, access=access)

    private = destinations.create(
        user.actor,
        user.id,
        "Private Discord",
        "discord",
        settings={},
        shared=False,
    )
    route = routes.create(
        admin.actor,
        admin.id,
        "XO system route",
        "xo",
        input_type="smtp",
    )
    relationships.replace_for_destination(user.actor, private.id, [route.id])
    filters.set_rules(
        user.actor,
        private.id,
        "xo",
        {"status": ["failure"]},
    )

    with pytest.raises(PermissionError):
        destinations.get(admin.actor, private.id)

    # Runtime delivery may resolve the private target internally, but the
    # ordinary API-visible get() path above remains denied to the administrator.
    target = destinations.for_delivery(admin.actor, private.id)
    assert target.destination.id == private.id

    destination_metadata = access.private_destination_metadata(admin.actor)
    assert destination_metadata == [
        {
            "id": private.id,
            "owner_user_id": user.id,
            "owner_username": "private-owner",
            "name": "Private Discord",
            "output_type": "discord",
            "enabled": True,
            "shared": False,
            "metadata_only": True,
        }
    ]
    assert "settings" not in destination_metadata[0]
    assert "route_ids" not in destination_metadata[0]

    filter_metadata = access.private_filter_metadata(admin.actor)
    assert filter_metadata[0]["destination_id"] == private.id
    assert filter_metadata[0]["owner_username"] == "private-owner"
    assert "sources" not in filter_metadata[0]
    assert "integrations" not in filter_metadata[0]
    assert "rules" not in filter_metadata[0]
