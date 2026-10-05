"""Pairing uses normal destination saves, owner boundaries and non-consuming polling."""
import json
from pathlib import Path

import pytest

from test_platform_api import platform_api, call, login
from integrations.mobile_connection import mobile_origin
from storage.ownership import Actor


@pytest.fixture
def pairing(platform_api, monkeypatch):
    api = platform_api["service"].platform
    calls = []
    def post(origin, operation, body):
        calls.append((origin, operation, body))
        if operation == "":
            return {"device_code": "private-device-credential-12345678", "user_code": "ABCD-EFGH", "expires_in": 600}
        if operation == "/status":
            return {"status": "approved", "topic_name": "Nowlert CE"}
        return {"status": "connected", "topic_id": "11111111-1111-4111-8111-111111111111", "topic_name": "Nowlert CE", "secret": "private-topic-publish-key"}
    monkeypatch.setattr(api.mobile_connections, "_post", post)
    monkeypatch.setenv("NOWLERT_DEPLOYMENT_ENVIRONMENT", "development")
    headers = login(platform_api)
    started = call(platform_api, "POST", "/api/v2/mobile-connections", {"name": "Friendly Mobile"}, headers)
    assert started.status == 200
    return api, headers, started.payload["connection_id"], calls


def test_poll_is_safe_owner_bound_and_does_not_create_destination(platform_api, pairing):
    api, headers, connection_id, calls = pairing
    for _ in range(2):
        status = call(platform_api, "POST", "/api/v2/mobile-connections/" + connection_id, {}, headers)
        assert status.status == 200 and status.payload == {"status": "approved", "topic_name": "Nowlert CE"}
    assert all(operation != "/redeem" for _, operation, _ in calls)
    assert not call(platform_api, "GET", "/api/v2/destinations", headers=headers).payload["destinations"]
    other = login(platform_api, "owner-user", "owner secure password")
    denied = call(platform_api, "POST", "/api/v2/mobile-connections/" + connection_id, {}, other)
    assert denied.status == 403
    csrf_missing = {"Cookie": headers["Cookie"]}
    assert call(platform_api, "POST", "/api/v2/mobile-connections", {"name": "Mobile"}, csrf_missing).status == 401
    for response in (status, denied):
        assert "private-device" not in json.dumps(response.payload)
    assert b"private-device-credential" not in platform_api["database"].path.read_bytes()


def test_standard_save_keeps_name_routes_and_existing_secret_on_edit(platform_api, pairing):
    api, headers, connection_id, calls = pairing
    actor = Actor(platform_api["admin"].id, "admin")
    route = api.routes.create(actor, actor.user_id, "Grafana route", "grafana")
    payload = {"name": "Renamed phone", "output_type": "nowlert_mobile", "route_ids": [route.id], "mobile_connection_id": connection_id}
    result = call(platform_api, "POST", "/api/v2/destinations", payload, headers)
    assert result.status == 201
    destination = result.payload["destination"]
    assert destination["name"] == "Renamed phone" and destination["route_ids"] == [route.id]
    assert destination["settings"]["topic_name"] == "Nowlert CE" and destination["secret_configured"]
    assert destination["settings"]["base_url"] == "https://nowlert-mb-dev.theriark.dev"
    assert "private-topic" not in json.dumps(result.payload)
    target = api.destinations.for_delivery_metadata(actor, destination["id"])
    secret = api.secrets.resolve(actor, target.secret_id)
    assert json.loads(secret)["api_token"] == "private-topic-publish-key"
    edit = call(platform_api, "PATCH", "/api/v2/destinations/" + destination["id"], {"name": "My phone", "route_ids": [route.id]}, headers)
    assert edit.status == 200
    assert api.secrets.resolve(actor, target.secret_id) == secret
    # Repeating the save after an interrupted response updates the same destination.
    retried = call(platform_api, "POST", "/api/v2/destinations", payload, headers)
    assert retried.status == 200 and retried.payload["destination"]["id"] == destination["id"]
    assert len([x for x in calls if x[1] == "/redeem"]) == 1
    status = call(platform_api, "POST", "/api/v2/mobile-connections/" + connection_id, {}, headers)
    assert status.status == 200 and status.payload["topic_name"] == "Nowlert CE"
    assert b"private-topic-publish-key" not in platform_api["database"].path.read_bytes()


def test_failed_save_retains_redeemed_grant_for_retry(platform_api, pairing, monkeypatch):
    api, headers, connection_id, calls = pairing
    original = api.destinations.create
    def fail(*args, **kwargs):
        raise ValueError("Temporary destination save failure")
    monkeypatch.setattr(api.destinations, "create", fail)
    payload = {"name": "Phone", "output_type": "nowlert_mobile", "route_ids": [], "mobile_connection_id": connection_id}
    assert call(platform_api, "POST", "/api/v2/destinations", payload, headers).status == 400
    # Re-initialization demonstrates retry state is in the established durable secret store.
    from integrations.mobile_connection import MobileConnections
    api.mobile_connections = MobileConnections(api.secrets)
    def consumed(*args, **kwargs):
        raise AssertionError("redeem must not repeat")
    monkeypatch.setattr(api.mobile_connections, "_post", consumed)
    monkeypatch.setattr(api.destinations, "create", original)
    result = call(platform_api, "POST", "/api/v2/destinations", payload, headers)
    assert result.status == 201 and result.payload["destination"]["secret_configured"]


def test_environment_origins_are_server_selected(monkeypatch):
    monkeypatch.delenv("NOWLERT_MOBILE_ORIGIN", raising=False)
    for environment, expected in (("development", "https://nowlert-mb-dev.theriark.dev"), ("stage", "https://nowlert-mb-stg.theriark.dev"), ("production", "https://nowlert-mb.theriark.com")):
        monkeypatch.setenv("NOWLERT_DEPLOYMENT_ENVIRONMENT", environment)
        assert mobile_origin() == expected
    monkeypatch.setenv("NOWLERT_MOBILE_ORIGIN", "https://mobile.example.com")
    assert mobile_origin() == "https://mobile.example.com"
    monkeypatch.setenv("NOWLERT_MOBILE_ORIGIN", "https://user:password@mobile.example.com/path")
    with pytest.raises(ValueError):
        mobile_origin()


def test_browser_cannot_supply_origin_or_credentials(platform_api, pairing):
    _, headers, connection_id, _ = pairing
    assert call(platform_api, "POST", "/api/v2/mobile-connections", {"name": "Mobile", "origin": "https://attacker.invalid"}, headers).status == 400
    assert call(platform_api, "POST", "/api/v2/destinations", {"name": "Mobile", "output_type": "nowlert_mobile", "mobile_connection_id": connection_id, "secret": {"api_token": "attacker"}}, headers).status == 400


def test_normal_editor_hides_technical_fields_and_uses_shared_save_helper():
    root = Path(__file__).parents[1]
    app = (root / "src/webui/app.js").read_text()
    start = app.index("    nowlert_mobile: {", app.index("function destinationDefinition"))
    definition = app[start:app.index("    discord: {", start)]
    assert "base_url" not in definition and "topic_id" not in definition and "api_token" not in definition
    assert 'byId("destination-name").value = "Nowlert Mobile"' in app
    assert "prepareMobileDestinationPayload(payload, id)" in (root / "src/webui/dashboard.js").read_text()


def test_deployment_tracing_environment_fallback(monkeypatch):
    monkeypatch.delenv("NOWLERT_DEPLOYMENT_ENVIRONMENT", raising=False)
    monkeypatch.delenv("NOWLERT_MOBILE_ORIGIN", raising=False)
    monkeypatch.setenv("DD_ENV", "development")
    assert mobile_origin() == "https://nowlert-mb-dev.theriark.dev"
    monkeypatch.setenv("DD_ENV", "stg")
    assert mobile_origin() == "https://nowlert-mb-stg.theriark.dev"
    monkeypatch.setenv("DD_ENV", "custom-tracing-name")
    assert mobile_origin() == "https://nowlert-mb.theriark.com"
    monkeypatch.setenv("NOWLERT_DEPLOYMENT_ENVIRONMENT", "unknown")
    with pytest.raises(ValueError):
        mobile_origin()


def test_expired_and_pending_connections_have_friendly_errors(platform_api, pairing, monkeypatch):
    api, headers, connection_id, _ = pairing
    actor = Actor(platform_api["admin"].id, "admin")
    record = json.loads(api.secrets.resolve(actor, connection_id))
    monkeypatch.setattr(api.mobile_connections, "_post", lambda *args: {"status": "pending"})
    payload = {"name": "Mobile", "output_type": "nowlert_mobile", "mobile_connection_id": connection_id}
    pending = call(platform_api, "POST", "/api/v2/destinations", payload, headers)
    assert pending.status == 400 and "Approve" in pending.payload["error"]
    record["expires_at"] = 1
    api.secrets.rotate(actor, connection_id, json.dumps(record))
    expired = call(platform_api, "POST", "/api/v2/mobile-connections/" + connection_id, {}, headers)
    assert expired.status == 400 and "expired" in expired.payload["error"]


def test_request_transport_does_not_follow_redirects_or_surface_credentials(platform_api, monkeypatch):
    from integrations import mobile_connection as module
    calls = []
    class Response:
        status_code = 302
        def json(self):
            raise AssertionError("redirect must not be parsed")
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr(module.requests, "post", post)
    with pytest.raises(ValueError, match="Could not contact"):
        platform_api["service"].platform.mobile_connections._post("https://mobile.example.com", "/status", {"device_code": "private-code"})
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["headers"]["User-Agent"] == "Nowlert-CE/1.0"


def test_reconnect_existing_destination_rotates_secret_and_keeps_routes(platform_api, pairing):
    api, headers, connection_id, _ = pairing
    actor = Actor(platform_api["admin"].id, "admin")
    route = api.routes.create(actor, actor.user_id, "Grafana mobile", "grafana")
    first = call(platform_api, "POST", "/api/v2/destinations", {"name": "Mobile", "output_type": "nowlert_mobile", "mobile_connection_id": connection_id, "route_ids": [route.id]}, headers)
    destination_id = first.payload["destination"]["id"]
    original_secret_id = api.destinations.for_delivery_metadata(actor, destination_id).secret_id
    started = call(platform_api, "POST", "/api/v2/mobile-connections", {"name": "Renamed mobile"}, headers)
    result = call(platform_api, "PATCH", "/api/v2/destinations/" + destination_id, {"name": "Renamed mobile", "output_type": "nowlert_mobile", "mobile_connection_id": started.payload["connection_id"], "route_ids": [route.id]}, headers)
    assert result.status == 200
    assert result.payload["destination"]["id"] == destination_id
    assert result.payload["destination"]["route_ids"] == [route.id]
    assert result.payload["destination"]["name"] == "Renamed mobile"
    assert api.destinations.for_delivery_metadata(actor, destination_id).secret_id == original_secret_id
    assert api.secrets.metadata(actor, original_secret_id).version == 2
