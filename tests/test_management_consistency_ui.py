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
    assert 'dashboard.textContent = `Updated ${detail.slice("Data updated ".length)}`' in script
    assert 'flow.textContent = `Updated ${detail.slice("Snapshot ".length)}`' in script
    assert '[data-delivery-workbench-action="close-detail"]' in script
    assert 'title.textContent = "Integration behavior"' in script


def test_management_consistency_styles_enlarge_destinations_and_fill_delivery_status():
    styles = CSS.read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr));" in styles
    assert "min-height: 196px;" in styles
    assert "#view-deliveries .delivery-detail-status .delivery-detail-badges" in styles
    assert "flex-wrap: nowrap;" in styles
    assert "#view-deliveries .delivery-detail-status .delivery-detail-badges > .badge" in styles
    assert "flex: 1 1 0;" in styles
    assert '#view-deliveries [data-delivery-workbench-action="close-detail"]' in styles
    assert "display: none !important;" in styles
    assert "#filtering-deterministic-processing > .panel-heading .eyebrow" in styles
