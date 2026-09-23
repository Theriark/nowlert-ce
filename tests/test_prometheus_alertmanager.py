"""Prometheus Alertmanager integration contract."""

from __future__ import annotations

import copy
import http.client
import json
import threading

from dispatcher import Dispatcher
from formatters.discord_prometheus import PrometheusDiscordFormatter
from formatters.teams_prometheus import PrometheusTeamsFormatter
from inputs.http import HTTPServer
from outputs.discord import DiscordOutput
from outputs.teams import TeamsOutput
from parsers.prometheus import Parser


def alertmanager_payload() -> dict:
    return {
        "version": "4",
        "groupKey": "synthetic-prometheus-group",
        "truncatedAlerts": 0,
        "status": "firing",
        "receiver": "nowlert-critical",
        "groupLabels": {"alertname": "HighRequestLatency"},
        "commonLabels": {
            "alertname": "HighRequestLatency",
            "severity": "critical",
            "instance": "api-01:9090",
            "job": "api-server",
            "service": "checkout",
            "namespace": "production",
            "environment": "production",
        },
        "commonAnnotations": {
            "summary": "High request latency",
            "description": "95th percentile latency exceeded two seconds.",
            "runbook_url": (
                "https://runbooks.example.invalid/high-request-latency"
            ),
        },
        "externalURL": "https://alertmanager.example.invalid",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighRequestLatency",
                    "severity": "critical",
                    "instance": "api-01:9090",
                    "job": "api-server",
                    "service": "checkout",
                    "namespace": "production",
                    "environment": "production",
                },
                "annotations": {
                    "summary": "High request latency",
                    "description": (
                        "95th percentile latency exceeded two seconds."
                    ),
                },
                "startsAt": "2026-09-23T08:30:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": (
                    "https://prometheus.example.invalid/graph?g0.expr=latency"
                ),
                "fingerprint": "synthetic-fingerprint-001",
            }
        ],
    }


def test_parser_normalizes_firing_and_resolved_alertmanager_groups():
    payload = alertmanager_payload()
    firing = Parser().parse(payload)

    assert firing.source == "prometheus"
    assert firing.category == "monitoring"
    assert firing.status == "failure"
    assert firing.title == "HighRequestLatency"
    assert firing.metadata["severity"] == "critical"
    assert firing.metadata["instance"] == "api-01:9090"
    assert firing.metadata["alert_count"] == 1

    resolved_payload = copy.deepcopy(payload)
    resolved_payload["status"] = "resolved"
    resolved_payload["alerts"][0]["status"] = "resolved"
    resolved_payload["alerts"][0]["endsAt"] = "2026-09-23T08:42:00Z"
    resolved = Parser().parse(resolved_payload)

    assert resolved.status == "success"
    assert resolved.metadata["state"] == "resolved"
    assert resolved.end_time == "2026-09-23T08:42:00Z"


def test_parser_handles_grouped_and_minimal_alerts():
    grouped = alertmanager_payload()
    second = copy.deepcopy(grouped["alerts"][0])
    second["labels"]["alertname"] = "WorkerFailures"
    second["labels"]["severity"] = "warning"
    second["labels"]["instance"] = "worker-02:9090"
    grouped["alerts"].append(second)
    grouped["commonLabels"].pop("alertname")
    grouped["commonLabels"].pop("severity")

    item = Parser().parse(grouped)
    assert item.title == "Prometheus alert group"
    assert item.status == "failure"
    assert item.metadata["alert_count"] == 2
    assert len(item.metadata["group_members"]) == 2

    minimal = {
        "version": "4",
        "status": "firing",
        "receiver": "default",
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "Watchdog"},
                "annotations": {},
                "startsAt": "2026-09-23T08:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "",
                "fingerprint": "watchdog",
            }
        ],
    }
    item = Parser().parse(minimal)
    assert item.title == "Watchdog"
    assert item.status == "warning"
    assert item.metadata["severity"] == "unspecified"


def test_dispatcher_rejects_invalid_prometheus_envelopes():
    invalid = {
        "version": "99",
        "status": "firing",
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "alerts": [
            {
                "status": "firing",
                "labels": {},
                "annotations": {},
            }
        ],
    }
    assert Parser.is_envelope(invalid) is False
    assert Dispatcher().parse_webhook("prometheus", invalid) is None


class _Router:
    def __init__(self):
        self.items = []

    def route(self, item):
        self.items.append(item)
        return True


def test_native_prometheus_http_endpoint_uses_nowlert_token():
    router = _Router()
    server = HTTPServer(
        ("127.0.0.1", 0),
        Dispatcher(),
        router,
        1_048_576,
        "synthetic-secret",
    )
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        port = server.server_port

        def send(token=""):
            connection = http.client.HTTPConnection(
                "127.0.0.1",
                port,
                timeout=2,
            )
            headers = {"Content-Type": "application/json"}
            if token:
                headers["X-Nowlert-Token"] = token
            connection.request(
                "POST",
                "/prometheus/alerts",
                body=json.dumps(alertmanager_payload()),
                headers=headers,
            )
            response = connection.getresponse()
            status = response.status
            response.read()
            connection.close()
            return status

        assert send() == 401
        assert send("wrong") == 401
        assert send("synthetic-secret") == 204
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert len(router.items) == 1
    assert router.items[0].source == "prometheus"
    assert router.items[0].metadata["_input_type"] == "HTTP"


def test_prometheus_formatters_and_classic_card_are_registered():
    assert isinstance(
        DiscordOutput().source_formatters["prometheus"],
        PrometheusDiscordFormatter,
    )
    assert isinstance(
        TeamsOutput().source_formatters["prometheus"],
        PrometheusTeamsFormatter,
    )

    payload = alertmanager_payload()
    item = Parser().parse(payload)
    embed = PrometheusDiscordFormatter().format(item)["embeds"][0]
    fields = {
        field["name"]: field["value"]
        for field in embed["fields"]
    }

    assert embed["title"] == "🚨 HighRequestLatency — Firing"
    assert embed["color"] == 0xE74C3C
    assert "Critical" in fields["🚨 Alert"]
    assert "api-01:9090" in fields["🎯 Target"]
    assert "nowlert-critical" in fields["📈 Prometheus"]
    assert "environment=production" in fields["🏷️ Labels"]
    assert (
        "[Alertmanager](https://alertmanager.example.invalid)"
        in fields["🔗 Links"]
    )
    assert (
        "[Prometheus]("
        "https://prometheus.example.invalid/graph?g0.expr=latency)"
        in fields["🔗 Links"]
    )
    assert (
        "[Runbook]("
        "https://runbooks.example.invalid/high-request-latency)"
        in fields["🔗 Links"]
    )

    rendered = repr(embed)
    assert payload["groupKey"] not in rendered
    assert payload["alerts"][0]["fingerprint"] not in rendered
