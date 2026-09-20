"""Round-39 regression for full Routing Flow filter values and +N overflow."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_routing_filter_values_are_full_width_or_moved_to_overflow():
    styles = read("src/webui/routing_flow.css")
    script = read("src/webui/routing_flow.js")

    selector = ".rf-filter-card-tags [data-filter-value]"
    assert selector in styles
    block = styles[styles.index(selector):]
    assert "flex: 0 0 auto !important;" in block
    assert "max-width: none !important;" in block
    assert "min-width: max-content;" in block
    assert "overflow: visible !important;" in block
    assert "text-overflow: clip !important;" in block
    assert "white-space: nowrap;" in block

    start = script.index("function renderFilterCard")
    end = script.index("function activeFlowGraph", start)
    card = script[start:end]
    assert "const visibleNodes = valueNodes;" in card
    assert "if (next <= available)" in card
    assert "item.hidden = true;" in card
    assert "toggle.textContent = `+${hiddenValues.length}`;" in card
    assert 'valuePopover.setAttribute("popover", "auto");' in card
    assert "valuePopover.showPopover();" in card


def test_round39_build_and_live_gate_track_full_value_overflow():
    assert UI_BUILD == "20260920-r52"

    index = read("src/webui/index.html")
    workflow = read(".github/workflows/ci.yml")

    assert 'name="nowlert-ui-build" content="20260920-r52"' in index
    assert "/ui/app.js?v=20260920-r52" in index
    assert "/ui/qa_patch.css?v=20260920-r52" in index
    assert "/ui/qa_patch.js?v=20260920-r52" in index
    assert "Routing Flow full filter values" in workflow
    assert '".rf-filter-card-tags [data-filter-value]"' in workflow
