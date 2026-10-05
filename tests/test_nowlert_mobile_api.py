"""Mobile destinations use the normal API, owner secrets and route dispatcher."""
import json

from test_platform_api import platform_api, call, login, event
from test_nowlert_mobile_output import SETTINGS, Client, adapter, alert
from storage.ownership import Actor
from storage.routes import RouteStore
from storage.delivery import PlatformDeliveryService, DeliveryHistoryStore


def test_mobile_api_secret_retained_and_not_exposed(platform_api):
    headers = login(platform_api)
    created = call(platform_api, "POST", "/api/v2/destinations", {
        "name": "Mobile acceptance", "output_type": "nowlert_mobile", "settings": SETTINGS,
        "secret": {"api_token": "private-publish-key"},
    }, headers)
    assert created.status == 201
    item = created.payload["destination"]
    assert item["secret_configured"]
    assert "private-publish-key" not in json.dumps(created.payload)
    target = "/api/v2/destinations/" + item["id"]
    changed = call(platform_api, "PATCH", target, {"name": "Updated Mobile"}, headers)
    assert changed.status == 200 and changed.payload["destination"]["secret_configured"]
    client = Client()
    api = platform_api["service"].platform
    api.outputs.registry.adapters["nowlert_mobile"] = adapter(client)
    result = call(platform_api, "POST", target + "/test", {"event": event()}, headers)
    assert result.status == 200 and result.payload["result"]["response_status"] == 202
    assert client.calls[0][1]["headers"]["Authorization"] == "Bearer private-publish-key"
    listed = call(platform_api, "GET", "/api/v2/destinations", headers=headers)
    assert "private-publish-key" not in json.dumps(listed.payload)
    assert "private-publish-key" not in json.dumps(result.payload)
    assert call(platform_api, "DELETE", target, headers=headers).status == 204


def test_mobile_api_requires_a_publish_key(platform_api):
    result = call(platform_api, "POST", "/api/v2/destinations", {
        "name": "Missing secret", "output_type": "nowlert_mobile", "settings": SETTINGS,
    }, login(platform_api))
    assert result.status == 400


def test_real_route_preserves_identity_on_retry_and_records_acceptance(platform_api):
    api = platform_api["service"].platform
    actor = Actor(platform_api["admin"].id, "admin")
    dest = api.destinations.create(actor, actor.user_id, "Mobile", "nowlert_mobile", settings=SETTINGS)
    secret = api.secrets.create(actor, actor.user_id, "Mobile key", "publish", b'{"api_token":"private-key"}')
    api.destinations.set_secret(actor, dest.id, secret.id)
    route = RouteStore(platform_api["database"]).create(actor, actor.user_id, "Mobile Grafana", "grafana", dest.id)
    client = Client()
    statuses = iter((503, 202))
    original_post = client.post
    def post(url, **kw):
        client.status = next(statuses)
        return original_post(url, **kw)
    client.post = post
    service = PlatformDeliveryService(RouteStore(platform_api["database"]), api.destinations, api.secrets,
        DeliveryHistoryStore(platform_api["database"]),
        {"nowlert_mobile": adapter(client)}, retry_delays=(0,), sleeper=lambda _: None)
    summary = service.deliver(actor, alert())
    assert summary.success and summary.attempts == 2
    first, second = [request[1]["json"] for request in client.calls]
    assert first == second
    assert first["content"]["metadata"]["route_id"] == route.id
    assert first["content"]["metadata"]["route_name"] == "Mobile Grafana"
    history = call(platform_api, "GET", "/api/v2/deliveries", headers=login(platform_api))
    assert history.status == 200
    assert any(row["delivery_status"] == "accepted" for row in history.payload["deliveries"])
    assert "private-key" not in json.dumps(history.payload)
