"""Named local, NFS, and SMB targets for scheduled state backups."""

from __future__ import annotations

import os
import re
import sqlite3
import time
import uuid

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable

from storage.database import Database
from storage.ownership import Actor
from storage.sanitize import sanitize_text
from storage.secrets import SecretStore
from storage.validation import normalized_name


_HOST = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
_SHARE = re.compile(r"^[^/\\\x00-\x1f]{1,80}$")
_MOUNT_OPTIONS = re.compile(r"^[A-Za-z0-9_.:=,-]{0,240}$")


_MOUNTINFO = Path("/proc/self/mountinfo")


def _remote_mounted(path: str | Path, target_type: str) -> bool:
    """A bind mount of a local host directory is not a NAS destination."""
    if not os.path.ismount(path):
        return False
    filesystems = {"nfs", "nfs4"} if target_type == "nfs" else {"cifs", "smb3"}
    try:
        resolved = Path(path).resolve()
        device = resolved.stat().st_dev
        device_id = f"{os.major(device)}:{os.minor(device)}"
        for line in _MOUNTINFO.read_text(encoding="utf-8").splitlines():
            mount, separator, filesystem = line.partition(" - ")
            fields = mount.split()
            if (separator and len(fields) >= 5 and fields[2] == device_id
                    and filesystem.split()[0] in filesystems):
                mountpoint = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
                if Path(mountpoint).resolve() == resolved:
                    return True
    except (OSError, ValueError, IndexError):
        pass
    return False


@dataclass(frozen=True)
class BackupTarget:
    id: str
    owner_user_id: str
    name: str
    target_type: str
    host: str
    remote_path: str
    share_name: str
    local_path: str
    username: str
    domain: str
    credentials_configured: bool
    mount_options: str
    enabled: bool
    mounted_at: int | None
    last_test_at: int | None
    last_test_outcome: str | None
    last_error: str | None
    created_at: int
    updated_at: int

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.target_type,
            "host": self.host,
            "remote_path": self.remote_path,
            "share_name": self.share_name,
            "local_path": self.local_path,
            "username": self.username,
            "domain": self.domain,
            "credentials_configured": self.credentials_configured,
            "mount_options": self.mount_options,
            "enabled": self.enabled,
            "mounted": (Path(self.local_path).is_dir() if self.target_type == "local"
                        else _remote_mounted(self.local_path, self.target_type)),
            "mounted_at": self.mounted_at,
            "last_test_at": self.last_test_at,
            "last_test_outcome": self.last_test_outcome,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BackupTargetStore:
    """Persist targets and test local or host-mounted backup storage."""

    def __init__(
        self,
        database: Database,
        configuration=None,
        *,
        secrets: SecretStore | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.database = database
        self.configuration = configuration
        self.secrets = secrets or SecretStore(database)
        self.clock = clock

    @property
    def managed_mounts(self) -> bool:
        return False

    def list(self, actor: Actor) -> list[BackupTarget]:
        self._require_admin(actor)
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM backup_targets ORDER BY name_normalized"
            ).fetchall()
        return [self._target(row) for row in rows]

    def get(self, actor: Actor, target_id: str) -> BackupTarget:
        self._require_admin(actor)
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM backup_targets WHERE id = ?", (str(target_id),)
            ).fetchone()
        if row is None:
            raise KeyError("backup target not found")
        return self._target(row)

    def create(self, actor: Actor, values: dict) -> BackupTarget:
        self._require_admin(actor)
        target_id = uuid.uuid4().hex
        spec = self._validated(values)
        now = int(self.clock())
        try:
            with self.database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO backup_targets(
                        id, owner_user_id, name, name_normalized, target_type,
                        host, remote_path, share_name, local_path, username,
                        domain, secret_id, mount_options, enabled, created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target_id,
                        actor.user_id,
                        spec["name"],
                        spec["normalized"],
                        spec["type"],
                        spec["host"],
                        spec["remote_path"],
                        spec["share_name"],
                        spec["local_path"],
                        spec["username"],
                        spec["domain"],
                        None,
                        spec["mount_options"],
                        1 if spec["enabled"] else 0,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("backup target name is already configured") from error
        return self.get(actor, target_id)

    def update(self, actor: Actor, target_id: str, values: dict) -> BackupTarget:
        current = self.get(actor, target_id)
        merged = {
            **current.public(),
            **values,
            "type": values.get("type", current.target_type),
        }
        spec = self._validated(merged)
        secret_id = self._secret_id(current.id)
        with self.database.connect() as connection:
            duplicate = connection.execute(
                "SELECT 1 FROM backup_targets WHERE name_normalized = ? AND id != ?",
                (spec["normalized"], current.id),
            ).fetchone()
        if duplicate is not None:
            raise ValueError("backup target name is already configured")
        retained_secret_id = secret_id if spec["type"] == "smb" else None
        now = int(self.clock())
        try:
            with self.database.transaction() as connection:
                connection.execute(
                """
                UPDATE backup_targets
                SET name = ?, name_normalized = ?, target_type = ?, host = ?,
                    remote_path = ?, share_name = ?, local_path = ?, username = ?,
                    domain = ?, secret_id = ?, mount_options = ?, enabled = ?,
                    mounted_at = NULL, last_test_outcome = NULL, last_error = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                    (
                        spec["name"], spec["normalized"], spec["type"], spec["host"],
                        spec["remote_path"], spec["share_name"], spec["local_path"],
                        spec["username"], spec["domain"], retained_secret_id,
                        spec["mount_options"], 1 if spec["enabled"] else 0,
                        now, current.id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("backup target name is already configured") from error
        if secret_id and retained_secret_id is None:
            self.secrets.delete(actor, secret_id)
        return self.get(actor, current.id)

    def delete(self, actor: Actor, target_id: str) -> None:
        current = self.get(actor, target_id)
        secret_id = self._secret_id(current.id)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM backup_targets WHERE id = ?", (current.id,))
        if secret_id:
            self.secrets.delete(actor, secret_id)

    def test(self, actor: Actor, target_id: str) -> BackupTarget:
        target = self.get(actor, target_id)
        now = int(self.clock())
        outcome = "success"
        error = None
        mounted_at = target.mounted_at
        try:
            path = self.ensure_ready(actor, target)
            probe = path / f".nowlert-write-test-{uuid.uuid4().hex}"
            descriptor = os.open(
                probe,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                os.write(descriptor, b"nowlert backup target write test\n")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
                probe.unlink(missing_ok=True)
            if target.target_type != "local":
                mounted_at = now
        except Exception as failure:
            outcome = "failed"
            mounted_at = None
            error = sanitize_text(failure)[:240] or "backup target test failed"
        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE backup_targets
                SET mounted_at = ?, last_test_at = ?, last_test_outcome = ?,
                    last_error = ?, updated_at = ? WHERE id = ?
                """,
                (mounted_at, now, outcome, error, now, target.id),
            )
        return self.get(actor, target.id)

    def ensure_ready(self, actor: Actor, target: BackupTarget | str) -> Path:
        item = self.get(actor, target) if isinstance(target, str) else target
        if not item.enabled:
            raise ValueError("backup target is disabled")
        local = Path(item.local_path)
        if item.target_type == "local":
            local.mkdir(parents=True, exist_ok=True, mode=0o700)
            return local
        if not _remote_mounted(local, item.target_type):
            raise RuntimeError("remote target is not mounted as a NAS filesystem; mount it on the Docker host and bind it into the container")
        destination = local
        if item.target_type == "smb" and item.remote_path:
            self._validate_smb_path(item.remote_path)
            destination = local / item.remote_path
            if not destination.resolve().is_relative_to(local.resolve()):
                raise ValueError("SMB backup path must remain inside the mounted share")
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        return destination

    @staticmethod
    def _validate_smb_path(path: str) -> None:
        if path.startswith("/") or ".." in PurePosixPath(path).parts or "\\" in path or any(ord(char) < 32 for char in path):
            raise ValueError("SMB backup path must be relative to the share")

    def _validated(self, values: dict) -> dict:
        if not isinstance(values, dict):
            raise ValueError("backup target must be an object")
        name, normalized = normalized_name(
            values.get("name"), "backup target name", maximum=120
        )
        target_type = str(values.get("type") or "").strip().casefold()
        if target_type not in {"local", "nfs", "smb"}:
            raise ValueError("backup target type must be Local, NFS, or SMB")
        host = str(values.get("host") or "").strip()
        remote_path = str(values.get("remote_path") or "").strip()
        share_name = str(values.get("share_name") or "").strip()
        username = sanitize_text(values.get("username") or "")[:120]
        domain = sanitize_text(values.get("domain") or "")[:120]
        options = str(values.get("mount_options") or "").strip()
        if not _MOUNT_OPTIONS.fullmatch(options):
            raise ValueError("mount options contain unsupported characters")
        option_keys = {
            part.split("=", 1)[0].casefold()
            for part in options.split(",")
            if part
        }
        if option_keys & {
            "credentials", "password", "username", "domain",
            "suid", "dev", "exec",
        }:
            raise ValueError("mount options contain a protected setting")
        if target_type != "local" and host and not _HOST.fullmatch(host):
            raise ValueError("backup target host is invalid")
        if target_type == "nfs" and remote_path and (
            not remote_path.startswith("/") or ".." in PurePosixPath(remote_path).parts
        ):
            raise ValueError("NFS export path must be an absolute safe path")
        if target_type == "smb" and share_name and not _SHARE.fullmatch(share_name):
            raise ValueError("SMB share name is invalid")
        if target_type == "smb":
            self._validate_smb_path(remote_path)
        local_path = str(values.get("local_path") or "").strip()
        if (not local_path.startswith("/") or local_path == "/"
                or (target_type != "local" and (
                    ".." in PurePosixPath(local_path).parts or "\\" in local_path
                    or any(ord(char) < 32 for char in local_path)))):
            raise ValueError("local backup path must be an absolute bounded directory")
        return {
            "name": name,
            "normalized": normalized,
            "type": target_type,
            "host": host if target_type != "local" else "",
            "remote_path": remote_path,
            "share_name": share_name if target_type == "smb" else "",
            "local_path": local_path,
            "username": username if target_type == "smb" else "",
            "domain": domain if target_type == "smb" else "",
            "mount_options": options,
            "enabled": values.get("enabled", True) is True,
        }

    def _secret_id(self, target_id: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT secret_id FROM backup_targets WHERE id = ?", (str(target_id),)
            ).fetchone()
        return str(row["secret_id"]) if row is not None and row["secret_id"] else None

    @staticmethod
    def _target(row) -> BackupTarget:
        return BackupTarget(
            id=str(row["id"]), owner_user_id=str(row["owner_user_id"]),
            name=str(row["name"]), target_type=str(row["target_type"]),
            host=str(row["host"]), remote_path=str(row["remote_path"]),
            share_name=str(row["share_name"]), local_path=str(row["local_path"]),
            username=str(row["username"]), domain=str(row["domain"]),
            credentials_configured=row["secret_id"] is not None,
            mount_options=str(row["mount_options"]), enabled=bool(row["enabled"]),
            mounted_at=int(row["mounted_at"]) if row["mounted_at"] is not None else None,
            last_test_at=int(row["last_test_at"]) if row["last_test_at"] is not None else None,
            last_test_outcome=str(row["last_test_outcome"]) if row["last_test_outcome"] else None,
            last_error=str(row["last_error"]) if row["last_error"] else None,
            created_at=int(row["created_at"]), updated_at=int(row["updated_at"]),
        )

    @staticmethod
    def _require_admin(actor: Actor) -> None:
        if not actor.is_admin:
            raise PermissionError("administrator access is required")
