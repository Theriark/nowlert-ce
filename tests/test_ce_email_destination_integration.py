"""CE integration coverage for outbound Email destinations and Email Alerts routes."""

from __future__ import annotations

from integrations.catalog import route_options
from storage.database import Database
from storage.destination_access import SystemRoutingRouteStore
from storage.users import UserStore
from test_route_destination_api import api, call, fast_hash, login


EMAIL_SETTINGS = {
    "server": "smtp.example.com",
    "port": 587,
    "security": "starttls",
    "from_address": "alerts@example.com",
    "to": ["noc@example.com"],
}


def test_managed_route_matrix_reconciles_email_alerts_with_clean_name(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin(
        "administrator",
        "correct horse battery staple",
    )
    routes = SystemRoutingRouteStore(database)

    for index, option in enumerate(route_options()):
        pair = (option["source"], option["input_type"])
        if pair == ("email", "email"):
            continue
        routes.create(
            admin.actor,
            admin.id,
            f"{option['label']} managed {index}",
            option["source"],
            input_type=option["input_type"],
            priority=100,
            enabled=True,
        )

    visible, errors = routes.list_visible_safe(admin.actor)
    assert errors == []
    email_route = next(
        item
        for item in visible
        if (item.source, item.input_type) == ("email", "email")
    )
    assert email_route.name == "Email Alerts"

    with database.transaction() as connection:
        connection.execute(
            """
            UPDATE routes
            SET name = ?, name_normalized = ?
            WHERE id = ?
            """,
            (
                "Email Alerts Email Alerts",
                "email alerts email alerts",
                email_route.id,
            ),
        )

    reconciled, errors = routes.list_visible_safe(admin.actor)
    assert errors == []
    email_route = next(
        item
        for item in reconciled
        if (item.source, item.input_type) == ("email", "email")
    )
    assert email_route.name == "Email Alerts"


def test_email_destination_is_assignable_filterable_and_visible_in_routing_flow(api):
    headers = login(api)

    route_response = call(
        api,
        "POST",
        "/api/v2/routes",
        {
            "name": "Email Alerts",
            "source": "email",
            "input_type": "email",
            "priority": "normal",
            "enabled": True,
        },
        headers,
    )
    assert route_response.status == 201
    route = route_response.payload["route"]
    assert route["source"] == "email"
    assert route["input_type"] == "email"

    destination_response = call(
        api,
        "POST",
        "/api/v2/destinations",
        {
            "name": "Operations email",
            "output_type": "email",
            "settings": EMAIL_SETTINGS,
            "route_ids": [route["id"]],
            "enabled": True,
        },
        headers,
    )
    assert destination_response.status == 201
    destination = destination_response.payload["destination"]
    assert destination["output_type"] == "email"
    assert destination["route_ids"] == [route["id"]]
    assert destination["secret_configured"] is False

    routes = call(api, "GET", "/api/v2/routes", headers=headers).payload["routes"]
    managed = next(item for item in routes if item["id"] == route["id"])
    assert managed["destination_ids"] == [destination["id"]]
    assert managed["destination_count"] == 1

    overview = call(api, "GET", "/api/v2/filters", headers=headers)
    assert overview.status == 200
    choice = next(
        item
        for item in overview.payload["destinations"]
        if item["id"] == destination["id"]
    )
    assert choice["output_type"] == "email"
    assert choice["available_integration_count"] == 1

    detail = call(
        api,
        "GET",
        f"/api/v2/filters/destinations/{destination['id']}",
        headers=headers,
    )
    assert detail.status == 200
    email_filter = next(
        item
        for item in detail.payload["integrations"]
        if item["source"] == "email"
    )
    assert email_filter["name"] == "Email Alerts"

    configured = call(
        api,
        "PUT",
        f"/api/v2/filters/destinations/{destination['id']}/sources/email",
        {
            "rules": {
                "sender_domain": ["monitoring.example.com"],
                "severity": ["critical"],
            },
            "enabled": True,
        },
        headers,
    )
    assert configured.status == 200
    assert configured.payload["integration"]["configured"] is True
    assert configured.payload["integration"]["filter_enabled"] is True

    flow = call(
        api,
        "GET",
        "/api/v2/routing-flow/15m",
        headers=headers,
    )
    assert flow.status == 200
    flow_route = next(item for item in flow.payload["routes"] if item["id"] == route["id"])
    flow_destination = next(
        item
        for item in flow.payload["destinations"]
        if item["id"] == destination["id"]
    )
    flow_filter = next(
        item
        for item in flow.payload["filters"]
        if item["destination_id"] == destination["id"]
    )
    assert flow_route["source"] == "email"
    assert flow_route["input_type"] == "email"
    assert flow_destination["output_type"] == "email"
    assert flow_filter["sources"] == ["email"]


def test_ce_email_credentials_are_enforced_for_private_create_and_patch(api):
    headers = login(api)
    platform = api["service"].platform
    owner = platform.users.create(
        "email-private-owner",
        "owner private secure password",
    )
    authenticated_settings = {
        **EMAIL_SETTINGS,
        "username": "alerts@example.com",
    }

    missing_private_password = call(
        api,
        "POST",
        "/api/v2/destinations",
        {
            "owner_user_id": owner.id,
            "name": "Private authenticated email",
            "output_type": "email",
            "settings": authenticated_settings,
            "shared": False,
            "enabled": True,
        },
        headers,
    )
    assert missing_private_password.status == 400
    assert "password is required" in missing_private_password.payload["error"]

    private_created = call(
        api,
        "POST",
        "/api/v2/destinations",
        {
            "owner_user_id": owner.id,
            "name": "Private authenticated email",
            "output_type": "email",
            "settings": authenticated_settings,
            "secret": {"password": "private-smtp-password"},
            "shared": False,
            "enabled": True,
        },
        headers,
    )
    assert private_created.status == 201
    assert private_created.payload["destination"]["secret_configured"] is True

    relay = call(
        api,
        "POST",
        "/api/v2/destinations",
        {
            "name": "Admin SMTP relay",
            "output_type": "email",
            "settings": EMAIL_SETTINGS,
            "enabled": True,
        },
        headers,
    )
    assert relay.status == 201
    relay_id = relay.payload["destination"]["id"]
    assert relay.payload["destination"]["secret_configured"] is False

    missing_patch_password = call(
        api,
        "PATCH",
        f"/api/v2/destinations/{relay_id}",
        {"settings": authenticated_settings},
        headers,
    )
    assert missing_patch_password.status == 400
    assert "password is required" in missing_patch_password.payload["error"]

    patched = call(
        api,
        "PATCH",
        f"/api/v2/destinations/{relay_id}",
        {
            "settings": authenticated_settings,
            "secret": {"password": "private-smtp-password"},
        },
        headers,
    )
    assert patched.status == 200
    assert patched.payload["destination"]["secret_configured"] is True
