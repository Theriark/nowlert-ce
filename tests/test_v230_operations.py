"""v2.3 WebUI operations and backup target contracts."""

from __future__ import annotations

from pathlib import Path

import os
import pytest

from api.security import hash_password
from models import Notification
from storage.backup_scheduler import BackupScheduler
from storage.backup_targets import BackupTargetStore, _remote_mounted
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult
from storage.destinations import DestinationStore
from storage.routes import RouteStore
from storage.users import UserStore
from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def __init__(self, data):
        self.data = data

    def get(self, *keys, default=None):
        value = self.data
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value


def fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x23" * 16, iterations=1_000)


@pytest.fixture
def platform_state(tmp_path):
    now = [1_800_000_000]
    database = Database(tmp_path / "state" / "nowlert.db")
    database.migrate()
    users = UserStore(
        database,
        clock=lambda: now[0],
        password_hasher=fast_hash,
    )
    admin = users.bootstrap_admin("administrator", "correct horse battery staple")
    user = users.create("observer", "observer secure password")
    return now, database, users, admin, user


@pytest.fixture
def mountinfo(tmp_path, monkeypatch):
    path = tmp_path / "mountinfo"
    path.write_text("")
    monkeypatch.setattr("storage.backup_targets._MOUNTINFO", path)
    return path


def test_local_backup_target_write_test_and_manual_run(platform_state, tmp_path):
    _now, database, _users, admin, _user = platform_state
    destination = tmp_path / "external"
    configuration = Configuration({"platform": {"backups": {}}})
    targets = BackupTargetStore(database, configuration)
    target = targets.create(
        admin.actor,
        {
            "name": "Local archive",
            "type": "local",
            "local_path": str(destination),
            "enabled": True,
        },
    )

    tested = targets.test(admin.actor, target.id)
    assert tested.last_test_outcome == "success"
    assert tested.public()["mounted"] is True
    assert not list(destination.glob(".nowlert-write-test-*"))

    scheduler = BackupScheduler(database, configuration)
    result = scheduler.run_now(admin.actor, target.id)
    assert result["outcome"] == "success"
    mirrored = Path(result["external_path"])
    assert (mirrored / "manifest.json").is_file()


def test_remote_backup_target_ignores_host_credentials(
    platform_state,
):
    _now, database, _users, admin, _user = platform_state
    configuration = Configuration({"platform": {"backups": {"managed_mounts": False}}})
    target = BackupTargetStore(database, configuration).create(
        admin.actor,
        {
            "name": "SMB archive",
            "type": "smb",
            "host": "nas.example.invalid",
            "share_name": "Backups",
            "remote_path": "Nowlert",
            "local_path": "/nowlert/mounts/smb",
            "username": "backup-service",
            "password": "server-side-only",
            "enabled": True,
        },
    )

    public = target.public()
    assert public["credentials_configured"] is False
    assert "password" not in public
    assert "server-side-only" not in str(public)
    store = BackupTargetStore(database, configuration)
    assert store._secret_id(target.id) is None
    assert store.update(admin.actor, target.id, {"password": "ignored"}).credentials_configured is False


def test_backup_target_conflict_does_not_rotate_secret(platform_state):
    _now, database, _users, admin, _user = platform_state
    targets = BackupTargetStore(database, Configuration({"platform": {}}))
    first = targets.create(
        admin.actor,
        {
            "name": "Primary SMB",
            "local_path": "/nowlert/mounts/primary",
            "type": "smb",
            "host": "nas.example.invalid",
            "share_name": "Backups",
            "username": "backup-service",
            "password": "original-secret",
        },
    )
    secret = targets.secrets.create(admin.actor, admin.id, "legacy-smb", "smb-password", "original-secret")
    with database.transaction() as connection:
        connection.execute("UPDATE backup_targets SET secret_id = ? WHERE id = ?", (secret.id, first.id))
    targets.create(
        admin.actor,
        {"name": "Duplicate name", "type": "local", "local_path": "/tmp/backups"},
    )

    with pytest.raises(ValueError, match="already configured"):
        targets.update(
            admin.actor,
            first.id,
            {"name": "Duplicate name", "password": "replacement-secret"},
        )

    secret_id = targets._secret_id(first.id)
    assert targets.secrets.resolve(admin.actor, secret_id) == b"original-secret"
    updated = targets.update(admin.actor, first.id, {"name": "Renamed SMB", "password": "ignored"})
    assert updated.id == first.id
    assert targets.secrets.resolve(admin.actor, secret_id) == b"original-secret"


def test_backup_target_protects_security_mount_options(platform_state):
    _now, database, _users, admin, _user = platform_state
    targets = BackupTargetStore(database, Configuration({"platform": {}}))
    with pytest.raises(ValueError, match="protected setting"):
        targets.create(
            admin.actor,
            {
                "name": "Unsafe NFS",
                "type": "nfs",
                "host": "nas.example.invalid",
                "remote_path": "/exports/nowlert",
                "mount_options": "exec",
            },
        )


def test_shared_destination_history_and_metrics_are_visible_to_users(
    platform_state,
):
    _now, database, _users, admin, user = platform_state
    destination = DestinationStore(database).create(
        admin.actor,
        admin.id,
        "Shared Discord",
        "discord",
        shared=True,
    )
    route = RouteStore(database).create(
        admin.actor,
        admin.id,
        "Shared operations",
        "home_assistant",
        destination.id,
    )
    history = DeliveryHistoryStore(database, clock=lambda: 1_800_000_100)
    history.record(
        admin.id,
        "shared-delivery",
        route,
        Notification(
            source="home_assistant",
            title="Helpers error",
            body="One helper could not be loaded.",
            status="error",
            metadata={"_input_type": "HTTP", "device": "Infrastructure"},
        ),
        1,
        "delivered",
        DeliveryResult(True, response_status=204),
    )

    assert history.list_visible(user.actor, limit=25)[0].input_type == "HTTP"
    assert history.metrics(user.actor, 1_800_000_000)["requests"] == 1


def test_https_redirect_and_v230_webui_contract():
    service = WebUIService(
        Configuration({
            "webui": {
                "public_url": "https://nowlert.example.test",
                "enforce_https": True,
            }
        }),
        root=ROOT,
    )
    assert service.redirect_location("/", {}) == "https://nowlert.example.test/"
    assert service.redirect_location("/ui", {}) == "https://nowlert.example.test/ui"
    assert service.redirect_location("/", {"X-Forwarded-Proto": "https"}) is None

    markup = (ROOT / "src" / "webui" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "src" / "webui" / "app.js").read_text(encoding="utf-8")
    assert "Welcome back" not in markup
    assert 'id="view-inputs"' in markup and 'id="view-backups"' in markup
    assert 'id="backup-target-dialog"' in markup
    assert 'id="restart-dialog"' in markup
    assert '<th>Order</th>' not in markup
    assert 'request("/notices")' not in script
    assert "renderNotices" not in script
    assert 'actionButton("Send test", "test-destination-card"' in script
    assert 'state.auditPageSize = Number' in script
    assert 'toDataURL("image/png")' in script
    assert "Send a real test delivery?" not in script
    assert 'toast("Preview generated.")' not in script


@pytest.mark.parametrize("target_type", ["nfs", "smb"])
@pytest.mark.parametrize("local_bind", [False, True])
def test_remote_backup_missing_mount_fails_closed(platform_state, tmp_path, monkeypatch, mountinfo, target_type, local_bind):
    _now, database, _users, admin, _user = platform_state
    targets = BackupTargetStore(database, Configuration({"platform": {"backups": {"managed_mounts": True}}}))
    mount = tmp_path / "missing-mount"
    target = targets.create(admin.actor, {
        "name": "Host NAS", "type": target_type, "local_path": str(mount),
    })
    mountinfo.write_text(f"30 20 0:50 / {mount} rw - ext4 /dev/sda rw\n")
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda _path: local_bind)
    assert targets.managed_mounts is False
    tested = targets.test(admin.actor, target.id)
    assert tested.last_test_outcome == "failed"
    assert "not mounted" in tested.last_error
    assert not mount.exists()
    with pytest.raises(RuntimeError, match="manual backup failed"):
        BackupScheduler(database, targets.configuration).run_now(admin.actor, target.id)
    assert not mount.exists()


def test_host_mount_write_test_status_and_delete(platform_state, tmp_path, monkeypatch, mountinfo):
    _now, database, _users, admin, _user = platform_state
    targets = BackupTargetStore(database)
    mount = tmp_path / "host-mount"
    mount.mkdir()
    target = targets.create(admin.actor, {
        "name": "Host SMB", "type": "smb", "local_path": str(mount), "remote_path": "archives/nowlert",
        "host": "nas.example.invalid", "share_name": "Legacy Backups",
    })
    device = mount.stat().st_dev
    mountinfo.write_text(f"30 20 {os.major(device)}:{os.minor(device)} / {mount} rw - cifs //nas/backups rw\n")
    target = targets.update(admin.actor, target.id, {"name": "Renamed host SMB"})
    assert (target.remote_path, target.host, target.share_name) == ("archives/nowlert", "nas.example.invalid", "Legacy Backups")
    mounted = [True]
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda path: mounted[0] and Path(path) == mount)
    tested = targets.test(admin.actor, target.id)
    assert tested.last_test_outcome == "success"
    assert tested.public()["mounted"] is True
    assert (mount / "archives" / "nowlert").is_dir()
    assert not list(mount.rglob(".nowlert-write-test-*"))
    mounted[0] = False
    assert tested.public()["mounted"] is False
    assert targets.test(admin.actor, target.id).public()["mounted"] is False
    mounted[0] = True
    targets.delete(admin.actor, target.id)
    assert mount.is_dir()


@pytest.mark.parametrize("path", ["../escape", "/absolute", "archives/../../escape", "bad\\escape", "bad\x00path"])
def test_smb_subdirectory_rejects_unsafe_paths(platform_state, path):
    _now, database, _users, admin, _user = platform_state
    with pytest.raises(ValueError, match="SMB backup path"):
        BackupTargetStore(database).create(admin.actor, {
            "name": "Unsafe SMB", "type": "smb", "local_path": "/nowlert/mounts/smb", "remote_path": path,
        })


def test_smb_subdirectory_rejects_symlink_escape(platform_state, tmp_path, monkeypatch, mountinfo):
    _now, database, _users, admin, _user = platform_state
    mount = tmp_path / "mounted"
    mount.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (mount / "escape").symlink_to(outside, target_is_directory=True)
    targets = BackupTargetStore(database)
    target = targets.create(admin.actor, {"name": "SMB", "type": "smb", "local_path": str(mount), "remote_path": "escape/backups"})
    device = mount.stat().st_dev
    mountinfo.write_text(f"30 20 {os.major(device)}:{os.minor(device)} / {mount} rw - cifs //nas/backups rw\n")
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda _path: True)
    with pytest.raises(ValueError, match="SMB backup path"):
        targets.ensure_ready(admin.actor, target)
    assert not (outside / "backups").exists()


@pytest.mark.parametrize("filesystem,target_type,expected", [
    ("nfs", "nfs", True), ("nfs4", "nfs", True), ("cifs", "smb", True),
    ("smb3", "smb", True), ("ext4", "nfs", False), ("overlay", "smb", False),
    ("cifs", "nfs", False), ("nfs4", "smb", False),
])
def test_remote_mount_requires_matching_nas_filesystem(tmp_path, monkeypatch, mountinfo, filesystem, target_type, expected):
    mount = tmp_path / "NAS backups"
    mount.mkdir()
    device = mount.stat().st_dev
    escaped = str(mount).replace(" ", r"\040")
    mountinfo.write_text(f"30 20 {os.major(device)}:{os.minor(device)} / {escaped} rw - {filesystem} nas:/export rw\n")
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda _path: True)
    assert _remote_mounted(mount, target_type) is expected
    assert _remote_mounted(tmp_path / "other", target_type) is False


@pytest.mark.parametrize("target_type,filesystem", [("nfs", "nfs4"), ("smb", "cifs")])
def test_local_overmount_cannot_use_hidden_nas_filesystem(tmp_path, monkeypatch, mountinfo, target_type, filesystem):
    mount = tmp_path / "NAS"
    mount.mkdir()
    device = mount.stat().st_dev
    local_device = f"{os.major(device)}:{os.minor(device)}"
    mountinfo.write_text(
        f"30 20 0:50 / {mount} rw - {filesystem} nas:/export rw\n"
        f"31 30 {local_device} / {mount} rw - ext4 /dev/sda rw\n"
    )
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda _path: True)
    assert _remote_mounted(mount, target_type) is False


def test_remote_mount_without_mountinfo_is_unavailable(tmp_path, monkeypatch, mountinfo):
    mountinfo.unlink()
    monkeypatch.setattr("storage.backup_targets.os.path.ismount", lambda _path: True)
    assert _remote_mounted(tmp_path / "NAS", "nfs") is False
