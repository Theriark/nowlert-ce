"""Round-42 regression for the final EE Classic Card v1 templates."""

from models import Notification
from outputs.discord import DiscordOutput


FOOTER = {"text": "🦉 Nowlert CE • Classic Card"}


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


def test_xo_success_matches_compact_ce_classic_v1_geometry():
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
        "✅ Successful VMs · 3",
        "🆔 Job ID",
    ]

    assert embed["fields"][3]["value"] == (
        "`Non-Critical Backups · UNAS-01 · NFS · Full`"
    )
    assert embed["fields"][4]["value"].splitlines() == [
        "**VM-01 | Admin** · `45.01 GiB`",
        "**VM-06 | XO-02** · `3.42 GiB`",
        "**VM-02 | XO-01** · `3.62 GiB`",
    ]
    assert embed["fields"][5] == {
        "name": "🆔 Job ID",
        "value": "`91f9f6d3-9439-5376-b6b6-e379a4227b69`",
        "inline": False,
    }

    rendered = repr(embed)
    assert "33.73 MiB/s" in rendered
    assert "28.11 MiB/s" not in rendered
    assert "22.27 MiB/s" not in rendered
    assert "178943504801" not in rendered
    assert "Xen Orchestra <xo@xen-orchestra-development.invalid>" not in rendered
    assert "mock-ce-dev@nowlert.theriark.invalid" not in rendered
    assert "Backup report for [NON-CRITICAL - 01] Administration" not in [
        field["value"] for field in embed["fields"]
    ]
    assert "Insight" not in rendered
    assert "Context" not in rendered
    assert "Recommended Action" not in rendered
    assert "Nowlert AI" not in rendered

