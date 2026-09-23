"""Retention and housekeeping for persisted operational history."""

from __future__ import annotations

import sqlite3
import time
import uuid

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.settings import (
    DEFAULT_HOUSEKEEPING_SETTINGS,
    DEFAULT_REGIONAL_SETTINGS,
    SettingsStore,
)


_BATCH_SIZE = 5000
_SESSION_GRACE_SECONDS = 7 * 24 * 60 * 60


class HousekeepingService:
    """Apply bounded retention to operational history without touching configuration."""

    def __init__(self, database: Database, *, audit=None, settings=None, clock=time.time):
        self.database = database
        self.audit = audit or AuditEventStore(database)
        self.settings_store = settings or SettingsStore(database, audit=self.audit)
        self.clock = clock

    def settings(self) -> dict:
        values, _error = self.settings_store.get_safe(
            "platform", "housekeeping", DEFAULT_HOUSEKEEPING_SETTINGS
        )
        return values

    def update_settings(self, actor, values: dict) -> dict:
        record = self.settings_store.set(actor, "platform", "housekeeping", values)
        return record.value

    def status(self) -> dict:
        settings = self.settings()
        with self.database.connect() as connection:
            deliveries = connection.execute(
                "SELECT COUNT(*) AS total, MIN(created_at) AS oldest FROM delivery_attempts"
            ).fetchone()
            audit = connection.execute(
                "SELECT COUNT(*) AS total, MIN(created_at) AS oldest FROM audit_events"
            ).fetchone()
            backup_runs = connection.execute(
                "SELECT COUNT(*) AS total, MIN(started_at) AS oldest FROM backup_schedule_runs"
            ).fetchone()
            email_messages = connection.execute(
                "SELECT COUNT(*) AS total, MIN(created_at) AS oldest FROM email_messages"
            ).fetchone()
            email_content = connection.execute(
                "SELECT COUNT(*) AS total, MIN(stored_at) AS oldest FROM email_message_contents"
            ).fetchone()
            email_processing = connection.execute(
                "SELECT COUNT(*) AS total, MIN(created_at) AS oldest FROM email_processing_history"
            ).fetchone()
            last = connection.execute(
                """
                SELECT * FROM housekeeping_runs
                WHERE completed_at IS NOT NULL
                ORDER BY completed_at DESC, started_at DESC
                LIMIT 1
                """
            ).fetchone()
            recent = connection.execute(
                """
                SELECT * FROM housekeeping_runs
                WHERE completed_at IS NOT NULL
                  AND period_key LIKE 'daily:%'
                ORDER BY completed_at DESC, started_at DESC
                LIMIT 3
                """
            ).fetchall()
        return {
            "delivery_history": {
                "rows": int(deliveries["total"] or 0),
                "oldest_at": int(deliveries["oldest"]) if deliveries["oldest"] is not None else None,
            },
            "audit_history": {
                "rows": int(audit["total"] or 0),
                "oldest_at": int(audit["oldest"]) if audit["oldest"] is not None else None,
            },
            "backup_runs": {
                "rows": int(backup_runs["total"] or 0),
                "oldest_at": int(backup_runs["oldest"]) if backup_runs["oldest"] is not None else None,
            },
            "email_message_metadata": {
                "rows": int(email_messages["total"] or 0),
                "oldest_at": int(email_messages["oldest"]) if email_messages["oldest"] is not None else None,
            },
            "email_raw_content": {
                "rows": int(email_content["total"] or 0),
                "oldest_at": int(email_content["oldest"]) if email_content["oldest"] is not None else None,
            },
            "email_processing_history": {
                "rows": int(email_processing["total"] or 0),
                "oldest_at": int(email_processing["oldest"]) if email_processing["oldest"] is not None else None,
            },
            "last_run": dict(last) if last is not None else None,
            "recent_runs": [dict(row) for row in recent],
            "next_run_at": self._next_run_at(settings),
        }

    def _next_run_at(self, settings: dict) -> int | None:
        if settings.get("enabled") is not True:
            return None
        regional, _error = self.settings_store.get_safe(
            "platform", "regional", DEFAULT_REGIONAL_SETTINGS
        )
        try:
            zone = ZoneInfo(str(regional.get("timezone") or "Europe/Lisbon"))
        except (ValueError, ZoneInfoNotFoundError):
            zone = ZoneInfo("UTC")
        timestamp = int(self.clock())
        current = datetime.fromtimestamp(timestamp, zone)
        hour, minute = (
            int(part) for part in str(settings.get("time") or "03:15").split(":")
        )
        candidate = datetime(
            current.year,
            current.month,
            current.day,
            hour,
            minute,
            tzinfo=zone,
        )
        if int(candidate.timestamp()) <= timestamp:
            tomorrow = current.date() + timedelta(days=1)
            candidate = datetime(
                tomorrow.year,
                tomorrow.month,
                tomorrow.day,
                hour,
                minute,
                tzinfo=zone,
            )
        return int(candidate.timestamp())

    def run(self, actor=None, *, period_key: str | None = None) -> dict | None:
        now = int(self.clock())
        period = str(period_key or f"manual:{uuid.uuid4().hex}")
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    "INSERT INTO housekeeping_runs(period_key, started_at) VALUES (?, ?)",
                    (period, now),
                )
        except sqlite3.IntegrityError:
            return None

        values = self.settings()
        removed = {
            "deliveries_deleted": 0,
            "audit_deleted": 0,
            "backup_runs_deleted": 0,
            "sessions_deleted": 0,
            "email_messages_deleted": 0,
            "email_raw_content_deleted": 0,
            "email_processing_deleted": 0,
        }
        try:
            delivery_days = int(values["delivery_history_days"])
            if delivery_days > 0:
                removed["deliveries_deleted"] = self._delete_before(
                    "delivery_attempts", "created_at", now - delivery_days * 86400
                )

            audit_days = int(values["audit_history_days"])
            if audit_days > 0:
                removed["audit_deleted"] = self._delete_before(
                    "audit_events", "created_at", now - audit_days * 86400
                )

            run_days = int(values["backup_run_history_days"])
            if run_days > 0:
                removed["backup_runs_deleted"] = self._delete_before(
                    "backup_schedule_runs", "started_at", now - run_days * 86400,
                    extra="completed_at IS NOT NULL",
                )

            email_raw_days = int(values["email_raw_content_days"])
            if email_raw_days > 0:
                removed["email_raw_content_deleted"] = self._delete_before(
                    "email_message_contents",
                    "stored_at",
                    now - email_raw_days * 86400,
                )

            email_processing_days = int(
                values["email_processing_history_days"]
            )
            if email_processing_days > 0:
                removed["email_processing_deleted"] = self._delete_before(
                    "email_processing_history",
                    "created_at",
                    now - email_processing_days * 86400,
                )

            email_metadata_days = int(values["email_message_metadata_days"])
            if email_metadata_days > 0:
                removed["email_messages_deleted"] = self._delete_before(
                    "email_messages",
                    "created_at",
                    now - email_metadata_days * 86400,
                )

            session_cutoff = now - _SESSION_GRACE_SECONDS
            removed["sessions_deleted"] = self._delete_sessions(session_cutoff)
            self._finish(period, "success", removed)
        except Exception:
            self._finish(period, "failed", removed)
            self.audit.write(
                actor,
                "housekeeping.run",
                "platform",
                None,
                "failed",
                {"period": period, **removed},
            )
            raise

        result = {
            "period": period,
            "outcome": "success",
            **removed,
            "completed_at": int(self.clock()),
        }
        self.audit.write(
            actor,
            "housekeeping.run",
            "platform",
            None,
            "success",
            result,
        )
        return result

    def _delete_before(self, table: str, column: str, cutoff: int, *, extra: str = "") -> int:
        if table not in {
            "delivery_attempts",
            "audit_events",
            "backup_schedule_runs",
            "email_messages",
            "email_message_contents",
            "email_processing_history",
        }:
            raise ValueError("unsupported housekeeping table")
        if column not in {"created_at", "started_at", "stored_at"}:
            raise ValueError("unsupported housekeeping timestamp")
        suffix = f" AND {extra}" if extra else ""
        total = 0
        while True:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE rowid IN (
                        SELECT rowid FROM {table}
                        WHERE {column} < ?{suffix}
                        ORDER BY {column}
                        LIMIT ?
                    )
                    """,
                    (int(cutoff), _BATCH_SIZE),
                )
                deleted = max(0, int(cursor.rowcount))
            total += deleted
            if deleted < _BATCH_SIZE:
                return total

    def _delete_sessions(self, cutoff: int) -> int:
        total = 0
        while True:
            with self.database.transaction() as connection:
                cursor = connection.execute(
                    """
                    DELETE FROM sessions
                    WHERE rowid IN (
                        SELECT rowid FROM sessions
                        WHERE (
                            expires_at < ?
                            OR idle_expires_at < ?
                            OR (revoked_at IS NOT NULL AND revoked_at < ?)
                        )
                        LIMIT ?
                    )
                    """,
                    (cutoff, cutoff, cutoff, _BATCH_SIZE),
                )
                deleted = max(0, int(cursor.rowcount))
            total += deleted
            if deleted < _BATCH_SIZE:
                return total

    def _finish(self, period: str, outcome: str, removed: dict) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE housekeeping_runs
                SET completed_at = ?, outcome = ?,
                    deliveries_deleted = ?, audit_deleted = ?,
                    backup_runs_deleted = ?, sessions_deleted = ?
                WHERE period_key = ?
                """,
                (
                    int(self.clock()),
                    outcome,
                    int(removed["deliveries_deleted"]),
                    int(removed["audit_deleted"]),
                    int(removed["backup_runs_deleted"]),
                    int(removed["sessions_deleted"]),
                    period,
                ),
            )
