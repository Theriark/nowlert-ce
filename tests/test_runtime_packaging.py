"""Container and process-lifecycle deployment invariants."""

import os
from pathlib import Path
import stat
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_production_image_uses_immutable_python_base_and_pinned_dependencies():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "FROM python:3.13.14-slim-bookworm@sha256:" in dockerfile
    for line in requirements.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            assert "==" in stripped


def test_start_script_execs_python_as_the_container_process():
    script = (ROOT / "start.sh").read_text(encoding="utf-8")

    assert "/nowlert/bootstrap-config.sh" in script
    assert "exec python3 main.py" in script


def test_empty_config_volume_is_initialized_once(tmp_path):
    config_dir = tmp_path / "config"
    template = tmp_path / "config.example.yaml"
    template.write_text("http:\n  enabled: true\n", encoding="utf-8")

    subprocess.run(
        [
            "sh",
            str(ROOT / "bootstrap-config.sh"),
            str(config_dir),
            str(template),
        ],
        check=True,
    )

    config_file = config_dir / "config.yaml"
    assert config_file.read_text(encoding="utf-8") == template.read_text(
        encoding="utf-8"
    )
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600

    config_file.write_text("custom: true\n", encoding="utf-8")
    os.chmod(config_file, 0o640)

    subprocess.run(
        [
            "sh",
            str(ROOT / "bootstrap-config.sh"),
            str(config_dir),
            str(template),
        ],
        check=True,
    )

    assert config_file.read_text(encoding="utf-8") == "custom: true\n"
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o640


def test_production_image_packages_bootstrap_configuration():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert (
        "COPY config/config.example.yaml "
        "/usr/local/share/nowlert/config.example.yaml"
    ) in dockerfile
    assert "COPY bootstrap-config.sh /nowlert/bootstrap-config.sh" in dockerfile
    assert (
        "chmod +x /nowlert/bootstrap-config.sh /nowlert/start.sh"
    ) in dockerfile


def test_production_compose_applies_runtime_hardening():
    compose = yaml.safe_load(
        (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    )
    assert compose["name"] == "nowlert"
    service = compose["services"]["nowlert"]

    assert service["container_name"] == "nowlert"
    assert service["read_only"] is True
    assert service["init"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert service["user"] == (
        "${NOWLERT_UID:-1000}:"
        "${NOWLERT_GID:-1000}"
    )
    assert (
        "${NOWLERT_STATE_DIR:-./state}:"
        "/nowlert/state"
    ) in service["volumes"]
    assert service["environment"]["NOWLERT_STATE_DIR"] == "/nowlert/state"


def test_public_configuration_enables_secure_webui_bootstrap_defaults():
    configuration = yaml.safe_load(
        (ROOT / "config" / "config.example.yaml").read_text(encoding="utf-8")
    )

    assert configuration["http"]["enabled"] is True
    assert configuration["api"]["enabled"] is True
    assert configuration["platform"]["enabled"] is True
    assert configuration["platform"]["secure_cookies"] is False
    assert configuration["webui"]["enforce_https"] is False
    assert configuration["platform"]["state_dir"] == "/nowlert/state"
    assert configuration["webui"]["enabled"] is True


def test_ci_validates_webui_compose_and_production_image():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "actions/setup-node@v7" in workflow
    assert 'node-version: "24"' in workflow
    assert "package-manager-cache: false" in workflow
    assert "node --check src/webui/app.js" in workflow
    assert "docker compose -f compose.production.yaml config" in workflow
    assert "docker build --tag nowlert:ci ." in workflow
