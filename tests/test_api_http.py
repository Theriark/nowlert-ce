"""End-to-end HTTP transport tests for the v1.9 backend boundary."""

from __future__ import annotations

import http.client
import json
import threading

from io import BytesIO

from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

import inputs.http as http_module

from api.audit import AuditLog
from api.security import hash_token
from dispatcher import Dispatcher
from inputs.http import HTTPServer
from outputs.teams_modern_image import publish_teams_modern_image


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
    def __init__(self):
        self.items = []

    def route(self, item):
        self.items.append(item)
        return True


class RunningServer:
    def __init__(self, monkeypatch, tmp_path, limit=60):
        secret = "synthetic-v190-api-secret"
        configuration = Configuration({
            "api": {
                "enabled": True,
                "tokens": {
                    "client": {
                        "token_sha256": hash_token(secret),
                        "role": "application",
                        "sources": ["home_assistant", "home_lab"],
                        "rate_limit_per_minute": limit,
                    }
                },
            }
        })
        monkeypatch.setattr(http_module, "config", configuration)
        self.secret = secret
        self.router = Router()
        self.server = HTTPServer(
            ("127.0.0.1", 0), Dispatcher(), self.router, 1_048_576, ""
        )
        self.server.api.audit = AuditLog(tmp_path / "audit.log")
        self.thread = threading.Thread(target=self.server.serve_forever)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def request(port, method, path, payload=None, token=""):
    headers = {}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    status = response.status
    raw = response.read()
    connection.close()
    return status, json.loads(raw) if raw else None


def raw_request(port, method, path):
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        port,
        timeout=2,
    )
    connection.request(method, path)
    response = connection.getresponse()
    status = response.status
    content_type = response.getheader("Content-Type")
    cache_control = response.getheader("Cache-Control")
    raw = response.read()
    connection.close()
    return status, content_type, cache_control, raw


def event(source="home_lab"):
    return {
        "schema": "nowlert.event.v1",
        "source": source,
        "title": "Synthetic API event",
        "message": "End-to-end backend transport validation.",
        "severity": "information",
    }


def home_assistant_event():
    return {
        "schema": "nowlert.home_assistant.v1",
        "title": "Synthetic Home Assistant event",
        "message": "Source-scoped transport validation.",
        "severity": "information",
        "entity_id": "binary_sensor.synthetic_validation",
        "tags": ["synthetic"],
    }


def test_health_and_generic_event_transport(monkeypatch, tmp_path):
    with RunningServer(monkeypatch, tmp_path) as running:
        port = running.server.server_port
        health = request(port, "GET", "/api/health")
        missing = request(port, "POST", "/api/events", event())
        accepted = request(port, "POST", "/api/events", event(), running.secret)

    assert health[0] == 200
    assert health[1]["version"] == "3.1.6"
    assert missing[0] == 401
    assert accepted == (202, {"accepted": True, "delivered": True})
    assert [item.source for item in running.router.items] == ["home_lab"]


def test_source_endpoint_uses_api_scope_without_global_secret(monkeypatch, tmp_path):
    with RunningServer(monkeypatch, tmp_path) as running:
        port = running.server.server_port
        missing = request(port, "POST", "/home-assistant/events", home_assistant_event())
        accepted = request(
            port,
            "POST",
            "/home-assistant/events",
            home_assistant_event(),
            running.secret,
        )

    assert (missing[0], accepted[0]) == (401, 204)
    assert [item.source for item in running.router.items] == ["home_assistant"]


def test_teams_modern_media_uses_path_below_public_health_prefix(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "NOWLERT_STATE_DIR",
        str(tmp_path / "state"),
    )
    monkeypatch.setenv(
        "NOWLERT_TEAMS_PUBLIC_BASE_URL",
        "https://nowlert.example.test",
    )

    stream = BytesIO()
    Image.new("RGB", (32, 24), (8, 12, 15)).save(
        stream,
        format="PNG",
    )

    with RunningServer(monkeypatch, tmp_path) as running:
        url = publish_teams_modern_image(
            http_module.config,
            stream.getvalue(),
        )
        assert url is not None
        path = urlsplit(url).path

        card = raw_request(
            running.server.server_port,
            "GET",
            path,
        )
        missing = raw_request(
            running.server.server_port,
            "GET",
            "/api/health/teams-modern-card/"
            + ("0" * 48)
            + ".png",
        )
        health = request(
            running.server.server_port,
            "GET",
            "/api/health",
        )

    assert card[0] == 200
    assert card[1] == "image/png"
    assert card[2] == "public, max-age=86400, immutable"
    assert card[3].startswith(b"\x89PNG")
    assert missing[0] == 404
    assert health[0] == 200
    assert health[1]["version"] == "3.1.6"


def test_api_rate_limit_returns_429(monkeypatch, tmp_path):
    with RunningServer(monkeypatch, tmp_path, limit=1) as running:
        port = running.server.server_port
        first = request(port, "POST", "/api/events", event(), running.secret)
        second = request(port, "POST", "/api/events", event(), running.secret)

    assert first[0] == 202
    assert second == (429, {"error": "rate limit exceeded"})
