from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    target = ROOT / path
    assert target.exists(), f"missing acceptance asset: {path}"
    return target.read_text(encoding="utf-8")


def test_dashboard_range_uses_routing_style_without_placeholder_icon():
    script = _read("src/webui/operations_acceptance.js")
    assert 'control.querySelector(".ops-calendar")?.remove()' in script
    assert 'control.classList.remove("ops-global-range")' in script
    assert 'control.classList.add("rf-range", "ops-dashboard-range-control")' in script
    assert 'const range = byId("ops-dashboard-range")?.closest("label")' in script


def test_persisted_ranges_restore_before_first_authenticated_paint():
    script = _read("src/webui/operations_acceptance.js")
    assert 'showApp = function operationsAcceptanceShowApp(session)' in script
    assert 'restorePersistedRanges("dashboard")' in script
    assert 'restorePersistedRanges("routing-flow")' in script


def test_dashboard_keeps_configuration_metrics_and_removes_only_heading():
    script = _read("src/webui/operations_acceptance.js")
    dashboard = _read("src/webui/operations_dashboard.js")
    assert 'function removeDashboardConfigurationHeading()' in script
    assert 'document.querySelector("#view-dashboard .ops-configuration .ops-config-heading")?.remove()' in script
    assert 'removeDashboardConfigurationHeading();' in script
    assert 'strip.replaceWith(sink)' not in script
    assert 'ops-dashboard-configuration-sink' not in script
    assert '<section class="panel ops-configuration"' in dashboard
    for item_id in (
        "ops-config-tokens",
        "ops-config-filters",
        "ops-config-shared",
        "ops-config-audit",
    ):
        assert item_id in dashboard
