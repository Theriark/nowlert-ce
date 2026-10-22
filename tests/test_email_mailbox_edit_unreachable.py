"""IMAP mailbox edits must not depend on the IMAP server being reachable."""

from __future__ import annotations

import json

import pytest

from inputs.email_mailboxes import MailboxConnectionError, MailboxConnectionService
from storage.database import Database

from test_email_mailbox_connections import EditableIMAP, user


def _unreachable(*args, **kwargs):
    raise OSError("server unreachable")


def _service_with_mailbox(tmp_path):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    actor = user(database)
    service = MailboxConnectionService(database, imap_ssl_factory=EditableIMAP)
    mailbox = service.create_mailbox(
        actor,
        actor.user_id,
        "imap",
        "alerts@example.com",
        name="IMAP alerts",
        settings={"host": "imap.example.invalid", "port": 993, "security": "ssl"},
        credential={"username": "edited@example.com", "password": "new-password"},
    )
    service.imap.imap_ssl_factory = _unreachable
    return service, actor, mailbox


def test_name_and_visibility_edit_saves_when_server_is_unreachable(tmp_path):
    service, actor, mailbox = _service_with_mailbox(tmp_path)

    updated = service.update_mailbox(actor, mailbox.id, name="Renamed IMAP", shared=True)

    assert updated.name == "Renamed IMAP"
    assert updated.shared is True
    assert updated.settings["host"] == "imap.example.invalid"


def test_changed_host_or_password_is_still_verified_before_saving(tmp_path):
    service, actor, mailbox = _service_with_mailbox(tmp_path)

    with pytest.raises(MailboxConnectionError):
        service.update_mailbox(
            actor,
            mailbox.id,
            settings={
                "host": "other.example.invalid",
                "port": 993,
                "security": "ssl",
                "folder": "INBOX",
            },
        )
    assert (
        service.store.get_mailbox(actor, mailbox.id).settings["host"]
        == "imap.example.invalid"
    )

    with pytest.raises(MailboxConnectionError):
        service.update_mailbox(
            actor,
            mailbox.id,
            credential={"username": "edited@example.com", "password": "other"},
        )
    secret_id = service.store.mailbox_secret_id(actor, mailbox.id)
    secret = json.loads(service.secrets.resolve(actor, secret_id).decode("utf-8"))
    assert secret["password"] == "new-password"
