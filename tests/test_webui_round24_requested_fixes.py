from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_round24_routing_flow_animates_filtered_and_delivered_branches():
    script = read("src/webui/routing_flow.js")
    storage = read("src/storage/routing_flow.py")

    assert '"outcome": "filtered"' in storage
    assert 'f"filtered:{row[\'id\']}"' in storage
    assert "recent_filtered = connection.execute(" in storage
    assert 'const filtered = item.outcome === "filtered";' in script
    assert "p.filtered && paths.length > 1 ? paths.slice(0, 1) : paths" in script
    assert "rf-filtered-particle" in script


def test_round24_filter_card_uses_real_filter_fields_counts_and_source_icons():
    script = read("src/webui/routing_flow.js")
    api = read("src/api/routing_flow.py")

    assert '"filter_sources": filter_sources' in api
    assert '"filter_policies": filter_policies' in api
    assert "policy.policy_rules" in script
    assert "group.values.length" in script
    assert "Applied to active route" not in script
    assert "All notifications" not in script[script.index("function filterCardDescriptor(link)"):script.index("function activeFlowGraph()")]
    assert "for (const source of sourceKeys) sourceSummary.append(sourceIcon(source));" in script
    assert 'el("span", "", route.integration_name)' not in script[script.index("function renderFilterCard"):script.index("function activeFlowGraph()")]


def test_round24_delivery_detail_does_not_stretch_one_row_tags_downward():
    style = read("src/webui/destination_overview_acceptance.css")
    marker = "/* 2026-09-18 round-24 compact one-row delivery detail alignment. */"
    assert marker in style
    final = style[style.index(marker):]
    assert "align-content: start;" in final
    assert "grid-auto-rows: max-content;" in final


def test_round24_security_profile_avatar_mfa_and_new_token_match_request():
    markup = read("src/webui/index.html")
    app = read("src/webui/app.js")
    script = read("src/webui/reference_acceptance.js")
    style = read("src/webui/reference_acceptance.css")

    assert "<h2>Profile</h2>" in script
    assert "Profile & access" not in script
    assert "justify-self: end !important;" in style
    assert 'id="mfa-qr-code"' in markup
    assert 'qr.src = response.qr_code || "";' in app
    assert "mfa-setup-grid" in style
    assert 'data-action="new-token">＋ New token</button>' in markup
    assert 'add.textContent = "＋ New token";' in script


def test_round24_import_preview_matches_reference_and_is_wired_to_preview_data():
    markup = read("src/webui/index.html")
    app = read("src/webui/app.js")
    style = read("src/webui/reference_acceptance.css")

    for identity in (
        "import-metric-fingerprint",
        "import-metric-valid",
        "import-metric-errors",
        "import-metric-warnings",
        "import-metric-destinations",
        "import-metric-routes",
        "import-issue-count",
        "import-issue-filter",
        "import-issue-list",
        "import-copy-preview",
    ):
        assert f'id="{identity}"' in markup
    assert "CONFIGURATION PREVIEW" in markup
    assert "All issues" in markup
    assert "function renderImportPreview(preview)" in app
    assert "function renderImportIssues(preview)" in app
    assert "renderImportPreview(response.preview);" in app
    assert 'byId("import-apply").disabled = !response.preview.valid;' in app
    assert 'byId("import-issue-filter")?.addEventListener("change"' in app
    assert 'byId("import-copy-preview")?.addEventListener("click", copyImportPreview);' in app
    assert ".reference-import-metrics" in style
    assert ".reference-import-workbench" in style
    assert ".reference-import-issue" in style


def test_round24_mfa_qr_is_generated_from_backend_provisioning_uri():
    platform = read("src/api/platform.py")
    mfa = read("src/storage/mfa.py")
    requirements = read("requirements.txt")

    assert "provisioning_qr_data_uri" in platform
    assert '"qr_code": provisioning_qr_data_uri(uri)' in platform
    assert "def provisioning_qr_data_uri(uri: str)" in mfa
    assert "qrcode.image.svg.SvgPathImage" in mfa
    assert "qrcode==8.2" in requirements
