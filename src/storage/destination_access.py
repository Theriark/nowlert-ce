"""Destination-specific visibility and delegated management for the WebUI platform."""

from __future__ import annotations

import json
import time

from dataclasses import replace

from integrations.catalog import canonical_source
from models import Notification
from storage.delivery import DeliveryHistoryStore
from storage.destinations import DeliveryDestination, DestinationStore
from storage.filtering import RoutingOnlyRouteStore
from storage.filtering_toggle import DestinationFilterStore as ToggleDestinationFilterStore
from storage.ownership import Actor, OwnershipPolicy
from storage.route_destinations import RouteDestinationCandidate, RouteDestinationStore


_PERMISSION_NAMESPACE = "destination_user_permissions"


class DestinationAccessStore:
    """Resolve owner/shared visibility and per-user delegated permissions."""

    def __init__(self, database, *, audit=None, clock=time.time):
        self.database = database
        self.audit = audit
        self.clock = clock

    @staticmethod
    def _key(destination_id: str, user_id: str) -> str:
        return f"{str(destination_id)}:{str(user_id)}"

    def destination_row(self, destination_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM destinations WHERE id = ?",
                (str(destination_id),),
            ).fetchone()
        if row is None:
            raise KeyError("destination not found")
        return row

    def _user_row(self, user_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, username, role, enabled FROM users WHERE id = ?",
                (str(user_id),),
            ).fetchone()
        if row is None:
            raise KeyError("user not found")
        return row

    def permissions(self, destination_id: str, user_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings_records "
                "WHERE namespace = ? AND setting_key = ?",
                (_PERMISSION_NAMESPACE, self._key(destination_id, user_id)),
            ).fetchone()
        if row is None:
            return {"can_edit_destination": False, "can_manage_filters": False}
        try:
            value = json.loads(str(row["value_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            value = {}
        return {
            "can_edit_destination": value.get("can_edit_destination") is True,
            "can_manage_filters": value.get("can_manage_filters") is True,
        }

    def can_view(self, actor: Actor, destination) -> bool:
        owner_user_id = str(destination["owner_user_id"])
        return actor.user_id == owner_user_id or bool(destination["shared"])

    def can_edit_destination(self, actor: Actor, destination) -> bool:
        owner_user_id = str(destination["owner_user_id"])
        if actor.user_id == owner_user_id:
            return True
        if not bool(destination["shared"]):
            return False
        if actor.is_admin:
            return True
        return self.permissions(str(destination["id"]), actor.user_id)[
            "can_edit_destination"
        ]

    def can_manage_filters(self, actor: Actor, destination) -> bool:
        owner_user_id = str(destination["owner_user_id"])
        if actor.user_id == owner_user_id:
            return True
        if not bool(destination["shared"]):
            return False
        if actor.is_admin:
            return True
        return self.permissions(str(destination["id"]), actor.user_id)[
            "can_manage_filters"
        ]

    def require_view(self, actor: Actor, destination) -> None:
        if not self.can_view(actor, destination):
            raise PermissionError("destination is not available to this user")

    def require_edit_destination(self, actor: Actor, destination) -> None:
        if not self.can_edit_destination(actor, destination):
            raise PermissionError("destination cannot be changed by this user")

    def require_manage_filters(self, actor: Actor, destination) -> None:
        if not self.can_manage_filters(actor, destination):
            raise PermissionError("destination filters cannot be changed by this user")

    def public_permissions(self, actor: Actor, destination) -> dict:
        owner = actor.user_id == str(destination["owner_user_id"])
        return {
            "owned": owner,
            "can_edit_destination": self.can_edit_destination(actor, destination),
            "can_manage_filters": self.can_manage_filters(actor, destination),
        }

    def private_destination_count(self, user_id: str) -> int:
        self._user_row(user_id)
        with self.database.connect() as connection:
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM destinations "
                    "WHERE owner_user_id = ? AND shared = 0",
                    (str(user_id),),
                ).fetchone()[0]
            )

    def list_for_user(self, actor: Actor, user_id: str) -> list[dict]:
        if not actor.is_admin:
            raise PermissionError("administrator access is required")
        user = self._user_row(user_id)
        if str(user["role"]) != "user":
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, owner_user_id, name, output_type, shared, enabled
                FROM destinations
                WHERE shared = 1 AND owner_user_id <> ?
                ORDER BY name_normalized
                """,
                (str(user_id),),
            ).fetchall()
        result = []
        for row in rows:
            permission = self.permissions(str(row["id"]), str(user_id))
            result.append(
                {
                    "destination_id": str(row["id"]),
                    "name": str(row["name"]),
                    "output_type": str(row["output_type"]),
                    "enabled": bool(row["enabled"]),
                    **permission,
                }
            )
        return result

    def set_for_user(
        self,
        actor: Actor,
        user_id: str,
        destination_id: str,
        *,
        can_edit_destination: bool,
        can_manage_filters: bool,
    ) -> dict:
        if not actor.is_admin:
            raise PermissionError("administrator access is required")
        user = self._user_row(user_id)
        if str(user["role"]) != "user":
            raise ValueError("destination permissions apply only to normal users")
        destination = self.destination_row(destination_id)
        if not bool(destination["shared"]):
            raise ValueError("permissions can be granted only for shared destinations")
        if str(destination["owner_user_id"]) == str(user_id):
            raise ValueError("destination owners already have full access")
        value = {
            "can_edit_destination": bool(can_edit_destination),
            "can_manage_filters": bool(can_manage_filters),
        }
        key = self._key(destination_id, user_id)
        now = int(self.clock())
        with self.database.transaction() as connection:
            if any(value.values()):
                connection.execute(
                    """
                    INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        _PERMISSION_NAMESPACE,
                        key,
                        json.dumps(value, sort_keys=True, separators=(",", ":")),
                        now,
                    ),
                )
            else:
                connection.execute(
                    "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                    (_PERMISSION_NAMESPACE, key),
                )
        if self.audit is not None:
            self.audit.write(
                actor,
                "destination.permission.update",
                "destination",
                str(destination_id),
                "success",
                {"user_id": str(user_id), **value},
            )
        return {"destination_id": str(destination_id), "user_id": str(user_id), **value}

    def clear_destination(self, destination_id: str) -> None:
        prefix = f"{str(destination_id)}:"
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key LIKE ?",
                (_PERMISSION_NAMESPACE, f"{prefix}%"),
            )

    def clear_user(self, user_id: str) -> None:
        suffix = f":{str(user_id)}"
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key LIKE ?",
                (_PERMISSION_NAMESPACE, f"%{suffix}"),
            )

    def audit_event_visible(self, actor: Actor, event) -> bool:
        if event.resource_type not in {"destination", "destination_filter"}:
            return True
        if event.resource_id:
            try:
                row = self.destination_row(str(event.resource_id))
            except KeyError:
                row = None
            if row is not None:
                return self.can_view(actor, row)
        if event.actor_user_id:
            try:
                user = self._user_row(str(event.actor_user_id))
            except KeyError:
                user = None
            if user is not None and str(user["role"]) == "user":
                return False
        return True


class AccessControlledDestinationStore(DestinationStore):
    """Destination store that hides private user resources from administrators."""

    def __init__(self, database, *, access=None, audit=None, clock=time.time):
        super().__init__(database, audit=audit, clock=clock)
        self.access = access or DestinationAccessStore(
            database, audit=audit, clock=clock
        )

    @staticmethod
    def _elevated(actor: Actor) -> Actor:
        return actor if actor.is_admin else Actor(actor.user_id, "admin")

    def get(self, actor: Actor, destination_id: str):
        row = self._record(destination_id)
        self.access.require_view(actor, row)
        return self._destination(row)

    def list_visible_safe(self, actor: Actor):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM destinations
                WHERE owner_user_id = ? OR shared = 1
                ORDER BY name_normalized
                """,
                (actor.user_id,),
            ).fetchall()
        items = []
        errors = []
        for row in rows:
            try:
                items.append(self._destination(row))
            except Exception as error:
                errors.append(
                    {
                        "resource_id": str(row["id"]),
                        "resource": str(row["name"]),
                        "code": "destination_record_invalid",
                        "message": f"Destination {str(row['name'])!r} could not be loaded: {error}",
                    }
                )
        return items, errors

    def for_delivery_metadata(self, actor: Actor, destination_id: str) -> DeliveryDestination:
        row = self._record(destination_id)
        self.access.require_view(actor, row)
        return DeliveryDestination(
            self._destination(row),
            str(row["secret_id"]) if row["secret_id"] is not None else None,
        )

    def record_test_result(self, actor, destination_id, result):
        row = self._record(destination_id)
        self.access.require_edit_destination(actor, row)
        return super().record_test_result(
            self._elevated(actor), destination_id, result
        )

    def set_enabled(self, actor, destination_id, enabled):
        row = self._record(destination_id)
        self.access.require_edit_destination(actor, row)
        return super().set_enabled(self._elevated(actor), destination_id, enabled)

    def set_shared(self, actor, destination_id, shared):
        row = self._record(destination_id)
        if str(row["owner_user_id"]) != actor.user_id:
            raise PermissionError("only the destination owner can change sharing")
        self.access.require_view(actor, row)
        return super().set_shared(actor, destination_id, shared)

    def update(self, actor, destination_id, **kwargs):
        row = self._record(destination_id)
        self.access.require_edit_destination(actor, row)
        if "shared" in kwargs and kwargs["shared"] is not None:
            if (
                bool(kwargs["shared"]) != bool(row["shared"])
                and str(row["owner_user_id"]) != actor.user_id
            ):
                raise PermissionError("only the destination owner can change sharing")
        settings = kwargs.get("settings")
        if (
            not actor.is_admin
            and isinstance(settings, dict)
            and settings.get("allow_private_network")
        ):
            raise PermissionError(
                "only administrators can allow private-network destinations"
            )
        return super().update(self._elevated(actor), destination_id, **kwargs)

    def update_settings(self, actor, destination_id, settings):
        row = self._record(destination_id)
        self.access.require_edit_destination(actor, row)
        if (
            not actor.is_admin
            and isinstance(settings, dict)
            and settings.get("allow_private_network")
        ):
            raise PermissionError(
                "only administrators can allow private-network destinations"
            )
        return super().update_settings(
            self._elevated(actor), destination_id, settings
        )

    def set_secret(self, actor, destination_id, secret_id):
        row = self._record(destination_id)
        self.access.require_edit_destination(actor, row)
        return super().set_secret(
            self._elevated(actor), destination_id, secret_id
        )

    def delete(self, actor, destination_id):
        row = self._record(destination_id)
        owner = str(row["owner_user_id"]) == actor.user_id
        if not owner:
            raise PermissionError("destination cannot be deleted by this user")
        self.access.require_view(actor, row)
        result = super().delete(self._elevated(actor), destination_id)
        self.access.clear_destination(destination_id)
        return result


class AccessControlledDestinationFilterStore(ToggleDestinationFilterStore):
    """Destination filtering with owner or explicitly delegated write authority."""

    def __init__(self, database, *, access=None, **kwargs):
        self.access = access or DestinationAccessStore(database)
        super().__init__(database, **kwargs)

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
            self.access.require_manage_filters(actor, row)
        else:
            self.access.require_view(actor, row)
        return row

    def destination_view(self, actor, destination_id):
        view = super().destination_view(actor, destination_id)
        row = self.access.destination_row(destination_id)
        view["destination"].update(
            {
                "shared": bool(row["shared"]),
                **self.access.public_permissions(actor, row),
            }
        )
        return view

    def list_visible(self, actor):
        self.migrate_legacy_route_filters()
        with self.database.connect() as connection:
            destinations = connection.execute(
                """
                SELECT id, owner_user_id, name, output_type, shared, enabled
                FROM destinations
                WHERE owner_user_id = ? OR shared = 1
                ORDER BY name_normalized
                """,
                (actor.user_id,),
            ).fetchall()
        result = []
        for destination in destinations:
            destination_id = str(destination["id"])
            policies = self._policies_for_destination(destination_id)
            if not policies:
                continue
            view = self.destination_view(actor, destination_id)
            active = [
                item["source"]
                for item in view["integrations"]
                if item.get("configured") and item.get("filter_enabled")
            ]
            result.append(
                {
                    "destination_id": destination_id,
                    "destination_name": str(destination["name"]),
                    "output_type": str(destination["output_type"]),
                    "enabled": bool(destination["enabled"]),
                    "shared": bool(destination["shared"]),
                    **self.access.public_permissions(actor, destination),
                    "configured_count": len(active),
                    "active_count": len(active),
                    "available_count": len(view["integrations"]),
                    "sources": active,
                }
            )
        return result


class SystemRoutingRouteStore(RoutingOnlyRouteStore):
    """Expose Route definitions as always-available system integration plumbing."""

    def _visible_destination_ids(self, actor: Actor, route_id: str) -> tuple[str, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT destinations.id
                FROM route_destinations
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE route_destinations.route_id = ?
                  AND (destinations.owner_user_id = ? OR destinations.shared = 1)
                ORDER BY destinations.name_normalized, destinations.id
                """,
                (str(route_id), actor.user_id),
            ).fetchall()
        return tuple(str(row["id"]) for row in rows)

    def _for_actor(self, actor: Actor, row):
        route = self._route(row)
        return replace(
            route,
            enabled=True,
            filters={},
            destination_ids=self._visible_destination_ids(actor, str(row["id"])),
        )

    def get(self, actor: Actor, route_id: str):
        row = self._record(route_id)
        return self._for_actor(actor, row)

    def list_visible_safe(self, actor: Actor):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM routes ORDER BY priority, name_normalized"
            ).fetchall()
        items = []
        errors = []
        for row in rows:
            try:
                items.append(self._for_actor(actor, row))
            except Exception as error:
                errors.append(
                    {
                        "resource_id": str(row["id"]),
                        "resource": str(row["name"]),
                        "code": "route_record_invalid",
                        "message": f"Route {str(row['name'])!r} could not be loaded: {error}",
                    }
                )
        return items, errors

    def matching(self, actor: Actor, owner_user_id: str, notification: Notification):
        source = canonical_source(notification.source)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM routes
                WHERE (source = ? OR source = '*')
                ORDER BY priority, name_normalized
                """,
                (source,),
            ).fetchall()
        routes = [self._for_actor(actor, row) for row in rows]
        matched = [route for route in routes if self.matches(route, notification)]
        specific = [route for route in matched if route.source != "*"]
        return specific if specific else [route for route in matched if route.source == "*"]


class AccessControlledRouteDestinationStore(RouteDestinationStore):
    """Allow editable Destinations to select system Routes regardless of Route owner."""

    def __init__(self, database, *, access=None, **kwargs):
        self.access = access or DestinationAccessStore(database)
        super().__init__(database, **kwargs)

    def _destination(self, actor: Actor, destination_id: str, *, write: bool):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, owner_user_id, shared, enabled "
                "FROM destinations WHERE id = ?",
                (str(destination_id),),
            ).fetchone()
        if row is None:
            raise KeyError("destination not found")
        if write:
            self.access.require_edit_destination(actor, row)
        else:
            self.access.require_view(actor, row)
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

    def validate_for_destination(self, actor, destination_id, route_ids):
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
            self._route(actor, route_id, write=False)
        return destination, normalized

    def destination_ids_for_route(self, actor, route_id):
        self._route(actor, route_id, write=False)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT destinations.id
                FROM route_destinations
                JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE route_destinations.route_id = ?
                  AND (destinations.owner_user_id = ? OR destinations.shared = 1)
                ORDER BY destinations.name_normalized, destinations.id
                """,
                (str(route_id), actor.user_id),
            ).fetchall()
        return tuple(str(row["id"]) for row in rows)

    def expand(self, actor: Actor, routes):
        result = []
        seen_destinations = set()
        for route in routes:
            with self.database.connect() as connection:
                rows = connection.execute(
                    """
                    SELECT destinations.id, destinations.owner_user_id,
                           destinations.shared, destinations.enabled
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
                if not self.access.can_view(actor, row):
                    continue
                destination_id = str(row["id"])
                if destination_id in seen_destinations:
                    continue
                seen_destinations.add(destination_id)
                result.append(RouteDestinationCandidate(route, destination_id))
        return result


class AccessControlledDeliveryHistoryStore(DeliveryHistoryStore):
    """History visibility follows the same owner-or-shared Destination boundary."""

    @staticmethod
    def _visible_where(alias: str = "attempts") -> str:
        return (
            f"({alias}.owner_user_id = ? OR EXISTS ("
            "SELECT 1 FROM destinations AS visible_destination "
            f"WHERE visible_destination.id = {alias}.destination_id "
            "AND visible_destination.shared = 1))"
        )

    def get(self, actor: Actor, attempt_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT attempts.* FROM delivery_attempts AS attempts "
                f"WHERE attempts.id = ? AND {self._visible_where()}",
                (str(attempt_id), actor.user_id),
            ).fetchone()
        if row is None:
            raise KeyError("delivery attempt not found")
        return self._attempt(row)

    def list_visible(self, actor: Actor, limit: int = 100, offset: int = 0):
        bounded = max(1, min(int(limit), 500))
        bounded_offset = max(0, int(offset))
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT attempts.* FROM delivery_attempts AS attempts
                WHERE {self._visible_where()}
                ORDER BY attempts.created_at DESC, attempts.id
                LIMIT ? OFFSET ?
                """,
                (actor.user_id, bounded, bounded_offset),
            ).fetchall()
        return [self._attempt(row) for row in rows]

    def count_visible(self, actor: Actor) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM delivery_attempts AS attempts "
                f"WHERE {self._visible_where()}",
                (actor.user_id,),
            ).fetchone()
        return int(row[0] or 0)

    def metrics(self, actor: Actor, since: int) -> dict:
        where = f"attempts.created_at >= ? AND {self._visible_where('attempts')}"
        parameters = (int(since), actor.user_id)
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                WITH latest AS (
                    SELECT attempts.delivery_id, MAX(attempts.attempt_number) AS attempt_number
                    FROM delivery_attempts AS attempts
                    WHERE {where}
                    GROUP BY attempts.delivery_id
                )
                SELECT
                    COUNT(*) AS requests,
                    SUM(CASE WHEN attempts.outcome = 'delivered' THEN 1 ELSE 0 END) AS delivered
                FROM latest
                JOIN delivery_attempts AS attempts
                  ON attempts.delivery_id = latest.delivery_id
                 AND attempts.attempt_number = latest.attempt_number
                """,
                parameters,
            ).fetchone()
            sources = connection.execute(
                f"SELECT COUNT(DISTINCT attempts.source) "
                f"FROM delivery_attempts AS attempts WHERE {where}",
                parameters,
            ).fetchone()[0]
        requests = int(row["requests"] or 0)
        delivered = int(row["delivered"] or 0)
        return {
            "requests": requests,
            "delivered": delivered,
            "success_percent": round(delivered * 100 / requests) if requests else None,
            "sources": int(sources or 0),
        }
