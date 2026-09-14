"""Regression coverage for CE Development/Stage matrix HTTP parity."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dispatcher import Dispatcher
from inputs import http as native_http
from inputs.http_matrix_parity import install


EXPECTED_SCOPED_SOURCES = {
    "network": "unifi_network",
    "protect": "unifi_protect",
    "drive": "unifi_drive",
    "portainer": "portainer",
    "proxmox": "proxmox",
    "synology": "synology",
    "grafana": "grafana",
}


def test_install_registers_all_matrix_http_application_token_sources():
    install()

    assert native_http.ENDPOINTS["/grafana/alerts"] == "grafana"
    for application, source in EXPECTED_SCOPED_SOURCES.items():
        assert native_http.SCOPED_SOURCES[application] == source


def test_platform_runtime_uses_application_token_auth_for_matrix_sources(monkeypatch):
    install()
    calls = []

    class API:
        platform = object()

        def authorize_source(self, headers, source, client):
            calls.append((source, client, headers.get("Authorization")))
            return object()

    handler = object.__new__(native_http.HTTPHandler)
    handler.server = SimpleNamespace(api=API(), shared_secret="legacy-shared-secret")
    handler.headers = {"Authorization": "Bearer matrix-token"}
    handler.client_address = ("10.42.20.67", 50000)
    monkeypatch.setattr(handler, "_authenticated", lambda path, query: False)

    assert handler._authenticated_application(
        "portainer",
        "/portainer/alerts",
        "",
    )
    assert calls == [("portainer", "10.42.20.67", "Bearer matrix-token")]


@pytest.mark.parametrize(
    "state,alert_count",
    (
        ("firing", 1),
        ("pending", 1),
        ("no_data", 1),
        ("error", 1),
        ("resolved", 1),
        ("test", 1),
        ("firing", 2),
    ),
)
def test_registered_grafana_boundary_accepts_all_matrix_profiles(state, alert_count):
    install()

    alerts = [
        {
            "status": state,
            "labels": {
                "alertname": f"Synthetic Grafana alert {index}",
                "severity": "warning",
            },
            "annotations": {"summary": "Synthetic matrix notification"},
        }
        for index in range(1, alert_count + 1)
    ]
    payload = {
        "status": state,
        "title": f"Synthetic Grafana {state}",
        "message": "Synthetic matrix notification",
        "alerts": alerts,
    }

    notification = Dispatcher().parse_webhook("grafana", payload)

    assert notification is not None
    assert notification.source == "grafana"
    assert notification.metadata["fixture_format"] == "webhook-json"
    assert notification.metadata["parser_confidence"] == "high"


def test_registered_grafana_boundary_rejects_unrelated_json():
    install()

    assert Dispatcher().parse_webhook("grafana", {"hello": "world"}) is None
