from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "src/webui/destination_editor_fix.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/webui/destination_editor_fix.css").read_text(encoding="utf-8") if (ROOT / "src/webui/destination_editor_fix.css").exists() else ""


def test_webhook_uses_backend_owned_message_styles():
    assert 'const WEBHOOK_ADVANCED_FIELDS = new Set([' in SCRIPT
    assert 'select.dataset.field = "message_style"' in SCRIPT
    assert 'modern.textContent = "Modern Card"' in SCRIPT
    assert 'classic.textContent = "Classic Card"' in SCRIPT
    assert 'settings.replaceChildren(channel, styleField)' in SCRIPT
    assert 'Advanced request options' not in SCRIPT
    assert 'PROGRESSIVE_DESTINATION_LAYOUTS' not in SCRIPT


def test_webhook_credentials_stay_last_and_use_webhook_url_label():
    assert 'title.textContent = "Credentials"' in SCRIPT
    assert 'routing.after(credentials)' in SCRIPT
    assert 'urlTitle.textContent = "Webhook URL"' in SCRIPT
    assert 'title.textContent = "Endpoint"' not in SCRIPT
    assert 'WEBHOOK_ADVANCED_SECRETS = new Set(["hmac_secret", "headers"])' in SCRIPT


def test_webhook_simplification_runs_before_the_dialog_is_shown():
    assert 'renderDestinationFieldsWithWebhookTemplate' in SCRIPT
    assert 'normalizeWebhookEditor();' in SCRIPT
    assert 'settings.dataset.destinationWebhookSimplified === "true"' in SCRIPT


def test_removed_destination_types_are_pruned_from_editor():
    assert 'REMOVED_DESTINATION_TYPES = new Set(["mqtt", "ntfy"])' in SCRIPT
    assert 'type === "mqtt"' not in SCRIPT
    assert 'type === "ntfy"' not in SCRIPT
    assert "Discord, Microsoft Teams, Slack, Email, and generic webhooks." in SCRIPT


def test_destination_editor_keeps_fixed_footer_layout():
    if not CSS:
        return
    assert ".destination-editor-main > *" in CSS
    assert "flex-shrink: 0;" in CSS
