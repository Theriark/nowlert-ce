from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_delivery_history_restarts_at_newest_page_and_document_top():
    script = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    assert 'window.history.scrollRestoration = "manual";' in script
    hydration = script[
        script.index("function qaHydrateWorkspaceCache("):
        script.index("function qaClearWorkspaceCache(")
    ]
    assert "qaDeliveryPage = 1;" in hydration
    assert "const savedPage = Math.max(1, Number(cached.delivery.page || 1));" in hydration
    assert "savedPage === 1" in hydration
    assert 'requestedView === "deliveries"' in hydration
    assert "const size = Number(cached.delivery.page_size || qaDeliveryPageSize);" in hydration


def test_selected_delivery_history_workbench_contract():
    script = (
        ROOT / "src" / "webui" / "destination_overview_acceptance.js"
    ).read_text(encoding="utf-8")
    style = (
        ROOT / "src" / "webui" / "destination_overview_acceptance.css"
    ).read_text(encoding="utf-8")

    for token in (
        "delivery-history-workbench",
        "delivery-history-source-filter",
        "delivery-history-severity-filter",
        "delivery-history-outcome-filter",
        "delivery-history-range-filter",
        "delivery-history-sort",
        "delivery-history-detail",
        "delivery-history-copy",
        "qaLoadDeliveryPage = async function",
        "renderDeliveries = function",
    ):
        assert token in script

    assert "delivery-history-refresh" not in script

    assert (
        "grid-template-columns: minmax(0, 1.12fr) minmax(380px, 0.88fr);"
        in style
    )
    assert (
        "#view-deliveries .delivery-history-workbench {\n"
        "  display: grid;\n"
        "  grid-template-columns: minmax(0, 1.12fr) minmax(380px, 0.88fr);\n"
        "  gap: 12px;\n"
        "  align-items: stretch;\n"
        "}" in style
    )
    assert ".delivery-history-list-scroll" in style
    assert "overflow-y: auto;" in style


def test_dashboard_refresh_hides_legacy_markup_until_operations_dashboard_is_ready():
    style = (
        ROOT / "src" / "webui" / "destination_overview_acceptance.css"
    ).read_text(encoding="utf-8")
    dashboard = (
        ROOT / "src" / "webui" / "operations_dashboard.js"
    ).read_text(encoding="utf-8")

    assert (
        '#view-dashboard:not([data-operations-dashboard="1"]) {\n'
        "  visibility: hidden;\n"
        "}" in style
    )
    assert 'section.dataset.operationsDashboard = "1";' in dashboard


def test_delivery_history_panels_use_approved_header_bands_and_bottom_aligned_pager():
    theme = (ROOT / "src" / "webui" / "visual_refinement.css").read_text(encoding="utf-8")

    assert "#view-deliveries#view-deliveries .delivery-history-list-heading" in theme
    assert "#view-deliveries#view-deliveries .delivery-history-tags-heading" in theme
    assert "#view-deliveries#view-deliveries .delivery-history-list-panel::before" in theme
    assert "#view-deliveries#view-deliveries .delivery-history-list-scroll" in theme
    assert ".delivery-history-list-footer" in theme
