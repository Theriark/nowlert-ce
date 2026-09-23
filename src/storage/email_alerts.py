"""Durable Email Alerts foundation for mailbox, rule and message state."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid

from dataclasses import dataclass
from email.utils import parseaddr
from typing import Callable
from urllib.parse import urlsplit

from models.email_alert import EMAIL_CLASSIFICATIONS, EmailAlertEvent
from storage.database import Database
from storage.ownership import Actor, OwnershipPolicy
from storage.sanitize import sanitize_text
from storage.validation import normalized_name


EMAIL_MAILBOX_PROVIDERS = frozenset({"gmail", "microsoft_365", "imap"})
EMAIL_MATCH_MODES = frozenset({"all", "any"})
EMAIL_RULE_FIELDS = frozenset(
    {"sender", "sender_domain", "recipient", "subject", "body", "mailbox"}
)
EMAIL_RULE_OPERATORS = frozenset(
    {"equals", "contains", "starts_with", "ends_with"}
)
EMAIL_PROCESSING_ACTIONS = frozenset(
    {
        "matched",
        "ignored",
        "promoted",
        "duplicate",
        "suppressed",
        "reprocessed",
        "error",
    }
)
EMAIL_CONNECTION_STATES = frozenset(
    {"disconnected", "connecting", "healthy", "degraded", "error"}
)

DEFAULT_EMAIL_METADATA_RETENTION_DAYS = 90
DEFAULT_EMAIL_CONTENT_RETENTION_DAYS = 7
DEFAULT_EMAIL_PROCESSING_RETENTION_DAYS = 90

_MAX_JSON_BYTES = 64 * 1024
_MAX_RAW_CONTENT_BYTES = 5 * 1024 * 1024
_CONTENT_TYPE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9.+_-]*/[A-Za-z0-9][A-Za-z0-9.+_-]*$"
)
_SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|cookie|password|secret|token|api[_-]?key)"
)


@dataclass(frozen=True)
class EmailMailbox:
    id: str
    owner_user_id: str
    provider: str
    name: str
    address: str
    secret_configured: bool
    settings: dict
    enabled: bool
    connection_state: str
    sync_cursor: str
    last_sync_at: int | None
    last_error_code: str
    last_error_safe: str
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class EmailGroup:
    id: str
    owner_user_id: str
    name: str
    description: str
    enabled: bool
    quiet_window_seconds: int
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class EmailRule:
    id: str
    owner_user_id: str
    group_id: str
    name: str
    classification: str
    match_mode: str
    conditions: tuple[dict, ...]
    priority: int
    enabled: bool
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class EmailMessage:
    id: str
    owner_user_id: str
    mailbox_id: str
    provider_message_id: str
    internet_message_id: str
    identity_key: str
    sender: str
    sender_domain: str
    recipients: tuple[str, ...]
    subject: str
    folder: str
    labels: tuple[str, ...]
    provider_deep_link: str
    metadata: dict
    received_at: int
    metadata_expires_at: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True)
class EmailProcessingRecord:
    id: str
    owner_user_id: str
    message_id: str
    group_id: str | None
    rule_id: str | None
    action: str
    classification: str
    details: dict
    event_id: str
    created_at: int
    expires_at: int | None


def email_message_identity(
    mailbox_id: str,
    *,
    provider_message_id: str = "",
    internet_message_id: str = "",
) -> str:
    mailbox = str(mailbox_id or "").strip()
    if not mailbox:
        raise ValueError("mailbox identifier is required")
    provider_value = str(provider_message_id or "").strip()
    internet_value = str(internet_message_id or "").strip()
    if internet_value.startswith("<") and internet_value.endswith(">"):
        internet_value = internet_value[1:-1].strip()
    if provider_value:
        kind, value = "provider", provider_value
    elif internet_value:
        kind, value = "message-id", internet_value
    else:
        raise ValueError(
            "provider message id or Message-ID is required for deduplication"
        )
    material = f"{mailbox}\0{kind}\0{value}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class EmailAlertStore:
    """Persist Email Alerts state without exposing raw mail through metadata APIs."""

    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.database = database
        self.clock = clock

    def create_mailbox(
        self,
        actor: Actor,
        owner_user_id: str,
        provider: str,
        address: str,
        *,
        name: str = "",
        secret_id: str | None = None,
        settings: dict | None = None,
        enabled: bool = True,
    ) -> EmailMailbox:
        OwnershipPolicy.require_write(actor, str(owner_user_id))
        provider_value = str(provider or "").strip().casefold()
        if provider_value not in EMAIL_MAILBOX_PROVIDERS:
            raise ValueError("email mailbox provider is not supported")
        address_value, address_normalized, _domain = self._email_address(
            address,
            "mailbox address",
        )
        display_name, normalized_name_value = normalized_name(
            name or address_value,
            "mailbox name",
            maximum=160,
        )
        settings_value = self._settings(settings)
        now = int(self.clock())
        mailbox_id = uuid.uuid4().hex

        try:
            with self.database.transaction() as connection:
                self._enabled_owner(connection, owner_user_id)
                if secret_id:
                    secret = connection.execute(
                        "SELECT owner_user_id FROM secret_records WHERE id = ?",
                        (str(secret_id),),
                    ).fetchone()
                    if secret is None:
                        raise KeyError("email mailbox secret not found")
                    if str(secret["owner_user_id"]) != str(owner_user_id):
                        raise PermissionError(
                            "email mailbox and secret must have the same owner"
                        )
                connection.execute(
                    """
                    INSERT INTO email_mailboxes(
                        id, owner_user_id, provider, name, name_normalized,
                        address, address_normalized, secret_id, settings_json,
                        enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mailbox_id,
                        str(owner_user_id),
                        provider_value,
                        display_name,
                        normalized_name_value,
                        address_value,
                        address_normalized,
                        str(secret_id) if secret_id else None,
                        self._json(settings_value),
                        1 if enabled else 0,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email mailbox name or provider address is already configured"
            ) from error
        return self.get_mailbox(actor, mailbox_id)

    def get_mailbox(self, actor: Actor, mailbox_id: str) -> EmailMailbox:
        row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._mailbox(row)

    def list_mailboxes(self, actor: Actor) -> list[EmailMailbox]:
        with self.database.connect() as connection:
            if actor.is_admin:
                rows = connection.execute(
                    "SELECT * FROM email_mailboxes ORDER BY name_normalized"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM email_mailboxes
                    WHERE owner_user_id = ?
                    ORDER BY name_normalized
                    """,
                    (actor.user_id,),
                ).fetchall()
        return [self._mailbox(row) for row in rows]

    def mailbox_secret_id(
        self,
        actor: Actor,
        mailbox_id: str,
    ) -> str | None:
        """Return the credential reference without ever resolving its value."""

        row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return str(row["secret_id"]) if row["secret_id"] is not None else None

    def update_mailbox_connection(
        self,
        actor: Actor,
        mailbox_id: str,
        *,
        connection_state: str,
        sync_cursor: str | None = None,
        last_sync_at: int | None = None,
        error_code: str | None = None,
        safe_error: str | None = None,
        clear_error: bool = False,
    ) -> EmailMailbox:
        """Persist provider health/checkpoints without exposing credentials."""

        row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        state = str(connection_state or "").strip().casefold()
        if state not in EMAIL_CONNECTION_STATES:
            raise ValueError("email mailbox connection state is invalid")
        assignments = ["connection_state = ?", "updated_at = ?"]
        values: list[object] = [state, int(self.clock())]
        if sync_cursor is not None:
            cursor = str(sync_cursor)
            if len(cursor.encode("utf-8")) > 16 * 1024:
                raise ValueError("email mailbox synchronization checkpoint is too large")
            assignments.append("sync_cursor = ?")
            values.append(cursor)
        if last_sync_at is not None:
            assignments.append("last_sync_at = ?")
            values.append(int(last_sync_at))
        if clear_error:
            assignments.extend(
                ["last_error_code = NULL", "last_error_safe = NULL"]
            )
        else:
            if error_code is not None:
                assignments.append("last_error_code = ?")
                values.append(sanitize_text(error_code)[:64] or None)
            if safe_error is not None:
                assignments.append("last_error_safe = ?")
                values.append(sanitize_text(safe_error)[:500] or None)
        values.append(str(mailbox_id))
        with self.database.transaction() as connection:
            connection.execute(
                f"UPDATE email_mailboxes SET {', '.join(assignments)} WHERE id = ?",
                tuple(values),
            )
        return self.get_mailbox(actor, mailbox_id)

    def update_mailbox(
        self,
        actor: Actor,
        mailbox_id: str,
        *,
        name: str | None = None,
        settings: dict | None = None,
        enabled: bool | None = None,
    ) -> EmailMailbox:
        row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        assignments = ["updated_at = ?"]
        values: list[object] = [int(self.clock())]
        if name is not None:
            display, normalized = normalized_name(
                name,
                "mailbox name",
                maximum=160,
            )
            assignments.extend(["name = ?", "name_normalized = ?"])
            values.extend([display, normalized])
        if settings is not None:
            assignments.append("settings_json = ?")
            values.append(self._json(self._settings(settings)))
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise ValueError("mailbox enabled must be a boolean")
            assignments.append("enabled = ?")
            values.append(1 if enabled else 0)
        values.append(str(mailbox_id))
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    f"UPDATE email_mailboxes SET {', '.join(assignments)} WHERE id = ?",
                    tuple(values),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email mailbox name is already configured for this owner"
            ) from error
        return self.get_mailbox(actor, mailbox_id)

    def delete_mailbox(self, actor: Actor, mailbox_id: str) -> str | None:
        row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        secret_id = (
            str(row["secret_id"])
            if row["secret_id"] is not None
            else None
        )
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM email_mailboxes WHERE id = ?",
                (str(mailbox_id),),
            )
        return secret_id

    def create_group(
        self,
        actor: Actor,
        owner_user_id: str,
        name: str,
        *,
        description: str = "",
        enabled: bool = True,
        quiet_window_seconds: int = 0,
    ) -> EmailGroup:
        OwnershipPolicy.require_write(actor, str(owner_user_id))
        display, normalized = normalized_name(
            name,
            "email group name",
            maximum=160,
        )
        description_value = sanitize_text(description)[:1000]
        quiet = int(quiet_window_seconds)
        if not 0 <= quiet <= 604800:
            raise ValueError(
                "email group quiet window must be between 0 and 604800 seconds"
            )
        now = int(self.clock())
        group_id = uuid.uuid4().hex
        try:
            with self.database.transaction() as connection:
                self._enabled_owner(connection, owner_user_id)
                connection.execute(
                    """
                    INSERT INTO email_groups(
                        id, owner_user_id, name, name_normalized,
                        description, enabled, quiet_window_seconds,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        group_id,
                        str(owner_user_id),
                        display,
                        normalized,
                        description_value,
                        1 if enabled else 0,
                        quiet,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email group name is already configured for this owner"
            ) from error
        return self.get_group(actor, group_id)

    def update_group(
        self,
        actor: Actor,
        group_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        quiet_window_seconds: int | None = None,
    ) -> EmailGroup:
        row = self._group_row(group_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        assignments = ["updated_at = ?"]
        values: list[object] = [int(self.clock())]
        if name is not None:
            display, normalized = normalized_name(
                name,
                "email group name",
                maximum=160,
            )
            assignments.extend(["name = ?", "name_normalized = ?"])
            values.extend([display, normalized])
        if description is not None:
            assignments.append("description = ?")
            values.append(sanitize_text(description)[:1000])
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise ValueError("email group enabled must be a boolean")
            assignments.append("enabled = ?")
            values.append(1 if enabled else 0)
        if quiet_window_seconds is not None:
            quiet = int(quiet_window_seconds)
            if not 0 <= quiet <= 604800:
                raise ValueError(
                    "email group quiet window must be between 0 and 604800 seconds"
                )
            assignments.append("quiet_window_seconds = ?")
            values.append(quiet)
        values.append(str(group_id))
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    f"UPDATE email_groups SET {', '.join(assignments)} WHERE id = ?",
                    tuple(values),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email group name is already configured for this owner"
            ) from error
        return self.get_group(actor, group_id)

    def delete_group(self, actor: Actor, group_id: str) -> None:
        row = self._group_row(group_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM email_groups WHERE id = ?",
                (str(group_id),),
            )

    def get_group(self, actor: Actor, group_id: str) -> EmailGroup:
        row = self._group_row(group_id)
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._group(row)

    def list_groups(self, actor: Actor) -> list[EmailGroup]:
        with self.database.connect() as connection:
            if actor.is_admin:
                rows = connection.execute(
                    "SELECT * FROM email_groups ORDER BY name_normalized"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM email_groups
                    WHERE owner_user_id = ?
                    ORDER BY name_normalized
                    """,
                    (actor.user_id,),
                ).fetchall()
        return [self._group(row) for row in rows]

    def create_rule(
        self,
        actor: Actor,
        owner_user_id: str,
        group_id: str,
        name: str,
        classification: str,
        conditions: list[dict],
        *,
        match_mode: str = "all",
        priority: int = 100,
        enabled: bool = True,
    ) -> EmailRule:
        OwnershipPolicy.require_write(actor, str(owner_user_id))
        display, normalized = normalized_name(
            name,
            "email rule name",
            maximum=160,
        )
        classification_value = self._classification(classification)
        mode = str(match_mode or "").strip().casefold()
        if mode not in EMAIL_MATCH_MODES:
            raise ValueError("email rule match mode must be all or any")
        conditions_value = self._conditions(conditions)
        priority_value = int(priority)
        if not 0 <= priority_value <= 100000:
            raise ValueError("email rule priority must be between 0 and 100000")
        now = int(self.clock())
        rule_id = uuid.uuid4().hex

        try:
            with self.database.transaction() as connection:
                self._enabled_owner(connection, owner_user_id)
                group = connection.execute(
                    "SELECT owner_user_id FROM email_groups WHERE id = ?",
                    (str(group_id),),
                ).fetchone()
                if group is None:
                    raise KeyError("email group not found")
                if str(group["owner_user_id"]) != str(owner_user_id):
                    raise PermissionError(
                        "email rule and group must have the same owner"
                    )
                connection.execute(
                    """
                    INSERT INTO email_rules(
                        id, owner_user_id, group_id, name, name_normalized,
                        classification, match_mode, conditions_json,
                        priority, enabled, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rule_id,
                        str(owner_user_id),
                        str(group_id),
                        display,
                        normalized,
                        classification_value,
                        mode,
                        self._json(conditions_value),
                        priority_value,
                        1 if enabled else 0,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email rule name is already configured in this group"
            ) from error
        return self.get_rule(actor, rule_id)

    def update_rule(
        self,
        actor: Actor,
        rule_id: str,
        *,
        group_id: str | None = None,
        name: str | None = None,
        classification: str | None = None,
        conditions: list[dict] | None = None,
        match_mode: str | None = None,
        priority: int | None = None,
        enabled: bool | None = None,
    ) -> EmailRule:
        row = self._rule_row(rule_id)
        owner_user_id = str(row["owner_user_id"])
        OwnershipPolicy.require_write(actor, owner_user_id)
        assignments = ["updated_at = ?"]
        values: list[object] = [int(self.clock())]
        if group_id is not None:
            group = self._group_row(group_id)
            if str(group["owner_user_id"]) != owner_user_id:
                raise PermissionError(
                    "email rule and group must have the same owner"
                )
            assignments.append("group_id = ?")
            values.append(str(group_id))
        if name is not None:
            display, normalized = normalized_name(
                name,
                "email rule name",
                maximum=160,
            )
            assignments.extend(["name = ?", "name_normalized = ?"])
            values.extend([display, normalized])
        if classification is not None:
            assignments.append("classification = ?")
            values.append(self._classification(classification))
        if conditions is not None:
            assignments.append("conditions_json = ?")
            values.append(self._json(self._conditions(conditions)))
        if match_mode is not None:
            mode = str(match_mode or "").strip().casefold()
            if mode not in EMAIL_MATCH_MODES:
                raise ValueError("email rule match mode must be all or any")
            assignments.append("match_mode = ?")
            values.append(mode)
        if priority is not None:
            priority_value = int(priority)
            if not 0 <= priority_value <= 100000:
                raise ValueError(
                    "email rule priority must be between 0 and 100000"
                )
            assignments.append("priority = ?")
            values.append(priority_value)
        if enabled is not None:
            if not isinstance(enabled, bool):
                raise ValueError("email rule enabled must be a boolean")
            assignments.append("enabled = ?")
            values.append(1 if enabled else 0)
        values.append(str(rule_id))
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    f"UPDATE email_rules SET {', '.join(assignments)} WHERE id = ?",
                    tuple(values),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "email rule name is already configured in this group"
            ) from error
        return self.get_rule(actor, rule_id)

    def delete_rule(self, actor: Actor, rule_id: str) -> None:
        row = self._rule_row(rule_id)
        OwnershipPolicy.require_write(actor, str(row["owner_user_id"]))
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM email_rules WHERE id = ?",
                (str(rule_id),),
            )

    def get_rule(self, actor: Actor, rule_id: str) -> EmailRule:
        row = self._rule_row(rule_id)
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._rule(row)

    def list_rules(
        self,
        actor: Actor,
        *,
        group_id: str | None = None,
    ) -> list[EmailRule]:
        query = "SELECT * FROM email_rules"
        values: list[str] = []
        clauses = []
        if not actor.is_admin:
            clauses.append("owner_user_id = ?")
            values.append(actor.user_id)
        if group_id is not None:
            clauses.append("group_id = ?")
            values.append(str(group_id))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY priority, name_normalized"
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(values)).fetchall()
        return [self._rule(row) for row in rows]

    def record_message(
        self,
        actor: Actor,
        mailbox_id: str,
        *,
        provider_message_id: str = "",
        internet_message_id: str = "",
        sender: str = "",
        recipients: list[str] | tuple[str, ...] = (),
        subject: str = "",
        received_at: int | None = None,
        folder: str = "",
        labels: list[str] | tuple[str, ...] = (),
        provider_deep_link: str = "",
        metadata: dict | None = None,
        metadata_retention_days: int = DEFAULT_EMAIL_METADATA_RETENTION_DAYS,
    ) -> tuple[EmailMessage, bool]:
        mailbox_row = self._mailbox_row(mailbox_id)
        OwnershipPolicy.require_write(
            actor,
            str(mailbox_row["owner_user_id"]),
        )
        owner_user_id = str(mailbox_row["owner_user_id"])
        identity = email_message_identity(
            str(mailbox_id),
            provider_message_id=provider_message_id,
            internet_message_id=internet_message_id,
        )
        sender_value, sender_normalized, sender_domain = self._optional_email(
            sender,
            "sender",
        )
        recipient_values = tuple(
            self._email_address(value, "recipient")[0]
            for value in list(recipients)[:256]
        )
        label_values = tuple(
            sanitize_text(value)[:160]
            for value in list(labels)[:128]
            if sanitize_text(value)[:160]
        )
        metadata_value = self._object(
            {} if metadata is None else metadata,
            "email message metadata",
        )
        deep_link = self._deep_link(provider_deep_link)
        now = int(self.clock())
        received = now if received_at is None else int(received_at)
        expires = self._expiry(
            now,
            metadata_retention_days,
            "email metadata retention",
        )
        message_id = uuid.uuid4().hex

        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO email_messages(
                        id, owner_user_id, mailbox_id, provider_message_id,
                        internet_message_id, identity_key, sender,
                        sender_normalized, sender_domain, recipients_json,
                        subject, folder, labels_json, provider_deep_link,
                        metadata_json, received_at, metadata_expires_at,
                        created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        message_id,
                        owner_user_id,
                        str(mailbox_id),
                        sanitize_text(provider_message_id)[:1024],
                        sanitize_text(internet_message_id)[:1024],
                        identity,
                        sender_value,
                        sender_normalized,
                        sender_domain,
                        self._json(list(recipient_values)),
                        sanitize_text(subject)[:2000],
                        sanitize_text(folder)[:512],
                        self._json(list(label_values)),
                        deep_link,
                        self._json(metadata_value),
                        received,
                        expires,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError:
            with self.database.connect() as connection:
                existing = connection.execute(
                    """
                    SELECT * FROM email_messages
                    WHERE mailbox_id = ? AND identity_key = ?
                    """,
                    (str(mailbox_id), identity),
                ).fetchone()
            if existing is None:
                raise
            return self._message(existing), False

        return self.get_message(actor, message_id), True

    def list_messages(
        self,
        actor: Actor,
        *,
        mailbox_id: str | None = None,
        limit: int = 100,
    ) -> list[EmailMessage]:
        bounded = max(1, min(int(limit), 500))
        query = "SELECT * FROM email_messages"
        clauses = []
        values: list[object] = []
        if not actor.is_admin:
            clauses.append("owner_user_id = ?")
            values.append(actor.user_id)
        if mailbox_id is not None:
            clauses.append("mailbox_id = ?")
            values.append(str(mailbox_id))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY received_at DESC, id DESC LIMIT ?"
        values.append(bounded)
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(values)).fetchall()
        return [self._message(row) for row in rows]

    def list_activity_messages(
        self,
        actor: Actor,
        *,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """Return only messages that participated in Nowlert processing."""

        bounded = max(1, min(int(limit), 500))
        values: list[object] = []
        owner_clause = ""
        if not actor.is_admin:
            owner_clause = "AND email_messages.owner_user_id = ?"
            values.append(actor.user_id)
        values.append(bounded)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT email_messages.*
                FROM email_messages
                WHERE EXISTS (
                    SELECT 1
                    FROM email_processing_history
                    WHERE email_processing_history.message_id = email_messages.id
                )
                {owner_clause}
                ORDER BY email_messages.received_at DESC, email_messages.id DESC
                LIMIT ?
                """,
                tuple(values),
            ).fetchall()
        return [self._message(row) for row in rows]

    def get_message(self, actor: Actor, message_id: str) -> EmailMessage:
        row = self._message_row(message_id)
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._message(row)

    def store_raw_content(
        self,
        actor: Actor,
        message_id: str,
        raw_content: bytes | str,
        *,
        content_type: str = "message/rfc822",
        retention_days: int = DEFAULT_EMAIL_CONTENT_RETENTION_DAYS,
    ) -> dict:
        message = self._message_row(message_id)
        OwnershipPolicy.require_write(actor, str(message["owner_user_id"]))
        if isinstance(raw_content, str):
            content = raw_content.encode("utf-8")
        elif isinstance(raw_content, bytes):
            content = raw_content
        else:
            raise ValueError("raw email content must be bytes or text")
        if len(content) > _MAX_RAW_CONTENT_BYTES:
            raise ValueError("raw email content exceeds the 5 MiB foundation limit")
        content_type_value = str(content_type or "").strip().casefold()
        if not _CONTENT_TYPE.fullmatch(content_type_value):
            raise ValueError("email content type is invalid")
        now = int(self.clock())
        expires = self._expiry(
            now,
            retention_days,
            "email raw content retention",
        )
        digest = hashlib.sha256(content).hexdigest()
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO email_message_contents(
                    message_id, content_type, raw_content, content_sha256,
                    stored_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    content_type = excluded.content_type,
                    raw_content = excluded.raw_content,
                    content_sha256 = excluded.content_sha256,
                    stored_at = excluded.stored_at,
                    expires_at = excluded.expires_at
                """,
                (
                    str(message_id),
                    content_type_value,
                    sqlite3.Binary(content),
                    digest,
                    now,
                    expires,
                ),
            )
        return {
            "message_id": str(message_id),
            "content_type": content_type_value,
            "content_sha256": digest,
            "size_bytes": len(content),
            "stored_at": now,
            "expires_at": expires,
        }

    def read_raw_content(self, actor: Actor, message_id: str) -> bytes:
        message = self._message_row(message_id)
        OwnershipPolicy.require_read(actor, str(message["owner_user_id"]))
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT raw_content FROM email_message_contents WHERE message_id = ?",
                (str(message_id),),
            ).fetchone()
        if row is None:
            raise KeyError("raw email content not found")
        return bytes(row["raw_content"])

    def record_processing(
        self,
        actor: Actor,
        message_id: str,
        action: str,
        *,
        classification: str = "",
        group_id: str | None = None,
        rule_id: str | None = None,
        details: dict | None = None,
        event_id: str = "",
        retention_days: int = DEFAULT_EMAIL_PROCESSING_RETENTION_DAYS,
    ) -> EmailProcessingRecord:
        message = self._message_row(message_id)
        owner_user_id = str(message["owner_user_id"])
        OwnershipPolicy.require_write(actor, owner_user_id)
        action_value = str(action or "").strip().casefold()
        if action_value not in EMAIL_PROCESSING_ACTIONS:
            raise ValueError("email processing action is invalid")
        classification_value = (
            self._classification(classification)
            if str(classification or "").strip()
            else ""
        )
        group_value = self._owned_optional(
            "email_groups", group_id, owner_user_id, "email group"
        )
        rule_value = self._owned_optional(
            "email_rules", rule_id, owner_user_id, "email rule"
        )
        details_value = self._safe_details(details)
        now = int(self.clock())
        expires = self._expiry(
            now,
            retention_days,
            "email processing retention",
        )
        record_id = uuid.uuid4().hex
        with self.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO email_processing_history(
                    id, owner_user_id, message_id, group_id, rule_id,
                    action, classification, details_json, event_id,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    owner_user_id,
                    str(message_id),
                    group_value,
                    rule_value,
                    action_value,
                    classification_value or None,
                    self._json(details_value),
                    sanitize_text(event_id)[:128] or None,
                    now,
                    expires,
                ),
            )
        return self.get_processing(actor, record_id)

    def get_processing(
        self,
        actor: Actor,
        record_id: str,
    ) -> EmailProcessingRecord:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_processing_history WHERE id = ?",
                (str(record_id),),
            ).fetchone()
        if row is None:
            raise KeyError("email processing record not found")
        OwnershipPolicy.require_read(actor, str(row["owner_user_id"]))
        return self._processing(row)

    def list_processing(
        self,
        actor: Actor,
        *,
        message_id: str | None = None,
        limit: int = 100,
    ) -> list[EmailProcessingRecord]:
        bounded = max(1, min(int(limit), 500))
        query = "SELECT * FROM email_processing_history"
        clauses = []
        values: list[object] = []
        if not actor.is_admin:
            clauses.append("owner_user_id = ?")
            values.append(actor.user_id)
        if message_id is not None:
            clauses.append("message_id = ?")
            values.append(str(message_id))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        values.append(bounded)
        with self.database.connect() as connection:
            rows = connection.execute(query, tuple(values)).fetchall()
        return [self._processing(row) for row in rows]

    def latest_processing(
        self,
        actor: Actor,
        message_id: str,
    ) -> EmailProcessingRecord | None:
        message = self._message_row(message_id)
        OwnershipPolicy.require_read(actor, str(message["owner_user_id"]))
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM email_processing_history
                WHERE message_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (str(message_id),),
            ).fetchone()
        return self._processing(row) if row is not None else None

    def recent_group_delivery(
        self,
        actor: Actor,
        group_id: str,
        *,
        since: int,
        excluding_message_id: str = "",
    ) -> EmailProcessingRecord | None:
        group = self._group_row(group_id)
        OwnershipPolicy.require_read(actor, str(group["owner_user_id"]))
        values: list[object] = [
            str(group_id),
            int(since),
        ]
        excluding = str(excluding_message_id or "").strip()
        exclusion_sql = ""
        if excluding:
            exclusion_sql = " AND message_id <> ?"
            values.append(excluding)
        with self.database.connect() as connection:
            row = connection.execute(
                f"""
                SELECT * FROM email_processing_history
                WHERE group_id = ?
                  AND created_at >= ?
                  AND action IN ('promoted', 'reprocessed')
                  {exclusion_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                tuple(values),
            ).fetchone()
        return self._processing(row) if row is not None else None

    def build_event(
        self,
        actor: Actor,
        message_id: str,
        classification: str,
        *,
        group_id: str = "",
        rule_id: str = "",
    ) -> EmailAlertEvent:
        message = self.get_message(actor, message_id)
        mailbox = self.get_mailbox(actor, message.mailbox_id)
        classification_value = self._classification(classification)

        group_name = ""
        group_value = ""
        if group_id:
            group = self.get_group(actor, group_id)
            if group.owner_user_id != message.owner_user_id:
                raise PermissionError(
                    "email event group and message must have the same owner"
                )
            group_value = group.id
            group_name = group.name

        rule_name = ""
        rule_value = ""
        if rule_id:
            rule = self.get_rule(actor, rule_id)
            if rule.owner_user_id != message.owner_user_id:
                raise PermissionError(
                    "email event rule and message must have the same owner"
                )
            rule_value = rule.id
            rule_name = rule.name
            if group_value and rule.group_id != group_value:
                raise ValueError("email event rule is not part of the selected group")
            if not group_value:
                group = self.get_group(actor, rule.group_id)
                group_value = group.id
                group_name = group.name

        return EmailAlertEvent(
            message_id=message.id,
            mailbox_id=mailbox.id,
            mailbox=mailbox.address,
            provider=mailbox.provider,
            provider_message_id=message.provider_message_id,
            internet_message_id=message.internet_message_id,
            sender=message.sender,
            sender_domain=message.sender_domain,
            recipient=message.recipients[0] if message.recipients else "",
            recipients=message.recipients,
            subject=message.subject,
            group_id=group_value,
            group=group_name,
            rule_id=rule_value,
            rule=rule_name,
            classification=classification_value,
            provider_deep_link=message.provider_deep_link,
            received_at=message.received_at,
        )

    def purge_expired(self, *, now: int | None = None) -> dict:
        timestamp = int(self.clock()) if now is None else int(now)
        removed = {
            "raw_content_deleted": 0,
            "processing_history_deleted": 0,
            "message_metadata_deleted": 0,
        }
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                DELETE FROM email_message_contents
                WHERE expires_at IS NOT NULL AND expires_at <= ?
                """,
                (timestamp,),
            )
            removed["raw_content_deleted"] = max(0, int(cursor.rowcount))
            cursor = connection.execute(
                """
                DELETE FROM email_processing_history
                WHERE expires_at IS NOT NULL AND expires_at <= ?
                """,
                (timestamp,),
            )
            removed["processing_history_deleted"] = max(0, int(cursor.rowcount))
            cursor = connection.execute(
                """
                DELETE FROM email_messages
                WHERE metadata_expires_at IS NOT NULL
                  AND metadata_expires_at <= ?
                """,
                (timestamp,),
            )
            removed["message_metadata_deleted"] = max(0, int(cursor.rowcount))
        return removed

    def _mailbox_row(self, mailbox_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_mailboxes WHERE id = ?",
                (str(mailbox_id),),
            ).fetchone()
        if row is None:
            raise KeyError("email mailbox not found")
        return row

    def _group_row(self, group_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_groups WHERE id = ?",
                (str(group_id),),
            ).fetchone()
        if row is None:
            raise KeyError("email group not found")
        return row

    def _rule_row(self, rule_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_rules WHERE id = ?",
                (str(rule_id),),
            ).fetchone()
        if row is None:
            raise KeyError("email rule not found")
        return row

    def _message_row(self, message_id: str):
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_messages WHERE id = ?",
                (str(message_id),),
            ).fetchone()
        if row is None:
            raise KeyError("email message not found")
        return row

    @staticmethod
    def _enabled_owner(connection, owner_user_id: str) -> None:
        row = connection.execute(
            "SELECT enabled FROM users WHERE id = ?",
            (str(owner_user_id),),
        ).fetchone()
        if row is None:
            raise KeyError("email resource owner not found")
        if not bool(row["enabled"]):
            raise PermissionError(
                "disabled users cannot own new email alert resources"
            )

    def _owned_optional(
        self,
        table: str,
        resource_id: str | None,
        owner_user_id: str,
        label: str,
    ) -> str | None:
        if resource_id is None or not str(resource_id).strip():
            return None
        if table not in {"email_groups", "email_rules"}:
            raise ValueError("unsupported email owned resource")
        with self.database.connect() as connection:
            row = connection.execute(
                f"SELECT owner_user_id FROM {table} WHERE id = ?",
                (str(resource_id),),
            ).fetchone()
        if row is None:
            raise KeyError(f"{label} not found")
        if str(row["owner_user_id"]) != str(owner_user_id):
            raise PermissionError(
                f"{label} and email message must have the same owner"
            )
        return str(resource_id)

    @staticmethod
    def _classification(value: str) -> str:
        classification = str(value or "").strip().casefold()
        if classification not in EMAIL_CLASSIFICATIONS:
            raise ValueError("email classification is invalid")
        return classification

    @classmethod
    def _conditions(cls, value) -> list[dict]:
        if not isinstance(value, list):
            raise ValueError("email rule conditions must be a list")
        if not 1 <= len(value) <= 32:
            raise ValueError(
                "email rule must contain between 1 and 32 conditions"
            )
        result = []
        for condition in value:
            if not isinstance(condition, dict):
                raise ValueError("email rule conditions must be objects")
            if set(condition) - {"field", "operator", "value"}:
                raise ValueError("email rule condition contains unsupported fields")
            field = str(condition.get("field") or "").strip().casefold()
            operator = str(condition.get("operator") or "").strip().casefold()
            raw_value = sanitize_text(condition.get("value"))[:2000]
            if field not in EMAIL_RULE_FIELDS:
                raise ValueError("email rule condition field is invalid")
            if operator not in EMAIL_RULE_OPERATORS:
                raise ValueError("email rule condition operator is invalid")
            if not raw_value:
                raise ValueError("email rule condition value is required")
            if field in {"sender", "sender_domain", "recipient", "mailbox"}:
                raw_value = raw_value.casefold()
            result.append(
                {
                    "field": field,
                    "operator": operator,
                    "value": raw_value,
                }
            )
        cls._json(result)
        return result

    @classmethod
    def _settings(cls, value) -> dict:
        result = cls._object(
            {} if value is None else value,
            "email mailbox settings",
        )
        cls._reject_sensitive_settings(result)
        return result

    @classmethod
    def _reject_sensitive_settings(cls, value) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if _SENSITIVE_KEY.search(str(key)):
                    raise ValueError(
                        "email mailbox secrets must use the secret store"
                    )
                cls._reject_sensitive_settings(child)
        elif isinstance(value, list):
            for child in value:
                cls._reject_sensitive_settings(child)

    @classmethod
    def _safe_details(cls, value) -> dict:
        supplied = cls._object(
            {} if value is None else value,
            "email processing details",
        )
        result = cls._safe_detail_value(supplied, depth=0)
        if not isinstance(result, dict):
            raise ValueError("email processing details must be an object")
        cls._json(result)
        return result

    @classmethod
    def _safe_detail_value(cls, value, *, depth: int):
        if depth > 3:
            return sanitize_text(value)[:1000]
        if isinstance(value, dict):
            result = {}
            for key, child in list(value.items())[:32]:
                label = sanitize_text(key)[:64]
                if not label:
                    continue
                if _SENSITIVE_KEY.search(label):
                    result[label] = "<redacted>"
                else:
                    result[label] = cls._safe_detail_value(
                        child,
                        depth=depth + 1,
                    )
            return result
        if isinstance(value, list):
            return [
                cls._safe_detail_value(child, depth=depth + 1)
                for child in value[:32]
            ]
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, (int, float)):
            return value
        return sanitize_text(value)[:1000]

    @staticmethod
    def _object(value, label: str) -> dict:
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an object")
        return dict(value)

    @staticmethod
    def _json(value) -> str:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
            raise ValueError("email alert JSON value exceeds 65536 bytes")
        return encoded

    @staticmethod
    def _deep_link(value: str) -> str:
        link = str(value or "").strip()
        if not link:
            return ""
        if len(link) > 2048:
            raise ValueError("email provider deep link is too long")
        parsed = urlsplit(link)
        if (
            parsed.scheme.casefold() != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError(
                "email provider deep link must be a safe HTTPS URL"
            )
        return link

    @classmethod
    def _email_address(
        cls,
        value: str,
        label: str,
    ) -> tuple[str, str, str]:
        _display, address = parseaddr(str(value or ""))
        address = address.strip()
        if not address or len(address) > 320 or "@" not in address:
            raise ValueError(f"{label} must be a valid email address")
        local, domain = address.rsplit("@", 1)
        if (
            not local
            or not domain
            or len(domain) > 253
            or any(character.isspace() for character in address)
        ):
            raise ValueError(f"{label} must be a valid email address")
        normalized = f"{local}@{domain.casefold()}"
        return address, normalized, domain.casefold()

    @classmethod
    def _optional_email(
        cls,
        value: str,
        label: str,
    ) -> tuple[str, str, str]:
        if not str(value or "").strip():
            return "", "", ""
        return cls._email_address(value, label)

    @staticmethod
    def _expiry(now: int, days: int, label: str) -> int | None:
        if isinstance(days, bool):
            raise ValueError(f"{label} must be an integer")
        value = int(days)
        if value == 0:
            return None
        if not 1 <= value <= 3650:
            raise ValueError(
                f"{label} must be 0 or between 1 and 3650 days"
            )
        return int(now) + value * 86400

    @staticmethod
    def _mailbox(row) -> EmailMailbox:
        return EmailMailbox(
            id=str(row["id"]),
            owner_user_id=str(row["owner_user_id"]),
            provider=str(row["provider"]),
            name=str(row["name"]),
            address=str(row["address"]),
            secret_configured=row["secret_id"] is not None,
            settings=json.loads(str(row["settings_json"] or "{}")),
            enabled=bool(row["enabled"]),
            connection_state=str(row["connection_state"]),
            sync_cursor=str(row["sync_cursor"] or ""),
            last_sync_at=(
                int(row["last_sync_at"])
                if row["last_sync_at"] is not None
                else None
            ),
            last_error_code=str(row["last_error_code"] or ""),
            last_error_safe=str(row["last_error_safe"] or ""),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _group(row) -> EmailGroup:
        return EmailGroup(
            id=str(row["id"]),
            owner_user_id=str(row["owner_user_id"]),
            name=str(row["name"]),
            description=str(row["description"] or ""),
            enabled=bool(row["enabled"]),
            quiet_window_seconds=int(row["quiet_window_seconds"]),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _rule(row) -> EmailRule:
        decoded = json.loads(str(row["conditions_json"] or "[]"))
        return EmailRule(
            id=str(row["id"]),
            owner_user_id=str(row["owner_user_id"]),
            group_id=str(row["group_id"]),
            name=str(row["name"]),
            classification=str(row["classification"]),
            match_mode=str(row["match_mode"]),
            conditions=tuple(
                dict(item) for item in decoded if isinstance(item, dict)
            ),
            priority=int(row["priority"]),
            enabled=bool(row["enabled"]),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _message(row) -> EmailMessage:
        recipients = json.loads(str(row["recipients_json"] or "[]"))
        labels = json.loads(str(row["labels_json"] or "[]"))
        metadata = json.loads(str(row["metadata_json"] or "{}"))
        return EmailMessage(
            id=str(row["id"]),
            owner_user_id=str(row["owner_user_id"]),
            mailbox_id=str(row["mailbox_id"]),
            provider_message_id=str(row["provider_message_id"] or ""),
            internet_message_id=str(row["internet_message_id"] or ""),
            identity_key=str(row["identity_key"]),
            sender=str(row["sender"] or ""),
            sender_domain=str(row["sender_domain"] or ""),
            recipients=tuple(str(item) for item in recipients),
            subject=str(row["subject"] or ""),
            folder=str(row["folder"] or ""),
            labels=tuple(str(item) for item in labels),
            provider_deep_link=str(row["provider_deep_link"] or ""),
            metadata=metadata if isinstance(metadata, dict) else {},
            received_at=int(row["received_at"]),
            metadata_expires_at=(
                int(row["metadata_expires_at"])
                if row["metadata_expires_at"] is not None
                else None
            ),
            created_at=int(row["created_at"]),
            updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _processing(row) -> EmailProcessingRecord:
        details = json.loads(str(row["details_json"] or "{}"))
        return EmailProcessingRecord(
            id=str(row["id"]),
            owner_user_id=str(row["owner_user_id"]),
            message_id=str(row["message_id"]),
            group_id=(
                str(row["group_id"])
                if row["group_id"] is not None
                else None
            ),
            rule_id=(
                str(row["rule_id"])
                if row["rule_id"] is not None
                else None
            ),
            action=str(row["action"]),
            classification=str(row["classification"] or ""),
            details=details if isinstance(details, dict) else {},
            event_id=str(row["event_id"] or ""),
            created_at=int(row["created_at"]),
            expires_at=(
                int(row["expires_at"])
                if row["expires_at"] is not None
                else None
            ),
        )


__all__ = [
    "DEFAULT_EMAIL_CONTENT_RETENTION_DAYS",
    "DEFAULT_EMAIL_METADATA_RETENTION_DAYS",
    "DEFAULT_EMAIL_PROCESSING_RETENTION_DAYS",
    "EMAIL_CONNECTION_STATES",
    "EMAIL_MAILBOX_PROVIDERS",
    "EMAIL_MATCH_MODES",
    "EMAIL_RULE_FIELDS",
    "EMAIL_RULE_OPERATORS",
    "EMAIL_PROCESSING_ACTIONS",
    "EmailAlertStore",
    "EmailGroup",
    "EmailMailbox",
    "EmailMessage",
    "EmailProcessingRecord",
    "EmailRule",
    "email_message_identity",
]
