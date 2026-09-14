"""Regression coverage for CE Development/Stage matrix HTTP parity."""

from __future__ import annotations

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
