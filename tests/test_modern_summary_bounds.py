"""Shared Modern summary text stays inside its three fixed cells."""

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from formatters.discord_modern_image import (
    GenericFallbackDiscordModernImageRenderer,
    GrafanaDiscordModernImageRenderer,
    PortainerDiscordModernImageRenderer,
    ProxmoxDiscordModernImageRenderer,
    QNAPDiscordModernImageRenderer,
    ZabbixDiscordModernImageRenderer,
)
from models import Notification


@pytest.mark.parametrize("source", ["email", "semaphore"])
@pytest.mark.parametrize("category", ["Backup", "CE QA OpenAI synthetic", "Déploiement 日本語 " * 8])
def test_summary_values_stay_inside_cells_and_fixed_strip(monkeypatch, tmp_path, source, category):
    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)
    item = Notification(source=source, title="CE QA OpenAI incident update", status="information",
                        category=category, body="Synthetic incident: resolved", start_time="2026-10-15 12:49:36 UTC",
                        metadata={"classification": "information", "severity": "information",
                                  "group": category, "provider": "imap"})
    painted = []
    original = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, **kwargs):
        font = kwargs.get("font")
        painted.append((str(text), draw.textbbox(xy, text, font=font, anchor=kwargs.get("anchor")), xy))
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    png = renderer.render(item, {"embeds": [{"title": item.title, "description": item.body}]})
    metrics = [("status", "Severity", "information", renderer.TEXT),
               ("sync", "Category", renderer._summary_category(item), renderer.TEXT),
               ("clock", "Event time", "12:49:36", renderer.TEXT)]
    cells = renderer._summary_cells_for_metrics(renderer.CARD_SIDE_PADDING,
                                               renderer.WIDTH - renderer.CARD_SIDE_PADDING, metrics)
    summary = []
    for label, (left, right) in zip(("Severity:", "Category:", "Event time:"), cells):
        index = next(i for i, (text, _, _) in enumerate(painted) if text == label)
        value, bounds, _ = painted[index + 1]
        middle_y = painted[index][2][1]
        assert bounds[0] >= left and bounds[2] <= right, (label, value, bounds, right)
        assert bounds[1] >= middle_y - renderer.SUMMARY_HEIGHT // 2
        assert bounds[3] <= middle_y + renderer.SUMMARY_HEIGHT // 2
        summary.append(value)
    if category == "Backup":
        assert summary[1] == "Backup"
    else:
        assert summary[1].endswith("…")
    with Image.open(BytesIO(png)) as image:
        assert image.height == renderer.BASE_HEIGHT


@pytest.mark.parametrize("source", ["email", "semaphore"])
def test_missing_event_time_is_a_dash_not_an_empty_cell(monkeypatch, tmp_path, source):
    renderer = GenericFallbackDiscordModernImageRenderer(tmp_path)
    item = Notification(source=source, title="Task failed", status="error", category="Automation",
                        body="Task 42 failed", metadata={"state": "failure"})
    painted = []
    original = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, **kwargs):
        painted.append(str(text))
        return original(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    renderer.render(item, {"embeds": [{"title": item.title, "description": item.body}]})
    assert painted[painted.index("Event time:") + 1] == "\u2014"


@pytest.mark.parametrize(
    "renderer_class",
    [
        ZabbixDiscordModernImageRenderer,
        GrafanaDiscordModernImageRenderer,
        PortainerDiscordModernImageRenderer,
        ProxmoxDiscordModernImageRenderer,
        QNAPDiscordModernImageRenderer,
        GenericFallbackDiscordModernImageRenderer,
    ],
)
@pytest.mark.parametrize(
    "values",
    [
        ("warning", "Security", "15:50:00 UTC"),
        ("Critical", "Alerting", "10:15:00"),
        ("information", "Administration", "\u2014"),
        ("information", "Automation", "12:00:00 UTC"),
    ],
)
def test_zabbix_family_summary_groups_fit_their_measured_text(tmp_path, renderer_class, values):
    renderer = renderer_class(tmp_path)
    metrics = [
        ("status", "Severity", values[0], renderer.TEXT),
        ("sync", "Category", values[1], renderer.TEXT),
        ("clock", "Event time", values[2], renderer.TEXT),
    ]
    left, right = renderer.CARD_SIDE_PADDING, renderer.WIDTH - renderer.CARD_SIDE_PADDING
    cells = renderer._summary_cells_for_metrics(left, right, metrics)
    label_font, value_font = renderer._summary_fonts_for_metrics(metrics)
    draw = ImageDraw.Draw(Image.new("RGB", (renderer.WIDTH, 1)))
    for (_icon, label, value, _color), (cell_left, cell_right) in zip(metrics, cells):
        needed = (
            renderer.SUMMARY_LABEL_OFFSET
            + draw.textlength(f"{label}:", font=label_font)
            + renderer.SUMMARY_VALUE_GAP
            + draw.textlength(value, font=value_font)
        )
        assert cell_right - cell_left >= needed, (renderer_class.__name__, label, value)
    assert cells[0][1] < cells[1][0] < cells[1][1] < cells[2][0]
    assert cells[2][1] <= right
