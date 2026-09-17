from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "src/webui/management_consistency.js"
CSS = ROOT / "src/webui/management_consistency.css"
SERVICE = ROOT / "src/webui/service.py"


def test_management_consistency_assets_are_registered_and_loaded_last():
    service = SERVICE.read_text(encoding="utf-8")

    assert '"/ui/management_consistency.js"' in service
    assert '"src/webui/management_consistency.js"' in service
    assert '"/ui/management_consistency.css"' in service
    assert '"src/webui/management_consistency.css"' in service
    assert '<link rel="stylesheet" href="/ui/management_consistency.css">' in service
    assert '<script src="/ui/management_consistency.js" defer></script>' in service
    assert service.rfind("management_consistency.css") > service.rfind("audit_log_refinement.css")
    assert service.rfind("management_consistency.js") > service.rfind("audit_log_refinement.js")


def test_management_consistency_runtime_matches_selected_ui_contract():
    script = JS.read_text(encoding="utf-8")

    assert 'add.textContent = "+ New destination"' in script
    assert 'button.textContent = "+ New user"' in script
    assert 'span("destination-status-dot")' in script
    assert 'shareIcon()' in script
    assert 'span("destination-status-label", enabled ? "Active" : "Disabled")' in script
    assert 'span("destination-sharing-label", shared ? "Shared" : "Private")' in script
    assert 'acceptance-private-destination' in script
    assert 'privateBadge.className = "badge destination-sharing-control is-private"' in script
    assert 'dashboard.textContent = `Updated ${detail.slice("Data updated ".length)}`' in script
    assert 'flow.textContent = `Updated ${detail.slice("Snapshot ".length)}`' in script
    assert '"#view-deliveries .delivery-history-detail-close"' in script
    assert '[data-delivery-workbench-action="close-detail"]' not in script
    assert '"#view-audit .audit-log-detail-close"' in script
    assert '"#view-users .private-resource-count"' in script
    assert 'second.textContent = "Configuration"' in script
    assert 'title.textContent = "Integration behavior"' in script


def test_management_consistency_styles_cover_workbench_layout_regressions():
    styles = CSS.read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr));" in styles
    assert "min-height: 196px;" in styles
    assert "#view-deliveries .delivery-history-status-row" in styles
    assert ".delivery-detail-status .delivery-detail-badges" not in styles
    assert "grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));" in styles
    assert "#view-deliveries .delivery-history-status-row > .badge" in styles
    assert "width: 100%;" in styles
    assert "#view-deliveries .delivery-history-detail-close," in styles
    assert "#view-audit .audit-log-detail-close" in styles
    assert "grid-template-columns: minmax(0, 1fr) auto;" in styles
    assert "minmax(118px, 0.75fr)" in styles
    assert "overflow: visible;" in styles
    assert "#view-deliveries .delivery-history-list-footer .qa-pagination-row," in styles
    assert "#view-audit .audit-log-list-footer .qa-pagination-row" in styles
    assert "grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);" in styles
    assert "grid-column: 2;" in styles
    assert "grid-column: 3;" in styles
    assert "#filtering-deterministic-processing > .panel-heading .eyebrow" in styles
