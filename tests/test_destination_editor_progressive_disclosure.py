from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "src/webui/destination_editor_fix.js").read_text(encoding="utf-8")


def test_complex_destination_settings_use_progressive_disclosure():
    assert "PROGRESSIVE_DESTINATION_LAYOUTS" in SCRIPT
    assert 'title: "Advanced request options"' in SCRIPT
    assert 'title: "Advanced delivery options"' in SCRIPT
    assert 'title: "Message options"' in SCRIPT
    assert 'document.createElement("details")' in SCRIPT
    assert "details.open = sectionNeedsAttention(settings, section)" in SCRIPT


def test_webhook_endpoint_stays_visible_and_hmac_is_conditional():
    assert 'title.textContent = "Endpoint"' in SCRIPT
    assert "routing.before(credentials)" in SCRIPT
    assert "hmac.hidden = !signHmac.checked" in SCRIPT
    assert "secretHeaders.hidden = !advanced?.open" in SCRIPT


def test_mqtt_and_ntfy_authentication_is_collapsible():
    assert 'sectionHeading("Authentication")' in SCRIPT
    assert "details.open = Boolean(currentDestination()?.secret_configured)" in SCRIPT
    assert 'type === "mqtt" || type === "ntfy"' in SCRIPT
    assert "public ntfy servers" in SCRIPT


def test_existing_non_default_options_open_their_advanced_section():
    assert "sectionNeedsAttention" in SCRIPT
    assert 'timeout_seconds: "15"' in SCRIPT
    assert 'qos: "1"' in SCRIPT
    assert 'keepalive_seconds: "60"' in SCRIPT
    assert 'title: "${title}"' in SCRIPT
    assert "include_action: true" in SCRIPT
