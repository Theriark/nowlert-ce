"""Acceptance access model for shared Destinations and owner-private Filtering."""

from __future__ import annotations

import re
from urllib.parse import unquote

from api.filtering import PlatformAPI as BasePlatformAPI
from api.response import APIResponse
from integrations.catalog import canonical_source
from storage.destination_access import (
    AccessControlledDeliveryHistoryStore,
    AccessControlledDestinationStore,
    AccessControlledRouteDestinationStore,
    DestinationAccessStore,
)
from storage.destinations import DeliveryDestination
from storage.filtering import FilteredPlatformDeliveryService, _clause_matches
from storage.route_destinations import RouteDestinationCandidate
from storage.system_filtering import SystemDestinationFilterStore


_DESTINATION_FILTER = re.compile(r"/api/v2/filters/destinations/([0-9a-f]{32})")
_SOURCE_FILTER = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/sources/([^/]+)"
)


class AcceptanceDestinationAccessStore(DestinationAccessStore):
    """Admin-shared Destinations are collaborative; Filtering stays owner-private."""

    def can_edit_destination(self, actor, destination) -> bool:
        owner_user_id = str(destination["owner_user_id"])
        if actor.user_id == owner_user_id:
            return True
        if not bool(destination["shared"]):
            return False
        if actor.is_admin:
            return True
        # Normal users cannot share their own Destinations. A shared
        # administrator Destination is therefore the collaborative resource
        # normal users may operate; a Destination merely owned by another
        # normal user is never made cross-user editable.
        owner = self._user_row(owner_user_id)
        return str(owner["role"]) == "admin"

    def can_manage_filters(self, actor, destination) -> bool:
        return actor.user_id == str(destination["owner_user_id"])

    def private_destination_metadata(self, actor) -> list[dict]:
        if not actor.is_admin:
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.owner_user_id, d.name, d.output_type, d.enabled,
                       u.username AS owner_username
                FROM destinations AS d
                JOIN users AS u ON u.id = d.owner_user_id
                WHERE d.shared = 0 AND d.owner_user_id <> ?
                ORDER BY u.username_normalized, d.name_normalized
                """,
                (actor.user_id,),
            ).fetchall()
        return [
            {
                "id": str(row["id"]),
                "owner_user_id": str(row["owner_user_id"]),
                "owner_username": str(row["owner_username"]),
                "name": str(row["name"]),
                "output_type": str(row["output_type"]),
                "enabled": bool(row["enabled"]),
                "shared": False,
                "metadata_only": True,
            }
            for row in rows
        ]

    def private_filter_metadata(self, actor) -> list[dict]:
        if not actor.is_admin:
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT d.id, d.owner_user_id, d.name, d.output_type,
                       d.enabled, u.username AS owner_username
                FROM destinations AS d
                JOIN users AS u ON u.id = d.owner_user_id
                JOIN destination_filters AS f ON f.destination_id = d.id
                WHERE d.shared = 0 AND d.owner_user_id <> ?
                ORDER BY u.username_normalized, d.name_normalized
                """,
                (actor.user_id,),
            ).fetchall()
        return [
            {
                "destination_id": str(row["id"]),
                "owner_user_id": str(row["owner_user_id"]),
                "owner_username": str(row["owner_username"]),
                "destination_name": str(row["name"]),
                "output_type": str(row["output_type"]),
                "enabled": bool(row["enabled"]),
                "shared": False,
                "metadata_only": True,
            }
            for row in rows
        ]


class AcceptanceDestinationStore(AccessControlledDestinationStore):
    """Keep API reads private while allowing internal runtime delivery."""

    def for_delivery_metadata(self, actor, destination_id: str) -> DeliveryDestination:
        row = self._record(destination_id)
        return DeliveryDestination(
            self._destination(row),
            str(row["secret_id"]) if row["secret_id"] is not None else None,
        )


class AcceptanceRouteDestinationStore(AccessControlledRouteDestinationStore):
    """Use access checks for editing, never for runtime delivery expansion."""

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


class AcceptanceFilterStore(SystemDestinationFilterStore):
    """Evaluate private filters at runtime without exposing them to the event actor."""

    def matches(self, actor, destination_id: str, notification) -> bool:
        source = canonical_source(notification.source)
        policy = self._policy(destination_id, source)
        policy_rules = list(policy.get("policy_rules") or []) if policy else []
        if not policy_rules or not self.filter_enabled(destination_id, source):
            return True
        block_rules = [item for item in policy_rules if item["action"] == "block"]
        allow_rules = [item for item in policy_rules if item["action"] == "allow"]
        if any(
            _clause_matches(source, item["conditions"], notification)
            for item in block_rules
        ):
            return False
        if allow_rules:
            return any(
                _clause_matches(source, item["conditions"], notification)
                for item in allow_rules
            )
        return True


class PlatformAPI(BasePlatformAPI):
    """Apply the accepted Destination/Filtering privacy contract."""

    def __init__(self, database, *args, **kwargs):
        super().__init__(database, *args, **kwargs)
        self.destination_access = AcceptanceDestinationAccessStore(database, audit=self.audit)
        self.destinations = AcceptanceDestinationStore(
            database, audit=self.audit, access=self.destination_access
        )
        self.relationships = AcceptanceRouteDestinationStore(
            database, audit=self.audit, access=self.destination_access
        )
        self.filters = AcceptanceFilterStore(
            database, audit=self.audit, access=self.destination_access
        )
        self.history = AccessControlledDeliveryHistoryStore(database)
        self.outputs.destinations = self.destinations
        self.portability.destinations = self.destinations
        self.portability.relationships = self.relationships
        self.delivery = FilteredPlatformDeliveryService(
            self.routes,
            self.destinations,
            self.secrets,
            self.history,
            self.registry.delivery_adapters(),
            filters=self.filters,
            relationships=self.relationships,
        )

    def _destinations_endpoint(self, method, payload, actor) -> APIResponse:
        response = super()._destinations_endpoint(method, payload, actor)
        if (
            method == "GET"
            and not self.yaml_resource_authority
            and response.status < 300
            and isinstance(response.payload, dict)
        ):
            response.payload["private_resources"] = (
                self.destination_access.private_destination_metadata(actor)
            )
        return response

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if action is not None and not self.yaml_resource_authority:
            row = self.destination_access.destination_row(destination_id)
            self.destination_access.require_view(actor, row)
        return super()._destination_resource(method, payload, actor, destination_id, action)

    def _owner_filter_destination(self, actor, destination_id: str):
        row = self.destination_access.destination_row(destination_id)
        if actor.user_id != str(row["owner_user_id"]):
            raise PermissionError("destination filtering is private to its owner")
        return row

    def _filters_overview(self, actor) -> APIResponse:
        choices = []
        for destination in self.destinations.list_visible(actor):
            if actor.user_id != destination.owner_user_id:
                continue
            available = self.filters.available_sources(actor, destination.id)
            choices.append(
                {
                    "id": destination.id,
                    "name": destination.name,
                    "output_type": destination.output_type,
                    "enabled": destination.enabled,
                    "shared": destination.shared,
                    "owned": True,
                    "can_manage_filters": True,
                    "available_integration_count": len(available),
                }
            )

        policies = [
            policy
            for policy in self.filters.list_visible(actor)
            if policy.get("owned") is True
        ]
        for policy in policies:
            view = self.filters.destination_view(actor, policy["destination_id"])
            integrations = list(view["integrations"])
            configured = [item for item in integrations if item.get("configured")]
            active = [item for item in configured if item.get("filter_enabled", True)]
            policy["configured_count"] = len(configured)
            policy["active_count"] = len(active)
            policy["integrations"] = configured
            policy["unconfigured_integrations"] = [
                {"source": item["source"], "name": item.get("name")}
                for item in integrations
                if not item.get("configured")
            ]

        return APIResponse(
            200,
            {
                "filters": policies,
                "destinations": choices,
                "private_resources": self.destination_access.private_filter_metadata(actor),
            },
        )

    def _resource_endpoint(self, method, path, payload, actor):
        if path.startswith("/api/v2/routing-flow/"):
            if method != "GET":
                return self._method_not_allowed("GET")
            from api.routing_flow import snapshot

            return APIResponse(200, snapshot(self, actor, path.rsplit("/", 1)[-1]))

        if path == "/api/v2/filters" and method == "GET":
            return self._filters_overview(actor)

        source_match = _SOURCE_FILTER.fullmatch(path)
        if source_match:
            destination_id, encoded_source = source_match.groups()
            source = canonical_source(unquote(encoded_source))
            self._owner_filter_destination(actor, destination_id)
            if method == "GET":
                view = self.filters.destination_view(actor, destination_id)
                item = next(
                    (
                        integration
                        for integration in view["integrations"]
                        if integration["source"] == source
                    ),
                    None,
                )
                if item is None:
                    raise KeyError("destination integration not found")
                return APIResponse(
                    200,
                    {"destination": view["destination"], "integration": item},
                )

        destination_match = _DESTINATION_FILTER.fullmatch(path)
        if destination_match and method == "GET":
            destination_id = destination_match.group(1)
            self._owner_filter_destination(actor, destination_id)
            return APIResponse(200, self.filters.destination_view(actor, destination_id))

        return super()._resource_endpoint(method, path, payload, actor)
