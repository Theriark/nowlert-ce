import pytest
import threading

from test_platform_api import platform_api, call, login, create_destination, create_route
from test_platform_api_http import request

from models import Notification
from storage.delivery import DeliveryHistoryStore, DeliveryResult
from inputs.http import HTTPServer
from dispatcher import Dispatcher


def seed_history(platform, headers, count=130):
    destination = create_destination(platform, headers)
    route = create_route(platform, headers, destination["id"])
    store = DeliveryHistoryStore(platform["database"], batch_wait_seconds=0)
    route = platform["service"].platform.routes.get(platform["admin"].actor, route["id"])
    for index in range(count):
        store.record(platform["admin"].id, f"event-{index}", route,
                     Notification(source="home_assistant", title=f"Event {index}", status="critical"),
                     1, "delivered", DeliveryResult(True))
    return store


def test_history_filters_search_sort_and_count_cover_full_authorized_history(platform_api):
    headers = login(platform_api)
    seed_history(platform_api, headers)
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE delivery_attempts SET created_at = 1 WHERE delivery_id = 'event-0'")
    response = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?search=Event%200&sort=oldest", headers=headers)
    assert response.status == 200
    assert response.payload["pagination"]["total"] == 1
    assert response.payload["deliveries"][0]["delivery_id"] == "event-0"
    assert response.payload["filter_options"]["sources"] == ["home_assistant"]
    oldest = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?sort=oldest", headers=headers)
    assert oldest.payload["deliveries"][0]["delivery_id"] == "event-0"
    recent = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?range=1d&source=home_assistant&severity=critical&outcome=delivered", headers=headers)
    assert recent.payload["pagination"]["total"] == 129
    assert recent.payload["pagination"]["total_pages"] == 6
    assert len(recent.payload["deliveries"]) == 25
    other = login(platform_api, "owner-user", "owner secure password")
    hidden = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?search=Event", headers=other)
    assert hidden.status == 200
    assert hidden.payload["pagination"]["total"] == 0
    assert hidden.payload["filter_options"]["sources"] == []
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE destinations SET shared = 1")
    shared = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?search=Event", headers=other)
    assert shared.payload["pagination"]["total"] == 130


@pytest.mark.parametrize("query", ["sort=invalid", "range=invalid", "search=x&search=y", "unknown=x", "search=" + "x" * 1001])
def test_history_rejects_invalid_query(platform_api, query):
    headers = login(platform_api)
    assert call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?" + query, headers=headers).status == 400


def test_native_http_preserves_delivery_query(platform_api):
    headers = login(platform_api)
    server = HTTPServer(("127.0.0.1", 0), Dispatcher(), None, 1_048_576, "", platform_api["database"])
    server.api = platform_api["service"]
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        status, _payload, _headers = request(server.server_port, "GET", "/api/v2/deliveries/page/1/size/25?sort=invalid", headers=headers)
        assert status == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_dashboard_aggregates_more_than_latest_hundred(platform_api):
    headers = login(platform_api)
    store = seed_history(platform_api, headers)
    route_id = store.list_visible(platform_api["admin"].actor, limit=1)[0].route_id
    route = platform_api["service"].platform.routes.get(platform_api["admin"].actor, route_id)
    store.record(platform_api["admin"].id, "event-0", route,
                 Notification(source="home_assistant", title="Recovered", status="critical"),
                 2, "delivered", DeliveryResult(True))
    response = call(platform_api, "GET", "/api/v2/metrics/1d", headers=headers)
    assert response.status == 200
    metrics = response.payload["metrics"]
    assert metrics["history"]["total"] == 130
    assert sum(bucket["delivered"] for bucket in metrics["buckets"]) == 130
    assert metrics["top_sources"] == [{"source": "home_assistant", "count": 130}]
    assert metrics["history_previous"]["total"] == 0
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE delivery_attempts SET created_at = created_at - 86400 WHERE delivery_id = 'event-129'")
    previous = call(platform_api, "GET", "/api/v2/metrics/1d", headers=headers).payload["metrics"]
    assert previous["history_previous"]["total"] == 1
    assert previous["history_previous"]["delivered"] == 1
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE delivery_attempts SET created_at = created_at + 86400 WHERE delivery_id = 'event-129'")
    other = login(platform_api, "owner-user", "owner secure password")
    hidden = call(platform_api, "GET", "/api/v2/metrics/1d", headers=other).payload["metrics"]
    assert hidden["history"]["total"] == 0
    assert hidden["top_sources"] == []
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE delivery_attempts SET outcome = 'retry_scheduled', retryable = 1 WHERE delivery_id = 'event-0'")
        connection.execute("UPDATE delivery_attempts SET outcome = 'failed', retryable = 1 WHERE delivery_id = 'event-1'")
        connection.execute("UPDATE delivery_attempts SET created_at = 1 WHERE delivery_id = 'event-2'")
    metrics = call(platform_api, "GET", "/api/v2/metrics/1d", headers=headers).payload["metrics"]
    assert metrics["history"]["total"] == 129
    assert metrics["history"]["retry"] == 1
    assert metrics["history"]["failed"] == 1
    with platform_api["database"].transaction() as connection:
        connection.execute("UPDATE delivery_attempts SET owner_user_id = ?, source = 'private-source'", (platform_api["owner"].id,))
        connection.execute("UPDATE destinations SET owner_user_id = ?", (platform_api["owner"].id,))
    hidden_admin = call(platform_api, "GET", "/api/v2/metrics/1d", headers=headers).payload["metrics"]
    assert hidden_admin["history"]["total"] == 0
    assert hidden_admin["top_sources"] == []
    page = call(platform_api, "GET", "/api/v2/deliveries/page/1/size/25?source=private-source", headers=headers).payload
    assert page["pagination"]["total"] == 0
    assert page["filter_options"]["sources"] == []


def test_housekeeping_accepts_eight_fields_and_preserves_email_values_for_legacy_clients(platform_api):
    headers = login(platform_api)
    settings = call(platform_api, "GET", "/api/v2/housekeeping", headers=headers).payload["settings"]
    settings["email_raw_content_days"] = 14
    saved = call(platform_api, "PUT", "/api/v2/housekeeping", settings, headers)
    assert saved.status == 200
    assert saved.payload["settings"]["email_raw_content_days"] == 14
    legacy = {key: value for key, value in settings.items() if not key.startswith("email_")}
    assert call(platform_api, "PUT", "/api/v2/housekeeping", legacy, headers).payload["settings"]["email_raw_content_days"] == 14
    settings["email_raw_content_days"] = 999
    assert call(platform_api, "PUT", "/api/v2/housekeeping", settings, headers).status == 400
