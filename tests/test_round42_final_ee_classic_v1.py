"""Round-42 regression for the final EE Classic Embed v1 templates."""

from models import Notification
from outputs.discord import DiscordOutput


FOOTER = {"text": "🦉 Nowlert CE • Classic Embed"}


def xo_success() -> Notification:
    item = Notification(
        source="xo",
        category="backup",
        status="success",
        title="Backup report for [NON-CRITICAL - 01] Administration",
        subject="Backup report for [NON-CRITICAL - 01] Administration",
        sender="Xen Orchestra <xo@xen-orchestra-development.invalid>",
        job_name="[NON-CRITICAL - 01] Administration",
        job_id="91f9f6d3-9439-5376-b6b6-e379a4227b69",
        run_id="178943504801",
        mode="full",
        repository="UNAS-01 | NFS | Non-Critical Backups",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        start_time="2026-09-15 00:49:28 UTC",
        end_time="2026-09-15 01:17:28 UTC",
        duration="28 minutes",
        vm_total=3,
        vm_success=3,
        successful_vms=[
            "VM-01 | Admin",
            "VM-06 | XO-02",
            "VM-02 | XO-01",
        ],
        vm_details={
            "VM-01 | Admin": {"size": "45.01 GiB", "speed": "33.73 MiB/s"},
            "VM-06 | XO-02": {"size": "3.42 GiB", "speed": "28.11 MiB/s"},
            "VM-02 | XO-01": {"size": "3.62 GiB", "speed": "22.27 MiB/s"},
        },
    )
    item.metadata = {
        "provider": "Xen Orchestra",
        "to": "mock-ce-dev@nowlert.theriark.invalid",
    }
    return item


def test_xo_success_matches_final_ee_classic_v1_geometry_without_ai():
    embed = DiscordOutput().source_formatters["xo"].format(xo_success())["embeds"][0]

    assert embed["title"] == "✅ Backup Successful — [NON-CRITICAL - 01] Administration"
    assert embed["description"] == "3 VMs protected successfully with no failures."
    assert embed["color"] == 0x57F287
    assert embed["footer"] == FOOTER

    assert [field["name"] for field in embed["fields"]] == [
        "⏱️ Duration",
        "📦 Transfer Size",
        "🚀 Transfer Speed",
        "📁 Storage",
        "⏱️ Timing",
        "✅ Successful VMs",
        "📧 Email",
        "✉️ Subject",
        "🆔 Job ID",
        "🔢 Job Details",
    ]

    assert embed["fields"][3]["value"] == (
        "**Repository:** `UNAS-01 | NFS | Non-Critical Backups`\n"
        "**Mode:** `full`"
    )
    assert embed["fields"][5]["value"].splitlines() == [
        "**VM-01 | Admin:** `45.01 GiB · 33.73 MiB/s`",
        "**VM-06 | XO-02:** `3.42 GiB · 28.11 MiB/s`",
        "**VM-02 | XO-01:** `3.62 GiB · 22.27 MiB/s`",
    ]
    assert embed["fields"][6]["value"].splitlines() == [
        "**From:** `Xen Orchestra <xo@xen-orchestra-development.invalid>`",
        "**To:** `mock-ce-dev@nowlert.theriark.invalid`",
    ]
    assert embed["fields"][7] == {
        "name": "✉️ Subject",
        "value": "`Backup report for [NON-CRITICAL - 01] Administration`",
        "inline": False,
    }
    assert embed["fields"][8] == {
        "name": "🆔 Job ID",
        "value": "`91f9f6d3-9439-5376-b6b6-e379a4227b69`",
        "inline": False,
    }
    assert embed["fields"][9]["value"].splitlines() == [
        "**Run ID:** `178943504801`",
        "**Provider:** `Xen Orchestra`",
        "**Source:** `xo`",
    ]

    rendered = repr(embed)
    assert "Insight" not in rendered
    assert "Context" not in rendered
    assert "Recommended Action" not in rendered
    assert "Nowlert AI" not in rendered
