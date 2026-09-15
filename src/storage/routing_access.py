"""Internal routing helpers for system Routes without cross-owner duplication."""

from __future__ import annotations

from storage.destination_access import AccessControlledRouteDestinationStore
from storage.route_destinations import RouteDestinationCandidate


class OwnerOnlyRouteDestinationStore(AccessControlledRouteDestinationStore):
    """Expand system Routes only to Destinations owned by the delivery actor."""

    def expand(self, actor, routes):
        result = []
        seen_destinations = set()
        for route in routes:
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT destinations.id
                    FROM route_destinations
                    JOIN destinations
                      ON destinations.id = route_destinations.destination_id
                    WHERE route_destinations.route_id = ?
                      AND destinations.owner_user_id = ?
                      AND destinations.enabled = 1
                    ORDER BY destinations.name_normalized, destinations.id
                    """,
                    (str(route.id), actor.user_id),
                ).fetchall()
            for row in rows:
                destination_id = str(row["id"])
                if destination_id in seen_destinations:
                    continue
                seen_destinations.add(destination_id)
                result.append(RouteDestinationCandidate(route, destination_id))
        return result
