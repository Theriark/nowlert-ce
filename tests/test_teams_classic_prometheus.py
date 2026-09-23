"""Microsoft Teams Classic rich Prometheus layout regressions."""

from __future__ import annotations

import json

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
        body=(
            "Request latency returned below the alert threshold."
            if resolved
            else "95th percentile latency exceeded two seconds."
        ),
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
        "labels": {"environment": "production"},
        "alert_count": 1,
        "group_members": [],
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
            for key in ("text", "title", "value"):
                raw = value.get(key)
                if isinstance(raw, str):
                    values.append(raw)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return "\n".join(values)


def classic_formatter():
    output = TeamsOutput()
    classic = output.classic_source_formatters["prometheus"]
    modern = output.source_formatters["prometheus"]

    assert isinstance(classic, PrometheusTeamsFormatter)
    assert isinstance(modern, PrometheusTeamsFormatter)
    assert classic is not modern
    assert classic.card_style == "classic"
    assert modern.card_style == "modern"
    return classic


def test_prometheus_classic_uses_rich_header_summary_details_and_footer():
    payload = classic_formatter().format(prometheus_notification())
    body = card_body(payload)
    text = flattened_text(payload)

    header = body[0]
    heading = header["columns"][0]["items"]
    badge = heading[3]["columns"][0]["items"][0]
    icon = header["columns"][1]["items"][0]

    assert heading[0]["text"] == "Prometheus"
    assert heading[2]["text"] == "HighRequestLatency"
    assert badge["style"] == "attention"
    assert badge["items"][0]["text"] == "🚨 Firing"
    assert "/prometheus.png" in icon["url"]

    assert body[1]["style"] == "emphasis"
    assert "95th percentile latency exceeded two seconds." in text

    summary = body[2]
    labels = [
        column["items"][0]["text"]
        for column in summary["columns"]
    ]
    assert labels == [
        "🚨 Severity",
        "📁 Category",
        "🕒 Event time",
    ]

    for label in (
        "📥 Receiver:",
        "🧩 Service:",
        "⚙️ Job:",
        "📦 Namespace:",
        "🏷️ Labels:",
        "▶️ Started:",
    ):
        assert label in text

    assert "environment=production" in text
    assert body[-1]["text"] == "Nowlert CE • Classic Card"
    assert "Nowlert CE • Modern Card" not in json.dumps(payload)


def test_prometheus_classic_resolved_is_green_and_keeps_resolved_time():
    payload = classic_formatter().format(
        prometheus_notification("resolved")
    )
    body = card_body(payload)
    text = flattened_text(payload)
    badge = body[0]["columns"][0]["items"][3]["columns"][0]["items"][0]

    assert badge["style"] == "good"
    assert badge["items"][0]["text"] == "✅ Resolved"
    assert "🏁 Resolved:" in text
    assert "23 Sep 2026" in text


def test_prometheus_classic_keeps_grouped_alerts_and_actions():
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

    payload = classic_formatter().format(item)
    text = flattened_text(payload)
    actions = payload["attachments"][0]["content"]["actions"]

    assert "👥 Alerts · 2" in text
    assert "ApiErrorRateHigh" in text
    assert "QueueDepthHigh" in text
    assert [action["title"] for action in actions] == [
        "Open Alertmanager",
        "Open Prometheus",
        "Open runbook",
    ]


def test_prometheus_classic_payload_is_bounded():
    formatter = classic_formatter()
    payload = formatter._sanitize_payload(
        formatter.format(prometheus_notification())
    )

    assert (
        TeamsOutput.payload_size(payload)
        <= TeamsOutput.MAX_PAYLOAD_BYTES
    )
