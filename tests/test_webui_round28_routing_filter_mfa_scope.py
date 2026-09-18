from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_round28_filter_values_render_one_row_per_filter_field():
    script = read("src/webui/routing_flow.js")
    style = read("src/webui/routing_flow.css")
    block = script[
        script.index("function renderFilterCard("):
        script.index("function activeFlowGraph()")
    ]

    assert "function renderFilterRuleRow(group, groupIndex)" in block
    assert 'const row = el("div", "rf-filter-rule-row");' in block
    assert "for (const [groupIndex, group] of descriptor.groups.entries())" in block
    assert "tags.append(renderFilterRuleRow(group, groupIndex));" in block
    assert "rf-filter-rule-row" in style
    assert "flex-wrap: nowrap" in style
    assert "width: 100%" in style


def test_round28_filter_title_never_falls_back_to_managed_copy():
    script = read("src/webui/routing_flow.js")
    descriptor = script[
        script.index("function filterCardDescriptor(filter)"):
        script.index("function renderFilterCard(")
    ]

    assert '"Managed"' not in descriptor
    assert '"Configured filter"' not in descriptor
    assert 'return `${label} (${group.values.length})`;' in descriptor
    assert '.join(" · ")' in descriptor


def test_round28_mfa_status_uses_real_svg_check_and_pause_icons():
    script = read("src/webui/reference_acceptance.js")
    style = read("src/webui/reference_acceptance.css")

    assert "function setReferenceMfaStatusIcon(icon, enabled)" in script
    assert 'data-mfa-glyph="check"' in script
    assert 'data-mfa-glyph="pause"' in script
    assert 'mfaIcon.textContent = enabled ? "✓" : "Ⅱ";' not in script
    assert ".reference-account-meta-mfa-icon svg" in style
    assert "height: 30px !important;" in style
    assert "width: 30px !important;" in style
