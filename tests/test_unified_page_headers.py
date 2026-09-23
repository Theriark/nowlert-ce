from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unified_header_assets_are_wired_after_acceptance_layers():
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")

    assert '"/ui/page_headers.js"' in service
    assert '"/ui/page_headers.css"' in service
    assert service.index('/ui/page_headers.css') > service.index('/ui/operations_acceptance.css')
    assert service.index('/ui/page_headers.js') > service.index('/ui/operations_acceptance.js')


def test_requested_surfaces_use_one_page_command_header():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")

    for view in (
        'dashboard', 'routing-flow', 'destinations', 'filtering', 'deliveries',
        'email-alerts', 'audit', 'backups', 'tokens', 'account',
    ):
        assert f'"{view}"' in script

    assert 'const ADMIN_VIEWS = new Set(["users", "settings", "updates", "data"]);' in script
    assert 'page-command-copy' in script
    assert 'page-subtitle' in script
    assert 'page-data-toolbar' in script
    assert 'administration-section-header' in script
    assert 'ops-dashboard-top-actions' in script
    assert 'rf-live-status' in script
    assert 'platform-restart' in script
    assert 'data-qa-bottom' in script


def test_unified_header_styles_cover_page_admin_and_data_toolbar_levels():
    styles = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert '.topbar.page-command-bar' in styles
    assert '.page-command-copy' in styles
    assert '.page-command-actions' in styles
    assert '.page-data-toolbar' in styles
    assert '.administration-section-header' in styles
    assert '.administration-tabs' in styles


def test_acceptance_dashboard_does_not_reparent_controls_owned_by_unified_header():
    script = (ROOT / "src" / "webui" / "operations_acceptance.js").read_text(encoding="utf-8")

    assert 'const unifiedHeaderOwnsControls = document.querySelector(".topbar.page-command-bar");' in script
    assert 'if (!unifiedHeaderOwnsControls && controls.parentElement !== toolbar) toolbar.append(controls);' in script


def test_delivery_search_and_bottom_shortcut_live_in_delivery_panel():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert 'const DATA_TOOLBAR_VIEWS = new Set(["audit"]);' in script
    assert 'function syncDeliveryPanelControls(section)' in script
    assert '[data-panel-header="deliveries"]' in script
    assert '[data-qa-bottom="delivery-pagination"]' in script
    assert 'node.matches?.("[data-qa-bottom]")' in script
    assert '.delivery-panel-controls' in styles


def test_audit_bottom_shortcut_is_visible_and_not_deleted():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert 'removeBottomShortcut' not in script
    assert '.page-data-toolbar [data-qa-bottom]' in styles
    assert 'display: inline-flex !important;' in styles


def test_audit_health_results_are_visible_without_restoring_old_heading_box():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert 'function syncAuditHealthResults(section)' in script
    assert 'healthPanel.hidden = false;' in script
    assert 'healthPanel.removeAttribute("aria-hidden")' in script
    assert 'heading.hidden = true' in script
    assert '.health-panel.audit-health-results' in styles


def test_backup_add_action_is_owned_by_backup_storage_panel():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    assert 'function syncBackupAction(section)' in script
    assert '.backup-targets-card > .panel-heading' in script
    assert 'panelHeading.append(action)' in script
    assert 'else if (view === "backups")' not in script
    assert '.backup-targets-card > .panel-heading > [data-action="new-backup-target"]' in styles



def test_email_alerts_primary_action_is_promoted_to_unified_header():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")

    assert 'view === "email-alerts"' in script
    assert 'document.getElementById("email-primary-action")' in script
    assert '"email-alerts": "Connect mailboxes' in script
