from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v310_release_documentation_and_screenshots_are_packaged():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.0.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "v3.1.0-qa-checklist.md").read_text(encoding="utf-8")

    assert "stable-v3.1.0-F4C542" in readme
    assert "**Current Stable Release** | **v3.1.0**" in readme
    assert "docs/images/v3.1.0-dashboard.png" in readme
    assert "docs/images/v3.1.0-routing-flow.png" in readme
    assert "docs/images/v3.1.0-destinations.png" in readme
    assert "docs/images/v3.1.0-delivery-history.png" in readme
    assert "docs/images/v3.1.0-discord-xen-orchestra.png" in readme
    assert "docs/images/v3.1.0-teams-xen-orchestra.png" in readme
    assert len(readme.splitlines()) >= 1200
    for heading in (
        "# What is Nowlert?",
        "# 🦉 Why the name?",
        "# Why Nowlert?",
        "# ✨ Features",
        "# 🔌 Supported Integrations",
        "# 🚀 Quick Start",
        "# 📄 License",
    ):
        assert heading in readme

    assert "current stable release is **v3.1.0**" in dockerhub.lower()
    assert "theriark/nowlert-ce:3.1.0" in dockerhub
    assert "v3.1.0-dashboard.png" in dockerhub
    assert "v3.1.0-routing-flow.png" in dockerhub
    assert "main/docs/images/v3.1.0-dashboard.png" in dockerhub
    assert "main/docs/imagesv3.1.0-dashboard.png" not in dockerhub

    assert "## 3.1.0 - 2026-08-08" in changelog
    assert "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.0" in env_example
    assert "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.0}" in compose
    assert "NCE-20" in release
    assert "1023 passed" in release
    assert "NCE-5 through NCE-19" in checklist

    expected_images = (
        "logo.png",
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
        assert path.is_file()
        assert path.stat().st_size > 0
