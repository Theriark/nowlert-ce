"""Packaged WebUI, transport, and browser-security contract tests."""

from __future__ import annotations

import http.client
import threading

from html.parser import HTMLParser
from pathlib import Path

import inputs.http as http_module

from dispatcher import Dispatcher
from inputs.http import HTTPServer
from storage.database import Database
from webui.service import SECURITY_HEADERS, UI_BUILD, WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def __init__(self, data):
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


class Router:
    def route(self, _item):
        raise AssertionError("WebUI assets must not enter notification routing")


class MarkupInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.scripts = []
        self.stylesheets = []
        self.inline_handlers = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script":
            self.scripts.append(values.get("src"))
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))
        self.inline_handlers.extend(
            name for name, _value in attrs if name.casefold().startswith("on")
        )


def enabled_config():
    return Configuration({
        "http": {"enabled": True},
        "api": {"enabled": True},
        "platform": {"enabled": True},
        "webui": {"enabled": True},
    })


def http_request(port, method, path):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    connection.request(method, path)
    response = connection.getresponse()
    status = response.status
    headers = response.getheaders()
    body = response.read()
    connection.close()
    return status, headers, body


def test_webui_service_is_explicitly_gated_and_has_no_path_mapping():
    service = WebUIService(enabled_config(), root=ROOT)

    assert service.enabled is True
    assert service.response("/").status == 200
    assert service.response("/ui/app.js").content_type.startswith("text/javascript")
    assert service.response("/ui/i18n.js").content_type.startswith("text/javascript")
    assert service.response("/ui/styles.css").content_type.startswith("text/css")
    assert service.response("/ui/icon.png").content_type == "image/png"
    assert service.response("/ui/../config/config.yaml").status == 404
    assert service.response("/api/v2/session") is None
    assert service.response("/home-assistant/events") is None

    unavailable = WebUIService(
        enabled_config(),
        root=ROOT,
        platform_available=False,
    )
    assert unavailable.enabled is False
    assert unavailable.response("/").status == 404

    for section in ("http", "api", "platform", "webui"):
        configuration = enabled_config()
        configuration.data[section]["enabled"] = False
        disabled = WebUIService(configuration, root=ROOT)
        assert disabled.enabled is False
        assert disabled.response("/").status == 404
        assert disabled.response("/ui/app.js").status == 404


def test_webui_is_default_on_but_every_explicit_disable_is_authoritative():
    service = WebUIService(Configuration({}), root=ROOT, platform_available=True)

    assert service.enabled is True
    assert service.response("/").status == 200

    for section in ("http", "api", "platform", "webui"):
        disabled = WebUIService(
            Configuration({section: {"enabled": False}}),
            root=ROOT,
            platform_available=True,
        )
        assert disabled.enabled is False


def test_native_http_serves_get_and_head_with_strict_browser_headers(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(http_module, "config", enabled_config())
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    server = HTTPServer(
        ("127.0.0.1", 0),
        Dispatcher(),
        Router(),
        1_048_576,
        "",
        platform_database=database,
    )
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        page = http_request(server.server_port, "GET", "/")
        script = http_request(server.server_port, "GET", "/ui/app.js")
        head = http_request(server.server_port, "HEAD", "/ui/styles.css")
        missing = http_request(server.server_port, "GET", "/ui/missing.js")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

    page_headers = dict(page[1])
    assert page[0] == 200
    assert page_headers["Content-Type"] == "text/html; charset=utf-8"
    assert page_headers["Cache-Control"] == "no-store"
    assert page_headers["X-Frame-Options"] == "DENY"
    assert page_headers["X-Content-Type-Options"] == "nosniff"
    assert page_headers["Referrer-Policy"] == "no-referrer"
    assert page_headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "frame-ancestors 'none'" in page_headers["Content-Security-Policy"]
    assert script[0] == 200 and script[2]
    assert head[0] == 200 and head[2] == b""
    assert int(dict(head[1])["Content-Length"]) > 0
    assert missing[0] == 404 and missing[2] == b""
    assert set(SECURITY_HEADERS).issubset(set(page[1]))


def test_teams_destination_editor_exposes_modern_and_classic_message_style():
    script = (
        ROOT / "src" / "webui" / "app.js"
    ).read_text(encoding="utf-8")

    teams_start = script.index("teams: {")
    slack_start = script.index("slack: {", teams_start)
    teams_block = script[teams_start:slack_start]

    assert 'key: "message_style"' in teams_block
    assert 'label: "Message style"' in teams_block
    assert '["modern", "Modern Card"]' in teams_block
    assert '["classic", "Classic Card"]' in teams_block
    assert 'default: "modern"' in teams_block



def test_webui_markup_is_semantic_external_and_complete():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    inspector = MarkupInspector()
    inspector.feed(markup)

    required = {
        "bootstrap-form",
        "bootstrap-token",
        "login-form",
        "app-shell",
        "primary-nav",
        "main-content",
        "view-dashboard",
        "view-sources",
        "view-destinations",
        "view-routes",
        "view-tokens",
        "view-deliveries",
        "view-audit",
        "view-users",
        "view-settings",
        "view-updates",
        "view-data",
        "view-account",
        "configuration-inputs",
        "source-table",
        "history-range",
        "dashboard-flow",
        "dashboard-delivery-chart",
        "dashboard-top-sources",
        "dashboard-top-destinations",
        "dashboard-system-health",
        "health-check-list",
        "backup-settings-form",
        "avatar-form",
        "preferences-form",
        "destination-dialog",
        "route-dialog",
        "token-dialog",
        "preview-dialog",
        "secret-dialog",
        "import-dialog",
    }
    assert required <= inspector.ids
    for retired in ("notice-console", "notice-composer", "notice-form", "notice-panel", "notice-list"):
        assert retired not in inspector.ids
    assert inspector.scripts == [
        "/ui/app.js?v=20260920-r52",
        "/ui/enhancements.js",
        "/ui/qa_patch.js?v=20260920-r52",
        "/ui/i18n.js",
        "/ui/dashboard.js",
    ]
    assert inspector.stylesheets == [
        "/ui/styles.css",
        "/ui/enhancements.css",
        "/ui/qa_patch.css?v=20260920-r52",
        "/ui/professional.css",
    ]
    assert inspector.inline_handlers == []
    assert "<style" not in markup
    assert "javascript:" not in markup.casefold()


def test_webui_uses_same_origin_api_without_unsafe_dom_or_secret_persistence():
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    for endpoint in (
        "/bootstrap",
        "/session",
        "/destinations",
        "/routes",
        "/tokens",
        "/deliveries",
        "/audit-events",
        "/users",
        "/preferences",
        "/integrations",
        "/version",
        "/portability/export",
        "/portability/preview",
        "/portability/import",
        "/migrations/v1/preview",
        "/migrations/v1/import",
        "/configuration/inventory",
        "/configuration/migration/preview",
        "/configuration/migration/apply",
        "/configuration/routing-authority",
        "/backups",
        "/backup-settings",
        "/health-checks",
        "/account/avatar",
        "/metrics/",
        "/account/password",
    ):
        assert endpoint in script
    assert "/notices" not in script
    assert "renderNotices" not in script
    assert "saveNotice" not in script
    assert 'const API = "/api/v2"' in script
    assert 'credentials: "same-origin"' in script
    assert 'cache: "no-store"' in script
    assert '["delivered", "success"].includes(item.outcome)' in script
    assert "function destinationTestToast(delivery, outputType)" in script
    assert "Microsoft Teams accepted the test (HTTP 202)." in script
    assert "Delivery is not confirmed; check the channel." in script
    assert 'actionButton("Reset password", "reset-user", item.id)' in script
    assert 'dataset: { action: "toggle-token", id: item.id }' in script
    assert 'dataset: { action: "toggle-input", id: item.name }' in script
    assert 'outputIcon(item.output_type)' in script
    assert 'capitalize(item.priority_name || "normal")' in script
    assert "Promise.allSettled" in script
    assert "state.workspaceErrors.push" in script
    assert 'component: "Workspace"' in script
    assert "const values = await Promise.all" not in script
    assert 'if (!self)' in script
    assert 'headers["X-CSRF-Token"]' in script
    assert "navigator.clipboard.writeText" in script
    assert "textContent" in script
    for forbidden in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "localStorage",
        "sessionStorage",
        "eval(",
        "new Function",
    ):
        assert forbidden not in script


def test_webui_keeps_workspace_visible_and_identifies_partial_api_failures():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert 'id="workspace-alert"' in markup
    assert 'id="workspace-alert-list"' in markup
    assert 'role="alert"' in markup
    for component in (
        "Destinations",
        "Routes",
        "Event API tokens",
        "Configuration inventory",
        "Backup settings",
    ):
        assert f'["{component}", request(' in script
    assert 'deliveries: ["Delivery history", initialDeliveryRequest' in script
    assert 'audit: ["Audit log", initialAuditRequest' in script
    session_request = script.index('session = await request("/session")')
    session_show = script.index("showApp(session);", session_request)
    workspace_load = script.index("await loadWorkspace();", session_show)
    assert session_request < session_show < workspace_load


def test_production_image_already_packages_webui_and_icon():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY src /nowlert/src" in dockerfile
    assert "COPY assets /nowlert/assets" in dockerfile
    assert (ROOT / "src" / "webui" / "index.html").is_file()
    assert (ROOT / "src" / "webui" / "app.js").is_file()
    assert (ROOT / "src" / "webui" / "styles.css").is_file()
    assert (ROOT / "assets" / "icons" / "nowlert.png").is_file()


def test_v310_management_headers_and_dashboard_analytics_alignment():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "professional.css").read_text(encoding="utf-8")

    assert (
        "Configure delivery targets for Discord, Microsoft Teams, Slack, "
        "generic webhooks, MQTT, and ntfy."
    ) in markup
    assert (
        "Review final delivery outcomes, retries, response status, and safe "
        "transport errors for routed events."
    ) in markup
    marker = "/* Nowlert 3.1.0 final management headers and analytics alignment */"
    assert marker in styles
    final_styles = styles[styles.index(marker):]
    assert "#view-dashboard .dashboard-analytics-grid" in final_styles
    assert "> .dashboard-deliveries-panel" in final_styles
    assert "margin-top: 0;" in final_styles


def test_v310_management_descriptions_content_headers_and_ranking_empty_states():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    dashboard = (ROOT / "src" / "webui" / "dashboard.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "professional.css").read_text(encoding="utf-8")

    descriptions = (
        "Review built-in integrations, available inputs, and their operational categories.",
        "Connect integrations and inputs to destinations with priorities and event filters.",
        "Review security-relevant actions, health checks, outcomes, and operational details.",
        "Manage local accounts, roles, access state, and password resets.",
        "Configure regional preferences and integration-specific behavior.",
        "Review the running version and any advertised Nowlert update.",
        "Inspect and manage the SMTP, HTTP, and Redfish listeners used to receive events.",
        "Configure backup destinations, schedules, snapshots, restore operations, and portable configuration.",
        "Move user-created Nowlert configuration without moving credentials, accounts, history, or recovery data.",
        "Manage your profile information and account access.",
    )
    for copy in descriptions:
        assert copy in markup

    assert 'data-panel-header="destinations"' not in markup
    assert 'class="table-panel professional-resource-panel"' not in markup
    assert '<div id="destination-list" class="resource-grid"></div>' in markup
    assert 'data-panel-header="deliveries"' in markup
    assert ">Delivery attempts<" in markup
    assert ">Source, outcome, response, and time<" in markup

    assert '"No top sources"' in dashboard
    assert '"No top destinations"' in dashboard
    assert 'icon.src = "/ui/brand/nowlert-owl-v3.1.0.png";' in dashboard

    marker = "/* Nowlert 3.1.0 management descriptions and content headers */"
    assert marker in styles
    final_styles = styles[styles.index(marker):]
    assert ".dashboard-ranking-empty img" in final_styles
    assert ".professional-panel-header" in final_styles


def test_v310_menu_navigation_uses_browser_history_and_destinations_stay_a_card_grid():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    enhancements = (ROOT / "src" / "webui" / "enhancements.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "professional.css").read_text(encoding="utf-8")

    assert 'function navigate(view, historyMode = "push")' in app
    assert 'window.history.pushState({ nowlertView: view }' in app
    assert 'window.addEventListener("popstate", navigateFromHistory)' in app
    assert 'navigate(view, "none")' in app
    assert 'originalNavigate(view, historyMode)' in enhancements
    assert 'navigate(view, "replace")' in enhancements
    assert 'originalNavigate(view, "replace")' not in enhancements

    assert 'data-panel-header="destinations"' not in markup
    assert 'professional-resource-panel' not in markup
    assert '<div id="destination-list" class="resource-grid"></div>' in markup
    assert 'data-panel-header="deliveries"' in markup

    marker = "/* Nowlert 3.1.0 Destinations card-grid empty state */"
    assert marker in styles
    final_styles = styles[styles.index(marker):]
    assert "background: transparent;" in final_styles
    assert "border: 0;" in final_styles


def test_nce15_regional_i18n_save_boundary():
    script = (ROOT / "src" / "webui" / "i18n.js").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    for locale in (
        "pt", "es", "fr", "de", "it", "nl", "pl", "cs", "ro",
        "sv", "da", "nb", "fi", "el", "tr", "ru", "uk", "ja", "zh",
    ):
        assert f'"{locale}": [' in script

    assert '"en-GB": "English"' in script
    assert '"en-US": "English"' in script
    assert '"pt-PT": "Português"' in script
    assert '"pt-BR": "Português"' in script
    assert "canonicalAliases" not in script
    assert "select.value = canonicalAliases" not in script

    for forbidden_label in (
        "English — UK",
        "English — US",
        "Português — Portugal",
        "Português — Brasil",
        "English (United Kingdom)",
        "English (United States)",
        "Português (Portugal)",
        "Português (Brasil)",
    ):
        assert forbidden_label not in markup

    assert '<option value="en-GB">English</option>' in markup
    assert '<option value="en-US" hidden>English</option>' in markup
    assert '<option value="pt-PT">Português</option>' in markup
    assert '<option value="pt-BR" hidden>Português</option>' in markup

    assert (
        'const leavingSettings = state.currentView === "settings" && view !== "settings";'
        in script
    )
    assert "if (leavingSettings) renderPreferences();" in script
    assert 'if (view === "settings") renderPreferences();' in script

    save = app.index("async function savePreferences")
    request = app.index('const response = await request("/preferences"', save)
    persisted = app.index("state.preferences = response.preferences;", save)
    assert request < persisted


def test_nce22_nce24_delivery_and_audit_direct_pagination_controls():
    script = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(encoding="utf-8")
    platform = (ROOT / "src" / "api" / "platform.py").read_text(encoding="utf-8")

    # Only Delivery History and Audit Log get the extended pager.
    assert 'containerId === "delivery-pagination"' in script
    assert 'containerId === "audit-pagination"' in script
    assert "if (!directNavigation)" in script

    # First / Last navigation.
    assert 'text: "First"' in script
    assert 'text: "Last"' in script
    assert "disabled: page <= 1" in script
    assert "disabled: page >= totalPages" in script

    # Direct page-number navigation and validity constraints.
    assert 'className: "qa-page-number"' in script
    assert 'type: "number"' in script
    assert 'min: "1"' in script
    assert "max: String(totalPages)" in script
    assert "Number.isInteger(value)" in script
    assert "value < 1 || value > totalPages" in script
    assert "pageInput.setAttribute(" in script
    assert '"aria-invalid",' in script
    assert 'requestedPage() === null ? "true" : "false"' in script
    assert 'if (event.key === "Enter")' in script

    # Every paging action finishes at the actual document bottom, after
    # asynchronous layout settles.
    assert "const navigatePage = (targetPage) => {" in script
    assert "function qaScrollPageBottom()" in script
    assert "document.documentElement.scrollHeight" in script
    assert "document.body ? document.body.scrollHeight : 0" in script
    assert "window.requestAnimationFrame" in script
    assert "window.requestAnimationFrame(scroll);" in script
    assert "Promise.resolve(result).then(" in script
    assert 'previous.addEventListener("click", () => navigatePage(page - 1));' in script
    assert 'next.addEventListener("click", () => navigatePage(page + 1));' in script
    assert 'first.addEventListener("click", () => navigatePage(1));' in script
    assert 'last.addEventListener("click", () => navigatePage(totalPages));' in script
    assert "if (requested !== page) navigatePage(requested);" in script

    # Top, pager, and Entries share the bottom row. Bottom still uses
    # true document-bottom scrolling.
    assert "function qaCreateTopShortcut()" in script
    assert 'className: "button secondary small qa-top-shortcut"' in script
    assert 'text: "Top"' in script
    assert 'text: "Bottom"' in script
    assert "function qaArrangePaginationFooter(" in script
    assert 'className: "qa-pagination-left"' in script
    assert "footer.append(label);" in script
    assert 'footer.classList.add("qa-pagination-footer");' in script
    assert "qaScrollPageBottom();" in script
    assert 'data-qa-bottom' in script
    assert ".qa-pagination-footer" in styles
    assert "overflow-anchor: none" in styles

    # Entering Delivery History or Audit Log from another view always starts
    # at the top without changing pagination/page-size state.
    assert "function qaScrollPageTop()" in script
    assert "const qaOriginalNavigate = navigate;" in script
    assert 'navigate = function navigateWithPagedViewTop(view, historyMode = "push") {' in script
    assert "const previousView = state.currentView;" in script
    assert "const currentView = state.currentView;" in script
    assert "previousView !== currentView" in script
    assert 'currentView === "deliveries" || currentView === "audit"' in script
    assert "qaScrollPageTop();" in script

    # NCE-23 Audit entries-per-page persistence remains intact.
    assert 'const QA_AUDIT_PAGE_SIZE_KEY = "nowlert.audit.pageSize";' in script
    assert "qaReadAuditPageSize()" in script
    assert "qaWriteAuditPageSize(qaAuditPageSize);" in script
    assert "/size/${qaAuditPageSize}" in script

    # Delivery History gets the same persisted page-size choices.
    assert 'const QA_DELIVERY_PAGE_SIZE_KEY = "nowlert.delivery.pageSize";' in script
    assert "QA_DELIVERY_PAGE_SIZES = [25, 50, 100, 150, 250, 500]" in script
    assert "qaReadDeliveryPageSize()" in script
    assert "qaWriteDeliveryPageSize(qaDeliveryPageSize);" in script
    assert "/size/${qaDeliveryPageSize}" in script
    assert 'id: "delivery-page-size"' in script

    # Backend accepts the Delivery History selected page size.
    assert "_DELIVERY_PAGE_SIZES = (25, 50, 100, 150, 250, 500)" in platform
    assert "delivery_page_size = re.fullmatch(" in platform
    assert "/api/v2/deliveries/page/" in platform
    assert "int(delivery_page_size.group(2))" in platform
    assert "def _deliveries_page_endpoint(self, method, actor, page, size=None)" in platform

    # Layout remains usable on narrow displays.
    assert ".qa-pagination .qa-page-number" in styles
    assert "@media (max-width: 720px)" in styles


def test_audit_pagination_error_does_not_expose_request_details():
    script = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")
    handler_start = script.index("async function qaLoadAuditPage")
    handler_end = script.index("\n}\n", handler_start) + 3
    handler = script[handler_start:handler_end]

    assert 'toast("Audit page could not be loaded.", "error");' in handler
    assert "error.message" not in handler
    assert "error.stack" not in handler


def test_nce28_nce29_audit_context_and_explicit_health_checks():
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    # NCE-28: Audit Log exposes actor, precise action, affected resource,
    # resource identifier, outcome, and safe details.
    assert (
        "<th>Time</th><th>Action</th><th>User</th><th>Resource</th>"
        "<th>Outcome</th><th>Details</th>"
    ) in markup
    assert "function auditActionLabel(value)" in script
    assert "function auditActorLabel(item)" in script
    assert "function auditDetailsText(details)" in script
    assert "item.actor_username" in script
    assert "item.actor_user_id" in script
    assert "item.resource_id" in script
    assert 'text: item.action || "unknown"' in script
    assert 'text: auditDetailsText(item.details)' in script

    # Search includes the newly-visible actor and affected entity context.
    assert "item.actor_username," in script
    assert "item.actor_user_id," in script
    assert "item.resource_id," in script

    # NCE-29: generic workspace loading must not execute a health check.
    assert (
        'health: ["Health checks", request("/health-checks")'
        not in script
    )

    # Health checks remain available only as an explicit user action.
    assert 'action === "run-health-checks"' in script
    assert 'const response = await request("/health-checks");' in script



def test_nce30_nce31_admin_delete_controls():
    script = (ROOT / "src" / "webui" / "app.js").read_text(
        encoding="utf-8"
    )

    assert '"delete-user"' in script
    assert '"delete-backup"' in script

    assert (
        'actionButton("Delete", "delete-user", item.id, "danger")'
        in script
    )
    assert (
        'backupIconAction("delete-backup", item.id, "Delete", "trash", "danger")'
        in script
    )

    assert 'action === "delete-user"' in script
    assert 'action === "delete-backup"' in script

    assert 'await request(`/users/${id}`, { method: "DELETE" });' in script
    assert 'await request(`/backups/${id}`, { method: "DELETE" });' in script

    assert "the user still owns destinations, secrets, or backup destinations" in script
    assert "It cannot be restored after deletion." in script
    assert '"Delete snapshot"' in script



def test_nce31_nce33_nce34_nce35_development_followups():
    app = (ROOT / "src" / "webui" / "app.js").read_text(
        encoding="utf-8"
    )
    patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(
        encoding="utf-8"
    )
    styles = (ROOT / "src" / "webui" / "qa_patch.css").read_text(
        encoding="utf-8"
    )

    # NCE-31: destructive backup action has an explicit confirmation.
    assert "`Delete recovery snapshot ${id}?`" in app
    assert '"Delete snapshot"' in app
    assert "It cannot be restored after deletion." in app

    # NCE-33: role display uses the same authority as access control and
    # cannot be reset to the static HTML User value by the i18n layer.
    assert "const admin = isAdmin();" in app
    assert (
        'profileRole.textContent = admin ? "Admin" : "User";'
        in app
    )
    assert "delete profileRole.dataset.i18nSource;" in app
    assert (
        'accountRole.textContent = admin ? "Administrator" : "User";'
        in app
    )

    # NCE-34: restore the Stage-approved duplicate/empty badge cleanup.
    assert "function qaNormalizeDeliveryBadges()" in patch
    assert 'text === "—" || seen.has(key)' in patch
    assert "qaNormalizeDeliveryBadges();" in patch

    # NCE-35: direct page box is embedded in Page [n] of N, Go is gone,
    # and Enter remains the explicit direct navigation action.
    assert 'className: "qa-page-status"' in patch
    assert '"Page ",' in patch
    assert "pageInput," in patch
    assert 'text: "Go"' not in patch
    assert 'go.addEventListener(' not in patch
    assert 'pageInput.addEventListener("change"' not in patch
    assert 'if (event.key === "Enter")' in patch

    # Top / pager / Entries are one three-column bottom row.
    assert "function qaArrangePaginationFooter(" in patch
    assert 'className: "qa-pagination-left"' in patch
    assert "footer.append(label);" in patch
    assert (
        "grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);"
        in styles
    )
    assert ".qa-pagination-row > .qa-pagination-footer" in styles



def test_20260918_webui_polish_regressions():
    management = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")
    management_css = (ROOT / "src" / "webui" / "management_consistency.css").read_text(encoding="utf-8")
    delivery = (ROOT / "src" / "webui" / "destination_overview_acceptance.js").read_text(encoding="utf-8")
    delivery_css = (ROOT / "src" / "webui" / "destination_overview_acceptance.css").read_text(encoding="utf-8")
    audit_css = (ROOT / "src" / "webui" / "audit_log_refinement.css").read_text(encoding="utf-8")
    reference = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    reference_css = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    assert "function syncDestinationOwnerBadge(card)" in management
    assert "destinationOwnerName(item)" in management
    assert '<circle cx="6" cy="6" r="2"></circle>' in management
    assert '[data-action="preview-private-destination"]::before' in management_css
    assert '[data-action="test-private-destination-card"]::before' in management_css

    assert "function deliveryTagIcon(kind)" in delivery
    assert "delivery-history-tags-heading" in delivery
    assert "delivery-history-tag-pill" in delivery_css
    assert ".delivery-history-list-scroll::-webkit-scrollbar-button" in delivery_css

    assert "#view-audit .audit-log-list-scroll {" in audit_css
    assert "overflow-x: hidden;" in audit_css
    assert ".audit-log-list-scroll::-webkit-scrollbar-button" in audit_css

    assert "const USER_PAGE_SIZE = 6;" in reference
    assert "function openUserActivityDialog()" in reference
    assert "reference-users-recent-toggle" in reference
    assert "reference-users-page-size" not in reference
    assert 'textContent = `Showing ${start}–${end} of ${matching.length} users`' in reference
    assert ".reference-settings-grid > *" in reference_css
    assert 'restart.hidden = !show;' in reference
    assert "#restart-header-button.reference-account-restart" in reference_css

    assert 'account: "Security",' in app
    assert "<h2>Security</h2>" in markup


def test_20260918_round_two_screenshot_regressions():
    routing = (ROOT / "src" / "webui" / "routing_flow.js").read_text(encoding="utf-8")
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    headers = (ROOT / "src" / "webui" / "page_headers.js").read_text(encoding="utf-8")
    reference = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")
    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    # Routing Flow keeps connected barycentric placement instead of
    # independently pulling each column back to the top.
    assert "function shiftCentersToTop(" not in routing
    assert "routeCenters = resolveCenters(" in routing
    assert "filterCenters = resolveCenters(" in routing
    assert "destinationCenters = resolveCenters(" in routing

    # Restart keeps the existing action but uses the supplied confirmation UI.
    assert 'class="modal small-modal restart-reference-dialog"' in markup
    assert "Confirm restart to apply changes and reload the service." in markup
    assert 'id="restart-reason-count"' in markup
    assert 'id="restart-triggered-by"' in markup
    assert 'id="restart-environment"' in markup
    assert "function restartEnvironmentLabel()" in app
    assert "function updateRestartDialogContext()" in app

    # Security owns the accepted topbar restart button, not the menu-created one.
    assert 'if (view === "account") return "Security";' in headers
    assert 'nodes.push(document.getElementById("restart-header-button"));' in headers
    account_actions = headers[
        headers.index('} else if (view === "account")'):
        headers.index("return nodes.filter(Boolean);")
    ]
    assert 'platform-restart' not in account_actions
    assert 'restart.hidden = !show;' in reference

    # Delivery/Audit separators share the same full-height four-track grid.
    assert "grid-template-columns: 20% 46% 18% 16% !important;" in styles
    assert "#view-deliveries .delivery-history-list-footer," in styles
    assert "#view-audit .audit-log-list-footer" in styles
    assert "height: 78px !important;" in styles

    # Users no longer renders a page-size chip or trailing punctuation.
    assert "reference-users-page-size" not in reference
    assert 'Showing 0 users</span>' in reference
    assert 'Showing ${start}–${end} of ${matching.length} users`' in reference

    # Settings and Security are explicitly compact instead of stretching.
    assert ".reference-settings-grid {" in styles
    assert "align-items: start !important;" in styles
    assert ".reference-profile-card {" in styles
    assert "display: grid !important;" in styles
    assert ".reference-profile-copy {" in styles
    assert "#restart-dialog.restart-reference-dialog" in styles



def test_20260918_round_three_screenshot_regressions():
    reference = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    # Delivery History and Audit Log separators are painted by one shared row,
    # so the three vertical rules cannot drift with nested child heights.
    assert "background-position: 20% 0, 66% 0, 84% 0 !important;" in styles
    assert "background-size: 1px 100%, 1px 100%, 1px 100% !important;" in styles
    assert "#view-deliveries .reference-pagination-range," in styles
    assert "#view-audit .reference-pagination-range," in styles

    # Users View all is a separate dialog, not an expanded Recent activity card.
    assert "function ensureUserActivityDialog()" in reference
    assert "function openUserActivityDialog()" in reference
    assert 'dialog.id = "reference-users-activity-dialog";' in reference
    assert 'recentToggle.setAttribute("aria-haspopup", "dialog");' in reference
    assert "recentActivityExpanded" not in reference
    assert ".reference-users-activity-dialog" in styles

    # Only Updates is compressed in this pass; Regional settings selectors are
    # not part of the round-three compact overrides.
    round_three = styles[styles.index("/* 2026-09-18 round-three screenshot corrections. */"):]
    assert ".reference-updates-card {" in round_three
    assert ".reference-updates-card .reference-update-status-card" in round_three
    assert ".reference-regional-card {" not in round_three

    # Security is forced after i18n/runtime layers, including later mutations.
    assert "function forceProfileTitle()" in reference
    assert 'title.textContent = "Security";' in reference
    assert 'localTitle.textContent = "Security";' in reference
    assert "const titleObserver = new MutationObserver" in reference

    # Uploaded avatar images do not inherit the amber avatar gradient/glow.
    assert ".avatar.avatar-image {" in styles
    assert "box-shadow: none !important;" in round_three
    assert "#account-avatar.avatar-image" in styles
    assert "#profile-avatar.avatar-image" in styles

    # Password & sessions drops the two verbose posture descriptions and is
    # compacted to align visually with Profile & access.
    assert "You are currently signed in on this device." not in reference
    assert "No suspicious activity detected." not in reference
    assert "grid-template-columns: minmax(0, 1fr) 188px !important;" in round_three
    assert "min-height: 31px !important;" in round_three



def test_20260918_round_four_footer_destination_and_security_regressions():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    cleanup = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(encoding="utf-8")
    destination = (ROOT / "src" / "webui" / "destination_overview_acceptance.js").read_text(encoding="utf-8")
    management = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    # F5 must have the private-destination metadata before Destinations paints,
    # and only the unfinished first paint is temporarily hidden.
    assert "privateDestinations: []" in app
    assert "state.privateDestinations = Array.isArray(value.private_resources)" in app
    assert "function syncPrivateDestinationMetadataFromState()" in cleanup
    assert 'list.classList.add("acceptance-destination-first-paint")' in cleanup
    assert 'list.dataset.destinationFirstPaint = "1"' in cleanup
    assert "syncPrivateDestinationCards(state.privateDestinations);" in destination
    assert "state.privateDestinations = resources;" in destination
    assert "#view-destinations #destination-list.acceptance-destination-first-paint" in styles

    # Owner reconciliation is idempotent instead of replacing the badge DOM on
    # every consistency pass after the first paint.
    assert "const contentReady = (" in management
    assert "if (contentReady && positionReady) return;" in management

    # The wide desktop footer intentionally uses the compact reference pager.
    # Round five refines the exact number stepping without changing its controls.
    assert "function referencePageNumbers(page, totalPages)" in management
    round_four = styles[styles.index("/* 2026-09-18 round-four screenshot corrections. */"):]
    assert "background-image: none !important;" in round_four
    assert "minmax(250px, 1.62fr)" in round_four
    assert "height: 76px !important;" in round_four
    assert "border-right: 1px solid rgba(148, 163, 184, 0.2) !important;" in round_four
    assert "gap: 4px !important;" in round_four

    # Security cards share the same row height and the posture column consumes
    # its full height rather than collapsing after the removed descriptions.
    assert ".reference-account-grid {" in round_four
    assert "align-items: stretch !important;" in round_four
    assert ".reference-profile-card," in round_four
    assert "align-self: stretch !important;" in round_four
    assert "grid-template-rows: auto minmax(0, 1fr) auto !important;" in round_four
    assert "grid-template-columns: minmax(0, 1fr) 236px !important;" in round_four
    assert "grid-template-rows: minmax(0, 1fr) 1px minmax(0, 1fr) 1px minmax(0, 1fr) !important;" in round_four



def test_20260918_round_five_history_audit_settings_regressions():
    delivery = (ROOT / "src" / "webui" / "destination_overview_acceptance.js").read_text(encoding="utf-8")
    delivery_css = (ROOT / "src" / "webui" / "destination_overview_acceptance.css").read_text(encoding="utf-8")
    management = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")
    reference = (ROOT / "src" / "webui" / "reference_acceptance.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "reference_acceptance.css").read_text(encoding="utf-8")

    # Requested numeric stepping is current, next, current+4, then ellipsis.
    assert "const values = [page];" in management
    assert "const next = page + 1;" in management
    assert "const skip = page + 4;" in management
    assert 'if (skip < totalPages) values.push("ellipsis");' in management

    # The dead Delivery History refresh control is fully removed.
    assert "delivery-history-refresh" not in delivery
    assert "delivery-history-icon-button" not in delivery_css

    # The list card owns the outside border; the pager no longer draws a
    # second rounded box/bottom line inside Delivery History or Audit Log.
    round_five = styles[styles.index("/* 2026-09-18 round-five screenshot corrections. */"):]
    assert "border: 0 !important;" in round_five
    assert "border-radius: 0 !important;" in round_five
    assert "box-shadow: none !important;" in round_five
    assert "grid-template-rows: 76px !important;" in round_five
    assert "grid-template-rows: 14px 36px !important;" in round_five
    assert "padding: 7px 9px 19px !important;" in round_five

    # Regional settings remains the reference. Updates must not receive a
    # measured inline height because that can clip its nested cards while the
    # layout settles after refresh.
    assert "function alignSettingsReferenceCards()" in reference
    assert 'updates.style.height = "";' in reference
    assert 'window.matchMedia("(min-width: 1181px)")' not in reference
    assert "regional.getBoundingClientRect().height" not in reference
    assert "targetHeight" not in reference
    assert "requestAnimationFrame(alignSettingsReferenceCards);" in reference
    assert ".reference-updates-card #update-check-metadata" in round_five
    assert "display: none !important;" in round_five



def test_round19_served_html_cache_busts_round18_acceptance_assets():
    service = WebUIService(enabled_config(), root=ROOT)
    response = service.response("/")
    assert response is not None and response.status == 200
    markup = response.body.decode("utf-8")

    assert 'name="nowlert-ui-build" content="20260920-r52"' in markup
    assert "/ui/app.js?v=20260920-r52" in markup
    assert "/ui/qa_patch.css?v=20260920-r52" in markup

    # Every runtime extension receives the same build key so a newly deployed
    # WebUI cannot keep executing an older extension bundle.
    assert f'<script src="/ui/source_ui_retirement.js?v={UI_BUILD}" defer></script>' in markup
    assert f'<link rel="stylesheet" href="/ui/reference_acceptance.css?v={UI_BUILD}">' in markup

    app = service.response("/ui/app.js")
    patch = service.response("/ui/qa_patch.css")
    retirement = service.response("/ui/source_ui_retirement.js")
    assert app is not None and app.status == 200 and b"Preview completed." in app.body
    assert patch is not None and patch.status == 200 and b"round-18 acceptance corrections" in patch.body
    assert patch is not None and b"#primary-nav .nav-item[hidden]" in patch.body
    assert patch is not None and b"transform: scale(1.65)" in patch.body
    assert patch is not None and b"#app-shell .workspace" in patch.body
    assert retirement is not None and retirement.status == 200
    assert b"auditNav.hidden = !admin;" in retirement.body
    assert b"backupsNav.hidden = !admin;" in retirement.body
    assert b"usersNav.hidden = !admin;" in retirement.body

def test_destination_state_refreshes_across_signed_in_sessions():
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")

    assert "DESTINATION_STATE_SYNC_INTERVAL_MS = 5 * 1000" in script
    assert "async function refreshDestinationState()" in script
    assert 'request("/destinations", {' in script
    assert "reauthenticate: false" in script
    assert 'state.currentView !== "destinations"' in script
    assert 'if (state.user && view === "destinations") {' in script
    assert 'document.visibilityState === "hidden"' in script
    assert 'window.addEventListener("focus"' in script
    assert 'document.addEventListener("visibilitychange"' in script
    assert 'new CustomEvent("nowlert:filtering-state-invalidated")' in script
    assert 'new CustomEvent("nowlert:routing-topology-changed")' in script

def test_private_destination_admin_card_tracks_owner_state_and_matches_read_only_layout():
    cleanup = (ROOT / "src" / "webui" / "acceptance_cleanup.js").read_text(encoding="utf-8")
    management = (ROOT / "src" / "webui" / "management_consistency.js").read_text(encoding="utf-8")
    management_css = (ROOT / "src" / "webui" / "management_consistency.css").read_text(encoding="utf-8")
    destination = (ROOT / "src" / "webui" / "destination_overview_acceptance.js").read_text(encoding="utf-8")
    destination_css = (ROOT / "src" / "webui" / "destination_overview_acceptance.css").read_text(encoding="utf-8")

    # A private owner's enable/disable change must invalidate the admin-side
    # metadata signature so the card is rebuilt from the latest API response.
    signature = cleanup[
        cleanup.index("function privateDestinationSignature(items)"):
        cleanup.index("function syncPrivateDestinationMetadataFromState()")
    ]
    assert "item.enabled === true" in signature

    # The private admin card must render the current owner state instead of a
    # hard-coded Active badge, and both owner-only controls stay view-only.
    private_sync = management[
        management.index("function syncMetadataPrivateSharing(card)"):
        management.index("function destinationCardId(card)")
    ]
    assert 'const enabled = item?.enabled === true;' in private_sync
    assert 'const statusLabel = enabled ? "Active" : "Disabled";' in private_sync
    assert 'const statusState = enabled ? "active" : "disabled";' in private_sync
    assert "destination-control-readonly" in private_sync
    assert 'Private destination. View only.' in private_sync
    assert '${statusLabel} destination. View only.' in private_sync

    # Read-only controls use the same dimmed treatment as disabled controls.
    assert ".acceptance-private-destination .destination-control-readonly" in management_css
    assert "opacity: 0.45;" in management_css
    assert "pointer-events: none;" in management_css

    # Admin private cards keep the same action order and four-column desktop
    # geometry as ordinary read-only cards instead of stretching two buttons.
    action_block = destination[
        destination.index('className: "resource-actions acceptance-private-actions"'):
        destination.index("card.append(actions);")
    ]
    assert action_block.index('actionButton("Send test"') < action_block.index('actionButton("Preview"')
    assert "grid-template-columns: repeat(4, minmax(0, 1fr)) !important;" in destination_css
    assert "@media (max-width: 620px)" in destination_css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr)) !important;" in destination_css

def test_refresh_request_budget_and_dashboard_first_paint_regressions():
    app = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "src" / "webui" / "operations_dashboard.js").read_text(encoding="utf-8")
    acceptance = (ROOT / "src" / "webui" / "operations_acceptance.js").read_text(encoding="utf-8")

    # Cross-session destination state stays current without polling every page.
    assert "const DESTINATION_STATE_SYNC_INTERVAL_MS = 5 * 1000;" in app
    assert 'state.currentView !== "destinations"' in app
    assert 'if (state.user && view === "destinations") {' in app

    # The base workspace owns the initial Dashboard data request set, including
    # filtering, and publishes one readiness event for layered presentation.
    assert 'filters: ["Filtering", request("/filters"), (value) => {' in app
    assert "state.workspaceLoadedAt = Date.now();" in app
    assert 'new CustomEvent("nowlert:workspace-loaded"' in app

    # A temporary 429 must not be interpreted as an expired login.
    restore_start = app.index("async function restoreSession")
    restore_end = app.index("function toggleLoginPasswordVisibility", restore_start)
    restore = app[restore_start:restore_end]
    assert "error.status === 401" in restore
    assert "error.status === 429" in restore
    assert 'window.setTimeout(() => restoreSession(), 1500);' in restore
    assert "expireSession({ preserveCache: error instanceof APIError" not in restore

    # F5 does not launch the Dashboard's second four-request batch before the
    # workspace has loaded. The loaded workspace feeds the dashboard directly.
    assert 'view === DASHBOARD_VIEW && Number(state.workspaceLoadedAt || 0) > 0' in dashboard
    assert 'document.addEventListener("nowlert:workspace-loaded"' in dashboard
    assert "dashboardDeliveries = Array.isArray(state.deliveries)" in dashboard
    assert "filterSnapshot = state.filteringOverview" in dashboard

    # A valid cached/just-loaded dashboard may present Live immediately while
    # the 30-second refresh loop remains authoritative for subsequent updates.
    assert "function cachedDashboardTimestamp()" in acceptance
    assert "function workspaceDashboardTimestamp()" in acceptance
    assert "Math.max(" in acceptance
    assert 'document.addEventListener("nowlert:workspace-loaded"' in acceptance

def test_history_audit_and_backup_first_paint_cache_contract():
    patch = (ROOT / "src" / "webui" / "qa_patch.js").read_text(encoding="utf-8")

    # F5 restores the real current Delivery History and Audit Log page rows,
    # but keeps them out of the generic workspace fields so Dashboard cannot
    # inherit range-bound history data.
    fields = patch[
        patch.index("const QA_WORKSPACE_CACHE_FIELDS = ["):
        patch.index("];", patch.index("const QA_WORKSPACE_CACHE_FIELDS = [")) + 2
    ]
    assert '"deliveries",' not in fields
    assert '"audit",' not in fields
    assert "rows: state.deliveries," in patch
    assert "rows: state.audit," in patch
    assert 'requestedView === "deliveries"' in patch
    assert 'requestedView === "audit"' in patch

    # Backup overview placeholders are replaced from the last resolved
    # authenticated admin snapshot before the authoritative refresh completes.
    assert 'const QA_BACKUP_OVERVIEW_CACHE_KEY = "nowlert.backup-overview.v1";' in patch
    assert "function qaBackupOverviewSnapshot()" in patch
    assert "function qaSaveBackupOverviewCache()" in patch
    assert "function qaRestoreBackupOverviewCache(session)" in patch
    assert 'if (state.currentView === "backups") qaRestoreBackupOverviewCache(session);' in patch
    assert "Number(state.workspaceLoadedAt || 0) <= 0" in patch
    assert "renderBackupOverviewWithFirstPaintCache" in patch

def test_routing_flow_intentional_abort_does_not_flash_stale():
    acceptance = (ROOT / "src" / "webui" / "operations_acceptance.js").read_text(
        encoding="utf-8"
    )

    fetch_start = acceptance.index("window.fetch = async function operationsAcceptanceFetch")
    fetch_end = acceptance.index("const previousNavigate = navigate;", fetch_start)
    fetch_wrapper = acceptance[fetch_start:fetch_end]

    # Navigation intentionally aborts the warm Routing Flow request. That is not
    # a failed health refresh and must preserve the last successful Live state.
    assert 'if (error?.name !== "AbortError") flowLatestOk = false;' in fetch_wrapper
    assert 'catch (error) {\n      flowLatestOk = false;' not in fetch_wrapper
    assert "throw error;" in fetch_wrapper
