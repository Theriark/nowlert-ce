"""Round-30 Routing Flow filter-card and Filtering list regressions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_routing_filter_card_shows_only_field_name_tags_in_one_row():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")
    start = script.index("function renderFilterRuleRow(group, groupIndex)")
    end = script.index("const stats =", start)
    block = script[start:end]

    assert 'const row = el("div", "rf-filter-rule-row");' in block
    assert 'const label = el("span", "rf-filter-rule-label", group.label);' in block
    assert "data-filter-value" not in block
    assert "for (const value of group.values)" not in block
    assert "rf-filter-overflow-button" not in block

    assert "/* 2026-09-19 round-30 compact filter field summary. */" in styles
    round30 = styles.split(
        "/* 2026-09-19 round-30 compact filter field summary. */", 1
    )[1]
    assert "display: flex !important;" in round30
    assert "flex-wrap: nowrap !important;" in round30
    assert ".rf-filter-rule-row" in round30
    assert "display: contents !important;" in round30


def test_routing_filter_source_overflow_uses_hovering_popover_not_second_line():
    script = read("src/webui/routing_flow.js")
    styles = read("src/webui/routing_flow.css")
    start = script.index("const sourceGroup =")
    end = script.index("const destinationGroup =", start)
    block = script[start:end]

    assert "rf-filter-source-overflow-wrap" in block
    assert "rf-filter-source-popover" in block
    assert "rf-filter-source-popover-item" in block
    assert "sourceMenuOpen" in block
    assert "sourcesExpanded" not in block
    assert 'popover.hidden = !sourceMenuOpen;' in block
    assert 'toggle.setAttribute("aria-expanded", String(sourceMenuOpen));' in block

    assert ".rf-filter-source-overflow-wrap" in styles
    assert ".rf-filter-source-popover" in styles
    assert "position: absolute;" in styles
    assert "z-index: 50;" in styles


def test_filtering_overview_shows_persisted_filter_name_column():
    script = read("src/webui/filtering.js")
    ownership = read("src/webui/filtering_ownership_sync.js")

    assert "<th>Name</th>" in script
    assert 'className: "filtering-name-cell"' in script
    assert 'text: String(policy.filter_name || "").trim() || "—"' in script
    assert 'className: "filtering-status-cell"' in script
    assert 'row.querySelector(".filtering-status-cell")' in ownership


def test_routing_flow_filter_cards_are_packed_from_top_after_ordering():
    script = read("src/webui/routing_flow.js")

    assert "function packCentersFromTop(items, heights, gap, minimumTop)" in script
    layout = script[
        script.index("function computeFlowLayout(current, ordered, headerBottom)"):
        script.index("function positionNode", script.index("function computeFlowLayout(current, ordered, headerBottom)"))
    ]
    assert "filterCenters = packCentersFromTop(filterItems, filterHeights, 12, headerBottom);" in layout
    assert layout.count(
        "filterCenters = shiftCentersToTop(filterCenters, filterItems, filterHeights, headerBottom);"
    ) >= 2
