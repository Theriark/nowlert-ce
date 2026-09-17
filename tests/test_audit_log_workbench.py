from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_selected_audit_log_workbench_contract():
    script = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    style = (ROOT / "src" / "webui" / "page_headers.css").read_text(encoding="utf-8")

    for token in (
        "audit-log-workbench",
        "audit-log-summary",
        "audit-log-action-filter",
        "audit-log-outcome-filter",
        "audit-log-range-filter",
        "audit-log-detail",
        "audit-log-detail-tabs",
        "audit-log-health-strip",
        "qaLoadAuditPage = async function",
        "renderAudit = function",
    ):
        assert token in script

    assert "#view-audit .audit-log-workbench" in style
    assert "grid-template-columns: minmax(0, 1.15fr) minmax(390px, 0.85fr);" in style
    assert ".audit-log-list-scroll" in style
    assert "overflow-y: auto;" in style
