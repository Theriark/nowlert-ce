"""Slack Classic Xen Orchestra card contract."""

from __future__ import annotations

from formatters.slack import CLASSIC_FOOTER, SlackFormatter
from models import Notification


def xo_notification(*, status="success"):
    item = Notification(
        source="xo",
        category="backup",
        status=status,
        title="Synthetic backup job",
        subject="Synthetic backup subject",
        body="Synthetic backup detail.",
        job_name="Synthetic backup job",
        job_id="JOB-SLACK-XO",
        mode="full",
        repository="SYNTHETIC-REMOTE | NFS | SYNTHETIC-REPOSITORY",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        duration="28 minutes",
        vm_total=3,
        vm_success=2,
        vm_failed=1 if status == "failure" else 0,
        vm_skipped=0,
        successful_vms=["VM-OK-1", "VM-OK-2"],
        failed_vms=["VM-FAILED"] if status == "failure" else [],
        skipped_vms=[],
        vm_details={
            "VM-OK-1": {"size": "18 GiB"},
            "VM-OK-2": {"size": "12 GiB"},
            "VM-FAILED": {
                "size": "20 GiB",
                "error": "Synthetic timeout",
            },
        },
    )
    item.metadata = {"_input_type": "smtp"}
    return item


def test_xo_uses_compact_classic_slack_attachment_matching_discord_geometry():
    payload = SlackFormatter().format(xo_notification())

    assert "blocks" not in payload
    assert "text" not in payload
    assert len(payload["attachments"]) == 1

    attachment = payload["attachments"][0]
    assert attachment["color"] == "#57F287"
    assert attachment["fallback"] == "✅ Backup Successful — Synthetic backup job"
    assert "title" not in attachment
    assert "text" not in attachment
    assert "fields" not in attachment
    assert "thumb_url" not in attachment

    blocks = attachment["blocks"]
    header = blocks[0]
    assert header["type"] == "section"
    assert header["text"]["type"] == "mrkdwn"
    assert "*✅ Backup Successful — Synthetic backup job*" in header["text"]["text"]
    assert "2 VMs protected successfully with no failures." in header["text"]["text"]
    assert header["accessory"]["type"] == "image"
    assert header["accessory"]["image_url"].endswith("/xen-orchestra.png")
    assert header["accessory"]["alt_text"] == "Xen Orchestra"

    assert len(blocks) == 5

    first_metrics = blocks[1]["fields"]
    second_metrics = blocks[2]["fields"]
    assert len(first_metrics) == 2
    assert len(second_metrics) == 2

    rendered = str(blocks)
    assert "*⏱️ Duration*\\n`28 minutes`" in rendered
    assert "*📦 Transfer Size*\\n`52.06 GiB`" in rendered
    assert "*🚀 Transfer Speed*\\n`33.73 MiB/s`" in rendered
    assert "*📁 Storage*" in rendered
    assert "SYNTHETIC-REPOSITORY · SYNTHETIC-REMOTE · NFS · Full" in rendered
    assert "VM-OK-1" in rendered
    assert "\\u200b" not in rendered

    footer = blocks[-1]
    assert footer == {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🆔 `JOB-SLACK-XO`  •  {CLASSIC_FOOTER}",
            }
        ],
    }


def test_xo_failed_classic_slack_card_keeps_failure_details():
    payload = SlackFormatter().format(xo_notification(status="failure"))
    attachment = payload["attachments"][0]

    assert "text" not in payload
    assert attachment["fallback"] == "❌ Backup Failed — Synthetic backup job"
    assert attachment["color"] == "#ED4245"

    header = attachment["blocks"][0]
    assert "*❌ Backup Failed — Synthetic backup job*" in header["text"]["text"]
    assert "Backup operation failed with 1 VM error." in header["text"]["text"]
    assert header["accessory"]["image_url"].endswith("/xen-orchestra.png")

    rendered = str(attachment["blocks"])
    assert "VM-FAILED" in rendered
    assert "Synthetic timeout" in rendered


def test_non_xo_slack_notifications_use_classic_attachment():
    item = Notification(
        source="grafana",
        category="monitoring",
        status="firing",
        title="Synthetic Grafana alert",
        body="Synthetic alert body",
        metadata={"severity": "critical"},
    )

    payload = SlackFormatter().format(item)

    assert "blocks" not in payload
    assert "text" not in payload
    assert len(payload["attachments"]) == 1
    attachment = payload["attachments"][0]
    assert attachment["title"] == "🚨 Synthetic Grafana alert"
    assert attachment["color"] == "#E74C3C"
    assert attachment["footer"] == CLASSIC_FOOTER
    assert attachment["thumb_url"].endswith("/grafana.png")