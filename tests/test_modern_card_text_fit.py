"""Teams/Discord Modern image cards keep their text inside its outline."""

from PIL import Image, ImageDraw

from formatters.discord_classic_v1 import is_xo_backup_report, render_classic_embed_v1
from formatters.discord_modern_image import ProxmoxDiscordModernImageRenderer
from models import Notification
from parsers.event_api import Parser


def preview_event(source: str, severity: str = "warning") -> Notification:
    return Parser().parse({
        "schema": "nowlert.event.v1", "source": source, "title": "Synthetic Nowlert preview",
        "message": "Synthetic preview message.", "severity": severity, "status": "active",
        "category": "virtualization", "metadata": {"host": "webui-safe-preview"},
    })


def test_status_badge_grows_to_fit_its_label_and_keeps_the_frozen_width_otherwise():
    renderer = ProxmoxDiscordModernImageRenderer()
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    right = renderer.WIDTH - renderer.CARD_SIDE_PADDING

    short = renderer._standard_badge_box(draw, right, 80, 150, "warning", "Warning")
    assert short[2] - short[0] == renderer.STATUS_BADGE_WIDTH

    label = "Virtualization Warning"
    long = renderer._standard_badge_box(draw, right, 80, 150, "warning", label)
    text_end = long[0] + 112 + draw.textlength(label, font=renderer.font_bold)
    assert text_end <= long[2] - 30
    assert long[2] == right


def test_only_xo_backup_reports_use_the_xo_backup_card():
    assert is_xo_backup_report(Notification(source="xo", category="backup"))
    assert is_xo_backup_report(Notification(source="xo", category="", job_name="Nightly"))
    assert not is_xo_backup_report(preview_event("xo"))


def test_xo_warning_preview_is_not_described_as_a_backup():
    embed = render_classic_embed_v1(preview_event("xo"), {"embeds": [{}]})
    text = str(embed)
    assert "Backup Successful" not in text
    assert "Backup Skipped" not in text
    assert "VMs protected" not in text
