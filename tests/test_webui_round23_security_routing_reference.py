from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_account_page_title_is_security_without_profile_fallback():
    app = read("src/webui/app.js")
    headers = read("src/webui/page_headers.js")
    markup = read("src/webui/index.html")
    reference = read("src/webui/reference_acceptance.js")

    assert 'account: "Security"' in app
    assert 'if (view === "account") return "Security";' in headers
    assert '<section id="view-account"' in markup
    assert '<h2>Security</h2><p>Manage your profile information and account access.</p>' in markup
    assert 'title.textContent = "Security";' in reference


def test_profile_card_matches_approved_left_status_right_and_three_bottom_cards():
    script = read("src/webui/reference_acceptance.js")
    style = read("src/webui/reference_acceptance.css")

    assert '<h2>Profile</h2>' in script
    marker = "/* 2026-09-18 round-23 Profile reference alignment. */"
    assert marker in style
    final = style[style.index(marker):]
    assert "grid-template-columns: minmax(0, 1.08fr) minmax(250px, 0.92fr) !important;" in final
    assert ".reference-account-card-heading" in final
    assert "grid-column: 1 / -1 !important;" in final
    assert ".reference-profile-body" in final
    assert "grid-column: 1 !important;" in final
    assert ".reference-access-status" in final
    assert "grid-column: 2 !important;" in final
    assert ".reference-account-meta" in final
    assert "grid-template-columns: repeat(3, minmax(0, 1fr)) !important;" in final


def test_routing_flow_owns_its_range_control_without_dashboard_rewrites():
    flow = read("src/webui/routing_flow.js")
    dashboard = read("src/webui/operations_dashboard.js")

    assert 'class="rf-range ops-dashboard-range-control"' in flow
    assert "syncRangeOptionsFromDashboard" not in flow
    assert "installRoutingFlowRanges" not in dashboard
    assert '["15m", "Last 15 minutes"]' not in dashboard
    for label in (
        "Last 10 minutes",
        "Last 1 hour",
        "Last 24 hours",
        "Last 1 month",
        "Last 1 year",
    ):
        assert label in flow


def test_routing_filter_keeps_outer_size_and_animation_but_uses_reference_interior():
    script = read("src/webui/routing_flow.js")
    style = read("src/webui/routing_flow.css")

    assert "function filterCardDescriptor(filter)" in script
    assert "Applied to active route" not in script
    assert "policy.policy_rules" in script
    assert "current.filters" in script
    assert "filter.route_ids" in script
    assert "function filterCardValues(filter)" in script
    assert "rf-filter-rule-tag" in script
    assert "filterTagTone(value)" in script
    assert 'const sourceSummary = el("span", "rf-filter-card-sources")' in script
    assert "for (const source of configuredSources)" in script
    assert 'sourceNode.dataset.filterSource = "1";' in script
    assert 'const destinationSummary = el("span", "rf-filter-card-destination")' in script
    assert "rf-filter-card-period" not in script

    assert "min-height: 168px !important;" in style
    assert "animation: rf-filter-border-travel 3.2s linear infinite;" in style
    assert "@keyframes rf-filter-border-travel" in style
    assert "/* 2026-09-18 round-23 reference filter interior; outer card geometry unchanged. */" in style
