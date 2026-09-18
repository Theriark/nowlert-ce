import time

from models import Notification
from storage.routing_bridge import PlatformRoutingBridge
from storage.routing_flow import delivery_snapshot
from test_configuration_bridge import (
    RecordingAdapter,
    Registry,
    bridge_state,
)


def _activate_database_routing(state):
    actor = state["admin"].actor
    plan, _inventory, _warnings = state["bridge"].preview(actor)
    state["bridge"].activate(actor, plan.fingerprint)
    adapter = RecordingAdapter()
    bridge = PlatformRoutingBridge(
        state["database"],
        registry=Registry(adapter),
    )
    with state["database"].connect() as connection:
        route_id = str(connection.execute("SELECT id FROM routes").fetchone()["id"])
        destination_id = str(
            connection.execute("SELECT id FROM destinations").fetchone()["id"]
        )
    return actor, bridge, adapter, route_id, destination_id


def test_runtime_platform_bridge_records_real_filter_events_for_routing_flow(
    bridge_state,
):
    state = bridge_state
    actor, bridge, adapter, route_id, destination_id = _activate_database_routing(state)

    bridge.filters.set_rules(
        actor,
        destination_id,
        "dell_idrac",
        {
            "policy": [
                {
                    "action": "allow",
                    "conditions": {"severity": ["warning"]},
                }
            ]
        },
    )

    allowed = bridge.route(
        Notification(
            source="dell_idrac",
            title="Allowed warning",
            metadata={"host": "HOST-01", "severity": "warning"},
        )
    )
    blocked = bridge.route(
        Notification(
            source="dell_idrac",
            title="Blocked critical",
            metadata={"host": "HOST-01", "severity": "critical"},
        )
    )

    assert allowed.delivered == 1
    assert blocked.delivered == 0
    assert len(adapter.events) == 1

    with state["database"].connect() as connection:
        rows = connection.execute(
            """
            SELECT route_id, destination_id, filtered
            FROM routing_flow_events
            WHERE route_id = ? AND destination_id = ?
            ORDER BY id
            """,
            (route_id, destination_id),
        ).fetchall()
    assert [int(row["filtered"]) for row in rows] == [0, 1]

    snapshot = delivery_snapshot(
        state["database"],
        actor,
        int(time.time()) - 60,
    )
    metrics = snapshot["by_link"][(route_id, destination_id)]
    assert metrics["received"] == 2
    assert metrics["filtered"] == 1
    assert metrics["delivered"] == 1


def test_routing_flow_received_count_covers_pre_telemetry_deliveries(bridge_state):
    state = bridge_state
    actor, bridge, _adapter, route_id, destination_id = _activate_database_routing(state)

    result = bridge.route(
        Notification(
            source="dell_idrac",
            title="Existing delivered event",
            metadata={"host": "HOST-01", "severity": "warning"},
        )
    )
    assert result.delivered == 1

    # Simulate a delivery that predates Routing Flow filter telemetry.
    with state["database"].transaction() as connection:
        connection.execute("DELETE FROM routing_flow_events")

    snapshot = delivery_snapshot(
        state["database"],
        actor,
        int(time.time()) - 60,
    )
    metrics = snapshot["by_link"][(route_id, destination_id)]
    assert metrics["delivered"] == 1
    assert metrics["received"] == 1
    assert metrics["filtered"] == 0
