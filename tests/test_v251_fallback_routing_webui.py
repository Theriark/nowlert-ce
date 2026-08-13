"""v2.5.1 fallback-only routing, filter, migration, and WebUI contract."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from api.config_service import ConfigService
from api.security import hash_password
from models import Notification
from storage.configuration_bridge import ConfigurationBridgeService
from storage.configuration_sync import UnifiedConfigurationService
from storage.database import Database
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "correct horse battery staple"


class Configuration:
    def __init__(self, path: Path):
        self.path = path
        self.reload()

    def reload(self):
        self.data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x51" * 16, iterations=1_000)


def database_with_admin(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    assert database.migrate() == 9
    admin = UserStore(database, password_hasher=fast_hash).bootstrap_admin(
        "administrator", PASSWORD
    )
    return database, admin.actor


def notification(source="dell_idrac", input_type="redfish", **metadata):
    item = Notification()
    item.source = source
    item.title = "Infrastructure alert"
    item.status = metadata.pop("status", "active")
    item.metadata = {"_input_type": input_type, **metadata}
    return item


def test_specific_routes_suppress_wildcard_fallback(tmp_path):
    database, actor = database_with_admin(tmp_path)
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    idrac = destinations.create(
        actor, actor.user_id, "iDRAC alerts", "discord", settings={}, enabled=True
    )
    default = destinations.create(
        actor, actor.user_id, "Default alerts", "discord", settings={}, enabled=True
    )
    specific = routes.create(
        actor,
        actor.user_id,
        "Dell iDRAC",
        "dell_idrac",
        idrac.id,
        input_type="redfish",
        priority="normal",
    )
    routes.create(
        actor,
        actor.user_id,
        "Fallback Redfish",
        "*",
        default.id,
        input_type="redfish",
        priority="lowest",
    )

    matched = routes.matching(actor, actor.user_id, notification())
    assert [route.id for route in matched] == [specific.id]

    unmatched = routes.matching(
        actor,
        actor.user_id,
        notification(source="custom_hardware", input_type="redfish"),
    )
    assert len(unmatched) == 1
    assert unmatched[0].destination_id == default.id
    assert unmatched[0].source == "*"


def test_smtp_fallback_matches_generic_smtp_only(tmp_path):
    database, actor = database_with_admin(tmp_path)
    destination = DestinationStore(database).create(
        actor,
        actor.user_id,
        "Default SMTP alerts",
        "discord",
        settings={},
        enabled=True,
    )
    routes = RouteStore(database)
    fallback = routes.create(
        actor,
        actor.user_id,
        "Fallback SMTP",
        "*",
        destination.id,
        input_type="smtp",
        priority="lowest",
    )

    matched = routes.matching(
        actor,
        actor.user_id,
        notification(source="generic", input_type="smtp"),
    )
    assert [route.id for route in matched] == [fallback.id]

    assert routes.matching(
        actor,
        actor.user_id,
        notification(source="generic", input_type="http"),
    ) == []


def test_matching_routes_deliver_only_once_per_destination(tmp_path):
    database, actor = database_with_admin(tmp_path)
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    target = destinations.create(
        actor, actor.user_id, "iDRAC alerts", "discord", settings={}, enabled=True
    )
    first = routes.create(
        actor,
        actor.user_id,
        "All iDRAC",
        "dell_idrac",
        target.id,
        input_type="redfish",
        priority="high",
    )
    routes.create(
        actor,
        actor.user_id,
        "Critical iDRAC",
        "dell_idrac",
        target.id,
        input_type="redfish",
        filters={"severities": ["critical"]},
        priority="normal",
    )

    matched = routes.matching(
        actor,
        actor.user_id,
        notification(severity="critical"),
    )
    assert [route.id for route in matched] == [first.id]


def test_exclude_route_filters_win_over_include_filters(tmp_path):
    database, actor = database_with_admin(tmp_path)
    destinations = DestinationStore(database)
    routes = RouteStore(database)
    target = destinations.create(
        actor, actor.user_id, "Operations", "discord", settings={}, enabled=True
    )
    route = routes.create(
        actor,
        actor.user_id,
        "Production alerts",
        "zabbix",
        target.id,
        input_type="http",
        filters={
            "hosts": ["server-*"],
            "exclude_hosts": ["server-test-*"],
            "exclude_events": ["heartbeat*"],
        },
    )
    assert RouteStore.matches(
        route,
        notification(
            source="zabbix",
            input_type="http",
            host="server-01",
            event_name="Disk failure",
        ),
    )
    assert not RouteStore.matches(
        route,
        notification(
            source="zabbix",
            input_type="http",
            host="server-test-01",
            event_name="Disk failure",
        ),
    )
    assert not RouteStore.matches(
        route,
        notification(
            source="zabbix",
            input_type="http",
            host="server-01",
            event_name="Heartbeat check",
        ),
    )


def test_xo_outcome_switches_migrate_to_route_status_filters(tmp_path):
    path = tmp_path / "config" / "config.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "platform": {
                    "enabled": True,
                    "state_dir": str(tmp_path / "state"),
                    "configuration_model": "unified_yaml_v1",
                },
                "webui": {"enabled": True},
                "outputs": {
                    "discord": {
                        "enabled": True,
                        "xo": {
                            "name": "XO alerts",
                            "enabled": True,
                            "shared": True,
                            "webhook": "https://discord.com/api/webhooks/123/private",
                        },
                    }
                },
                "routing": {
                    "xo": {
                        "outputs": [
                            {
                                "name": "Xen Orchestra",
                                "input": "smtp",
                                "output": "discord",
                                "target": "xo",
                                "enabled": True,
                            }
                        ]
                    }
                },
                "notifications": {
                    "xo": {
                        "success": False,
                        "skipped": True,
                        "failure": True,
                        "show_ids": False,
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)
    database, _actor = database_with_admin(tmp_path)
    service = UnifiedConfigurationService(
        ConfigService(path, Configuration(path)), database
    )
    status = service.synchronize(force=True)
    assert status.ready, status.errors

    with database.connect() as connection:
        route_row = connection.execute(
            "SELECT filters_json FROM routes WHERE source = 'xo'"
        ).fetchone()
        setting_row = connection.execute(
            """
            SELECT value_json FROM settings_records
            WHERE namespace = 'integration' AND setting_key = 'xo'
            """
        ).fetchone()
    assert json.loads(route_row["filters_json"])["statuses"] == [
        "skipped",
        "failure",
    ]
    assert json.loads(setting_row["value_json"]) == {"show_ids": False}


def test_webui_uses_normalized_inputs_and_clickable_destination_states():
    script = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    markup = (ROOT / "src/webui/index.html").read_text(encoding="utf-8")
    css = (ROOT / "src/webui/enhancements.css").read_text(encoding="utf-8")

    assert "SOURCE_TRANSPORTS" not in script
    assert "events received through" not in script
    assert 'text: item.enabled ? "Enabled" : "Disabled"' in script
    assert 'action: "toggle-destination-shared"' in script
    assert "Credentials set" not in script
    assert "Credentials required" in script
    assert "Last test passed" in script
    assert "Event API tokens" in markup
    assert 'id="token-sources" multiple' in markup
    assert "Exclude hosts or devices" in markup
    assert "exclude_hosts" in script
    assert ".resource-card-heading" in css


def test_overview_flow_uses_independent_input_route_and_destination_states():
    script = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src/webui/styles.css").read_text(encoding="utf-8")

    assert 'symbols = { active: "➜", disabled: "⊘︎", error: "✕" }' in script
    assert "inputFlowState" in script
    assert "routeFlowState" in script
    assert "destinationFlowState" in script
    assert "flowSignal(firstStatus" in script
    assert "flowSignal(destinationStatus.state" in script
    assert "source-${inputStatus.state}" in script
    assert ".flow-row.source-active" in styles
    assert ".flow-row.source-disabled" in styles
    assert ".flow-row.source-error" in styles
    assert ".flow-arrow.flow-disabled" in styles
    assert ".flow-arrow.flow-error" in styles


def test_input_inventory_uses_only_normalized_operator_names():
    inventory = ConfigurationBridgeService._inputs(
        {
            "smtp": {"enabled": True, "host": "0.0.0.0", "port": 8025},
            "http": {"enabled": True, "host": "0.0.0.0", "port": 8080},
            "home_assistant": {"enabled": True},
            "unifi": {"enabled": True},
        }
    )
    assert [(item["name"], item["label"]) for item in inventory] == [
        ("smtp", "SMTP"),
        ("http", "HTTP"),
        ("redfish", "Redfish"),
    ]
    assert inventory[2]["enabled"] is True
    assert inventory[2]["details"] == {"transport": "HTTP"}


def test_settings_cards_have_clear_vertical_spacing():
    styles = (ROOT / "src/webui/styles.css").read_text(encoding="utf-8")
    assert ".settings-card + .settings-card" in styles
    assert "margin-top: 1.25rem" in styles


def test_integration_settings_list_has_heading_spacing():
    styles = (ROOT / "src/webui/enhancements.css").read_text(
        encoding="utf-8"
    )
    assert "#integration-settings-list {" in styles
    assert "margin-top: 1.5rem" in styles



def test_nce21_nce36_nce37_nce38_route_filter_ui():
    script = (ROOT / "src/webui/app.js").read_text(
        encoding="utf-8"
    )
    markup = (ROOT / "src/webui/index.html").read_text(
        encoding="utf-8"
    )
    patch = (ROOT / "src/webui/qa_patch.js").read_text(
        encoding="utf-8"
    )
    styles = (ROOT / "src/webui/qa_patch.css").read_text(
        encoding="utf-8"
    )
    layout_styles = (
        ROOT / "src/webui/enhancements.css"
    ).read_text(
        encoding="utf-8"
    )

    # NCE-21: complete enumerated filters are neutral and collapse to
    # All Events when no other restriction remains.
    assert "const ROUTE_ALL_EVENT_FILTERS = {" in script
    assert (
        'function routeFilterHasAllEvents(key, values, source = "")'
        in script
    )
    assert 'return parts.join(" · ") || "All Events";' in script
    assert 'return "Just Critical";' in script
    assert 'parts.unshift("All Events")' not in script

    # NCE-36: severity/status exclusions are no longer separate fields.
    assert "<span>Included severities</span>" in markup
    assert "<span>Included statuses</span>" in markup
    assert "<span>Exclude severities</span>" not in markup
    assert "<span>Exclude statuses</span>" not in markup
    assert 'id="route-exclude_severities"' not in markup
    assert 'id="route-exclude_statuses"' not in markup

    # Legacy include/exclude records are converted into their effective
    # allow-list before editing, then saved using include-only filters.
    assert "function routeAllowedFilterValues(" in script
    assert 'filters = {},' in script
    assert 'source = "",' in script
    assert 'const excludedKey = `exclude_${key}`;' in script
    assert 'for (const key of ["severities", "statuses"]) {' in script
    assert "Select at least one included" in script

    # NCE-39: the selected integration source owns the exact route
    # severity/status vocabulary. The input transport is not part of
    # the lookup, so Zabbix SMTP and HTTP share one definition.
    assert (
        'function routeFilterValuesForSource(source = "", key)'
        in script
    )
    assert "integration.route_filters" in script
    assert "function routeSelectedSource()" in script
    assert "function refreshRouteFilterOptions(filters = {})" in script
    assert "currentRouteFilterSelections()" in script
    assert 'sourceSelect.dataset.routeFilterSource = source;' in script
    assert "previousSource === nextSource" in script
    assert "field.hidden = values.length === 0;" in script
    assert "select.disabled = values.length === 0;" in script
    assert "const selectedSource = routeSelectedSource();" in script
    assert "const available = routeFilterValuesForSource(" in script
    assert "if (!available.length) continue;" in script

    # NCE-39 Development polish: show every available enum value and
    # pack the remaining route controls beside tall listboxes instead
    # of inheriting the height of one oversized grid row.
    assert "select.size = Math.max(values.length, 2);" in script
    assert "function refreshRouteFilterLayout()" in script
    assert "function scheduleRouteFilterLayout()" in script
    assert 'grid.style.gridAutoFlow = "row dense";' in script
    assert 'grid.style.gridAutoRows = "4px";' in script
    assert 'field.style.gridRowEnd = `span ${span}`;' in script
    assert "scheduleRouteFilterLayout();" in script
    assert "grid-auto-flow: row dense;" in layout_styles
    assert ".route-filter-grid > label {" in layout_styles
    assert "align-self: start;" in layout_styles
    assert (
        "filterSummary(route.filters, route.source)"
        in script
    )
    assert (
        "filterSummary(item.filters, item.source)"
        in script
    )
    assert 'severities: "All Severities"' in script
    assert 'statuses: "All Statuses"' in script

    # The generic global option list is no longer baked into the form.
    assert (
        '<select id="route-severities" multiple size="6"></select>'
        in markup
    )
    assert (
        '<select id="route-statuses" multiple size="7"></select>'
        in markup
    )

    # NCE-37: selected options retain the same system highlight even
    # when the listbox is not focused.
    assert "qaRefreshRouteChoiceColors" not in patch
    assert '"qa-route-included"' not in patch
    assert '"qa-route-excluded"' not in patch
    assert "#route-severities option:checked" in styles
    assert "#route-statuses option:checked" in styles
    assert "background: Highlight !important;" in styles
    assert "color: HighlightText !important;" in styles
    assert "Green options are included" not in markup
    assert "Existing selections stay highlighted" in markup

    # NCE-38: ordinary mouse interaction is owned from mousedown so
    # existing options never disappear temporarily.
    assert "function qaRouteChoiceValues(select)" in patch
    assert "function qaApplyRouteChoiceValues(select, values)" in patch
    assert "function qaRouteChoiceOption(event)" in patch
    assert "function qaBindRouteChoiceList(selectId)" in patch

    choice_block = patch.split(
        "function qaBindRouteChoiceList(selectId)",
        1,
    )[1].split(
        "function qaAddSelectActions",
        1,
    )[0]

    assert 'select.addEventListener("mousedown"' in choice_block
    assert 'select.addEventListener("mousemove"' in choice_block
    assert 'document.addEventListener("mouseup"' in choice_block
    assert 'select.addEventListener("click"' in choice_block

    # Ordinary mouse selection is intercepted before the browser can
    # collapse the existing multiple-selection state.
    assert "event.preventDefault();" in choice_block
    assert "select.focus({ preventScroll: true });" in choice_block
    assert "suppressClick" in choice_block

    # Normal click toggles only the clicked option.
    assert "if (snapshot.selected)" in choice_block
    assert "values.delete(snapshot.option.value);" in choice_block
    assert "values.add(snapshot.option.value);" in choice_block

    # Drag adds a contiguous range while preserving the original set.
    assert "pointer.dragged = true;" in choice_block
    assert "const first = Math.min(" in choice_block
    assert "const last = Math.max(" in choice_block
    assert "values.add(candidate.value);" in choice_block
    assert "const values = new Set(pointer.values);" in choice_block

    # Modifier-assisted native selection remains available.
    assert "event.ctrlKey" in choice_block
    assert "event.metaKey" in choice_block
    assert "event.shiftKey" in choice_block
    assert "snapshot.nativeOnly" not in choice_block

    assert 'new Event("change", { bubbles: true })' in choice_block
    assert "Drag across options to add a range" in markup

    # The old two-list conflict machinery is intentionally gone.
    assert "qaSyncRouteFilterPair" not in patch
    assert "qaSyncAllRouteFilterPairs" not in patch
    assert "qaBindRouteFilterPair" not in patch
