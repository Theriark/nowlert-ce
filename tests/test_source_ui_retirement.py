from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src" / "webui" / "service.py"
SCRIPT = ROOT / "src" / "webui" / "source_ui_retirement.js"


def test_source_management_is_retired_from_navigation():
    service = SERVICE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")

    assert '"/ui/source_ui_retirement.js"' in service
    assert '<script src="/ui/source_ui_retirement.js" defer></script>' in service
    assert 'delete VIEW_TITLES.sources;' in script
    assert 'document.querySelector(\'#primary-nav [data-view="sources"]\')' in script
    assert 'sourcesNav.remove();' in script
    assert 'if (view === "sources") view = "destinations";' in script
    assert 'if (state.currentView === "sources") navigate("destinations", "replace");' in script
