from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "src" / "webui" / "qa_patch.js"
INDEX = ROOT / "src" / "webui" / "index.html"


def test_nce_21_complete_route_filters_render_as_all_events() -> None:
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
    assert content.count("qaNormalizeDeliveryBadges();") >= 2


def test_nce_25_user_errors_hide_http_status_and_api_path() -> None:
    content = PATCH.read_text(encoding="utf-8")

    assert "function qaSanitizeApiError(error)" in content
    assert 'details.push(`HTTP ${error.status}`);' in content
    assert 'details.push(`${API}${error.path}`);' in content
    assert "error.message = error.message.slice(0, -suffix.length)" in content
    assert 'console.error("Nowlert API request failed"' in content
    assert 'message: "Test delivery failed. Check the destination configuration and logs."' in content


def test_qa_patch_loads_after_main_webui_script() -> None:
    content = INDEX.read_text(encoding="utf-8")

    assert content.index('<script src="/ui/app.js" defer></script>') < content.index(
        '<script src="/ui/qa_patch.js" defer></script>'
    )
