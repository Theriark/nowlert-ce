from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_destination_provider_selector_keeps_all_supported_types():
    markup = (ROOT / "src/webui/index.html").read_text(encoding="utf-8")
    for output_type in ("discord", "teams", "slack", "email", "webhook", "mqtt", "ntfy"):
        assert f'value="{output_type}"' in markup


def test_destination_provider_selector_is_visibly_a_dropdown():
    css = (ROOT / "src/webui/destination_editor_fix.css").read_text(encoding="utf-8")
    assert '.destination-provider-type::after' in css
    assert 'content: "⌄";' in css
    assert 'pointer-events: none;' in css
    assert 'background: rgba(255, 255, 255, 0.035);' in css
    assert 'border: 1px solid var(--destination-border);' in css
    assert 'padding: 5px 24px 5px 8px;' in css
    assert 'content: none;' not in css
