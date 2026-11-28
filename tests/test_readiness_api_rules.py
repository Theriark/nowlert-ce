"""API rules found by the v27.0.0 readiness check."""

from __future__ import annotations

import pytest

from test_platform_api import (  # noqa: F401 - pytest fixture
    call,
    create_destination,
    event,
    login,
    platform_api,
)


def owner_login(platform):
    return login(platform, "owner-user", "owner secure password", client="127.0.0.2")


def another_login(platform):
    return login(platform, "another-user", "another secure password", client="127.0.0.3")


def webhook(name, url):
    return {
        "name": name,
        "output_type": "webhook",
        "settings": {"method": "POST"},
        "secret": {"url": url},
    }


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "http://hooks.example.com/nowlert",
        "https://",
        "https://user:secret@hooks.example.com/nowlert",
        "ftp://hooks.example.com/nowlert",
    ],
)
def test_webhook_destination_refuses_an_invalid_url(platform_api, url):
    headers = login(platform_api)

    response = call(platform_api, "POST", "/api/v2/destinations", webhook("Broken hook", url), headers)
    with platform_api["database"].connect() as connection:
        stored = connection.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]

    assert response.status == 400
    assert response.payload["error"].startswith(
        "Webhook URL must be a complete https:// address"
    )
    assert stored == 0


def test_webhook_url_is_validated_when_it_is_changed(platform_api):
    headers = login(platform_api)
    destination = create_destination(platform_api, headers)

    rejected = call(
        platform_api,
        "PATCH",
        f"/api/v2/destinations/{destination['id']}",
        {"secret": {"url": "not-a-url"}},
        headers,
    )
    accepted = call(
        platform_api,
        "PATCH",
        f"/api/v2/destinations/{destination['id']}",
        {"secret": {"url": "https://hooks.example.com/rotated"}},
        headers,
    )
    renamed = call(
        platform_api,
        "PATCH",
        f"/api/v2/destinations/{destination['id']}",
        {"name": "Renamed webhook"},
        headers,
    )

    assert rejected.status == 400
    assert "https://" in rejected.payload["error"]
    assert accepted.status == 200
    assert renamed.status == 200


def route(name, source="zabbix"):
    return {"name": name, "source": source, "input_type": "http", "filters": {}}


def test_route_names_are_unique_ignoring_case_across_owners(platform_api):
    admin_headers = login(platform_api)
    owner_headers = owner_login(platform_api)

    first = call(platform_api, "POST", "/api/v2/routes", route("Core switches"), admin_headers)
    same_owner = call(platform_api, "POST", "/api/v2/routes", route("CORE SWITCHES"), admin_headers)
    other_owner = call(
        platform_api, "POST", "/api/v2/routes", route("core switches", "grafana"), owner_headers
    )

    assert first.status == 201
    for duplicate in (same_owner, other_owner):
        assert duplicate.status == 409
        assert duplicate.payload["error"] == (
            "A route named CORE SWITCHES already exists. Choose another name."
            if duplicate is same_owner
            else "A route named core switches already exists. Choose another name."
        )


def test_route_rename_refuses_a_duplicate_but_keeps_its_own_name(platform_api):
    headers = login(platform_api)
    call(platform_api, "POST", "/api/v2/routes", route("Core switches"), headers)
    edge = call(platform_api, "POST", "/api/v2/routes", route("Edge routers", "grafana"), headers)
    route_id = edge.payload["route"]["id"]

    duplicate = call(
        platform_api, "PATCH", f"/api/v2/routes/{route_id}", {"name": "core Switches"}, headers
    )
    same_name = call(
        platform_api,
        "PATCH",
        f"/api/v2/routes/{route_id}",
        {"name": "Edge routers", "priority": 10},
        headers,
    )
    recased = call(
        platform_api, "PATCH", f"/api/v2/routes/{route_id}", {"name": "EDGE routers"}, headers
    )

    assert duplicate.status == 409
    assert "already exists" in duplicate.payload["error"]
    assert same_name.status == 200
    assert recased.status == 200
    assert recased.payload["route"]["name"] == "EDGE routers"


def test_only_owner_or_admin_can_send_a_test_to_a_shared_destination(platform_api):
    owner_headers = owner_login(platform_api)
    destination = create_destination(platform_api, owner_headers, shared=True)
    another_headers = another_login(platform_api)
    admin_headers = login(platform_api)
    path = f"/api/v2/destinations/{destination['id']}/test"

    denied = call(platform_api, "POST", path, {"event": event()}, another_headers)
    preview = call(
        platform_api,
        "POST",
        f"/api/v2/destinations/{destination['id']}/preview",
        {"event": event()},
        another_headers,
    )
    owner = call(platform_api, "POST", path, {"event": event()}, owner_headers)
    admin = call(platform_api, "POST", path, {"event": event()}, admin_headers)

    assert denied.status == 403
    assert denied.payload["error"] == (
        "Only the destination owner or an administrator can send a test."
    )
    assert preview.status == 200
    assert owner.status == 200
    assert admin.status == 200
    assert len(platform_api["adapter"].deliveries) == 2


def test_wrong_current_password_names_the_current_password(platform_api):
    headers = owner_login(platform_api)

    response = call(
        platform_api,
        "PUT",
        "/api/v2/account/password",
        {"current_password": "incorrect password", "new_password": "replacement owner password"},
        headers,
    )

    assert response.status == 403
    assert response.payload == {
        "error": "The current password is not correct.",
        "code": "password_invalid",
        "field": "current_password",
    }
