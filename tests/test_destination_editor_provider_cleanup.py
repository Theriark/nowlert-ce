from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "src/webui/destination_editor_fix.js").read_text(encoding="utf-8")
STYLE = (ROOT / "src/webui/destination_editor_fix.css").read_text(encoding="utf-8")


def test_destination_editor_uses_real_teams_and_slack_icons():
    assert 'OUTPUT_ICONS.teams = "/ui/icons/routing-teams.svg"' in SCRIPT
    assert 'OUTPUT_ICONS.slack = "/ui/icons/routing-slack.svg"' in SCRIPT


def test_destination_editor_hides_artificial_provider_chevron():
    start = STYLE.index(".destination-provider-type::after")
    block = STYLE[start:STYLE.index("}", start)]
    assert 'content: "⌄";' in block
    assert "display: none;" in block


def test_slack_metadata_is_presented_as_message_options_not_filtering():
    assert 'data-field="include_metadata"' in SCRIPT
    assert 'destination-message-options' in SCRIPT
    assert 'heading.textContent = "Message options"' in SCRIPT
    assert "it does not filter events" in SCRIPT
    assert ".destination-message-options" in STYLE
    assert "grid-column: 1 / -1" in STYLE


def test_long_destination_forms_keep_actions_outside_scrollable_body():
    assert 'form.append(actions)' in SCRIPT
    assert 'destination-editor-footer-fixed' in SCRIPT
    assert "grid-template-rows: minmax(0, 1fr) auto" in STYLE
    assert ".destination-editor-main" in STYLE
    assert "overflow-y: auto" in STYLE
    assert ".destination-editor-actions.destination-editor-footer-fixed" in STYLE
    assert "grid-row: 1 / span 2" in STYLE


def test_generic_webhook_removes_raw_http_controls_from_normal_editor():
    assert 'const WEBHOOK_ADVANCED_FIELDS = new Set([' in SCRIPT
    for key in (
        '"method"',
        '"timeout_seconds"',
        '"headers"',
        '"body_template"',
        '"sign_hmac"',
        '"allow_private_network"',
    ):
        assert key in SCRIPT
    assert 'WEBHOOK_ADVANCED_FIELDS.has(input.dataset.field)' in SCRIPT
    assert 'LONG_PROVIDER_LAYOUTS' not in SCRIPT
    assert 'normalizeLongDestinationProviderLayout' not in SCRIPT


def test_generic_webhook_uses_destination_label_message_style_and_credentials():
    assert 'channelTitle.textContent = "Destination label"' in SCRIPT
    assert 'title.textContent = "Message style"' in SCRIPT
    assert 'modern.textContent = "Modern Card"' in SCRIPT
    assert 'classic.textContent = "Classic Embed"' in SCRIPT
    assert 'urlTitle.textContent = "Webhook URL"' in SCRIPT
    assert 'title.textContent = "Credentials"' in SCRIPT
    assert 'routing.after(credentials)' in SCRIPT
