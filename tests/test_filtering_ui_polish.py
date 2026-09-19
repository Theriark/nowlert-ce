"""Filtering overview and modal presentation regression tests."""

from __future__ import annotations

from pathlib import Path

from api.filtering import PlatformAPI
from api.security import hash_password
from storage.database import Database
from storage.destinations import DestinationStore
from storage.filtering import DestinationFilterStore, RoutingOnlyRouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


ROOT = Path(__file__).resolve().parents[1]


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x0c" * 16, iterations=1_000)


def test_filtering_overview_api_exposes_active_configured_rule_details(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(database, password_hasher=fast_hash)
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    secrets = SecretStore(database)
    destinations = DestinationStore(database)
    routes = RoutingOnlyRouteStore(database)
    filters = DestinationFilterStore(database)

    secret = secrets.create(
        admin.actor,
        admin.id,
        "Discord credential",
        "discord",
        "https://discord.com/api/webhooks/123/token",
    )
    target = destinations.create(
        admin.actor,
        admin.id,
        "CE Development - Discord",
        "discord",
        secret_id=secret.id,
        settings={"channel_name": "Development"},
    )
    routes.create(
        admin.actor,
        admin.id,
        "Zabbix Development",
        "zabbix",
        target.id,
        input_type="smtp",
        enabled=True,
    )
    routes.create(
        admin.actor,
        admin.id,
        "Grafana Development",
        "grafana",
        target.id,
        input_type="http",
        enabled=True,
    )
    filters.set_rules(
        admin.actor,
        target.id,
        "zabbix",
        {"severity": ["high", "disaster"], "host": ["prod-*"]},
    )

    api = PlatformAPI.__new__(PlatformAPI)
    api.filters = filters
    api.destinations = destinations
    response = api._resource_endpoint("GET", "/api/v2/filters", None, admin.actor)

    assert response.status == 200
    assert len(response.payload["filters"]) == 1
    policy = response.payload["filters"][0]
    assert policy["destination_id"] == target.id
    assert policy["sources"] == ["zabbix"]
    assert policy["configured_count"] == 1
    assert policy["unconfigured_integrations"] == [
        {"source": "grafana", "name": "Grafana"}
    ]
    assert len(policy["integrations"]) == 1
    integration = policy["integrations"][0]
    assert integration["source"] == "zabbix"
    assert integration["name"] == "Zabbix"
    assert integration["configured"] is True
    assert integration["rules"] == {
        "severity": ["high", "disaster"],
        "host": ["prod-*"],
    }
    labels = {field["key"]: field["label"] for field in integration["fields"]}
    assert labels["severity"] == "Severity"
    assert labels["host"] == "Host"


def test_filtering_webui_shows_active_filter_cards_and_reference_editor():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert "<th>Filters</th>" in script
    assert "filtering-overview-list" in script
    assert "filtering-overview-rule" in script
    assert 'title: values.join(", ")' in script
    assert ".filtering-overview-rule::after" in styles
    assert 'content: ": " attr(title);' in styles
    assert "overflow-wrap: anywhere;" in styles
    assert "white-space: normal;" in styles
    assert 'byId("page-title").textContent = VIEW_TITLES.filtering;' in script
    assert "width: min(1040px, calc(100vw - 2rem));" in styles
    assert "grid-template-columns: repeat(3, minmax(220px, 1fr));" in styles
    assert "justify-content: stretch;" in styles
    assert 'className: "filtering-expanded-cell"' in script
    assert "grid-template-columns: minmax(4.8rem, 6rem) minmax(8rem, 9.5rem) minmax(0, 1fr) auto;" in styles
    assert "sourceIcon(integration.source)" in script
    assert "filtering-switch" in script
    assert ".filtering-editor-identity" in styles
    assert "#filter-editor-step > .field-help" not in styles
    assert ".filtering-modal > section" in styles
    assert "background: var(--surface-solid);" in styles
    assert ".filtering-add-field-row .button" in styles
    assert "white-space: nowrap;" in styles
    assert "75%" not in script
    assert "25%" not in script


def test_filtering_overview_cards_top_align_and_space_rule_groups():
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert ".filtering-overview-integration {\n  align-content: start;\n  align-items: start;" in styles
    assert ".filtering-overview-copy { display: grid; gap: 0.45rem; min-width: 0; }" in styles
    assert ".filtering-overview-chips { display: flex; flex-wrap: wrap; column-gap: 0.2rem; row-gap: 0.28rem; min-width: 0; }" in styles
    assert '.filtering-overview-chips:has(> .filtering-overview-rule-value[aria-label^="Severity "]):has(> .filtering-overview-rule-value[aria-label^="Status "])::after {' in styles
    assert "margin-top: 0.16rem;" in styles


def test_filtering_overview_actions_have_clear_spacing():
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert ".filtering-table-actions { display: flex; gap: 0.65rem; justify-content: flex-end; }" in styles


def test_filtering_overview_final_polish_contract():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert "const active = integrations.length;" in script
    assert '`${active} active filter${active === 1 ? "" : "s"}`' in script
    assert 'actionButtonForFilter("✎ Configure", "manage-destination", policy.destination_id, "primary")' in script
    assert ".filtering-overview-integration:hover {" in styles
    assert '.filtering-source-icon[data-source-key="qnap"]' in styles
    assert '.filtering-source-icon[data-source-key="synology"]' in styles
    assert '.filtering-source-icon[data-source-key="unifi_network"]' in styles
    assert '.filtering-source-icon[data-source-key="dell_idrac"]' in styles
    assert ".filtering-table tbody td:first-child," in styles
    assert "vertical-align: top;" in styles


def test_filtering_overview_shows_only_active_filters_and_full_width_expand():
    script = (ROOT / "src" / "webui" / "filtering.js").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")

    assert "function filterOverviewUnconfiguredIntegration(integration)" not in script
    assert 'text: "No filter · All notifications"' not in script
    assert 'dataset: { filterOverviewToggle: policy.destination_id }' in script
    assert 'className: "filtering-expanded-row"' in script
    assert 'attributes: { colspan: "6" }' in script
    assert 'detailRow.hidden = !expanded;' in script
    assert 'return badge("Active", "success");' in script
    assert '.filter((policy) => Array.isArray(policy.integrations) && policy.integrations.length > 0)' in script
    assert "unconfiguredIntegrations.forEach" not in script
    assert 'configured ? "Filter off" : "No filter / All notifications"' in script
    assert 'toast(enabled ? "Filter enabled." : "Filter disabled; saved rules were kept.", "success");' in script
    assert '.filtering-overview-header[aria-expanded="true"]::after' in styles
    assert "font-size: 0.6rem;" in styles


def test_shared_modal_shell_has_consistent_inner_spacing():
    professional = (ROOT / "src" / "webui" / "professional.css").read_text(encoding="utf-8")
    filtering_styles = (ROOT / "src" / "webui" / "filtering.css").read_text(encoding="utf-8")
    index = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")

    assert ".modal {\n  padding: 1.4rem;\n}" in professional
    assert ".modal > form,\n.modal > div,\n.modal > p,\n.modal > .secret-value {" in professional
    assert "  margin-left: 0;\n  margin-right: 0;" in professional
    assert ".modal > form {\n  margin-bottom: 0;\n  margin-top: 0;\n}" in professional
    assert ".filtering-modal > section { margin: 0; }" in filtering_styles
    assert ".filtering-modal-heading { margin-bottom: 1.2rem; }" in filtering_styles
    assert 'id="secret-dialog" class="modal small-modal"' in index
