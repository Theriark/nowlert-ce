"""The Backups list keeps full snapshot verification across a restart."""

from __future__ import annotations

import json
import os
import time

import pytest

from storage.backups import StateBackupStore
from test_platform_portability import platform_state, seed_destination


def _without_full_verification(monkeypatch, backups):
    def no_rehash(_path):
        raise AssertionError("snapshot was hashed again")

    def no_integrity_check(_path, **_options):
        raise AssertionError("snapshot database was integrity-checked again")

    monkeypatch.setattr(backups, "_digest", no_rehash)
    monkeypatch.setattr(backups, "_validate_database", no_integrity_check)


def _tamper_keeping_size_and_mtime(path):
    details = path.stat()
    payload = bytearray(path.read_bytes())
    payload[-1] ^= 0xFF
    # Coarse file timestamps must move past the snapshot's own change time.
    time.sleep(0.05)
    path.write_bytes(bytes(payload))
    os.utime(path, ns=(details.st_atime_ns, details.st_mtime_ns))


def test_state_backup_list_after_a_restart_trusts_the_recorded_full_verification(
    platform_state,
    monkeypatch,
):
    state = platform_state
    seed_destination(state)
    first = StateBackupStore(state["database"], audit=state["audit"])
    older = first.create(state["admin"].actor)
    (first.backup_directory / ".verified.json").unlink(missing_ok=True)
    # A snapshot made before the record existed is verified once, then recorded.
    assert [item.id for item in StateBackupStore(state["database"]).list(
        state["admin"].actor,
    )] == [older.id]
    newer = first.create(state["admin"].actor)
    expected = [item.public() for item in first.list(state["admin"].actor)]
    assert [item["id"] for item in expected] == sorted([older.id, newer.id], reverse=True)

    restarted = StateBackupStore(state["database"], audit=state["audit"])
    _without_full_verification(monkeypatch, restarted)
    assert [item.public() for item in restarted.list(state["admin"].actor)] == expected


@pytest.mark.parametrize("record", ["missing", "corrupt", "schema", "changed", "symlink"])
def test_state_backup_list_verifies_in_full_without_a_trustworthy_record(
    platform_state,
    record,
):
    state = platform_state
    seed_destination(state)
    backups = StateBackupStore(state["database"])
    backup = backups.create(state["admin"].actor)
    record_path = backups.backup_directory / ".verified.json"
    stored = json.loads(record_path.read_text(encoding="utf-8"))
    if record == "missing":
        record_path.unlink()
    elif record == "corrupt":
        record_path.write_text(record_path.read_text()[:-10], encoding="utf-8")
    elif record == "schema":
        stored["schema"] = "unknown"
        record_path.write_text(json.dumps(stored), encoding="utf-8")
    elif record == "changed":
        stored["snapshots"][backup.id][0][2] += 1
        record_path.write_text(json.dumps(stored), encoding="utf-8")
    else:
        elsewhere = state["tmp_path"] / "elsewhere.json"
        record_path.rename(elsewhere)
        record_path.symlink_to(elsewhere)

    restarted = StateBackupStore(state["database"])
    hashed = []
    original_digest = restarted._digest
    restarted._digest = lambda path: hashed.append(path) or original_digest(path)
    assert [item.id for item in restarted.list(state["admin"].actor)] == [backup.id]
    assert hashed

    again = StateBackupStore(state["database"])
    again._digest = lambda _path: pytest.fail("rewritten record was not trusted")
    assert [item.id for item in again.list(state["admin"].actor)] == [backup.id]


def test_state_backup_tampered_snapshot_stays_hidden_after_a_restart(platform_state):
    state = platform_state
    seed_destination(state)
    backups = StateBackupStore(state["database"])
    kept = backups.create(state["admin"].actor)
    tampered = backups.create(state["admin"].actor)
    assert len(backups.list(state["admin"].actor)) == 2

    _tamper_keeping_size_and_mtime(backups.backup_directory / tampered.id / "nowlert.db")

    restarted = StateBackupStore(state["database"])
    assert [item.id for item in restarted.list(state["admin"].actor)] == [kept.id]
    assert [item.id for item in backups.list(state["admin"].actor)] == [kept.id]
    record = json.loads(
        (backups.backup_directory / ".verified.json").read_text(encoding="utf-8")
    )
    assert list(record["snapshots"]) == [kept.id]


def test_state_backup_full_checks_still_run_and_drop_a_trusted_snapshot_that_fails(
    platform_state,
):
    state = platform_state
    seed_destination(state)
    external_root = state["tmp_path"] / "external"
    external_root.mkdir(mode=0o700)
    backups = StateBackupStore(state["database"])
    backup = backups.create(state["admin"].actor)
    database = backups.backup_directory / backup.id / "nowlert.db"
    _tamper_keeping_size_and_mtime(database)
    # Simulate damage the file metadata cannot show (for example bit rot):
    # the record matches the damaged files, so listing still trusts them.
    record_path = backups.backup_directory / ".verified.json"
    stored = json.loads(record_path.read_text(encoding="utf-8"))
    stored["snapshots"][backup.id] = [
        list(entry) for entry in StateBackupStore._file_signature(database.parent)
    ]
    record_path.write_text(json.dumps(stored), encoding="utf-8")

    restarted = StateBackupStore(state["database"])
    assert [item.id for item in restarted.list(state["admin"].actor)] == [backup.id]
    with pytest.raises(RuntimeError, match="integrity"):
        restarted.mirror(state["admin"].actor, backup.id, external_root)
    with pytest.raises(RuntimeError, match="integrity"):
        restarted.restore(state["admin"].actor, backup.id, backup.id)
    with pytest.raises(RuntimeError, match="integrity"):
        restarted.delete(state["admin"].actor, backup.id)

    assert restarted.list(state["admin"].actor) == []
    assert StateBackupStore(state["database"]).list(state["admin"].actor) == []
    assert backup.id not in json.loads(record_path.read_text(encoding="utf-8"))["snapshots"]
