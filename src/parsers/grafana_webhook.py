"""Normalize authenticated Grafana Alerting webhook JSON into Nowlert events."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from models import Notification
from parsers.grafana import Parser as GrafanaEmailParser


_STATE_NAMES = {
    "firing": "Firing",
    "pending": "Pending",
    "no data": "No Data",
    "nodata": "No Data",
    "error": "Error",
    "resolved": "Resolved",
    "normal": "Resolved",
    "test": "Test",
    "information": "Test",
}

_SEVERITY_BY_STATE = {
    "Firing": "Critical",
    "Pending": "Warning",
    "No Data": "Warning",
    "Error": "Error",
    "Resolved": "Normal",
    "Test": "Information",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return re.sub(r"\s+", " ", str(value)).strip()
    return ""


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _alerts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("alerts")
    if not isinstance(raw, list):
        return []
    return [item for item in raw[:100] if isinstance(item, dict)]


def _lookup(mapping: dict[str, Any], *names: str) -> str:
    folded = {str(key).casefold(): value for key, value in mapping.items()}
    for name in names:
        value = _text(folded.get(name.casefold()))
        if value:
            return value
    return ""


def _state_name(*values: Any) -> str:
    for value in values:
        normalized = re.sub(
            r"\s+",
            " ",
            _text(value).casefold().replace("_", " ").replace("-", " "),
        ).strip()
        if normalized in _STATE_NAMES:
            return _STATE_NAMES[normalized]
    return ""


def _timestamp(value: Any) -> str:
    raw = _text(value)
    if not raw or raw.startswith("0001-"):
        return ""
    candidate = raw
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return raw
    if parsed.year <= 1:
        return ""
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _mapping_text(value: Any, *, excluded: set[str] | None = None) -> str:
    if not isinstance(value, dict):
        return _text(value)
    excluded = {item.casefold() for item in (excluded or set())}
    parts = []
    for key, item in value.items():
        name = _text(key)
        rendered = _text(item)
        if not name or not rendered or name.casefold() in excluded:
            continue
        parts.append(f"{name}={rendered}")
    return ", ".join(parts)


def is_envelope(payload: Any) -> bool:
    """Accept bounded Grafana Alerting webhook objects, not arbitrary JSON."""
    if not isinstance(payload, dict) or len(payload) > 128:
        return False
    raw_alerts = payload.get("alerts")
    if raw_alerts is not None:
        if not isinstance(raw_alerts, list) or len(raw_alerts) > 100:
            return False
        if any(not isinstance(item, dict) for item in raw_alerts):
            return False
    signals = (
        payload.get("status"),
        payload.get("state"),
        payload.get("title"),
        payload.get("message"),
        payload.get("receiver"),
    )
    return bool(raw_alerts) or any(_text(value) for value in signals)


def parse_webhook(payload: dict[str, Any]) -> Notification:
    """Map Grafana's webhook schema onto the established Grafana metadata contract."""
    if not is_envelope(payload):
        raise ValueError("invalid Grafana webhook envelope")

    alerts = _alerts(payload)
    first = alerts[0] if alerts else {}
    first_labels = _mapping(first.get("labels"))
    common_labels = _mapping(payload.get("commonLabels"))
    labels = {**common_labels, **first_labels}
    first_annotations = _mapping(first.get("annotations"))
    common_annotations = _mapping(payload.get("commonAnnotations"))
    annotations = {**common_annotations, **first_annotations}

    state = _state_name(
        payload.get("state"),
        first.get("state"),
        first.get("status"),
        payload.get("status"),
    )
    if not state:
        state = "Firing" if alerts else "Test"

    severity = (
        _text(payload.get("severity"))
        or _lookup(labels, "severity", "level", "priority")
        or _SEVERITY_BY_STATE.get(state, "Information")
    )

    title = _text(payload.get("title"))
    alert_name = (
        _text(payload.get("alertName"))
        or _lookup(labels, "alertname", "alert_name", "name")
    )
    if not alert_name and title:
        alert_name = re.sub(r"^\[[^]]+\]\s*", "", title).strip()
    alert_name = alert_name or "Grafana alert"

    alert_rule = (
        _text(payload.get("ruleName"))
        or _lookup(labels, "rulename", "rule_name", "rule")
        or alert_name
    )
    folder = _lookup(labels, "grafana_folder", "folder")
    dashboard = _lookup(annotations, "dashboard", "dashboard_name") or _lookup(
        labels, "dashboard", "dashboard_name"
    )
    panel = _lookup(annotations, "panel", "panel_name") or _lookup(
        labels, "panel", "panel_name"
    )
    datasource = _lookup(annotations, "datasource", "data_source") or _lookup(
        labels, "datasource", "data_source"
    )
    organization = _text(payload.get("orgName")) or _text(payload.get("orgId"))

    summary = _lookup(annotations, "summary") or _text(payload.get("summary"))
    description = _lookup(annotations, "description") or _text(payload.get("description"))
    message = (
        _text(payload.get("message"))
        or _lookup(annotations, "message")
        or summary
        or description
        or title
        or alert_name
    )
    subject = title or f"[{state.upper()}:{max(1, len(alerts))}] {alert_name}"

    values = first.get("values")
    values_text = _mapping_text(values) or _text(first.get("valueString"))
    labels_text = _mapping_text(
        labels,
        excluded={"alertname", "alert_name", "grafana_folder", "severity", "rulename", "rule_name"},
    )

    starts_at = _timestamp(first.get("startsAt"))
    ends_at = _timestamp(first.get("endsAt"))
    event_time = ends_at if state == "Resolved" and ends_at else starts_at or ends_at

    source_fields: dict[str, str] = {
        "alert count": str(max(1, len(alerts))),
        "alert name": alert_name,
        "alert rule": alert_rule,
        "state": state,
        "severity": severity,
        "folder": folder,
        "dashboard": dashboard,
        "panel": panel,
        "organization": organization,
        "datasource": datasource,
        "labels": labels_text,
        "values": values_text,
        "summary": summary,
        "description": description,
        "message": message,
        "starts at": starts_at,
        "ends at": ends_at,
        "event time": event_time,
        "dashboard url": _text(first.get("dashboardURL")),
        "panel url": _text(first.get("panelURL")),
        "silence url": _text(first.get("silenceURL")),
        "rule url": _text(first.get("generatorURL")),
    }
    source_fields = {key: value for key, value in source_fields.items() if value}

    service = _lookup(labels, "service")
    if service:
        source_fields["service"] = service
    if isinstance(values, dict):
        for key, value in values.items():
            rendered = _text(value)
            if rendered and _text(key):
                source_fields.setdefault(_text(key).casefold(), rendered)

    evaluation_error = _lookup(
        annotations,
        "evaluation_error",
        "evaluation error",
        "error",
        "error_message",
    )
    if evaluation_error and state == "Error":
        source_fields["evaluation error"] = evaluation_error

    if len(alerts) > 1:
        for index, alert in enumerate(alerts, start=1):
            alert_labels = _mapping(alert.get("labels"))
            name = _lookup(alert_labels, "alertname", "alert_name", "name")
            alert_state = _state_name(alert.get("state"), alert.get("status")) or state
            alert_values = _mapping_text(alert.get("values")) or _text(alert.get("valueString"))
            if name:
                source_fields[f"alert {index}"] = name
            if alert_state:
                source_fields[f"alert {index} state"] = alert_state
            if alert_values:
                source_fields[f"alert {index} values"] = alert_values

    notification = Notification(
        source="grafana",
        category="generic",
        status="information",
        title=subject,
        subject=subject,
        body=message,
    )
    notification.metadata = {}

    parser = GrafanaEmailParser()
    parser._populate_notification(notification, source_fields, "webhook-json")
    notification.metadata["parser_confidence"] = "high"
    notification.metadata["fixture_format"] = "webhook-json"
    return notification


__all__ = ["is_envelope", "parse_webhook"]
