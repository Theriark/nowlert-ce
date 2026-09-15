"""Route legacy SMTP and webhook notifications through system Route definitions."""

from __future__ import annotations

from outputs.platform import PlatformOutputRegistry
from storage.delivery import DeliveryHistoryStore, DeliverySummary
from storage.destination_access import (
    AccessControlledDestinationStore,
    DestinationAccessStore,
    SystemRoutingRouteStore,
)
from storage.filtering import FilteredPlatformDeliveryService
from storage.ownership import Actor
from storage.routing_access import OwnerOnlyRouteDestinationStore
from storage.secrets import SecretStore
from storage.system_filtering import SystemDestinationFilterStore


class PlatformRoutingBridge:
    """Deliver one infrastructure event once to every assigned Destination owner."""

    def __init__(self, database, *, registry=None):
        self.database = database
        self.access = DestinationAccessStore(database)
        self.routes = SystemRoutingRouteStore(database)
        self.filters = SystemDestinationFilterStore(
            database,
            access=self.access,
        )
        self.destinations = AccessControlledDestinationStore(
            database,
            access=self.access,
        )
        self.relationships = OwnerOnlyRouteDestinationStore(
            database,
            access=self.access,
        )
        self.secrets = SecretStore(database)
        self.history = DeliveryHistoryStore(database)
        self.registry = registry or PlatformOutputRegistry()
        self.delivery = FilteredPlatformDeliveryService(
            self.routes,
            self.destinations,
            self.secrets,
            self.history,
            self.registry.delivery_adapters(),
            filters=self.filters,
            relationships=self.relationships,
        )

    def route(self, notification) -> DeliverySummary:
        matched = delivered = failed = attempts = 0
        for owner_id in self._owners(notification):
            summary = self.delivery.deliver(
                Actor(owner_id, "user"),
                notification,
            )
            matched += summary.matched_routes
            delivered += summary.delivered
            failed += summary.failed
            attempts += summary.attempts
        return DeliverySummary(matched, delivered, failed, attempts)

    def _owners(self, notification) -> tuple[str, ...]:
        source = str(notification.source or "").strip().casefold()
        input_type = str((notification.metadata or {}).get("_input_type") or "").strip().casefold()
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT destinations.owner_user_id
                FROM routes
                JOIN route_destinations
                  ON route_destinations.route_id = routes.id
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                JOIN users
                  ON users.id = destinations.owner_user_id
                WHERE destinations.enabled = 1
                  AND users.enabled = 1
                  AND (routes.source = ? OR routes.source = '*')
                  AND (routes.input_type = '' OR routes.input_type = ?)
                ORDER BY destinations.owner_user_id
                """,
                (source, input_type),
            ).fetchall()
        return tuple(str(row["owner_user_id"]) for row in rows)
