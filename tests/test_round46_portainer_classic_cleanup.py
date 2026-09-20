"""Round-46 Portainer Discord Classic cleanup contract."""

from __future__ import annotations

import json
from pathlib import Path

from outputs.discord import DiscordOutput
from parsers.portainer import Parser as PortainerParser


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "portainer"
    / "alert_firing.json"
)


def fixture_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def render(payload: dict) -> dict:
    item = PortainerParser().parse(payload)[0]
    return DiscordOutput().source_formatters["portainer"].format(item)["embeds"][0]


def test_portainer_auth_firing_uses_compact_operator_geometry():
    embed = render(fixture_payload())
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == (
        "⚠️ High authentication failures for a single user — Firing"
    )
    assert embed["description"] == (
        "Authentication failures exceeded the configured threshold."
    )
    assert embed["color"] == 0xF39C12

    assert list(fields) == [
        "⚠️ Alert",
        "📦 Portainer",
        "🔐 Authentication",
        "📈 Signal",
        "⏱️ Timing",
    ]
    assert fields["⚠️ Alert"] == "**Severity:** `warning`"
    assert fields["📦 Portainer"].splitlines() == [
        "**Instance:** `synthetic-portainer`",
        "**Area:** `security`",
    ]
    assert fields["🔐 Authentication"].splitlines() == [
        "**Method:** `local`",
        "**User:** `nowlert-discovery-test`",
    ]
    assert fields["📈 Signal"] == (
        "**Metric:** `authentication_failures_total`"
    )
    assert fields["⏱️ Timing"] == (
        "**Started:** `2026-07-14T15:45:00Z`"
    )

    rendered = repr(embed)
    assert "HighAuthenticationFailuresSingleUser" not in rendered
    assert "**State:**" not in rendered
    assert "**Rule:**" not in rendered
    assert "**Current:**" not in rendered
    assert "**Failures:**" not in rendered
    assert "**Threshold:**" not in rendered
    assert "**Window:**" not in rendered


def test_portainer_environment_firing_omits_irrelevant_authentication():
    payload = fixture_payload()

    for labels in (
        payload["commonLabels"],
        payload["alerts"][0]["labels"],
    ):
        labels["alertname"] = "PortainerEnvironmentUnreachable"
        labels["summary"] = "Portainer environment is unreachable"
        labels["severity"] = "critical"
        labels["alert_source"] = "environment"
        labels["alert_metric_name"] = "endpoint_health"
        labels["instance"] = "synthetic-portainer-edge"
        labels.pop("authentication_method", None)
        labels.pop("username", None)

    payload["commonAnnotations"]["description"] = (
        "The Portainer environment stopped responding to health checks."
    )
    payload["alerts"][0]["annotations"]["description"] = (
        "The Portainer environment stopped responding to health checks."
    )
    payload["alerts"][0]["startsAt"] = "2026-07-14T16:00:00Z"

    embed = render(payload)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == (
        "🚨 Portainer environment is unreachable — Firing"
    )
    assert embed["color"] == 0xE74C3C
    assert list(fields) == [
        "🚨 Alert",
        "📦 Portainer",
        "📈 Signal",
        "⏱️ Timing",
    ]
    assert "🔐 Authentication" not in fields
    assert fields["🚨 Alert"] == "**Severity:** `critical`"
    assert fields["📦 Portainer"].splitlines() == [
        "**Instance:** `synthetic-portainer-edge`",
        "**Area:** `environment`",
    ]
    assert fields["📈 Signal"] == "**Metric:** `endpoint_health`"


def test_portainer_resolved_keeps_only_started_and_resolved_timing():
    payload = fixture_payload()
    payload["status"] = "resolved"
    payload["alerts"][0]["status"] = "resolved"
    payload["alerts"][0]["labels"]["status"] = "resolved"
    payload["commonLabels"]["status"] = "resolved"
    payload["alerts"][0]["endsAt"] = "2026-07-14T15:50:00Z"

    embed = render(payload)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == (
        "✅ High authentication failures for a single user — Resolved"
    )
    assert embed["color"] == 0x2ECC71
    assert fields["✅ Alert"] == "**Severity:** `warning`"
    assert fields["⏱️ Timing"].splitlines() == [
        "**Started:** `2026-07-14T15:45:00Z`",
        "**Resolved:** `2026-07-14T15:50:00Z`",
    ]

    rendered = repr(embed)
    assert "**State:**" not in rendered
    assert "**Rule:**" not in rendered
