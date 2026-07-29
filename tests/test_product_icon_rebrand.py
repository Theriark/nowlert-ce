"""Nowlert product icon identity and legacy asset compatibility."""

from pathlib import Path

from formatters.presentation import PresentationMixin
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    @staticmethod
    def get(*_keys, default=None):
        return default


def test_nowlert_and_legacy_product_assets_are_packaged():
    assert (ROOT / "assets" / "icons" / "nowlert.png").is_file()
    assert (ROOT / "assets" / "icons" / "notifinho.png").is_file()


def test_product_sources_use_the_current_nowlert_asset():
    assert PresentationMixin.PRODUCT_ICONS["nowlert"] == "nowlert.png"
    assert PresentationMixin.PRODUCT_ICONS["notifinho"] == "nowlert.png"
    assert PresentationMixin.TEAMS_ICON_PIXELS["nowlert"] == 80
    assert PresentationMixin.TEAMS_ICON_PIXELS["notifinho"] == 80


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


def test_legacy_webui_product_icon_url_remains_available():
    service = WebUIService(
        Configuration(),
        root=ROOT,
        platform_available=True,
    )

    assert (
        service.assets["/ui/source-icons/notifinho.png"][0]
        == "assets/icons/notifinho.png"
    )


def test_webui_uses_nowlert_source_while_preserving_legacy_schema():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    enhancements = (
        ROOT / "src" / "webui" / "enhancements.js"
    ).read_text(encoding="utf-8")

    assert 'GENERIC_SOURCE_ICON = "/ui/source-icons/nowlert.png"' in app
    assert 'source: "nowlert"' in app
    assert 'schema: "notifinho.event.v1"' in app
    assert 'route.source : "nowlert"' in enhancements
