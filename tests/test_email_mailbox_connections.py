"""Phase 6 Email Alerts mailbox-connection regressions."""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from api.platform import PlatformAPI
from email_alert_pipeline import email_message_text
from inputs.email_mailboxes import (
    MailboxConnectionService,
    MailboxSyncScheduler,
    email_oauth_applications,
)
from storage.database import Database
from storage.ownership import Actor


class Response:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.content = content

    def json(self):
        return self._payload


class GmailHTTP:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        data = kwargs.get("data") or {}
        if data.get("grant_type") == "authorization_code":
            return Response(
                payload={
                    "access_token": "gmail-access",
                    "refresh_token": "gmail-refresh",
                    "expires_in": 3600,
                }
            )
        return Response(
            payload={"access_token": "gmail-refreshed", "expires_in": 3600}
        )

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        if url.endswith("/messages"):
            return Response(payload={"messages": [{"id": "gmail-message-1"}]})
        if url.endswith("/messages/gmail-message-1"):
            return Response(
                payload={
                    "id": "gmail-message-1",
                    "threadId": "gmail-thread-1",
                    "historyId": "99",
                    "internalDate": "1790181000000",
                    "labelIds": ["INBOX", "IMPORTANT"],
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<gmail-message@example.invalid>",
                            },
                            {
                                "name": "From",
                                "value": "Monitor <monitor@example.invalid>",
                            },
                            {
                                "name": "To",
                                "value": "alerts@example.com",
                            },
                            {
                                "name": "Subject",
                                "value": "Database warning",
                            },
                        ]
                    },
                }
            )
        if url.endswith("/profile"):
            return Response(payload={"historyId": "100"})
        if url.endswith("/history"):
            return Response(payload={"history": []})
        raise AssertionError(url)


class GmailRawHTTP(GmailHTTP):
    def get(self, url, **kwargs):
        params = kwargs.get("params")
        if url.endswith("/messages/gmail-message-1") and params == {"format": "raw"}:
            encoded = base64.urlsafe_b64encode(
                b"From: monitor@example.invalid\n\nprivate body"
            ).decode("ascii").rstrip("=")
            return Response(payload={"raw": encoded})
        return super().get(url, **kwargs)


class MicrosoftHTTP:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return Response(
            payload={
                "access_token": "graph-access",
                "refresh_token": "graph-refresh",
                "expires_in": 3600,
            }
        )

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        if "/messages/delta" in url:
            return Response(
                payload={
                    "value": [
                        {
                            "id": "graph-message-1",
                            "internetMessageId": "<graph@example.invalid>",
                            "receivedDateTime": "2026-09-23T15:30:00Z",
                            "subject": "Microsoft alert",
                            "from": {
                                "emailAddress": {
                                    "address": "monitor@example.invalid"
                                }
                            },
                            "toRecipients": [
                                {
                                    "emailAddress": {
                                        "address": "alerts@example.com"
                                    }
                                }
                            ],
                            "ccRecipients": [],
                            "parentFolderId": "folder-1",
                            "categories": ["Operations"],
                            "webLink": (
                                "https://outlook.office.com/mail/deeplink/read/"
                                "graph-message-1"
                            ),
                        }
                    ],
                    "@odata.deltaLink": (
                        "https://graph.microsoft.com/v1.0/me/mailFolders/"
                        "inbox/messages/delta?$deltatoken=opaque"
                    ),
                }
            )
        raise AssertionError(url)


class FakeIMAP:
    def __init__(self, _host, _port, timeout=None):
        self.timeout = timeout
        self.logged_in = False

    def login(self, username, password):
        assert username == "alerts@example.com"
        assert password == "private-password"
        self.logged_in = True
        return "OK", [b"logged in"]

    def select(self, folder, readonly=True):
        assert self.logged_in is True
        assert folder == "INBOX"
        assert readonly is True
        return "OK", [b"2"]

    def response(self, name):
        assert name == "UIDVALIDITY"
        return "UIDVALIDITY", [b"777"]

    def uid(self, command, *args):
        command = command.casefold()
        if command == "search":
            return "OK", [b"41 42"]
        if command == "fetch":
            uid = str(args[0])
            if uid == "41":
                body = (
                    b"Message-ID: <imap-41@example.invalid>\r\n"
                    b"From: monitor@example.invalid\r\n"
                    b"To: alerts@example.com\r\n"
                    b"Subject: First IMAP alert\r\n"
                    b"Date: Wed, 23 Sep 2026 15:20:00 +0000\r\n\r\n"
                )
            else:
                body = (
                    b"Message-ID: <imap-42@example.invalid>\r\n"
                    b"From: monitor@example.invalid\r\n"
                    b"To: alerts@example.com\r\n"
                    b"Subject: Second IMAP alert\r\n"
                    b"Date: Wed, 23 Sep 2026 15:21:00 +0000\r\n\r\n"
                )
            return "OK", [(b"metadata", body)]
        raise AssertionError((command, args))

    def close(self):
        return "OK", []

    def logout(self):
        return "BYE", []


def user(database, identifier="u" * 32):
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users(
                id, username, username_normalized, password_hash,
                role, enabled, created_at, updated_at
            ) VALUES (?, 'owner', 'owner', 'hash', 'user', 1, 1, 1)
            """,
            (identifier,),
        )
    return Actor(identifier, "user")


def test_gmail_oauth_and_incremental_metadata_sync(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    http = GmailHTTP()
    service = MailboxConnectionService(
        database,
        http=http,
        clock=lambda: now,
    )
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "gmail",
        "alerts@example.com",
        name="Gmail alerts",
        credential={
            "client_id": "gmail-client",
            "client_secret": "gmail-secret",
            "redirect_uri": "https://ce-dev-nowlert.theriark.dev/oauth/gmail",
        },
    )

    oauth = service.oauth_start(actor, mailbox.id)
    query = parse_qs(urlsplit(oauth.authorization_url).query)
    assert query["scope"] == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]
    assert query["access_type"] == ["offline"]
    state = query["state"][0]

    mailbox = service.oauth_complete(
        actor,
        mailbox.id,
        code="authorization-code",
        state=state,
    )
    assert mailbox.connection_state == "healthy"

    summary = service.sync_mailbox(actor, mailbox.id)
    assert summary.observed == 1
    assert summary.created == 1
    mailbox = service.store.get_mailbox(actor, mailbox.id)
    assert mailbox.sync_cursor == "100"
    assert mailbox.last_sync_at == now
    assert mailbox.last_error_code == ""

    with database.connect() as connection:
        message = connection.execute(
            "SELECT * FROM email_messages"
        ).fetchone()
        contents = connection.execute(
            "SELECT COUNT(*) FROM email_message_contents"
        ).fetchone()[0]
    assert message["provider_message_id"] == "gmail-message-1"
    assert message["internet_message_id"] == "<gmail-message@example.invalid>"
    assert message["subject"] == "Database warning"
    assert message["provider_deep_link"].startswith(
        "https://mail.google.com/mail/u/?"
    )
    assert contents == 0

    second = service.sync_mailbox(actor, mailbox.id)
    assert second.observed == 0
    assert second.created == 0
    assert any("/history" in call[1] for call in http.calls)


def test_gmail_raw_content_is_retrieved_only_on_demand(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(
        database,
        http=GmailRawHTTP(),
        clock=lambda: now,
    )
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "gmail",
        "alerts@example.com",
        credential={
            "client_id": "client",
            "client_secret": "secret",
            "redirect_uri": "https://example.invalid/oauth",
            "access_token": "existing",
            "refresh_token": "refresh",
            "expires_at": now + 3600,
        },
    )
    service.store.update_mailbox_connection(
        actor,
        mailbox.id,
        connection_state="healthy",
    )
    service.sync_mailbox(actor, mailbox.id)
    with database.connect() as connection:
        message_id = connection.execute(
            "SELECT id FROM email_messages"
        ).fetchone()[0]
        assert connection.execute(
            "SELECT COUNT(*) FROM email_message_contents"
        ).fetchone()[0] == 0

    stored = service.fetch_raw_content(actor, message_id)
    retained = service.store.read_raw_content(actor, message_id)
    assert stored["size_bytes"] > 0
    assert email_message_text(retained) == "private body"
    assert b"X-Nowlert-Retained-Content: sanitized-body-only" in retained


def test_microsoft_365_delta_sync_uses_provider_web_link(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(
        database,
        http=MicrosoftHTTP(),
        clock=lambda: now,
    )
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "microsoft_365",
        "alerts@example.com",
        name="Microsoft 365",
        settings={"tenant": "organizations", "folder": "inbox"},
        credential={
            "client_id": "graph-client",
            "client_secret": "graph-secret",
            "redirect_uri": "https://example.invalid/oauth/microsoft",
            "access_token": "graph-access",
            "refresh_token": "graph-refresh",
            "expires_at": now + 3600,
        },
    )
    service.store.update_mailbox_connection(
        actor,
        mailbox.id,
        connection_state="healthy",
    )

    summary = service.sync_mailbox(actor, mailbox.id)

    assert summary.created == 1
    mailbox = service.store.get_mailbox(actor, mailbox.id)
    assert mailbox.sync_cursor.startswith(
        "https://graph.microsoft.com/v1.0/"
    )
    with database.connect() as connection:
        row = connection.execute(
            "SELECT provider_deep_link, subject FROM email_messages"
        ).fetchone()
    assert row["subject"] == "Microsoft alert"
    assert row["provider_deep_link"].startswith(
        "https://outlook.office.com/"
    )


def test_imaps_metadata_sync_uses_uid_checkpoint_and_message_id_dedup(tmp_path):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(
        database,
        imap_ssl_factory=FakeIMAP,
        clock=lambda: now,
    )
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="IMAPS",
        settings={
            "host": "imap.example.invalid",
            "port": 993,
            "security": "ssl",
            "folder": "INBOX",
        },
        credential={
            "username": "alerts@example.com",
            "password": "private-password",
        },
    )

    summary = service.sync_mailbox(actor, mailbox.id)

    assert summary.observed == 2
    assert summary.created == 2
    mailbox = service.store.get_mailbox(actor, mailbox.id)
    assert '"uidvalidity":"777"' in mailbox.sync_cursor
    assert '"last_uid":42' in mailbox.sync_cursor
    assert mailbox.connection_state == "healthy"
    with database.connect() as connection:
        rows = connection.execute(
            """
            SELECT provider_message_id, internet_message_id, metadata_json
            FROM email_messages
            ORDER BY subject
            """
        ).fetchall()
    assert [row["provider_message_id"] for row in rows] == ["", ""]
    assert [row["internet_message_id"] for row in rows] == [
        "<imap-41@example.invalid>",
        "<imap-42@example.invalid>",
    ]
    assert all("imap_uid" in row["metadata_json"] for row in rows)


def test_invalid_oauth_state_is_rejected_without_exposing_credentials(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(database, http=GmailHTTP())
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "gmail",
        "alerts@example.com",
        credential={
            "client_id": "client",
            "client_secret": "private-client-secret",
            "redirect_uri": "https://example.invalid/oauth",
        },
    )

    with pytest.raises(PermissionError, match="state"):
        service.oauth_complete(
            actor,
            mailbox.id,
            code="code",
            state="invalid",
        )

    public = PlatformAPI._email_mailbox(
        service.store.get_mailbox(actor, mailbox.id)
    )
    assert "sync_cursor" not in public
    assert "credential" not in public
    assert "secret_id" not in public
    assert public["secret_configured"] is True



def test_platform_managed_gmail_oauth_keeps_application_secret_out_of_mailbox_secret(
    tmp_path,
):
    now = 2_000_000_000
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    http = GmailHTTP()
    service = MailboxConnectionService(
        database,
        http=http,
        clock=lambda: now,
        oauth_applications={
            "gmail": {
                "client_id": "instance-gmail-client",
                "client_secret": "instance-gmail-secret",
                "redirect_uri": "https://nowlert.example.com/ui/",
            },
            "microsoft_365": {},
        },
    )

    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "gmail",
        "alerts@example.com",
        name="Operations Gmail",
    )

    secret_id = service.store.mailbox_secret_id(actor, mailbox.id)
    stored = json.loads(service.secrets.resolve(actor, secret_id).decode("utf-8"))
    assert len(stored["state_key"]) >= 32
    assert "client_id" not in stored
    assert "client_secret" not in stored
    assert "redirect_uri" not in stored

    oauth = service.oauth_start(actor, mailbox.id)
    query = parse_qs(urlsplit(oauth.authorization_url).query)
    assert query["client_id"] == ["instance-gmail-client"]
    assert query["redirect_uri"] == ["https://nowlert.example.com/ui/"]

    state = query["state"][0]
    service.oauth_complete(
        actor,
        mailbox.id,
        code="authorization-code",
        state=state,
    )

    stored = json.loads(service.secrets.resolve(actor, secret_id).decode("utf-8"))
    assert stored["access_token"] == "gmail-access"
    assert stored["refresh_token"] == "gmail-refresh"
    assert "client_id" not in stored
    assert "client_secret" not in stored
    assert "redirect_uri" not in stored


def test_mailbox_provider_status_exposes_configuration_without_oauth_secrets(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    service = MailboxConnectionService(
        database,
        oauth_applications={
            "gmail": {
                "client_id": "configured",
                "client_secret": "private-secret",
                "redirect_uri": "https://nowlert.example.com/ui/",
            },
            "microsoft_365": {},
        },
    )

    status = service.provider_status()

    assert status == {
        "imap": {
            "label": "IMAP / IMAPS",
            "configured": True,
            "authentication": "credentials",
        },
        "gmail": {
            "label": "Gmail",
            "configured": True,
            "authentication": "oauth",
        },
        "microsoft_365": {
            "label": "Microsoft 365",
            "configured": False,
            "authentication": "oauth",
        },
    }
    assert "private-secret" not in json.dumps(status)



def test_oauth_applications_read_instance_secret_files(tmp_path):
    gmail_secret = tmp_path / "gmail-client-secret"
    microsoft_secret = tmp_path / "microsoft-client-secret"
    gmail_secret.write_text("gmail-private\n", encoding="utf-8")
    microsoft_secret.write_text("microsoft-private\n", encoding="utf-8")

    applications = email_oauth_applications(
        environment={
            "NOWLERT_EMAIL_GMAIL_CLIENT_ID": "gmail-client-id",
            "NOWLERT_EMAIL_GMAIL_CLIENT_SECRET_FILE": str(gmail_secret),
            "NOWLERT_EMAIL_GMAIL_REDIRECT_URI": "https://nowlert.example/ui/",
            "NOWLERT_EMAIL_MICROSOFT_CLIENT_ID": "microsoft-client-id",
            "NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET_FILE": str(
                microsoft_secret
            ),
            "NOWLERT_EMAIL_MICROSOFT_REDIRECT_URI": "https://nowlert.example/ui/",
        }
    )

    assert applications["gmail"] == {
        "client_id": "gmail-client-id",
        "client_secret": "gmail-private",
        "redirect_uri": "https://nowlert.example/ui/",
    }
    assert applications["microsoft_365"] == {
        "client_id": "microsoft-client-id",
        "client_secret": "microsoft-private",
        "redirect_uri": "https://nowlert.example/ui/",
    }


def test_microsoft_oauth_uses_instance_tenant_id(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(
        database,
        oauth_applications={
            "gmail": {},
            "microsoft_365": {
                "client_id": "client",
                "client_secret": "secret",
                "redirect_uri": "https://nowlert.example/ui/",
                "tenant_id": "152cc14d-5969-4329-a9a0-c1ddb5e3232b",
            },
        },
    )
    mailbox = service.create_mailbox(
        actor, actor.user_id, "microsoft_365", "qa@theriark.com",
        name="QA", settings={"folder": "inbox"},
    )
    start = service.oauth_start(actor, mailbox.id)
    assert "login.microsoftonline.com/152cc14d-5969-4329-a9a0-c1ddb5e3232b/oauth2/v2.0/authorize" in start.authorization_url

def test_mailbox_sync_scheduler_runs_immediately_on_fast_background_thread():
    class RecordingService:
        def __init__(self):
            self.calls = 0
            self.called = __import__("threading").Event()

        def sync_ready_mailboxes(self):
            self.calls += 1
            self.called.set()
            return []

    service = RecordingService()
    scheduler = MailboxSyncScheduler(object(), service=service)

    assert scheduler.interval_seconds == 5

    scheduler.start()
    try:
        assert service.called.wait(1)
        assert service.calls == 1
        assert scheduler._thread is not None
        assert scheduler._thread.daemon is True
        assert scheduler._thread.name == "nowlert-email-mailboxes"
    finally:
        scheduler.stop()


def test_mailbox_sync_scheduler_clamps_interval_to_safe_bounds():
    service = type("Service", (), {"sync_ready_mailboxes": lambda self: []})()

    assert (
        MailboxSyncScheduler(
            object(),
            interval_seconds=1,
            service=service,
        ).interval_seconds
        == 5
    )
    assert (
        MailboxSyncScheduler(
            object(),
            interval_seconds=7200,
            service=service,
        ).interval_seconds
        == 3600
    )

