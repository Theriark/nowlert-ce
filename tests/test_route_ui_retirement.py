from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILTERING = ROOT / "src" / "webui" / "filtering.js"


def test_filtering_is_independent_from_legacy_routes_view_and_retires_routes_navigation():
    source = FILTERING.read_text(encoding="utf-8")

    assert 'const destinationsNav = document.querySelector(\'#primary-nav [data-view="destinations"]\')' in source
    assert "destinationsNav.after(button)" in source
    assert 'const destinationsView = byId("view-destinations")' in source
    assert "destinationsView.after(section)" in source

    assert 'const routesNav = document.querySelector(\'#primary-nav [data-view="routes"]\')' not in source
    assert 'const routesView = byId("view-routes")' not in source
    assert "routesView.after(section)" not in source
    assert "function decoupleRouteUI()" not in source

    assert 'const legacyRoutesNav = document.querySelector(\'#primary-nav [data-view="routes"]\')' in source
    assert "legacyRoutesNav.remove()" in source
    assert "delete VIEW_TITLES.routes" in source
    assert 'if (view === "routes") view = "destinations";' in source
    assert 'if (state.currentView === "routes") navigate("destinations", "replace");' in source


def test_filtering_user_copy_no_longer_instructs_route_management():
    source = FILTERING.read_text(encoding="utf-8")

    assert "Assign at least one integration to a destination before creating a filter." in source
    assert "This destination currently has no enabled integration." in source
    assert "Enable at least one route to a destination before creating a filter." not in source
    assert "This destination currently has no enabled route/integration relationship." not in source
