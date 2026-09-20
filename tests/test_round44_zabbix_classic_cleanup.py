"""Round-44 Zabbix Discord Classic cleanup contract."""

from __future__ import annotations

from email.message import EmailMessage

import pytest

from models import Notification
from outputs.discord import DiscordOutput
from parsers.zabbix import Parser as ZabbixParser


PROBLEM = "PostgreSQL replication lag exceeds 120 seconds"
HOST = "VM-08 | Zabbix Server"
TRIGGER = "max(/DB-REPLICA/pgsql.replication.lag,5m)>120"
RUNBOOK = "DB-RUNBOOK-REPLICATION-01"
EVENT_TAGS = "component=postgresql, scope=replication, site=development"


def zabbix_notification(event_type: str) -> Notification:
    state = {
        "problem": {
            "status": "failure",
            "subject": f"Problem: {PROBLEM}",
            "event_time": "2026-09-20 04:37:00",
            "duration": "4m 37s",
        },
        "update": {
            "status": "failure",
            "subject": f"Problem update: {PROBLEM}",
            "event_time": "2026-09-20 04:37:03",
            "duration": "8m 12s",
        },
        "recovery": {
            "status": "success",
            "subject": f"Resolved in 12m 41s: {PROBLEM}",
            "event_time": "2026-09-20 04:37:05",
            "duration": "12m 41s",
        },
    }[event_type]

    item = Notification(
        source="zabbix",
        category="monitoring",
        status=state["status"],
        title=PROBLEM,
        subject=state["subject"],
        body=f"Synthetic {event_type} Zabbix notification.",
        sender="Zabbix <zabbix@monitoring-development.invalid>",
        duration=state["duration"],
    )
    item.metadata = {
        "event_type": event_type,
        "problem_name": PROBLEM,
        "host": HOST,
        "severity": "High",
        "operational_data": (
            "replication_lag=146s; wal_receiver=connected; primary=DB-01"
        ),
        "problem_id": "3270662261",
        "event_time": state["event_time"],
        "to": "mock-ce-dev@nowlert.theriark.invalid",
        "fields": {
            "trigger expression": TRIGGER,
            "event tags": EVENT_TAGS,
            "runbook": RUNBOOK,
            "problem duration": state["duration"],
            "problem started": "at 04:37:00 on 2026.09.20",
            "problem updated": "at 04:37:03 on 2026.09.20",
            "problem has been resolved": "at 04:37:05 on 2026.09.20",
        },
    }
    return item


@pytest.mark.parametrize(
    ("event_type", "expected_title", "expected_problem_field", "expected_color", "time_label"),
    [
        ("problem", f"🚨 {PROBLEM}", "🚨 Problem", 0xE74C3C, "Started"),
        ("update", f"🔄 {PROBLEM} — Updated", "🔄 Problem", 0xF1C40F, "Updated"),
        ("recovery", f"✅ {PROBLEM} — Resolved", "✅ Problem", 0x2ECC71, "Resolved"),
    ],
)
def test_zabbix_classic_states_share_compact_operator_geometry(
    event_type,
    expected_title,
    expected_problem_field,
    expected_color,
    time_label,
):
    item = zabbix_notification(event_type)
    embed = DiscordOutput().source_formatters["zabbix"].format(item)["embeds"][0]
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == expected_title
    assert embed["color"] == expected_color
    assert list(fields) == [
        expected_problem_field,
        "📈 Operational Data",
        "🧪 Trigger",
        "🆔 Problem ID",
        "⏱️ Timing",
        "📘 Runbook",
    ]

    assert fields[expected_problem_field].splitlines() == [
        f"**Host:** `{HOST}`",
        "**Severity:** `High`",
    ]
    assert PROBLEM not in fields[expected_problem_field]
    assert fields["📈 Operational Data"] == (
        "`replication_lag=146s; wal_receiver=connected; primary=DB-01`"
    )
    assert fields["🧪 Trigger"] == f"`{TRIGGER}`"
    assert fields["🆔 Problem ID"] == "`3270662261`"
    assert f"**{time_label}:** `{item.metadata['event_time']}`" in fields["⏱️ Timing"]
    assert f"**Duration:** `{item.duration}`" in fields["⏱️ Timing"]
    assert fields["📘 Runbook"] == f"`{RUNBOOK}`"

    rendered = repr(embed)
    assert EVENT_TAGS not in rendered
    assert "📧 Email" not in rendered
    assert "✉️ Subject" not in rendered
    assert "📎 Problem Started" not in rendered
    assert "📎 Problem Updated" not in rendered
    assert "📎 Problem Has Been Resolved" not in rendered
    assert "zabbix@monitoring-development.invalid" not in rendered
    assert "mock-ce-dev@nowlert.theriark.invalid" not in rendered


def test_zabbix_parser_classifies_problem_update_and_preserves_source_fields():
    message = EmailMessage()
    message["From"] = "Zabbix <zabbix@monitoring-development.invalid>"
    message["To"] = "mock-ce-dev@nowlert.theriark.invalid"
    message["Subject"] = f"Problem update: {PROBLEM}"
    message.set_content("Synthetic Zabbix update.")
    message.add_alternative(
        (
            "<html><body>"
            f"<b>Problem name:</b> {PROBLEM}<br>"
            f"<b>Host:</b> {HOST}<br>"
            "<b>Severity:</b> High<br>"
            "<b>Operational data:</b> "
            "replication_lag=146s; wal_receiver=connected; primary=DB-01<br>"
            "<b>Original problem ID:</b> 3270662261<br>"
            f"<b>Trigger expression:</b> {TRIGGER}<br>"
            f"<b>Event tags:</b> {EVENT_TAGS}<br>"
            "<b>Problem duration:</b> 8m 12s<br>"
            "<b>Problem Updated:</b> at 04:37:03 on 2026.09.20<br>"
            f"<b>Runbook:</b> {RUNBOOK}<br>"
            "</body></html>"
        ),
        subtype="html",
    )

    notification = ZabbixParser().parse(message)

    assert notification.status == "failure"
    assert notification.title == PROBLEM
    assert notification.start_time == "2026-09-20 04:37:03"
    assert notification.duration == "8m 12s"
    assert notification.metadata["event_type"] == "update"
    assert notification.metadata["event_time"] == "2026-09-20 04:37:03"
    assert notification.metadata["fields"]["event tags"] == EVENT_TAGS
    assert notification.metadata["fields"]["problem updated"] == (
        "at 04:37:03 on 2026.09.20"
    )
