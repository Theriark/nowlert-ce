"""Backups bottom row (THE-942): the Recovery snapshots and Stored copies
tables no longer hide Restore and Delete inside a horizontal scroller at
desktop widths. Companion to tests/test_the927_narrow_desktop_layout.py."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = "/* THE-942 Backups bottom row"
STACK_RANGE = "@media (min-width: 1181px) and (max-width: 1599px) {"
ROW_RANGE = "@media (min-width: 1600px) {"
TABLES = (".backup-recovery-table", ".backup-stored-table")


def _read(name: str) -> str:
    return (ROOT / "src" / "webui" / name).read_text(encoding="utf-8")


def _the942() -> str:
    css = _read("management_consistency.css")
    return css[css.index(MARKER):]


def _block(stylesheet: str, selector: str) -> str:
    start = stylesheet.index(selector)
    return stylesheet[start:stylesheet.index("}", start) + 1]


def test_block_is_the_last_layer_after_the927_and_contains_both_ranges():
    css = _read("management_consistency.css")
    assert css.index(MARKER) > css.index("/* THE-927 narrow desktop widths")
    block = _the942()
    assert block.count(STACK_RANGE) == 1
    assert block.count(ROW_RANGE) == 1
    assert block.index(STACK_RANGE) < block.index(ROW_RANGE)


def test_every_table_has_the_760px_floor_the_fix_removes():
    # styles.css gives every table a 760px minimum; qa_patch.css keeps the
    # bottom row side by side from 901px with an !important two-column grid.
    assert "table {\n  border-collapse: collapse;\n  min-width: 760px;" in _read("styles.css")
    qa = _read("qa_patch.css")
    assert ".backup-dashboard-grid-bottom {\n    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;" in qa
    assert ".backup-dashboard-panel table {\n  font-size: 11px;\n  table-layout: fixed;" in qa


def test_bottom_row_stacks_between_1181_and_1599():
    block = _the942()
    stack = block[block.index(STACK_RANGE):block.index(ROW_RANGE)]
    grid = _block(stack, "#view-backups .backup-dashboard-grid-bottom {")
    # Same !important as the qa_patch.css rule it overrides, id-scoped and in
    # a later stylesheet, so it wins; visual_refinement.css only touches the
    # grid below 1181px.
    assert "grid-template-columns: minmax(0, 1fr) !important;" in grid
    assert "backup-recovery-table" not in stack
    assert "backup-stored-table" not in stack
    # Measured on Development: the half panel scroller is 430px at 1181px and
    # 585px at 1500px for a 760px table; stacked, the table is 904px at 1181px.
    assert 904 >= 760 > 585 > 430


def test_tables_fit_their_half_panel_from_1600():
    block = _the942()
    row = block[block.index(ROW_RANGE):]
    floor = _block(row, "#view-backups .backup-recovery-table,")
    assert "#view-backups .backup-stored-table {" in floor
    assert "min-width: 0;" in floor
    # The fixed layout and its ellipsis cells stay; only the floor goes.
    assert "table-layout" not in row

    recovery = {1: 25, 2: 18, 3: 21, 4: 13, 5: 23}
    stored = {1: 25, 2: 24, 3: 18, 4: 13, 5: 20}
    for table, shares in ((".backup-recovery-table", recovery), (".backup-stored-table", stored)):
        for column, share in shares.items():
            assert f"#view-backups {table} th:nth-child({column}) {{ width: {share}%; }}" in row
        assert sum(shares.values()) == 100

    # Cell needs measured on Development at the 12.8px cell font with a 633px
    # scroller at 1600px: Date & time 155px, Type 108px (SCHEDULED badge),
    # Size 80px, Restore + icon-only Delete 142px, Restore alone 102px, the
    # Full snapshot title 101px.
    scroller = 633
    needs_recovery = {1: 155, 2: 108, 3: 101, 4: 80, 5: 142}
    needs_stored = {1: 155, 3: 108, 4: 80, 5: 102}
    for column, minimum in needs_recovery.items():
        assert scroller * recovery[column] / 100 >= minimum
    for column, minimum in needs_stored.items():
        assert scroller * stored[column] / 100 >= minimum


def test_cells_do_not_wrap_and_delete_is_icon_only_from_1600():
    row = _the942()[_the942().index(ROW_RANGE):]
    cells = _block(row, "#view-backups .backup-recovery-table td,")
    assert "#view-backups .backup-stored-table td {" in cells
    assert "white-space: nowrap;" in cells

    delete = "#view-backups .backup-recovery-table .backup-table-action[data-action=\"delete-backup\"]"
    button = _block(row, delete + " {")
    assert "width: 34px;" in button and "min-width: 34px;" in button
    assert "padding: 5px !important;" in button
    label = _block(row, delete + " > span {")
    assert "display: none;" in label
    # Same geometry as the icon-only Edit and Delete of the destinations table.
    icon_only = _block(_read("qa_patch.css"), ".backup-table-action.icon-only {")
    assert "min-width: 34px;" in icon_only and "width: 34px;" in icon_only
    # The button keeps its accessible name: app.js sets title and aria-label.
    app = _read("app.js")
    assert "title: label," in app and "\"aria-label\": label" in app
    assert "backupIconAction(\"delete-backup\", item.id, \"Delete\", \"trash\", \"danger\")" in app


def test_destinations_table_narrow_widths_and_filtering_pin_are_untouched():
    block = _the942()
    assert "backup-destination-table" not in block
    assert "filtering-table" not in block
    assert ".filtering-table th:nth-child(6) { width: 24%; }" in _read("filtering.css")
    # Below 1181px visual_refinement.css keeps its contained scroll.
    narrow = _read("visual_refinement.css")
    narrow = narrow[narrow.index("@media (max-width: 1180px)"):]
    assert "#view-backups .backup-recovery-table,\n  #view-backups .backup-stored-table {\n    min-width: 760px !important;" in narrow
    assert "max-width: 1180px" not in block and "max-width: 900px" not in block
