from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src/webui/policy_simplification.css"


def test_filtering_integration_behavior_uses_three_equal_visual_cards():
    styles = CSS.read_text(encoding="utf-8")

    assert "#filtering-deterministic-processing .simplified-settings-groups" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "#filtering-deterministic-processing .settings-subsection," in styles
    assert "#filtering-deterministic-processing .settings-subsection-grid" in styles
    assert "display: contents;" in styles
    assert "#filtering-deterministic-processing .settings-subsection-heading" in styles
    assert "display: none;" in styles
    assert "/ui/source-icons/unifi-protect.png" in styles
    assert "/ui/source-icons/home-assistant.png" in styles
    assert "/ui/source-icons/redfish.jpg" in styles
    assert "#filtering-deterministic-processing .settings-resource-card > .resource-actions .button" in styles
    assert "width: 100%;" in styles
