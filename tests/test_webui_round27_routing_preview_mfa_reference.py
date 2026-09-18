from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_round27_routing_filter_uses_active_destination_policy_values():
    script = read("src/webui/routing_flow.js")
    block = script[
        script.index("function filterCardDescriptor(filter)"):
        script.index("function renderFilterCard(", script.index("function filterCardDescriptor(filter)"))
    ]

    assert 'Object.prototype.hasOwnProperty.call(policy, "filter_enabled")' in block
    assert "? policy.filter_enabled" in block
    assert 'return !policy.restricted && policy.configured && enabled !== false;' in block
    assert 'return `${label} (${group.values.length})`;' in block
    assert '.join(" · ")' in block
    assert '"Managed"' not in block
    assert 'groups: items' in block


def test_round27_filter_sources_fill_available_footer_width_before_plus_n():
    script = read("src/webui/routing_flow.js")
    style = read("src/webui/routing_flow.css")
    card = script[
        script.index("function renderFilterCard("):
        script.index("function activeFlowGraph()")
    ]

    assert "FILTER_SOURCE_LIMIT" not in script
    assert "const fitCollapsedSources = () => {" in card
    assert "const width = sourceSummary.clientWidth;" in card
    assert 'sourceNode.dataset.filterSource = "1";' in card
    assert 'toggle.textContent = `+${hidden}`;' in card
    assert 'sourceSummary.classList.toggle("is-expanded", sourcesExpanded);' in card

    round27 = style[
        style.index("/* 2026-09-18 round-27 filter semantics and full-width source fitting. */"):
    ]
    assert "width: 100% !important;" in round27
    assert ".rf-filter-card-sources:not(.is-expanded)" in round27
    assert ".rf-filter-card-sources.is-expanded" in round27


def test_round27_import_preview_scrolls_every_issue_instead_of_truncating_to_eight():
    app = read("src/webui/app.js")
    style = read("src/webui/reference_acceptance.css")
    block = app[
        app.index("function renderImportIssues(preview)"):
        app.index("function renderImportPreview(preview)")
    ]

    assert "visible.slice(0, 8)" not in block
    assert "for (const [index, issue] of visible.entries())" in block
    assert "list.scrollTop = 0;" in block
    assert "more.hidden = true;" in block
    assert "overflow-y: auto !important;" in style
    assert "scrollbar-gutter: stable;" in style


def test_round27_mfa_status_card_matches_enabled_disabled_reference_states():
    script = read("src/webui/reference_acceptance.js")
    style = read("src/webui/reference_acceptance.css")

    assert 'icon.classList.add("reference-account-meta-mfa-icon");' in script
    assert 'reference-mfa-action' not in script
    assert 'mfaIcon.textContent = enabled ? "✓" : "Ⅱ";' in script
    assert 'Manage multi-factor authentication. Current status:' in script

    round27 = style[
        style.index("/* 2026-09-18 round-27 full issue scrolling and approved MFA status/disable references. */"):
    ]
    assert "border: 2px solid rgba(237, 185, 34, 0.9) !important;" in round27
    assert ".reference-account-meta-mfa.is-enabled .reference-account-meta-icon" in round27
    assert ".reference-account-meta-mfa.is-disabled .reference-account-meta-icon" in round27
    assert "color: #24e2a0 !important;" in round27
    assert "color: #ff6868 !important;" in round27


def test_round27_disable_mfa_dialog_is_the_confirmation_surface():
    markup = read("src/webui/index.html")
    app = read("src/webui/app.js")
    style = read("src/webui/reference_acceptance.css")

    assert 'id="mfa-dialog-summary"' in markup
    assert 'id="mfa-dialog-detail"' in markup
    assert "mfa-reference-disable-summary" in markup
    assert "mfa-reference-disable-icon" in markup
    assert "mfa-reference-disable-form" in markup
    assert "mfa-reference-disable-submit" in markup
    assert 'placeholder="000000"' not in markup[
        markup.index('id="mfa-disable-panel"'):
        markup.index('id="integration-settings-dialog"')
    ]

    block = app[
        app.index("async function openMfaDialog()"):
        app.index("function closeMfaDialog()")
    ]
    assert "confirmAction(" not in block
    assert 'dialog.classList.toggle("is-disable-mode", enabled);' in block
    assert '"Confirm your current password and authenticator code to disable MFA."' in block
    assert "detail.hidden = enabled;" in block

    round27 = style[
        style.index("/* 2026-09-18 round-27 full issue scrolling and approved MFA status/disable references. */"):
    ]
    assert ".reference-mfa-dialog.is-disable-mode" in round27
    assert "max-width: min(1000px, calc(100vw - 32px)) !important;" in round27
    assert ".mfa-reference-disable-summary" in round27
    assert ".mfa-reference-disable-submit" in round27
