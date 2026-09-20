"""Round-48 QNAP Discord Classic cleanup contract."""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest

from outputs.discord import DiscordOutput
from parsers.qnap import Parser as QNAPParser


FIXTURES = Path(__file__).parent / "fixtures" / "qnap"


def render_fixture(name: str) -> tuple[object, dict]:
    with (FIXTURES / name).open("rb") as fixture:
        message = BytesParser(
            policy=policy.default,
        ).parse(fixture)

    notification = QNAPParser().parse(message)
    embed = DiscordOutput().source_formatters["qnap"].format(notification)[
        "embeds"
    ][0]
    return notification, embed


@pytest.mark.parametrize(
    (
        "fixture_name",
        "expected_title",
        "expected_color",
        "context_field",
    ),
    [
        (
            "failed_login.eml",
            "⚠️ Failed login attempt on SYNTHETIC-QNAP-LAB — Warning",
            0xF39C12,
            "🔐 Security",
        ),
        (
            "hbs_backup_failure.eml",
            "🚨 Backup job Synthetic Nightly Backup failed — Failed",
            0xE74C3C,
            "💾 Backup",
        ),
        (
            "notification_center_test.eml",
            "ℹ️ Test notification from SYNTHETIC-QNAP-LAB — Information",
            0x3498DB,
            None,
        ),
        (
            "smart_warning.eml",
            "⚠️ Disk 3 S.M.A.R.T. warning — Warning",
            0xF39C12,
            "💽 Storage",
        ),
        (
            "storage_warning.eml",
            "⚠️ Storage Pool 1 is in warning state — Warning",
            0xF39C12,
            "💽 Storage",
        ),
        (
            "ups_power_event.eml",
            "⚠️ UPS entered battery mode — Warning",
            0xF39C12,
            "🔋 Power",
        ),
        (
            "update_notice.eml",
            "ℹ️ A synthetic system update is available — Information",
            0x3498DB,
            "⚙️ System",
        ),
    ],
)
def test_qnap_classic_states_use_clean_titles_and_expected_context(
    fixture_name,
    expected_title,
    expected_color,
    context_field,
):
    _notification, embed = render_fixture(fixture_name)
    names = [field["name"] for field in embed["fields"]]

    assert embed["title"] == expected_title
    assert embed["color"] == expected_color
    assert names[:2] == [
        embed["title"].split(" ", 1)[0] + " Alert",
        "🗄️ QNAP NAS",
    ]
    if context_field:
        assert context_field in names
    assert names[-1] == "⏱️ Timing"

    assert "[" not in embed["title"]
    assert "]" not in embed["title"]


def test_qnap_failed_login_keeps_only_actionable_security_context():
    _notification, embed = render_fixture("failed_login.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert list(fields) == [
        "⚠️ Alert",
        "🗄️ QNAP NAS",
        "🔐 Security",
        "⏱️ Timing",
    ]
    assert fields["⚠️ Alert"] == "**Severity:** `Warning`"
    assert fields["🗄️ QNAP NAS"].splitlines() == [
        "**NAS:** `SYNTHETIC-QNAP-LAB`",
        "**Application:** `QuLog Center`",
    ]
    assert fields["🔐 Security"].splitlines() == [
        "**Account:** `synthetic-operator`",
        "**Login Result:** `Failed`",
    ]

    rendered = repr(embed)
    assert "**Status:**" not in rendered
    assert "**Category:**" not in rendered
    assert "**Event:**" not in rendered
    assert "**Connection:**" not in rendered


def test_qnap_backup_failure_removes_duplicate_job_status():
    _notification, embed = render_fixture("hbs_backup_failure.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert list(fields) == [
        "🚨 Alert",
        "🗄️ QNAP NAS",
        "💾 Backup",
        "⏱️ Timing",
    ]
    assert fields["💾 Backup"].splitlines() == [
        "**Job:** `Synthetic Nightly Backup`",
        "**Type:** `One-way sync`",
        "**Source:** `Synthetic Source`",
        "**Destination:** `Synthetic Remote Storage`",
    ]
    assert "Job Status" not in repr(embed)


def test_qnap_smart_warning_removes_duplicate_disk_health():
    _notification, embed = render_fixture("smart_warning.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["💽 Storage"].splitlines() == [
        "**Disk:** `Disk 3`",
        "**SMART Result:** `Warning`",
        "**SMART Test:** `Rapid Test`",
    ]
    assert "Disk Health" not in repr(embed)


def test_qnap_storage_pool_warning_removes_duplicate_pool_status():
    _notification, embed = render_fixture("storage_warning.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["💽 Storage"].splitlines() == [
        "**Storage Pool:** `Storage Pool 1`",
        "**RAID Group:** `RAID Group 1`",
        "**RAID Type:** `RAID 5`",
    ]
    assert "Pool Status" not in repr(embed)


def test_qnap_power_warning_keeps_power_event_and_runtime_only():
    _notification, embed = render_fixture("ups_power_event.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["🔋 Power"].splitlines() == [
        "**Power Event:** `Utility power unavailable`",
        "**Estimated Runtime:** `Synthetic value`",
    ]
    assert "UPS Status" not in repr(embed)


def test_qnap_update_notice_keeps_versions_without_raw_lifecycle_rows():
    _notification, embed = render_fixture("update_notice.eml")
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["⚙️ System"].splitlines() == [
        "**Update Type:** `System firmware`",
        "**Current Version:** `SYNTHETIC-CURRENT`",
        "**Available Version:** `SYNTHETIC-UPDATE`",
    ]
    rendered = repr(embed)
    assert "**Status:**" not in rendered
    assert "**Category:**" not in rendered
    assert "**Event:**" not in rendered
