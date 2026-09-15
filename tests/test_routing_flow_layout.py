from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTING_FLOW = ROOT / "src" / "webui" / "routing_flow.js"


def test_routing_flow_layout_is_derived_from_live_topology():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "function computeFlowLayout()" in script
    assert "function barycentricOrder(" in script
    assert "linksByRoute" in script
    assert "linksByDestination" in script
    assert "routeRows" in script
    assert "destinationRows" in script
    assert "filterRows" in script
    assert "node.dataset.layoutRow = String(row)" in script

    # Regression: the first implementation independently pinned Routes and
    # Destinations to unrelated fixed row sequences. That produced the tangled
    # graph seen when only a few filters were active.
    assert "Math.floor(i * rows / data.destinations.length)" not in script
    assert "row += span" not in script
    assert "row + index" not in script


def test_routing_flow_only_inserts_active_filters_and_bypasses_the_filter_column():
    script = ROUTING_FLOW.read_text(encoding="utf-8")

    assert "if (!activePolicies(link).length) continue" in script
    assert "nearestFreeRow(routeRows.get(route.id), usedFilterRows)" in script
    assert "const pairs = filter ? [[route,filter,false],[filter,destination,false]] : [[route,destination,true]]" in script
    assert "const turn = x + gap * .68" in script
    assert "Keep unfiltered traffic level through the filter column" in script
