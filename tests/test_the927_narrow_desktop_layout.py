"""Narrow desktop widths 1181-1399px (THE-927): Delivery history Time and
chevron, Audit log Outcome and the Backups Delete button are not clipped."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "/* THE-927 narrow desktop widths"
RANGE = "@media (min-width: 1181px) and (max-width: 1399px) {"


def _read(name: str) -> str:
    return (ROOT / "src" / "webui" / name).read_text(encoding="utf-8")


def _block(stylesheet: str, selector: str) -> str:
    start = stylesheet.index(selector)
    return stylesheet[start:stylesheet.index("}", start) + 1]


def _the927() -> str:
    css = _read("management_consistency.css")
    section = css[css.index(MARKER):]
    return section[section.index(RANGE):]


def test_narrow_range_follows_the_wider_the875_rules_it_overrides():
    css = _read("management_consistency.css")
    # Same selectors and specificity as the 1181-1500px THE-875 rules, so the
    # THE-927 block must come later in the file to win between 1181 and 1399.
    the875 = css.index("@media (min-width: 1181px) and (max-width: 1500px) {")
    audit_the875 = css.rindex("@media (min-width: 1181px) and (max-width: 1500px) {")
    assert css.index(MARKER) > the875
    assert css.index(MARKER) > audit_the875
    assert css.count(RANGE) == 1


def test_narrow_range_starts_where_the_existing_stacked_layout_ends():
    # Below 1181px the page stylesheets already stack both workbenches; the
    # THE-927 range continues that layout up to 1399px without a gap.
    for name, selector in (
        ("destination_overview_acceptance.css", "#view-deliveries .delivery-history-workbench"),
        ("page_headers.css", "#view-audit .audit-log-workbench"),
    ):
        css = _read(name)
        below = css[css.index("@media (max-width: 1180px)"):]
        assert selector in below
    assert RANGE.startswith("@media (min-width: 1181px)")


def test_delivery_and_audit_workbenches_stack_between_1181_and_1399():
    block = _the927()
    workbench = _block(block, "#view-deliveries .delivery-history-workbench,")
    assert "#view-audit .audit-log-workbench {" in workbench
    assert "grid-template-columns: minmax(0, 1fr);" in workbench

    scroll = _block(block, "#view-deliveries .delivery-history-list-scroll,")
    assert "#view-audit .audit-log-list-scroll {" in scroll
    assert "max-height: 620px;" in scroll

    detail = _block(block, "#view-deliveries .delivery-history-detail-grid {")
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in detail

    # Measured on Development (navigation expanded): side by side, the list
    # panel was 524px at 1181px and 620px at 1280px, narrower than the 708px
    # Delivery row (116 + 160 + 100 + 92 + 132 + 16, five 12px gaps, 32px
    # padding). Stacked, the list is 936px at 1181px.
    delivery_row = 116 + 160 + 100 + 92 + 132 + 16 + 5 * 12 + 32
    assert delivery_row == 708
    assert 524 < delivery_row <= 936
    assert 620 < delivery_row


def test_backup_destination_columns_fit_their_content_at_1181():
    block = _the927()
    widths = {1: 10, 2: 15, 3: 11, 4: 17, 5: 12, 6: 18, 7: 17}
    for column, width in widths.items():
        assert f".backup-destination-table th:nth-child({column}) {{ width: {width}%; }}" in block
    assert sum(widths.values()) == 100

    # Content widths measured at 1181px, where the fixed-layout table is 906px:
    # Type 82px, Status 105px, Last test 152px and Actions 145px (Test, Edit
    # and Delete buttons with their gaps and the cell padding).
    table = 906
    needs = {1: 82, 5: 105, 6: 152, 7: 145}
    for column, minimum in needs.items():
        assert table * widths[column] / 100 >= minimum


def test_filtering_actions_pin_is_untouched():
    pin = ".filtering-table th:nth-child(6) { width: 24%; }"
    assert pin in _read("filtering.css")
    assert "filtering-table" not in _the927()
