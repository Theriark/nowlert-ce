"""API acceptance for reusable Routes assigned from Destinations."""

from __future__ import annotations

import api.platform as platform_module
import pytest

from api.security import hash_password
from api.service import APIService
from dispatcher import Dispatcher
from outputs.platform import OutputPreview, PlatformOutputAdapter, PlatformOutputRegistry
from storage.database import Database
from storage.delivery import DeliveryResult
from storage.users import UserStore


PASSWORD = "correct horse battery staple"


class Configuration:
    def __init__(self, data):
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


class Router:
    def route(self, _notification):
        raise AssertionError("platform ingestion must use database Routes")


class Adapter(PlatformOutputAdapter):
    output_type = "webhook"

    def __init__(self):
        self.deliveries = []

    def preview(self, destination, notification):
        return OutputPreview("webhook", "application/json", {}, {})

    def deliver(self, destination, secret_value, notification):
        self.deliveries.append((destination.id, notification.source))
        return DeliveryResult(True, response_status=202)


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0d" * 16, iterations=1_000)


@pytest.fixture
def api(tmp_path, monkeypatch):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()

    def users(database_value):
        return UserStore(database_value, password_hasher=fast_hash)

    monkeypatch.setattr(platform_module, "UserStore", users)
    store = users(database)
    admin = store.bootstrap_admin("administrator", PASSWORD)
    adapter = Adapter()
    service = APIService(
        Dispatcher(),
        Router(),
        Configuration(
            {
                "api": {"enabled": True},
                "platform": {
                    "enabled": True,
                    "state_dir": str(tmp_path / "state"),
                    "secure_cookies": False,
                },
            }
        ),
        platform_database=database,
        platform_registry=PlatformOutputRegistry([adapter]),
    )
    return {"database": database, "admin": admin, "service": service, "adapter": adapter}


def call(api, method, path, payload=None, headers=None):
    return api["service"].handle_http(
        method,
        path,
        payload,
        headers or {},
        "127.0.0.1",
    )


def login(api):
    response = call(
        api,
        "POST",
        "/api/v2/session",
        {"username": "administrator", "password": PASSWORD},
    )
    assert response.status == 200
    cookies = [value for name, value in response.headers if name == "Set-Cookie"]
    session = next(item.split(";", 1)[0] for item in cookies if "session=" in item)
    return {"Cookie": session, "X-CSRF-Token": response.payload["csrf_token"]}


def create_route(api, headers, name, source="grafana"):
    response = call(
        api,
        "POST",
        "/api/v2/routes",
        {
            "name": name,
            "source": source,
            "input_type": "http",
            "priority": "normal",
            "enabled": True,
        },
        headers,
    )
    assert response.status == 201
    return response.payload["route"]


def create_destination(api, headers, name, route_ids):
    response = call(
        api,
        "POST",
        "/api/v2/destinations",
        {
            "name": name,
            "output_type": "webhook",
            "settings": {"method": "POST"},
            "secret": {"url": "https://example.invalid/events"},
            "route_ids": list(route_ids),
            "enabled": True,
        },
        headers,
    )
    assert response.status == 201
    return response.payload["destination"]


def test_route_create_requires_no_destination_and_returns_assignment_metadata(api):
    headers = login(api)

    route = create_route(api, headers, "Reusable Grafana")

    assert "destination_id" not in route
    assert route["destination_ids"] == []
    assert route["destination_count"] == 0


def test_destination_can_assign_multiple_routes_atomically(api):
    headers = login(api)
    first = create_route(api, headers, "Grafana reusable")
    second = create_route(api, headers, "Zabbix reusable", source="zabbix")

    destination = create_destination(
        api,
        headers,
        "Operations webhook",
        [first["id"], second["id"]],
    )

    assert destination["route_ids"] == [first["id"], second["id"]]
    routes = call(api, "GET", "/api/v2/routes", headers=headers).payload["routes"]
    by_id = {item["id"]: item for item in routes}
    assert by_id[first["id"]]["destination_count"] == 1
    assert by_id[second["id"]]["destination_count"] == 1

    failed = call(
        api,
        "PATCH",
        f"/api/v2/destinations/{destination['id']}",
        {"route_ids": [first["id"], "0" * 32]},
        headers,
    )
    assert failed.status in {400, 404}
    after = call(
        api,
        "GET",
        "/api/v2/destinations",
        headers=headers,
    ).payload["destinations"]
    current = next(item for item in after if item["id"] == destination["id"])
    assert current["route_ids"] == [first["id"], second["id"]]


def test_one_route_is_reused_by_multiple_destinations(api):
    headers = login(api)
    route = create_route(api, headers, "Reusable Grafana")
    first = create_destination(api, headers, "Webhook one", [route["id"]])
    second = create_destination(api, headers, "Webhook two", [route["id"]])

    listed = call(api, "GET", "/api/v2/routes", headers=headers).payload["routes"]
    current = next(item for item in listed if item["id"] == route["id"])

    assert current["destination_count"] == 2
    assert set(current["destination_ids"]) == {first["id"], second["id"]}


def test_destination_delete_does_not_delete_reusable_route(api):
    headers = login(api)
    route = create_route(api, headers, "Reusable Grafana")
    destination = create_destination(api, headers, "Disposable output", [route["id"]])

    deleted = call(
        api,
        "DELETE",
        f"/api/v2/destinations/{destination['id']}",
        headers=headers,
    )
    assert deleted.status == 204

    listed = call(api, "GET", "/api/v2/routes", headers=headers).payload["routes"]
    current = next(item for item in listed if item["id"] == route["id"])
    assert current["destination_count"] == 0
    assert current["destination_ids"] == []
