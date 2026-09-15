from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "src" / "webui" / "destination_editor_fix.css"


def test_more_routes_menu_has_packaged_vertical_popover_layout():
    stylesheet = STYLE.read_text(encoding="utf-8")

    assert ".destination-route-more-wrap" in stylesheet
    assert ".destination-route-more-menu {" in stylesheet
    assert "position: absolute" in stylesheet
    assert "display: grid" in stylesheet
    assert "max-height: min(320px, 45vh)" in stylesheet
    assert "min-width: 300px" in stylesheet
    assert "overflow-y: auto" in stylesheet
    assert ".destination-route-more-menu .destination-route-pill" in stylesheet
    assert "width: 100%" in stylesheet
    assert "justify-content: flex-start" in stylesheet
