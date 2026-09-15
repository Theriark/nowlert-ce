"""Regression coverage for route-row selection styling."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "src" / "webui" / "destination_editor_fix.css"


def test_checked_route_row_keeps_neutral_resting_style():
    stylesheet = STYLE.read_text(encoding="utf-8")
    match = re.search(
        r"\.route-assignment-option:has\(input:checked\)\s*\{(?P<body>[^}]*)\}",
        stylesheet,
    )

    assert match is not None
    body = match.group("body")
    assert "background: rgba(255, 255, 255, 0.018);" in body
    assert "border-color: var(--destination-border);" in body
    assert "rgba(244, 197, 66" not in body


def test_route_row_hover_keeps_neutral_row_chrome():
    stylesheet = STYLE.read_text(encoding="utf-8")
    match = re.search(
        r"\.destination-editor-dialog \.route-assignment-option:hover\s*\{(?P<body>[^}]*)\}",
        stylesheet,
    )

    assert match is not None
    body = match.group("body")
    assert "border-color: var(--destination-border);" in body
    assert "box-shadow: none;" in body
    assert "rgba(244, 197, 66" not in body


def test_route_checkbox_pointer_focus_does_not_keep_amber_halo():
    stylesheet = STYLE.read_text(encoding="utf-8")
    match = re.search(
        r'\.destination-editor-dialog \.route-assignment-option input\[type="checkbox"\]:focus:not\(:focus-visible\)\s*\{(?P<body>[^}]*)\}',
        stylesheet,
    )

    assert match is not None
    body = match.group("body")
    assert "border-color: var(--destination-border);" in body
    assert "box-shadow: none;" in body
    assert "rgba(244, 197, 66" not in body


def test_route_checkbox_hover_does_not_reintroduce_amber_border():
    stylesheet = STYLE.read_text(encoding="utf-8")
    match = re.search(
        r'\.destination-editor-dialog \.route-assignment-option input\[type="checkbox"\]:hover\s*\{(?P<body>[^}]*)\}',
        stylesheet,
    )

    assert match is not None
    body = match.group("body")
    assert "border-color: var(--destination-border);" in body
    assert "rgba(244, 197, 66" not in body
