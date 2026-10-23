"""Development walk fix-and-recheck round (THE-875): F2 mailbox cards and the
trivial low UI findings F3-F6. The F7 script fixes (symbol glyphs, security
posture, confirm dialog) follow in the same pull request."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER_MARKER = "/* THE-875 Development walk fixes"


def _read(name: str) -> str:
    return (ROOT / "src" / "webui" / name).read_text(encoding="utf-8")


def _block(stylesheet: str, selector: str) -> str:
    start = stylesheet.index(selector)
    return stylesheet[start:stylesheet.index("}", start) + 1]


def _layer() -> str:
    css = _read("management_consistency.css")
    return css[css.index(LAYER_MARKER):]


def test_consistency_layer_loads_after_the_page_stylesheets_it_overrides():
    service = _read("service.py")
    for earlier in ("email_alerts.css", "qa_patch.css", "audit_log_refinement.css"):
        assert service.rfind("management_consistency.css") > service.rfind(earlier)


def test_f2_mailbox_cards_size_to_the_available_width_instead_of_four_fixed_columns():
    grid = _block(_layer(), ".email-card-grid.email-mailboxes-grid {")
    assert "grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));" in grid


def test_f2_mailbox_action_row_and_heading_never_overflow_the_card():
    layer = _layer()

    actions = _block(layer, ".email-mailbox-card-actions {")
    assert "flex-wrap: wrap;" in actions

    buttons = _block(layer, ".email-mailbox-card-actions .button {")
    assert "flex: 1 1 auto;" in buttons

    heading = _block(layer, ".email-mailbox-card-heading {")
    assert "min-width: 0;" in heading
    assert "flex-wrap: wrap;" in heading

    identity = _block(layer, ".email-mailbox-card-identity {")
    assert "grid-template-columns: minmax(0, 1fr);" in identity

    wrap = _block(layer, ".email-mailbox-card-identity h3,")
    assert ".email-mailbox-card .email-safe-error" in wrap
    assert "overflow-wrap: anywhere;" in wrap


def test_f3_filtering_status_and_sharing_columns_have_room_for_the_disabled_badge():
    css = _read("filtering.css")
    widths = {1: "16%", 2: "17%", 3: "20%", 4: "12%", 5: "12%", 6: "23%"}
    for column, width in widths.items():
        assert f".filtering-table th:nth-child({column}) {{ width: {width}; }}" in css
    assert sum(int(value.rstrip("%")) for value in widths.values()) == 100


def test_f3_backup_destination_actions_and_last_test_columns_fit_their_content():
    layer = _layer()
    widths = {2: "20%", 3: "13%", 4: "22%", 5: "10%", 6: "14%", 7: "14%"}
    for column, width in widths.items():
        assert f".backup-destination-table th:nth-child({column}) {{ width: {width}; }}" in layer
    # The Type column keeps the 7% declared in qa_patch.css.
    assert ".backup-destination-table th:nth-child(1) { width: 7%; }" in _read("qa_patch.css")
    assert ".backup-destination-table th:nth-child(1)" not in layer
    assert 7 + sum(int(value.rstrip("%")) for value in widths.values()) == 100


def test_f4_delivery_history_list_keeps_source_and_time_readable_at_1440():
    css = _read("management_consistency.css")
    desktop = css[css.index("@media (min-width: 821px) {"):]
    columns = _block(desktop, "#view-deliveries .delivery-history-columns,")
    assert (
        "grid-template-columns: minmax(138px, 0.8fr) minmax(170px, 1.5fr) "
        "minmax(106px, 0.6fr) minmax(92px, 0.6fr) minmax(118px, 0.8fr) 16px;"
    ) in columns

    mid = css[css.index("@media (min-width: 1181px) and (max-width: 1500px) {"):]
    workbench = _block(mid, "#view-deliveries .delivery-history-workbench {")
    assert "grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.65fr);" in workbench


def test_f5_audit_log_outcome_column_is_not_clipped_at_1440():
    layer = _layer()
    mid = layer[layer.index("@media (min-width: 1181px) and (max-width: 1500px) {"):]
    workbench = _block(mid, "#view-audit .audit-log-workbench {")
    assert "grid-template-columns: minmax(0, 1.3fr) minmax(400px, 0.7fr);" in workbench

    # The effective desktop column minimums come from the last audit list rule
    # in audit_log_refinement.css; with four 10px gaps and 28px padding they
    # fit the 744px list panel that the 1.3fr share yields at 1440px.
    audit = _read("audit_log_refinement.css")
    final_rule = audit[audit.rindex("#view-audit .audit-log-columns,\n#view-audit .audit-log-row {\n  gap: 10px !important;"):]
    for minimum in ("minmax(104px, 0.78fr)", "minmax(170px, 1.28fr)", "minmax(136px, 1fr)", "minmax(78px, 0.58fr)"):
        assert minimum in final_rule
    assert 104 + 170 + 104 + 136 + 78 + 4 * 10 + 28 <= 744


def test_f6_update_status_copy_matches_the_check_result():
    script = _read("enhancements.js")
    message = script[script.index("function updateStatusMessage(version) {"):]
    message = message[: message.index("\n  }") + 4]
    assert "if (version.check_error) {" in message
    assert "could not be completed" in message
    assert "if (version.update_available) {" in message
    assert "if (!version.available) {" in message
    assert "No newer version is advertised" in message
    assert "Nowlert is up to date with the advertised version." in message

    render = script[script.index("renderUpdates = function enhancedRenderUpdates() {"):]
    render = render[: render.index("\n  };") + 5]
    assert "originalRenderUpdates();" in render
    assert 'if (status) status.textContent = updateStatusMessage(state.versionStatus || {});' in render
    assert "updateCheckMetadata();" in render


def test_f6_housekeeping_heading_matches_sibling_section_titles():
    heading = _block(_layer(), ".housekeeping-page-heading h2 {")
    assert "font-size: 1.08rem;" in heading
    assert "clamp(" not in heading


def test_f7_button_glyph_and_fair_posture_styles_exist_for_the_script_fixes():
    layer = _layer()
    glyph = _block(layer, ".button .button-glyph {")
    assert "stroke: currentColor;" in glyph
    assert "height: 1em;" in glyph
    assert ".reference-fair { color: #f4c542; }" in layer
