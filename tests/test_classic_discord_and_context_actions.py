"""Regression coverage for Discord Classic verification and contextual actions."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from models import Notification
from outputs.discord import DiscordOutput
from outputs.platform import WebhookPlatformAdapter
from storage.destinations import Destination


ROOT = Path(__file__).resolve().parents[1]


class AcceptedDiscordResponse:
    status_code = 200
    text = ""

    def json(self):
        return {"attachments": [], "embeds": []}


class AcceptedDiscordClient:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return AcceptedDiscordResponse()


def public_resolver(*_args, **_kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("8.8.8.8", 443),
        )
    ]


def classic_webhook_destination() -> Destination:
    return Destination(
        id="d" * 32,
        owner_user_id="u" * 32,
        name="Classic Discord webhook",
        output_type="webhook",
        settings={"message_style": "classic"},
        shared=True,
        enabled=True,
        secret_configured=True,
        created_at=1,
        updated_at=1,
    )


def xo_notification() -> Notification:
    return Notification(
        source="xo",
        category="virtualization",
        status="information",
        title="Backup successful",
        body="Classic Generic Webhook regression test",
        metadata={"severity": "information", "host": "DEVELOPMENT-HOST"},
    )


def test_classic_discord_wait_request_returns_message_without_components_v2():
    webhook = "https://discord.com/api/webhooks/123/token"
    result = DiscordOutput._delivery_webhook(
        webhook,
        {"embeds": [{"title": "Classic"}]},
        wait=True,
    )

    query = parse_qs(urlsplit(result).query)
    assert query == {"wait": ["true"]}


def test_generic_webhook_discord_classic_counts_accepted_delivery_as_success():
    client = AcceptedDiscordClient()
    adapter = WebhookPlatformAdapter(
        http_client=client,
        resolver=public_resolver,
    )
    adapter.discord.output.ICON_DIR = ROOT / "assets" / "icons"
    secret = json.dumps(
        {"url": "https://discord.com/api/webhooks/123/token"}
    ).encode()

    result = adapter.deliver(
        classic_webhook_destination(),
        secret,
        xo_notification(),
    )

    assert result.success is True
    assert result.response_status == 200
    assert len(client.calls) == 1
    url, kwargs = client.calls[0]
    query = parse_qs(urlsplit(url).query)
    assert query["wait"] == ["true"]
    assert "with_components" not in query
    assert "files[0]" in kwargs["files"]


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


def test_audit_run_checks_is_in_toolbar_and_health_box_is_retired():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "moveAuditHealthChecksIntoToolbar" in script
    assert 'auditView.querySelector(".section-toolbar")' in script
    assert "toolbar.append(runChecks)" in script
    assert "healthPanel.hidden = true" in script


def test_private_destination_matches_normal_destination_identity_layout():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert 'className: "resource-heading"' in script
    assert 'className: "resource-identity"' in script
    assert 'className: "resource-icon"' in script
    assert 'badge("Private", "warning")' in script
    assert 'badge("Metadata only", "")' in script


def test_generic_webhook_uses_dedicated_network_icon():
    script = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(
        encoding="utf-8"
    )

    assert "const WEBHOOK_ICON" in script
    assert "OUTPUT_ICONS.webhook = WEBHOOK_ICON" in script
    assert '<circle cx="5" cy="6" r="2.5"/>' in script


def test_processing_settings_use_two_named_desktop_columns():
    script = (ROOT / "src" / "webui" / "policy_simplification.js").read_text(
        encoding="utf-8"
    )
    styles = (ROOT / "src" / "webui" / "policy_simplification.css").read_text(
        encoding="utf-8"
    )

    assert '"Aliases & normalization"' in script
    assert '"Event processing"' in script
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in styles
    assert ".settings-subsection + .settings-subsection" in styles
    assert "border-left: 1px solid" in styles
