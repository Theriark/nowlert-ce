from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "src/webui/reference_acceptance.js"
CSS = ROOT / "src/webui/reference_acceptance.css"
SERVICE = ROOT / "src/webui/service.py"
COMPOSE = ROOT / "compose.managed-backups.yaml"


def test_reference_acceptance_assets_are_registered_and_loaded_after_consistency_layer():
    service = SERVICE.read_text(encoding="utf-8")

    assert '"/ui/reference_acceptance.js"' in service
    assert '"src/webui/reference_acceptance.js"' in service
    assert '"/ui/reference_acceptance.css"' in service
    assert '"src/webui/reference_acceptance.css"' in service
    assert '<link rel="stylesheet" href="/ui/reference_acceptance.css">' in service
    assert '<script src="/ui/reference_acceptance.js" defer></script>' in service
    assert service.rfind("reference_acceptance.css") > service.rfind("management_consistency.css")
    assert service.rfind("reference_acceptance.js") > service.rfind("management_consistency.js")


def test_reference_acceptance_runtime_contract():
    script = JS.read_text(encoding="utf-8")

    assert "function ensurePreviewReferenceLayout()" in script
    assert "function openPreviewRoutes()" in script
    assert '"Assigned routes"' in script
    assert 'placeholder = "Search routes..."' in script
    assert "function ensureUsersReferenceLayout()" in script
    assert "Recent activity" in script
    assert '"Never logged in"' in script
    assert "function ensureSettingsReferenceLayout()" in script
    assert "Regional settings" in script
    assert "Nowlert is up to date" in script
    assert "function ensureAccountReferenceLayout()" in script
    assert "Profile & access" in script
    assert "Password & sessions" in script
    assert "Security posture" in script
    assert 'title.textContent = "API tokens"' in script
    assert 'restart.textContent = "⏻ Restart Nowlert"' in script


def test_reference_acceptance_styles_contract():
    styles = CSS.read_text(encoding="utf-8")

    assert "#view-filtering .filtering-overview-header::after" in styles
    assert "content: none !important;" in styles
    assert '.qa-pagination-row[data-qa-pager="delivery-pagination"]' in styles
    assert '.qa-pagination-row[data-qa-pager="audit-pagination"]' in styles
    assert "grid-template-columns: minmax(145px, .8fr) minmax(330px, 1.7fr) minmax(120px, .62fr) minmax(112px, .58fr)" in styles
    assert ".reference-preview-form" in styles
    assert ".reference-preview-routing" in styles
    assert ".reference-preview-routes-open" in styles
    assert ".reference-users-metrics" in styles
    assert ".reference-settings-grid" in styles
    assert ".reference-account-grid" in styles
    assert "#restart-header-button.reference-account-restart" in styles


def test_managed_backup_override_targets_production_service_name():
    text = COMPOSE.read_text(encoding="utf-8")

    assert "  nowlert-ce:" in text
    assert "\n  nowlert:\n" not in text
    assert 'user: "0:0"' in text
    assert "- DAC_OVERRIDE" in text
    assert "- FOWNER" in text
    assert "- SYS_ADMIN" in text
