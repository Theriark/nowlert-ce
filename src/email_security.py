"""Security boundary for Email Alerts message inspection.

Nowlert is not a webmail client. This module extracts bounded message content,
sanitizes HTML, blocks active/remote content, and reports attachment metadata
without retaining attachment payloads.
"""

from __future__ import annotations

import html
import re

from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from html.parser import HTMLParser
from urllib.parse import urlsplit

from storage.sanitize import sanitize_text


MAX_EMAIL_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PREVIEW_TEXT_CHARS = 64 * 1024
MAX_PREVIEW_HTML_CHARS = 128 * 1024
MAX_ATTACHMENT_COUNT = 32
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

_SAFE_ATTACHMENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/csv",
        "text/plain",
    }
)
_ALLOWED_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "hr",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
_VOID_TAGS = frozenset({"br", "hr"})
_BLOCKED_WITH_CONTENT = frozenset(
    {
        "audio",
        "button",
        "canvas",
        "embed",
        "form",
        "iframe",
        "input",
        "link",
        "math",
        "meta",
        "noscript",
        "object",
        "script",
        "style",
        "svg",
        "template",
        "video",
    }
)


@dataclass(frozen=True)
class EmailAttachmentInfo:
    name: str
    content_type: str
    size_bytes: int
    within_policy: bool
    retained: bool = False

    def public(self) -> dict:
        return {
            "name": self.name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "within_policy": self.within_policy,
            "retained": False,
        }


@dataclass(frozen=True)
class EmailSafePreview:
    text: str
    html: str
    attachments: tuple[EmailAttachmentInfo, ...]
    active_content_blocked: int
    remote_content_blocked: int
    source_size_bytes: int
    retained_source: bytes

    def public(self) -> dict:
        return {
            "text": self.text,
            "html": self.html,
            "attachments": [item.public() for item in self.attachments],
            "active_content_blocked": self.active_content_blocked,
            "remote_content_blocked": self.remote_content_blocked,
            "source_size_bytes": self.source_size_bytes,
            "attachment_policy": {
                "maximum_count": MAX_ATTACHMENT_COUNT,
                "maximum_size_bytes": MAX_ATTACHMENT_BYTES,
                "allowed_types": sorted(_SAFE_ATTACHMENT_TYPES),
                "retained": False,
            },
        }


class _SafeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.text_parts: list[str] = []
        self._blocked_depth = 0
        self.active_content_blocked = 0
        self.remote_content_blocked = 0

    def handle_starttag(self, tag, attrs):
        name = str(tag or "").casefold()
        if self._blocked_depth:
            if name in _BLOCKED_WITH_CONTENT:
                self._blocked_depth += 1
            return
        if name in _BLOCKED_WITH_CONTENT:
            self._blocked_depth = 1
            self.active_content_blocked += 1
            return
        if name == "img":
            self.remote_content_blocked += 1
            return
        if name not in _ALLOWED_TAGS:
            self.active_content_blocked += 1
            return

        rendered_attrs = ""
        if name == "a":
            href = ""
            title = ""
            for key, value in attrs:
                key = str(key or "").casefold()
                if key == "href":
                    href = self._safe_href(value)
                elif key == "title":
                    title = sanitize_text(value)[:256]
            values = []
            if href:
                values.append(f'href="{html.escape(href, quote=True)}"')
            if title:
                values.append(f'title="{html.escape(title, quote=True)}"')
            values.extend(['target="_blank"', 'rel="noopener noreferrer nofollow"'])
            rendered_attrs = " " + " ".join(values)
        self.output.append(f"<{name}{rendered_attrs}>")

    def handle_startendtag(self, tag, attrs):
        name = str(tag or "").casefold()
        if name == "img":
            self.remote_content_blocked += 1
            return
        self.handle_starttag(name, attrs)
        if name not in _VOID_TAGS:
            self.handle_endtag(name)

    def handle_endtag(self, tag):
        name = str(tag or "").casefold()
        if self._blocked_depth:
            if name in _BLOCKED_WITH_CONTENT:
                self._blocked_depth -= 1
            return
        if name in _ALLOWED_TAGS and name not in _VOID_TAGS:
            self.output.append(f"</{name}>")

    def handle_data(self, data):
        if self._blocked_depth:
            return
        value = str(data or "")
        if not value:
            return
        self.output.append(html.escape(value))
        compact = sanitize_text(value)
        if compact:
            self.text_parts.append(compact)

    def handle_entityref(self, name):
        if not self._blocked_depth:
            self.handle_data(html.unescape(f"&{name};"))

    def handle_charref(self, name):
        if not self._blocked_depth:
            self.handle_data(html.unescape(f"&#{name};"))

    def unknown_decl(self, data):
        self.active_content_blocked += 1

    def sanitized_html(self) -> str:
        return "".join(self.output)[:MAX_PREVIEW_HTML_CHARS]

    def text(self) -> str:
        return sanitize_text(" ".join(self.text_parts))[:MAX_PREVIEW_TEXT_CHARS]

    def _safe_href(self, value) -> str:
        candidate = str(value or "").strip()
        if not candidate or len(candidate) > 2048:
            return ""
        parsed = urlsplit(candidate)
        scheme = parsed.scheme.casefold()
        if scheme in {"http", "https"}:
            if (
                not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
            ):
                return ""
            return candidate
        if scheme == "mailto":
            return candidate
        return ""


def build_email_preview(raw: bytes) -> EmailSafePreview:
    source = bytes(raw)
    if len(source) > MAX_EMAIL_SOURCE_BYTES:
        raise ValueError("email message exceeds the 25 MiB inspection limit")
    try:
        message = BytesParser(policy=policy.default).parsebytes(source)
    except Exception as error:
        raise ValueError("email message could not be parsed safely") from error

    attachments = _attachments(message)
    body = _body_part(message)
    active_blocked = 0
    remote_blocked = 0
    if body is None:
        text = ""
        safe_html = "<p>No previewable message body.</p>"
    else:
        try:
            payload = str(body.get_content() or "")
        except Exception:
            payload = ""
        if body.get_content_subtype().casefold() == "html":
            sanitizer = _SafeHTML()
            try:
                sanitizer.feed(payload)
                sanitizer.close()
            except Exception:
                sanitizer = _SafeHTML()
                sanitizer.handle_data(re.sub(r"<[^>]+>", " ", payload))
            text = sanitizer.text()
            safe_html = sanitizer.sanitized_html()
            active_blocked = sanitizer.active_content_blocked
            remote_blocked = sanitizer.remote_content_blocked
            if not safe_html:
                safe_html = "<p>No previewable message body.</p>"
        else:
            text = sanitize_text(payload)[:MAX_PREVIEW_TEXT_CHARS]
            safe_html = (
                "<pre>"
                + html.escape(text)
                + "</pre>"
            )[:MAX_PREVIEW_HTML_CHARS]

    retained = EmailMessage()
    retained["X-Nowlert-Retained-Content"] = "sanitized-body-only"
    retained.set_content(text)
    if safe_html:
        retained.add_alternative(safe_html, subtype="html")
    retained_source = retained.as_bytes(policy=policy.default)

    return EmailSafePreview(
        text=text,
        html=safe_html,
        attachments=attachments,
        active_content_blocked=active_blocked,
        remote_content_blocked=remote_blocked,
        source_size_bytes=len(source),
        retained_source=retained_source,
    )


def _body_part(message):
    try:
        if message.is_multipart():
            return message.get_body(preferencelist=("plain", "html"))
        if message.get_content_maintype().casefold() == "text":
            return message
    except Exception:
        return None
    return None


def _attachments(message) -> tuple[EmailAttachmentInfo, ...]:
    result: list[EmailAttachmentInfo] = []
    try:
        parts = list(message.walk()) if message.is_multipart() else [message]
    except Exception:
        return ()
    for part in parts:
        if part.is_multipart():
            continue
        disposition = str(part.get_content_disposition() or "").casefold()
        filename = sanitize_text(part.get_filename() or "")[:240]
        content_type = str(part.get_content_type() or "application/octet-stream").casefold()
        is_attachment = disposition == "attachment" or bool(filename)
        if not is_attachment:
            continue
        if len(result) >= MAX_ATTACHMENT_COUNT:
            break
        try:
            payload = part.get_payload(decode=True)
            size = len(payload) if isinstance(payload, bytes) else 0
        except Exception:
            size = 0
        result.append(
            EmailAttachmentInfo(
                name=filename or "Unnamed attachment",
                content_type=content_type[:160],
                size_bytes=size,
                within_policy=(
                    size <= MAX_ATTACHMENT_BYTES
                    and content_type in _SAFE_ATTACHMENT_TYPES
                ),
                retained=False,
            )
        )
    return tuple(result)


__all__ = [
    "EmailAttachmentInfo",
    "EmailSafePreview",
    "MAX_ATTACHMENT_BYTES",
    "MAX_ATTACHMENT_COUNT",
    "MAX_EMAIL_SOURCE_BYTES",
    "build_email_preview",
]
