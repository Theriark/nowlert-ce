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
                    source, filtered, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(actor.user_id),
                    route_id,
                    str(destination_id),
                    source,
                    0 if matched else 1,
                    now,
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

    total = {**empty_metrics(), "last_activity_at": 0}
    by_route, by_destination, by_link = {}, {}, {}

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
    for metrics in by_route.values():
        normalize_received(metrics)
    for metrics in by_destination.values():
        normalize_received(metrics)
    normalize_received(total)

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
        "history": history,
    }
