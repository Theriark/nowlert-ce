"""Read-only delivery and filter aggregates for the Routing Flow overview."""
from __future__ import annotations

import sqlite3
import time


def empty_metrics():
    return {
        "received": 0,
        "filtered": 0,
        "delivered": 0,
        "pending": 0,
        "failed": 0,
    }


def _telemetry_route_id(database, destination_id, notification):
    """Resolve the same first active Route candidate used by runtime expansion."""

    from integrations.catalog import canonical_source

    source = canonical_source(getattr(notification, "source", ""))
    metadata = getattr(notification, "metadata", None) or {}
    observed_input = str(metadata.get("_input_type") or "").strip().casefold()
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT routes.id, routes.source, routes.input_type
            FROM route_destinations
            JOIN routes ON routes.id = route_destinations.route_id
            WHERE route_destinations.destination_id = ?
              AND (routes.source = ? OR routes.source = '*')
            ORDER BY routes.priority, routes.name_normalized, routes.id
            """,
            (str(destination_id), source),
        ).fetchall()

    eligible = [
        row
        for row in rows
        if not str(row["input_type"] or "").strip()
        or str(row["input_type"] or "").strip().casefold() == observed_input
    ]
    specific = [row for row in eligible if str(row["source"]) != "*"]
    selected = (specific or eligible)
    return str(selected[0]["id"]) if selected else None


def record_destination_filter_decision(
    database,
    actor,
    destination_id,
    notification,
    matched,
    *,
    source_event_id=None,
    clock=time.time,
):
    """Record the filter decision at the filter boundary without payload data."""

    route_id = _telemetry_route_id(database, destination_id, notification)
    if route_id is None:
        return False
    now = int(clock())
    source = str(getattr(notification, "source", "") or "")[:64]
    try:
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO routing_flow_events(
                    owner_user_id, route_id, destination_id,
                    source, filtered, created_at, source_event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_event_id, destination_id) WHERE source_event_id IS NOT NULL DO NOTHING
                """,
                (
                    str(actor.user_id),
                    route_id,
                    str(destination_id),
                    source,
                    0 if matched else 1,
                    now,
                    source_event_id,
                ),
            )
            connection.execute(
                "DELETE FROM routing_flow_events WHERE created_at < ?",
                (now - 367 * 24 * 60 * 60,),
            )
    except sqlite3.DatabaseError:
        # Routing telemetry is observational and must never break delivery.
        return False
    return True


def _merge_metrics(target, values):
    for key in ("received", "filtered", "delivered", "pending", "failed"):
        target[key] += int(values.get(key, 0) or 0)
    target["last_activity_at"] = max(
        int(target.get("last_activity_at", 0) or 0),
        int(values.get("last_activity_at", 0) or 0),
    )


def delivery_snapshot(database, actor, since):
    """Aggregate delivered outcomes and filter decisions for one history window."""

    delivery_where = """
        a.created_at >= ? AND (
            a.owner_user_id = ? OR EXISTS (
                SELECT 1 FROM destinations AS visible_destination
                WHERE visible_destination.id = a.destination_id
                  AND visible_destination.shared = 1
            )
        )
    """
    event_where = """
        e.created_at >= ? AND (
            e.owner_user_id = ? OR EXISTS (
                SELECT 1 FROM destinations AS visible_destination
                WHERE visible_destination.id = e.destination_id
                  AND visible_destination.shared = 1
            )
        )
    """
    parameters = [int(since), actor.user_id]
    visible_deliveries = (
        f"SELECT a.* FROM delivery_attempts AS a WHERE {delivery_where}"
    )
    with database.connect() as connection:
        delivery_groups = connection.execute(
            f"""
            WITH visible AS ({visible_deliveries}), ranked AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY delivery_id, destination_id
                    ORDER BY attempt_number DESC, completed_at DESC, id DESC
                ) AS position FROM visible
            )
            SELECT route_id, destination_id,
                SUM(outcome = 'delivered') AS delivered,
                SUM(outcome = 'retry_scheduled') AS pending,
                SUM(outcome = 'failed') AS failed,
                MAX(completed_at) AS last_activity_at
            FROM ranked WHERE position = 1
            GROUP BY route_id, destination_id
            """,
            parameters,
        ).fetchall()
        filter_groups = connection.execute(
            f"""
            SELECT e.route_id, e.destination_id,
                COUNT(*) AS received,
                SUM(e.filtered = 1) AS filtered,
                MAX(e.created_at) AS last_activity_at
            FROM routing_flow_events AS e
            WHERE {event_where}
            GROUP BY e.route_id, e.destination_id
            """,
            parameters,
        ).fetchall()
        delivery_source_groups = connection.execute(
            f"""
            WITH visible AS ({visible_deliveries}), ranked AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY delivery_id, destination_id
                    ORDER BY attempt_number DESC, completed_at DESC, id DESC
                ) AS position FROM visible
            )
            SELECT destination_id, source,
                SUM(outcome = 'delivered') AS delivered,
                SUM(outcome = 'retry_scheduled') AS pending,
                SUM(outcome = 'failed') AS failed,
                MAX(completed_at) AS last_activity_at
            FROM ranked WHERE position = 1
            GROUP BY destination_id, source
            """,
            parameters,
        ).fetchall()
        filter_source_groups = connection.execute(
            f"""
            SELECT e.destination_id, e.source,
                COUNT(*) AS received,
                SUM(e.filtered = 1) AS filtered,
                MAX(e.created_at) AS last_activity_at
            FROM routing_flow_events AS e
            WHERE {event_where}
            GROUP BY e.destination_id, e.source
            """,
            parameters,
        ).fetchall()
        recent = connection.execute(
            f"{visible_deliveries} ORDER BY a.created_at DESC, a.id DESC LIMIT 30",
            parameters,
        ).fetchall()
        recent_filtered = connection.execute(
            f"""
            SELECT e.id, e.route_id, e.destination_id, e.source, e.created_at
            FROM routing_flow_events AS e
            WHERE {event_where}
              AND e.filtered = 1
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT 30
            """,
            parameters,
        ).fetchall()

        # Apply recipient visibility before sharing an identity across owners.
        receipt_cte = """WITH receipts AS (
            SELECT e.source_event_id, e.route_id, e.created_at
            FROM routing_flow_events e WHERE e.owner_user_id = ? OR EXISTS (
                SELECT 1 FROM destinations d WHERE d.id = e.destination_id AND d.shared = 1
            )
            UNION ALL
            SELECT a.source_event_id, a.route_id, a.created_at
            FROM delivery_attempts a WHERE a.owner_user_id = ? OR EXISTS (
                SELECT 1 FROM destinations d WHERE d.id = a.destination_id AND d.shared = 1
            )
        ), identified AS (
            SELECT source_event_id, route_id, MIN(created_at) AS received_at
            FROM receipts WHERE source_event_id IS NOT NULL
            GROUP BY source_event_id, route_id
        ) """
        receipt_parameters = (actor.user_id, actor.user_id, int(since), int(since))
        source_total = connection.execute(receipt_cte + """
            SELECT (SELECT COUNT(*) FROM (
                SELECT source_event_id FROM identified GROUP BY source_event_id
                HAVING MIN(received_at) >= ?
            )) AS received,
            EXISTS(SELECT 1 FROM receipts WHERE source_event_id IS NULL AND created_at >= ?) AS legacy
            """, receipt_parameters).fetchone()
        source_routes = connection.execute(receipt_cte + """
            SELECT route_id, COUNT(*) AS received, 0 AS legacy
            FROM identified WHERE received_at >= ? GROUP BY route_id
            UNION ALL
            SELECT DISTINCT route_id, 0 AS received, 1 AS legacy
            FROM receipts WHERE source_event_id IS NULL AND created_at >= ?
            """, receipt_parameters).fetchall()

    total = {**empty_metrics(), "last_activity_at": 0}
    by_route, by_destination, by_link, by_filter = {}, {}, {}, {}

    def add(route_id, destination_id, metrics):
        key = (route_id, destination_id)
        link = by_link.setdefault(
            key, {**empty_metrics(), "last_activity_at": 0}
        )
        _merge_metrics(link, metrics)
        for mapping, identity in (
            (by_route, route_id),
            (by_destination, destination_id),
        ):
            target = mapping.setdefault(
                identity, {**empty_metrics(), "last_activity_at": 0}
            )
            _merge_metrics(target, metrics)
        _merge_metrics(total, metrics)

    for row in delivery_groups:
        add(
            row["route_id"],
            row["destination_id"],
            {
                "delivered": row["delivered"],
                "pending": row["pending"],
                "failed": row["failed"],
                "last_activity_at": row["last_activity_at"],
            },
        )

    for row in filter_groups:
        add(
            row["route_id"],
            row["destination_id"],
            {
                "received": row["received"],
                "filtered": row["filtered"],
                "last_activity_at": row["last_activity_at"],
            },
        )

    def add_filter(destination_id, source, metrics):
        key = (str(destination_id), str(source))
        target = by_filter.setdefault(
            key, {**empty_metrics(), "last_activity_at": 0}
        )
        _merge_metrics(target, metrics)

    for row in delivery_source_groups:
        add_filter(
            row["destination_id"],
            row["source"],
            {
                "delivered": row["delivered"],
                "pending": row["pending"],
                "failed": row["failed"],
                "last_activity_at": row["last_activity_at"],
            },
        )

    for row in filter_source_groups:
        add_filter(
            row["destination_id"],
            row["source"],
            {
                "received": row["received"],
                "filtered": row["filtered"],
                "last_activity_at": row["last_activity_at"],
            },
        )

    def normalize_received(metrics):
        outcomes = (
            int(metrics.get("delivered", 0) or 0)
            + int(metrics.get("pending", 0) or 0)
            + int(metrics.get("failed", 0) or 0)
        )
        metrics["received"] = max(
            int(metrics.get("received", 0) or 0),
            int(metrics.get("filtered", 0) or 0),
            outcomes,
        )

    for metrics in by_link.values():
        normalize_received(metrics)
    for metrics in by_destination.values():
        normalize_received(metrics)
    for metrics in by_filter.values():
        normalize_received(metrics)
    # Source receipts cannot be inferred from destination delivery totals.
    total["received"] = None if source_total["legacy"] else int(source_total["received"])
    for metrics in by_route.values():
        metrics["received"] = 0
    for row in source_routes:
        metrics = by_route.setdefault(row["route_id"], {**empty_metrics(), "last_activity_at": 0})
        if row["legacy"]:
            metrics["received"] = None
        elif metrics["received"] is not None:
            metrics["received"] += int(row["received"])

    history_fields = (
        "id",
        "delivery_id",
        "route_id",
        "destination_id",
        "source",
        "input_type",
        "title",
        "outcome",
        "attempt_number",
        "created_at",
        "completed_at",
    )
    delivery_history = [
        {key: row[key] for key in history_fields}
        for row in recent
    ]
    filtered_history = [
        {
            "id": f"filtered:{row['id']}",
            "delivery_id": f"filtered:{row['id']}",
            "route_id": row["route_id"],
            "destination_id": row["destination_id"],
            "source": row["source"],
            "input_type": "",
            "title": "Filtered event",
            "outcome": "filtered",
            "attempt_number": 0,
            "created_at": row["created_at"],
            "completed_at": row["created_at"],
        }
        for row in recent_filtered
    ]
    history = sorted(
        [*delivery_history, *filtered_history],
        key=lambda item: (
            int(item.get("completed_at") or item.get("created_at") or 0),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )[:30]

    return {
        "metrics": {
            key: total[key]
            for key in ("received", "filtered", "delivered", "pending", "failed")
        },
        "by_route": by_route,
        "by_destination": by_destination,
        "by_link": by_link,
        "by_filter": by_filter,
        "history": history,
    }
