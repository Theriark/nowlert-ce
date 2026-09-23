"""Deterministic Email Alerts rule matching.

Phase 7 owns classification. Phase 8 consumes this result and promotes matched
messages into the existing Nowlert event/routing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from storage.email_alerts import (
    EmailAlertStore,
    EmailMailbox,
    EmailMessage,
    EmailRule,
)
from storage.ownership import Actor


@dataclass(frozen=True)
class EmailConditionResult:
    field: str
    operator: str
    value: str
    matched: bool

    def public(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "matched": self.matched,
        }


@dataclass(frozen=True)
class EmailRuleEvaluation:
    matched: bool
    rule_id: str = ""
    group_id: str = ""
    classification: str = ""
    conditions: tuple[EmailConditionResult, ...] = ()

    def public(self) -> dict:
        return {
            "matched": self.matched,
            "rule_id": self.rule_id,
            "group_id": self.group_id,
            "classification": self.classification,
            "conditions": [item.public() for item in self.conditions],
        }


class EmailRuleEngine:
    """Evaluate owner-scoped Email rules in deterministic priority order."""

    def __init__(self, store: EmailAlertStore):
        self.store = store

    def requires_body(
        self,
        actor: Actor,
        message_id: str,
    ) -> bool:
        message = self.store.get_message(actor, message_id)
        owner_id = message.owner_user_id
        enabled_groups = {
            item.id
            for item in self.store.list_groups(actor)
            if item.enabled and item.owner_user_id == owner_id
        }
        return any(
            rule.enabled
            and rule.owner_user_id == owner_id
            and rule.group_id in enabled_groups
            and any(
                str(condition.get("field") or "") == "body"
                for condition in rule.conditions
            )
            for rule in self.store.list_rules(actor)
        )

    def evaluate_message(
        self,
        actor: Actor,
        message_id: str,
        *,
        body: str = "",
    ) -> EmailRuleEvaluation:
        message = self.store.get_message(actor, message_id)
        mailbox = self.store.get_mailbox(actor, message.mailbox_id)
        owner_id = message.owner_user_id
        groups = {
            item.id: item
            for item in self.store.list_groups(actor)
            if item.enabled and item.owner_user_id == owner_id
        }
        for rule in self.store.list_rules(actor):
            if (
                not rule.enabled
                or rule.owner_user_id != owner_id
                or rule.group_id not in groups
            ):
                continue
            result = self.evaluate_rule(
                rule,
                message,
                mailbox,
                body=body,
            )
            if result.matched:
                return result
        return EmailRuleEvaluation(False)

    @classmethod
    def evaluate_rule(
        cls,
        rule: EmailRule,
        message: EmailMessage,
        mailbox: EmailMailbox,
        *,
        body: str = "",
    ) -> EmailRuleEvaluation:
        results = tuple(
            cls._condition(condition, message, mailbox, body)
            for condition in rule.conditions
        )
        if rule.match_mode == "all":
            matched = bool(results) and all(item.matched for item in results)
        else:
            matched = any(item.matched for item in results)
        return EmailRuleEvaluation(
            matched=matched,
            rule_id=rule.id if matched else "",
            group_id=rule.group_id if matched else "",
            classification=rule.classification if matched else "",
            conditions=results,
        )

    @classmethod
    def _condition(
        cls,
        condition: dict,
        message: EmailMessage,
        mailbox: EmailMailbox,
        body: str,
    ) -> EmailConditionResult:
        field = str(condition.get("field") or "")
        operator = str(condition.get("operator") or "")
        expected = str(condition.get("value") or "")
        candidates = cls._values(field, message, mailbox, body)
        matched = any(
            cls._compare(candidate, operator, expected)
            for candidate in candidates
        )
        return EmailConditionResult(
            field=field,
            operator=operator,
            value=expected,
            matched=matched,
        )

    @staticmethod
    def _values(
        field: str,
        message: EmailMessage,
        mailbox: EmailMailbox,
        body: str,
    ) -> tuple[str, ...]:
        if field == "sender":
            return (message.sender,)
        if field == "sender_domain":
            return (message.sender_domain,)
        if field == "recipient":
            return tuple(message.recipients)
        if field == "subject":
            return (message.subject,)
        if field == "body":
            return (str(body or ""),)
        if field == "mailbox":
            return (mailbox.address, mailbox.name, mailbox.id)
        return ()

    @staticmethod
    def _compare(candidate: str, operator: str, expected: str) -> bool:
        actual = str(candidate or "").casefold()
        wanted = str(expected or "").casefold()
        if operator == "equals":
            return actual == wanted
        if operator == "contains":
            return wanted in actual
        if operator == "starts_with":
            return actual.startswith(wanted)
        if operator == "ends_with":
            return actual.endswith(wanted)
        return False


__all__ = [
    "EmailConditionResult",
    "EmailRuleEngine",
    "EmailRuleEvaluation",
]
