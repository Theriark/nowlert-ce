"""Filtering view over system Routes with destination-owned allow/block policy."""

from __future__ import annotations

import json

from config import config
from integrations.catalog import canonical_source
from integrations.filtering import filter_schemas, sources_for_input
from storage.destination_access import AccessControlledDestinationFilterStore
from storage.filtering import _clause_matches
from storage.ownership import Actor
from storage.routing_flow import record_destination_filter_decision
from storage.settings import SettingsStore, runtime_overlay_status


_POLICY_VERSION = 2
_POLICY_KEY = "policy"
_ACTIONS = {"allow", "block"}


class SystemDestinationFilterStore(AccessControlledDestinationFilterStore):
    """Treat bound Routes as system plumbing and own destination delivery policy."""

    def __init__(self, database, *args, **kwargs):
        super().__init__(database, *args, **kwargs)
        self._migrate_dell_trusted_client_policy()
        self._enforce_runtime_policy_contract()

    def available_sources(self, actor, destination_id):
        self._destination(actor, destination_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT routes.source, routes.input_type
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE route_destinations.destination_id = ?
                ORDER BY routes.priority, routes.name_normalized
                """,
                (str(destination_id),),
            ).fetchall()
        catalogue_sources = [item["source"] for item in filter_schemas()]
        found = set()
        for row in rows:
            source = canonical_source(str(row["source"]))
            if source == "*":
                found.update(sources_for_input(str(row["input_type"] or "")))
            elif source in catalogue_sources:
                found.add(source)
        return tuple(source for source in catalogue_sources if source in found)

    def set_rules(self, actor, destination_id, source, rules):
        """Accept legacy single-rule payloads or the v2 allow/block policy envelope."""

        if not isinstance(rules, dict) or _POLICY_KEY not in rules:
            return super().set_rules(actor, destination_id, source, rules)

        self._destination(actor, destination_id, write=True)
        source = canonical_source(source)
        if source not in self.available_sources(actor, destination_id):
            raise ValueError("integration is not enabled for this destination")
        policy_rules = self._normalize_policy_rules(source, rules.get(_POLICY_KEY))
        self._write_policy(actor, destination_id, source, policy_rules)
        policy = self._policy(destination_id, source)
        if not policy_rules:
            self._clear_state(destination_id, source)
            return None
        return policy

    def destination_view(self, actor, destination_id):
        view = super().destination_view(actor, destination_id)
        destination_id = str(destination_id)
        for integration in view.get("integrations", []):
            source = canonical_source(integration.get("source"))
            policy = self._policy(destination_id, source)
            policy_rules = list(policy.get("policy_rules") or []) if policy else []
            integration["configured"] = bool(policy_rules)
            integration["policy_rules"] = self._public_policy_rules(policy_rules)
            if len(policy_rules) == 1 and policy_rules[0]["action"] == "allow":
                integration["rules"] = {
                    key: list(values)
                    for key, values in policy_rules[0]["conditions"].items()
                }
                integration["legacy_clauses"] = []
            else:
                integration["rules"] = {}
                integration["legacy_clauses"] = [
                    {
                        key: list(values)
                        for key, values in item["conditions"].items()
                    }
                    for item in policy_rules
                ]
        return view

    def matches(self, actor: Actor, destination_id: str, notification) -> bool:
        self._destination(actor, destination_id)
        source = canonical_source(notification.source)
        policy = self._policy(destination_id, source)
        policy_rules = list(policy.get("policy_rules") or []) if policy else []

        matched = True
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

    def _policy(self, destination_id: str, source: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT clauses_json FROM destination_filters "
                "WHERE destination_id = ? AND source = ?",
                (str(destination_id), canonical_source(source)),
            ).fetchone()
        if row is None:
            return None
        policy_rules = self._decode_policy_rules(row["clauses_json"])
        return self._compat_policy(policy_rules)

    def _policies_for_destination(self, destination_id: str):
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT source, clauses_json FROM destination_filters "
                "WHERE destination_id = ? ORDER BY source",
                (str(destination_id),),
            ).fetchall()
        result = {}
        for row in rows:
            policy_rules = self._decode_policy_rules(row["clauses_json"])
            if policy_rules:
                result[canonical_source(row["source"])] = self._compat_policy(policy_rules)
        return result

    @staticmethod
    def _compat_policy(policy_rules):
        return {
            "version": _POLICY_VERSION,
            "policy_rules": list(policy_rules),
            "clauses": [item["conditions"] for item in policy_rules],
        }

    def _decode_policy_rules(self, value):
        try:
            decoded = json.loads(str(value or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

        if isinstance(decoded, list):
            clauses = self._decode_clauses(value)
            return [
                {"action": "allow", "conditions": clause}
                for clause in clauses
                if clause
            ]
        if not isinstance(decoded, dict) or decoded.get("version") != _POLICY_VERSION:
            return []
        raw_rules = decoded.get("rules")
        if not isinstance(raw_rules, list):
            return []

        result = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                continue
            action = str(raw.get("action") or "").strip().casefold()
            conditions = raw.get("conditions")
            if action not in _ACTIONS or not isinstance(conditions, dict):
                continue
            normalized = {}
            for key, values in conditions.items():
                try:
                    patterns = self._patterns(values)
                except ValueError:
                    continue
                if patterns:
                    normalized[str(key)] = patterns
            if normalized:
                result.append({"action": action, "conditions": normalized})
        return result

    @staticmethod
    def _patterns(values):
        from storage.filtering import _patterns

        return _patterns(values)

    def _normalize_policy_rules(self, source: str, value):
        if not isinstance(value, list):
            raise ValueError("filter policy must be a list")
        if len(value) > 32:
            raise ValueError("filter policy must not exceed 32 rules")
        normalized = []
        for raw in value:
            if not isinstance(raw, dict):
                raise ValueError("filter policy rules must be objects")
            action = str(raw.get("action") or "").strip().casefold()
            if action not in _ACTIONS:
                raise ValueError("filter action must be allow or block")
            conditions = self._normalize_rules(source, raw.get("conditions") or {})
            if not conditions:
                continue
            normalized.append({"action": action, "conditions": conditions})
        encoded = self._encode_policy_rules(normalized)
        if len(encoded.encode("utf-8")) > 64 * 1024:
            raise ValueError("filter policy must not exceed 65536 bytes")
        return normalized

    @staticmethod
    def _encode_policy_rules(policy_rules):
        return json.dumps(
            {
                "version": _POLICY_VERSION,
                "rules": [
                    {
                        "action": item["action"],
                        "conditions": {
                            key: list(values)
                            for key, values in item["conditions"].items()
                        },
                    }
                    for item in policy_rules
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _public_policy_rules(policy_rules):
        return [
            {
                "action": item["action"],
                "conditions": {
                    key: list(values)
                    for key, values in item["conditions"].items()
                },
            }
            for item in policy_rules
        ]

    def _write_policy(self, actor, destination_id, source, policy_rules):
        now = int(self.clock())
        with self.database.transaction() as connection:
            if policy_rules:
                encoded = self._encode_policy_rules(policy_rules)
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
            "filter.update" if policy_rules else "filter.clear",
            destination_id,
            {
                "source": source,
                "configured": bool(policy_rules),
                "allow_rules": sum(item["action"] == "allow" for item in policy_rules),
                "block_rules": sum(item["action"] == "block" for item in policy_rules),
            },
        )

    def _migrate_dell_trusted_client_policy(self):
        """Move the old global Dell session suppression into destination BLOCK rules."""

        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings_records "
                "WHERE namespace = 'integration' AND setting_key = 'dell_idrac'",
            ).fetchone()
        if row is None:
            return 0
        try:
            legacy = json.loads(str(row["value_json"] or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            legacy = {}
        addresses = legacy.get("suppress_ipmi_session_audit_from", [])
        if isinstance(addresses, str):
            addresses = [addresses]
        addresses = [str(item).strip() for item in addresses if str(item).strip()]
        if not addresses:
            with self.database.transaction() as connection:
                connection.execute(
                    "DELETE FROM settings_records "
                    "WHERE namespace = 'integration' AND setting_key = 'dell_idrac'"
                )
            return 0

        actor = None
        with self.database.connect() as connection:
            destinations = connection.execute(
                """
                SELECT DISTINCT route_destinations.destination_id AS id
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE routes.source = 'dell_idrac'
                   OR (routes.source = '*' AND routes.input_type = 'redfish')
                ORDER BY route_destinations.destination_id
                """
            ).fetchall()
        migrated = 0
        for destination in destinations:
            destination_id = str(destination["id"])
            conditions = self._normalize_rules(
                "dell_idrac",
                {
                    "message_id": ["USR0030", "USR0032"],
                    "source_ip": addresses,
                },
            )
            if not conditions:
                continue
            existing = self._policy(destination_id, "dell_idrac")
            policy_rules = list(existing.get("policy_rules") or []) if existing else []
            candidate = {"action": "block", "conditions": conditions}
            signature = self._rule_signature(candidate)
            if signature not in {self._rule_signature(item) for item in policy_rules}:
                policy_rules.append(candidate)
                self._write_policy(actor, destination_id, "dell_idrac", policy_rules)
                migrated += 1

        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM settings_records "
                "WHERE namespace = 'integration' AND setting_key = 'dell_idrac'"
            )
        return migrated

    @staticmethod
    def _rule_signature(item):
        return json.dumps(
            {
                "action": item["action"],
                "conditions": {
                    key: list(values)
                    for key, values in item["conditions"].items()
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _enforce_runtime_policy_contract(self):
        """Retire legacy presentation/suppression toggles in persisted/live state."""

        now = int(self.clock())
        with self.database.transaction() as connection:
            for source in ("xo", "zabbix"):
                connection.execute(
                    """
                    INSERT INTO settings_records(
                        namespace, setting_key, value_json, updated_at
                    ) VALUES ('integration', ?, ?, ?)
                    ON CONFLICT(namespace, setting_key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (source, '{"show_ids":false}', now),
                )

        overlay, _errors = runtime_overlay_status(SettingsStore(self.database))
        apply = getattr(config, "apply_runtime_overlay", None)
        if callable(apply):
            apply(overlay)
