"""Nowlert product icon identity."""

from pathlib import Path

from formatters.presentation import PresentationMixin
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    @staticmethod
    def get(*_keys, default=None):
        return default


def test_nowlert_product_asset_is_packaged():
    assert (ROOT / "assets" / "icons" / "nowlert.png").is_file()


def test_product_sources_use_the_current_nowlert_asset():
    assert PresentationMixin.PRODUCT_ICONS["nowlert"] == "nowlert.png"
    assert PresentationMixin.TEAMS_ICON_PIXELS["nowlert"] == 80


def test_webui_primary_icon_uses_nowlert_asset():
    service = WebUIService(
        Configuration(),
        root=ROOT,
        platform_available=True,
    )

    assert service.assets["/ui/icon.png"][0] == "assets/icons/nowlert.png"
    assert (
        service.assets["/ui/source-icons/nowlert.png"][0]
        == "assets/icons/nowlert.png"
    )


def test_webui_uses_nowlert_source_and_schema():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    enhancements = (
        ROOT / "src" / "webui" / "enhancements.js"
    ).read_text(encoding="utf-8")

    assert 'GENERIC_SOURCE_ICON = "/ui/source-icons/nowlert.png"' in app
    assert 'source: "nowlert"' in app
    assert 'schema: "nowlert.event.v1"' in app
    assert 'route.source : "nowlert"' in enhancements
