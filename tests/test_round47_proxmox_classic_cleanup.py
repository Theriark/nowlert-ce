"""Round-47 Proxmox Discord Classic cleanup contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from models import Notification
from outputs.discord import DiscordOutput
from parsers.proxmox import Parser as ProxmoxParser


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "proxmox"
    / "event_warning.json"
)


def webhook_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def render(item: Notification) -> dict:
    return DiscordOutput().source_formatters["proxmox"].format(item)[
        "embeds"
    ][0]


def test_proxmox_backup_failure_uses_compact_operator_geometry():
    item = Notification(
        source="proxmox",
        category="backup",
        status="failure",
        title="Synthetic backup failure",
        subject="Synthetic backup failure",
        body="Synthetic backup job completed with errors; one guest failed.",
        start_time="2026-07-15T01:30:00Z",
        failed_vms=["101 | synthetic-db"],
        successful_vms=["100 | home-assistant"],
        errors=["synthetic timeout"],
    )
    item.metadata = {
        "severity": "critical",
        "state": "firing",
        "node": "synthetic-pve-01",
        "guest": "synthetic-db",
        "vmid": "101",
        "storage": "synthetic-backup-store",
        "job_id": "vzdump-synthetic-01",
    }

    embed = render(item)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == "🚨 Synthetic backup failure — Failed"
    assert embed["description"] == (
        "Synthetic backup job completed with errors; one guest failed."
    )
    assert embed["color"] == 0xE74C3C
    assert list(fields) == [
        "🚨 Alert",
        "🟧 Proxmox VE",
        "💾 Backup",
        "⏱️ Timing",
    ]
    assert fields["🚨 Alert"] == "**Severity:** `critical`"
    assert fields["🟧 Proxmox VE"].splitlines() == [
        "**Node:** `synthetic-pve-01`",
        "**Guest:** `synthetic-db`",
        "**VMID:** `101`",
    ]
    assert fields["💾 Backup"].splitlines() == [
        "**Storage:** `synthetic-backup-store`",
        "**Job:** `vzdump-synthetic-01`",
    ]
    assert fields["⏱️ Timing"] == (
        "**Started:** `2026-07-15T01:30:00Z`"
    )

    rendered = repr(embed)
    assert "**Status:**" not in rendered
    assert "**State:**" not in rendered
    assert "**Category:**" not in rendered
    assert "❌ Failed Guests" not in rendered
    assert "🧯 Error Details" not in rendered
    assert "✅ Successful Guests" not in rendered
    assert "**Duration:**" not in rendered


def test_proxmox_storage_warning_keeps_only_approved_storage_context():
    item = ProxmoxParser().parse_webhook(webhook_fixture())
    embed = render(item)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == "⚠️ Synthetic storage warning — Warning"
    assert embed["color"] == 0xF39C12
    assert list(fields) == [
        "⚠️ Alert",
        "🟧 Proxmox VE",
        "💾 Storage",
        "⏱️ Timing",
    ]
    assert fields["⚠️ Alert"] == "**Severity:** `warning`"
    assert fields["🟧 Proxmox VE"] == (
        "**Node:** `synthetic-pve-01`"
    )
    assert fields["💾 Storage"] == (
        "**Storage:** `synthetic-backup-store`"
    )
    assert fields["⏱️ Timing"] == (
        "**Started:** `2026-07-15T01:15:00Z`"
    )

    rendered = repr(embed)
    assert "85" not in rendered
    assert "**Usage:**" not in rendered
    assert "**Status:**" not in rendered
    assert "**State:**" not in rendered
    assert "**Category:**" not in rendered


def test_proxmox_storage_resolved_keeps_started_and_finished_only():
    payload = copy.deepcopy(webhook_fixture())
    payload["title"] = "Synthetic storage recovered"
    payload["message"] = (
        "Synthetic backup storage usage returned to a healthy level."
    )
    payload["severity"] = "success"
    payload["status"] = "resolved"
    payload["timestamp"] = "2026-07-15T01:45:00Z"

    item = ProxmoxParser().parse_webhook(payload)
    embed = render(item)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert embed["title"] == "✅ Synthetic storage recovered — Resolved"
    assert embed["color"] == 0x2ECC71
    assert list(fields) == [
        "✅ Alert",
        "🟧 Proxmox VE",
        "💾 Storage",
        "⏱️ Timing",
    ]
    assert fields["✅ Alert"] == "**Severity:** `success`"
    assert fields["⏱️ Timing"].splitlines() == [
        "**Started:** `2026-07-15T01:45:00Z`",
        "**Finished:** `2026-07-15T01:45:00Z`",
    ]

    rendered = repr(embed)
    assert "**Status:**" not in rendered
    assert "**State:**" not in rendered
    assert "**Category:**" not in rendered
    assert "**Duration:**" not in rendered
