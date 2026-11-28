"""The legacy YAML token list marks what the one-way migration cannot import."""

from __future__ import annotations

import os
from types import SimpleNamespace

from storage.configuration_sync import UnifiedConfigurationService
from storage.database import Database


def listing(tmp_path, tokens):
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    configuration = SimpleNamespace(get=lambda *_keys, default=None: tokens)
    fake = SimpleNamespace(
        synchronize=lambda: None,
        database_authoritative=False,
        config_service=SimpleNamespace(configuration=configuration),
        database=database,
    )
    return {item["name"]: item for item in UnifiedConfigurationService.legacy_applications(fake)}


def test_listing_follows_the_migration_credential_rules(tmp_path, monkeypatch):
    private = tmp_path / "private-token"
    private.write_text("private-value\n", encoding="utf-8")
    os.chmod(private, 0o600)
    shared = tmp_path / "shared-token"
    shared.write_text("shared-value\n", encoding="utf-8")
    os.chmod(shared, 0o644)
    monkeypatch.delenv("NOWLERT_TEST_UNSET_TOKEN", raising=False)

    items = listing(tmp_path, {
        "private-file": {"token_file": str(private)},
        "readable-by-others": {"token_file": str(shared)},
        "env-named-but-unset": {"token_env": "NOWLERT_TEST_UNSET_TOKEN", "token_file": str(private)},
        "bad-digest": {"token_sha256": "not-a-digest"},
        "good-digest": {"token_sha256": "a" * 64},
    })

    assert items["private-file"]["credential_available"] is True
    # The migration ignores a file other accounts can read...
    assert items["readable-by-others"]["credential_available"] is False
    # ...never falls back to the file when an environment variable is named...
    assert items["env-named-but-unset"]["credential_available"] is False
    assert items["env-named-but-unset"]["credential_source"] == "environment"
    # ...and accepts only a 64-character hexadecimal digest.
    assert items["bad-digest"]["credential_available"] is False
    assert items["good-digest"]["credential_available"] is True
    assert items["good-digest"]["credential_source"] == "SHA-256"
