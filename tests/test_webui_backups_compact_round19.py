from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _round19_styles() -> str:
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    marker = "/* 2026-09-18 round-19 compact backup top row. */"
    assert marker in styles
    return styles[styles.index(marker):]


def test_round19_backup_top_row_uses_natural_height_instead_of_vertical_stretch():
    final = _round19_styles()

    assert ".backup-dashboard-grid-top {" in final
    assert "align-items: start !important;" in final
    assert "#backup-schedule-panel," in final
    assert "#backup-data-tools-panel {" in final
    assert "align-self: start !important;" in final
    assert "height: auto !important;" in final
    assert "min-height: 0 !important;" in final
    assert "display: block !important;" in final


def test_round19_data_tools_cards_are_compact_and_do_not_equalize_heights():
    final = _round19_styles()

    assert "#backup-data-tools-panel > .backup-data-tools-grid {" in final
    assert "align-items: start !important;" in final
    assert "flex: 0 0 auto !important;" in final
    assert "gap: 12px !important;" in final
    assert "padding: 14px !important;" in final

    assert "#backup-data-tools-panel .data-tools-reference-card {" in final
    assert "height: auto !important;" in final
    assert "min-height: 0 !important;" in final
    assert "padding: 16px 18px !important;" in final

    assert "#backup-data-tools-panel .data-tools-reference-card > p {" in final
    assert "margin: 12px 0 14px !important;" in final
    assert "min-height: 0 !important;" in final


def test_round19_data_tools_controls_use_compact_desktop_dimensions():
    final = _round19_styles()

    assert "font-size: 16px !important;" in final
    assert "flex-basis: 48px !important;" in final
    assert "height: 48px !important;" in final
    assert "#backup-data-tools-panel .data-tools-reference-download {" in final
    assert "min-height: 42px !important;" in final
    assert "#backup-data-tools-panel .data-tools-reference-file {" in final
    assert "height: 50px !important;" in final
    assert "min-height: 50px !important;" in final
    assert 'input[type="file"]::file-selector-button' in final
    assert "height: 38px !important;" in final
    assert "#backup-data-tools-panel .data-tools-reference-preview {" in final
    assert "min-height: 42px !important;" in final
