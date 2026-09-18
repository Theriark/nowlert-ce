"""Validated, preview-first platform export and v1 YAML migration."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import unicodedata

from dataclasses import dataclass

import yaml

from integrations.catalog import canonical_source
from outputs.settings import normalize_output_settings, validate_public_https_url
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.destinations import DestinationStore
from storage.ownership import Actor
from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.validation import normalized_name


PORTABLE_SCHEMA = "nowlert.platform.v2"
LEGACY_PORTABLE_SCHEMA = "nowlert.platform.v1"
MAXIMUM_DOCUMENT_BYTES = 1024 * 1024
MAXIMUM_DESTINATIONS = 500
MAXIMUM_ROUTES = 1000
MAXIMUM_FILTERS = 5000
_FILTER_SOURCE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")


@dataclass(frozen=True)
class ImportPlan:
    kind: str
    fingerprint: str
    destinations: tuple[dict, ...]
    routes: tuple[dict, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def public(self) -> dict:
        return {
            "kind": self.kind,
            "fingerprint": self.fingerprint,
            "valid": self.valid,
            "destinations": [
                {
                    "ref": item["ref"],
                    "owner": item["owner"],
                    "name": item["name"],
                    "output_type": item["output_type"],
                    "shared": item["shared"],
                    "enabled": item["enabled"],
                    "secret_present": bool(item.get("secret_value")),
                    "secret_required": bool(item.get("secret_required")),
                    "route_refs": list(item.get("route_refs") or ()),
                    "filtering_enabled": bool(item.get("filtering_enabled", True)),
                    "filters": len(item.get("filters") or ()),
                }
                for item in self.destinations
            ],
            "routes": [
                {
                    "ref": item["ref"],
                    "owner": item["owner"],
                    "name": item["name"],
                    "source": item["source"],
                    "input_type": item.get("input_type", ""),
                    "enabled": item["enabled"],
                }
                for item in self.routes
            ],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "summary": {
                "destinations": len(self.destinations),
                "routes": len(self.routes),
                "filters": sum(len(item.get("filters") or ()) for item in self.destinations),
            },
        }


class PlatformPortabilityService:
    """Export safe metadata and import only after an unchanged preview."""

    def __init__(
        self,
        database: Database,
        *,
        secrets: SecretStore | None = None,
        audit: AuditEventStore | None = None,
        clock=time.time,
    ):
        self.database = database
        self.secrets = secrets or SecretStore(database)
        self.audit = audit
        self.clock = clock
        self.destinations = DestinationStore(database, audit=audit)
        self.routes = RouteStore(database, audit=audit)
        self.relationships = RouteDestinationStore(database, audit=audit)

    def export_document(self, actor: Actor) -> dict:
        self._require_admin(actor)
        with self.database.connect() as connection:
            destination_rows = connection.execute(
                """
                SELECT destinations.*, users.username AS owner_username
                FROM destinations
                JOIN users ON users.id = destinations.owner_user_id
                ORDER BY users.username_normalized, destinations.name_normalized
                """
            ).fetchall()
            route_rows = connection.execute(
                """
                SELECT routes.*, users.username AS owner_username
                FROM routes
                JOIN users ON users.id = routes.owner_user_id
                ORDER BY users.username_normalized, routes.priority,
                         routes.name_normalized
                """
            ).fetchall()
            relationship_rows = connection.execute(
                """
                SELECT route_id, destination_id FROM route_destinations
                ORDER BY destination_id, route_id
                """
            ).fetchall()
            filter_rows = connection.execute(
                """
                SELECT destination_id, source, clauses_json
                FROM destination_filters
                ORDER BY destination_id, source
                """
            ).fetchall()
            filter_state_rows = connection.execute(
                """
                SELECT setting_key, value_json
                FROM settings_records
                WHERE namespace = 'destination_filter_enabled'
                """
            ).fetchall()
            filter_master_rows = connection.execute(
                """
                SELECT setting_key, value_json
                FROM settings_records
                WHERE namespace = 'destination_filter_master_enabled'
                """
            ).fetchall()
        destination_refs = {
            str(row["id"]): f"destination-{index}"
            for index, row in enumerate(destination_rows, start=1)
        }
        route_refs = {
            str(row["id"]): f"route-{index}"
            for index, row in enumerate(route_rows, start=1)
        }
        destination_routes: dict[str, list[str]] = {
            str(row["id"]): [] for row in destination_rows
        }
        for relationship in relationship_rows:
            destination_id = str(relationship["destination_id"])
            route_id = str(relationship["route_id"])
            if destination_id in destination_routes and route_id in route_refs:
                destination_routes[destination_id].append(route_refs[route_id])

        disabled_filters = set()
        for row in filter_state_rows:
            try:
                enabled = bool(json.loads(str(row["value_json"])))
            except (TypeError, ValueError, json.JSONDecodeError):
                enabled = True
            if not enabled:
                disabled_filters.add(str(row["setting_key"]))

        disabled_filtering = set()
        for row in filter_master_rows:
            try:
                enabled = bool(json.loads(str(row["value_json"])))
            except (TypeError, ValueError, json.JSONDecodeError):
                enabled = True
            if not enabled:
                disabled_filtering.add(str(row["setting_key"]))

        destination_filters: dict[str, list[dict]] = {
            str(row["id"]): [] for row in destination_rows
        }
        for row in filter_rows:
            destination_id = str(row["destination_id"])
            if destination_id not in destination_filters:
                continue
            source = canonical_source(str(row["source"]))
            try:
                policy = json.loads(str(row["clauses_json"]))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError("stored destination filter contains invalid JSON") from error
            if not isinstance(policy, (list, dict)):
                raise ValueError("stored destination filter policy is invalid")
            destination_filters[destination_id].append(
                {
                    "source": source,
                    "policy": policy,
                    "enabled": f"{destination_id}:{source}" not in disabled_filters,
                }
            )

        document = {
            "schema": PORTABLE_SCHEMA,
            "exported_at": int(self.clock()),
            "destinations": [
                {
                    "ref": destination_refs[str(row["id"])],
                    "owner": str(row["owner_username"]),
                    "name": str(row["name"]),
                    "output_type": str(row["output_type"]),
                    "settings": json.loads(str(row["settings_json"])),
                    "shared": bool(row["shared"]),
                    "enabled": bool(row["enabled"]),
                    "secret_required": row["secret_id"] is not None,
                    "route_refs": destination_routes[str(row["id"])],
                    "filtering_enabled": str(row["id"]) not in disabled_filtering,
                    "filters": destination_filters[str(row["id"])],
                }
                for row in destination_rows
            ],
            "routes": [
                {
                    "ref": route_refs[str(row["id"])],
                    "owner": str(row["owner_username"]),
                    "name": str(row["name"]),
                    "source": str(row["source"]),
                    "input_type": str(row["input_type"] or ""),
                    "priority": int(row["priority"]),
                    "enabled": bool(row["enabled"]),
                }
                for row in route_rows
            ],
        }
        self._audit(actor, "portability.export", "success", {
            "destinations": len(destination_rows),
            "routes": len(route_rows),
            "filters": sum(len(items) for items in destination_filters.values()),
            "secrets_exported": False,
        })
        return document

    def preview_document(self, actor: Actor, document) -> ImportPlan:
        self._require_admin(actor)
        fingerprint, decoded, size_error = self._json_document(document)
        if size_error:
            return ImportPlan("portable", fingerprint, (), (), (), (size_error,))
        errors: list[str] = []
        warnings: list[str] = []
        destinations: list[dict] = []
        routes: list[dict] = []
        schema = decoded.get("schema") if isinstance(decoded, dict) else None
        if schema not in {PORTABLE_SCHEMA, LEGACY_PORTABLE_SCHEMA}:
            return ImportPlan(
                "portable",
                fingerprint,
                (),
                (),
                (),
                (
                    f"document schema must be {PORTABLE_SCHEMA} "
                    f"or {LEGACY_PORTABLE_SCHEMA}",
                ),
            )
        raw_destinations = decoded.get("destinations", [])
        raw_routes = decoded.get("routes", [])
        if not isinstance(raw_destinations, list):
            errors.append("destinations must be a list")
            raw_destinations = []
        if not isinstance(raw_routes, list):
            errors.append("routes must be a list")
            raw_routes = []
        if len(raw_destinations) > MAXIMUM_DESTINATIONS:
            errors.append(f"destinations must not exceed {MAXIMUM_DESTINATIONS}")
            raw_destinations = []
        if len(raw_routes) > MAXIMUM_ROUTES:
            errors.append(f"routes must not exceed {MAXIMUM_ROUTES}")
            raw_routes = []

        users = self._users()
        existing_destinations, existing_routes = self._existing_names()
        planned_destination_names = set(existing_destinations)
        planned_route_names = set(existing_routes)
        destination_refs: dict[str, dict] = {}
        for index, raw in enumerate(raw_destinations, start=1):
            label = f"destination {index}"
            try:
                item = self._portable_destination(
                    raw,
                    users,
                    allow_filters=schema == PORTABLE_SCHEMA,
                )
                if item["ref"] in destination_refs:
                    raise ValueError("destination reference is duplicated")
                key = (item["owner_id"], item["name_normalized"])
                if key in planned_destination_names:
                    raise ValueError("destination name already exists for this owner")
                planned_destination_names.add(key)
                destination_refs[item["ref"]] = item
                destinations.append(item)
                if item["secret_required"]:
                    warnings.append(
                        f"{item['name']}: credential was intentionally not exported; "
                        "destination will be imported disabled"
                    )
            except (TypeError, ValueError) as error:
                errors.append(f"{label}: {error}")

        route_refs: dict[str, dict] = {}
        for index, raw in enumerate(raw_routes, start=1):
            label = f"route {index}"
            try:
                item = self._portable_route(raw, users, destination_refs, index=index)
                if item["ref"] in route_refs:
                    raise ValueError("route reference is duplicated")
                key = (item["owner_id"], item["name_normalized"])
                if key in planned_route_names:
                    raise ValueError("route name already exists for this owner")
                planned_route_names.add(key)
                route_refs[item["ref"]] = item
                routes.append(item)
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"{label}: {error}")

        # Validate new Destination-owned relationships after both resource sets
        # have been parsed. Translate old Route.destination_ref documents into
        # the same in-memory representation without mutating the submitted data.
        for destination in destinations:
            validated = []
            for route_ref in destination.get("route_refs") or ():
                route = route_refs.get(route_ref)
                if route is None:
                    errors.append(
                        f"destination {destination['name']}: route reference {route_ref!r} does not exist"
                    )
                    continue
                if (
                    route["owner_id"] != destination["owner_id"]
                    and not destination["shared"]
                ):
                    errors.append(
                        f"destination {destination['name']}: route {route['name']} requires an owned or shared destination"
                    )
                    continue
                if route_ref not in validated:
                    validated.append(route_ref)
            destination["route_refs"] = tuple(validated)

        for route in routes:
            legacy_destination_ref = route.pop("legacy_destination_ref", "")
            if not legacy_destination_ref:
                continue
            destination = destination_refs.get(legacy_destination_ref)
            if destination is None:
                errors.append(
                    f"route {route['name']}: destination reference does not exist"
                )
                continue
            if (
                route["owner_id"] != destination["owner_id"]
                and not destination["shared"]
            ):
                errors.append(
                    f"route {route['name']}: destination must be owned or shared"
                )
                continue
            refs = list(destination.get("route_refs") or ())
            if route["ref"] not in refs:
                refs.append(route["ref"])
            destination["route_refs"] = tuple(refs)

        return ImportPlan(
            "portable",
            fingerprint,
            tuple(destinations),
            tuple(routes),
            tuple(warnings),
            tuple(errors),
        )

    def preview_v1_yaml(self, actor: Actor, source: str) -> ImportPlan:
        self._require_admin(actor)
        raw = str(source or "")
        encoded = raw.encode("utf-8")
        fingerprint = hashlib.sha256(encoded).hexdigest()
        if not encoded or len(encoded) > MAXIMUM_DOCUMENT_BYTES:
            message = "YAML document must contain 1 to 1048576 bytes"
            return ImportPlan("v1_yaml", fingerprint, (), (), (), (message,))
        try:
            decoded = yaml.safe_load(raw)
        except yaml.YAMLError:
            return ImportPlan(
                "v1_yaml", fingerprint, (), (), (), ("YAML document is invalid",)
            )
        if not isinstance(decoded, dict):
            return ImportPlan(
                "v1_yaml", fingerprint, (), (), (), ("YAML root must be an object",)
            )
        users = self._users()
        admin_name = users[actor.user_id]["username"]
        existing_destinations, existing_routes = self._existing_names()
        planned_destination_names = set(existing_destinations)
        planned_route_names = set(existing_routes)
        errors: list[str] = []
        warnings: list[str] = []
        destinations: list[dict] = []
        routes: list[dict] = []
        references: dict[tuple[str, str], dict] = {}
        outputs = decoded.get("outputs") or {}
        if not isinstance(outputs, dict):
            errors.append("outputs must be an object")
            outputs = {}
        for output_type in ("discord", "teams"):
            group = outputs.get(output_type) or {}
            if not isinstance(group, dict):
                errors.append(f"outputs.{output_type} must be an object")
                continue
            group_enabled = group.get("enabled", True)
            if not isinstance(group_enabled, bool):
                errors.append(f"outputs.{output_type}.enabled must be a boolean")
                group_enabled = False
            for target, settings in group.items():
                if target == "enabled":
                    continue
                if not isinstance(settings, dict):
                    errors.append(f"outputs.{output_type}.{target} must be an object")
                    continue
                value = str(settings.get("webhook") or "").strip()
                if not value or "PASTE_" in value.upper():
                    warnings.append(
                        f"outputs.{output_type}.{target}: placeholder credential skipped"
                    )
                    continue
                try:
                    validate_public_https_url(value, f"{output_type} webhook")
                    display, normalized = normalized_name(
                        f"Imported {output_type} {target}",
                        "destination name",
                    )
                    key = (actor.user_id, normalized)
                    if key in planned_destination_names:
                        raise ValueError("destination name already exists")
                    planned_destination_names.add(key)
                    reference = f"{output_type}:{target}"
                    item = {
                        "ref": reference,
                        "owner": admin_name,
                        "owner_id": actor.user_id,
                        "name": display,
                        "name_normalized": normalized,
                        "output_type": output_type,
                        "settings": normalize_output_settings(output_type, {}),
                        "shared": True,
                        "enabled": group_enabled,
                        "secret_required": True,
                        "secret_value": value,
                        "route_refs": [],
                    }
                    references[(output_type, str(target))] = item
                    destinations.append(item)
                except (TypeError, ValueError) as error:
                    errors.append(f"outputs.{output_type}.{target}: {error}")

        routing = decoded.get("routing") or {}
        if not isinstance(routing, dict):
            errors.append("routing must be an object")
            routing = {}
        route_position = 0
        for source_name, raw_route in routing.items():
            if not isinstance(raw_route, dict):
                errors.append(f"routing.{source_name} must be an object")
                continue
            entries = raw_route.get("outputs")
            if entries is None:
                entries = [raw_route]
            if not isinstance(entries, list):
                errors.append(f"routing.{source_name}.outputs must be a list")
                continue
            for position, entry in enumerate(entries, start=1):
                try:
                    if not isinstance(entry, dict):
                        raise ValueError("route must be an object")
                    output_type = str(entry.get("output") or "").casefold()
                    target = str(entry.get("target", "default"))
                    destination = references.get((output_type, target))
                    if destination is None:
                        warnings.append(
                            f"routing.{source_name} entry {position}: target was not "
                            "imported and route was skipped"
                        )
                        continue
                    filters = self._v1_filters(entry.get("match"))
                    display, normalized = normalized_name(
                        f"Imported {source_name} to {output_type} {target} {position}",
                        "route name",
                    )
                    key = (actor.user_id, normalized)
                    if key in planned_route_names:
                        raise ValueError("route name already exists")
                    planned_route_names.add(key)
                    source_value = RouteStore._source(source_name)
                    RouteStore._filters(filters)
                    route_position += 1
                    route_ref = f"route-{route_position}"
                    routes.append({
                        "ref": route_ref,
                        "owner": admin_name,
                        "owner_id": actor.user_id,
                        "name": display,
                        "name_normalized": normalized,
                        "source": source_value,
                        "input_type": "",
                        "filters": filters,
                        "priority": min(1000, 100 + position),
                        "enabled": bool(destination["enabled"]),
                    })
                    destination["route_refs"].append(route_ref)
                except (TypeError, ValueError) as error:
                    errors.append(f"routing.{source_name} entry {position}: {error}")
        for destination in destinations:
            destination["route_refs"] = tuple(destination["route_refs"])
        return ImportPlan(
            "v1_yaml",
            fingerprint,
            tuple(destinations),
            tuple(routes),
            tuple(warnings),
            tuple(errors),
        )

    def apply_document(
        self,
        actor: Actor,
        document,
        fingerprint: str,
    ) -> dict:
        with self.database.maintenance():
            plan = self.preview_document(actor, document)
            return self._apply(actor, plan, fingerprint)

    def apply_v1_yaml(
        self,
        actor: Actor,
        source: str,
        fingerprint: str,
    ) -> dict:
        with self.database.maintenance():
            plan = self.preview_v1_yaml(actor, source)
            return self._apply(actor, plan, fingerprint)

    def apply_v1_yaml_with_resources(
        self,
        actor: Actor,
        source: str,
        fingerprint: str,
    ) -> dict:
        """Apply a local migration and retain private rollback handles."""

        with self.database.maintenance():
            plan = self.preview_v1_yaml(actor, source)
            if not plan.valid:
                raise ValueError("import preview contains errors")
            if not fingerprint or not hmac.compare_digest(
                plan.fingerprint,
                str(fingerprint),
            ):
                raise ValueError("import fingerprint does not match the preview")
            return self._apply_plan(actor, plan, include_resources=True)

    def rollback_resources(self, actor: Actor, resources: dict) -> None:
        """Remove only resources created by an interrupted local migration."""

        route_ids = list(resources.get("routes") or ())
        destination_ids = list(resources.get("destinations") or ())
        secret_ids = list(resources.get("secrets") or ())
        with self.database.maintenance():
            for route_id in reversed(route_ids):
                self.routes.delete(actor, route_id)
            for destination_id in reversed(destination_ids):
                self.destinations.delete(actor, destination_id)
            for secret_id in reversed(secret_ids):
                self.secrets.delete(actor, secret_id)

    def _apply(self, actor: Actor, plan: ImportPlan, fingerprint: str) -> dict:
        if not plan.valid:
            raise ValueError("import preview contains errors")
        if not fingerprint or not hmac.compare_digest(
            plan.fingerprint,
            str(fingerprint),
        ):
            raise ValueError("import fingerprint does not match the preview")
        with self.database.maintenance():
            return self._apply_plan(actor, plan)

    def _apply_plan(
        self,
        actor: Actor,
        plan: ImportPlan,
        *,
        include_resources: bool = False,
    ) -> dict:
        created_routes: list[str] = []
        created_destinations: list[str] = []
        created_secrets: list[str] = []
        destination_ids: dict[str, str] = {}
        route_ids: dict[str, str] = {}
        try:
            for item in plan.destinations:
                secret_id = None
                if item.get("secret_value"):
                    metadata = self.secrets.create(
                        actor,
                        item["owner_id"],
                        f"{item['name']} credential",
                        f"{item['output_type']}_credential",
                        item["secret_value"],
                    )
                    secret_id = metadata.id
                    created_secrets.append(metadata.id)
                enabled = bool(item["enabled"] and not (
                    item.get("secret_required") and not secret_id
                ))
                destination = self.destinations.create(
                    actor,
                    item["owner_id"],
                    item["name"],
                    item["output_type"],
                    secret_id=secret_id,
                    settings=item["settings"],
                    shared=item["shared"],
                    enabled=enabled,
                )
                created_destinations.append(destination.id)
                destination_ids[item["ref"]] = destination.id
            for item in plan.routes:
                route = self.routes.create(
                    actor,
                    item["owner_id"],
                    item["name"],
                    item["source"],
                    input_type=item.get("input_type", ""),
                    filters=item["filters"],
                    priority=item["priority"],
                    enabled=item["enabled"],
                )
                created_routes.append(route.id)
                route_ids[item["ref"]] = route.id
            filters_created = 0
            for item in plan.destinations:
                destination_id = destination_ids[item["ref"]]
                selected = [route_ids[ref] for ref in item.get("route_refs") or ()]
                self.relationships.replace_for_destination(
                    actor,
                    destination_id,
                    selected,
                )
                filters_created += self._install_portable_filters(
                    destination_id,
                    item.get("filters") or (),
                    filtering_enabled=bool(item.get("filtering_enabled", True)),
                )
        except Exception:
            self._clear_portable_filter_state(created_destinations)
            for route_id in reversed(created_routes):
                try:
                    self.routes.delete(actor, route_id)
                except Exception:
                    pass
            for destination_id in reversed(created_destinations):
                try:
                    self.destinations.delete(actor, destination_id)
                except Exception:
                    pass
            for secret_id in reversed(created_secrets):
                try:
                    self.secrets.delete(actor, secret_id)
                except Exception:
                    pass
            self._audit(actor, f"portability.{plan.kind}.apply", "failed")
            raise
        result = {
            "kind": plan.kind,
            "destinations_created": len(created_destinations),
            "routes_created": len(created_routes),
            "filters_created": filters_created,
            "warnings": list(plan.warnings),
        }
        self._audit(actor, f"portability.{plan.kind}.apply", "success", result)
        if include_resources:
            return {
                "public": result,
                "resources": {
                    "routes": tuple(created_routes),
                    "destinations": tuple(created_destinations),
                    "secrets": tuple(created_secrets),
                },
            }
        return result

    def _portable_destination(self, raw, users, *, allow_filters: bool = False) -> dict:
        if not isinstance(raw, dict):
            raise ValueError("must be an object")
        allowed = {
            "ref", "owner", "name", "output_type", "settings", "shared",
            "enabled", "secret_required", "route_refs",
        }
        if allow_filters:
            allowed.update({"filters", "filtering_enabled"})
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unsupported field: {sorted(unknown)[0]}")
        reference = str(raw.get("ref") or "").strip()
        if not reference or len(reference) > 128:
            raise ValueError("reference must contain 1 to 128 characters")
        owner = str(raw.get("owner") or "").strip()
        owner_normalized = self._normalized_username(owner)
        owner_record = next(
            (value for value in users.values() if value["normalized"] == owner_normalized),
            None,
        )
        if owner_record is None:
            raise ValueError("owner does not exist on this instance")
        display, normalized = normalized_name(raw.get("name"), "destination name")
        output_type = str(raw.get("output_type") or "").strip().casefold()
        settings = normalize_output_settings(output_type, raw.get("settings") or {})
        shared = self._boolean(raw, "shared", False)
        enabled = self._boolean(raw, "enabled", True)
        required = self._boolean(raw, "secret_required", False)
        raw_route_refs = raw.get("route_refs", [])
        if not isinstance(raw_route_refs, list):
            raise ValueError("route_refs must be a list")
        route_refs = []
        for value in raw_route_refs:
            route_ref = str(value or "").strip()
            if not route_ref or len(route_ref) > 128:
                raise ValueError("route reference must contain 1 to 128 characters")
            if route_ref not in route_refs:
                route_refs.append(route_ref)
        filters = self._portable_filters(raw.get("filters", [])) if allow_filters else ()
        filtering_enabled = raw.get("filtering_enabled", True) if allow_filters else True
        if not isinstance(filtering_enabled, bool):
            raise ValueError("filtering_enabled must be a boolean")
        return {
            "ref": reference,
            "owner": owner_record["username"],
            "owner_id": owner_record["id"],
            "name": display,
            "name_normalized": normalized,
            "output_type": output_type,
            "settings": settings,
            "shared": shared,
            "enabled": enabled,
            "secret_required": required,
            "route_refs": tuple(route_refs),
            "filtering_enabled": filtering_enabled,
            "filters": filters,
        }

    def _portable_filters(self, raw_filters) -> tuple[dict, ...]:
        if not isinstance(raw_filters, list):
            raise ValueError("filters must be a list")
        if len(raw_filters) > MAXIMUM_FILTERS:
            raise ValueError(f"filters must not exceed {MAXIMUM_FILTERS}")
        result = []
        seen = set()
        for position, raw in enumerate(raw_filters, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"filter {position} must be an object")
            unknown = set(raw) - {"source", "policy", "enabled"}
            if unknown:
                raise ValueError(
                    f"filter {position} unsupported field: {sorted(unknown)[0]}"
                )
            source = canonical_source(raw.get("source"))
            if not _FILTER_SOURCE.fullmatch(source):
                raise ValueError(f"filter {position} source is invalid")
            if source in seen:
                raise ValueError(f"filter {position} source is duplicated")
            seen.add(source)
            policy = raw.get("policy")
            if not isinstance(policy, (list, dict)):
                raise ValueError(f"filter {position} policy must be an object or list")
            encoded = json.dumps(
                policy,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            if not encoded or len(encoded.encode("utf-8")) > 64 * 1024:
                raise ValueError(f"filter {position} policy is too large")
            enabled = raw.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(f"filter {position} enabled must be a boolean")
            result.append(
                {"source": source, "policy": policy, "enabled": enabled}
            )
        return tuple(result)

    def _install_portable_filters(
        self,
        destination_id: str,
        filters,
        *,
        filtering_enabled: bool = True,
    ) -> int:
        now = int(self.clock())
        with self.database.transaction() as connection:
            if filtering_enabled:
                connection.execute(
                    """
                    DELETE FROM settings_records
                    WHERE namespace = 'destination_filter_master_enabled'
                      AND setting_key = ?
                    """,
                    (destination_id,),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO settings_records(
                        namespace, setting_key, value_json, updated_at
                    ) VALUES ('destination_filter_master_enabled', ?, 'false', ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (destination_id, now),
                )
            for item in filters:
                source = str(item["source"])
                encoded = json.dumps(
                    item["policy"],
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                connection.execute(
                    """
                    INSERT INTO destination_filters(
                        destination_id, source, clauses_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(destination_id, source) DO UPDATE SET
                        clauses_json = excluded.clauses_json,
                        updated_at = excluded.updated_at
                    """,
                    (destination_id, source, encoded, now, now),
                )
                key = f"{destination_id}:{source}"
                if item["enabled"]:
                    connection.execute(
                        """
                        DELETE FROM settings_records
                        WHERE namespace = 'destination_filter_enabled'
                          AND setting_key = ?
                        """,
                        (key,),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO settings_records(
                            namespace, setting_key, value_json, updated_at
                        ) VALUES ('destination_filter_enabled', ?, 'false', ?)
                        ON CONFLICT(namespace, setting_key) DO UPDATE SET
                            value_json = excluded.value_json,
                            updated_at = excluded.updated_at
                        """,
                        (key, now),
                    )
        return len(filters)

    def _clear_portable_filter_state(self, destination_ids) -> None:
        if not destination_ids:
            return
        with self.database.transaction() as connection:
            for destination_id in destination_ids:
                connection.execute(
                    """
                    DELETE FROM settings_records
                    WHERE namespace = 'destination_filter_enabled'
                      AND setting_key LIKE ?
                    """,
                    (f"{destination_id}:%",),
                )
                connection.execute(
                    """
                    DELETE FROM settings_records
                    WHERE namespace = 'destination_filter_master_enabled'
                      AND setting_key = ?
                    """,
                    (destination_id,),
                )

    def _portable_route(self, raw, users, destination_refs, *, index: int) -> dict:
        if not isinstance(raw, dict):
            raise ValueError("must be an object")
        allowed = {
            "ref", "owner", "name", "source", "input_type", "destination_ref",
            "filters", "priority", "enabled",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unsupported field: {sorted(unknown)[0]}")
        owner = str(raw.get("owner") or "").strip()
        owner_normalized = self._normalized_username(owner)
        owner_record = next(
            (value for value in users.values() if value["normalized"] == owner_normalized),
            None,
        )
        if owner_record is None:
            raise ValueError("owner does not exist on this instance")
        display, normalized = normalized_name(raw.get("name"), "route name")
        reference = str(raw.get("ref") or f"legacy-route-{index}").strip()
        if not reference or len(reference) > 128:
            raise ValueError("route reference must contain 1 to 128 characters")
        source = RouteStore._source(raw.get("source"))
        input_type = RouteStore._input_type(raw.get("input_type", ""))
        filters = raw.get("filters") or {}
        RouteStore._filters(filters)
        priority = int(raw.get("priority", 100))
        if not 0 <= priority <= 1000:
            raise ValueError("route priority must be between 0 and 1000")
        legacy_destination_ref = str(raw.get("destination_ref") or "").strip()
        if legacy_destination_ref and legacy_destination_ref not in destination_refs:
            raise KeyError(legacy_destination_ref)
        return {
            "ref": reference,
            "owner": owner_record["username"],
            "owner_id": owner_record["id"],
            "name": display,
            "name_normalized": normalized,
            "source": source,
            "input_type": input_type,
            "legacy_destination_ref": legacy_destination_ref,
            "filters": filters,
            "priority": priority,
            "enabled": self._boolean(raw, "enabled", True),
        }

    def _users(self) -> dict[str, dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, username, username_normalized FROM users"
            ).fetchall()
        return {
            str(row["id"]): {
                "id": str(row["id"]),
                "username": str(row["username"]),
                "normalized": str(row["username_normalized"]),
            }
            for row in rows
        }

    def _existing_names(self):
        with self.database.connect() as connection:
            destinations = {
                (str(row["owner_user_id"]), str(row["name_normalized"]))
                for row in connection.execute(
                    "SELECT owner_user_id, name_normalized FROM destinations"
                )
            }
            routes = {
                (str(row["owner_user_id"]), str(row["name_normalized"]))
                for row in connection.execute(
                    "SELECT owner_user_id, name_normalized FROM routes"
                )
            }
        return destinations, routes

    @staticmethod
    def _json_document(document):
        try:
            encoded = json.dumps(
                document,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError):
            return "", None, "document must contain JSON values"
        fingerprint = hashlib.sha256(encoded).hexdigest()
        if not encoded or len(encoded) > MAXIMUM_DOCUMENT_BYTES:
            return fingerprint, None, "document must not exceed 1048576 bytes"
        return fingerprint, document, None

    @staticmethod
    def _boolean(value, key, default):
        item = value.get(key, default)
        if not isinstance(item, bool):
            raise ValueError(f"{key} must be a boolean")
        return item

    @staticmethod
    def _v1_filters(value) -> dict:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("match must be an object")
        unknown = set(value) - {"hosts"}
        if unknown:
            raise ValueError(f"unsupported v1 match field: {sorted(unknown)[0]}")
        hosts = value.get("hosts")
        if hosts is None:
            return {}
        return {"hosts": hosts if isinstance(hosts, list) else [hosts]}

    @staticmethod
    def _normalized_username(value: str) -> str:
        return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()

    @staticmethod
    def _require_admin(actor: Actor) -> None:
        if not actor.is_admin:
            raise PermissionError("administrator role is required")

    def _audit(self, actor, action, outcome, details=None):
        if self.audit is not None:
            self.audit.write(actor, action, "platform_state", None, outcome, details)
