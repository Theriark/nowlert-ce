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


def record_filter_decisions(
    database,
    actor,
    notification,
    decisions,
    *,
    clock=time.time,
):
    """Record only route/destination filter outcomes; never persist event payloads."""

    items = list(decisions)
    if not items:
        return True
    now = int(clock())
    source = str(getattr(notification, "source", "") or "")[:64]
    rows = [
        (
            str(actor.user_id),
            str(candidate.route.id),
            str(candidate.destination_id),
            source,
            0 if matched else 1,
            now,
        )
        for candidate, matched in items
    ]
    try:
        with database.transaction() as connection:
            # Keep the write path self-healing for installations upgraded from
            # a failed or interrupted schema transition. Telemetry must never
            # block notification delivery.
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS routing_flow_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner_user_id TEXT NOT NULL,
                    route_id TEXT NOT NULL,
                    destination_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    filtered INTEGER NOT NULL DEFAULT 0 CHECK (filtered IN (0, 1)),
                    created_at INTEGER NOT NULL
                )
                """
            )
            for row in rows:
                connection.execute(
                    """
                    INSERT INTO routing_flow_events(
                        owner_user_id, route_id, destination_id,
                        source, filtered, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
            connection.execute(
                "DELETE FROM routing_flow_events WHERE created_at < ?",
                (now - 367 * 24 * 60 * 60,),
            )
    except sqlite3.DatabaseError:
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
    return {
        "metrics": {
            key: total[key]
            for key in ("received", "filtered", "delivered", "pending", "failed")
        },
        "by_route": by_route,
        "by_destination": by_destination,
        "by_link": by_link,
        "history": [
            {key: row[key] for key in history_fields}
            for row in recent
        ],
    }
