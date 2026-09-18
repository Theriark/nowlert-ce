from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _after(path: str, marker: str) -> str:
    value = (ROOT / path).read_text(encoding="utf-8")
    assert marker in value
    return value[value.index(marker):]


def test_round20_backup_columns_align_at_compact_equal_height():
    final = _after(
        "src/webui/qa_patch.css",
        "/* 2026-09-18 round-20 aligned compact backups. */",
    )

    assert ".backup-dashboard-grid-top {" in final
    assert "align-items: stretch !important;" in final
    assert "#backup-schedule-panel," in final
    assert "#backup-data-tools-panel {" in final
    assert "height: 300px !important;" in final
    assert "max-height: 300px !important;" in final
    assert "min-height: 300px !important;" in final


def test_round20_data_tools_inner_columns_align_and_stay_compact():
    final = _after(
        "src/webui/qa_patch.css",
        "/* 2026-09-18 round-20 aligned compact backups. */",
    )

    assert "#backup-data-tools-panel > .backup-data-tools-grid {" in final
    assert "align-items: stretch !important;" in final
    assert "grid-auto-rows: 1fr;" in final
    assert "#backup-data-tools-panel .data-tools-reference-card {" in final
    assert "height: 100% !important;" in final
    assert "padding: 12px 14px !important;" in final
    assert "min-height: 45px !important;" in final
    assert "margin-top: auto !important;" in final
    assert "height: 40px !important;" in final
    assert "min-height: 36px !important;" in final


def test_routing_flow_uses_the_approved_live_filter_card_without_fake_metrics():
    script = (ROOT / "src/webui/routing_flow.js").read_text(encoding="utf-8")

    assert "function renderFilterCard(" in script
    assert "function filterRuleTags(link)" in script
    assert "policy.legacy_clauses?.length" in script
    assert 'key.startsWith("__")' in script
    assert '["Events in", filterMetricText(filter.metrics?.received), "yellow"]' in script
    assert '["Filtered out", filterMetricText(filter.metrics?.filtered), "cyan"]' in script
    assert '["Reduction", filterReductionText(filter.metrics), "green"]' in script
    assert 'return Number.isFinite(value) ? String(value) : "—";' in script
    assert 'return "—";' in script
    assert "renderFilterCard(node, filter, routes, destination);" in script
    assert "rangeLabel()" in script
    assert "destination.name" in script


def test_routing_flow_filter_card_keeps_coloured_tags_and_travelling_yellow_border():
    style = (ROOT / "src/webui/routing_flow.css").read_text(encoding="utf-8")

    assert "/* 2026-09-18 approved compact Routing Flow filter card. */" in style
    assert ".rf-filter-card {" in style
    assert "min-height: 168px !important;" in style
    assert ".rf-filter-rule-tag-yellow" in style
    assert ".rf-filter-rule-tag-blue" in style
    assert ".rf-filter-rule-tag-green" in style
    assert ".rf-filter-card-stat-yellow strong" in style
    assert ".rf-filter-card-stat-cyan strong" in style
    assert ".rf-filter-card-stat-green strong" in style
    assert "@keyframes rf-filter-border-travel" in style
    assert "conic-gradient(" in style
    assert "#ffd13a" in style
    assert "animation: rf-filter-border-travel 3.2s linear infinite;" in style
    assert "nfc-bars" not in style
    assert "nfc-ring" not in style
