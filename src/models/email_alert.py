"""Normalized Email Alerts event contract."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


EMAIL_CLASSIFICATIONS = frozenset(
    {"urgent", "warning", "information", "ignore"}
)
EMAIL_EVENT_PROVIDERS = frozenset(
    {"gmail", "microsoft_365", "imap", "smtp"}
)


def _safe_deep_link(value: str) -> str:
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
        raise ValueError("email provider deep link must be a safe HTTPS URL")
    return link


@dataclass(frozen=True)
class EmailAlertEvent:
    """Provider-neutral Email Alerts event ready for later Nowlert conversion."""

    message_id: str
    mailbox_id: str
    mailbox: str
    provider: str
    provider_message_id: str
    internet_message_id: str
    sender: str
    sender_domain: str
    recipient: str
    recipients: tuple[str, ...]
    subject: str
    group_id: str
    group: str
    rule_id: str
    rule: str
    classification: str
    provider_deep_link: str
    received_at: int

    def __post_init__(self) -> None:
        provider = str(self.provider or "").strip().casefold()
        classification = str(self.classification or "").strip().casefold()
        if provider not in EMAIL_EVENT_PROVIDERS:
            raise ValueError("email event provider is not supported")
        if classification not in EMAIL_CLASSIFICATIONS:
            raise ValueError("email event classification is invalid")
        if not str(self.message_id or "").strip():
            raise ValueError("email event message identifier is required")
        if not str(self.mailbox_id or "").strip():
            raise ValueError("email event mailbox identifier is required")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(
            self,
            "provider_deep_link",
            _safe_deep_link(self.provider_deep_link),
        )
        object.__setattr__(
            self,
            "recipients",
            tuple(str(item) for item in self.recipients),
        )
        object.__setattr__(self, "received_at", int(self.received_at))

    @property
    def source(self) -> str:
        return "email"

    def filter_metadata(self) -> dict:
        return {
            "mailbox": self.mailbox,
            "mailbox_id": self.mailbox_id,
            "sender": self.sender,
            "sender_domain": self.sender_domain,
            "recipient": self.recipient,
            "recipients": list(self.recipients),
            "subject": self.subject,
            "group": self.group,
            "group_id": self.group_id,
            "rule": self.rule,
            "rule_id": self.rule_id,
            "provider": self.provider,
            "provider_message_id": self.provider_message_id,
            "internet_message_id": self.internet_message_id,
            "message_id": self.message_id,
            "classification": self.classification,
            "provider_deep_link": self.provider_deep_link,
            "received_at": self.received_at,
        }

    def public(self) -> dict:
        return {"source": self.source, **self.filter_metadata()}


__all__ = [
    "EMAIL_CLASSIFICATIONS",
    "EMAIL_EVENT_PROVIDERS",
    "EmailAlertEvent",
]
