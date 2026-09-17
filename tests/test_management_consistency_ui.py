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
    assert '"Owner: User"' in script
    assert '"View only"' in script
    assert 'destination-reference-card' in script
    assert 'dashboard.textContent = `Updated ${detail.slice("Data updated ".length)}`' in script
    assert 'flow.textContent = `Updated ${detail.slice("Snapshot ".length)}`' in script
    assert '"#view-deliveries .delivery-history-detail-close"' in script
    assert '[data-delivery-workbench-action="close-detail"]' not in script
    assert '"#view-audit .audit-log-detail-close"' in script
    assert '"#view-users .private-resource-count"' in script
    assert 'second.textContent = "Configuration"' in script
    assert 'element("h3", { text: "Integration behavior" })' in script
    assert 'Configure how each integration handles and maps incoming data.' in script
    assert 'integration-behavior-count' in script
    assert 'CHANNEL_DESTINATION_TYPES' in script
    assert 'destination-channel-prefix' in script
    assert 'result.channel_name = channel ? `#${channel}` : "";' in script
    assert 'pagerButton("«", "First page"' in script
    assert 'pagerButton("‹", "Previous page"' in script
    assert 'pagerButton("›", "Next page"' in script
    assert 'pagerButton("»", "Last page"' in script
    assert 'span("reference-pagination-label", "Go to page")' in script
    assert 'text: "Go"' in script


def test_management_consistency_styles_cover_workbench_layout_regressions():
    styles = CSS.read_text(encoding="utf-8")

    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert "min-height: 228px;" in styles
    assert ".destination-channel-input" in styles
    assert ".destination-channel-prefix" in styles
    assert "#view-deliveries .delivery-history-status-row" in styles
    assert ".delivery-detail-status .delivery-detail-badges" not in styles
    assert "grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));" in styles
    assert "#view-deliveries .delivery-history-status-row > .badge" in styles
    assert "width: 100%;" in styles
    assert "#view-deliveries .delivery-history-detail-close," in styles
    assert "#view-audit .audit-log-detail-close" in styles
    assert "grid-template-columns: minmax(0, 1fr) auto;" in styles
    assert "minmax(126px, 0.82fr)" in styles
    assert "overflow: visible;" in styles
    assert "#view-deliveries .delivery-history-list-footer .qa-pagination-row," in styles
    assert "#view-audit .audit-log-list-footer .qa-pagination-row" in styles
    assert "reference-pagination-range" in styles
    assert "reference-pagination-pages" in styles
    assert "reference-pagination-jump" in styles
    assert "reference-pagination-page.is-current" in styles
    assert "background: #eeb824;" in styles
    assert "#view-filtering .filtering-overview-details > summary" in styles
    assert "summary::-webkit-details-marker" in styles
    assert "#filtering-deterministic-processing > .panel-heading" in styles
    assert ".integration-behavior-heading-main" in styles
    assert ".integration-behavior-count" in styles
