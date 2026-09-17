from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        "delivery-history-refresh",
        "qaLoadDeliveryPage = async function",
        "renderDeliveries = function",
    ):
        assert token in script

    assert (
        "grid-template-columns: minmax(0, 1.12fr) minmax(380px, 0.88fr);"
        in style
    )
    assert ".delivery-history-list-scroll" in style
    assert "overflow-y: auto;" in style
