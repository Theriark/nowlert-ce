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
    assert payload["text"] == "✅ Backup Successful — Synthetic backup job"
    assert len(payload["attachments"]) == 1

    attachment = payload["attachments"][0]
    assert attachment["color"] == "#57F287"
    assert attachment["title"] == payload["text"]
    assert (
        attachment["text"]
        == "2 VMs protected successfully with no failures."
    )
    assert attachment["footer"] == CLASSIC_FOOTER
    assert attachment["mrkdwn_in"] == ["text", "fields"]

    fields = {field["title"]: field for field in attachment["fields"]}
    assert fields["⏱️ Duration"] == {
        "title": "⏱️ Duration",
        "value": "`28 minutes`",
        "short": True,
    }
    assert fields["📦 Transfer Size"]["value"] == "`52.06 GiB`"
    assert fields["🚀 Transfer Speed"]["value"] == "`33.73 MiB/s`"
    assert fields["📁 Storage"]["value"] == (
        "`SYNTHETIC-REPOSITORY · SYNTHETIC-REMOTE · NFS · Full`"
    )
    assert "VM-OK-1" in fields["✅ Successful VMs · 2"]["value"]
    assert fields["🆔 Job ID"]["value"] == "`JOB-SLACK-XO`"


def test_xo_failed_classic_slack_card_keeps_failure_details():
    payload = SlackFormatter().format(xo_notification(status="failure"))
    attachment = payload["attachments"][0]

    assert payload["text"] == "❌ Backup Failed — Synthetic backup job"
    assert attachment["color"] == "#ED4245"
    assert attachment["text"] == "Backup operation failed with 1 VM error."

    fields = {field["title"]: field for field in attachment["fields"]}
    failed = fields["❌ Failed VMs · 1"]["value"]
    assert "VM-FAILED" in failed
    assert "Synthetic timeout" in failed


def test_non_xo_slack_notifications_keep_existing_block_kit_fallback():
    item = Notification(
        source="grafana",
        category="monitoring",
        status="firing",
        title="Synthetic Grafana alert",
        body="Synthetic alert body",
        metadata={"severity": "critical"},
    )

    payload = SlackFormatter().format(item)

    assert "blocks" in payload
    assert "attachments" not in payload
    assert payload["text"] == "Synthetic Grafana alert"
