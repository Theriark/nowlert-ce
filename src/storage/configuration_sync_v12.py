"""Schema-12 compatibility adapters for legacy configuration synchronization.

The mounted-YAML synchronizer remains a compatibility surface while SQLite is
canonical. These method replacements translate old output/target route entries
into independent Routes plus route_destinations rows without re-introducing a
Destination column on Route records.
"""

from __future__ import annotations

import json
import time
import uuid

from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.validation import normalized_name


def _upsert_route(self, actor, spec):
    key = spec["key"]
    display, normalized = normalized_name(spec["name"], "route name")
    with self.database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM routes WHERE configuration_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            row = connection.execute(
                """
                SELECT routes.*
                FROM routes
                LEFT JOIN route_destinations
                  ON route_destinations.route_id = routes.id
                WHERE routes.configuration_key IS NULL
                  AND routes.owner_user_id = ?
                  AND routes.source = ?
                  AND route_destinations.destination_id = ?
                ORDER BY routes.priority, routes.created_at LIMIT 1
                """,
                (actor.user_id, spec["source"], spec["destination_id"]),
            ).fetchone()
        if row is None:
            row = connection.execute(
                """
                SELECT * FROM routes
                WHERE configuration_key IS NULL AND owner_user_id = ?
                  AND name_normalized = ?
                ORDER BY priority, created_at LIMIT 1
                """,
                (actor.user_id, normalized),
            ).fetchone()

    source = RouteStore._source(spec["source"])
    filters_json = RouteStore._filters(spec["filters"])
    now = int(time.time())
    if row is None:
        route_id = uuid.uuid4().hex
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO routes(
                    id, owner_user_id, name, name_normalized, source,
                    input_type, filters_json, priority, enabled,
                    created_at, updated_at, configuration_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    route_id,
                    actor.user_id,
                    display,
                    normalized,
                    source,
                    spec["input_type"],
                    filters_json,
                    spec["priority"],
                    1 if spec["enabled"] else 0,
                    now,
                    now,
                    key,
                ),
            )
    else:
        route_id = str(row["id"])
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE routes
                SET owner_user_id = ?, name = ?, name_normalized = ?,
                    source = ?, input_type = ?, filters_json = ?, priority = ?,
                    enabled = ?, updated_at = ?, configuration_key = ?
                WHERE id = ?
                """,
                (
                    actor.user_id,
                    display,
                    normalized,
                    source,
                    spec["input_type"],
                    filters_json,
                    spec["priority"],
                    1 if spec["enabled"] else 0,
                    now,
                    key,
                    route_id,
                ),
            )

    RouteDestinationStore(self.database).replace_for_route_compat(
        actor,
        route_id,
        spec["destination_id"],
    )
    return self._route_by_key(key)


def _route_by_key(self, key):
    with self.database.connect() as connection:
        row = connection.execute(
            "SELECT id FROM routes WHERE configuration_key = ?",
            (key,),
        ).fetchone()
    if row is None:
        raise KeyError("route not found")
    return RouteStore(self.database).get(
        self._configuration_actor_for_route(str(row["id"])),
        str(row["id"]),
    )


def _configuration_actor_for_route(self, route_id):
    with self.database.connect() as connection:
        row = connection.execute(
            "SELECT owner_user_id FROM routes WHERE id = ?",
            (str(route_id),),
        ).fetchone()
    if row is None:
        raise KeyError("route not found")
    from storage.ownership import Actor

    return Actor(str(row["owner_user_id"]), "user")


def _adopt_unmanaged(self, candidate, actor):
    adopted = 0
    outputs = candidate.setdefault("outputs", {})
    with self.database.connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM destinations
            WHERE configuration_key IS NULL AND owner_user_id = ?
            ORDER BY created_at
            """,
            (actor.user_id,),
        ).fetchall()
    adopted_targets = {}
    for row in rows:
        output_type = str(row["output_type"])
        group = outputs.setdefault(output_type, {"enabled": True})
        target = self._new_target(str(row["name"]), output_type, data=candidate)
        settings = json.loads(str(row["settings_json"]))
        secret = None
        if row["secret_id"]:
            secret = self._decode_secret_value(
                output_type,
                self.secrets.resolve(actor, str(row["secret_id"])),
            )
        group[target] = self._destination_entry(
            output_type,
            str(row["name"]),
            settings,
            bool(row["enabled"]),
            secret,
        )
        adopted_targets[str(row["id"])] = (output_type, target)
        adopted += 1

    if adopted_targets:
        routing = candidate.setdefault("routing", {})
        with self.database.connect() as connection:
            routes = connection.execute(
                """
                SELECT * FROM routes
                WHERE configuration_key IS NULL AND owner_user_id = ?
                ORDER BY priority, created_at
                """,
                (actor.user_id,),
            ).fetchall()
            bindings = {
                str(route["id"]): [
                    str(item["destination_id"])
                    for item in connection.execute(
                        """
                        SELECT destination_id FROM route_destinations
                        WHERE route_id = ? ORDER BY destination_id
                        """,
                        (str(route["id"]),),
                    ).fetchall()
                ]
                for route in routes
            }
        for row in routes:
            source = str(row["source"])
            for position, destination_id in enumerate(bindings.get(str(row["id"]), [])):
                destination = adopted_targets.get(destination_id)
                if destination is None:
                    continue
                route_name = str(row["name"])
                if position:
                    route_name = f"{route_name} ({position + 1})"
                routing.setdefault(source, {"outputs": []}).setdefault("outputs", []).append(
                    self._route_entry(
                        uuid.uuid4().hex[:16],
                        route_name,
                        destination[0],
                        destination[1],
                        str(row["input_type"] or ""),
                        json.loads(str(row["filters_json"])),
                        int(row["priority"]),
                        bool(row["enabled"]),
                    )
                )
                adopted += 1
    return adopted


def apply_configuration_sync_v12(service_class):
    """Install schema-12 adapters on the existing compatibility service."""

    service_class._upsert_route = _upsert_route
    service_class._route_by_key = _route_by_key
    service_class._configuration_actor_for_route = _configuration_actor_for_route
    service_class._adopt_unmanaged = _adopt_unmanaged
