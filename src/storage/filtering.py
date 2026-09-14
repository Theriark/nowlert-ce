"""Destination-owned notification filtering, decoupled from route records."""

from __future__ import annotations

import fnmatch
import json
import time
import unicodedata

from dataclasses import replace

from integrations.catalog import canonical_source
from integrations.filtering import filter_schema, filter_schemas, sources_for_input
from models import Notification
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.delivery import DeliverySummary, PlatformDeliveryService
from storage.ownership import Actor, OwnershipPolicy
from storage.routes import Route, RouteStore


_LEGACY_KEYS = {
    "hosts",
    "events",
    "severities",
    "statuses",
    "exclude_hosts",
    "exclude_events",
    "exclude_severities",
    "exclude_statuses",
}


def _normalized(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def _patterns(values) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = values.split(",")
    if not isinstance(values, (list, tuple, set)):
        raise ValueError("filter values must be a list")
    result = []
    for value in values:
        text = _normalized(value)
        if not text:
            continue
        if len(text) > 256:
            raise ValueError("filter values must not exceed 256 characters")
        if text not in result:
            result.append(text)
    if len(result) > 128:
        raise ValueError("a filter field must not exceed 128 values")
    return tuple(result)


def _flatten(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            nested = _flatten(item)
            result.extend(nested)
            result.extend(
                _normalized(f"{key}={entry}")
                for entry in nested
                if _normalized(f"{key}={entry}")
            )
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_flatten(item))
        return result
    text = _normalized(value)
    return [text] if text else []


def _path_values(notification: Notification, path: str) -> list[str]:
    if path.startswith("metadata."):
        current = notification.metadata or {}
        for part in path.split(".")[1:]:
            if not isinstance(current, dict):
                return []
            current = current.get(part)
        return _flatten(current)
    return _flatten(getattr(notification, path, ""))


def _any_pattern(values, patterns) -> bool:
    return any(
        fnmatch.fnmatchcase(value, pattern)
        for value in values
        for pattern in patterns
    )


def _legacy_values(notification: Notification, key: str) -> list[str]:
    metadata = notification.metadata or {}
    if key == "hosts":
        result = []
        for name in ("host", "hostname", "device", "node"):
            result.extend(_flatten(metadata.get(name)))
        return result
    if key == "events":
        result = []
        for name in ("event", "event_type", "event_name"):
            result.extend(_flatten(metadata.get(name)))
        result.extend(_flatten(notification.category))
        result.extend(_flatten(notification.title))
        return result
    if key == "severities":
        result = _flatten(metadata.get("severity"))
        result.extend(_flatten(notification.status))
        return result
    if key == "statuses":
        result = _flatten(notification.status)
        result.extend(_flatten(metadata.get("state")))
        result.extend(_flatten(metadata.get("status")))
        return result
    return []


def _clause_matches(source: str, clause: dict, notification: Notification) -> bool:
    schema = filter_schema(source) or {"fields": []}
    fields = {item["key"]: item for item in schema["fields"]}
    for key, raw_patterns in clause.items():
        excluded = key.startswith("exclude_")
        base_key = key[len("exclude_"):] if excluded else key
        patterns = tuple(raw_patterns)
        if base_key in {"hosts", "events", "severities", "statuses"}:
            values = _legacy_values(notification, base_key)
        else:
            descriptor = fields.get(base_key)
            if descriptor is None:
                return False
            values = []
            for path in descriptor.get("paths", []):
                values.extend(_path_values(notification, path))
        if excluded:
            if values and _any_pattern(values, patterns):
                return False
        elif not values or not _any_pattern(values, patterns):
            return False
    return True


class DestinationFilterStore:
    """Persist policies by destination + canonical integration source."""

    def __init__(
        self,
        database: Database,
        *,
        audit: AuditEventStore | None = None,
        clock=time.time,
        migrate_legacy: bool = True,
    ):
        self.database = database
        self.audit = audit
        self.clock = clock
        if migrate_legacy:
            self.migrate_legacy_route_filters()

    def _destination(self, actor: Actor, destination_id: str, *, write=False):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, owner_user_id, name, output_type, shared, enabled "
                "FROM destinations WHERE id = ?",
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

    def available_sources(self, actor: Actor, destination_id: str) -> tuple[str, ...]:
        """Return built-in integrations reachable through enabled bound Routes."""

        self._destination(actor, destination_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT routes.source, routes.input_type
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                JOIN users ON users.id = routes.owner_user_id
                WHERE route_destinations.destination_id = ?
                  AND routes.enabled = 1
                  AND users.enabled = 1
                ORDER BY routes.priority, routes.name_normalized
                """,
                (str(destination_id),),
            ).fetchall()
        catalogue = filter_schemas()
        catalogue_sources = [item["source"] for item in catalogue]
        found = set()
        for row in rows:
            source = canonical_source(str(row["source"]))
            if source == "*":
                found.update(sources_for_input(str(row["input_type"] or "")))
            elif source in catalogue_sources:
                found.add(source)
        return tuple(source for source in catalogue_sources if source in found)

    def destination_view(self, actor: Actor, destination_id: str) -> dict:
        self.migrate_legacy_route_filters()
        destination = self._destination(actor, destination_id)
        policies = self._policies_for_destination(destination_id)
        integrations = []
        for source in self.available_sources(actor, destination_id):
            schema = filter_schema(source)
            policy = policies.get(source)
            integrations.append(
                {
                    **schema,
                    "configured": bool(policy and policy.get("clauses")),
                    "rules": self._public_rules(source, policy),
                    "legacy_clauses": self._legacy_public(source, policy),
                }
            )
        return {
            "destination": {
                "id": str(destination["id"]),
                "name": str(destination["name"]),
                "output_type": str(destination["output_type"]),
                "enabled": bool(destination["enabled"]),
            },
            "integrations": integrations,
        }

    def list_visible(self, actor: Actor) -> list[dict]:
        self.migrate_legacy_route_filters()
        with self.database.connect() as connection:
            if actor.is_admin:
                destinations = connection.execute(
                    "SELECT id, owner_user_id, name, output_type, shared, enabled "
                    "FROM destinations ORDER BY name_normalized"
                ).fetchall()
            else:
                destinations = connection.execute(
                    "SELECT id, owner_user_id, name, output_type, shared, enabled "
                    "FROM destinations WHERE owner_user_id = ? OR shared = 1 "
                    "ORDER BY name_normalized",
                    (actor.user_id,),
                ).fetchall()
        result = []
        for destination in destinations:
            destination_id = str(destination["id"])
            policies = self._policies_for_destination(destination_id)
            if not policies:
                continue
            available = set(self.available_sources(actor, destination_id))
            active = [source for source in policies if source in available]
            result.append(
                {
                    "destination_id": destination_id,
                    "destination_name": str(destination["name"]),
                    "output_type": str(destination["output_type"]),
                    "enabled": bool(destination["enabled"]),
                    "configured_count": len(policies),
                    "active_count": len(active),
                    "sources": active,
                }
            )
        return result

    def set_rules(
        self,
        actor: Actor,
        destination_id: str,
        source: str,
        rules: dict | None,
    ) -> dict | None:
        self._destination(actor, destination_id, write=True)
        source = canonical_source(source)
        if source not in self.available_sources(actor, destination_id):
            raise ValueError("integration is not enabled for this destination")
        clause = self._normalize_rules(source, rules or {})
        now = int(self.clock())
        with self.database.transaction() as connection:
            if clause:
                encoded = json.dumps(
                    [{key: list(values) for key, values in clause.items()}],
                    sort_keys=True,
                    separators=(",", ":"),
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
                    (str(destination_id), source, encoded, now, now),
                )
            else:
                connection.execute(
                    "DELETE FROM destination_filters WHERE destination_id = ? AND source = ?",
                    (str(destination_id), source),
                )
        self._audit(
            actor,
            "filter.update" if clause else "filter.clear",
            destination_id,
            {"source": source, "configured": bool(clause)},
        )
        return {"version": 1, "clauses": [clause]} if clause else None

    def clear_source(self, actor: Actor, destination_id: str, source: str) -> None:
        self._destination(actor, destination_id, write=True)
        source = canonical_source(source)
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM destination_filters WHERE destination_id = ? AND source = ?",
                (str(destination_id), source),
            )
        self._audit(actor, "filter.clear", destination_id, {"source": source})

    def clear_destination(self, actor: Actor, destination_id: str) -> None:
        self._destination(actor, destination_id, write=True)
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM destination_filters WHERE destination_id = ?",
                (str(destination_id),),
            )
        self._audit(actor, "filter.delete", destination_id)

    def matches(
        self,
        actor: Actor,
        destination_id: str,
        notification: Notification,
    ) -> bool:
        self._destination(actor, destination_id)
        source = canonical_source(notification.source)
        policy = self._policy(destination_id, source)
        clauses = list(policy.get("clauses") or []) if policy else []
        if not clauses:
            return True
        return any(_clause_matches(source, clause, notification) for clause in clauses)

    def migrate_legacy_route_filters(self, *, force: bool = False) -> int:
        """Move route-owned filters to every currently bound Destination."""

        with self.database.connect() as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'destination_filters'"
            ).fetchone()
            relationships = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'route_destinations'"
            ).fetchone()
            if table is None or relationships is None:
                return 0
            pending = connection.execute(
                "SELECT 1 FROM routes WHERE filters_json <> '{}' LIMIT 1"
            ).fetchone()
        if pending is None and not force:
            return 0

        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id, source, input_type, filters_json
                FROM routes
                WHERE filters_json <> '{}'
                ORDER BY priority, name_normalized
                """
            ).fetchall()
            grouped: dict[tuple[str, str], list[dict]] = {}
            migrated_ids = []
            for row in rows:
                try:
                    decoded = json.loads(str(row["filters_json"] or "{}"))
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if not isinstance(decoded, dict) or not decoded:
                    continue
                destination_rows = connection.execute(
                    """
                    SELECT destination_id FROM route_destinations
                    WHERE route_id = ? ORDER BY destination_id
                    """,
                    (str(row["id"]),),
                ).fetchall()
                destination_ids = [str(item["destination_id"]) for item in destination_rows]
                if not destination_ids:
                    # Keep compatibility filters until the Route is assigned.
                    continue
                source = canonical_source(str(row["source"]))
                target_sources = (
                    sources_for_input(str(row["input_type"] or ""))
                    if source == "*"
                    else (source,)
                )
                clause = self._normalize_legacy(decoded)
                if not clause:
                    continue
                wrote = False
                for destination_id in destination_ids:
                    for target_source in target_sources:
                        if filter_schema(target_source) is None:
                            continue
                        grouped.setdefault(
                            (destination_id, target_source), []
                        ).append(clause)
                        wrote = True
                if wrote:
                    migrated_ids.append(str(row["id"]))

            now = int(self.clock())
            for (destination_id, source), clauses in grouped.items():
                existing_row = connection.execute(
                    "SELECT clauses_json, created_at FROM destination_filters "
                    "WHERE destination_id = ? AND source = ?",
                    (destination_id, source),
                ).fetchone()
                existing = self._decode_clauses(
                    existing_row["clauses_json"] if existing_row else "[]"
                )
                combined = list(existing)
                signatures = {
                    json.dumps(
                        {key: list(values) for key, values in item.items()},
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for item in combined
                }
                for clause in clauses:
                    signature = json.dumps(
                        {key: list(values) for key, values in clause.items()},
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    if signature in signatures:
                        continue
                    combined.append(clause)
                    signatures.add(signature)
                encoded = json.dumps(
                    [
                        {key: list(values) for key, values in item.items()}
                        for item in combined
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                )
                created_at = int(existing_row["created_at"]) if existing_row else now
                connection.execute(
                    """
                    INSERT INTO destination_filters(
                        destination_id, source, clauses_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(destination_id, source) DO UPDATE SET
                        clauses_json = excluded.clauses_json,
                        updated_at = excluded.updated_at
                    """,
                    (destination_id, source, encoded, created_at, now),
                )

            if migrated_ids:
                placeholders = ",".join("?" for _ in migrated_ids)
                connection.execute(
                    f"UPDATE routes SET filters_json = '{{}}' WHERE id IN ({placeholders})",
                    tuple(migrated_ids),
                )
        return len(migrated_ids)

    def _policy(self, destination_id: str, source: str) -> dict | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT clauses_json FROM destination_filters "
                "WHERE destination_id = ? AND source = ?",
                (str(destination_id), canonical_source(source)),
            ).fetchone()
        if row is None:
            return None
        return {"version": 1, "clauses": self._decode_clauses(row["clauses_json"])}

    def _policies_for_destination(self, destination_id: str) -> dict[str, dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT source, clauses_json FROM destination_filters "
                "WHERE destination_id = ? ORDER BY source",
                (str(destination_id),),
            ).fetchall()
        return {
            canonical_source(row["source"]): {
                "version": 1,
                "clauses": self._decode_clauses(row["clauses_json"]),
            }
            for row in rows
        }

    @staticmethod
    def _decode_clauses(value) -> list[dict[str, tuple[str, ...]]]:
        try:
            decoded = json.loads(str(value or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(decoded, list):
            return []
        result = []
        for clause in decoded:
            if not isinstance(clause, dict):
                continue
            normalized = {}
            for key, values in clause.items():
                try:
                    patterns = _patterns(values)
                except ValueError:
                    continue
                if patterns:
                    normalized[str(key)] = patterns
            if normalized:
                result.append(normalized)
        return result

    @staticmethod
    def _normalize_legacy(filters: dict) -> dict[str, tuple[str, ...]]:
        result = {}
        for key, values in filters.items():
            if key not in _LEGACY_KEYS:
                continue
            patterns = _patterns(values)
            if patterns:
                result[key] = patterns
        return result

    @staticmethod
    def _normalize_rules(source: str, rules: dict) -> dict[str, tuple[str, ...]]:
        if not isinstance(rules, dict):
            raise ValueError("filter rules must be an object")
        schema = filter_schema(source)
        if schema is None:
            raise ValueError("integration does not support filtering")
        fields = {item["key"]: item for item in schema["fields"]}
        unknown = set(rules) - set(fields)
        if unknown:
            raise ValueError(f"unsupported filter field: {sorted(unknown)[0]}")
        result = {}
        for key, values in rules.items():
            descriptor = fields[key]
            patterns = _patterns(values)
            if not patterns:
                continue
            if descriptor["kind"] == "enum":
                options = {_normalized(value) for value in descriptor.get("values", [])}
                invalid = set(patterns) - options
                if invalid:
                    raise ValueError(f"unsupported {descriptor['label']} value")
                if set(patterns) == options:
                    continue
            result[key] = patterns
        encoded = json.dumps(
            {key: list(values) for key, values in result.items()},
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(encoded.encode("utf-8")) > 32 * 1024:
            raise ValueError("filter rules must not exceed 32768 bytes")
        return result

    @staticmethod
    def _public_rules(source: str, policy: dict | None) -> dict:
        if not policy or len(policy.get("clauses") or []) != 1:
            return {}
        clause = policy["clauses"][0]
        schema = filter_schema(source) or {"fields": []}
        allowed = {item["key"] for item in schema["fields"]}
        if set(clause) - allowed:
            return {}
        return {key: list(values) for key, values in clause.items()}

    @staticmethod
    def _legacy_public(source: str, policy: dict | None) -> list[dict]:
        if not policy or not policy.get("clauses"):
            return []
        clauses = policy["clauses"]
        schema = filter_schema(source) or {"fields": []}
        allowed = {item["key"] for item in schema["fields"]}
        if len(clauses) == 1 and not (set(clauses[0]) - allowed):
            return []
        return [
            {key: list(values) for key, values in clause.items()}
            for clause in clauses
        ]

    def _audit(self, actor, action, destination_id, details=None):
        if self.audit is not None:
            self.audit.write(
                actor,
                action,
                "destination_filter",
                str(destination_id),
                "success",
                details,
            )


class RoutingOnlyRouteStore(RouteStore):
    """Use Routes only for source/input candidates; filtering happens later."""

    def create(
        self,
        actor,
        owner_user_id,
        name,
        source,
        destination_id=None,
        **kwargs,
    ):
        kwargs["filters"] = {}
        return super().create(
            actor,
            owner_user_id,
            name,
            source,
            destination_id,
            **kwargs,
        )

    def update(self, actor, route_id, **kwargs):
        kwargs["filters"] = {}
        return super().update(actor, route_id, **kwargs)

    def matching(
        self,
        actor: Actor,
        owner_user_id: str,
        notification: Notification,
    ) -> list[Route]:
        return [
            replace(route, filters={})
            for route in super().matching(actor, owner_user_id, notification)
        ]


class FilteredPlatformDeliveryService(PlatformDeliveryService):
    """Apply Destination Filtering after Route/Destination candidate resolution."""

    def __init__(self, *args, filters: DestinationFilterStore, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = filters

    def deliver(self, actor: Actor, notification: Notification) -> DeliverySummary:
        self.filters.migrate_legacy_route_filters()
        routes = self.routes.matching(actor, actor.user_id, notification)
        candidates = self.relationships.expand(actor, routes)
        allowed = [
            candidate
            for candidate in candidates
            if self.filters.matches(actor, candidate.destination_id, notification)
        ]
        return self._deliver_candidates(actor, notification, allowed)
