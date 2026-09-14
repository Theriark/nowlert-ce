"""Platform API extension for destination-owned filtering and Route assignment."""

from __future__ import annotations

import re
import time

from urllib.parse import unquote

from api.platform import PlatformAPI as BasePlatformAPI
from api.response import APIResponse
from integrations.catalog import canonical_source
from storage.filtering import FilteredPlatformDeliveryService, RoutingOnlyRouteStore
from storage.filtering_toggle import DestinationFilterStore
from storage.route_destinations import RouteDestinationStore


_DESTINATION_FILTER = re.compile(r"/api/v2/filters/destinations/([0-9a-f]{32})")
_SOURCE_FILTER = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/sources/([^/]+)"
)


class PlatformAPI(BasePlatformAPI):
    """Expose filtering and Destination-owned reusable Route assignments."""

    def __init__(self, database, *args, **kwargs):
        super().__init__(database, *args, **kwargs)
        self.routes = RoutingOnlyRouteStore(database, audit=self.audit)
        self.relationships = RouteDestinationStore(database, audit=self.audit)
        self.filters = DestinationFilterStore(database, audit=self.audit)
        self.delivery = FilteredPlatformDeliveryService(
            self.routes,
            self.destinations,
            self.secrets,
            self.history,
            self.registry.delivery_adapters(),
            filters=self.filters,
            relationships=self.relationships,
        )
        # Portability is created by the base API before relationship support is
        # installed. Expose the store without changing its constructor contract.
        self.portability.relationships = self.relationships

    def _routes_endpoint(self, method, payload, actor) -> APIResponse:
        if method == "POST" and isinstance(payload, dict):
            payload = {**payload, "filters": {}}
        return super()._routes_endpoint(method, payload, actor)

    def _route_resource(self, method, payload, actor, route_id):
        legacy_filters = None
        if method == "PATCH" and isinstance(payload, dict):
            legacy_filters = payload.get("filters") if "filters" in payload else None
            payload = {**payload, "filters": {}}
        response = super()._route_resource(method, payload, actor, route_id)
        if (
            legacy_filters is not None
            and response.status < 300
            and isinstance(response.payload, dict)
            and isinstance(response.payload.get("route"), dict)
        ):
            response.payload["route"]["filters"] = legacy_filters
        return response

    def _destinations_endpoint(self, method, payload, actor) -> APIResponse:
        route_ids = None
        if method == "POST" and isinstance(payload, dict) and "route_ids" in payload:
            route_ids = payload.get("route_ids")
            payload = {key: value for key, value in payload.items() if key != "route_ids"}
        response = super()._destinations_endpoint(method, payload, actor)
        if method == "POST" and response.status < 300 and route_ids is not None:
            destination = response.payload.get("destination", {})
            destination_id = str(destination.get("id") or "")
            try:
                self.relationships.replace_for_destination(actor, destination_id, route_ids)
            except Exception:
                try:
                    if self.yaml_resource_authority:
                        self.configuration_sync.delete_destination(actor, destination_id)
                    else:
                        self.destinations.delete(actor, destination_id)
                finally:
                    raise
            response.payload["destination"] = self._destination(
                self.destinations.get(actor, destination_id)
            )
        return response

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if action is not None or method != "PATCH" or not isinstance(payload, dict):
            return super()._destination_resource(
                method, payload, actor, destination_id, action
            )
        if "route_ids" not in payload:
            return super()._destination_resource(
                method, payload, actor, destination_id, action
            )

        route_ids = payload.get("route_ids")
        payload = {key: value for key, value in payload.items() if key != "route_ids"}
        current = self.relationships.route_ids_for_destination(actor, destination_id)
        destination = self.destinations.get(actor, destination_id)
        _row, normalized = self.relationships.validate_for_destination(
            actor, destination_id, route_ids
        )
        if payload.get("shared") is False:
            with self.database.connect() as connection:
                if normalized:
                    placeholders = ",".join("?" for _ in normalized)
                    external = connection.execute(
                        f"""
                        SELECT COUNT(*) FROM routes
                        WHERE id IN ({placeholders}) AND owner_user_id != ?
                        """,
                        (*normalized, destination.owner_user_id),
                    ).fetchone()[0]
                else:
                    external = 0
            if int(external):
                raise ValueError(
                    "private destination cannot use another user's route"
                )

        prebind = payload.get("shared") is False and destination.shared
        if prebind:
            self.relationships.replace_for_destination(actor, destination_id, normalized)
        try:
            response = super()._destination_resource(
                method, payload, actor, destination_id, action
            )
            if response.status < 300 and not prebind:
                self.relationships.replace_for_destination(actor, destination_id, normalized)
        except Exception:
            if prebind:
                self.relationships.replace_for_destination(actor, destination_id, current)
            raise
        response.payload["destination"] = self._destination(
            self.destinations.get(actor, destination_id)
        )
        return response

    def _resource_endpoint(self, method, path, payload, actor):
        if path == "/api/v2/filters":
            if method != "GET":
                return self._method_not_allowed("GET")
            choices = []
            for destination in self.destinations.list_visible(actor):
                available = self.filters.available_sources(actor, destination.id)
                choices.append(
                    {
                        "id": destination.id,
                        "name": destination.name,
                        "output_type": destination.output_type,
                        "enabled": destination.enabled,
                        "available_integration_count": len(available),
                    }
                )
            filters = self.filters.list_visible(actor)
            for policy in filters:
                view = self.filters.destination_view(actor, policy["destination_id"])
                integrations = list(view["integrations"])
                configured = [
                    integration
                    for integration in integrations
                    if integration.get("configured")
                ]
                policy["configured_count"] = len(configured)
                policy["integrations"] = [
                    integration
                    for integration in configured
                    if integration.get("filter_enabled", True)
                ]
                policy["unconfigured_integrations"] = [
                    {
                        "source": integration["source"],
                        "name": integration.get("name"),
                    }
                    for integration in integrations
                    if not integration.get("configured")
                ]
            return APIResponse(200, {"filters": filters, "destinations": choices})

        source_match = _SOURCE_FILTER.fullmatch(path)
        if source_match:
            destination_id, encoded_source = source_match.groups()
            source = canonical_source(unquote(encoded_source))
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
            if method == "PUT":
                self._require_admin(actor)
                data = self._object(payload, {"rules", "enabled"})
                if not data:
                    raise ValueError("filter rules or enabled state are required")
                if "enabled" in data and not isinstance(data["enabled"], bool):
                    raise ValueError("enabled must be a boolean")
                policy = None
                if "rules" in data:
                    policy = self.filters.set_rules(
                        actor,
                        destination_id,
                        source,
                        data["rules"],
                    )
                if "enabled" in data:
                    if "rules" not in data or policy is not None:
                        self.filters.set_enabled(
                            actor,
                            destination_id,
                            source,
                            data["enabled"],
                        )
                view = self.filters.destination_view(actor, destination_id)
                item = next(
                    integration
                    for integration in view["integrations"]
                    if integration["source"] == source
                )
                return APIResponse(
                    200,
                    {"destination": view["destination"], "integration": item},
                )
            if method == "DELETE":
                self._require_admin(actor)
                self.filters.clear_source(actor, destination_id, source)
                return APIResponse(204)
            return self._method_not_allowed("GET, PUT, DELETE")

        destination_match = _DESTINATION_FILTER.fullmatch(path)
        if destination_match:
            destination_id = destination_match.group(1)
            if method == "GET":
                return APIResponse(
                    200,
                    self.filters.destination_view(actor, destination_id),
                )
            if method == "DELETE":
                self._require_admin(actor)
                self.filters.clear_destination(actor, destination_id)
                return APIResponse(204)
            return self._method_not_allowed("GET, DELETE")

        return super()._resource_endpoint(method, path, payload, actor)

    def _metrics_endpoint(self, method, actor, history_range) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        windows = {
            "10m": 10 * 60,
            "1h": 60 * 60,
            "1d": 24 * 60 * 60,
            "1m": 31 * 24 * 60 * 60,
            "1y": 366 * 24 * 60 * 60,
        }
        if history_range not in windows:
            raise ValueError("history range is invalid")
        since = int(time.time()) - windows[history_range]
        delivery = self.history.metrics(actor, since)
        with self.database.connect() as connection:
            route_where = "WHERE routes.enabled = 1"
            destination_where = "WHERE enabled = 1"
            route_parameters = ()
            destination_parameters = ()
            if not actor.is_admin:
                route_where += (
                    " AND (routes.owner_user_id = ? OR routes.id IN ("
                    "SELECT route_destinations.route_id FROM route_destinations "
                    "JOIN destinations ON destinations.id = route_destinations.destination_id "
                    "WHERE destinations.shared = 1))"
                )
                destination_where += " AND (owner_user_id = ? OR shared = 1)"
                route_parameters = (actor.user_id,)
                destination_parameters = (actor.user_id,)
            route_row = connection.execute(
                f"SELECT COUNT(*) AS total, COUNT(DISTINCT source) AS sources FROM routes {route_where}",
                route_parameters,
            ).fetchone()
            destination_row = connection.execute(
                f"SELECT COUNT(*) FROM destinations {destination_where}",
                destination_parameters,
            ).fetchone()
        applications = self.tokens.list_for_owner(actor, actor.user_id)
        active_applications = sum(
            1 for item in applications if item.enabled and item.revoked_at is None
        )
        if actor.is_admin and self.configuration_sync is not None:
            active_applications += sum(
                1
                for item in self.configuration_sync.legacy_applications()
                if item["enabled"] and item["credential_available"]
            )
        return APIResponse(
            200,
            {
                "metrics": {
                    "range": history_range,
                    "since": since,
                    "sources": int(route_row["sources"] or 0),
                    "destinations": int(destination_row[0] or 0),
                    "routes": int(route_row["total"] or 0),
                    "applications": active_applications,
                    **delivery,
                }
            },
        )

    def _portability_import(self, method, payload, actor):
        response = super()._portability_import(method, payload, actor)
        if method == "POST" and response.status < 300:
            self.filters.migrate_legacy_route_filters(force=True)
        return response

    def _v1_migration_import(self, method, payload, actor):
        response = super()._v1_migration_import(method, payload, actor)
        if method == "POST" and response.status < 300:
            self.filters.migrate_legacy_route_filters(force=True)
        return response

    def _configuration_migration_apply(self, method, payload, actor):
        response = super()._configuration_migration_apply(method, payload, actor)
        if method == "POST" and response.status < 300:
            self.filters.migrate_legacy_route_filters(force=True)
        return response

    def _destination(self, item):
        data = BasePlatformAPI._destination(item)
        data["route_ids"] = list(
            self.relationships.route_ids_for_destination(
                self._serialization_actor(item.owner_user_id), item.id
            )
        )
        return data

    def _route(self, item):
        data = BasePlatformAPI._route(item)
        data.pop("destination_id", None)
        data["filters"] = {}
        data["destination_ids"] = list(item.destination_ids)
        data["destination_count"] = len(item.destination_ids)
        return data

    @staticmethod
    def _serialization_actor(owner_user_id):
        # Relationship serialization already passed visibility checks through the
        # enclosing resource list/get. An owner Actor is sufficient for the
        # relationship lookup and does not broaden the HTTP authorization scope.
        from storage.ownership import Actor

        return Actor(str(owner_user_id), "user")
