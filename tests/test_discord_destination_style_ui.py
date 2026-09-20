"""Discord destination message-style WebUI regression contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_discord_destination_uses_user_facing_message_style_selector():
    script = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    assert 'text: "Message style"' in script
    assert 'value: "modern", text: "Modern Card"' in script
    assert 'value: "classic", text: "Classic Card"' in script
    assert 'checkbox.checked = select.value === "modern";' in script
    assert 'checkbox.hidden = true;' in script
    assert 'Choose how Nowlert notifications are presented in Discord.' in script
    assert 'Modern Card uses responsive structured sections; Classic Card uses the traditional Discord embed layout.' in script
