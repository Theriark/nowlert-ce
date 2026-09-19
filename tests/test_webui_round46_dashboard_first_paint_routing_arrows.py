"""Round-46 regressions for Dashboard first paint and Routing Flow arrowheads."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_dashboard_show_app_paints_shell_before_authenticated_app_render():
    script = read("src/webui/operations_dashboard.js")

    start = script.index("showApp = function operationsDashboardShowApp(session)")
    end = script.index("const previousExpireSession", start)
    block = script[start:end]

    restore = block.index("restoreDashboardSnapshot(session, state.historyRange);")
    render = block.index("renderOperationsDashboard();")
    handoff = block.index("return previousShowApp(session);")

    assert restore < render < handoff


def test_routing_flow_arrowheads_use_fixed_size_marker_and_stop_before_target_card():
    script = read("src/webui/routing_flow.js")

    edge_start = script.index("function edgeCurve(a, b)")
    edge_end = script.index("function drawEdges()", edge_start)
    edge = script[edge_start:edge_end]

    assert "const targetInset = 7;" in edge
    assert "const xx = b.offsetLeft - targetInset" in edge
    assert "$" + "{xx} $" + "{yy}" in edge

    draw_start = script.index("function drawEdges()")
    draw_end = script.index("function stopPulses()", draw_start)
    draw = script[draw_start:draw_end]

    assert 'markerUnits:"userSpaceOnUse"' in draw
    assert 'viewBox:"0 0 6 6"' in draw
    assert "markerWidth:6" in draw
    assert "markerHeight:6" in draw
    assert 'd:"M0 0 L6 3 L0 6 Z"' in draw
    assert '"marker-end": "url(#rf-arrow)"' in draw
