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


def test_production_image_uses_nowlert_icon_argument():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.count("ARG NOWLERT_TEAMS_ICON_BASE_URL=") == 1
    assert dockerfile.count("ENV NOWLERT_TEAMS_ICON_BASE_URL=") == 1


def test_release_workflow_supplies_nowlert_icon_argument():
    workflow = (
        ROOT / ".github" / "workflows" / "docker-release.yml"
    ).read_text(encoding="utf-8")

    assert workflow.count("NOWLERT_TEAMS_ICON_BASE_URL=") == 1


def test_internal_root_uses_nowlert():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    start_script = (ROOT / "start.sh").read_text(encoding="utf-8")

    assert "WORKDIR /nowlert" in dockerfile
    assert "COPY src /nowlert/src" in dockerfile
    assert 'CMD ["/nowlert/start.sh"]' in dockerfile

    assert 'sys.path.insert(0, "/nowlert/src")' in start_script
    assert "mkdir -p /nowlert/logs/emails" in start_script
    assert "cd /nowlert/src" in start_script


def test_development_image_has_nowlert_identity():
    dockerfile = (ROOT / "Dockerfile.dev").read_text(encoding="utf-8")

    assert 'org.opencontainers.image.title="Nowlert Development"' in dockerfile
    assert 'org.opencontainers.image.vendor="Theriark"' in dockerfile
    assert "WORKDIR /nowlert" in dockerfile
