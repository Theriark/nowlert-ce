"""Destination editor regression fixes for the compact drawer UI."""

from pathlib import Path

from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]
FIX_SCRIPT = ROOT / "src" / "webui" / "destination_editor_fix.js"
FIX_STYLE = ROOT / "src" / "webui" / "destination_editor_fix.css"


class Configuration:
    def get(self, *_keys, default=None):
        return default


def test_destination_editor_fix_assets_are_served_after_destination_routes():
    service = WebUIService(Configuration(), root=ROOT)

    page = service.response("/")
    assert page is not None and page.status == 200
    html = page.body.decode("utf-8")
    assert html.index('/ui/destination_routes.css') < html.index('/ui/destination_editor_fix.css')
    assert html.index('/ui/destination_routes.js') < html.index('/ui/destination_editor_fix.js')

    stylesheet = service.response("/ui/destination_editor_fix.css")
    assert stylesheet is not None and stylesheet.status == 200
    assert stylesheet.content_type == "text/css; charset=utf-8"

    script = service.response("/ui/destination_editor_fix.js")
    assert script is not None and script.status == 200
    assert script.content_type == "text/javascript; charset=utf-8"


def test_destination_editor_fix_removes_duplicate_message_style_and_duplicate_title_suffix():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert 'querySelectorAll(".destination-message-style")' in source
    assert "controls.slice(1)" in source
    assert 'editing ? `Edit ${name}` : "Add destination"' in source


def test_destination_editor_fix_keeps_sharing_with_credentials():
    source = FIX_SCRIPT.read_text(encoding="utf-8")

    assert 'const credentials = secrets?.closest("fieldset");' in source
    assert "credentials.append(shared);" in source


def test_destination_editor_fix_restores_amber_accent_and_dark_provider_options():
    stylesheet = FIX_STYLE.read_text(encoding="utf-8")

    assert "--destination-accent: var(--accent, #f4c542);" in stylesheet
    assert "--destination-accent-strong: var(--accent-strong, #d9a629);" in stylesheet
    assert ".destination-provider-type select option" in stylesheet
    assert "#16aef2" not in stylesheet
    assert "#0e97d6" not in stylesheet
