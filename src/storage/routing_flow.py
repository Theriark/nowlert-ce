"""Read-only delivery aggregates for the Routing Flow overview."""
from __future__ import annotations


def empty_metrics():
    return {"delivered": 0, "pending": 0, "failed": 0}


def delivery_snapshot(database, actor, since):
    """Aggregate the whole window using the current delivery-history boundary."""
    where = """
        a.created_at >= ? AND (
            a.owner_user_id = ? OR EXISTS (
                SELECT 1 FROM destinations AS visible_destination
                WHERE visible_destination.id = a.destination_id
                  AND visible_destination.shared = 1
            )
        )
    """
    parameters = [int(since), actor.user_id]
    visible = f"SELECT a.* FROM delivery_attempts AS a WHERE {where}"
    with database.connect() as connection:
        groups = connection.execute(
            f"""
            WITH visible AS ({visible}), ranked AS (
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
        recent = connection.execute(
            f"{visible} ORDER BY a.created_at DESC, a.id DESC LIMIT 30",
            parameters,
        ).fetchall()

    total = empty_metrics()
    by_route, by_destination, by_link = {}, {}, {}
    for row in groups:
        metrics = {key: int(row[key] or 0) for key in total}
        metrics["last_activity_at"] = int(row["last_activity_at"] or 0)
        by_link[(row["route_id"], row["destination_id"])] = metrics
        for mapping, identity in (
            (by_route, row["route_id"]),
            (by_destination, row["destination_id"]),
        ):
            target = mapping.setdefault(
                identity, {**empty_metrics(), "last_activity_at": 0}
            )
            for key in total:
                target[key] += metrics[key]
            target["last_activity_at"] = max(
                target["last_activity_at"], metrics["last_activity_at"]
            )
        for key in total:
            total[key] += metrics[key]

    # Whitelist operational fields; no credentials or arbitrary payload/metadata.
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
        "metrics": {"received": None, "filtered": None, **total},
        "by_route": by_route,
        "by_destination": by_destination,
        "by_link": by_link,
        "history": [
            {key: row[key] for key in history_fields}
            for row in recent
        ],
    }
