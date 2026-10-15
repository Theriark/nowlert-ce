"""Native application cards keep readable status and unfolded short context."""

import json
from pathlib import Path

import pytest
from PIL import ImageDraw

from formatters.slack import SlackFormatter
from outputs.discord import DiscordOutput
from parsers.application_alerts import Parser


def semaphore_item(native="❌ ERROR"):
    payload = json.loads(
        (Path(__file__).parent / "fixtures/application_alerts/semaphore.json").read_text()
    )
    payload["attachments"][0]["text"] = f"execution #42, status: {native}!"
    return Parser("semaphore").parse(payload)[0]


@pytest.mark.parametrize("native,readable", [
    ("❌ ERROR", "✗ ERROR"),
    ("✅ SUCCESS", "✓ SUCCESS"),
    ("⚠️ WAITING_CONFIRMATION", "⚠ WAITING_CONFIRMATION"),
    ("⏹️ STOPPED", "■ STOPPED"),
])
@pytest.mark.parametrize("long_message", [False, True])
def test_modern_native_status_is_readable_without_emoji_font(monkeypatch, native, readable, long_message):
    item = semaphore_item(native)
    item.body += " — déploiement 日本語" + (" context" * 300 if long_message else "")
    classic = DiscordOutput().source_formatters["semaphore"].format(item)
    assert native in json.dumps(classic, ensure_ascii=False)
    drawn = []
    original = ImageDraw.ImageDraw.text

    def capture(self, xy, text, *args, **kwargs):
        drawn.append(str(text))
        if readable[0] in str(text):
            font = kwargs["font"]
            assert bytes(font.getmask(readable[0])) != bytes(font.getmask("\uffff"))
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    assert DiscordOutput().render_modern_image(item)
    rendered = " ".join(drawn)
    assert readable in rendered
    assert "déploiement 日本語" in rendered
    assert not any(symbol in rendered for symbol in "❌✅⏹\ufe0f")


@pytest.mark.parametrize("actor", ["operator", ""])
def test_slack_short_semaphore_context_stays_below_section_fold(actor):
    item = semaphore_item()
    item.metadata["actor"] = actor
    blocks = SlackFormatter().format(item)["attachments"][0]["blocks"]
    body_sections = [
        block["text"]["text"] for block in blocks
        if block.get("type") == "section" and "accessory" not in block and "text" in block
    ]
    assert all(len(section.splitlines()) <= 5 for section in body_sections)
    if actor:
        assert any("Actor: operator" in section.replace("*", "").replace("`", "") for section in body_sections)


def test_slack_long_semaphore_context_remains_bounded():
    item = semaphore_item()
    item.metadata["workflow"] = "Automation\n" * 80
    blocks = SlackFormatter().format(item)["attachments"][0]["blocks"]
    for block in blocks:
        if "text" in block and "accessory" not in block:
            assert len(block["text"]["text"]) <= 3000
            assert len(block["text"]["text"].splitlines()) <= 5
