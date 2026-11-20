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
    # A short menu (normal users) must not stretch its items to fill the sidebar.
    assert "align-content: start !important; grid-auto-rows: min-content !important;" in compact
    # Wide tables keep their Actions column on screen.
    assert "table.email-rules-table" in compact and ":is(th, td):last-child" in compact
    assert "position: sticky !important; right: 0 !important;" in compact
    # Pinned cells stay opaque even where a table paints its headers transparent.
    assert "#view-filtering#view-filtering .filtering-table-panel .filtering-table :is(th, td):last-child" in compact
    # Tall dialogs keep Save/Cancel visible while the form scrolls.
    assert "form > .modal-actions" in compact and "position: sticky !important; bottom:" in compact


def test_email_rule_cards_are_not_pinned_or_narrowed_below_900px():
    css = (ROOT / "src/webui/laptop_layout.css").read_text(encoding="utf-8")
    compact = " ".join(css.split())
    # Below 900px the rules are stacked cards: the table-only rules must not apply there.
    assert "@media (min-width: 901px) and (max-width: 1440px) { table.email-rules-table { min-width: 0 !important; }" in compact
    assert "@media (max-width: 900px) { table.email-rules-table :is(th, td):last-child { position: static !important;" in compact


def test_filtering_dialog_pins_its_heading_and_footer_while_the_step_body_scrolls():
    """NCE-127 F1: the View/New filter dialog is not a form, so the generic sticky
    footer rule misses it. The open dialog becomes a column: heading pinned, the
    visible step scrolls, and the step footer (Close / Cancel / Save) sticks to
    the bottom of that scrolling step."""
    css = (ROOT / "src/webui/laptop_layout.css").read_text(encoding="utf-8")
    compact = " ".join(css.split())

    # Only the open dialog is a flex column: a closed <dialog> must stay display: none.
    assert "#filtering-dialog[open] { display: flex !important; flex-direction: column !important; overflow: hidden !important;" in compact
    assert "#filtering-dialog > .modal-heading { flex: 0 0 auto !important;" in compact
    # The step body is the only scroll container.
    assert "#filtering-dialog > section { flex: 1 1 auto !important; min-height: 0 !important; overflow-y: auto !important;" in compact
    # The step footer sticks to the bottom of the scrolling step, with an opaque background.
    assert "#filtering-dialog > section > .modal-actions { position: sticky !important; bottom: 0 !important;" in compact
    footer = compact[compact.index("#filtering-dialog > section > .modal-actions {"):]
    footer = footer[: footer.index("}")]
    assert "background:" in footer and "z-index:" in footer


def test_dashboard_kpi_delta_badge_wraps_inside_its_card_instead_of_being_clipped():
    """NCE-127 F2: at 1280 wide the Failures "vs. previous window" badge was wider
    than its grid column and the card (overflow: hidden) cut it to "windo". The
    badge is capped at the column width and its items and text may wrap."""
    css = (ROOT / "src/webui/laptop_layout.css").read_text(encoding="utf-8")
    compact = " ".join(css.split())

    badge = compact[compact.index(".ops-kpi-card > .ops-kpi-delta {"):]
    badge = badge[: badge.index("}")]
    assert "max-width: 100% !important;" in badge
    assert "min-width: 0 !important;" in badge
    assert "margin-left: 0 !important;" in badge
    assert "box-sizing: border-box" in badge
    # A wrapping flex container sizes itself to its widest part and broke the note at 1366.
    assert "flex-wrap" not in badge
    assert ".ops-kpi-card > .ops-kpi-delta > small { white-space: normal !important;" in compact
    # Between 1181 and 1450 px (five cards per row) the note stacks under the value.
    assert "@media (min-width: 1181px) and (max-width: 1450px) { .ops-kpi-card > .ops-kpi-delta { flex-direction: column !important; align-items: flex-start !important;" in compact


def test_phone_menu_gets_the_sidebar_styles_that_only_desktop_media_queries_gave_it():
    """NCE-127: at 390 px the open menu let the page show through, drew the icons filled black, put the owl in a grey
    outset button and showed both "COMMUNITY EDITION" and "CE"."""
    css = (ROOT / "src/webui/laptop_layout.css").read_text(encoding="utf-8")
    compact = re.sub(r"\s+", " ", css)
    phone = compact[compact.index("@media (max-width: 760px) {"):]
    phone = phone[: phone.index("} }") + 3]

    assert ".sidebar { background: rgb(12, 15, 18) !important; }" in phone
    assert ".sidebar > .brand.sidebar-brand > .sidebar-owl-button { background: transparent !important; border: 0 !important;" in phone
    assert ".sidebar .nav-icon svg { fill: none !important; stroke: currentColor !important;" in phone
    assert ".sidebar > .brand.sidebar-brand > .sidebar-edition-collapsed { display: none !important; }" in phone
    # The desktop rules these copy are still desktop-only, which is why the phone block is needed.
    styles = re.sub(r"\s+", " ", (ROOT / "src/webui/styles.css").read_text(encoding="utf-8"))
    assert re.search(r"@media \(min-width: 761px\) \{[^@]*\.nav-icon svg \{[^}]*fill: none", styles)
