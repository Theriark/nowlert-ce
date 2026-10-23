"""Development walk fix-and-recheck round (THE-875): F2 mailbox cards and the
trivial low UI findings F3-F7."""
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


def test_f3_filtering_status_column_has_room_for_the_disabled_badge():
    # Measured on CE Development at 1440px (1185px table): the Status cell
    # grows from 106.7px to 142.2px, so the 119.3px DISABLED badge fits with
    # 7px spare and sits 23px from the SHARED chip instead of overlapping it
    # by 12.5px. Sharing keeps its original 11% (the 111.4px chip has 3.1px
    # spare) and Actions keeps the 24% that the Development live check pins.
    css = _read("filtering.css")
    widths = {1: "16%", 2: "17%", 3: "20%", 4: "12%", 5: "11%", 6: "24%"}
    for column, width in widths.items():
        assert f".filtering-table th:nth-child({column}) {{ width: {width}; }}" in css
    assert sum(int(value.rstrip("%")) for value in widths.values()) == 100


def test_f3_filtering_actions_width_matches_the_development_live_check():
    # The deploy-development job verifies the served filtering.css against this
    # exact declaration after the image is deployed; changing the Actions
    # width without that pin would fail the Development deployment.
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    pin = ".filtering-table th:nth-child(6) { width: 24%; }"
    assert f'require_contains "Filtering Actions width" "{pin}"' in workflow
    assert pin in _read("filtering.css")


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
        "grid-template-columns: minmax(116px, 0.8fr) minmax(160px, 1.5fr) "
        "minmax(100px, 0.6fr) minmax(92px, 0.6fr) minmax(132px, 0.8fr) 16px;"
    ) in columns
    # Row minimums plus five 12px gaps and 32px padding fit the 764px list
    # panel that the 1.3fr share yields at 1440px with the navigation expanded.
    assert 116 + 160 + 100 + 92 + 132 + 16 + 5 * 12 + 32 <= 764

    # The Source name wraps onto a second line instead of truncating to
    # "Email A...": the 48px icon plus the bold name need 158px on one line.
    source = _block(desktop, "#view-deliveries .delivery-history-row .delivery-history-source strong {")
    assert "white-space: normal;" in source
    assert "overflow-wrap: anywhere;" in source

    mid = css[css.index("@media (min-width: 1181px) and (max-width: 1500px) {"):]
    workbench = _block(mid, "#view-deliveries .delivery-history-workbench {")
    assert "grid-template-columns: minmax(0, 1.3fr) minmax(400px, 0.7fr);" in workbench

    # With a 400px inspector the Transport and Timeline cards stack, so their
    # values never break mid-word.
    detail_grid = _block(mid, "#view-deliveries .delivery-history-detail-grid {")
    assert "grid-template-columns: minmax(0, 1fr);" in detail_grid


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


def test_f7_buttons_use_ascii_or_inline_svg_instead_of_symbol_glyphs():
    markup = _read("index.html")
    filtering = _read("filtering.js")
    reference = _read("reference_acceptance.js")

    assert 'data-action="new-token">+ New token</button>' in markup
    assert "+ New filter</button>" in filtering
    assert 'add.textContent = "+ New token";' in reference
    assert 'button.textContent = "Check for updates";' in reference
    assert 'restart.append("Restart Nowlert");' in reference
    assert 'if (!restart.querySelector(".button-glyph")) {' in reference
    for glyph in ("＋", "⟳", "⏻"):
        assert glyph not in markup
        assert glyph not in filtering
        assert glyph not in reference
    # The Restart dialog button and the header Restart button draw the glyph
    # with an inline SVG that inherits the button colour.
    assert '<button class="button danger" value="default"><svg class="button-glyph"' in markup
    assert 'restart.insertAdjacentHTML("afterbegin", \'<svg class="button-glyph"' in reference


def test_f7_security_posture_follows_the_mfa_state():
    reference = _read("reference_acceptance.js")
    assert 'id="reference-security-posture-value"' in reference
    assert 'postureValue.textContent = enabled ? "Good" : "Fair";' in reference
    assert 'postureValue.classList.toggle("reference-good", enabled);' in reference
    assert 'postureValue.classList.toggle("reference-fair", !enabled);' in reference


def test_f7_email_alert_destructive_actions_use_the_app_confirm_dialog():
    script = _read("email_alerts.js")
    assert "window.confirm" not in script
    for title in (
        '"Delete Email Alert group"',
        '"Delete Email Alert rule"',
        '"Create Ignore rule"',
        '"Delete mailbox"',
    ):
        assert f"await confirmAction({title}," in script
    assert 'await confirmAction(\n          "Force replay",' in script
