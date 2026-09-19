"""Round-46/47 regressions for Dashboard first paint and Routing Flow connectors."""

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


def test_routing_flow_connections_end_at_shared_card_ports_without_arrowheads():
    script = read("src/webui/routing_flow.js")
    css = read("src/webui/routing_flow.css")

    edge_start = script.index("function edgeCurve(a, b)")
    edge_end = script.index("function drawEdges()", edge_start)
    edge = script[edge_start:edge_end]

    assert "const xx = b.offsetLeft" in edge
    assert "targetInset" not in edge
    assert "$" + "{xx} $" + "{yy}" in edge

    draw_start = script.index("function drawEdges()")
    draw_end = script.index("function stopPulses()", draw_start)
    draw = script[draw_start:draw_end]

    assert 'svg("marker"' not in draw
    assert '"marker-end"' not in draw
    assert 'classList.remove("rf-has-incoming")' in draw
    assert 'classList.add("rf-has-incoming")' in draw

    assert ".rf-socket {" in css
    assert ".rf-node.rf-has-incoming > .rf-socket-left" in css
    assert ".rf-node.rf-has-outgoing > .rf-socket-right" in css
