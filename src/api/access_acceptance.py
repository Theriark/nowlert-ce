"""Acceptance access model for shared Destinations and owner-private Filtering."""

from __future__ import annotations

import json
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
from storage.routing_flow import record_destination_filter_decision
from storage.system_filtering import SystemDestinationFilterStore


_DESTINATION_FILTER = re.compile(r"/api/v2/filters/destinations/([0-9a-f]{32})")
_DESTINATION_FILTER_ENABLED = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/enabled"
)
_SOURCE_FILTER = re.compile(
    r"/api/v2/filters/destinations/([0-9a-f]{32})/sources/([^/]+)"
)
_MASTER_FILTER_NAMESPACE = "destination_filter_master_enabled"
_FILTER_NAME_NAMESPACE = "destination_filter_name"


class AcceptanceDestinationAccessStore(DestinationAccessStore):
    """Keep Destination mutation owner-only while shared resources remain visible."""

    def can_edit_destination(self, actor, destination) -> bool:
        return actor.user_id == str(destination["owner_user_id"])

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
    """Evaluate owner-private filters with a non-destructive destination master switch."""

    def filter_name(self, destination_id: str) -> str:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings_records "
                "WHERE namespace = ? AND setting_key = ?",
                (_FILTER_NAME_NAMESPACE, str(destination_id)),
            ).fetchone()
        if row is None:
            return ""
        try:
            value = json.loads(str(row["value_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            return ""
        return str(value or "").strip()[:120]

    def set_filter_name(self, actor, destination_id: str, name) -> str:
        self._destination(actor, destination_id, write=True)
        value = str(name or "").strip()
        if len(value) > 120:
            raise ValueError("filter name must be 120 characters or fewer")
        with self.database.transaction() as connection:
            if value:
                connection.execute(
                    """
                    INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        _FILTER_NAME_NAMESPACE,
                        str(destination_id),
                        json.dumps(value),
                        int(self.clock()),
                    ),
                )
            else:
                connection.execute(
                    "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                    (_FILTER_NAME_NAMESPACE, str(destination_id)),
                )
        self._audit(
            actor,
            "filter.destination.rename",
            destination_id,
            {"name": value},
        )
        return value

    def _fallback_integration(self, actor, destination_id: str):
        self._destination(actor, destination_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT routes.id, routes.input_type
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE route_destinations.destination_id = ?
                  AND routes.source = '*'
                ORDER BY routes.priority, routes.name_normalized
                """,
                (str(destination_id),),
            ).fetchall()
        if not rows:
            return None
        input_names = {
            "http": "HTTP",
            "smtp": "SMTP",
            "redfish": "Redfish",
        }
        input_types = []
        route_ids = []
        for row in rows:
            input_type = str(row["input_type"] or "").strip().casefold()
            if input_type and input_type not in input_types:
                input_types.append(input_type)
            route_ids.append(str(row["id"]))
        return {
            "source": "*",
            "name": "Fallback",
            "icon_key": "fallback",
            "category": "Routing",
            "inputs": [
                {"id": input_type, "name": input_names.get(input_type, input_type.upper())}
                for input_type in input_types
            ],
            "fields": [],
            "configured": False,
            "filter_enabled": False,
            "rules": {},
            "legacy_clauses": [],
            "policy_rules": [],
            "fallback": True,
            "configurable": False,
            "route_ids": route_ids,
        }

    def destination_view(self, actor, destination_id):
        view = super().destination_view(actor, destination_id)
        fallback = self._fallback_integration(actor, destination_id)
        if fallback is not None:
            view["integrations"].append(fallback)
        view["filter_name"] = self.filter_name(destination_id)
        return view

    def destination_filtering_enabled(self, destination_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings_records "
                "WHERE namespace = ? AND setting_key = ?",
                (_MASTER_FILTER_NAMESPACE, str(destination_id)),
            ).fetchone()
        if row is None:
            return True
        try:
            return bool(json.loads(str(row["value_json"])))
        except (TypeError, ValueError, json.JSONDecodeError):
            return True

    def _write_destination_filtering_enabled(
        self, destination_id: str, enabled: bool
    ) -> None:
        destination_id = str(destination_id)
        now = int(self.clock())
        with self.database.transaction() as connection:
            if enabled:
                connection.execute(
                    "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                    (_MASTER_FILTER_NAMESPACE, destination_id),
                )
                return

            connection.execute(
                """
                INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
                VALUES (?, ?, 'false', ?)
                ON CONFLICT(namespace, setting_key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (_MASTER_FILTER_NAMESPACE, destination_id, now),
            )
            configured = connection.execute(
                "SELECT source, clauses_json FROM destination_filters "
                "WHERE destination_id = ?",
                (destination_id,),
            ).fetchall()
            for row in configured:
                if not self._decode_policy_rules(row["clauses_json"]):
                    continue
                source = canonical_source(str(row["source"]))
                connection.execute(
                    """
                    INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
                    VALUES ('destination_filter_enabled', ?, 'false', ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (self._state_key(destination_id, source), now),
                )

    def set_destination_filtering_enabled(
        self, actor, destination_id: str, enabled: bool
    ) -> bool:
        self._destination(actor, destination_id, write=True)
        self._write_destination_filtering_enabled(destination_id, enabled)
        self._audit(
            actor,
            "filter.destination.enable" if enabled else "filter.destination.disable",
            destination_id,
            {"enabled": bool(enabled)},
        )
        return bool(enabled)

    def disable_for_destination(self, actor, destination_id: str) -> None:
        """Cascade an authorized Destination disable into Filtering state."""

        self._write_destination_filtering_enabled(destination_id, False)
        self._audit(
            actor,
            "filter.destination.disable",
            destination_id,
            {"enabled": False, "reason": "destination_disabled"},
        )

    def clear_destination(self, actor, destination_id: str) -> None:
        super().clear_destination(actor, destination_id)
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                (_MASTER_FILTER_NAMESPACE, str(destination_id)),
            )
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                (_FILTER_NAME_NAMESPACE, str(destination_id)),
            )

    def matches(self, actor, destination_id: str, notification) -> bool:
        matched = True
        if self.destination_filtering_enabled(destination_id):
            source = canonical_source(notification.source)
            policy = self._policy(destination_id, source)
            policy_rules = list(policy.get("policy_rules") or []) if policy else []
            if policy_rules and self.filter_enabled(destination_id, source):
                block_rules = [
                    item for item in policy_rules if item["action"] == "block"
                ]
                allow_rules = [
                    item for item in policy_rules if item["action"] == "allow"
                ]
                if any(
                    _clause_matches(source, item["conditions"], notification)
                    for item in block_rules
                ):
                    matched = False
                elif allow_rules:
                    matched = any(
                        _clause_matches(source, item["conditions"], notification)
                        for item in allow_rules
                    )

        record_destination_filter_decision(
            self.database,
            actor,
            destination_id,
            notification,
            matched,
        )
        return matched


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

        response = super()._destination_resource(
            method,
            payload,
            actor,
            destination_id,
            action,
        )
        if (
            action is None
            and method == "PATCH"
            and not self.yaml_resource_authority
            and response.status < 300
            and isinstance(payload, dict)
            and "enabled" in payload
            and isinstance(response.payload, dict)
            and isinstance(response.payload.get("destination"), dict)
            and response.payload["destination"].get("enabled") is False
        ):
            self.filters.disable_for_destination(actor, destination_id)
        return response

    def _owner_filter_destination(self, actor, destination_id: str):
        row = self.destination_access.destination_row(destination_id)
        if actor.user_id != str(row["owner_user_id"]):
            raise PermissionError("destination filtering is private to its owner")
        return row

    @staticmethod
    def _sanitized_integration(item, *, effective_enabled: bool) -> dict:
        return {
            "source": item["source"],
            "name": item.get("name"),
            "inputs": list(item.get("inputs") or []),
            "configured": True,
            "filter_enabled": bool(effective_enabled),
            "restricted": True,
            "fields": [],
            "rules": {},
            "legacy_clauses": [],
            "policy_rules": [],
        }

    def _filters_overview(self, actor) -> APIResponse:
        self.filters.migrate_legacy_route_filters()
        choices = []
        policies = []
        for destination in self.destinations.list_visible(actor):
            row = self.destination_access.destination_row(destination.id)
            owned = actor.user_id == destination.owner_user_id
            can_manage = self.destination_access.can_manage_filters(actor, row)
            available = self.filters.available_sources(actor, destination.id)
            master_enabled = self.filters.destination_filtering_enabled(destination.id)
            if owned and can_manage:
                choices.append(
                    {
                        "id": destination.id,
                        "name": destination.name,
                        "output_type": destination.output_type,
                        "enabled": destination.enabled,
                        "shared": destination.shared,
                        "owned": True,
                        "can_manage_filters": True,
                        "can_change_sharing": bool(owned),
                        "filtering_enabled": master_enabled,
                        "available_integration_count": len(available),
                    }
                )

            stored = self.filters._policies_for_destination(destination.id)
            if not stored:
                continue
            view = self.filters.destination_view(actor, destination.id)
            configured = [
                item for item in view["integrations"] if item.get("configured")
            ]
            if not configured:
                continue

            managed_by_admin = False
            if not owned:
                owner = self.destination_access._user_row(destination.owner_user_id)
                managed_by_admin = bool(destination.shared) and str(owner["role"]) == "admin"
                if not managed_by_admin:
                    continue

            effective = [
                bool(master_enabled and item.get("filter_enabled", True))
                for item in configured
            ]
            public_integrations = (
                [
                    {**item, "filter_enabled": enabled}
                    for item, enabled in zip(configured, effective)
                ]
                if owned
                else [
                    self._sanitized_integration(item, effective_enabled=enabled)
                    for item, enabled in zip(configured, effective)
                ]
            )
            policies.append(
                {
                    "destination_id": destination.id,
                    "destination_name": destination.name,
                    "output_type": destination.output_type,
                    "enabled": destination.enabled,
                    "shared": destination.shared,
                    "owned": owned,
                    "can_manage_filters": bool(can_manage),
                    "can_change_sharing": bool(owned),
                    "managed_by_admin": managed_by_admin,
                    "filtering_enabled": master_enabled,
                    "filter_name": self.filters.filter_name(destination.id),
                    "configured_count": len(configured),
                    "active_count": sum(effective),
                    "available_count": len(view["integrations"]),
                    "sources": [
                        item["source"]
                        for item, enabled in zip(configured, effective)
                        if enabled
                    ],
                    "integrations": public_integrations,
                    "unconfigured_integrations": (
                        [
                            {"source": item["source"], "name": item.get("name")}
                            for item in view["integrations"]
                            if not item.get("configured")
                        ]
                        if owned
                        else []
                    ),
                }
            )

        return APIResponse(
            200,
            {
                "filters": policies,
                "destinations": choices,
                "private_resources": [],
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

        enabled_match = _DESTINATION_FILTER_ENABLED.fullmatch(path)
        if enabled_match:
            destination_id = enabled_match.group(1)
            self._owner_filter_destination(actor, destination_id)
            if method == "GET":
                return APIResponse(
                    200,
                    {
                        "destination_id": destination_id,
                        "enabled": self.filters.destination_filtering_enabled(
                            destination_id
                        ),
                    },
                )
            if method == "PUT":
                data = self._object(payload, {"enabled"})
                if set(data) != {"enabled"} or not isinstance(data["enabled"], bool):
                    raise ValueError("enabled must be a boolean")
                enabled = self.filters.set_destination_filtering_enabled(
                    actor, destination_id, data["enabled"]
                )
                return APIResponse(
                    200,
                    {"destination_id": destination_id, "enabled": enabled},
                )
            return self._method_not_allowed("GET, PUT")

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
        if destination_match:
            destination_id = destination_match.group(1)
            self._owner_filter_destination(actor, destination_id)
            if method == "GET":
                view = self.filters.destination_view(actor, destination_id)
                view["destination"]["filtering_enabled"] = (
                    self.filters.destination_filtering_enabled(destination_id)
                )
                return APIResponse(200, view)
            if method == "PUT":
                data = self._object(payload, {"name"})
                if set(data) != {"name"}:
                    raise ValueError("filter name is required")
                name = data.get("name")
                if not isinstance(name, str):
                    raise ValueError("filter name must be a string")
                return APIResponse(
                    200,
                    {
                        "destination_id": destination_id,
                        "filter_name": self.filters.set_filter_name(
                            actor, destination_id, name
                        ),
                    },
                )

        return super()._resource_endpoint(method, path, payload, actor)
