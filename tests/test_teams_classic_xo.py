"""Microsoft Teams Classic rich Xen Orchestra layout regressions."""

from __future__ import annotations

import json

import pytest

from formatters.teams import TeamsFormatter
from models import Notification
from outputs.teams import TeamsOutput


def xo_notification(status="success") -> Notification:
    return Notification(
        source="xo",
        category="backup",
        status=status,
        title="Daily Production Backup",
        subject="Backup report for Daily Production Backup",
        body="Backup report for Daily Production Backup",
        job_name="Daily Production Backup",
        job_id="JOB-123",
        mode="full",
        repository="UNAS-01 | NFS | Non-Critical Backups",
        duration="28 min",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        start_time="2026-09-22T20:53:04Z",
        end_time="2026-09-22T21:21:04Z",
        vm_total=3,
        vm_success=2,
        vm_failed=(
            1
            if status in {"failure", "failed", "error", "critical"}
            else 0
        ),
        vm_skipped=1 if status in {"skipped", "warning"} else 0,
        successful_vms=["VM-01 | Admin", "VM-06 | XO-02"],
        failed_vms=(
            ["VM-14 | Windows Server"]
            if status in {"failure", "failed", "error", "critical"}
            else []
        ),
        skipped_vms=(
            ["VM-12 | Maintenance Window"]
            if status in {"skipped", "warning"}
            else []
        ),
        vm_details={
            "VM-01 | Admin": {
                "size": "45.01 GiB",
                "speed": "33.73 MiB/s",
            },
            "VM-06 | XO-02": {
                "size": "3.42 GiB",
                "speed": "28.11 MiB/s",
            },
            "VM-14 | Windows Server": {
                "size": "23.66 GiB",
                "speed": "34.25 MiB/s",
                "error": "Body Timeout Error",
            },
            "VM-12 | Maintenance Window": {
                "size": "5.50 GiB",
                "error": (
                    "Backup policy excluded this VM during its "
                    "maintenance window"
                ),
            },
        },
    )


def card_body(payload):
    return payload["attachments"][0]["content"]["body"]


def flattened_text(payload):
    values = []

    def visit(value):
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                values.append(text)
            title = value.get("title")
            if isinstance(title, str):
                values.append(title)
            raw = value.get("value")
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
    formatter = TeamsOutput().classic_source_formatters["xo"]
    assert isinstance(formatter, TeamsFormatter)
    assert formatter.card_style == "classic"
    return formatter


@pytest.mark.parametrize(
    ("status", "badge_text", "badge_style"),
    (
        ("success", "✅ Backup Successful", "good"),
        ("failure", "🚨 Backup Failure", "attention"),
        ("skipped", "ℹ️ Backup Skipped", "accent"),
    ),
)
def test_xo_classic_uses_rich_header_badge_and_source_icon(
    status,
    badge_text,
    badge_style,
):
    payload = classic_formatter().format(xo_notification(status))
    body = card_body(payload)
    header = body[0]
    heading = header["columns"][0]["items"]
    badge = heading[3]["columns"][0]["items"][0]
    icon = header["columns"][1]["items"][0]

    assert heading[0]["text"] == "Xen Orchestra"
    assert heading[2]["text"] in {
        "Backup Successful",
        "Backup Failure",
        "Backup Skipped",
    }
    assert badge["style"] == badge_style
    assert badge["items"][0]["text"] == badge_text
    assert "/xen-orchestra.png" in icon["url"]


def test_xo_classic_matches_rich_report_summary_details_and_footer():
    payload = classic_formatter().format(xo_notification("success"))
    body = card_body(payload)
    text = flattened_text(payload)

    assert body[2]["style"] == "emphasis"
    assert "Backup report for Daily Production Backup" in text

    summary = body[3]
    labels = [
        column["items"][0]["text"]
        for column in summary["columns"]
    ]
    assert labels == [
        "✅ Severity",
        "🔄 Category",
        "🕒 Event time",
    ]

    assert "🧾 Event details" in text
    for label in (
        "🧰 Mode:",
        "⏱️ Duration:",
        "📦 Transfer size:",
        "💾 Repository:",
        "🚀 Speed:",
        "📊 Result:",
        "▶️ Started:",
        "🏁 Finished:",
    ):
        assert label in text

    assert "✅ Successful VMs" in text
    assert "VM-01 | Admin" in text
    assert "45.01 GiB" in text
    assert body[-1]["text"] == "Nowlert CE • Classic Card"
    assert "Nowlert CE • Modern Card" not in json.dumps(payload)


def test_xo_classic_keeps_failure_and_skipped_sections_dynamic():
    failed = flattened_text(
        classic_formatter().format(xo_notification("failure"))
    )
    skipped = flattened_text(
        classic_formatter().format(xo_notification("skipped"))
    )

    assert "❌ Failed VM" in failed
    assert "VM-14 | Windows Server" in failed
    assert "Body Timeout Error" in failed

    assert "⚠️ Skipped VM" in skipped
    assert "VM-12 | Maintenance Window" in skipped
    assert "maintenance window" in skipped


def test_xo_classic_is_sanitized_and_bounded():
    item = xo_notification("failure")
    item.vm_details["VM-14 | Windows Server"]["error"] = (
        "token=private-token timeout"
    )

    formatter = classic_formatter()
    payload = formatter._sanitize_payload(formatter.format(item))
    encoded = json.dumps(payload)

    assert "private-token" not in encoded
    assert "<redacted>" in encoded
    assert (
        TeamsOutput.payload_size(payload)
        <= TeamsOutput.MAX_PAYLOAD_BYTES
    )
