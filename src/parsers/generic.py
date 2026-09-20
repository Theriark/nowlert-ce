"""
Nowlert

generic.py

Fallback parser.

Used when no platform-specific parser matches
an incoming email.
"""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import parseaddr

from bs4 import BeautifulSoup

from models import Notification


class Parser:
    """Generic email parser used only after dedicated parsers decline."""

    def parse(
        self,
        message: EmailMessage,
    ) -> Notification:
        subject = self._clean(
            message.get("Subject", ""),
            500,
        )
        sender = self._clean(
            message.get("From", ""),
            500,
        )
        body = self._body(message)
        display_name, address = parseaddr(sender)
        provider = self._clean(
            display_name or address or "Generic SMTP",
            128,
        )
        started = self._clean(
            message.get("Date", ""),
            128,
        )
        message_id = self._clean(
            message.get("Message-ID", ""),
            256,
        )

        notification = Notification(
            source="generic",
            category="email",
            status="information",
            title=subject or "Generic SMTP notification",
            subject=subject,
            body=body or subject or "Generic SMTP notification",
            sender=sender,
            start_time=started,
        )
        notification.metadata = {
            "provider": provider,
            "sender": sender,
            "sender_address": self._clean(address, 320),
            "severity": "information",
            "event_state": "active",
            "message_id": message_id,
            "format": "smtp",
        }
        return notification

    @staticmethod
    def _clean(value, limit: int) -> str:
        return " ".join(
            str(value or "").replace("\x00", " ").split()
        )[:limit]

    @classmethod
    def _body(cls, message: EmailMessage) -> str:
        plain: list[str] = []
        html: list[str] = []
        parts = message.walk() if message.is_multipart() else (message,)

        for part in parts:
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            try:
                content = str(part.get_content())
            except Exception:
                raw = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                content = raw.decode(charset, "replace")
            if content_type == "text/plain":
                plain.append(content)
            else:
                html.append(
                    BeautifulSoup(content, "lxml").get_text("\n")
                )

        selected = plain or html
        lines = []
        for line in "\n".join(selected).replace("\x00", " ").splitlines():
            cleaned = " ".join(line.split())
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)[:4000]
