"""Platform API extension for destination-owned filtering and delegated access."""

from __future__ import annotations

import re
import sqlite3
import time

from urllib.parse import unquote

from api.platform import PlatformAPI as BasePlatformAPI
from api.response import APIResponse
from integrations.catalog import canonical_source
from outputs.settings import normalize_output_settings
from storage.destination_access import (
    AccessControlledDeliveryHistoryStore,
    AccessControlledDestinationStore,
    AccessControlledRouteDestinationStore,
    DestinationAccessStore,
    SystemRoutingRouteStore,
)
from storage.filtering import FilteredPlatformDeliveryService
from storage.ownership import Actor
from storage.system_filtering import SystemDestinationFilterStore
from storage.validation import ConflictError, normalized_name


_DESTINATION_FILTER = re.compile(r"/api/v2/filters/destinations/([0-9a-f]{32})")
_SOURCE_FILTER = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/sources/([^/]+)"
)
_USER_DESTINATION_PERMISSIONS = re.compile(
    r"/api/v2/users/([0-9a-f]{32})/destination-permissions"
)


class PlatformAPI(BasePlatformAPI):
    """Expose destination ownership, delegated filtering, and system routing."""

    def __init__(self, database, *args, **kwargs):
        super().__init__(database, *args, **kwargs)
        self.destination_access = DestinationAccessStore(database, audit=self.audit)
        self.destinations = AccessControlledDestinationStore(
            database,
            audit=self.audit,
            access=self.destination_access,
        )
        self.routes = SystemRoutingRouteStore(database, audit=self.audit)
        self.relationships = AccessControlledRouteDestinationStore(
            database,
            audit=self.audit,
            access=self.destination_access,
        )
        self.filters = SystemDestinationFilterStore(
            database,
            audit=self.audit,
            access=self.destination_access,
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

    def _access_store(self):
        access = getattr(self, "destination_access", None)
        if access is None:
            database = getattr(self, "database", None) or getattr(self.filters, "database", None)
            if database is None:
                raise RuntimeError("destination access store is unavailable")
            access = DestinationAccessStore(database)
            self.destination_access = access
        return access

    def _users_endpoint(self, method, payload, actor) -> APIResponse:
        response = super()._users_endpoint(method, payload, actor)
        if method == "GET" and response.status < 300 and isinstance(response.payload, dict):
            for user in response.payload.get("users", []):
                user["private_destination_count"] = self._access_store().private_destination_count(
                    user["id"]
                )
        return response

    def _user_resource(self, method, payload, actor, user_id, action):
        response = super()._user_resource(method, payload, actor, user_id, action)
        if method == "GET" and action is None and response.status < 300:
            response.payload["user"]["private_destination_count"] = (
                self._access_store().private_destination_count(user_id)
            )
        if method == "DELETE" and response.status < 300:
            self._access_store().clear_user(user_id)
        return response

    def _routes_endpoint(self, method, payload, actor) -> APIResponse:
        if method == "GET" and not self.yaml_resource_authority:
            routes, errors = self.routes.list_visible_safe(actor)
            return APIResponse(
                200,
                {"routes": [self._route(item) for item in routes], "errors": errors},
            )
        if method != "GET":
            self._require_admin(actor)
        requested_enabled = None
        if method == "POST" and isinstance(payload, dict):
            if isinstance(payload.get("enabled"), bool):
                requested_enabled = payload.get("enabled")
            payload = {**payload, "filters": {}}
        response = super()._routes_endpoint(method, payload, actor)
        if (
            requested_enabled is not None
            and response.status < 300
            and isinstance(response.payload, dict)
            and isinstance(response.payload.get("route"), dict)
        ):
            response.payload["route"]["enabled"] = requested_enabled
        return response

    def _route_resource(self, method, payload, actor, route_id):
        if method in {"PATCH", "DELETE"}:
            self._require_admin(actor)
        legacy_filters = None
        requested_enabled = None
        if method == "PATCH" and isinstance(payload, dict):
            legacy_filters = payload.get("filters") if "filters" in payload else None
            if isinstance(payload.get("enabled"), bool):
                requested_enabled = payload.get("enabled")
            payload = {**payload, "filters": {}}
        response = super()._route_resource(method, payload, actor, route_id)
        if (
            response.status < 300
            and isinstance(response.payload, dict)
            and isinstance(response.payload.get("route"), dict)
        ):
            if legacy_filters is not None:
                response.payload["route"]["filters"] = legacy_filters
            if requested_enabled is not None:
                response.payload["route"]["enabled"] = requested_enabled
        return response

    def _destinations_endpoint(self, method, payload, actor) -> APIResponse:
        route_ids = None
        if method == "GET" and not self.yaml_resource_authority:
            destinations, errors = self.destinations.list_visible_safe(actor)
            return APIResponse(
                200,
                {
                    "destinations": [
                        self._destination_for_actor(item, actor)
                        for item in destinations
                    ],
                    "errors": errors,
                },
            )

        if method == "POST" and isinstance(payload, dict):
            if "route_ids" in payload:
                route_ids = payload.get("route_ids")
                payload = {
                    key: value for key, value in payload.items() if key != "route_ids"
                }
            requested_owner = str(payload.get("owner_user_id") or actor.user_id)
            requested_shared = payload.get("shared") is True
            if (
                not self.yaml_resource_authority
                and actor.is_admin
                and requested_owner != actor.user_id
                and not requested_shared
            ):
                return self._create_private_destination_for_user(
                    payload,
                    actor,
                    route_ids=route_ids,
                )

        response = super()._destinations_endpoint(method, payload, actor)
        if method == "POST" and response.status < 300:
            destination = response.payload.get("destination", {})
            destination_id = str(destination.get("id") or "")
            if route_ids is not None:
                try:
                    self.relationships.replace_for_destination(
                        actor,
                        destination_id,
                        route_ids,
                    )
                except Exception:
                    try:
                        if self.yaml_resource_authority:
                            self.configuration_sync.delete_destination(actor, destination_id)
                        else:
                            self.destinations.delete(actor, destination_id)
                    finally:
                        raise
            if not self.yaml_resource_authority:
                response.payload["destination"] = self._destination_for_actor(
                    self.destinations.get(actor, destination_id), actor
                )
        return response

    def _create_private_destination_for_user(self, payload, actor, *, route_ids=None):
        data = self._object(
            payload,
            {
                "owner_user_id",
                "name",
                "output_type",
                "settings",
                "shared",
                "enabled",
                "secret",
            },
        )
        owner_id = self._owner(data, actor)
        output_type = data.get("output_type")
        settings = data.get("settings", {})
        normalized_settings = normalize_output_settings(output_type, settings)
        if (
            str(output_type or "").strip().casefold() == "email"
            and normalized_settings.get("username")
            and not self._email_password_configured(data.get("secret"))
        ):
            raise ValueError(
                "Email destination password is required when username is configured"
            )
        if not self.destinations.name_available(owner_id, data.get("name")):
            raise ConflictError(
                f"A destination named {str(data.get('name') or '').strip()} already exists."
            )
        secret_value = (
            self._secret_value(data.get("secret"))
            if "secret" in data
            else None
        )
        owner_actor = Actor(owner_id, "user")
        private_store = AccessControlledDestinationStore(
            self.database,
            access=self._access_store(),
            audit=None,
        )
        destination = private_store.create(
            owner_actor,
            owner_id,
            data.get("name"),
            output_type,
            settings=settings,
            shared=False,
            enabled=self._boolean(data, "enabled", True),
        )
        try:
            if secret_value is not None:
                secret = self.secrets.create(
                    owner_actor,
                    owner_id,
                    self._secret_name(destination.name),
                    f"{destination.output_type}-credentials",
                    secret_value,
                )
                destination = private_store.set_secret(
                    owner_actor,
                    destination.id,
                    secret.id,
                )
            if route_ids is not None:
                self.relationships.replace_for_destination(
                    owner_actor,
                    destination.id,
                    route_ids,
                )
                destination = private_store.get(owner_actor, destination.id)
        except Exception:
            try:
                private_store.delete(owner_actor, destination.id)
            finally:
                raise
        self.audit.write(
            actor,
            "destination.create",
            "destination",
            destination.id,
            "success",
            {"output_type": destination.output_type, "shared": False},
        )
        return APIResponse(201, {"destination": self._destination(destination)})

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if self.yaml_resource_authority:
            return super()._destination_resource(
                method, payload, actor, destination_id, action
            )

        if action is not None:
            response = super()._destination_resource(
                method, payload, actor, destination_id, action
            )
            if (
                response.status < 300
                and isinstance(response.payload, dict)
                and isinstance(response.payload.get("destination"), dict)
            ):
                response.payload["destination"] = self._destination_for_actor(
                    self.destinations.get(actor, destination_id), actor
                )
            return response

        if method == "GET":
            destination = self.destinations.get(actor, destination_id)
            return APIResponse(
                200,
                {"destination": self._destination_for_actor(destination, actor)},
            )

        if method == "DELETE":
            self.destinations.delete(actor, destination_id)
            return APIResponse(204)

        if method != "PATCH" or not isinstance(payload, dict):
            return self._method_not_allowed("GET, PATCH, DELETE")

        data = self._object(
            payload,
            {
                "name",
                "output_type",
                "settings",
                "enabled",
                "shared",
                "secret",
                "route_ids",
            },
        )
        destination = self.destinations.get(actor, destination_id)
        row = self._access_store().destination_row(destination_id)
        self._access_store().require_edit_destination(actor, row)

        route_ids = data.pop("route_ids", None) if "route_ids" in data else None
        normalized_routes = None
        if route_ids is not None:
            _destination_row, normalized_routes = self.relationships.validate_for_destination(
                actor,
                destination_id,
                route_ids,
            )

        next_name = data.get("name", destination.name)
        next_type = str(
            data.get("output_type", destination.output_type)
            or destination.output_type
        ).strip().casefold()
        type_changed = next_type != destination.output_type
        if not self.destinations.name_available(
            destination.owner_user_id,
            next_name,
            excluding_id=destination.id,
        ):
            raise ConflictError(
                f"A destination named {str(next_name or '').strip()} already exists."
            )
        if type_changed and "settings" not in data:
            raise ValueError(
                "destination settings are required when changing destination type"
            )
        if type_changed and "secret" not in data:
            raise ValueError(
                "new credentials are required when changing destination type"
            )

        next_settings = data.get("settings", destination.settings)
        normalized_settings = normalize_output_settings(next_type, next_settings)
        if (
            next_type == "email"
            and normalized_settings.get("username")
            and (
                (
                    "secret" in data
                    and not self._email_password_configured(data.get("secret"))
                )
                or (
                    "secret" not in data
                    and not destination.secret_configured
                )
            )
        ):
            raise ValueError(
                "Email destination password is required when username is configured"
            )
        enabled = (
            self._boolean(data, "enabled")
            if "enabled" in data
            else destination.enabled
        )
        shared = (
            self._boolean(data, "shared")
            if "shared" in data
            else destination.shared
        )
        secret_value = (
            self._secret_value(data.get("secret"))
            if "secret" in data
            else None
        )

        if secret_value is not None:
            target = self.destinations.for_delivery_metadata(actor, destination_id)
            secret_actor = Actor(target.destination.owner_user_id, "user")
            if target.secret_id:
                self.secrets.rotate(secret_actor, target.secret_id, secret_value)
            else:
                secret = self.secrets.create(
                    secret_actor,
                    target.destination.owner_user_id,
                    self._secret_name(str(next_name)),
                    f"{next_type}-credentials",
                    secret_value,
                )
                self.destinations.set_secret(actor, destination_id, secret.id)

        destination = self._update_destination_record(
            actor,
            destination,
            next_name=next_name,
            next_type=next_type,
            next_settings=next_settings,
            enabled=enabled,
            shared=shared,
        )
        if not destination.shared:
            self._access_store().clear_destination(destination.id)
        if normalized_routes is not None:
            self.relationships.replace_for_destination(
                actor,
                destination_id,
                normalized_routes,
            )
            destination = self.destinations.get(actor, destination_id)
        return APIResponse(
            200,
            {"destination": self._destination_for_actor(destination, actor)},
        )

    def _update_destination_record(
        self,
        actor,
        destination,
        *,
        next_name,
        next_type,
        next_settings,
        enabled,
        shared,
    ):
        """Update an authorized Destination without applying retired Route ownership rules."""

        display, normalized = normalized_name(next_name, "destination name")
        encoded_settings = self.destinations._settings(next_type, next_settings)
        now = int(time.time())
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    UPDATE destinations
                    SET name = ?, name_normalized = ?, output_type = ?,
                        settings_json = ?, shared = ?, enabled = ?, updated_at = ?,
                        configuration_key = NULL
                    WHERE id = ?
                    """,
                    (
                        display,
                        normalized,
                        next_type,
                        encoded_settings,
                        1 if shared else 0,
                        1 if enabled else 0,
                        now,
                        destination.id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ConflictError(
                f"A destination named {display} already exists."
            ) from error
        updated = self.destinations.get(actor, destination.id)
        self.destinations._audit(
            actor,
            "destination.update",
            destination.id,
            "success",
            {"output_type": updated.output_type, "shared": updated.shared},
        )
        return updated

    def _resource_endpoint(self, method, path, payload, actor):
        access = self._access_store()
        permission_match = _USER_DESTINATION_PERMISSIONS.fullmatch(path)
        if permission_match:
            self._require_admin(actor)
            user_id = permission_match.group(1)
            user = self.users.get(user_id)
            if method == "GET":
                return APIResponse(
                    200,
                    {
                        "user": {
                            **self._user(user),
                            "private_destination_count": access.private_destination_count(
                                user_id
                            ),
                        },
                        "destinations": access.list_for_user(actor, user_id),
                    },
                )
            if method == "PUT":
                data = self._object(
                    payload,
                    {
                        "destination_id",
                        "can_edit_destination",
                        "can_manage_filters",
                    },
                )
                if set(data) != {
                    "destination_id",
                    "can_edit_destination",
                    "can_manage_filters",
                }:
                    raise ValueError("all destination permission fields are required")
                result = access.set_for_user(
                    actor,
                    user_id,
                    str(data.get("destination_id") or ""),
                    can_edit_destination=self._boolean(data, "can_edit_destination"),
                    can_manage_filters=self._boolean(data, "can_manage_filters"),
                )
                return APIResponse(200, {"permission": result})
            return self._method_not_allowed("GET, PUT")

        if path == "/api/v2/filters":
            if method != "GET":
                return self._method_not_allowed("GET")
            choices = []
            for destination in self.destinations.list_visible(actor):
                row = access.destination_row(destination.id)
                can_manage = access.can_manage_filters(actor, row)
                if not actor.is_admin and not can_manage:
                    continue
                available = self.filters.available_sources(actor, destination.id)
                choices.append(
                    {
                        "id": destination.id,
                        "name": destination.name,
                        "output_type": destination.output_type,
                        "enabled": destination.enabled,
                        "shared": destination.shared,
                        "owned": actor.user_id == destination.owner_user_id,
                        "can_manage_filters": can_manage,
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
                row = access.destination_row(destination_id)
                access.require_manage_filters(actor, row)
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
                row = access.destination_row(destination_id)
                access.require_manage_filters(actor, row)
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
                row = access.destination_row(destination_id)
                access.require_manage_filters(actor, row)
                self.filters.clear_destination(actor, destination_id)
                return APIResponse(204)
            return self._method_not_allowed("GET, DELETE")

        return super()._resource_endpoint(method, path, payload, actor)

    def _audit_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        if not actor.is_admin:
            return APIResponse(200, {"audit_events": []})
        events = [
            item
            for item in self.audit.list_visible(actor, limit=500)
            if self._access_store().audit_event_visible(actor, item)
        ]
        return APIResponse(200, {"audit_events": self._audit_items(events)})

    def _audit_page_endpoint(self, method, actor, page, size=None) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        page_size = 25
        if size is not None and int(size) in self._AUDIT_PAGE_SIZES:
            page_size = int(size)
        if not actor.is_admin:
            return APIResponse(
                200,
                {
                    "audit_events": [],
                    "pagination": {
                        "page": 1,
                        "page_size": page_size,
                        "total": 0,
                        "total_pages": 1,
                    },
                },
            )
        events = [
            item
            for item in self.audit.list_visible(actor, limit=500)
            if self._access_store().audit_event_visible(actor, item)
        ]
        total = len(events)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current = min(max(1, int(page)), total_pages)
        start = (current - 1) * page_size
        selected = events[start:start + page_size]
        return APIResponse(
            200,
            {
                "audit_events": self._audit_items(selected),
                "pagination": {
                    "page": current,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            },
        )

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
            route_row = connection.execute(
                """
                SELECT COUNT(DISTINCT routes.id) AS total,
                       COUNT(DISTINCT routes.source) AS sources
                FROM routes
                JOIN route_destinations
                  ON route_destinations.route_id = routes.id
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE destinations.enabled = 1
                  AND (destinations.owner_user_id = ? OR destinations.shared = 1)
                """,
                (actor.user_id,),
            ).fetchone()
            destination_row = connection.execute(
                """
                SELECT COUNT(*) FROM destinations
                WHERE enabled = 1 AND (owner_user_id = ? OR shared = 1)
                """,
                (actor.user_id,),
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

    def _health_endpoint(self, method, actor) -> APIResponse:
        response = super()._health_endpoint(method, actor)
        if response.status < 300 and isinstance(response.payload, dict):
            for check in response.payload.get("checks", []):
                if check.get("key") in {"destination_credentials", "routes"}:
                    check["detail"] = (
                        "available"
                        if check.get("status") == "healthy"
                        else "one or more destinations require attention"
                    )
        return response

    def _portability_export(self, method, actor) -> APIResponse:
        response = super()._portability_export(method, actor)
        if method != "GET" or response.status >= 300:
            return response
        document = response.payload.get("document") if isinstance(response.payload, dict) else None
        if not isinstance(document, dict):
            return response
        username = self.users.get(actor.user_id).username
        document["destinations"] = [
            item
            for item in document.get("destinations", [])
            if item.get("shared") is True or item.get("owner") == username
        ]
        return response

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

    def _destination_for_actor(self, item, actor):
        data = self._destination(item)
        row = self._access_store().destination_row(item.id)
        data.update(self._access_store().public_permissions(actor, row))
        return data

    def _destination(self, item):
        data = BasePlatformAPI._destination(item)
        data["owner_username"] = self.users.get(item.owner_user_id).username
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
        data["enabled"] = True
        return data

    @staticmethod
    def _serialization_actor(owner_user_id):
        return Actor(str(owner_user_id), "user")
