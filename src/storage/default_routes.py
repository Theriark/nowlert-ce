"""Seed the shipped reusable route catalogue for newly initialized accounts."""

from __future__ import annotations

import json
import time
import uuid

from integrations.catalog import route_options
from storage.database import Database
from storage.validation import normalized_name


_SEED_NAMESPACE = "platform.default_routes"
_SEED_VERSION = 1


def seed_default_routes(
    database: Database,
    owner_user_id: str,
    role: str,
    *,
    clock=time.time,
) -> int:
    """Create the built-in source/input routes once for an account.

    Default routes are definitions only. They are unassigned, enabled, and
    owned by the account so private destinations can select them safely.
    Wildcard fallbacks remain admin-only, matching normal route creation rules.
    """

    owner_user_id = str(owner_user_id)
    normalized_role = str(role or "").casefold()
    now = int(clock())
    created = 0
    with database.transaction() as connection:
        marker = connection.execute(
            "SELECT value_json FROM settings_records "
            "WHERE namespace = ? AND setting_key = ?",
            (_SEED_NAMESPACE, owner_user_id),
        ).fetchone()
        if marker is not None:
            try:
                version = int(json.loads(str(marker["value_json"])).get("version", 0))
            except (TypeError, ValueError, json.JSONDecodeError):
                version = 0
            if version >= _SEED_VERSION:
                return 0

        existing = connection.execute(
            "SELECT COUNT(*) FROM routes WHERE owner_user_id = ?",
            (owner_user_id,),
        ).fetchone()[0]
        if not existing:
            for option in route_options():
                source = str(option["source"])
                if source == "*" and normalized_role != "admin":
                    continue
                integration = str(option["integration_name"])
                input_name = str(option["input_name"])
                name = integration if integration == input_name else f"{integration} {input_name}"
                display, normalized = normalized_name(name, "route name")
                connection.execute(
                    """
                    INSERT INTO routes(
                        id, owner_user_id, name, name_normalized, source,
                        input_type, filters_json, priority, enabled,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, '{}', 50, 1, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex,
                        owner_user_id,
                        display,
                        normalized,
                        source,
                        str(option["input_type"]),
                        now,
                        now,
                    ),
                )
                created += 1

        connection.execute(
            """
            INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(namespace, setting_key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (
                _SEED_NAMESPACE,
                owner_user_id,
                json.dumps({"version": _SEED_VERSION, "created": created}),
                now,
            ),
        )
    return created


def seed_missing_default_routes(database: Database, *, clock=time.time) -> int:
    """Backfill accounts created by older builds without changing configured routes."""

    with database.connect() as connection:
        users = connection.execute(
            "SELECT id, role FROM users ORDER BY created_at, id"
        ).fetchall()
    return sum(
        seed_default_routes(
            database,
            str(user["id"]),
            str(user["role"]),
            clock=clock,
        )
        for user in users
    )
