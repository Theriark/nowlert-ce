"""Regression coverage for Filtering editor navigation and state handling."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_filtering_editor_uses_native_save_flow_for_every_integration():
    script = (ROOT / "src" / "webui" / "policy_simplification.js").read_text(
        encoding="utf-8"
    )

    assert "async function saveDellFilter" not in script
    assert 'button[data-filter-action="save-integration"]' not in script
    assert "const oldRequest = request;" in script
    assert 'rules: { policy },' in script
    assert "return oldRequest(path, transformed);" in script


def test_filtering_editor_close_matches_cancel_and_preserves_list_position():
    script = (ROOT / "src" / "webui" / "policy_simplification.js").read_text(
        encoding="utf-8"
    )

    assert "let integrationListScrollTop = 0;" in script
    assert "new MutationObserver(restoreIntegrationScroll)" in script
    assert 'button.classList.contains("icon-button")' in script
    assert 'button[data-filter-action="back-integrations"]' in script
    assert "cancelButton.click();" in script


def test_filtering_editor_enable_state_follows_user_intent():
    script = (ROOT / "src" / "webui" / "policy_simplification.js").read_text(
        encoding="utf-8"
    )

    assert "const expectedEnabled = Boolean(listToggle?.checked);" in script
    assert "editorToggle.checked = expectedEnabled;" in script
    assert "if (editorToggle) editorToggle.checked = true;" in script
    assert 'const source = toggle.dataset.filterToggle || "";' in script
