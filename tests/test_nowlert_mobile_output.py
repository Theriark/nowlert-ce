"""Native Mobile publishing and secret-safe destination contract."""
import json
import socket
from dataclasses import replace

import pytest
import requests

from models import Notification
from outputs.platform import PlatformOutputRegistry
from outputs.settings import normalize_output_settings
from storage.destinations import Destination

TOPIC = "929c382c-74bf-4667-91cb-865225661ef9"
SETTINGS = {"base_url": "https://mobile.example.com", "topic_id": TOPIC}


def destination(settings=None):
    return Destination("mobile-output", "owner", "Operations", "nowlert_mobile",
                       settings or SETTINGS, False, True, True, 1, 1)


def alert(**metadata):
    return Notification(source="grafana", category="alert", status="firing",
                        title="Database latency", body="token=private-value latency is high",
                        metadata={"event_id": "event-42", "host": "db-1",
                                  "severity": "critical", **metadata})


class Client:
    def __init__(self, status=202, error=None):
        self.status, self.error, self.calls = status, error, []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return type("Response", (), {"status_code": self.status,
                                     "text": "secret=never-persist-this"})()


def adapter(client=None, private=False):
    instance = PlatformOutputRegistry().get("nowlert_mobile")
    instance.http_client = client or Client()
    instance.resolver = lambda host, port, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1" if private else "93.184.216.34", port))]
    return instance


def test_mobile_settings_canonical():
    assert normalize_output_settings("nowlert_mobile", {**SETTINGS, "base_url": SETTINGS["base_url"] + "/"}) == SETTINGS


@pytest.mark.parametrize("changes", [
    {"base_url": "http://mobile.example.com"}, {"base_url": "https://secret@mobile.example.com"},
    {"base_url": "https://mobile.example.com?token=secret"}, {"base_url": "https://mobile.example.com/api/v1"},
    {"topic_id": ""}, {"topic_id": "invalid"}, {"api_token": "secret"},
])
def test_mobile_settings_reject_invalid_or_secret(changes):
    with pytest.raises(ValueError):
        normalize_output_settings("nowlert_mobile", {**SETTINGS, **changes})


def test_native_payload_and_stable_delivery_identity():
    preview = adapter().preview(destination(), alert(api_key="private-key"))
    payload = preview.payload
    assert payload["target"] == {"type": "topic", "id": TOPIC}
    assert payload["priority"] == "urgent"
    assert payload["content"]["title"] == "Database latency"
    assert payload["content"]["metadata"]["source_name"] == "Nowlert CE · grafana"
    assert payload["content"]["metadata"]["ce_event_id"] == "event-42"
    assert payload["content"]["actions"] == [{"type": "acknowledge", "label": "Acknowledge"}]
    assert "private-key" not in json.dumps(payload)
    assert "private-value" not in json.dumps(payload)
    assert payload == adapter().preview(destination(), alert()).payload
    updated = adapter().preview(destination(), alert(event_id="event-43")).payload
    assert updated["thread_key"] == payload["thread_key"]
    assert updated["idempotency_key"] != payload["idempotency_key"]
    other = adapter().preview(replace(destination(), id="other-output"), alert()).payload
    assert other["idempotency_key"] != payload["idempotency_key"]


@pytest.mark.parametrize("severity,expected", [("warning", "high"), ("critical", "urgent"),
    ("information", "default"), ("unknown", "default"), ("recovery", "default"),
    ("caution", "high"), ("high", "high"), ("average", "high"), ("failure", "high"),
    ("alert", "urgent"), ("emergency", "urgent")])
def test_priority(severity, expected):
    assert adapter().preview(destination(), alert(severity=severity)).payload["priority"] == expected


def test_recovery_overrides_critical_severity():
    assert adapter().preview(destination(), replace(alert(), status="resolved")).payload["priority"] == "default"


def test_publish_uses_native_endpoint_write_only_token_and_no_redirects():
    client = Client()
    result = adapter(client).deliver(destination(), b'{"api_token":"fixture-secret"}', alert())
    assert result.success and result.response_status == 202
    url, request = client.calls[0]
    assert url == "https://mobile.example.com/api/v1/notifications"
    assert request["headers"]["Authorization"] == "Bearer fixture-secret"
    assert request["timeout"] == 15 and request["allow_redirects"] is False
    assert "fixture-secret" not in json.dumps(request["json"])
    assert "fixture-secret" not in repr(result)


@pytest.mark.parametrize("status,retryable", [(401, False), (403, False), (422, False),
    (429, True), (500, True), (503, True), (302, False), (200, False), (204, False)])
def test_response_classification(status, retryable):
    result = adapter(Client(status)).deliver(destination(), b'{"api_token":"fixture-secret"}', alert())
    assert not result.success and result.retryable == retryable
    assert "never-persist" not in repr(result)


def test_timeout_retries():
    result = adapter(Client(error=requests.Timeout("secret=private"))).deliver(
        destination(), b'{"api_token":"fixture-secret"}', alert())
    assert result.retryable and "private" not in repr(result)


@pytest.mark.parametrize("secret", [None, b'{}', b'{"api_token":"bad\\r\\nheader"}'])
def test_missing_or_invalid_token_does_not_send(secret):
    client = Client()
    assert not adapter(client).deliver(destination(), secret, alert()).success
    assert not client.calls


def test_private_network_rejected():
    client = Client()
    assert not adapter(client, private=True).deliver(destination(), b'{"api_token":"fixture-secret"}', alert()).success
    assert not client.calls


@pytest.mark.parametrize("change", [{"host": "db-2"}, {"source": "redfish"},
    {"status": "resolved"}, {"start_time": "2026-10-05T05:00:00Z"}])
def test_reused_provider_event_id_does_not_collapse_different_occurrences(change):
    original = alert()
    updated = replace(original, **change) if "host" not in change else alert(**change)
    assert adapter().preview(destination(), original).payload["idempotency_key"] != adapter().preview(destination(), updated).payload["idempotency_key"]


def test_hardware_identity_keeps_distinct_threads():
    first = replace(alert(), source="redfish", metadata={"event_id": "1", "system": "server-1"})
    second = replace(first, metadata={"event_id": "1", "system": "server-2"})
    left, right = [adapter().preview(destination(), item).payload for item in (first, second)]
    assert left["thread_key"] != right["thread_key"]
    assert left["idempotency_key"] != right["idempotency_key"]


def test_yaml_validation_rejects_invalid_mobile_key():
    from api.schema import validate_config
    errors = validate_config({"outputs": {"nowlert_mobile": {"enabled": True,
        "mobile": {"name": "Mobile", "enabled": True, "settings": SETTINGS,
                   "secret": {"password": "wrong-key-shape"}}}}})
    assert any("publish key" in message for message in errors)


def test_changed_route_context_gets_a_new_identity():
    first = adapter().preview(destination(), alert(_ce_route={"id": "route-1", "name": "Original"})).payload
    second = adapter().preview(destination(), alert(_ce_route={"id": "route-1", "name": "Renamed"})).payload
    assert first["idempotency_key"] != second["idempotency_key"]
