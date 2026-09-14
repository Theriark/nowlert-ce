"""Many-to-many assignment of reusable Routes to delivery Destinations."""

from __future__ import annotations

import time

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.ownership import Actor, OwnershipPolicy

if TYPE_CHECKING:
    from storage.routes import Route


@dataclass(frozen=True)
class RouteDestinationCandidate:
    """One matched Route resolved to one concrete Destination."""

    route: "Route"
    destination_id: str


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
        previous = self.route_ids_for_destination(actor, str(destination["id"]))
        now = int(self.clock())
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM route_destinations WHERE destination_id = ?",
                (str(destination["id"]),),
            )
            for route_id in normalized:
                connection.execute(
                    """
                    INSERT INTO route_destinations(route_id, destination_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (route_id, str(destination["id"]), now),
                )
        added = [item for item in normalized if item not in previous]
        removed = [item for item in previous if item not in normalized]
        self._audit(
            actor,
            "destination.routes_update",
            str(destination["id"]),
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
                    SELECT destinations.id
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
                result.append(RouteDestinationCandidate(route, destination_id))
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
