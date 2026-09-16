"""Regression coverage for Discord Classic verification and contextual actions."""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from outputs.discord import DiscordOutput


ROOT = Path(__file__).resolve().parents[1]


def test_classic_discord_wait_request_returns_message_without_components_v2():
    webhook = "https://discord.com/api/webhooks/123/token"
    result = DiscordOutput._delivery_webhook(
        webhook,
        {"embeds": [{"title": "Classic"}]},
        wait=True,
    )

    query = parse_qs(urlsplit(result).query)
    assert query == {"wait": ["true"]}


def test_platform_actions_are_relocated_to_contextual_pages():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )
    enhancements = (ROOT / "src" / "webui" / "enhancements.js").read_text(
        encoding="utf-8"
    )

    assert "movePlatformActionsIntoContext" in script
    assert 'document.querySelector("#view-updates .section-toolbar")' in script
    assert 'document.querySelector("#view-account .section-toolbar")' in script
    assert 'updateButton.className = "button secondary"' in script
    assert 'restartButton.className = "button danger"' in script
    assert 'platformMenu.style.display = "none"' in script
    assert "updateToolbar.append(updateButton)" in script
    assert "accountToolbar.append(restartButton)" in script
    assert 'if (restart) restart.hidden = !isAdmin();' in enhancements
