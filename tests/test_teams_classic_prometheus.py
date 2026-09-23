"""Microsoft Teams Classic Prometheus card regressions."""

from __future__ import annotations

from formatters.teams_classic_v1 import (
    CLASSIC_FOOTER,
    TeamsClassicPrometheusFormatter,
)
from formatters.teams_prometheus import PrometheusTeamsFormatter
from models import Notification
from outputs.teams import TeamsOutput


def prometheus_notification(state="firing") -> Notification:
    resolved = state == "resolved"
    item = Notification(
        source="prometheus",
        category="monitoring",
        status="success" if resolved else "failure",
        title="HighRequestLatency",
        subject="HighRequestLatency",
        body="95th percentile latency exceeded two seconds.",
        start_time="2026-09-23T02:00:00Z",
        end_time="2026-09-23T02:02:00Z" if resolved else "",
    )
    item.metadata = {
        "state": state,
        "severity": "critical",
        "instance": "api-01:9090",
        "service": "checkout",
        "job": "api-server",
        "namespace": "production",
        "pod": "",
        "node": "",
        "receiver": "nowlert-critical",
        "notification_reason": "",
        "truncated_alerts": 0,
        "labels": "environment=production",
        "alert_count": 1,
        "group_members": [],
        "description": (
            "Request latency returned below the alert threshold."
            if resolved
            else "95th percentile latency exceeded two seconds."
        ),
        "external_url": "https://alertmanager.example.invalid",
        "generator_url": (
            "https://prometheus.example.invalid/graph?g0.expr=latency"
        ),
        "runbook_url": (
            "https://runbooks.example.invalid/high-request-latency"
        ),
    }
    return item


def card_body(payload):
    return payload["attachments"][0]["content"]["body"]


def flattened_text(payload):
    values = []

    def visit(value):
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                values.append(text)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return "\n".join(values)


def section_value(payload, title):
    for item in card_body(payload):
        if item.get("type") != "Container":
            continue
        blocks = item.get("items") or []
        if (
            blocks
            and blocks[0].get("text") == title
            and len(blocks) > 1
        ):
            return blocks[1].get("text") or ""
    return ""


def test_prometheus_classic_formatter_is_registered_without_touching_modern():
    output = TeamsOutput()

    assert isinstance(
        output.classic_source_formatters["prometheus"],
        TeamsClassicPrometheusFormatter,
    )
    assert isinstance(
        output.source_formatters["prometheus"],
        PrometheusTeamsFormatter,
    )


def test_prometheus_classic_uses_xo_style_summary_and_sections():
    formatter = TeamsClassicPrometheusFormatter()
    payload = formatter.format(prometheus_notification())
    body = card_body(payload)
    text = flattened_text(payload)

    summary = body[2]
    assert summary["type"] == "ColumnSet"
    labels = [
        column["items"][0]["text"]
        for column in summary["columns"]
    ]
    values = [
        column["items"][1]["text"]
        for column in summary["columns"]
    ]

    assert labels == [
        "🚨 Severity",
        "🎯 Target",
        "📥 Receiver",
    ]
    assert values == [
        "Critical",
        "api-01:9090",
        "nowlert-critical",
    ]

    expected_order = [
        "📈 Prometheus",
        "🏷️ Labels",
        "⏱️ Timing",
        "🔗 Links",
    ]
    positions = [text.index(label) for label in expected_order]
    assert positions == sorted(positions)

    prometheus = section_value(payload, "📈 Prometheus")
    assert "**Service:** checkout" in prometheus
    assert "**Job:** api-server" in prometheus
    assert "**Namespace:** production" in prometheus
    assert "Receiver" not in prometheus

    assert "environment=production" in text
    assert "Alertmanager" in text
    assert "Prometheus" in text
    assert "Runbook" in text
    assert CLASSIC_FOOTER in text
    assert "`" not in text
    assert (
        TeamsOutput.payload_size(payload)
        <= TeamsOutput.MAX_PAYLOAD_BYTES
    )


def test_prometheus_classic_resolved_keeps_started_and_resolved_times():
    payload = TeamsClassicPrometheusFormatter().format(
        prometheus_notification("resolved")
    )
    text = flattened_text(payload)
    timing = section_value(payload, "⏱️ Timing")

    assert "✅ HighRequestLatency — Resolved" in text
    assert "**Started:** 2026-09-23T02:00:00Z" in timing
    assert "**Resolved:** 2026-09-23T02:02:00Z" in timing


def test_prometheus_classic_keeps_grouped_alerts_compact():
    item = prometheus_notification()
    item.title = "Prometheus alert group"
    item.metadata["alert_count"] = 2
    item.metadata["group_members"] = [
        {
            "title": "ApiErrorRateHigh",
            "state": "firing",
            "severity": "critical",
            "target": "api-02:9090",
        },
        {
            "title": "QueueDepthHigh",
            "state": "firing",
            "severity": "warning",
            "target": "worker-02:9090",
        },
    ]

    payload = TeamsClassicPrometheusFormatter().format(item)
    alerts = section_value(payload, "👥 Alerts · 2")

    assert (
        "**ApiErrorRateHigh** · Firing · Critical · api-02:9090"
        in alerts
    )
    assert (
        "**QueueDepthHigh** · Firing · Warning · worker-02:9090"
        in alerts
    )


def test_prometheus_classic_omits_empty_optional_summary_and_sections():
    item = prometheus_notification()
    for key in (
        "instance",
        "service",
        "job",
        "namespace",
        "pod",
        "node",
        "labels",
        "external_url",
        "generator_url",
        "runbook_url",
    ):
        item.metadata[key] = ""

    payload = TeamsClassicPrometheusFormatter().format(item)
    body = card_body(payload)
    text = flattened_text(payload)
    summary = body[2]

    labels = [
        column["items"][0]["text"]
        for column in summary["columns"]
    ]
    assert labels == ["🚨 Severity", "📥 Receiver"]
    assert "📈 Prometheus" not in text
    assert "🏷️ Labels" not in text
    assert "🔗 Links" not in text
