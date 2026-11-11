"""Laptop and small-screen layout fixes stay loaded last and keep their key rules."""

import re
from pathlib import Path

from webui.service import UI_BUILD, WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def get(self, *_keys, default=None):
        return default


def test_laptop_layout_stylesheet_is_served_and_loaded_after_every_other_stylesheet():
    service = WebUIService(Configuration(), root=ROOT)

    page = service.response("/")
    assert page is not None and page.status == 200
    body = page.body.decode("utf-8")
    link = f'<link rel="stylesheet" href="/ui/laptop_layout.css?v={UI_BUILD}">'
    assert link in body
    stylesheets = re.findall(r'<link rel="stylesheet" href="([^"]+)"', body)
    assert stylesheets[-1] == f"/ui/laptop_layout.css?v={UI_BUILD}"

    stylesheet = service.response("/ui/laptop_layout.css")
    assert stylesheet is not None and stylesheet.status == 200
    assert stylesheet.content_type == "text/css; charset=utf-8"


def test_laptop_layout_keeps_navigation_actions_and_dialog_buttons_reachable():
    css = (ROOT / "src/webui/laptop_layout.css").read_text(encoding="utf-8")
    compact = re.sub(r"\s+", " ", css)

    # Short screens: the menu scrolls and the profile menu below it stays visible.
    assert ".sidebar > #primary-nav { flex: 1 1 auto !important; min-height: 0 !important; overflow-y: auto !important;" in compact
    assert ".sidebar > .sidebar-footer { flex: 0 0 auto !important; }" in compact
    # Wide tables keep their Actions column on screen.
    assert "table.email-rules-table" in compact and ":is(th, td):last-child" in compact
    assert "position: sticky !important; right: 0 !important;" in compact
    # Tall dialogs keep Save/Cancel visible while the form scrolls.
    assert "form > .modal-actions" in compact and "position: sticky !important; bottom:" in compact
