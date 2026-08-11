from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "src" / "webui" / "qa_patch.js"


def test_nce_21_complete_include_filters_collapse_to_all_events() -> None:
    content = PATCH.read_text(encoding="utf-8")

    assert 'const QA_ALL_SEVERITIES = ["debug", "information", "warning", "error", "critical", "failure"]' in content
    assert 'const QA_ALL_STATUSES = ["active", "resolved", "firing", "recovered", "success", "skipped", "failure"]' in content
    assert "qaSelectionCoversAll(normalized.severities, QA_ALL_SEVERITIES)" in content
    assert "qaSelectionCoversAll(normalized.statuses, QA_ALL_STATUSES)" in content
    assert 'return summary === "All events" ? "All Events" : summary;' in content


def test_delivery_history_removes_placeholder_and_duplicate_badges() -> None:
    content = PATCH.read_text(encoding="utf-8")

    assert "function qaNormalizeDeliveryBadges()" in content
    assert 'text === "—" || seen.has(key)' in content
    assert "renderDeliveriesWithoutDuplicateBadges" in content
    assert "qaLoadDeliveryPageWithoutDuplicateBadges" in content


def test_nce_25_hides_http_and_api_path_from_user_errors_but_logs_details() -> None:
    content = PATCH.read_text(encoding="utf-8")

    assert "function qaSafeErrorMessage(message)" in content
    assert "HTTP\\s+\\d{3}" in content
    assert "\\/api\\/v2" in content
    assert 'console.error("Nowlert API request failed"' in content
    assert "status: error.status" in content
    assert "path: error.path" in content
    assert 'message: "Test delivery failed. Check the destination configuration and logs."' in content
    assert '"#login-error, .form-error, #workspace-alert-list li, .toast.error"' in content
