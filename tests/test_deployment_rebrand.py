"""Nowlert deployment identity and legacy deployment compatibility."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_production_compose_uses_nowlert_identity():
    compose = yaml.safe_load(
        (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    )

    assert compose["name"] == "nowlert"
    assert "notifinho" not in compose["services"]
    assert "nowlert" in compose["services"]

    service = compose["services"]["nowlert"]

    assert service["container_name"] == "nowlert"
    assert service["image"] == (
        "${NOWLERT_IMAGE:-${NOTIFINHO_IMAGE:-theriark/nowlert:3.0.0}}"
    )


def test_production_compose_accepts_new_and_legacy_host_variables():
    document = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

    pairs = (
        ("NOWLERT_IMAGE", "NOTIFINHO_IMAGE"),
        ("NOWLERT_UID", "NOTIFINHO_UID"),
        ("NOWLERT_GID", "NOTIFINHO_GID"),
        ("NOWLERT_SMTP_PORT", "NOTIFINHO_SMTP_PORT"),
        ("NOWLERT_HTTP_PORT", "NOTIFINHO_HTTP_PORT"),
        ("NOWLERT_CONFIG_DIR", "NOTIFINHO_CONFIG_DIR"),
        ("NOWLERT_LOG_DIR", "NOTIFINHO_LOG_DIR"),
        ("NOWLERT_SECRETS_DIR", "NOTIFINHO_SECRETS_DIR"),
        ("NOWLERT_STATE_DIR", "NOTIFINHO_STATE_DIR"),
        ("NOWLERT_EXTERNAL_BACKUP_DIR", "NOTIFINHO_EXTERNAL_BACKUP_DIR"),
        ("NOWLERT_SMTP_PASSWORD", "NOTIFINHO_SMTP_PASSWORD"),
        ("NOWLERT_ADMIN_TOKEN", "NOTIFINHO_ADMIN_TOKEN"),
        ("NOWLERT_HARDWARE_TOKEN", "NOTIFINHO_HARDWARE_TOKEN"),
        ("NOWLERT_AVAILABLE_VERSION", "NOTIFINHO_AVAILABLE_VERSION"),
    )

    for primary, legacy in pairs:
        assert primary in document
        assert legacy in document


def test_new_environment_example_uses_nowlert_namespace():
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")

    assignments = [
        line
        for line in environment.splitlines()
        if line and not line.startswith("#") and "=" in line
    ]

    nowlert_assignments = [
        line for line in assignments if line.startswith("NOWLERT_")
    ]
    legacy_assignments = [
        line for line in assignments if line.startswith("NOTIFINHO_")
    ]

    assert nowlert_assignments
    assert not legacy_assignments


def test_internal_container_paths_remain_upgrade_compatible():
    compose = yaml.safe_load(
        (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    )
    service = compose["services"]["nowlert"]

    assert service["environment"]["NOWLERT_STATE_DIR"] == "/notifinho/state"
    assert service["environment"]["NOTIFINHO_STATE_DIR"] == "/notifinho/state"

    targets = {
        volume.rsplit(":", 1)[-1]
        for volume in service["volumes"]
    }

    assert "/notifinho/config" in targets
    assert "/notifinho/logs" in targets
    assert "/notifinho/state" in targets
    assert "/notifinho/external-backups" in targets


def test_development_compose_uses_nowlert_identity():
    compose = yaml.safe_load(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    )
    service = compose["services"]["nowlert-dev"]

    assert service["image"] == "nowlert-dev:local"
    assert service["container_name"] == "nowlert-dev"
    assert service["working_dir"] == "/notifinho"
    assert service["command"] == "/notifinho/start.sh"
