from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / "src/webui/visual_refinement.css"
THEME = THEME_PATH.read_text(encoding="utf-8") if THEME_PATH.exists() else ""
ROUTING = (ROOT / "src/webui/routing_flow.css").read_text(encoding="utf-8")
APP_VIEWS = (
    "dashboard", "routing-flow", "sources", "destinations", "routes", "tokens",
    "deliveries", "email-alerts", "audit", "backups", "users", "settings",
    "updates", "inputs", "data", "account",
)


def test_shared_charcoal_surface_covers_all_menus_and_nested_cards():
    assert "--surface: #202327;" in THEME
    assert "background: linear-gradient(180deg, rgba(17, 24, 31, 0.98), rgba(12, 18, 24, 0.98)) !important;" in THEME
    for view in APP_VIEWS:
        assert f"#view-{view}#view-{view}" in THEME
    for nested in (
        ".audit-log-detail", ".email-condition-row", ".data-tools-reference-card",
        ".reference-user-metric", ".housekeeping-workspace", ".reference-profile-body",
        ".delivery-history-detail-card",
    ):
        assert nested in THEME


def test_surface_accent_pulses_but_excludes_dashboard_kpis_and_routing_metrics():
    assert "ops-dashboard-accent-pulse 2s ease-in-out infinite" in THEME
    assert "#view-dashboard#view-dashboard .ops-kpi-card::before" in THEME
    assert "content: none !important;" in THEME
    assert ".rf-page .rf-node:not(.rf-filter-card)::before" in THEME
    assert "#view-routing-flow .rf-metric::before { content:none !important; display:none !important; }" in ROUTING
    for view in APP_VIEWS:
        assert f"#view-{view}#view-{view}" in THEME


def test_filter_cards_keep_geometry_content_semantics_and_approved_pulse():
    assert ".rf-filter { min-height:66px; padding:10px; gap:10px; }" in ROUTING
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in ROUTING
    assert ".rf-filter-card-tags" in ROUTING and ".rf-filter-rule-tag-blue { color: #12bce9" in ROUTING
    assert "rf-node.rf-filter.rf-pulse-dual::before" in ROUTING
    assert "@keyframes rf-trace-forward" in ROUTING
    assert "#view-routing-flow#view-routing-flow .rf-filter-card" in THEME
    assert "):not(button):not(input):not(select):not(textarea):not(.rf-filter-card):not(.rf-filter-card *)" in THEME


def test_semantic_colors_and_reduced_motion_remain_intact():
    assert ".ops-severity.severity-critical" in THEME
    assert ".ops-severity.severity-warning" in THEME
    assert ".ops-config-status.is-shared { --status-rgb: 114, 180, 255; }" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
