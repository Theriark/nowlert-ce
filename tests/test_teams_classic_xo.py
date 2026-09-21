"""Microsoft Teams Classic Xen Orchestra pilot regressions."""

from __future__ import annotations

import json

import pytest

from formatters.teams_classic_v1 import (
    CLASSIC_FOOTER,
    TeamsClassicXenOrchestraFormatter,
)
from models import Notification
from outputs.teams import TeamsOutput


def xo_notification(status="success") -> Notification:
    return Notification(
        source="xo",
        category="backup",
        status=status,
        title="Daily Production Backup",
        body="Backup completed.",
        job_name="Daily Production Backup",
        job_id="JOB-123",
        mode="full",
        repository="NFS | Backup Repository | Repository-01",
        duration="5 min",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        vm_total=3,
        vm_success=2,
        vm_failed=(
            1
            if status in {"failure", "failed", "error", "critical"}
            else 0
        ),
        vm_skipped=1 if status in {"skipped", "warning"} else 0,
        successful_vms=["VM-01", "VM-02"],
        failed_vms=(
            ["VM-03"]
            if status in {"failure", "failed", "error", "critical"}
            else []
        ),
        skipped_vms=(
            ["VM-04"]
            if status in {"skipped", "warning"}
            else []
        ),
        vm_details={
            "VM-01": {"size": "18 GiB"},
            "VM-02": {"size": "12 GiB"},
            "VM-03": {
                "size": "22 GiB",
                "error": "Synthetic timeout",
            },
            "VM-04": {
                "size": "8 GiB",
                "error": "Excluded by policy",
            },
        },
    )


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


@pytest.mark.parametrize(
    ("status", "expected_title", "expected_description"),
    (
        (
            "success",
            "✅ Backup Successful — Daily Production Backup",
            "2 VMs protected successfully with no failures.",
        ),
        (
            "failure",
            "❌ Backup Failed — Daily Production Backup",
            "Backup operation failed with 1 VM error.",
        ),
        (
            "skipped",
            "⏭️ Backup Skipped — Daily Production Backup",
            (
                "2 VMs protected successfully and 1 VM was skipped "
                "by backup policy."
            ),
        ),
    ),
)
def test_xo_classic_lifecycle_title_and_description(
    status,
    expected_title,
    expected_description,
):
    payload = TeamsClassicXenOrchestraFormatter().format(
        xo_notification(status)
    )
    text = flattened_text(payload)

    assert expected_title in text
    assert expected_description in text
    assert CLASSIC_FOOTER in text


def test_xo_classic_preserves_approved_field_order():
    payload = TeamsClassicXenOrchestraFormatter().format(
        xo_notification("failure")
    )
    text = flattened_text(payload)

    labels = [
        "⏱️ Duration",
        "📦 Transfer Size",
        "🚀 Transfer Speed",
        "📁 Storage",
        "✅ Successful VMs · 2",
        "❌ Failed VMs · 1",
        "🆔 Job ID",
    ]
    positions = [text.index(label) for label in labels]

    assert positions == sorted(positions)
    assert (
        "Repository-01 · NFS · Backup Repository · Full"
        in text
    )
    assert "VM-01" in text and "18 GiB" in text
    assert "VM-03" in text and "Synthetic timeout" in text
    assert "JOB-123" in text


def test_xo_classic_keeps_approved_plain_text_geometry():
    payload = TeamsClassicXenOrchestraFormatter().format(
        xo_notification("success")
    )
    text = flattened_text(payload)

    assert "`" not in text
    assert "5 min" in text
    assert "52.06 GiB" in text
    assert "33.73 MiB/s" in text
    assert "Repository-01 · NFS · Backup Repository · Full" in text
    assert "**VM-01** · 18 GiB" in text
    assert "JOB-123" in text


def test_xo_classic_omits_empty_optional_sections():
    item = xo_notification("success")
    item.transfer_speed = ""
    item.failed_vms = []
    item.skipped_vms = []
    item.job_id = ""

    payload = TeamsClassicXenOrchestraFormatter().format(item)
    text = flattened_text(payload)

    assert "🚀 Transfer Speed" not in text
    assert "❌ Failed VMs" not in text
    assert "⏭️ Skipped VMs" not in text
    assert "🆔 Job ID" not in text


def test_xo_classic_bounds_long_vm_lists_and_payload_size():
    item = xo_notification("success")
    item.successful_vms = [
        f"VM-{index:02d}"
        for index in range(20)
    ]
    item.vm_success = 20
    item.vm_total = 20
    item.vm_details = {
        name: {"size": "10 GiB"}
        for name in item.successful_vms
    }

    formatter = TeamsClassicXenOrchestraFormatter()
    payload = formatter._sanitize_payload(
        formatter.format(item)
    )
    text = flattened_text(payload)

    assert "… and 10 more" in text
    assert (
        TeamsOutput.payload_size(payload)
        <= TeamsOutput.MAX_PAYLOAD_BYTES
    )


def test_xo_classic_sanitizes_secret_like_text():
    item = xo_notification("failure")
    item.vm_details["VM-03"]["error"] = (
        "token=private-token timeout"
    )

    formatter = TeamsClassicXenOrchestraFormatter()
    payload = formatter._sanitize_payload(
        formatter.format(item)
    )
    encoded = json.dumps(payload)

    assert "private-token" not in encoded
    assert "<redacted>" in encoded
