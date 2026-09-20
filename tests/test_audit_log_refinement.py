from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_log_refinement_assets_are_wired_last():
    service = (ROOT / "src" / "webui" / "service.py").read_text(encoding="utf-8")

    assert '"/ui/audit_log_refinement.js"' in service
    assert '"/ui/audit_log_refinement.css"' in service
    assert service.index('/ui/audit_log_refinement.css') > service.index('/ui/page_headers.css')
    assert service.index('/ui/audit_log_refinement.js') > service.index('/ui/page_headers.js')


def test_audit_log_refinement_matches_selected_interaction_contract():
    script = (ROOT / "src" / "webui" / "audit_log_refinement.js").read_text(
        encoding="utf-8"
    )
    styles = (ROOT / "src" / "webui" / "audit_log_refinement.css").read_text(
        encoding="utf-8"
    )

    assert "Execute all health checks" in script
    assert 'button.className = "button primary audit-run-checks"' in script
    assert 'document.querySelectorAll("#view-audit .audit-log-row-more")' in script
    assert "node.remove()" in script
    assert "function requestEntries(item)" in script
    assert "function responseEntries(item)" in script
    assert "function generalEntries(item)" in script
    assert "Historical events are not backfilled." in script
    assert "audit-refine-list" in script

    assert "fetchAuditAnalytics" in script
    assert "/audit-events/page/${page}/size/500" in script
    assert "vs. previous 7 days" in script
    assert "Last 7 days" in script
    assert "All pages" in script

    assert "renderHealthDashboard" in script
    assert "Latest health check run" in script
    assert "Latest real operational checks across Nowlert." in script
    assert "persistHealthSnapshot" in script
    assert 'request("/health-checks")' in script

    assert ".audit-run-checks" in styles
    assert ".audit-refine-row" in styles
    assert ".audit-refine-list" in styles
    assert "grid-template-columns: minmax(112px, 0.46fr) minmax(0, 1.54fr) 30px;" in styles
    assert "#view-audit .audit-log-row-more" in styles
    assert "display: none !important;" in styles
    assert ".audit-health-dashboard" in styles
    assert ".audit-refine-trend" in styles


def test_audit_tabs_do_not_dump_request_and_response_metadata_into_details():
    script = (ROOT / "src" / "webui" / "audit_log_refinement.js").read_text(
        encoding="utf-8"
    )

    assert "!isRequestKey(key)" in script
    assert "!isResponseKey(key)" in script
    assert "detailRows(generalEntries(item))" in script
    assert "detailRows(requestEntries(item))" in script
    assert "detailRows(responseEntries(item))" in script


def test_audit_log_alignment_polish_matches_accepted_desktop_layout():
    styles = (ROOT / "src" / "webui" / "audit_log_refinement.css").read_text(
        encoding="utf-8"
    )

    assert ".audit-run-checks-copy small" in styles
    assert "display: none !important;" in styles
    assert "grid-template-columns: minmax(0, 1.05fr) minmax(460px, 0.95fr);" in styles
    assert "align-items: stretch;" in styles
    assert "grid-template-columns: minmax(300px, 1.78fr)" in styles
    assert "height: 100%;" in styles

def test_audit_summary_analytics_restore_immediately_after_refresh():
    script = (ROOT / "src" / "webui" / "audit_log_refinement.js").read_text(
        encoding="utf-8"
    )

    assert 'const AUDIT_ANALYTICS_STORAGE_VERSION = "v1";' in script
    assert "function auditAnalyticsStorageKey()" in script
    assert "function normalizedAuditAnalytics(value)" in script
    assert "function readAuditAnalytics()" in script
    assert "function persistAuditAnalytics(value)" in script
    assert "function restoreAuditAnalytics()" in script
    assert "window.sessionStorage.getItem(key)" in script
    assert "window.sessionStorage.setItem(key, JSON.stringify(normalized))" in script
    assert "persistAuditAnalytics(auditAnalytics);" in script

    refine_start = script.index("function refineAudit()")
    refine_end = script.index("function scheduleRefine()", refine_start)
    refine = script[refine_start:refine_end]
    assert refine.index("restoreAuditAnalytics();") < refine.index("ensureSummaryMetricChrome();")
    assert refine.index("restoreAuditAnalytics();") < refine.index("applyAuditAnalytics();")

