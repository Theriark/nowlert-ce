"""Email Alert classification, suppression, conversion, and routing."""

from __future__ import annotations

import time
import uuid

from dataclasses import dataclass
from typing import Callable

from email_rules import EmailRuleEngine
from email_security import build_email_preview
from models import Notification
from storage.audit_events import AuditEventStore
from storage.email_alerts import EmailAlertStore
from storage.ownership import Actor
from storage.routing_bridge import PlatformRoutingBridge
from storage.sanitize import sanitize_text


_TERMINAL_ACTIONS = frozenset(
    {"promoted", "reprocessed", "ignored", "suppressed", "duplicate", "error"}
)
_CLASSIFICATION_SEVERITY = {
    "urgent": "critical",
    "warning": "warning",
    "information": "information",
}
_MAX_RULE_BODY_CHARS = 64 * 1024
_MAX_NOTIFICATION_BODY_CHARS = 4000


def email_message_text(raw: bytes) -> str:
    """Extract bounded sanitized body text without exposing attachments."""

    try:
        return build_email_preview(raw).text[:_MAX_RULE_BODY_CHARS]
    except (TypeError, ValueError):
        return ""


@dataclass(frozen=True)
class EmailPipelineResult:
    message_id: str
    action: str
    matched: bool
    classification: str = ""
    group_id: str = ""
    rule_id: str = ""
    event_id: str = ""
    matched_routes: int = 0
    delivered: int = 0
    failed: int = 0
    attempts: int = 0
    replay: bool = False
    reason: str = ""

    def public(self) -> dict:
        return {
            "message_id": self.message_id,
            "action": self.action,
            "matched": self.matched,
            "classification": self.classification,
            "group_id": self.group_id,
            "rule_id": self.rule_id,
            "event_id": self.event_id,
            "matched_routes": self.matched_routes,
            "delivered": self.delivered,
            "failed": self.failed,
            "attempts": self.attempts,
            "replay": self.replay,
            "reason": self.reason,
        }


class EmailAlertProcessor:
    """Turn one retained mailbox message into the normal Nowlert routing path."""

    def __init__(
        self,
        database,
        *,
        store: EmailAlertStore | None = None,
        rules: EmailRuleEngine | None = None,
        audit: AuditEventStore | None = None,
        delivery=None,
        raw_loader: Callable[[Actor, str], bytes] | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.database = database
        self.clock = clock
        self.store = store or EmailAlertStore(database, clock=clock)
        self.rules = rules or EmailRuleEngine(self.store)
        self.audit = audit or AuditEventStore(database, clock=clock)
        self._delivery = delivery
        self.raw_loader = raw_loader

    def process(
        self,
        actor: Actor,
        message_id: str,
        *,
        replay: bool = False,
        bypass_quiet_window: bool = False,
    ) -> EmailPipelineResult:
        message = self.store.get_message(actor, message_id)
        if message.owner_user_id != actor.user_id and not actor.is_admin:
            raise PermissionError("email message is not available to this user")
        owner_actor = Actor(message.owner_user_id, "user")

        latest = self.store.latest_processing(owner_actor, message.id)
        if latest is not None and latest.action in _TERMINAL_ACTIONS and not replay:
            record = self.store.record_processing(
                owner_actor,
                message.id,
                "duplicate",
                classification=latest.classification,
                group_id=latest.group_id,
                rule_id=latest.rule_id,
                details={"reason": "already_processed"},
                event_id=latest.event_id,
            )
            self._audit(
                actor,
                "email.message.duplicate",
                message.id,
                "success",
                {"previous_action": latest.action},
            )
            return EmailPipelineResult(
                message_id=message.id,
                action=record.action,
                matched=bool(latest.rule_id),
                classification=latest.classification,
                group_id=latest.group_id or "",
                rule_id=latest.rule_id or "",
                event_id=latest.event_id,
                replay=False,
                reason="already_processed",
            )

        body = ""
        if self.rules.requires_body(owner_actor, message.id):
            if self.raw_loader is None:
                return self._processing_error(
                    owner_actor,
                    message.id,
                    audit_actor=actor,
                    replay=replay,
                    reason="message_content_unavailable",
                )
            try:
                body = email_message_text(
                    self.raw_loader(owner_actor, message.id)
                )
            except Exception:
                return self._processing_error(
                    owner_actor,
                    message.id,
                    audit_actor=actor,
                    replay=replay,
                    reason="message_content_unavailable",
                )

        evaluation = self.rules.evaluate_message(
            owner_actor,
            message.id,
            body=body,
        )
        if not evaluation.matched:
            record = self.store.record_processing(
                owner_actor,
                message.id,
                "ignored",
                details={
                    "reason": "no_matching_rule",
                    "replay": bool(replay),
                },
            )
            self._audit(
                actor,
                "email.message.ignore",
                message.id,
                "success",
                {"reason": "no_matching_rule", "replay": bool(replay)},
            )
            return EmailPipelineResult(
                message_id=message.id,
                action=record.action,
                matched=False,
                replay=bool(replay),
                reason="no_matching_rule",
            )

        classification = evaluation.classification
        group = self.store.get_group(owner_actor, evaluation.group_id)
        explanation = {
            "matched_conditions": [
                condition.public()
                for condition in evaluation.conditions
                if condition.matched
            ],
            "resulting_classification": classification,
            "resulting_severity": _CLASSIFICATION_SEVERITY.get(
                classification,
                "information",
            ),
        }
        if classification == "ignore":
            record = self.store.record_processing(
                owner_actor,
                message.id,
                "ignored",
                classification=classification,
                group_id=evaluation.group_id,
                rule_id=evaluation.rule_id,
                details={
                    "reason": "classification_ignore",
                    "replay": bool(replay),
                    **explanation,
                },
            )
            self._audit(
                actor,
                "email.message.ignore",
                message.id,
                "success",
                {
                    "classification": classification,
                    "rule_id": evaluation.rule_id,
                    "replay": bool(replay),
                },
            )
            return EmailPipelineResult(
                message_id=message.id,
                action=record.action,
                matched=True,
                classification=classification,
                group_id=evaluation.group_id,
                rule_id=evaluation.rule_id,
                replay=bool(replay),
                reason="classification_ignore",
            )

        if (
            group.quiet_window_seconds > 0
            and not bypass_quiet_window
            and self.store.recent_group_delivery(
                owner_actor,
                group.id,
                since=int(self.clock()) - group.quiet_window_seconds,
                excluding_message_id=message.id,
            )
            is not None
        ):
            record = self.store.record_processing(
                owner_actor,
                message.id,
                "suppressed",
                classification=classification,
                group_id=evaluation.group_id,
                rule_id=evaluation.rule_id,
                details={
                    "reason": "quiet_window",
                    "quiet_window_seconds": group.quiet_window_seconds,
                    "replay": bool(replay),
                    **explanation,
                },
            )
            self._audit(
                actor,
                "email.message.suppress",
                message.id,
                "success",
                {
                    "group_id": group.id,
                    "quiet_window_seconds": group.quiet_window_seconds,
                    "replay": bool(replay),
                },
            )
            return EmailPipelineResult(
                message_id=message.id,
                action=record.action,
                matched=True,
                classification=classification,
                group_id=evaluation.group_id,
                rule_id=evaluation.rule_id,
                replay=bool(replay),
                reason="quiet_window",
            )

        event = self.store.build_event(
            owner_actor,
            message.id,
            classification,
            group_id=evaluation.group_id,
            rule_id=evaluation.rule_id,
        )
        event_id = uuid.uuid4().hex
        notification = self._notification(event, body, event_id)
        summary = self._delivery_service().deliver(owner_actor, notification)
        action = "reprocessed" if replay else "promoted"
        details = {
            "matched_routes": summary.matched_routes,
            "delivered": summary.delivered,
            "failed": summary.failed,
            "attempts": summary.attempts,
            "replay": bool(replay),
            "bypass_quiet_window": bool(bypass_quiet_window),
            **explanation,
        }
        self.store.record_processing(
            owner_actor,
            message.id,
            action,
            classification=classification,
            group_id=evaluation.group_id,
            rule_id=evaluation.rule_id,
            details=details,
            event_id=event_id,
        )
        self._audit(
            actor,
            "email.message.reprocess" if replay else "email.message.promote",
            message.id,
            "success",
            {
                "classification": classification,
                "group_id": evaluation.group_id,
                "rule_id": evaluation.rule_id,
                **details,
            },
        )
        return EmailPipelineResult(
            message_id=message.id,
            action=action,
            matched=True,
            classification=classification,
            group_id=evaluation.group_id,
            rule_id=evaluation.rule_id,
            event_id=event_id,
            matched_routes=summary.matched_routes,
            delivered=summary.delivered,
            failed=summary.failed,
            attempts=summary.attempts,
            replay=bool(replay),
            reason=(
                "no_matching_route"
                if summary.matched_routes == 0
                else (
                    "delivery_failed"
                    if summary.delivered == 0 and summary.failed > 0
                    else "routed"
                )
            ),
        )

    def _delivery_service(self):
        if self._delivery is None:
            self._delivery = PlatformRoutingBridge(self.database).delivery
        return self._delivery

    @staticmethod
    def _notification(event, body: str, event_id: str) -> Notification:
        severity = _CLASSIFICATION_SEVERITY[event.classification]
        metadata = {
            **event.filter_metadata(),
            "_input_type": "email",
            "severity": severity,
            "status": severity,
            "state": event.classification,
            "event_type": "email_alert",
            "event_name": event.subject or "Email alert",
            "event_id": event_id,
        }
        summary = (
            body[:_MAX_NOTIFICATION_BODY_CHARS]
            if body
            else (
                f"Email from {event.sender or 'unknown sender'} "
                f"to {event.mailbox} matched {event.rule or 'an Email Alert rule'}."
            )
        )
        return Notification(
            source="email",
            category=event.group or "Email Alerts",
            status=severity,
            title=event.subject or "Email alert",
            subject=event.subject,
            body=summary,
            sender=event.sender,
            metadata=metadata,
        )

    def _processing_error(
        self,
        actor: Actor,
        message_id: str,
        *,
        audit_actor: Actor | None = None,
        replay: bool,
        reason: str,
    ) -> EmailPipelineResult:
        self.store.record_processing(
            actor,
            message_id,
            "error",
            details={"reason": reason, "replay": bool(replay)},
        )
        self._audit(
            audit_actor or actor,
            "email.message.process",
            message_id,
            "failed",
            {"reason": reason, "replay": bool(replay)},
        )
        return EmailPipelineResult(
            message_id=message_id,
            action="error",
            matched=False,
            replay=bool(replay),
            reason=reason,
        )

    def _audit(self, actor, action, message_id, outcome, details):
        try:
            self.audit.write(
                actor,
                action,
                "email_message",
                str(message_id),
                outcome,
                details,
            )
        except Exception:
            pass


__all__ = [
    "EmailAlertProcessor",
    "EmailPipelineResult",
    "email_message_text",
]
