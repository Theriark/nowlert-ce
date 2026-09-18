from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_round25_filter_editor_selection_means_filter_out():
    filtering = read("src/webui/filtering.js")
    system = read("src/storage/system_filtering.py")
    base = read("src/storage/filtering.py")

    assert "input.checked = current.has(String(value).toLowerCase());" in filtering
    assert "if (selected.length > 0) rules[field.key] = selected;" in filtering
    assert 'action: "block", conditions' in filtering
    assert "{ method: \"PUT\", body: { rules: policy, enabled } }" in filtering

    assert '"action": "block"' in system
    assert "collapse_full_enum=False" in system
    assert 'collapse_full_enum=action != "block"' in system
    assert "collapse_full_enum: bool = True" in base


def test_round25_routing_flow_has_one_card_per_filtering_record():
    api = read("src/api/routing_flow.py")
    script = read("src/webui/routing_flow.js")

    assert 'destination_filter_id = (' in api
    assert 'f"{destination.id}:filter"' in api
    assert '"sources": filter_sources' in api
    assert '"route_ids": filter_route_ids' in api
    assert '"policies": filter_policies' in api
    assert '"filters": filters' in api

    assert "const filters = (data.filters || [])" in script
    assert "for (const filter of current.filters)" in script
    assert "renderFilterCard(node, filter, routes, destination);" in script
    assert "filter.route_ids" in script
    assert "current.links.filter(link => activePolicies(link).length)" not in script


def test_round25_filter_card_overflow_and_destination_alignment_are_interactive():
    script = read("src/webui/routing_flow.js")
    style = read("src/webui/routing_flow.css")

    assert "rf-filter-overflow-button" in script
    assert "rf-filter-source-overflow" in script
    assert "toggle.addEventListener(\"click\"" in script
    assert 'toggle.setAttribute("aria-expanded", String(tagsExpanded));' in script
    assert 'toggle.setAttribute("aria-expanded", String(sourcesExpanded));' in script
    assert "FILTER_SOURCE_LIMIT" in script

    marker = "/* 2026-09-18 round-25 individual filter cards and expandable summaries. */"
    assert marker in style
    final = style[style.index(marker):]
    assert "grid-template-columns: minmax(0, 1fr) max-content !important;" in final
    assert "justify-self: end !important;" in final
    assert "text-align: right !important;" in final
    assert "flex-wrap: nowrap !important;" in final
    assert ".rf-filter-source-overflow" in final


def test_round25_mfa_matches_reference_and_uses_six_digit_entry():
    markup = read("src/webui/index.html")
    app = read("src/webui/app.js")
    style = read("src/webui/reference_acceptance.css")

    assert "Set up an authenticator app to add an extra layer of security" in markup
    assert ">Scan QR code<" in markup
    assert ">Use setup key<" in markup
    assert ">Enter authenticator code<" in markup
    assert markup.count('class="mfa-code-digit"') == 6
    assert 'id="mfa-enable-code" type="hidden"' in markup

    assert "function mfaDigitInputs()" in app
    assert "function syncMfaCodeDigits()" in app
    assert "function handleMfaDigitPaste(event)" in app
    assert 'if (!/^\\d{6}$/.test(code))' in app
    assert '"Disable multi-factor authentication?"' in app
    assert "await confirmAction(" in app

    assert ".mfa-reference-methods" in style
    assert ".mfa-reference-code-digits" in style
    assert ".mfa-reference-enable" in style


def test_round25_profile_mfa_card_is_the_click_target():
    script = read("src/webui/reference_acceptance.js")
    style = read("src/webui/reference_acceptance.css")

    assert 'ref(kind === "mfa" ? "button" : "div"' in script
    assert 'item.dataset.action = "account-mfa";' in script
    assert 'const action = ref("span", "reference-mfa-action", "Enable MFA");' in script
    assert 'enabled ? "Disable MFA" : "Enable MFA"' in script
    assert 'enabled ? "Disable multi-factor authentication" : "Enable multi-factor authentication"' in script
    assert ".reference-account-meta-mfa {" in style
    assert "cursor: pointer;" in style


def test_round25_dell_special_filter_stays_block_based():
    script = read("src/webui/policy_simplification.js")

    assert "function regularDellBlockRules(integration)" in script
    assert "function hydrateDellBlockRule(integration)" in script
    assert 'rule.action === "block"' in script
    assert 'input.checked = selected.has(normalized(input.value));' in script
    assert '? [{ action: "block", conditions: nativeRules }]' in script
