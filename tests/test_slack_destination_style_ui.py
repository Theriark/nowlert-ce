"""Slack destination Classic/Modern selector regression contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_slack_destination_exposes_classic_and_modern_message_style():
    app = (ROOT / "src" / "webui" / "app.js").read_text(
        encoding="utf-8"
    )
    editor = (
        ROOT / "src" / "webui" / "destination_editor_fix.js"
    ).read_text(encoding="utf-8")

    slack_start = app.index("    slack: {")
    slack_end = app.index("    webhook: {", slack_start)
    slack = app[slack_start:slack_end]

    assert 'key: "message_style"' in slack
    assert 'label: "Message style"' in slack
    assert '["classic", "Classic Card"]' in slack
    assert '["modern", "Modern Card"]' in slack
    assert 'default: "classic"' in slack
    assert 'key: "include_metadata"' in slack

    assert 'style.value === "modern"' in editor
    assert "label.hidden = modern;" in editor
    assert 'data-field="message_style"' in editor
    assert "Slack Classic Card detail" in editor
