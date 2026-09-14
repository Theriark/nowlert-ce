"""Persist enable/disable state for destination filters without discarding rules."""

from __future__ import annotations

import json

from integrations.catalog import canonical_source
from storage.filtering import DestinationFilterStore as BaseDestinationFilterStore


_STATE_NAMESPACE = "destination_filter_enabled"


class DestinationFilterStore(BaseDestinationFilterStore):
    """Destination filter store with a non-destructive enabled switch."""

    @staticmethod
    def _state_key(destination_id: str, source: str) -> str:
        return f"{destination_id}:{canonical_source(source)}"

    def filter_enabled(self, destination_id: str, source: str) -> bool:
        policy = self._policy(destination_id, source)
        if not policy or not policy.get("clauses"):
            return False
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings_records "
                "WHERE namespace = ? AND setting_key = ?",
                (_STATE_NAMESPACE, self._state_key(destination_id, source)),
            ).fetchone()
        if row is None:
            return True
        try:
            return bool(json.loads(str(row["value_json"])))
        except (TypeError, ValueError, json.JSONDecodeError):
            return True

    def set_enabled(self, actor, destination_id: str, source: str, enabled: bool) -> bool:
        self._destination(actor, destination_id, write=True)
        source = canonical_source(source)
        if source not in self.available_sources(actor, destination_id):
            raise ValueError("integration is not enabled for this destination")
        policy = self._policy(destination_id, source)
        if enabled and (not policy or not policy.get("clauses")):
            raise ValueError("configure filter rules before enabling filtering")
        key = self._state_key(destination_id, source)
        now = int(self.clock())
        with self.database.transaction() as connection:
            if enabled:
                connection.execute(
                    "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                    (_STATE_NAMESPACE, key),
                )
            elif policy and policy.get("clauses"):
                connection.execute(
                    """
                    INSERT INTO settings_records(namespace, setting_key, value_json, updated_at)
                    VALUES (?, ?, 'false', ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (_STATE_NAMESPACE, key, now),
                )
            else:
                connection.execute(
                    "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                    (_STATE_NAMESPACE, key),
                )
        self._audit(
            actor,
            "filter.enable" if enabled else "filter.disable",
            destination_id,
            {"source": source, "enabled": bool(enabled)},
        )
        return bool(enabled and policy and policy.get("clauses"))

    def set_rules(self, actor, destination_id: str, source: str, rules: dict | None):
        policy = super().set_rules(actor, destination_id, source, rules)
        if policy is None:
            self._clear_state(destination_id, source)
        return policy

    def destination_view(self, actor, destination_id: str) -> dict:
        view = super().destination_view(actor, destination_id)
        for integration in view["integrations"]:
            integration["filter_enabled"] = bool(
                integration.get("configured")
                and self.filter_enabled(destination_id, integration["source"])
            )
        return view

    def list_visible(self, actor) -> list[dict]:
        result = []
        for policy in super().list_visible(actor):
            view = self.destination_view(actor, policy["destination_id"])
            active = [
                item["source"]
                for item in view["integrations"]
                if item.get("configured") and item.get("filter_enabled")
            ]
            if not active:
                continue
            result.append(
                {
                    **policy,
                    "configured_count": len(active),
                    "active_count": len(active),
                    "available_count": len(view["integrations"]),
                    "sources": active,
                }
            )
        return result

    def matches(self, actor, destination_id: str, notification) -> bool:
        source = canonical_source(notification.source)
        policy = self._policy(destination_id, source)
        if policy and policy.get("clauses") and not self.filter_enabled(destination_id, source):
            self._destination(actor, destination_id)
            return True
        return super().matches(actor, destination_id, notification)

    def clear_source(self, actor, destination_id: str, source: str) -> None:
        super().clear_source(actor, destination_id, source)
        self._clear_state(destination_id, source)

    def clear_destination(self, actor, destination_id: str) -> None:
        super().clear_destination(actor, destination_id)
        prefix = f"{destination_id}:"
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key LIKE ?",
                (_STATE_NAMESPACE, f"{prefix}%"),
            )

    def _clear_state(self, destination_id: str, source: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records WHERE namespace = ? AND setting_key = ?",
                (_STATE_NAMESPACE, self._state_key(destination_id, source)),
            )
