"""Many-to-many assignment of reusable Routes to delivery Destinations."""

from __future__ import annotations

import json
import time

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from integrations.catalog import canonical_source
from models import Notification
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.destinations import DeliveryDestination, DestinationStore
from storage.ownership import Actor, OwnershipPolicy

if TYPE_CHECKING:
    from storage.routes import Route


_FILTER_STATE_NAMESPACE = "destination_filter_enabled"


@dataclass(frozen=True)
class RouteDestinationCandidate:
    """One matched Route resolved to one concrete Destination."""

    route: "Route"
    destination_id: str
    target: DeliveryDestination | None = None


class RouteDestinationStore:
    """Persist and resolve the relationship between Routes and Destinations."""

    def __init__(
        self,
        database: Database,
        *,
        audit: AuditEventStore | None = None,
        clock=time.time,
    ):
        self.database = database
        self.audit = audit
        self.clock = clock

    def route_ids_for_destination(
        self,
        actor: Actor,
        destination_id: str,
    ) -> tuple[str, ...]:
        destination = self._destination(actor, destination_id, write=False)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT routes.id
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE route_destinations.destination_id = ?
                ORDER BY routes.priority, routes.name_normalized, routes.id
                """,
                (str(destination["id"]),),
            ).fetchall()
        return tuple(str(row["id"]) for row in rows)

    def destination_ids_for_route(
        self,
        actor: Actor,
        route_id: str,
    ) -> tuple[str, ...]:
        route = self._route(actor, route_id, write=False)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT destinations.id
                FROM route_destinations
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE route_destinations.route_id = ?
                ORDER BY destinations.name_normalized, destinations.id
                """,
                (str(route["id"]),),
            ).fetchall()
        return tuple(str(row["id"]) for row in rows)

    def replace_for_destination(
        self,
        actor: Actor,
        destination_id: str,
        route_ids: Iterable[str],
    ) -> tuple[str, ...]:
        destination, normalized = self.validate_for_destination(
            actor,
            destination_id,
            route_ids,
        )
        destination_id = str(destination["id"])
        previous = self.route_ids_for_destination(actor, destination_id)
        now = int(self.clock())
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM route_destinations WHERE destination_id = ?",
                (destination_id,),
            )
            for route_id in normalized:
                connection.execute(
                    """
                    INSERT INTO route_destinations(route_id, destination_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (route_id, destination_id, now),
                )
            if not normalized:
                configured = connection.execute(
                    "SELECT source FROM destination_filters WHERE destination_id = ?",
                    (destination_id,),
                ).fetchall()
                for row in configured:
                    state_key = f"{destination_id}:{str(row['source'])}"
                    connection.execute(
                        """
                        INSERT INTO settings_records(
                            namespace, setting_key, value_json, updated_at
                        ) VALUES (?, ?, 'false', ?)
                        ON CONFLICT(namespace, setting_key) DO UPDATE SET
                            value_json = excluded.value_json,
                            updated_at = excluded.updated_at
                        """,
                        (_FILTER_STATE_NAMESPACE, state_key, now),
                    )
        added = [item for item in normalized if item not in previous]
        removed = [item for item in previous if item not in normalized]
        self._audit(
            actor,
            "destination.routes_update",
            destination_id,
            {"added_route_ids": added, "removed_route_ids": removed},
        )
        return normalized

    def validate_for_destination(
        self,
        actor: Actor,
        destination_id: str,
        route_ids: Iterable[str],
    ):
        destination = self._destination(actor, destination_id, write=True)
        if isinstance(route_ids, (str, bytes)) or route_ids is None:
            raise ValueError("route_ids must be a list")
        try:
            normalized = tuple(
                dict.fromkeys(str(item).strip() for item in route_ids if str(item).strip())
            )
        except TypeError as error:
            raise ValueError("route_ids must be a list") from error
        for route_id in normalized:
            route = self._route(actor, route_id, write=False)
            if not actor.is_admin and str(route["owner_user_id"]) != actor.user_id:
                raise PermissionError("route cannot be assigned by this user")
            if (
                str(route["owner_user_id"]) != str(destination["owner_user_id"])
                and not bool(destination["shared"])
            ):
                raise PermissionError(
                    "route destination must be owned by the route owner or shared"
                )
        return destination, normalized

    def replace_for_route_compat(
        self,
        actor: Actor,
        route_id: str,
        destination_id: str | None,
    ) -> tuple[str, ...]:
        route = self._route(actor, route_id, write=True)
        current = self.destination_ids_for_route(actor, route_id)
        if len(current) > 1:
            raise ValueError(
                "legacy destination_id cannot replace a route with multiple destinations"
            )
        if destination_id in (None, ""):
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM route_destinations WHERE route_id = ?",
                    (str(route_id),),
                )
            return ()
        with self.database.connect() as connection:
            destination = connection.execute(
                """
                SELECT id, owner_user_id, shared, enabled
                FROM destinations WHERE id = ?
                """,
                (str(destination_id),),
            ).fetchone()
        if destination is None:
            raise KeyError("destination not found")
        if (
            str(route["owner_user_id"]) != str(destination["owner_user_id"])
            and not bool(destination["shared"])
        ):
            raise PermissionError(
                "route destination must be owned by the user or shared"
            )
        now = int(self.clock())
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM route_destinations WHERE route_id = ?",
                (str(route_id),),
            )
            connection.execute(
                """
                INSERT INTO route_destinations(route_id, destination_id, created_at)
                VALUES (?, ?, ?)
                """,
                (str(route_id), str(destination_id), now),
            )
        return (str(destination_id),)

    def resolve_matching(
        self,
        actor: Actor,
        owner_user_id: str,
        notification: Notification,
    ) -> list[RouteDestinationCandidate]:
        """Resolve matching Routes and delivery Destinations in one SQLite read."""

        # Import lazily to keep the existing routes -> route_destinations
        # dependency acyclic at module import time.
        from storage.routes import Route, RouteStore

        OwnershipPolicy.require_read(actor, str(owner_user_id))
        source = canonical_source(notification.source)

        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    routes.id AS route_id,
                    routes.owner_user_id AS route_owner_user_id,
                    routes.name AS route_name,
                    routes.source AS route_source,
                    routes.input_type AS route_input_type,
                    routes.filters_json AS route_filters_json,
                    routes.priority AS route_priority,
                    routes.enabled AS route_enabled,
                    routes.created_at AS route_created_at,
                    routes.updated_at AS route_updated_at,
                    destinations.*
                FROM routes
                JOIN users
                  ON users.id = routes.owner_user_id
                LEFT JOIN route_destinations
                  ON route_destinations.route_id = routes.id
                LEFT JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE routes.owner_user_id = ?
                  AND routes.enabled = 1
                  AND users.enabled = 1
                  AND (routes.source = ? OR routes.source = '*')
                ORDER BY
                    routes.priority,
                    routes.name_normalized,
                    destinations.name_normalized,
                    destinations.id
                """,
                (str(owner_user_id), source),
            ).fetchall()

        grouped = {}
        for row in rows:
            route_id = str(row["route_id"])
            group = grouped.setdefault(
                route_id,
                {
                    "route_row": row,
                    "destination_rows": [],
                },
            )
            if row["id"] is not None:
                group["destination_rows"].append(row)

        route_entries = []
        for route_id, group in grouped.items():
            row = group["route_row"]
            destination_rows = group["destination_rows"]
            decoded = json.loads(str(row["route_filters_json"]))
            route = Route(
                id=route_id,
                owner_user_id=str(row["route_owner_user_id"]),
                name=str(row["route_name"]),
                source=str(row["route_source"]),
                filters={
                    key: tuple(values)
                    for key, values in decoded.items()
                },
                priority=int(row["route_priority"]),
                enabled=bool(row["route_enabled"]),
                created_at=int(row["route_created_at"]),
                updated_at=int(row["route_updated_at"]),
                input_type=str(row["route_input_type"] or ""),
                destination_ids=tuple(
                    str(destination_row["id"])
                    for destination_row in destination_rows
                ),
            )
            route_entries.append((route, destination_rows))

        matched = [
            entry
            for entry in route_entries
            if RouteStore.matches(entry[0], notification)
        ]

        # Preserve RouteStore.matching() fallback semantics: source-specific
        # routes suppress wildcard routes whenever at least one specific route
        # matches the notification.
        specific = [
            entry
            for entry in matched
            if entry[0].source != "*"
        ]
        selected = (
            specific
            if specific
            else [
                entry
                for entry in matched
                if entry[0].source == "*"
            ]
        )

        result: list[RouteDestinationCandidate] = []
        seen_destinations: set[str] = set()
        for route, destination_rows in selected:
            if str(route.owner_user_id) != actor.user_id and not actor.is_admin:
                continue
            for row in destination_rows:
                if not bool(row["enabled"]):
                    continue
                destination_id = str(row["id"])
                if destination_id in seen_destinations:
                    continue
                seen_destinations.add(destination_id)
                result.append(
                    RouteDestinationCandidate(
                        route,
                        destination_id,
                        DestinationStore._delivery_destination(row),
                    )
                )
        return result

    def expand(
        self,
        actor: Actor,
        routes: Iterable["Route"],
    ) -> list[RouteDestinationCandidate]:
        result: list[RouteDestinationCandidate] = []
        seen_destinations: set[str] = set()
        for route in routes:
            if str(route.owner_user_id) != actor.user_id and not actor.is_admin:
                continue
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT destinations.*
                    FROM route_destinations
                    JOIN destinations
                      ON destinations.id = route_destinations.destination_id
                    WHERE route_destinations.route_id = ?
                      AND destinations.enabled = 1
                    ORDER BY destinations.name_normalized, destinations.id
                    """,
                    (str(route.id),),
                ).fetchall()
            for row in rows:
                destination_id = str(row["id"])
                if destination_id in seen_destinations:
                    continue
                seen_destinations.add(destination_id)
                target = DestinationStore._delivery_destination(row)
                result.append(
                    RouteDestinationCandidate(
                        route,
                        destination_id,
                        target,
                    )
                )
        return result

    def foreign_owner_route_ids(self, destination_id: str) -> tuple[str, ...]:
        with self.database.connect() as connection:
            destination = connection.execute(
                "SELECT owner_user_id FROM destinations WHERE id = ?",
                (str(destination_id),),
            ).fetchone()
            if destination is None:
                raise KeyError("destination not found")
            rows = connection.execute(
                """
                SELECT routes.id
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE route_destinations.destination_id = ?
                  AND routes.owner_user_id <> ?
                ORDER BY routes.id
                """,
                (str(destination_id), str(destination["owner_user_id"])),
            ).fetchall()
        return tuple(str(row["id"]) for row in rows)

    def _destination(self, actor: Actor, destination_id: str, *, write: bool):
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id, owner_user_id, shared, enabled
                FROM destinations WHERE id = ?
                """,
                (str(destination_id),),
            ).fetchone()
        if row is None:
            raise KeyError("destination not found")
        if write:
            OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        else:
            OwnershipPolicy.require_read(
                actor,
                str(row["owner_user_id"]),
                shared=bool(row["shared"]),
            )
        return row

    def _route(self, actor: Actor, route_id: str, *, write: bool):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, owner_user_id FROM routes WHERE id = ?",
                (str(route_id),),
            ).fetchone()
            if row is None:
                raise KeyError("route not found")
            if write:
                OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
                return row
            if OwnershipPolicy.can_read(actor, str(row["owner_user_id"])):
                return row
            shared = connection.execute(
                """
                SELECT 1
                FROM route_destinations
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE route_destinations.route_id = ? AND destinations.shared = 1
                LIMIT 1
                """,
                (str(route_id),),
            ).fetchone()
        if shared is None:
            raise PermissionError("resource is not available to this user")
        return row

    def _audit(self, actor, action, resource_id, details=None):
        if self.audit is not None:
            self.audit.write(
                actor,
                action,
                "destination",
                resource_id,
                "success",
                details,
            )
