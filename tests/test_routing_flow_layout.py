from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTING_FLOW = ROOT / "src" / "webui" / "routing_flow.js"


def test_routing_flow_only_contains_active_connected_paths():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "function activeFlowGraph()" in script
    assert "link.enabled && routeIds.has(link.route_id) && destinationIds.has(link.destination_id)" in script
    assert "connectedRouteIds" in script
    assert "connectedDestinationIds" in script
    assert "No visible destination assigned" not in script
    assert "No active connected routes and destinations." in script
    assert "const assigned = current.links.filter(link => link.destination_id === d.id).length" in script


def test_routing_flow_uses_pixel_auto_layout_instead_of_grid_rows():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "function resolveCenters(" in script
    assert "function computeFlowLayout(current, ordered, headerBottom)" in script
    assert 'node.style.position = "absolute"' in script
    assert "node.style.top =" in script
    assert "node.dataset.layoutY" in script
    assert "connected-pixel-auto" in script
    assert "routeRows" not in script
    assert "destinationRows" not in script
    assert "filterRows" not in script
    assert "node.style.gridRow = `${row} / span ${span}`" not in script


def test_routing_flow_uses_smooth_curves_for_every_active_path():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "function edgeCurve(a, b)" in script
    assert 'return `M${x} ${y} C${x+bend} ${y} ${xx-bend} ${yy} ${xx} ${yy}`' in script
    assert " L${turn}" not in script
    assert "Keep unfiltered traffic level through the filter column" not in script
    assert "for (const link of current.links)" in script


def test_routing_flow_reflows_when_canvas_size_changes():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "if(data&&active())renderGraph();else drawEdges();" in script
