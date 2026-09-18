"""Read-only Routing Flow contract against the current CE access model."""
import json
import time

from test_route_destination_api import api, call, login, create_route, create_destination
from models import Notification
from storage.delivery import DeliveryResult


def snapshot(api, headers, window="15m"):
    return call(api, "GET", f"/api/v2/routing-flow/{window}", headers=headers)


def test_empty_snapshot_is_read_only_and_unrecorded_is_not_zero(api):
    headers = login(api)
    response = snapshot(api, headers)
    assert response.status == 200
    data = response.payload
    assert data["routes"] == []
    assert data["destinations"] == []
    assert data["metrics"] == {
        "received": 0,
        "filtered": 0,
        "delivered": 0,
        "pending": 0,
        "failed": 0,
    }
    assert data["capabilities"]["received"] is True
    assert data["capabilities"]["filtered"] is True
    assert call(api, "POST", "/api/v2/routing-flow/15m", {}, headers).status == 405
    assert snapshot(api, headers, "invalid").status == 400
    assert snapshot(api, {}).status == 401


def test_snapshot_reads_current_filters_without_writing_existing_configuration(api):
    headers = login(api)
    route = create_route(api, headers, "Grafana production")
    first = create_destination(api, headers, "Teams", [route["id"]])
    second = create_destination(api, headers, "Slack", [route["id"]])
    platform = api["service"].platform
    platform.filters.set_rules(
        api["admin"].actor,
        first["id"],
        "grafana",
        {"policy": [{"action": "allow", "conditions": {"alert_name": ["cpu*"]}}]},
    )
    platform.filters.set_rules(
        api["admin"].actor,
        second["id"],
        "grafana",
        {"policy": [{"action": "block", "conditions": {"alert_name": ["disk*"]}}]},
    )
    with api["database"].connect() as connection:
        before = list(connection.iterdump())

    data = snapshot(api, headers).payload
    assert len(data["routes"]) == 1
    assert len(data["links"]) == 2
    assert {link["destination_id"] for link in data["links"]} == {
        first["id"],
        second["id"],
    }
    actions = {
        link["policies"][0]["policy_rules"][0]["action"]
        for link in data["links"]
    }
    assert actions == {"allow", "block"}
    assert "secret" not in json.dumps(data).lower()
    assert "example.invalid" not in json.dumps(data)

    with api["database"].connect() as connection:
        after = list(connection.iterdump())
    persisted_tables = (
        "routes",
        "destinations",
        "route_destinations",
        "destination_filters",
        "settings_records",
    )
    keep = lambda lines: [
        line
        for line in lines
        if any(f'INSERT INTO "{table}"' in line for table in persisted_tables)
    ]
    assert keep(before) == keep(after)


def test_latest_delivery_outcomes_use_whole_window_not_only_history_page(api):
    headers = login(api)
    route = create_route(api, headers, "Grafana")
    target = create_destination(api, headers, "Ops", [route["id"]])
    platform = api["service"].platform
    stored_route = platform.routes.get(api["admin"].actor, route["id"])
    notification = Notification(source="grafana", title="Alert", status="critical")
    for index in range(105):
        platform.history.record(
            api["admin"].id,
            f"delivery-{index}",
            stored_route,
            notification,
            1,
            "delivered",
            DeliveryResult(True),
            destination_id=target["id"],
        )
    platform.history.record(
        api["admin"].id,
        "retry",
        stored_route,
        notification,
        1,
        "retry_scheduled",
        DeliveryResult(False, retryable=True),
        destination_id=target["id"],
    )
    platform.history.record(
        api["admin"].id,
        "retry",
        stored_route,
        notification,
        2,
        "delivered",
        DeliveryResult(True),
        destination_id=target["id"],
    )
    platform.history.record(
        api["admin"].id,
        "terminal",
        stored_route,
        notification,
        1,
        "failed",
        DeliveryResult(False, retryable=True),
        destination_id=target["id"],
    )
    data = snapshot(api, headers).payload
    assert data["metrics"]["delivered"] == 106
    assert data["metrics"]["pending"] == 0
    assert data["metrics"]["failed"] == 1
    assert data["destinations"][0]["metrics"]["delivered"] == 106
    assert len(data["history"]) == 30

    old = int(time.time()) - 2000
    with api["database"].transaction() as connection:
        connection.execute(
            "UPDATE delivery_attempts SET created_at = ?, completed_at = ?",
            (old, old),
        )
    assert snapshot(api, headers).payload["metrics"]["delivered"] == 0
    assert snapshot(api, headers, "1h").payload["metrics"]["delivered"] == 106


def test_private_destination_and_delivery_are_not_exposed_to_another_user(api):
    headers = login(api)
    route = create_route(api, headers, "Private route")
    destination = create_destination(api, headers, "Private destination", [route["id"]])
    platform = api["service"].platform
    platform.history.record(
        api["admin"].id,
        "private-delivery",
        platform.routes.get(api["admin"].actor, route["id"]),
        Notification(source="grafana", title="Private payload"),
        1,
        "delivered",
        DeliveryResult(True),
        destination_id=destination["id"],
    )
    user = platform.users.create("other-user", "other secure password")
    from api.routing_flow import snapshot as read_snapshot

    data = read_snapshot(platform, user.actor, "15m")
    assert data["destinations"] == []
    assert data["history"] == []
    assert data["metrics"]["delivered"] == 0


def test_admin_routing_flow_does_not_expose_user_private_delivery_contents(api):
    headers = login(api)
    platform = api["service"].platform
    route = create_route(api, headers, "Private owner route")
    stored_route = platform.routes.get(api["admin"].actor, route["id"])
    owner = platform.users.create("private-owner", "private owner secure password")
    private = platform.destinations.create(
        owner.actor,
        owner.id,
        "Private owner destination",
        "webhook",
        settings={"method": "POST"},
        shared=False,
    )
    platform.relationships.replace_for_destination(
        owner.actor, private.id, [route["id"]]
    )
    platform.history.record(
        owner.id,
        "user-private-delivery",
        stored_route,
        Notification(source="grafana", title="Do not expose me"),
        1,
        "delivered",
        DeliveryResult(True),
        destination_id=private.id,
    )

    data = snapshot(api, headers).payload
    encoded = json.dumps(data)
    assert private.id not in encoded
    assert "Do not expose me" not in encoded


def test_packaged_assets_load_after_current_webui_extensions():
    from test_webui import enabled_config
    from webui.service import WebUIService

    web = WebUIService(enabled_config())
    for name in ("routing_flow.js", "routing_flow.css"):
        response = web.response(f"/ui/{name}")
        assert response.status == 200
    html = web.response("/").body.decode()
    assert html.index('/ui/routing_flow.js') > html.index('/ui/acceptance_cleanup.js')


def test_shared_destination_visibility_does_not_expose_owner_private_filters(api):
    headers = login(api)
    route = create_route(api, headers, "Shared Grafana")
    unused = create_route(api, headers, "Unassigned", "proxmox")
    destination = create_destination(api, headers, "Shared", [route["id"]])
    platform = api["service"].platform
    actor = api["admin"].actor
    platform.filters.set_rules(
        actor,
        destination["id"],
        "grafana",
        {"policy": [{"action": "allow", "conditions": {"alert_name": ["cpu*"]}}]},
    )
    platform.filters.set_enabled(actor, destination["id"], "grafana", False)
    response = call(
        api,
        "PATCH",
        f'/api/v2/destinations/{destination["id"]}',
        {"shared": True},
        headers,
    )
    assert response.status == 200

    owner_view = snapshot(api, headers).payload
    assert next(
        item for item in owner_view["routes"] if item["id"] == unused["id"]
    )["destination_ids"] == []
    link = next(
        item
        for item in owner_view["links"]
        if item["destination_id"] == destination["id"]
    )
    assert link["enabled"] is True
    assert link["policies"][0]["configured"] is True
    assert link["policies"][0]["enabled"] is False

    other = platform.users.create("shared-reader", "other secure password")
    from api.routing_flow import snapshot as read_snapshot

    shared = read_snapshot(platform, other.actor, "15m")
    assert any(item["id"] == destination["id"] for item in shared["destinations"])
    shared_link = next(
        item
        for item in shared["links"]
        if item["destination_id"] == destination["id"]
    )
    policy = shared_link["policies"][0]
    assert policy["restricted"] is True
    assert "cpu*" not in json.dumps(shared_link)
    assert "Filter details private" in json.dumps(shared_link)


def test_fallback_source_reports_current_policy_without_mutating_filtering(api):
    headers = login(api)
    fallback = create_route(api, headers, "Fallback HTTP", "*")
    target = create_destination(api, headers, "Fallback target", [fallback["id"]])
    platform = api["service"].platform
    platform.filters.set_rules(
        api["admin"].actor,
        target["id"],
        "grafana",
        {"policy": [{"action": "block", "conditions": {"alert_name": ["cpu*"]}}]},
    )
    data = snapshot(api, headers).payload
    link = data["links"][0]
    assert link["fallback"] is True
    assert len(link["policies"]) > 1
    grafana = next(
        policy for policy in link["policies"] if policy["source"] == "grafana"
    )
    assert grafana["policy_rules"] == [
        {"action": "block", "conditions": {"alert_name": ["cpu*"]}}
    ]
    assert grafana["enabled"] is True
    assert any(not policy["configured"] for policy in link["policies"])



def test_filter_decisions_feed_received_filtered_and_reduction_metrics(api):
    headers = login(api)
    route = create_route(api, headers, "Grafana filtered")
    destination = create_destination(api, headers, "Filtered webhook", [route["id"]])
    platform = api["service"].platform
    platform.filters.set_rules(
        api["admin"].actor,
        destination["id"],
        "grafana",
        {"policy": [{"action": "allow", "conditions": {"severity": ["critical"]}}]},
    )

    blocked = platform.delivery.deliver(
        api["admin"].actor,
        Notification(
            source="grafana",
            title="Warning",
            metadata={"severity": "warning", "_input_type": "http"},
        ),
    )
    allowed = platform.delivery.deliver(
        api["admin"].actor,
        Notification(
            source="grafana",
            title="Critical",
            metadata={"severity": "critical", "_input_type": "http"},
        ),
    )

    assert blocked.matched_routes == 0
    assert allowed.matched_routes == 1
    with api["database"].connect() as connection:
        recorded = connection.execute(
            """
            SELECT route_id, destination_id, filtered
            FROM routing_flow_events
            WHERE route_id = ? AND destination_id = ?
            ORDER BY id
            """,
            (route["id"], destination["id"]),
        ).fetchall()
    assert [(row["filtered"]) for row in recorded] == [1, 0]
    data = snapshot(api, headers, "10m").payload
    link = next(
        item for item in data["links"]
        if item["route_id"] == route["id"]
        and item["destination_id"] == destination["id"]
    )
    assert link["metrics"]["received"] == 2
    assert link["metrics"]["filtered"] == 1
    assert link["metrics"]["delivered"] == 1
    assert data["metrics"]["received"] == 2
    assert data["metrics"]["filtered"] == 1
    filtered_history = [
        item for item in data["history"]
        if item["outcome"] == "filtered"
    ]
    assert len(filtered_history) == 1
    assert filtered_history[0]["route_id"] == route["id"]
    assert filtered_history[0]["destination_id"] == destination["id"]
    assert filtered_history[0]["source"] == "grafana"


def test_snapshot_exposes_one_filter_card_per_filtering_record(api):
    headers = login(api)
    grafana = create_route(api, headers, "Grafana filtered", source="grafana")
    zabbix = create_route(api, headers, "Zabbix filtered", source="zabbix")
    destination = create_destination(
        api,
        headers,
        "Shared filtered destination",
        [grafana["id"], zabbix["id"]],
    )
    platform = api["service"].platform
    platform.filters.set_rules(
        api["admin"].actor,
        destination["id"],
        "grafana",
        {
            "policy": [
                {
                    "action": "block",
                    "conditions": {
                        "severity": ["warning", "critical"],
                        "status": ["firing"],
                    },
                }
            ]
        },
    )
    platform.filters.set_rules(
        api["admin"].actor,
        destination["id"],
        "zabbix",
        {
            "policy": [
                {
                    "action": "block",
                    "conditions": {
                        "severity": ["warning", "high", "disaster"],
                        "status": ["failure"],
                    },
                }
            ]
        },
    )
    platform.filters.set_enabled(
        api["admin"].actor,
        destination["id"],
        "zabbix",
        False,
    )

    filtering_overview = platform._filters_overview(api["admin"].actor).payload
    filtering_record = next(
        item
        for item in filtering_overview["filters"]
        if item["destination_id"] == destination["id"]
    )

    first = snapshot(api, headers, "10m").payload
    assert len(first["filters"]) == 1
    filter_card = first["filters"][0]
    assert filter_card["id"] == f'{destination["id"]}:filter'
    assert filter_card["name"] == filtering_record["destination_name"]
    assert filter_card["destination_id"] == filtering_record["destination_id"]
    assert filter_card["configured_count"] == filtering_record["configured_count"]
    assert filter_card["active_count"] == filtering_record["active_count"]
    assert filter_card["sources"] == [
        item["source"] for item in filtering_record["integrations"]
    ]
    assert filter_card["active_sources"] == [
        item["source"]
        for item in filtering_record["integrations"]
        if item["filter_enabled"]
    ]
    assert set(filter_card["route_ids"]) == {grafana["id"], zabbix["id"]}
    assert filter_card["policies"] == filtering_record["integrations"]

    first_links = {
        item["route_id"]: item
        for item in first["links"]
        if item["destination_id"] == destination["id"]
    }
    assert first_links[grafana["id"]]["filter_ids"] == [
        f'{destination["id"]}:filter'
    ]
    assert first_links[grafana["id"]]["direct"] is False
    assert first_links[zabbix["id"]]["filter_ids"] == []
    assert first_links[zabbix["id"]]["direct"] is True

    # Editing the existing Filtering record updates the stable Routing Flow
    # card instead of appending another card or reconstructing stale sources.
    platform.filters.set_rules(
        api["admin"].actor,
        destination["id"],
        "grafana",
        {
            "policy": [
                {
                    "action": "block",
                    "conditions": {"severity": ["critical"]},
                }
            ]
        },
    )
    second = snapshot(api, headers, "10m").payload
    assert len(second["filters"]) == 1
    updated = second["filters"][0]
    assert updated["id"] == f'{destination["id"]}:filter'
    refreshed_overview = platform._filters_overview(api["admin"].actor).payload
    refreshed_record = next(
        item
        for item in refreshed_overview["filters"]
        if item["destination_id"] == destination["id"]
    )
    assert updated["policies"] == refreshed_record["integrations"]
    grafana_policy = next(
        policy for policy in updated["policies"] if policy["source"] == "grafana"
    )
    assert grafana_policy["policy_rules"] == [
        {"action": "block", "conditions": {"severity": ["critical"]}}
    ]


def test_routing_flow_supports_dashboard_history_windows(api):
    headers = login(api)
    for window in ("10m", "1h", "1d", "1m", "1y"):
        response = snapshot(api, headers, window)
        assert response.status == 200
        assert response.payload["range"] == window
