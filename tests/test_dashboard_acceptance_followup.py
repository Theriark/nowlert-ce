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


def test_dashboard_workspace_summary_preserves_live_configuration_metrics():
    script = _read("src/webui/operations_acceptance.js")
    dashboard = _read("src/webui/operations_dashboard.js")
    styles = _read("src/webui/operations_acceptance.css")

    assert 'function ensureWorkspaceSummary()' in script
    assert '"Workspace Summary"' in script
    assert '"Quick overview of configuration and collaboration"' in script
    assert 'ensureWorkspaceSummary();' in script
    assert 'removeDashboardConfigurationHeading' not in script
    assert '<section class="panel ops-configuration"' in dashboard

    for item_id in (
        "ops-config-tokens",
        "ops-config-filters",
        "ops-config-shared",
        "ops-config-audit",
    ):
        assert item_id in dashboard

    for key in ("tokens", "filters", "shared", "audit"):
        assert f'key: "{key}"' in script

    for label in ("Healthy", "No filters", "Shared", "Review"):
        assert f'"{label}"' in script

    assert 'status.setAttribute("data-summary-status", key)' in script
    assert '.ops-workspace-summary' in styles
    assert '.ops-workspace-summary-icon' in styles
    assert '.ops-config-status' in styles
    assert '.ops-config-status.is-healthy' in styles
    assert '.ops-config-status.is-neutral' in styles
    assert '.ops-config-status.is-shared' in styles
    assert '.ops-config-status.is-review' in styles
