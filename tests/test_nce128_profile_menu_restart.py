"""NCE-128 (THE-1962, THE-1965): Restart Nowlert lives in the profile menu only.

PR 653 removed the duplicate header button from the Security page but left the
menu-created platform restart parked in the hidden Security toolbar, so an
administrator had no visible Restart control at all. The restart item is now
static markup in the profile (user icon) menu, shown to administrators only,
and it opens the existing restart confirmation dialog.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _ui_build() -> str:
    service = _read("src/webui/service.py")
    start = service.index('UI_BUILD = "') + len('UI_BUILD = "')
    return service[start:service.index('"', start)]


def _profile_menu(markup: str) -> str:
    start = markup.index('id="profile-menu-popover"')
    return markup[start:markup.index("</div>", start)]


def _security_view(markup: str) -> str:
    start = markup.index('<section id="view-account"')
    return markup[start:markup.index("</section>", start)]


def test_profile_menu_carries_one_admin_only_restart_item_between_profile_and_sign_out():
    menu = _profile_menu(_read("src/webui/index.html"))

    item_start = menu.index('id="platform-restart"')
    item = menu[menu.rindex("<button", 0, item_start):menu.index("</button>", item_start)]
    assert 'type="button"' in item
    assert 'role="menuitem"' in item
    assert 'data-action="restart-platform"' in item
    assert " hidden" in item
    assert "Restart Nowlert" in item
    # The glyph is an inline SVG like the dialog button, never a symbol character.
    assert '<svg class="button-glyph"' in item
    assert "⏻" not in item
    # policy_simplification.js decorates only the Security and Sign out rows at
    # runtime, so the restart row carries the same row classes statically and
    # lays out on the same icon/label grid as its siblings.
    assert 'class="profile-menu-item"' in item
    assert '<span class="profile-menu-icon profile-menu-glyph" aria-hidden="true">' in item
    assert '<span class="profile-menu-label">Restart Nowlert</span>' in item
    assert menu.index('data-view="account"') < item_start < menu.index('data-action="logout"')


def test_security_page_has_no_restart_control_visible_or_hidden():
    markup = _read("src/webui/index.html")
    account = _security_view(markup)

    for marker in ("restart-platform", "platform-restart", "Restart Nowlert", "restart-header-button"):
        assert marker not in account
    assert markup.count('data-action="restart-platform"') == 1
    assert 'id="restart-header-button"' not in markup

    cleanup = _read("src/webui/acceptance_cleanup.js")
    assert "platform-restart" not in cleanup
    assert "accountToolbar" not in cleanup
    assert '"#view-account .section-toolbar"' not in cleanup
    assert 'document.getElementById("platform-check-updates")' in cleanup

    headers = _read("src/webui/page_headers.js")
    assert 'else if (view === "account")' not in headers
    assert "restart-header-button" not in headers


def test_enhancements_bind_the_menu_item_and_no_longer_create_a_platform_restart():
    script = _read("src/webui/enhancements.js")

    assert 'restartButton.id = "platform-restart"' not in script
    assert 'element("span", { text: "Restart Nowlert" })' not in script
    assert "menu.append(updateButton);" in script
    assert "function installProfileRestart()" in script
    assert 'restart.dataset.profileRestartBound === "1"' in script
    assert 'if (typeof closeProfileMenu === "function") closeProfileMenu();' in script

    sync = script[script.index("function syncHeaderMenu()"):script.index("function desiredView()")]
    assert "installProfileRestart();" in sync
    assert "restart.hidden = !isAdmin();" in sync
    assert script.index("installProfileRestart();", script.index("restorePersistedView();")) > 0

    # The dialog flow is reused, not duplicated: the menu item is dispatched by
    # app.js handleClick through data-action="restart-platform".
    app = _read("src/webui/app.js")
    assert 'else if (action === "restart-platform") {' in app
    assert 'byId("restart-dialog").showModal();' in app
    assert 'request("/reboot", {' in app
    assert "resourceAction(\"restart-platform\"" not in script


def test_reference_styles_describe_the_profile_menu_restart_and_drop_the_header_rule():
    styles = _read("src/webui/reference_acceptance.css")

    assert "the legacy header button is the retained, accepted Restart control" not in styles
    assert '.topbar[data-page-view="account"] #platform-restart' not in styles
    assert "restart-header-button" not in styles
    assert ".profile-menu-popover .profile-menu-glyph .button-glyph" in styles
    assert ".profile-menu-popover #platform-restart" in styles
    # The row layout lives in policy_simplification.css: the label is as wide as
    # the popover's label column at 15 px, so it stays on one line there.
    rows = " ".join(_read("src/webui/policy_simplification.css").split())
    assert ".profile-menu-popover #platform-restart .profile-menu-label { white-space: nowrap; }" in rows


def test_nce128_build_versions_the_changed_webui_bundle():
    # r85 was taken by NCE-127 on development while this fix was in review.
    build = _ui_build()
    assert build == "20260929-r86"
    markup = _read("src/webui/index.html")
    assert f'name="nowlert-ui-build" content="{build}"' in markup
    assert f"/ui/app.js?v={build}" in markup
    assert f"/ui/qa_patch.css?v={build}" in markup
    assert f"/ui/qa_patch.js?v={build}" in markup
    assert "20260929-r84" not in markup
    assert "20260929-r85" not in markup
