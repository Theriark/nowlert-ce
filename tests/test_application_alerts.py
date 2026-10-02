"""Native notification contracts, authenticated intake and upgrade coverage."""
import hashlib
import hmac
import http.client
import json
from email.message import EmailMessage
from pathlib import Path

import pytest

from dispatcher import Dispatcher
from inputs.http import ENDPOINTS, SCOPED_SOURCES
from inputs.http_matrix_parity import install
from integrations.catalog import integration
from integrations.filtering import filter_schema
from outputs.discord import DiscordOutput
from outputs.teams import TeamsOutput
from parsers.application_alerts import Parser, NAMES
from test_portainer_webhook import RunningServer, request


FIXTURES = Path(__file__).parent / "fixtures" / "application_alerts"


def payload(source):
    return json.loads((FIXTURES / f"{source}.json").read_text())


@pytest.mark.parametrize("source", NAMES)
def test_native_events_keep_product_identity_and_filterable_fields(source):
    item = Dispatcher().parse_webhook(source, payload(source))[0]
    assert item.source == source
    assert item.body and item.title
    assert item.metadata["state"]
    assert item.metadata["severity"]
    assert integration(source)["name"] == NAMES[source]
    assert len(filter_schema(source)["fields"]) >= 5
    assert source in DiscordOutput().source_formatters
    assert source in TeamsOutput().source_formatters
    assert NAMES[source] in json.dumps(DiscordOutput().source_formatters[source].format(item))
    assert NAMES[source] in json.dumps(TeamsOutput().source_formatters[source].format(item))
    assert DiscordOutput().render_modern_image(item) is not None


@pytest.mark.parametrize("source", NAMES)
@pytest.mark.parametrize("invalid", [None, [], {}, {"eventType": "HealthIssue"}, {"type": "alert", "data": []}])
def test_malformed_payload_does_not_route(source, invalid):
    assert Dispatcher().parse_webhook(source, invalid) is None


def test_servarr_health_restored_and_future_events_are_not_discarded():
    restored = Parser("radarr").parse(payload("radarr"))[0]
    assert restored.status == "success"
    value = payload("sonarr")
    assert Parser("sonarr").parse(value)[0].status == "failure"
    value.update(eventType="FutureNativeEvent", level="Information")
    assert Parser("sonarr").parse(value)[0].metadata["event_type"] == "FutureNativeEvent"


def test_metabase_does_not_persist_chart_or_raw_query_rows():
    item = Parser("metabase").parse(payload("metabase"))[0]
    assert item.metadata["row_count"] == 1
    assert "visualization" not in item.metadata and "raw_data" not in item.metadata
    value = payload("metabase")
    value["alert_id"] = None
    assert Parser("metabase").parse(value)[0].metadata["state"] == "test"


@pytest.mark.parametrize("state,status", [("success", "success"), ("failure", "failure"), ("cancelled", "information"), ("timed_out", "failure"), ("skipped", "information")])
def test_github_conclusions(state, status):
    value = payload("github_actions")
    value["workflow_run"]["conclusion"] = state
    assert Parser("github_actions").parse(value)[0].status == status


def test_github_job_and_ping():
    value = payload("github_actions")
    value["workflow_job"] = value.pop("workflow_run")
    assert Parser("github_actions").parse(value)[0].metadata["event_type"] == "workflow_job"
    assert Parser("github_actions").parse({"zen": "Keep it logically awesome.", "hook": {"id": 12}})[0].metadata["state"] == "test"


def test_application_context_survives_classic_and_modern_image_preparation():
    item = Parser("github_actions").parse(payload("github_actions"))[0]
    rendered = json.dumps(DiscordOutput().source_formatters["github_actions"].format(item))
    assert "development" in rendered and "abcd" in rendered and "123" in rendered
    item = Parser("metabase").parse(payload("metabase"))[0]
    rendered = json.dumps(DiscordOutput().source_formatters["metabase"].format(item))
    assert "108" in rendered and "Result rows" in rendered


def test_native_semaphore_smtp_failure_requires_application_identity():
    message = EmailMessage()
    message["From"] = "automation@example.com"
    message["To"] = "semaphore@nowlert.local"
    message["Subject"] = "Task failed"
    message.set_content("Task 42 with template 'Infrastructure apply' has failed!\nTask Log: Link")
    item = Dispatcher().parse(message)
    assert item.source == "semaphore" and item.status == "failure"
    assert item.run_id == "42" and item.metadata["template"] == "Infrastructure apply"
    message.replace_header("To", "other@example.com")
    assert Dispatcher().parse(message).source == "generic"


@pytest.mark.parametrize("native,state,status", [
    ("❌ ERROR", "failure", "failure"),
    ("✅ SUCCESS", "success", "success"),
    ("⚠️ WAITING_CONFIRMATION", "waiting_confirmation", "warning"),
    ("⏹️ STOPPED", "stopped", "information"),
])
def test_semaphore_native_task_status_format(native, state, status):
    value = payload("semaphore")
    value["attachments"][0]["text"] = f"execution #42, status: {native}!"
    item = Parser("semaphore").parse(value)[0]
    assert item.metadata["state"] == state and item.status == status


def test_semaphore_native_zero_id_notification_test():
    value = payload("semaphore")
    value["attachments"][0].update(title="Task: Test Notification", text="execution #0, status: ✅ SUCCESS!")
    assert Parser("semaphore").parse(value)[0].metadata["state"] == "test"


@pytest.mark.parametrize("source", ["checkmk", "semaphore", "sonarr", "radarr", "metabase"])
def test_authenticated_native_http_inputs(source):
    install()
    path = next(path for path, application in ENDPOINTS.items() if application == source)
    assert SCOPED_SOURCES[source] == source
    token = "synthetic-source-token"
    with RunningServer(shared_secret=token) as server:
        assert request(server.port, path, payload(source)) == 401
        expected = 200 if source == "semaphore" else 204
        assert request(server.port, path, payload(source), {"Content-Type": "application/json", "X-Nowlert-Token": token}) == expected
        assert len(server.router.notifications) == 1
        assert server.router.notifications[0].metadata["_input_type"] == "HTTP"


def test_github_signature_verifies_exact_bytes_and_rejects_tampering():
    install()
    token = "synthetic-github-token"
    raw = json.dumps(payload("github_actions")).encode()
    signature = "sha256=" + hmac.new(token.encode(), raw, hashlib.sha256).hexdigest()
    with RunningServer(shared_secret=token) as server:
        for body, signature_value, expected in [(raw, signature, 204), (raw + b" ", signature, 401), (raw, "", 401)]:
            connection = http.client.HTTPConnection("127.0.0.1", server.port)
            connection.request("POST", f"/github/actions?token={token}", body=body, headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature_value})
            response = connection.getresponse()
            assert response.status == expected
            response.read()
            connection.close()
        assert len(server.router.notifications) == 1


def test_source_scope_cannot_be_reused_for_another_application():
    install()
    with RunningServer() as server:
        server.server.api.platform = object()
        scopes = []
        server.server.api.authorize_source = lambda headers, source, remote: scopes.append(source) or (source == "sonarr" and headers.get("X-Nowlert-Token") == "scoped-token")
        headers = {"Content-Type": "application/json", "X-Nowlert-Token": "scoped-token"}
        assert request(server.port, "/sonarr/events", payload("sonarr"), headers) == 204
        assert request(server.port, "/radarr/events", payload("radarr"), headers) == 401
        assert scopes == ["sonarr", "radarr"]


def test_metabase_native_empty_connection_probe_requires_source_authentication():
    install()
    with RunningServer() as server:
        server.server.api.platform = object()
        server.server.api.authorize_source = lambda headers, source, remote: (
            source == "metabase" and headers.get("X-Nowlert-Token") == "metabase-token"
        )
        for path, body, token, expected in [
            ("/metabase/alerts", b"", "wrong", 401),
            ("/metabase/alerts", b"", "metabase-token", 204),
            ("/metabase/alerts", b"{}", "metabase-token", 400),
            ("/sonarr/events", b"", "metabase-token", 401),
        ]:
            connection = http.client.HTTPConnection("127.0.0.1", server.port)
            connection.request("POST", path, body=body, headers={
                "Content-Type": "application/json", "X-Nowlert-Token": token,
            })
            response = connection.getresponse()
            assert response.status == expected
            response.read()
            connection.close()
        assert server.router.notifications == []
