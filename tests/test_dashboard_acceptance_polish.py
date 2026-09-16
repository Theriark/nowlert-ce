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
