"""Safe operational checks shown beside the platform audit trail."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from storage.backup_targets import _remote_mounted


class HealthCheckService:
    def __init__(self, database, configuration_sync, *, clock=time.time):
        self.database = database
        self.configuration_sync = configuration_sync
        self.clock = clock

    # Background polls retry a failing mailbox every few minutes, so a single
    # failure is noise; this many in a day means synchronization is broken.
    MAILBOX_FAILURE_WINDOW_SECONDS = 24 * 3600
    MAILBOX_FAILURE_THRESHOLD = 3

    def run(self, actor=None) -> list[dict]:
        checks = [self._database(), self._configuration()]
        checks.extend(self._routing())
        checks.append(self._backup_target())
        checks.append(self._deliveries(actor))
        checks.append(self._mailbox_sync())
        return checks

    def _database(self):
        try:
            with self.database.connect() as connection:
                result = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            return self._check("database", result == "ok", "SQLite integrity", result)
        except Exception:
            return self._check("database", False, "SQLite integrity", "check failed")

    def _configuration(self):
        if self.configuration_sync is None:
            return self._check("configuration", True, "Configuration", "legacy mode")
        status = self.configuration_sync.synchronize()
        if status.ready and status.errors:
            return self._check(
                "configuration",
                False,
                "Database settings",
                "; ".join(status.errors),
                warning=True,
            )
        return self._check(
            "configuration",
            status.ready,
            "Core configuration",
            "synchronized" if status.ready else "; ".join(status.errors),
        )

    def _routing(self):
        checks = []
        with self.database.connect() as connection:
            destinations = connection.execute(
                """
                SELECT id, name, output_type, enabled, secret_id, settings_json
                FROM destinations ORDER BY name_normalized
                """
            ).fetchall()
            broken_bindings = connection.execute(
                """
                SELECT DISTINCT routes.name
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                LEFT JOIN destinations
                  ON destinations.id = route_destinations.destination_id
                WHERE routes.enabled = 1
                  AND destinations.id IS NULL
                ORDER BY routes.name_normalized
                """
            ).fetchall()
        missing = [
            str(row["name"])
            for row in destinations
            if bool(row["enabled"])
            and self._destination_requires_credentials(row)
            and row["secret_id"] is None
        ]
        checks.append(
            self._check(
                "destination_credentials",
                not missing,
                "Destination credentials",
                "available" if not missing else f"missing: {', '.join(missing[:5])}",
            )
        )
        names = [str(row["name"]) for row in broken_bindings]
        checks.append(
            self._check(
                "routes",
                not names,
                "Enabled route assignments",
                "healthy" if not names else f"unavailable destination: {', '.join(names[:5])}",
            )
        )
        return checks

    @staticmethod
    def _destination_requires_credentials(row) -> bool:
        output_type = str(row["output_type"] or "").strip().casefold()
        if output_type in {"discord", "teams", "slack", "webhook", "nowlert_mobile"}:
            return True
        if output_type != "email":
            return False
        try:
            settings = json.loads(str(row["settings_json"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return True
        if not isinstance(settings, dict):
            return True
        return bool(str(settings.get("username") or "").strip())

    def _backup_target(self):
        if self.configuration_sync is None:
            return self._check("external_backup", True, "External backup", "not configured")
        settings = self.configuration_sync.backup_settings()
        schedule = str(settings.get("schedule") or "disabled").strip().casefold()
        target_id = str(settings.get("target_id") or "").strip()
        # The scheduler prefers a named backup target over the legacy
        # external path (storage/backup_scheduler.py), so health does too.
        if target_id:
            return self._scheduled_backup_target(schedule, target_id)
        if not settings.get("external_enabled"):
            if schedule != "disabled":
                return self._check(
                    "external_backup",
                    True,
                    "External backup",
                    f"{schedule} backups are kept in local state only; "
                    "no external backup target is selected",
                )
            return self._check("external_backup", True, "External backup", "disabled")
        path = Path(settings["external_path"])
        healthy = path.is_dir() and not path.is_symlink()
        return self._check(
            "external_backup",
            healthy,
            f"{settings['external_type'].upper()} backup target",
            "mounted" if healthy else "mounted path is unavailable",
        )

    def _scheduled_backup_target(self, schedule, target_id):
        with self.database.connect() as connection:
            target = connection.execute(
                """
                SELECT name, target_type, local_path, enabled
                FROM backup_targets WHERE id = ?
                """,
                (target_id,),
            ).fetchone()
            last_run = connection.execute(
                """
                SELECT outcome FROM backup_schedule_runs
                WHERE period_key NOT LIKE 'manual:%' AND completed_at IS NOT NULL
                ORDER BY started_at DESC LIMIT 1
                """
            ).fetchone()
        if target is None:
            return self._check(
                "external_backup",
                False,
                "Backup target",
                "the selected backup target no longer exists",
            )
        target_type = str(target["target_type"] or "local").casefold()
        label = f"{target_type.upper() if target_type != 'local' else 'Local'} backup target"
        name = str(target["name"])
        when = "scheduled backups are disabled" if schedule == "disabled" else f"{schedule} backups"
        if not bool(target["enabled"]):
            return self._check(
                "external_backup",
                False,
                label,
                f"{when} to {name}: the target is disabled",
                warning=True,
            )
        if target_type != "local" and not _remote_mounted(
            str(target["local_path"]), target_type
        ):
            return self._check(
                "external_backup",
                False,
                label,
                f"{when} to {name}: mounted path is unavailable",
            )
        if schedule != "disabled" and last_run is not None and last_run["outcome"] == "failed":
            return self._check(
                "external_backup",
                False,
                label,
                f"{when} to {name}: the last scheduled backup failed",
                warning=True,
            )
        return self._check(
            "external_backup",
            True,
            label,
            f"{when} to {name}" + ("" if target_type == "local" else ": mounted"),
        )

    def _mailbox_sync(self):
        since = int(self.clock()) - self.MAILBOX_FAILURE_WINDOW_SECONDS
        try:
            with self.database.connect() as connection:
                states = [
                    str(row[0])
                    for row in connection.execute(
                        "SELECT connection_state FROM email_mailboxes WHERE enabled = 1"
                    )
                ]
                failures = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM audit_events
                        WHERE action = 'email.mailbox.sync'
                          AND outcome = 'failed' AND created_at >= ?
                        """,
                        (since,),
                    ).fetchone()[0]
                )
        except sqlite3.Error:
            return self._check(
                "mailbox_sync",
                False,
                "Mailbox synchronization",
                "mailbox status could not be read",
                warning=True,
            )
        if not states:
            return self._check(
                "mailbox_sync", True, "Mailbox synchronization", "no mailboxes connected"
            )
        attention = sum(1 for state in states if state in {"degraded", "error"})
        repeated = failures >= self.MAILBOX_FAILURE_THRESHOLD
        parts = []
        if attention:
            parts.append(
                f"{attention} of {len(states)} mailbox(es) cannot synchronize; "
                "reconnect them under Email Alerts"
            )
        if failures and (attention or repeated):
            parts.append(f"{failures} failed synchronization(s) in the last 24 hours")
        if attention or repeated:
            return self._check(
                "mailbox_sync",
                False,
                "Mailbox synchronization",
                "; ".join(parts),
                warning=True,
            )
        detail = f"{len(states)} mailbox(es) synchronizing"
        if failures:
            detail += f"; {failures} failed attempt(s) in the last 24 hours"
        return self._check("mailbox_sync", True, "Mailbox synchronization", detail)

    RECENT_DELIVERY_LIMIT = 3

    def _deliveries(self, actor=None):
        """Recent delivery failures, named so the viewer can act on them.

        Failures to destinations the viewer can see (its own and shared ones)
        are listed by destination. An administrator also gets one line for
        failures to other accounts' private destinations, by owner, because
        those deliveries do not appear in the administrator's own Delivery
        history. A regular user is not told about other accounts' private
        destinations. Without a viewer every failure is listed by destination.
        """

        since = int(self.clock()) - 3600
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT attempts.destination_id AS destination_id,
                       destinations.name AS name,
                       destinations.owner_user_id AS owner_id,
                       destinations.shared AS shared,
                       users.username AS owner,
                       COUNT(*) AS failures
                FROM delivery_attempts AS attempts
                LEFT JOIN destinations ON destinations.id = attempts.destination_id
                LEFT JOIN users ON users.id = destinations.owner_user_id
                WHERE attempts.created_at >= ? AND attempts.outcome = 'failed'
                GROUP BY attempts.destination_id
                ORDER BY failures DESC, name
                """,
                (since,),
            ).fetchall()
        visible = []
        hidden = {}
        for row in rows:
            count = int(row["failures"])
            name = str(row["name"]) if row["name"] is not None else "a deleted destination"
            owner = str(row["owner"] or "unknown owner")
            mine = actor is not None and str(row["owner_id"] or "") == str(actor.user_id)
            if actor is None or mine or (row["name"] is not None and bool(row["shared"])):
                visible.append((name, count))
            else:
                hidden[owner] = hidden.get(owner, 0) + count
        parts = []
        if visible:
            total = sum(count for _name, count in visible)
            listed = ", ".join(
                f"{name} ({count})" for name, count in visible[: self.RECENT_DELIVERY_LIMIT]
            )
            more = len(visible) - self.RECENT_DELIVERY_LIMIT
            if more > 0:
                listed += f" and {more} more"
            parts.append(f"{total} failed attempt(s) in the last hour: {listed}")
        if hidden and (actor is None or actor.is_admin):
            total = sum(hidden.values())
            owners = ", ".join(f"{owner} ({count})" for owner, count in sorted(hidden.items()))
            parts.append(
                f"{total} failed attempt(s) to other accounts' private destinations, "
                f"which your Delivery history does not show; owners: {owners}"
            )
        return self._check(
            "recent_delivery",
            not parts,
            "Recent delivery failures",
            "; ".join(parts) if parts else "none in the last hour",
            warning=True,
        )

    @staticmethod
    def _check(key, healthy, name, detail, warning=False):
        return {
            "key": key,
            "name": name,
            "status": "healthy" if healthy else "warning" if warning else "error",
            "detail": str(detail)[:500],
        }
