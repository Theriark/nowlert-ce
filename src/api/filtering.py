"""Platform API extension for destination-owned notification filtering."""

from __future__ import annotations

import re

from urllib.parse import unquote

from api.platform import PlatformAPI as BasePlatformAPI
from api.response import APIResponse
from integrations.catalog import canonical_source
from storage.filtering import FilteredPlatformDeliveryService, RoutingOnlyRouteStore
from storage.filtering_toggle import DestinationFilterStore


_DESTINATION_FILTER = re.compile(r"/api/v2/filters/destinations/([0-9a-f]{32})")
_SOURCE_FILTER = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/sources/([^/]+)"
)


class PlatformAPI(BasePlatformAPI):
    """Expose destination filters while keeping route selection filter-free."""

    def __init__(self, database, *args, **kwargs):
        super().__init__(database, *args, **kwargs)
        self.routes = RoutingOnlyRouteStore(database, audit=self.audit)
        self.filters = DestinationFilterStore(database, audit=self.audit)
        self.delivery = FilteredPlatformDeliveryService(
            self.routes,
            self.destinations,
            self.secrets,
            self.history,
            self.registry.delivery_adapters(),
            filters=self.filters,
        )

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

    @staticmethod
    def _route(item):
        data = BasePlatformAPI._route(item)
        data["filters"] = {}
        return data
