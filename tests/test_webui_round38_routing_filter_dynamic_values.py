"""Round-38 regression for width-driven Routing Flow filter values."""

from pathlib import Path

from webui.service import UI_BUILD


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_filter_value_fitting_uses_available_width_without_a_fixed_cap():
    script = read("src/webui/routing_flow.js")

    start = script.index("function renderFilterCard")
    end = script.index("function activeFlowGraph", start)
    card = script[start:end]

    assert "const visibleValueLimit = 6;" not in card
    assert ".slice(0, visibleValueLimit)" not in card
    assert "for (const item of valueNodes) item.hidden = false;" in card
    assert "const visibleNodes = valueNodes;" in card
    assert "const available = Math.max(0, width - overflowWidth - gap);" in card
    assert "if (next <= available)" in card
    assert "toggle.textContent = `+${hiddenValues.length}`;" in card

    # Preserve the Round-37 top-layer overflow behavior.
    assert 'valuePopover.setAttribute("popover", "auto");' in card
    assert "valuePopover.showPopover();" in card


def test_round38_build_and_live_gate_track_dynamic_value_fitting():
    assert UI_BUILD == "20260919-r38"

    index = read("src/webui/index.html")
    workflow = read(".github/workflows/ci.yml")

    assert 'name="nowlert-ui-build" content="20260919-r38"' in index
    assert "/ui/app.js?v=20260919-r38" in index
    assert "/ui/qa_patch.css?v=20260919-r38" in index
    assert "/ui/qa_patch.js?v=20260919-r38" in index

    assert "Routing Flow dynamic value fitting" in workflow
    assert '"const visibleNodes = valueNodes;"' in workflow
    assert "Routing Flow six visible values" not in workflow
