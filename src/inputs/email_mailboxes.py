"""Mailbox connection providers for Email Alerts.

This phase deliberately synchronizes message metadata first. Raw MIME is only
retrieved on demand so mailbox polling does not turn Nowlert into a webmail
client or retain message bodies unnecessarily.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import imaplib
import json
import secrets as token_secrets
import threading
import time

from dataclasses import dataclass
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from email.utils import getaddresses, parsedate_to_datetime
from typing import Callable
from urllib.parse import quote, urlencode, urlsplit

import requests

from email_alert_pipeline import EmailAlertProcessor
from environment import first_environment, secret_environment
from email_security import build_email_preview
from storage.audit_events import AuditEventStore
from storage.database import Database
from storage.email_alerts import EmailAlertStore, EmailMailbox, EmailMessage
from storage.ownership import Actor
from storage.sanitize import sanitize_text
from storage.secrets import SecretStore


GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
MICROSOFT_SCOPE = "https://graph.microsoft.com/Mail.Read"
_OAUTH_STATE_TTL_SECONDS = 10 * 60
_HTTP_TIMEOUT_SECONDS = 20
_DEFAULT_SYNC_LIMIT = 100
_MAX_SYNC_LIMIT = 500
_OAUTH_APPLICATION_FIELDS = ("client_id", "client_secret", "redirect_uri")
_OAUTH_MAILBOX_FIELDS = ("state_key", "access_token", "refresh_token", "expires_at")


def email_oauth_applications(configuration=None, *, environment=None) -> dict:
    """Load deployment-owned OAuth application credentials.

    OAuth application credentials belong to the Nowlert instance, never to an
    individual mailbox owner. The redirect URI defaults to the canonical
    WebUI URL so self-hosted operators configure the application once.
    """

    public_url = ""
    if configuration is not None:
        public_url = str(
            configuration.get("webui", "public_url", default="") or ""
        ).strip().rstrip("/")
    default_redirect = (
        f"{public_url}/ui/" if public_url else ""
    )

    common_redirect = str(
        first_environment(
            "NOWLERT_EMAIL_OAUTH_REDIRECT_URI",
            default=default_redirect,
            environment=environment,
        )
        or ""
    ).strip()

    def application(prefix: str) -> dict:
        return {
            "client_id": str(
                first_environment(
                    f"NOWLERT_EMAIL_{prefix}_CLIENT_ID",
                    default="",
                    environment=environment,
                )
                or ""
            ).strip(),
            "client_secret": str(
                secret_environment(
                    f"NOWLERT_EMAIL_{prefix}_CLIENT_SECRET",
                    default_file=(
                        "/run/secrets/"
                        f"nowlert_email_{prefix.casefold()}_client_secret"
                    ),
                    default="",
                    environment=environment,
                )
                or ""
            ).strip(),
            "redirect_uri": str(
                first_environment(
                    f"NOWLERT_EMAIL_{prefix}_REDIRECT_URI",
                    default=common_redirect,
                    environment=environment,
                )
                or ""
            ).strip(),
        }

    return {
        "gmail": application("GMAIL"),
        "microsoft_365": application("MICROSOFT"),
    }


class MailboxConnectionError(RuntimeError):
    """A provider failure with a safe, stable error code."""

    def __init__(self, code: str, safe_message: str):
        super().__init__(safe_message)
        self.code = str(code)
        self.safe_message = sanitize_text(safe_message)[:500]


@dataclass(frozen=True)
class MailboxProviderMessage:
    provider_message_id: str
    internet_message_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    received_at: int
    folder: str = ""
    labels: tuple[str, ...] = ()
    provider_deep_link: str = ""
    metadata: dict | None = None


@dataclass(frozen=True)
class MailboxSyncBatch:
    messages: tuple[MailboxProviderMessage, ...]
    cursor: str


@dataclass(frozen=True)
class MailboxSyncSummary:
    mailbox_id: str
    provider: str
    observed: int
    created: int
    duplicates: int
    cursor_changed: bool
    last_sync_at: int

    def public(self) -> dict:
        return {
            "mailbox_id": self.mailbox_id,
            "provider": self.provider,
            "observed": self.observed,
            "created": self.created,
            "duplicates": self.duplicates,
            "cursor_changed": self.cursor_changed,
            "last_sync_at": self.last_sync_at,
        }


@dataclass(frozen=True)
class OAuthStart:
    authorization_url: str
    expires_at: int

    def public(self) -> dict:
        return {
            "authorization_url": self.authorization_url,
            "expires_at": self.expires_at,
        }


class _HTTPProvider:
    def __init__(self, *, http=None, clock: Callable[[], float] = time.time):
        self.http = http or requests.Session()
        self.clock = clock

    def _json(
        self,
        method: str,
        url: str,
        *,
        headers=None,
        params=None,
        data=None,
        cursor_request: bool = False,
    ) -> dict:
        try:
            response = getattr(self.http, method)(
                url,
                headers=headers,
                params=params,
                data=data,
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise MailboxConnectionError(
                "provider_unreachable",
                "mailbox provider could not be reached",
            ) from error
        status = int(getattr(response, "status_code", 500))
        if status in {401, 403}:
            raise MailboxConnectionError(
                "authentication_required",
                "mailbox authorization is invalid or expired",
            )
        if cursor_request and status in {404, 410}:
            raise MailboxConnectionError(
                "sync_cursor_expired",
                "mailbox synchronization checkpoint expired",
            )
        if status < 200 or status >= 300:
            raise MailboxConnectionError(
                "provider_request_failed",
                f"mailbox provider returned HTTP {status}",
            )
        try:
            value = response.json()
        except (TypeError, ValueError) as error:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "mailbox provider returned an invalid response",
            ) from error
        if not isinstance(value, dict):
            raise MailboxConnectionError(
                "provider_response_invalid",
                "mailbox provider returned an invalid response",
            )
        return value

    def _form(self, url: str, data: dict) -> dict:
        return self._json("post", url, data=data)


class GmailMailboxProvider(_HTTPProvider):
    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_ROOT = "https://gmail.googleapis.com/gmail/v1/users/me"

    def authorization_url(
        self,
        mailbox: EmailMailbox,
        credentials: dict,
        state: str,
    ) -> str:
        return self.AUTHORIZATION_URL + "?" + urlencode(
            {
                "client_id": credentials["client_id"],
                "redirect_uri": credentials["redirect_uri"],
                "response_type": "code",
                "scope": GMAIL_SCOPE,
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
                "login_hint": mailbox.address,
            }
        )

    def exchange_code(self, credentials: dict, code: str) -> dict:
        return self._form(
            self.TOKEN_URL,
            {
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "redirect_uri": credentials["redirect_uri"],
                "grant_type": "authorization_code",
                "code": code,
            },
        )

    def refresh_token(self, credentials: dict) -> dict:
        return self._form(
            self.TOKEN_URL,
            {
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
            },
        )

    def sync(
        self,
        mailbox: EmailMailbox,
        access_token: str,
    ) -> MailboxSyncBatch:
        headers = {"Authorization": f"Bearer {access_token}"}
        limit = _sync_limit(mailbox.settings)
        ids: list[str] = []
        if mailbox.sync_cursor:
            try:
                ids = self._history_ids(
                    mailbox.sync_cursor,
                    headers,
                    limit,
                )
            except MailboxConnectionError as error:
                if error.code != "sync_cursor_expired":
                    raise
                ids = self._initial_ids(mailbox, headers, limit)
        else:
            ids = self._initial_ids(mailbox, headers, limit)

        messages = tuple(
            self._message(mailbox, headers, message_id)
            for message_id in ids
        )
        profile = self._json(
            "get",
            f"{self.API_ROOT}/profile",
            headers=headers,
        )
        cursor = str(profile.get("historyId") or mailbox.sync_cursor or "")
        if not cursor:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "Gmail did not return a synchronization checkpoint",
            )
        return MailboxSyncBatch(messages, cursor)

    def fetch_raw(
        self,
        _mailbox: EmailMailbox,
        message: EmailMessage,
        access_token: str,
    ) -> bytes:
        payload = self._json(
            "get",
            f"{self.API_ROOT}/messages/{quote(message.provider_message_id, safe='')}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "raw"},
        )
        encoded = str(payload.get("raw") or "")
        if not encoded:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "Gmail did not return message content",
            )
        try:
            padding = "=" * (-len(encoded) % 4)
            return base64.urlsafe_b64decode(encoded + padding)
        except (ValueError, TypeError) as error:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "Gmail returned invalid message content",
            ) from error

    def _initial_ids(self, mailbox, headers, limit: int) -> list[str]:
        label = str(mailbox.settings.get("label") or "INBOX").strip()
        payload = self._json(
            "get",
            f"{self.API_ROOT}/messages",
            headers=headers,
            params={
                "maxResults": limit,
                "labelIds": label,
            },
        )
        return [
            str(item.get("id"))
            for item in payload.get("messages", [])
            if isinstance(item, dict) and item.get("id")
        ][:limit]

    def _history_ids(self, cursor: str, headers, limit: int) -> list[str]:
        ids: list[str] = []
        page_token = ""
        while len(ids) < limit:
            params = {
                "startHistoryId": str(cursor),
                "historyTypes": "messageAdded",
                "maxResults": min(100, limit),
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._json(
                "get",
                f"{self.API_ROOT}/history",
                headers=headers,
                params=params,
                cursor_request=True,
            )
            for entry in payload.get("history", []):
                if not isinstance(entry, dict):
                    continue
                for added in entry.get("messagesAdded", []):
                    message = added.get("message") if isinstance(added, dict) else None
                    identifier = message.get("id") if isinstance(message, dict) else None
                    if identifier and str(identifier) not in ids:
                        ids.append(str(identifier))
                        if len(ids) >= limit:
                            break
                if len(ids) >= limit:
                    break
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token:
                break
        return ids

    def _message(self, mailbox, headers, message_id: str) -> MailboxProviderMessage:
        payload = self._json(
            "get",
            f"{self.API_ROOT}/messages/{quote(message_id, safe='')}",
            headers=headers,
            params=[
                ("format", "metadata"),
                ("metadataHeaders", "From"),
                ("metadataHeaders", "To"),
                ("metadataHeaders", "Cc"),
                ("metadataHeaders", "Subject"),
                ("metadataHeaders", "Message-ID"),
                ("metadataHeaders", "Date"),
            ],
        )
        header_items = (
            payload.get("payload", {}).get("headers", [])
            if isinstance(payload.get("payload"), dict)
            else []
        )
        headers_map = {}
        for item in header_items:
            if isinstance(item, dict) and item.get("name"):
                headers_map[str(item["name"]).casefold()] = str(item.get("value") or "")
        sender = _single_address(headers_map.get("from", ""))
        recipients = _addresses(
            headers_map.get("to", ""),
            headers_map.get("cc", ""),
        )
        received_at = _milliseconds_timestamp(
            payload.get("internalDate"),
            fallback=_header_timestamp(headers_map.get("date", ""), int(self.clock())),
        )
        thread_id = str(payload.get("threadId") or message_id)
        deep_link = (
            "https://mail.google.com/mail/u/?"
            + urlencode({"authuser": mailbox.address})
            + "#all/"
            + quote(thread_id, safe="")
        )
        return MailboxProviderMessage(
            provider_message_id=str(payload.get("id") or message_id),
            internet_message_id=headers_map.get("message-id", ""),
            sender=sender,
            recipients=recipients,
            subject=headers_map.get("subject", ""),
            received_at=received_at,
            folder=str(mailbox.settings.get("label") or "INBOX"),
            labels=tuple(
                str(item)
                for item in payload.get("labelIds", [])
                if str(item)
            ),
            provider_deep_link=deep_link,
            metadata={
                "thread_id": thread_id,
                "history_id": str(payload.get("historyId") or ""),
            },
        )


class Microsoft365MailboxProvider(_HTTPProvider):
    GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

    @staticmethod
    def _tenant(mailbox: EmailMailbox) -> str:
        tenant = str(mailbox.settings.get("tenant") or "common").strip()
        if (
            not tenant
            or len(tenant) > 128
            or "/" in tenant
            or "\\" in tenant
            or any(character.isspace() for character in tenant)
        ):
            raise ValueError("Microsoft tenant is invalid")
        return tenant

    def authorization_url(
        self,
        mailbox: EmailMailbox,
        credentials: dict,
        state: str,
    ) -> str:
        tenant = self._tenant(mailbox)
        endpoint = (
            f"https://login.microsoftonline.com/{quote(tenant, safe='')}"
            "/oauth2/v2.0/authorize"
        )
        return endpoint + "?" + urlencode(
            {
                "client_id": credentials["client_id"],
                "redirect_uri": credentials["redirect_uri"],
                "response_type": "code",
                "response_mode": "query",
                "scope": f"openid profile email offline_access {MICROSOFT_SCOPE}",
                "state": state,
                "login_hint": mailbox.address,
            }
        )

    def exchange_code(
        self,
        mailbox: EmailMailbox,
        credentials: dict,
        code: str,
    ) -> dict:
        return self._form(
            self._token_url(mailbox),
            {
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "redirect_uri": credentials["redirect_uri"],
                "grant_type": "authorization_code",
                "code": code,
                "scope": f"openid profile email offline_access {MICROSOFT_SCOPE}",
            },
        )

    def refresh_token(
        self,
        mailbox: EmailMailbox,
        credentials: dict,
    ) -> dict:
        return self._form(
            self._token_url(mailbox),
            {
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
                "scope": f"openid profile email offline_access {MICROSOFT_SCOPE}",
            },
        )

    def sync(
        self,
        mailbox: EmailMailbox,
        access_token: str,
    ) -> MailboxSyncBatch:
        headers = {"Authorization": f"Bearer {access_token}"}
        limit = _sync_limit(mailbox.settings)
        if mailbox.sync_cursor:
            url = _safe_graph_cursor(mailbox.sync_cursor)
            params = None
        else:
            folder = str(mailbox.settings.get("folder") or "inbox").strip()
            if not folder or len(folder) > 256:
                raise ValueError("Microsoft mail folder is invalid")
            url = (
                f"{self.GRAPH_ROOT}/me/mailFolders/"
                f"{quote(folder, safe='')}/messages/delta"
            )
            params = {
                "$select": (
                    "id,internetMessageId,receivedDateTime,subject,from,"
                    "toRecipients,ccRecipients,parentFolderId,categories,webLink"
                ),
                "$top": min(limit, 100),
            }

        messages: list[MailboxProviderMessage] = []
        cursor = mailbox.sync_cursor
        while True:
            payload = self._json(
                "get",
                url,
                headers=headers,
                params=params,
                cursor_request=bool(mailbox.sync_cursor),
            )
            params = None
            for item in payload.get("value", []):
                if isinstance(item, dict) and "@removed" not in item:
                    messages.append(self._message(mailbox, item))
            next_link = str(payload.get("@odata.nextLink") or "")
            delta_link = str(payload.get("@odata.deltaLink") or "")
            if len(messages) >= limit and next_link:
                cursor = _safe_graph_cursor(next_link)
                break
            if next_link:
                url = _safe_graph_cursor(next_link)
                continue
            cursor = _safe_graph_cursor(delta_link) if delta_link else cursor
            break
        if not cursor:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "Microsoft 365 did not return a synchronization checkpoint",
            )
        return MailboxSyncBatch(tuple(messages), cursor)

    def fetch_raw(
        self,
        _mailbox: EmailMailbox,
        message: EmailMessage,
        access_token: str,
    ) -> bytes:
        url = (
            f"{self.GRAPH_ROOT}/me/messages/"
            f"{quote(message.provider_message_id, safe='')}/$value"
        )
        try:
            response = self.http.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=_HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise MailboxConnectionError(
                "provider_unreachable",
                "Microsoft 365 could not be reached",
            ) from error
        status = int(getattr(response, "status_code", 500))
        if status in {401, 403}:
            raise MailboxConnectionError(
                "authentication_required",
                "mailbox authorization is invalid or expired",
            )
        if status < 200 or status >= 300:
            raise MailboxConnectionError(
                "provider_request_failed",
                f"Microsoft 365 returned HTTP {status}",
            )
        return bytes(getattr(response, "content", b""))

    def _token_url(self, mailbox: EmailMailbox) -> str:
        tenant = self._tenant(mailbox)
        return (
            f"https://login.microsoftonline.com/{quote(tenant, safe='')}"
            "/oauth2/v2.0/token"
        )

    def _message(self, mailbox, item: dict) -> MailboxProviderMessage:
        sender = ""
        from_value = item.get("from")
        if isinstance(from_value, dict):
            address = from_value.get("emailAddress")
            if isinstance(address, dict):
                sender = str(address.get("address") or "")
        recipients = []
        for key in ("toRecipients", "ccRecipients"):
            for entry in item.get(key, []):
                if not isinstance(entry, dict):
                    continue
                address = entry.get("emailAddress")
                if isinstance(address, dict) and address.get("address"):
                    recipients.append(str(address["address"]))
        received = _iso_timestamp(
            item.get("receivedDateTime"),
            int(self.clock()),
        )
        return MailboxProviderMessage(
            provider_message_id=str(item.get("id") or ""),
            internet_message_id=str(item.get("internetMessageId") or ""),
            sender=sender,
            recipients=tuple(recipients),
            subject=str(item.get("subject") or ""),
            received_at=received,
            folder=str(mailbox.settings.get("folder") or "inbox"),
            labels=tuple(str(value) for value in item.get("categories", []) if str(value)),
            provider_deep_link=str(item.get("webLink") or ""),
            metadata={
                "parent_folder_id": str(item.get("parentFolderId") or ""),
            },
        )


class IMAPMailboxProvider:
    def __init__(
        self,
        *,
        imap_factory=None,
        imap_ssl_factory=None,
        clock: Callable[[], float] = time.time,
    ):
        self.imap_factory = imap_factory or imaplib.IMAP4
        self.imap_ssl_factory = imap_ssl_factory or imaplib.IMAP4_SSL
        self.clock = clock

    def sync(
        self,
        mailbox: EmailMailbox,
        credentials: dict,
    ) -> MailboxSyncBatch:
        client = self._connect(mailbox, credentials)
        try:
            folder, uidvalidity = self._select(client, mailbox)
            cursor = _imap_cursor(mailbox.sync_cursor)
            limit = _sync_limit(mailbox.settings)
            last_uid = 0
            if cursor and cursor.get("uidvalidity") == uidvalidity:
                last_uid = int(cursor.get("last_uid") or 0)
                identifiers = self._search(
                    client,
                    f"UID {last_uid + 1}:*",
                )
            else:
                identifiers = self._search(client, "ALL")
                identifiers = identifiers[-limit:]
            messages = []
            for identifier in identifiers[:limit]:
                messages.append(
                    self._metadata_message(
                        client,
                        mailbox,
                        folder,
                        uidvalidity,
                        identifier,
                    )
                )
                last_uid = max(last_uid, int(identifier))
            if not identifiers and cursor and cursor.get("uidvalidity") == uidvalidity:
                last_uid = int(cursor.get("last_uid") or 0)
            encoded = json.dumps(
                {
                    "uidvalidity": uidvalidity,
                    "last_uid": last_uid,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            return MailboxSyncBatch(tuple(messages), encoded)
        finally:
            self._close(client)

    def fetch_raw(
        self,
        mailbox: EmailMailbox,
        message: EmailMessage,
        credentials: dict,
    ) -> bytes:
        uid = str(message.metadata.get("imap_uid") or "")
        expected_validity = str(message.metadata.get("imap_uidvalidity") or "")
        if not uid or not expected_validity:
            raise MailboxConnectionError(
                "provider_message_missing",
                "IMAP message location is not available",
            )
        client = self._connect(mailbox, credentials)
        try:
            _folder, current_validity = self._select(client, mailbox)
            if current_validity != expected_validity:
                raise MailboxConnectionError(
                    "sync_cursor_expired",
                    "IMAP mailbox identity changed; synchronize the mailbox again",
                )
            status, data = client.uid("fetch", uid, "(BODY.PEEK[])")
            if str(status).upper() != "OK":
                raise MailboxConnectionError(
                    "provider_request_failed",
                    "IMAP server could not return message content",
                )
            payload = _imap_bytes(data)
            if payload is None:
                raise MailboxConnectionError(
                    "provider_response_invalid",
                    "IMAP server returned invalid message content",
                )
            return payload
        finally:
            self._close(client)

    def _connect(self, mailbox: EmailMailbox, credentials: dict):
        settings = mailbox.settings
        host = str(settings["host"])
        port = int(settings["port"])
        security = str(settings["security"])
        try:
            if security == "ssl":
                client = self.imap_ssl_factory(
                    host,
                    port,
                    timeout=_HTTP_TIMEOUT_SECONDS,
                )
            else:
                client = self.imap_factory(
                    host,
                    port,
                    timeout=_HTTP_TIMEOUT_SECONDS,
                )
                status, _data = client.starttls()
                if str(status).upper() != "OK":
                    raise MailboxConnectionError(
                        "tls_failed",
                        "IMAP STARTTLS negotiation failed",
                    )
            status, _data = client.login(
                credentials["username"],
                credentials["password"],
            )
            if str(status).upper() != "OK":
                raise MailboxConnectionError(
                    "authentication_required",
                    "IMAP authentication failed",
                )
            return client
        except MailboxConnectionError:
            raise
        except (imaplib.IMAP4.error, OSError, TimeoutError) as error:
            raise MailboxConnectionError(
                "provider_unreachable",
                "IMAP mailbox could not be connected",
            ) from error

    def _select(self, client, mailbox):
        folder = str(mailbox.settings.get("folder") or "INBOX")
        try:
            status, _data = client.select(folder, readonly=True)
        except imaplib.IMAP4.error as error:
            raise MailboxConnectionError(
                "mailbox_unavailable",
                "IMAP folder could not be opened",
            ) from error
        if str(status).upper() != "OK":
            raise MailboxConnectionError(
                "mailbox_unavailable",
                "IMAP folder could not be opened",
            )
        response = client.response("UIDVALIDITY")
        values = response[1] if isinstance(response, tuple) and len(response) > 1 else None
        raw = values[0] if values else b""
        uidvalidity = (
            raw.decode("ascii", errors="ignore")
            if isinstance(raw, bytes)
            else str(raw or "")
        ).strip()
        if not uidvalidity:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "IMAP server did not return UIDVALIDITY",
            )
        return folder, uidvalidity

    @staticmethod
    def _search(client, criterion: str) -> list[str]:
        status, data = client.uid("search", None, criterion)
        if str(status).upper() != "OK":
            raise MailboxConnectionError(
                "provider_request_failed",
                "IMAP mailbox search failed",
            )
        raw = data[0] if data else b""
        text = raw.decode("ascii", errors="ignore") if isinstance(raw, bytes) else str(raw)
        return [value for value in text.split() if value.isdigit()]

    def _metadata_message(
        self,
        client,
        mailbox,
        folder: str,
        uidvalidity: str,
        uid: str,
    ) -> MailboxProviderMessage:
        status, data = client.uid(
            "fetch",
            uid,
            "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM TO CC SUBJECT DATE)])",
        )
        if str(status).upper() != "OK":
            raise MailboxConnectionError(
                "provider_request_failed",
                "IMAP message metadata could not be read",
            )
        payload = _imap_bytes(data)
        if payload is None:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "IMAP server returned invalid message metadata",
            )
        message = BytesParser(policy=default).parsebytes(payload)
        internet_id = str(message.get("Message-ID") or "")
        provider_id = "" if internet_id else f"imap:{uidvalidity}:{uid}"
        return MailboxProviderMessage(
            provider_message_id=provider_id,
            internet_message_id=internet_id,
            sender=_single_address(str(message.get("From") or "")),
            recipients=_addresses(
                str(message.get("To") or ""),
                str(message.get("Cc") or ""),
            ),
            subject=str(message.get("Subject") or ""),
            received_at=_header_timestamp(
                str(message.get("Date") or ""),
                int(self.clock()),
            ),
            folder=folder,
            metadata={
                "imap_uid": str(uid),
                "imap_uidvalidity": uidvalidity,
                "imap_folder": folder,
            },
        )

    @staticmethod
    def _close(client) -> None:
        try:
            client.close()
        except Exception:
            pass
        try:
            client.logout()
        except Exception:
            pass


class MailboxConnectionService:
    """Own mailbox credentials, OAuth, metadata sync and provider health."""

    def __init__(
        self,
        database: Database,
        *,
        store: EmailAlertStore | None = None,
        secrets: SecretStore | None = None,
        audit: AuditEventStore | None = None,
        http=None,
        imap_factory=None,
        imap_ssl_factory=None,
        oauth_applications: dict | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.database = database
        self.clock = clock
        self.store = store or EmailAlertStore(database, clock=clock)
        self.secrets = secrets or SecretStore(database, clock=clock)
        self.audit = audit or AuditEventStore(database, clock=clock)
        self.oauth_applications = (
            email_oauth_applications()
            if oauth_applications is None
            else {
                str(key): dict(value or {})
                for key, value in oauth_applications.items()
            }
        )
        self.gmail = GmailMailboxProvider(http=http, clock=clock)
        self.microsoft = Microsoft365MailboxProvider(http=http, clock=clock)
        self.imap = IMAPMailboxProvider(
            imap_factory=imap_factory,
            imap_ssl_factory=imap_ssl_factory,
            clock=clock,
        )
        self.processor = EmailAlertProcessor(
            database,
            store=self.store,
            audit=self.audit,
            raw_loader=self._raw_for_rules,
            clock=clock,
        )

    def create_mailbox(
        self,
        actor: Actor,
        owner_user_id: str,
        provider: str,
        address: str,
        *,
        name: str = "",
        settings: dict | None = None,
        credential: dict | None = None,
        enabled: bool = True,
    ) -> EmailMailbox:
        provider_value = str(provider or "").strip().casefold()
        settings_value = self._settings(provider_value, settings or {})
        credential_value = self._credential(provider_value, credential or {})
        if provider_value in {"gmail", "microsoft_365"}:
            credential_value.setdefault("state_key", token_secrets.token_urlsafe(32))
            self._oauth_application(provider_value, credential_value)
        secret = self.secrets.create(
            actor,
            owner_user_id,
            f"Email {provider_value} {token_secrets.token_hex(6)}",
            f"email-{provider_value}",
            _encode_credential(credential_value),
        )
        try:
            mailbox = self.store.create_mailbox(
                actor,
                owner_user_id,
                provider_value,
                address,
                name=name,
                secret_id=secret.id,
                settings=settings_value,
                enabled=enabled,
            )
        except Exception:
            self.secrets.delete(actor, secret.id)
            raise
        self.audit.write(
            actor,
            "email.mailbox.create",
            "email_mailbox",
            mailbox.id,
            "success",
            {"provider": mailbox.provider},
        )
        return mailbox

    def update_mailbox(
        self,
        actor: Actor,
        mailbox_id: str,
        *,
        name: str | None = None,
        settings: dict | None = None,
        enabled: bool | None = None,
    ) -> EmailMailbox:
        mailbox = self.store.get_mailbox(actor, mailbox_id)
        settings_value = (
            self._settings(mailbox.provider, settings)
            if settings is not None
            else None
        )
        updated = self.store.update_mailbox(
            actor,
            mailbox.id,
            name=name,
            settings=settings_value,
            enabled=enabled,
        )
        self.audit.write(
            actor,
            "email.mailbox.update",
            "email_mailbox",
            updated.id,
            "success",
            {"provider": updated.provider, "enabled": updated.enabled},
        )
        return updated

    def delete_mailbox(self, actor: Actor, mailbox_id: str) -> None:
        mailbox = self.store.get_mailbox(actor, mailbox_id)
        secret_id = self.store.delete_mailbox(actor, mailbox.id)
        if secret_id:
            try:
                self.secrets.delete(actor, secret_id)
            except KeyError:
                pass
        self.audit.write(
            actor,
            "email.mailbox.delete",
            "email_mailbox",
            mailbox.id,
            "success",
            {"provider": mailbox.provider},
        )

    def oauth_complete_from_state(
        self,
        actor: Actor,
        *,
        code: str,
        state: str,
    ) -> EmailMailbox:
        mailbox_id = _state_mailbox_id(state)
        return self.oauth_complete(
            actor,
            mailbox_id,
            code=code,
            state=state,
        )

    def oauth_start(self, actor: Actor, mailbox_id: str) -> OAuthStart:
        mailbox = self.store.get_mailbox(actor, mailbox_id)
        if mailbox.provider not in {"gmail", "microsoft_365"}:
            raise ValueError("OAuth is not used by this mailbox provider")
        credentials = self._credentials(actor, mailbox)
        application = self._oauth_application(mailbox.provider, credentials)
        oauth_credentials = {**credentials, **application}
        expires_at = int(self.clock()) + _OAUTH_STATE_TTL_SECONDS
        state = _signed_state(
            credentials["state_key"],
            mailbox.id,
            expires_at,
        )
        if mailbox.provider == "gmail":
            url = self.gmail.authorization_url(mailbox, oauth_credentials, state)
        else:
            url = self.microsoft.authorization_url(
                mailbox,
                oauth_credentials,
                state,
            )
        self.store.update_mailbox_connection(
            actor,
            mailbox.id,
            connection_state="connecting",
            clear_error=True,
        )
        self.audit.write(
            actor,
            "email.mailbox.oauth.start",
            "email_mailbox",
            mailbox.id,
            "success",
            {"provider": mailbox.provider},
        )
        return OAuthStart(url, expires_at)

    def oauth_complete(
        self,
        actor: Actor,
        mailbox_id: str,
        *,
        code: str,
        state: str,
    ) -> EmailMailbox:
        mailbox = self.store.get_mailbox(actor, mailbox_id)
        if mailbox.provider not in {"gmail", "microsoft_365"}:
            raise ValueError("OAuth is not used by this mailbox provider")
        credentials = self._credentials(actor, mailbox)
        application = self._oauth_application(mailbox.provider, credentials)
        oauth_credentials = {**credentials, **application}
        _verify_state(
            credentials["state_key"],
            mailbox.id,
            state,
            int(self.clock()),
        )
        authorization_code = str(code or "").strip()
        if not authorization_code or len(authorization_code) > 4096:
            raise ValueError("OAuth authorization code is invalid")
        try:
            if mailbox.provider == "gmail":
                token = self.gmail.exchange_code(
                    oauth_credentials,
                    authorization_code,
                )
            else:
                token = self.microsoft.exchange_code(
                    mailbox,
                    oauth_credentials,
                    authorization_code,
                )
            updated = self._merge_token(credentials, token)
            self._rotate_credentials(actor, mailbox, updated)
            mailbox = self.store.update_mailbox_connection(
                actor,
                mailbox.id,
                connection_state="healthy",
                clear_error=True,
            )
        except Exception as error:
            self._connection_failure(actor, mailbox, error)
            raise
        self.audit.write(
            actor,
            "email.mailbox.oauth.complete",
            "email_mailbox",
            mailbox.id,
            "success",
            {"provider": mailbox.provider},
        )
        return mailbox

    def sync_mailbox(
        self,
        actor: Actor,
        mailbox_id: str,
    ) -> MailboxSyncSummary:
        mailbox = self.store.get_mailbox(actor, mailbox_id)
        if not mailbox.enabled:
            raise PermissionError("email mailbox is disabled")
        self.store.update_mailbox_connection(
            actor,
            mailbox.id,
            connection_state="connecting",
            clear_error=True,
        )
        old_cursor = mailbox.sync_cursor
        try:
            credentials = self._credentials(actor, mailbox)
            if mailbox.provider == "gmail":
                access_token, credentials = self._oauth_access_token(
                    actor,
                    mailbox,
                    credentials,
                )
                batch = self.gmail.sync(mailbox, access_token)
            elif mailbox.provider == "microsoft_365":
                access_token, credentials = self._oauth_access_token(
                    actor,
                    mailbox,
                    credentials,
                )
                batch = self.microsoft.sync(mailbox, access_token)
            elif mailbox.provider == "imap":
                batch = self.imap.sync(mailbox, credentials)
            else:
                raise ValueError("email mailbox provider is not supported")

            created = 0
            duplicates = 0
            new_message_ids: list[str] = []
            for item in batch.messages:
                message, inserted = self.store.record_message(
                    actor,
                    mailbox.id,
                    provider_message_id=item.provider_message_id,
                    internet_message_id=item.internet_message_id,
                    sender=item.sender,
                    recipients=item.recipients,
                    subject=item.subject,
                    received_at=item.received_at,
                    folder=item.folder,
                    labels=item.labels,
                    provider_deep_link=item.provider_deep_link,
                    metadata=item.metadata or {},
                )
                if inserted:
                    created += 1
                    new_message_ids.append(message.id)
                else:
                    duplicates += 1
            synced_at = int(self.clock())
            mailbox = self.store.update_mailbox_connection(
                actor,
                mailbox.id,
                connection_state="healthy",
                sync_cursor=batch.cursor,
                last_sync_at=synced_at,
                clear_error=True,
            )
            for message_id in new_message_ids:
                try:
                    self.processor.process(actor, message_id)
                except Exception:
                    try:
                        self.store.record_processing(
                            actor,
                            message_id,
                            "error",
                            details={"reason": "processing_exception"},
                        )
                    except Exception:
                        pass
        except Exception as error:
            self._connection_failure(actor, mailbox, error)
            raise

        summary = MailboxSyncSummary(
            mailbox_id=mailbox.id,
            provider=mailbox.provider,
            observed=len(batch.messages),
            created=created,
            duplicates=duplicates,
            cursor_changed=batch.cursor != old_cursor,
            last_sync_at=synced_at,
        )
        self.audit.write(
            actor,
            "email.mailbox.sync",
            "email_mailbox",
            mailbox.id,
            "success",
            summary.public(),
        )
        return summary

    def fetch_raw_content(
        self,
        actor: Actor,
        message_id: str,
    ) -> dict:
        """Fetch on demand but retain only sanitized body content.

        Attachment payloads and remote/active HTML content never enter the
        retained message-content store.
        """

        message = self.store.get_message(actor, message_id)
        mailbox = self.store.get_mailbox(actor, message.mailbox_id)
        try:
            preview = build_email_preview(
                self._provider_raw_content(actor, mailbox, message)
            )
            stored = self.store.store_raw_content(
                actor,
                message.id,
                preview.retained_source,
                content_type="message/rfc822",
            )
            return {
                **stored,
                "attachments": [item.public() for item in preview.attachments],
                "active_content_blocked": preview.active_content_blocked,
                "remote_content_blocked": preview.remote_content_blocked,
            }
        except Exception as error:
            self._connection_failure(actor, mailbox, error, degraded=True)
            raise

    def preview_message(
        self,
        actor: Actor,
        message_id: str,
    ) -> dict:
        """Return a sandbox-ready preview without attachment payloads."""

        message = self.store.get_message(actor, message_id)
        mailbox = self.store.get_mailbox(actor, message.mailbox_id)
        try:
            raw = self._provider_raw_content(actor, mailbox, message)
            preview = build_email_preview(raw)
            self.store.store_raw_content(
                actor,
                message.id,
                preview.retained_source,
                content_type="message/rfc822",
            )
            self.audit.write(
                actor,
                "email.message.preview",
                "email_message",
                message.id,
                "success",
                {
                    "attachments": len(preview.attachments),
                    "active_content_blocked": preview.active_content_blocked,
                    "remote_content_blocked": preview.remote_content_blocked,
                },
            )
            return preview.public()
        except Exception as error:
            self._connection_failure(actor, mailbox, error, degraded=True)
            raise

    def _provider_raw_content(
        self,
        actor: Actor,
        mailbox: EmailMailbox,
        message: EmailMessage,
    ) -> bytes:
        credentials = self._credentials(actor, mailbox)
        if mailbox.provider == "gmail":
            access_token, _credentials = self._oauth_access_token(
                actor,
                mailbox,
                credentials,
            )
            return self.gmail.fetch_raw(mailbox, message, access_token)
        if mailbox.provider == "microsoft_365":
            access_token, _credentials = self._oauth_access_token(
                actor,
                mailbox,
                credentials,
            )
            return self.microsoft.fetch_raw(mailbox, message, access_token)
        if mailbox.provider == "imap":
            return self.imap.fetch_raw(mailbox, message, credentials)
        raise ValueError("email mailbox provider is not supported")

    def sync_ready_mailboxes(self) -> list[MailboxSyncSummary]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, owner_user_id
                FROM email_mailboxes
                WHERE enabled = 1
                  AND secret_id IS NOT NULL
                  AND connection_state IN ('healthy', 'degraded', 'connecting')
                ORDER BY id
                """
            ).fetchall()
        results = []
        for row in rows:
            actor = Actor(str(row["owner_user_id"]), "user")
            try:
                results.append(self.sync_mailbox(actor, str(row["id"])))
            except Exception:
                continue
        return results

    def _raw_for_rules(
        self,
        actor: Actor,
        message_id: str,
    ) -> bytes:
        try:
            return self.store.read_raw_content(actor, message_id)
        except KeyError:
            message = self.store.get_message(actor, message_id)
            mailbox = self.store.get_mailbox(actor, message.mailbox_id)
            preview = build_email_preview(
                self._provider_raw_content(actor, mailbox, message)
            )
            self.store.store_raw_content(
                actor,
                message.id,
                preview.retained_source,
                content_type="message/rfc822",
            )
            return preview.retained_source

    def _oauth_access_token(
        self,
        actor: Actor,
        mailbox: EmailMailbox,
        credentials: dict,
    ) -> tuple[str, dict]:
        access_token = str(credentials.get("access_token") or "")
        expires_at = int(credentials.get("expires_at") or 0)
        if access_token and expires_at > int(self.clock()) + 60:
            return access_token, credentials
        if not str(credentials.get("refresh_token") or ""):
            raise MailboxConnectionError(
                "authentication_required",
                "mailbox authorization is required",
            )
        application = self._oauth_application(mailbox.provider, credentials)
        oauth_credentials = {**credentials, **application}
        if mailbox.provider == "gmail":
            token = self.gmail.refresh_token(oauth_credentials)
        else:
            token = self.microsoft.refresh_token(mailbox, oauth_credentials)
        updated = self._merge_token(credentials, token)
        self._rotate_credentials(actor, mailbox, updated)
        return str(updated["access_token"]), updated

    def _merge_token(self, credentials: dict, token: dict) -> dict:
        access_token = str(token.get("access_token") or "")
        if not access_token:
            raise MailboxConnectionError(
                "provider_response_invalid",
                "mailbox provider did not return an access token",
            )
        updated = dict(credentials)
        updated["access_token"] = access_token
        refresh_token = str(token.get("refresh_token") or "")
        if refresh_token:
            updated["refresh_token"] = refresh_token
        expires_in = int(token.get("expires_in") or 3600)
        updated["expires_at"] = int(self.clock()) + max(60, min(expires_in, 86400))
        return updated

    def provider_status(self) -> dict:
        result = {
            "imap": {
                "label": "IMAP / IMAPS",
                "configured": True,
                "authentication": "credentials",
            }
        }
        for provider, label in (
            ("gmail", "Gmail"),
            ("microsoft_365", "Microsoft 365"),
        ):
            result[provider] = {
                "label": label,
                "configured": self._oauth_application_configured(provider),
                "authentication": "oauth",
            }
        return result

    def _oauth_application_configured(self, provider: str) -> bool:
        try:
            self._oauth_application(provider)
            return True
        except MailboxConnectionError:
            return False

    def _oauth_application(
        self,
        provider: str,
        legacy_credentials: dict | None = None,
    ) -> dict:
        configured = dict(self.oauth_applications.get(provider) or {})
        legacy = dict(legacy_credentials or {})
        application = {}
        for key in _OAUTH_APPLICATION_FIELDS:
            application[key] = str(
                configured.get(key) or legacy.get(key) or ""
            ).strip()

        if not all(application.values()):
            label = "Gmail" if provider == "gmail" else "Microsoft 365"
            raise MailboxConnectionError(
                "provider_not_configured",
                f"{label} OAuth is not configured by the Nowlert administrator",
            )

        parsed = urlsplit(application["redirect_uri"])
        if (
            parsed.scheme.casefold() != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise MailboxConnectionError(
                "provider_not_configured",
                "mailbox OAuth redirect URI is not configured safely",
            )
        return application

    def _credentials(
        self,
        actor: Actor,
        mailbox: EmailMailbox,
    ) -> dict:
        reference = self.store.mailbox_secret_id(actor, mailbox.id)
        if not reference:
            raise MailboxConnectionError(
                "credentials_missing",
                "mailbox credentials are not configured",
            )
        try:
            raw = self.secrets.resolve(actor, reference)
            value = json.loads(raw.decode("utf-8"))
        except (KeyError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise MailboxConnectionError(
                "credentials_invalid",
                "mailbox credentials are invalid",
            ) from error
        return self._credential(mailbox.provider, value, existing=True)

    def _rotate_credentials(
        self,
        actor: Actor,
        mailbox: EmailMailbox,
        credentials: dict,
    ) -> None:
        reference = self.store.mailbox_secret_id(actor, mailbox.id)
        if not reference:
            raise MailboxConnectionError(
                "credentials_missing",
                "mailbox credentials are not configured",
            )
        persisted = dict(credentials)
        if (
            mailbox.provider in {"gmail", "microsoft_365"}
            and self._oauth_application_configured(mailbox.provider)
        ):
            for key in _OAUTH_APPLICATION_FIELDS:
                persisted.pop(key, None)
        self.secrets.rotate(actor, reference, _encode_credential(persisted))

    def _connection_failure(
        self,
        actor: Actor,
        mailbox: EmailMailbox,
        error: Exception,
        *,
        degraded: bool = False,
    ) -> None:
        if isinstance(error, MailboxConnectionError):
            code = error.code
            message = error.safe_message
        else:
            code = "mailbox_sync_failed"
            message = "mailbox synchronization failed"
        try:
            self.store.update_mailbox_connection(
                actor,
                mailbox.id,
                connection_state="degraded" if degraded else "error",
                error_code=code,
                safe_error=message,
            )
            self.audit.write(
                actor,
                "email.mailbox.sync",
                "email_mailbox",
                mailbox.id,
                "failed",
                {"provider": mailbox.provider, "code": code},
            )
        except Exception:
            pass

    @staticmethod
    def _settings(provider: str, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError("email mailbox settings must be an object")
        supplied = dict(value)
        if provider == "gmail":
            allowed = {"label", "max_messages_per_sync"}
            unknown = set(supplied) - allowed
            if unknown:
                raise ValueError(f"unsupported Gmail setting: {sorted(unknown)[0]}")
            label = str(supplied.get("label") or "INBOX").strip()
            if not label or len(label) > 128:
                raise ValueError("Gmail label is invalid")
            return {
                "label": label,
                "max_messages_per_sync": _sync_limit(supplied),
            }
        if provider == "microsoft_365":
            allowed = {"tenant", "folder", "max_messages_per_sync"}
            unknown = set(supplied) - allowed
            if unknown:
                raise ValueError(
                    f"unsupported Microsoft 365 setting: {sorted(unknown)[0]}"
                )
            tenant = str(supplied.get("tenant") or "common").strip()
            folder = str(supplied.get("folder") or "inbox").strip()
            if not tenant or len(tenant) > 128 or "/" in tenant:
                raise ValueError("Microsoft tenant is invalid")
            if not folder or len(folder) > 256:
                raise ValueError("Microsoft mail folder is invalid")
            return {
                "tenant": tenant,
                "folder": folder,
                "max_messages_per_sync": _sync_limit(supplied),
            }
        if provider == "imap":
            allowed = {
                "host",
                "port",
                "security",
                "folder",
                "max_messages_per_sync",
            }
            unknown = set(supplied) - allowed
            if unknown:
                raise ValueError(f"unsupported IMAP setting: {sorted(unknown)[0]}")
            host = str(supplied.get("host") or "").strip()
            if (
                not host
                or len(host) > 253
                or any(character.isspace() for character in host)
            ):
                raise ValueError("IMAP host is invalid")
            security = str(supplied.get("security") or "ssl").strip().casefold()
            if security not in {"ssl", "starttls"}:
                raise ValueError("IMAP security must be ssl or starttls")
            default_port = 993 if security == "ssl" else 143
            port = int(supplied.get("port", default_port))
            if not 1 <= port <= 65535:
                raise ValueError("IMAP port is invalid")
            folder = str(supplied.get("folder") or "INBOX").strip()
            if not folder or len(folder) > 512:
                raise ValueError("IMAP folder is invalid")
            return {
                "host": host,
                "port": port,
                "security": security,
                "folder": folder,
                "max_messages_per_sync": _sync_limit(supplied),
            }
        raise ValueError("email mailbox provider is not supported")

    @staticmethod
    def _credential(
        provider: str,
        value: dict,
        *,
        existing: bool = False,
    ) -> dict:
        if not isinstance(value, dict):
            raise ValueError("mailbox credential must be an object")
        credential = dict(value)
        if provider in {"gmail", "microsoft_365"}:
            # OAuth application credentials are deployment-owned. The legacy
            # fields remain readable only so existing mailboxes continue to
            # work until the instance-level provider configuration is present.
            allowed = set(_OAUTH_APPLICATION_FIELDS) | set(_OAUTH_MAILBOX_FIELDS)
            unknown = set(credential) - allowed
            if unknown:
                raise ValueError(
                    f"unsupported OAuth credential field: {sorted(unknown)[0]}"
                )
            for key in _OAUTH_APPLICATION_FIELDS:
                if key not in credential:
                    continue
                text = str(credential.get(key) or "").strip()
                if not text or len(text) > 4096:
                    raise ValueError(f"{key} is invalid")
                credential[key] = text
            if "redirect_uri" in credential:
                parsed = urlsplit(credential["redirect_uri"])
                if (
                    parsed.scheme.casefold() != "https"
                    or not parsed.netloc
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    raise ValueError("OAuth redirect_uri must be a safe HTTPS URL")
            if existing:
                state_key = str(credential.get("state_key") or "")
                if len(state_key) < 32:
                    raise ValueError("mailbox OAuth state key is invalid")
            for key in ("access_token", "refresh_token", "state_key"):
                if key in credential:
                    credential[key] = str(credential.get(key) or "")
            if "expires_at" in credential:
                credential["expires_at"] = int(credential.get("expires_at") or 0)
            return credential
        if provider == "imap":
            allowed = {"username", "password"}
            unknown = set(credential) - allowed
            if unknown:
                raise ValueError(
                    f"unsupported IMAP credential field: {sorted(unknown)[0]}"
                )
            username = str(credential.get("username") or "")
            password = str(credential.get("password") or "")
            if not username or len(username) > 1024:
                raise ValueError("IMAP username is required")
            if not password or len(password) > 4096:
                raise ValueError("IMAP password is required")
            return {"username": username, "password": password}
        raise ValueError("email mailbox provider is not supported")


class MailboxSyncScheduler:
    """Periodically synchronize already-connected mailboxes."""

    def __init__(
        self,
        database: Database,
        *,
        interval_seconds: int = 60,
        service: MailboxConnectionService | None = None,
        oauth_applications: dict | None = None,
    ):
        self.service = service or MailboxConnectionService(
            database,
            oauth_applications=oauth_applications,
        )
        self.interval_seconds = max(30, min(int(interval_seconds), 3600))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="nowlert-email-mailboxes",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        self.service.sync_ready_mailboxes()
        while not self._stop.wait(self.interval_seconds):
            self.service.sync_ready_mailboxes()


def _encode_credential(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sync_limit(settings: dict) -> int:
    raw = settings.get("max_messages_per_sync", _DEFAULT_SYNC_LIMIT)
    if isinstance(raw, bool):
        raise ValueError("max_messages_per_sync must be an integer")
    value = int(raw)
    if not 1 <= value <= _MAX_SYNC_LIMIT:
        raise ValueError(
            f"max_messages_per_sync must be between 1 and {_MAX_SYNC_LIMIT}"
        )
    return value


def _signed_state(state_key: str, mailbox_id: str, expires_at: int) -> str:
    payload = json.dumps(
        {
            "mailbox_id": str(mailbox_id),
            "expires_at": int(expires_at),
            "nonce": token_secrets.token_urlsafe(18),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    signature = hmac.new(
        str(state_key).encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"


def _state_mailbox_id(state: str) -> str:
    encoded, separator, _signature = str(state or "").partition(".")
    if not separator or not encoded:
        raise PermissionError("OAuth state is invalid or expired")
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermissionError("OAuth state is invalid or expired") from error
    mailbox_id = (
        str(payload.get("mailbox_id") or "")
        if isinstance(payload, dict)
        else ""
    )
    if (
        len(mailbox_id) != 32
        or any(character not in "0123456789abcdef" for character in mailbox_id)
    ):
        raise PermissionError("OAuth state is invalid or expired")
    return mailbox_id


def _verify_state(
    state_key: str,
    mailbox_id: str,
    state: str,
    now: int,
) -> None:
    encoded, separator, signature = str(state or "").partition(".")
    if not separator or not encoded or not signature:
        raise PermissionError("OAuth state is invalid or expired")
    expected = hmac.new(
        str(state_key).encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise PermissionError("OAuth state is invalid or expired")
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermissionError("OAuth state is invalid or expired") from error
    if (
        not isinstance(payload, dict)
        or str(payload.get("mailbox_id") or "") != str(mailbox_id)
        or int(payload.get("expires_at") or 0) < int(now)
    ):
        raise PermissionError("OAuth state is invalid or expired")


def _safe_graph_cursor(value: str) -> str:
    cursor = str(value or "").strip()
    parsed = urlsplit(cursor)
    if (
        parsed.scheme.casefold() != "https"
        or parsed.hostname != "graph.microsoft.com"
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise MailboxConnectionError(
            "sync_cursor_invalid",
            "Microsoft 365 synchronization checkpoint is invalid",
        )
    return cursor


def _single_address(value: str) -> str:
    values = _addresses(value)
    return values[0] if values else ""


def _addresses(*values: str) -> tuple[str, ...]:
    result = []
    for _name, address in getaddresses([str(value or "") for value in values]):
        address = str(address or "").strip()
        if address and address not in result:
            result.append(address)
    return tuple(result)


def _header_timestamp(value: str, fallback: int) -> int:
    try:
        parsed = parsedate_to_datetime(str(value or ""))
        if parsed is None:
            return int(fallback)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        return int(fallback)


def _milliseconds_timestamp(value, fallback: int) -> int:
    try:
        return int(int(value) / 1000)
    except (TypeError, ValueError):
        return int(fallback)


def _iso_timestamp(value, fallback: int) -> int:
    text = str(value or "").strip()
    if not text:
        return int(fallback)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except (TypeError, ValueError, OverflowError):
        return int(fallback)


def _imap_cursor(value: str) -> dict:
    if not str(value or "").strip():
        return {}
    try:
        decoded = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def _imap_bytes(data) -> bytes | None:
    for item in data or []:
        if isinstance(item, tuple):
            for part in item:
                if isinstance(part, bytes) and b"\n" in part:
                    return part
        elif isinstance(item, bytes) and b"\n" in item:
            return item
    return None


__all__ = [
    "GMAIL_SCOPE",
    "MICROSOFT_SCOPE",
    "GmailMailboxProvider",
    "IMAPMailboxProvider",
    "MailboxConnectionError",
    "MailboxConnectionService",
    "MailboxProviderMessage",
    "MailboxSyncBatch",
    "MailboxSyncScheduler",
    "MailboxSyncSummary",
    "Microsoft365MailboxProvider",
    "OAuthStart",
]
