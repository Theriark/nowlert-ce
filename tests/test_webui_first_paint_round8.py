from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_round8_cache_hydrates_before_requested_view_navigation():
    script = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    assert "function qaHydrateWorkspaceCache(session, { render = true } = {})" in script
    start = script.index("showApp = function showAppWithWorkspaceCache")
    end = script.index("const qaOriginalExpireSession", start)
    block = script[start:end]
    hydrate = "qaHydrateWorkspaceCache(session, { render: false })"
    assert hydrate in block
    assert block.index(hydrate) < block.index("qaOriginalShowApp(session)")
    assert block.index("qaOriginalShowApp(session)") < block.index("if (hydrated) renderAll();")


def test_round8_reference_layout_is_synchronized_before_first_paint():
    script = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")

    nav_start = script.index("navigateWithReferenceAcceptance")
    nav = script[nav_start:script.index("return result", nav_start)]
    show_start = script.index("showAppWithReferenceAcceptance")
    show = script[show_start:script.index("return result", show_start)]
    assert "syncAll();" in nav
    assert nav.index("syncAll();") < nav.index("scheduleSync();")
    assert "syncAll();" in show
    assert show.index("syncAll();") < show.index("scheduleSync();")


def test_round8_management_polish_is_synchronized_before_first_paint():
    script = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")

    nav_start = script.index("navigateWithManagementConsistency")
    nav = script[nav_start:script.index("return result", nav_start)]
    show_start = script.index("showAppWithManagementConsistency")
    show = script[show_start:script.index("return result", show_start)]
    assert "syncConsistency();" in nav
    assert nav.index("syncConsistency();") < nav.index("scheduleSync();")
    assert "syncConsistency();" in show
    assert show.index("syncConsistency();") < show.index("scheduleSync();")


def test_round8_security_token_actions_are_right_aligned():
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    marker = "/* 2026-09-18 round-seven first-paint and Security token acceptance. */"
    token_styles = styles[styles.index(marker):]
    assert ".reference-api-tokens th:last-child" in token_styles
    assert ".reference-api-tokens td:last-child" in token_styles
    assert "text-align: right !important;" in token_styles
    assert "justify-content: flex-end !important;" in token_styles
