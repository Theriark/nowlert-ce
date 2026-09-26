from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "src/webui/routing_flow.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/webui/routing_flow.css").read_text(encoding="utf-8")


def test_header_matches_management_page_pattern_and_keeps_only_range_control():
    assert 'class="section-toolbar rf-toolbar"' in SCRIPT
    assert "Visualize active routes, filters, and destinations." in SCRIPT
    assert 'id="rf-range"' in SCRIPT
    assert "Read-only" not in SCRIPT
    assert "Automatically mapped from existing configuration" not in SCRIPT
    assert "Delivery counts use the latest attempt per delivery" not in SCRIPT
    assert 'id="rf-live"' not in SCRIPT
    assert 'id="rf-pause"' not in SCRIPT
    assert "rf-footnote" not in SCRIPT
    assert 'id="rf-counts"' not in SCRIPT


def test_canvas_headings_have_no_explanatory_subtitles():
    assert '[["route", "Integration routes"], ["filter", "Active filters"], ["destination", "Destinations"]]' in SCRIPT
    assert "Event sources with configured routes" not in SCRIPT
    assert "Per destination and integration" not in SCRIPT
    assert "Alert channels receiving events" not in SCRIPT


def test_route_dialog_is_icon_led_and_contains_only_route_information():
    route_branch = SCRIPT.split('if (kind === "route") {', 1)[1].split('} else if (kind === "destination") {', 1)[0]
    assert 'setDialogTitle(route.integration_name, sourceIcon(route.source))' in route_branch
    for label in ["Route", "Integration", "Input / protocol", "Active destinations"]:
        assert f'detailRow("{label}"' in route_branch
    assert "appendMetricRows(dialogBody, route.metrics)" in route_branch
    assert 'detailRow("State"' not in route_branch
    assert "policyLines(link)" not in route_branch


def test_filter_dialog_has_identity_icons_status_and_policy_rows():
    filter_branch = SCRIPT.split(
        "const filter = current.filters.find(item => item.id === identity);", 1
    )[1].split("    drawEdges();", 1)[0]
    assert 'setDialogTitle(String(filter.filter_name || filter.name || "").trim() || "Active filter", icon("filter"))' in filter_branch
    assert 'detailRow("Sources", sourceNames.join(", ") || "Managed")' in filter_branch
    assert 'detailIdentityRow("Destination", destinationLogo(d), d.name)' in filter_branch
    assert 'detailRow("Status", "Active")' not in filter_branch
    assert "policyDetailRows({ policies: filter.policies || [], fallback: true }).forEach" in filter_branch
    assert 'detailRow("Connection"' not in filter_branch


def test_destination_dialog_has_destination_information_without_filter_rules():
    branch = SCRIPT.split('} else if (kind === "destination") {', 1)[1].split('    } else {', 1)[0]
    assert 'setDialogTitle(d.name, destinationLogo(d))' in branch
    for label in ["Platform", "Channel", "Visibility", "Active routes"]:
        assert f'detailRow("{label}"' in branch
    assert "appendMetricRows(dialogBody, d.metrics)" in branch
    assert "policyLines(" not in branch
    assert 'detailRow("State"' not in branch


def test_dialogs_do_not_show_read_only_footer_note():
    assert "rf-detail-note" not in SCRIPT
    assert "Read-only snapshot. Configuration remains in Destinations and Filtering." not in SCRIPT


def test_zoom_and_fit_controls_have_equal_dimensions():
    assert ".rf-canvas-footer .rf-zoom, .rf-canvas-footer #rf-fit" in CSS
    assert "width:126px" in CSS
    assert "height:40px" in CSS


def test_dialog_icons_have_scoped_sizes():
    assert ".rf-dialog-title-icon" in CSS
    assert ".rf-detail-identity" in CSS
    assert ".rf-detail-icon" in CSS


def test_routing_node_pulse_modes_follow_active_direct_and_filtered_links():
    assert "NowlertRoutingPulseModel?.resolveNodeModes(current)" in SCRIPT
    assert 'classList.remove("rf-pulse-single", "rf-pulse-dual", "rf-pulse-mixed")' in SCRIPT
    assert 'classList.add(`rf-pulse-${item.mode}`)' in SCRIPT
    assert "rf-node.rf-route.rf-pulse-single" in CSS
    assert "rf-node.rf-destination.rf-pulse-dual" in CSS
    assert "rf-node.rf-route.rf-pulse-mixed" in CSS
    assert "rf-card-highlight-yellow" in CSS
    assert "rf-card-highlight-gray" in CSS
    assert "rf-node-tracer" not in CSS


def test_routing_pulse_keeps_filter_geometry_and_metric_exceptions():
    assert ".rf-filter { min-height:66px; padding:10px; gap:10px; }" in CSS
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in CSS
    assert "#view-routing-flow .rf-metric::before { content:none !important; display:none !important; }" in CSS
    assert "@media(prefers-reduced-motion:reduce)" in CSS
