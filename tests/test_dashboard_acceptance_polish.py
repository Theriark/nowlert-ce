from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    target = ROOT / path
    assert target.exists(), f"missing acceptance asset: {path}"
    return target.read_text(encoding="utf-8")


def test_dashboard_acceptance_layer_removes_duplicate_and_fake_live_controls():
    script = _read("src/webui/operations_acceptance.js")
    assert '.ops-range' in script
    assert 'remove()' in script
    assert '.ops-kpi-config .ops-kpi-delta' in script
    assert 'ops-live-age' in script
    assert 'data-feed' in script


def test_dashboard_range_is_persisted_per_authenticated_user():
    script = _read("src/webui/operations_acceptance.js")
    assert 'localStorage' in script
    assert 'dashboard-range' in script
    assert 'state.user' in script
    assert 'ops-dashboard-range' in script
    assert 'dispatchEvent(new Event("change"' in script


def test_routing_flow_range_is_persisted_per_authenticated_user():
    script = _read("src/webui/operations_acceptance.js")
    assert 'routing-flow-range' in script
    assert 'rf-range' in script
    assert 'dispatchEvent(new Event("change"' in script


def test_dashboard_live_status_depends_on_real_data_requests():
    script = _read("src/webui/operations_acceptance.js")
    for endpoint in ('/metrics/', '/deliveries', '/filters', '/audit-events'):
        assert endpoint in script
    assert 'request = async function' in script
    assert 'Degraded' in script
    assert 'Stale' in script
    assert 'Live' in script
    assert 'lastSuccess' in script


def test_routing_flow_live_status_depends_on_actual_poll_result():
    script = _read("src/webui/operations_acceptance.js")
    assert 'window.fetch = async function' in script
    assert '/routing-flow/' in script
    assert 'rf-live-status' in script
    assert 'Offline' in script
    assert 'Connecting' in script


def test_percentages_drop_redundant_point_zero_and_success_has_spacing():
    script = _read("src/webui/operations_acceptance.js")
    css = _read("src/webui/operations_acceptance.css")
    assert 'replace(/(\\d+)\\.0%/g, "$1%")' in script
    assert '.ops-kpi-success .ops-kpi-delta' in css
    assert 'margin-left:' in css


def test_acceptance_assets_load_after_operations_dashboard():
    service = _read("src/webui/service.py")
    assert '/ui/operations_acceptance.css' in service
    assert '/ui/operations_acceptance.js' in service
    assert service.index('/ui/operations_dashboard.js') < service.index('/ui/operations_acceptance.js')


def test_dashboard_liveness_waits_for_complete_refresh_batch():
    script = _read("src/webui/operations_acceptance.js")
    assert "dashboardRefreshBatch" in script
    assert "DASHBOARD_FEED_KEYS.every(key => batch.started.has(key))" in script
    assert "if (batch.pending.size) return;" in script
    assert "commitDashboardRefreshBatch(batch)" in script


def test_dashboard_has_inner_toolbar_with_live_then_range_controls():
    script = _read("src/webui/operations_acceptance.js")
    css = _read("src/webui/operations_acceptance.css")
    assert "ops-dashboard-toolbar" in script
    assert "toolbar.append(controls)" in script
    assert "controls.append(live, range)" in script
    assert "#view-dashboard > .ops-dashboard-toolbar" in css
    assert "content: none" in css


def test_dashboard_toolbar_reordering_is_idempotent_under_mutation_observer():
    script = _read("src/webui/operations_acceptance.js")
    assert "controls.firstElementChild !== live || live.nextElementSibling !== range" in script
    assert 'if (live && range) controls.append(live, range);' not in script


def test_recent_activity_uses_stable_status_columns():
    css = _read("src/webui/operations_acceptance.css")
    assert "grid-template-columns: 36px minmax(110px, 1fr) 82px 62px 82px 64px;" in css
    assert ".ops-activity-row .ops-severity" in css
    assert ".ops-activity-row .ops-activity-time" in css


def test_administration_tabs_follow_the_page_title_box():
    script = _read("src/webui/operations_acceptance.js")
    assert "polishAdministrationTabs" in script
    assert "toolbar.after(tabs)" in script


def test_live_tooltips_state_their_actual_scope():
    script = _read("src/webui/operations_acceptance.js")
    assert "not an external integration heartbeat" in script
    assert "not an integration or destination heartbeat" in script
