"""Teams Modern standardized card regressions."""

from __future__ import annotations

import pytest

from formatters.teams_common import TeamsCardData, TeamsCardFormatter
from formatters.teams_generic import GenericTeamsFormatter
from models import Notification
from outputs.teams import TeamsOutput


SOURCES = (
    "xo",
    "zabbix",
    "grafana",
    "portainer",
    "proxmox",
    "qnap",
    "synology",
    "truenas",
    "unifi_network",
    "unifi_protect",
    "unifi_drive",
    "supermicro",
    "hpe_ilo",
    "dell_idrac",
    "home_assistant",
    "redfish",
    "generic",
)


def notification(source: str) -> Notification:
    item = Notification(
        source="home_lab" if source == "generic" else source,
        category="storage",
        status="warning",
        title="Synthetic modern event",
        subject="Synthetic modern event",
        body="Synthetic event body that must remain readable in Teams.",
        job_name="Synthetic backup",
        repository="Repository-01",
        start_time="2026-09-22T19:00:00Z",
        end_time="2026-09-22T19:05:00Z",
        duration="5 min",
    )
    item.metadata = {
        "provider": "Synthetic provider",
        "host": "LAB-01",
        "hostname": "LAB-01",
        "system": "LAB-01",
        "device": "LAB-01",
        "instance": "LAB-01",
        "node": "PVE-01",
        "nas_name": "NAS-01",
        "controller": "UDM-01",
        "area": "Server room",
        "service": "automation.turn_on",
        "entity_id": "sensor.lab",
        "problem_name": "Synthetic Zabbix problem",
        "severity": "warning",
        "event_time": "2026-09-22T19:05:00Z",
        "application": "Synthetic application",
        "event_type": "storage warning",
        "message": "Synthetic modern event",
        "alert_name": "Synthetic Grafana alert",
        "state": "warning",
        "alert_count": 1,
        "alerts": [{"event_type": "new", "message": "Synthetic alert"}],
        "client_display_name": "Synthetic client",
        "wifi_name": "Synthetic Wi-Fi",
        "trigger_key": "motion",
        "trigger_device": "Synthetic camera",
        "backup_task": "Synthetic backup",
        "alert_source": "portainer",
        "storage": "backup-nfs",
        "model": "SYNTHETIC-MODEL",
        "storage_pool": "Synthetic Pool",
        "sensor": "Temp 1",
        "message_id": "Synthetic.Message.1",
        "source_ip": "192.0.2.10",
        "recommended_action": "Inspect the affected component.",
    }
    return item


def card_for(source: str) -> dict:
    output = TeamsOutput()
    formatter = (
        output.default_formatter
        if source == "generic"
        else output.source_formatters[source]
    )
    return formatter.format(notification(source))["attachments"][0]["content"]


def lifecycle_badge(card: dict) -> dict:
    header = card["body"][0]
    heading_items = header["columns"][0]["items"]
    badge_row = next(
        item
        for item in heading_items
        if item.get("type") == "ColumnSet"
    )
    return badge_row["columns"][0]["items"][0]


@pytest.mark.parametrize("source", SOURCES)
def test_every_teams_modern_source_uses_shared_visual_shell(source):
    card = card_for(source)
    header = card["body"][0]
    footer = card["body"][-1]

    assert header["type"] == "ColumnSet"
    assert header["columns"][0]["items"][0]["type"] == "TextBlock"
    assert header["columns"][0]["items"][0]["weight"] == "Bolder"
    assert header["columns"][0]["items"][2]["size"] == "Medium"
    assert header["columns"][0]["items"][2]["wrap"] is True

    badge = lifecycle_badge(card)
    assert badge["type"] == "Container"
    assert badge["style"] in {"accent", "attention", "good", "warning"}
    assert badge["items"][0]["weight"] == "Bolder"
    assert badge["items"][0]["wrap"] is True

    assert card["body"][2]["type"] == "Container"
    assert card["body"][2]["style"] == "emphasis"
    assert card["body"][2]["items"][0]["wrap"] is True

    metrics = card["body"][3]
    assert metrics["type"] == "ColumnSet"
    assert metrics["separator"] is True
    assert metrics["columns"][0]["items"][1]["weight"] == "Bolder"

    assert footer["text"] == TeamsCardFormatter.MODERN_FOOTER
    assert footer["text"] == "Nowlert CE • Modern Card"
    assert footer["separator"] is True


@pytest.mark.parametrize(
    ("status", "severity", "expected_style"),
    (
        ("success", "critical", "good"),
        ("failure", "information", "attention"),
        ("warning", "information", "warning"),
        ("information", "information", "accent"),
    ),
)
def test_teams_modern_lifecycle_badge_uses_native_status_style(
    status,
    severity,
    expected_style,
):
    formatter = GenericTeamsFormatter()
    payload = formatter._render_teams_card(
        TeamsCardData(
            source="nowlert",
            integration="Nowlert",
            device="LAB-01",
            event="Synthetic lifecycle event",
            message="Synthetic lifecycle event body.",
            status=status,
            severity=severity,
            category="system",
            source_area="Nowlert",
            event_time="2026-09-22T19:05:00Z",
        )
    )
    card = payload["attachments"][0]["content"]

    assert lifecycle_badge(card)["style"] == expected_style


def test_teams_modern_long_text_wraps_without_fixed_height():
    formatter = GenericTeamsFormatter()
    long_text = " ".join(["long-event-detail"] * 220)
    payload = formatter._render_teams_card(
        TeamsCardData(
            source="nowlert",
            integration="Nowlert",
            device="LAB-01",
            event=long_text,
            message=long_text,
            status="warning",
            severity="warning",
            category="system",
            source_area="Platform",
            event_time="2026-09-22T19:05:00Z",
        )
    )
    card = payload["attachments"][0]["content"]
    header_event = card["body"][0]["columns"][0]["items"][2]
    message = card["body"][2]["items"][0]

    assert header_event["wrap"] is True
    assert message["wrap"] is True
    assert "height" not in header_event
    assert "height" not in message
    assert len(message["text"]) <= 4000
