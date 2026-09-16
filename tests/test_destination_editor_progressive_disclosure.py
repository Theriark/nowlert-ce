from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "src/webui/destination_editor_fix.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/webui/destination_editor_fix.css").read_text(encoding="utf-8")


def test_webhook_uses_progressive_disclosure():
    assert "PROGRESSIVE_DESTINATION_LAYOUTS" in SCRIPT
    assert 'title: "Advanced request options"' in SCRIPT
    assert 'document.createElement("details")' in SCRIPT
    assert "details.open = sectionNeedsAttention(settings, section)" in SCRIPT


def test_webhook_endpoint_stays_visible_and_hmac_is_conditional():
    assert 'title.textContent = "Endpoint"' in SCRIPT
    assert "routing.before(credentials)" in SCRIPT
    assert "hmac.hidden = !signHmac.checked" in SCRIPT
    assert "secretHeaders.hidden = !advanced?.open" in SCRIPT


def test_removed_destination_types_are_pruned_from_editor():
    assert 'REMOVED_DESTINATION_TYPES = new Set(["mqtt", "ntfy"])' in SCRIPT
    assert 'type === "mqtt"' not in SCRIPT
    assert 'type === "ntfy"' not in SCRIPT
    assert "normalizeAuthentication" not in SCRIPT
    assert "Discord, Microsoft Teams, Slack, and generic webhooks." in SCRIPT


def test_expanded_destination_sections_keep_intrinsic_height():
    assert ".destination-editor-main > *" in CSS
    assert "flex-shrink: 0;" in CSS
    assert ".destination-provider-settings-group details[open] > .form-grid" in CSS
