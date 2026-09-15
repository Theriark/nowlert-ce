from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "src" / "webui" / "destination_routes.css"


def test_destination_close_button_stays_anchored_on_hover():
    stylesheet = STYLE.read_text(encoding="utf-8")

    base_start = stylesheet.index(".destination-editor-heading > .icon-button {")
    base_end = stylesheet.index("}", base_start) + 1
    base_block = stylesheet[base_start:base_end]

    assert "position: relative;" in base_block
    assert "right: -8px;" in base_block
    assert "top: -8px;" in base_block
    assert "transform: translate(8px, -8px);" not in base_block

    hover_selector = ".destination-editor-heading > .icon-button:hover:not(:disabled) {"
    hover_start = stylesheet.index(hover_selector)
    hover_end = stylesheet.index("}", hover_start) + 1
    hover_block = stylesheet[hover_start:hover_end]

    assert "transform: none;" in hover_block
