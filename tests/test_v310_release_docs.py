"""Preserve the shipped v3.1.0 release documentation as historical evidence."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v310_release_documentation_and_screenshots_remain_packaged():
    release = (ROOT / "docs" / "releases" / "v3.1.0.md").read_text(
        encoding="utf-8"
    )
    checklist = (ROOT / "docs" / "v3.1.0-qa-checklist.md").read_text(
        encoding="utf-8"
    )
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert release.startswith("# Nowlert v3.1.0 release notes")
    assert "NCE-20" in release
    assert "1023 passed" in release
    assert "NCE-5 through NCE-19" in checklist
    assert "## 3.1.0 - 2026-08-08" in changelog

    expected_images = (
        "v3.1.0-dashboard.png",
        "v3.1.0-routing-flow.png",
        "v3.1.0-destinations.png",
        "v3.1.0-delivery-history.png",
        "v3.1.0-discord-idrac.png",
        "v3.1.0-discord-unifi.png",
        "v3.1.0-discord-xen-orchestra.png",
        "v3.1.0-teams-xen-orchestra.png",
    )
    for filename in expected_images:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0


def test_current_docs_do_not_relabel_v310_as_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

    assert "stable-v3.1.0-F4C542" not in readme
    assert "current stable release is **v3.1.0**" not in dockerhub.casefold()
