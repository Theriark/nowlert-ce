"""Database-backed, secret-safe audit events for v2 platform operations."""

from __future__ import annotations

import json
import re
import time

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable

from storage.database import Database
from storage.ownership import Actor
from storage.sanitize import sanitize_text
from storage.validation import normalized_identifier


_SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|cookie|password|secret|token|webhook|api[_-]?key)"
)


@dataclass(frozen=True)
class AuditEvent:
    id: int
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    details: dict
    created_at: int


class AuditEventStore:
    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.database = database
        self.clock = clock
        self._request_context = ContextVar(
            f"nowlert_audit_request_context_{id(self)}",
            default=None,
        )

    @contextmanager
    def request_scope(
        self,
        *,
        method: str,
        path: str,
        client: str,
        user_agent: str = "",
    ):
        """Attach bounded, non-secret HTTP context to audit writes in one request."""

        safe_path = str(path or "").split("?", 1)[0]
        context = {
            "request_method": sanitize_text(method)[:16].upper(),
            "request_path": sanitize_text(safe_path)[:256],
            "request_client": sanitize_text(client)[:128],
        }
        if user_agent:
            context["request_user_agent"] = sanitize_text(user_agent)[:256]
        token = self._request_context.set(context)
        try:
            yield
        finally:
            self._request_context.reset(token)

    def write(
        self,
        actor: Actor | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        outcome: str,
        details: dict | None = None,
    ) -> int:
        _action, normalized_action = normalized_identifier(
            action,
            "audit action",
            maximum=64,
        )
        _resource, normalized_resource = normalized_identifier(
            resource_type,
            "audit resource type",
            maximum=64,
        )
        _outcome, normalized_outcome = normalized_identifier(
            outcome,
            "audit outcome",
            maximum=32,
        )
        supplied_details = {} if details is None else details
        if not isinstance(supplied_details, dict):
            raise ValueError("audit details must be an object")
        request_context = self._request_context.get() or {}
        safe_details = self._safe_details({**supplied_details, **request_context})
        now = int(self.clock())
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events(
                    actor_user_id, action, resource_type, resource_id,
                    outcome, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    actor.user_id if actor else None,
                    normalized_action,
                    normalized_resource,
                    str(resource_id)[:128] if resource_id else None,
                    normalized_outcome,
                    json.dumps(safe_details, sort_keys=True, separators=(",", ":")),
                    now,
                ),
            )
        return int(cursor.lastrowid)

    def list_visible(
        self, actor: Actor, limit: int = 100, offset: int = 0, **filters
    ) -> list[AuditEvent]:
        bounded = max(1, min(int(limit), 500))
        bounded_offset = max(0, int(offset))
        where, parameters = self._query_where(actor, filters)
        direction = "ASC" if filters.get("sort") == "oldest" else "DESC"
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM audit_events WHERE {where} ORDER BY id {direction} LIMIT ? OFFSET ?",
                (*parameters, bounded, bounded_offset),
            ).fetchall()
        return [self._event(row) for row in rows]

    def count_visible(self, actor: Actor, **filters) -> int:
        where, parameters = self._query_where(actor, filters)
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) FROM audit_events WHERE {where}", parameters,
            ).fetchone()
        return int(row[0] or 0)

    def filter_options(self, actor: Actor) -> dict:
        where, parameters = self._query_where(actor, {})
        with self.database.connect() as connection:
            return {
                key: [row[0] for row in connection.execute(
                    f"SELECT DISTINCT {field} FROM audit_events WHERE {where} AND {field} != '' ORDER BY {field}",
                    parameters,
                )]
                for key, field in (("actions", "action"), ("outcomes", "outcome"))
            }

    @classmethod
    def _query_where(cls, actor: Actor, filters: dict) -> tuple[str, list]:
        visibility, visibility_parameters = cls._visibility(actor)
        clauses = [visibility]
        parameters = list(visibility_parameters)
        for field in ("action", "outcome"):
            if filters.get(field):
                clauses.append(f"{field} = ?")
                parameters.append(filters[field])
        if filters.get("since") is not None:
            clauses.append("created_at >= ?")
            parameters.append(int(filters["since"]))
        if filters.get("search"):
            fields = (
                "action", "resource_type", "resource_id", "outcome",
                "details_json", "actor_user_id",
                "(SELECT username FROM users WHERE users.id = audit_events.actor_user_id)",
            )
            clauses.append("(" + " OR ".join(
                f"instr(lower(COALESCE({field}, '')), lower(?)) > 0" for field in fields
            ) + ")")
            parameters.extend([filters["search"]] * len(fields))
        return " AND ".join(clauses), parameters

    @staticmethod
    def _visibility(actor: Actor) -> tuple[str, tuple]:
        return ("1", ()) if actor.is_admin else ("actor_user_id = ?", (actor.user_id,))

    def summary_visible(self, actor: Actor) -> dict:
        """Return fixed-size all-time totals and two adjacent seven-day windows."""
        now = int(self.clock())
        current_start = now - 7 * 86400
        previous_start = now - 14 * 86400
        where, parameters = self._visibility(actor)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT CASE
                    WHEN created_at >= ? AND created_at < ? THEN 'current'
                    WHEN created_at >= ? AND created_at < ? THEN 'previous'
                    ELSE 'outside' END AS period,
                    CASE
                    WHEN lower(outcome) IN ('success','ok','healthy','delivered','accepted','completed') THEN 'success'
                    WHEN lower(outcome) IN ('warning','warn','pending','retrying') THEN 'warning'
                    WHEN lower(outcome) IN ('failed','failure','error','denied','invalid') THEN 'failed'
                    ELSE 'other' END AS bucket,
                    COUNT(*) AS count
                FROM audit_events WHERE {where} GROUP BY period, bucket
                """,
                (current_start, now + 1, previous_start, current_start, *parameters),
            ).fetchall()
        result = {"total": 0, "current": dict.fromkeys(("success", "warning", "failed", "other"), 0),
                  "previous": dict.fromkeys(("success", "warning", "failed", "other"), 0)}
        for row in rows:
            count = int(row["count"])
            result["total"] += count
            if row["period"] in {"current", "previous"}:
                result[row["period"]][row["bucket"]] = count
        return result

    @classmethod
    def _safe_details(cls, details: dict) -> dict:
        if not isinstance(details, dict):
            raise ValueError("audit details must be an object")
        safe = {}
        for key, value in list(details.items())[:32]:
            label = str(key)[:64]
            if _SENSITIVE_KEY.search(label):
                safe[label] = "<redacted>"
            elif isinstance(value, bool) or value is None:
                safe[label] = value
            elif isinstance(value, (int, float)):
                safe[label] = value
            elif isinstance(value, (list, tuple)):
                safe[label] = [sanitize_text(item)[:128] for item in value[:32]]
            else:
                safe[label] = sanitize_text(value)[:256]
        return safe

    @staticmethod
    def _event(row) -> AuditEvent:
        return AuditEvent(
            id=int(row["id"]),
            actor_user_id=(
                str(row["actor_user_id"])
                if row["actor_user_id"] is not None
                else None
            ),
            action=str(row["action"]),
            resource_type=str(row["resource_type"]),
            resource_id=(
                str(row["resource_id"]) if row["resource_id"] is not None else None
            ),
            outcome=str(row["outcome"]),
            details=json.loads(str(row["details_json"])),
            created_at=int(row["created_at"]),
        )
