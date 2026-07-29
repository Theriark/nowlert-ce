"""Nowlert container-image identity and compatibility regressions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_image_has_nowlert_oci_identity():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'org.opencontainers.image.title="Nowlert"' in dockerfile
    assert 'org.opencontainers.image.vendor="Theriark"' in dockerfile
    assert (
        'org.opencontainers.image.description="Infrastructure Notification Engine"'
        in dockerfile
    )


def test_production_image_accepts_new_and_legacy_icon_arguments():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ARG NOWLERT_TEAMS_ICON_BASE_URL=" in dockerfile
    assert "ARG NOTIFINHO_TEAMS_ICON_BASE_URL=" in dockerfile
    assert "ENV NOWLERT_TEAMS_ICON_BASE_URL=" in dockerfile
    assert "ENV NOTIFINHO_TEAMS_ICON_BASE_URL=" in dockerfile


def test_release_workflow_supplies_both_icon_argument_names():
    workflow = (
        ROOT / ".github" / "workflows" / "docker-release.yml"
    ).read_text(encoding="utf-8")

    assert "NOWLERT_TEAMS_ICON_BASE_URL=" in workflow
    assert "NOTIFINHO_TEAMS_ICON_BASE_URL=" in workflow


def test_internal_root_remains_upgrade_compatible():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    start_script = (ROOT / "start.sh").read_text(encoding="utf-8")

    assert "WORKDIR /notifinho" in dockerfile
    assert "COPY src /notifinho/src" in dockerfile
    assert 'CMD ["/notifinho/start.sh"]' in dockerfile

    assert 'sys.path.insert(0, "/notifinho/src")' in start_script
    assert "mkdir -p /notifinho/logs/emails" in start_script
    assert "cd /notifinho/src" in start_script


def test_development_image_has_nowlert_identity():
    dockerfile = (ROOT / "Dockerfile.dev").read_text(encoding="utf-8")

    assert 'org.opencontainers.image.title="Nowlert Development"' in dockerfile
    assert 'org.opencontainers.image.vendor="Theriark"' in dockerfile
    assert "WORKDIR /notifinho" in dockerfile
