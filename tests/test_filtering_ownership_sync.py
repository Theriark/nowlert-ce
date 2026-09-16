"""Acceptance for owner-private Filtering status, sharing, and Routing Flow sync."""

from __future__ import annotations

import json

from models import Notification
from test_route_destination_api import api, call, create_destination, create_route, login


USER_PASSWORD = "owner private secure password"


def login_as(api, username: str, password: str):
    response = call(
        api,
        "POST",
        "/api/v2/session",
        {"username": username, "password": password},
    )
    assert response.status == 200
    cookies = [value for name, value in response.headers if name == "Set-Cookie"]
    session = next(item.split(";", 1)[0] for item in cookies if "session=" in item)
    return {"Cookie": session, "X-CSRF-Token": response.payload["csrf_token"]}


def configure_zabbix_filter(platform, actor, destination_id: str):
    return platform.filters.set_rules(
        actor,
        destination_id,
        "zabbix",
        {
            "policy": [
                {
                    "action": "allow",
                    "conditions": {"severity": ["high", "disaster"]},
                }
            ]
        },
    )


def test_destination_master_filter_switch_preserves_saved_integration_state(api):
    headers = login(api)
    route = create_route(api, headers, "Zabbix HTTP", source="zabbix")
    destination = create_destination(api, headers, "Operations", [route["id"]])
    platform = api["service"].platform
    configure_zabbix_filter(platform, api["admin"].actor, destination["id"])

    rejected = Notification(source="zabbix", metadata={"severity": "information"})
    assert not platform.filters.matches(api["admin"].actor, destination["id"], rejected)
    assert platform.filters.filter_enabled(destination["id"], "zabbix") is True

    disabled = call(
        api,
        "PUT",
        f'/api/v2/filters/destinations/{destination["id"]}/enabled',
        {"enabled": False},
        headers,
    )
    assert disabled.status == 200
    assert disabled.payload["enabled"] is False
    assert platform.filters.filter_enabled(destination["id"], "zabbix") is True
    assert platform.filters.matches(api["admin"].actor, destination["id"], rejected)

    overview = call(api, "GET", "/api/v2/filters", headers=headers).payload
    policy = next(item for item in overview["filters"] if item["destination_id"] == destination["id"])
    assert policy["filtering_enabled"] is False
    assert policy["configured_count"] == 1
    assert policy["active_count"] == 0
    assert policy["integrations"][0]["filter_enabled"] is False

    enabled = call(
        api,
        "PUT",
        f'/api/v2/filters/destinations/{destination["id"]}/enabled',
        {"enabled": True},
        headers,
    )
    assert enabled.status == 200
    assert enabled.payload["enabled"] is True
    assert platform.filters.filter_enabled(destination["id"], "zabbix") is True
    assert not platform.filters.matches(api["admin"].actor, destination["id"], rejected)


def test_shared_admin_filter_is_visible_but_rule_private_to_normal_user(api):
    admin_headers = login(api)
    route = create_route(api, admin_headers, "Zabbix shared", source="zabbix")
    destination = create_destination(api, admin_headers, "Shared operations", [route["id"]])
    platform = api["service"].platform
    configure_zabbix_filter(platform, api["admin"].actor, destination["id"])
    shared = call(
        api,
        "PATCH",
        f'/api/v2/destinations/{destination["id"]}',
        {"shared": True},
        admin_headers,
    )
    assert shared.status == 200

    user = platform.users.create("filter-reader", USER_PASSWORD)
    user_headers = login_as(api, user.username, USER_PASSWORD)
    overview = call(api, "GET", "/api/v2/filters", headers=user_headers)
    assert overview.status == 200
    assert overview.payload["private_resources"] == []
    assert all(item["id"] != destination["id"] for item in overview.payload["destinations"])
    policy = next(item for item in overview.payload["filters"] if item["destination_id"] == destination["id"])
    assert policy["managed_by_admin"] is True
    assert policy["owned"] is False
    assert policy["can_manage_filters"] is False
    assert policy["shared"] is True
    assert policy["configured_count"] == 1
    integration = policy["integrations"][0]
    assert integration["restricted"] is True
    assert integration["configured"] is True
    assert integration["filter_enabled"] is True
    assert integration["rules"] == {}
    assert "high" not in json.dumps(policy)
    assert "disaster" not in json.dumps(policy)

    private_detail = call(
        api,
        "GET",
        f'/api/v2/filters/destinations/{destination["id"]}',
        headers=user_headers,
    )
    assert private_detail.status == 403

    flow = call(api, "GET", "/api/v2/routing-flow/15m", headers=user_headers)
    assert flow.status == 200
    link = next(item for item in flow.payload["links"] if item["destination_id"] == destination["id"])
    assert "high" not in json.dumps(link)
    assert "disaster" not in json.dumps(link)
    managed = [item for item in link["policies"] if item.get("managed")]
    assert len(managed) == 1
    assert managed[0]["configured"] is True
    assert managed[0]["enabled"] is True
    assert managed[0]["rules"] == {"__managed": ["Managed by administrator"]}


def test_normal_user_can_manage_private_destination_filter_without_admin_visibility(api):
    admin_headers = login(api)
    route = create_route(api, admin_headers, "Private Zabbix", source="zabbix")
    platform = api["service"].platform
    owner = platform.users.create("private-filter-owner", USER_PASSWORD)
    private = platform.destinations.create(
        owner.actor,
        owner.id,
        "Owner private webhook",
        "webhook",
        settings={"method": "POST"},
        shared=False,
    )
    platform.relationships.replace_for_destination(owner.actor, private.id, [route["id"]])
    owner_headers = login_as(api, owner.username, USER_PASSWORD)

    empty_overview = call(api, "GET", "/api/v2/filters", headers=owner_headers)
    choice = next(item for item in empty_overview.payload["destinations"] if item["id"] == private.id)
    assert choice["owned"] is True
    assert choice["can_manage_filters"] is True
    assert choice["shared"] is False

    created = call(
        api,
        "PUT",
        f"/api/v2/filters/destinations/{private.id}/sources/zabbix",
        {"rules": {"severity": ["high", "disaster"]}, "enabled": True},
        owner_headers,
    )
    assert created.status == 200
    assert created.payload["integration"]["configured"] is True
    assert created.payload["integration"]["filter_enabled"] is True

    owner_overview = call(api, "GET", "/api/v2/filters", headers=owner_headers).payload
    owner_policy = next(item for item in owner_overview["filters"] if item["destination_id"] == private.id)
    assert owner_policy["owned"] is True
    assert owner_policy["can_manage_filters"] is True
    assert owner_policy["managed_by_admin"] is False

    admin_overview = call(api, "GET", "/api/v2/filters", headers=admin_headers).payload
    assert private.id not in json.dumps(admin_overview)
    assert admin_overview["private_resources"] == []

    owner_flow = call(api, "GET", "/api/v2/routing-flow/15m", headers=owner_headers).payload
    assert any(item["id"] == private.id for item in owner_flow["destinations"])
    owner_link = next(item for item in owner_flow["links"] if item["destination_id"] == private.id)
    assert any(item["configured"] and item["enabled"] for item in owner_link["policies"])

    admin_flow = call(api, "GET", "/api/v2/routing-flow/15m", headers=admin_headers).payload
    assert private.id not in json.dumps(admin_flow)


def test_sharing_state_is_single_destination_source_of_truth(api):
    headers = login(api)
    route = create_route(api, headers, "Shared state Zabbix", source="zabbix")
    destination = create_destination(api, headers, "Sharing sync", [route["id"]])
    platform = api["service"].platform
    configure_zabbix_filter(platform, api["admin"].actor, destination["id"])

    for shared in (True, False, True):
        response = call(
            api,
            "PATCH",
            f'/api/v2/destinations/{destination["id"]}',
            {"shared": shared},
            headers,
        )
        assert response.status == 200
        overview = call(api, "GET", "/api/v2/filters", headers=headers).payload
        policy = next(item for item in overview["filters"] if item["destination_id"] == destination["id"])
        assert policy["shared"] is shared
        assert policy["can_change_sharing"] is True
