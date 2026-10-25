"""Guard the comprehensive README and current Nowlert documentation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_remains_comprehensive_and_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    # The current front page keeps the complete operator contract while making
    # the first-screen product explanation and Quick Start easier to reach.
    assert len(lines) >= 350

    for heading in (
        "# What is Nowlert?",
        "# 🦉 Why the name?",
        "# Why Nowlert?",
        "# ✨ Features",
        "# 🔌 Supported Integrations",
        "# 🎯 Project Goals",
        "# 🧩 Core Concepts",
        "# 🏗️ Architecture",
        "# ⚡ Design Principles",
        "# 🚀 Quick Start",
        "# ⚙️ Configuration",
        "# 📬 SMTP Configuration",
        "# 🔄 Example Flow",
        "# 🗺️ Roadmap",
        "# 🤝 Contributing",
        "# 📄 License",
    ):
        assert heading in readme

    for value in (
        "stable-v3.1.6-F4C542",
        "| **Current Stable Release** | **v3.1.6** |",
        "v27.0.0 release candidates",
        "docs/images/v27.0.0-rc.1/dashboard-live-admin-1440.png",
        "docs/images/v27.0.0-rc.1/routing-flow-live-admin-1440.png",
        "docs/images/v27.0.0-rc.1/destinations-list-admin-1440.png",
        "docs/images/v27.0.0-rc.1/sign-in-empty-signed-out-1440.png",
        "docs/images/v27.0.0-rc.1/README.md",
        "platform_database_v1",
        "/nowlert/state",
        "Dedicated integration routes",
        "Fallback routes run only",
        "Build once, promote the same image",
        "development",
        "stage",
        "main",
    ):
        assert value in readme

    assert "stable-v3.1.5-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.5** |" not in readme
    assert "stable-v3.1.4-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.4** |" not in readme
    assert "stable-v3.1.3-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.3** |" not in readme
    assert "stable-v3.1.2-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.2** |" not in readme
    assert "stable-v3.1.1-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.1** |" not in readme
    assert "teams-xen-orchestra-v1.9.6.png" not in readme
    assert "discord-xen-orchestra-v1.9.6.png" not in readme
    # withdrawn on 22 October 2026 (docs/guides/screenshot-privacy.md)
    assert "v3.1.0-delivery-history.png" not in readme
    assert "v3.1.0-discord-xen-orchestra.png" not in readme
    assert "v3.1.0-teams-xen-orchestra.png" not in readme
    # The Preview shows the current candidate UI; older captures are history
    # listed in docs/README.md, never the front-page preview.
    assert "images/v3.1.0-" not in readme
    assert "Historical WebUI examples" not in readme
    assert "fresh v3.1.6\nconfiguration" not in readme
    assert "mounted `config.yaml` is the single configuration authority" not in readme
    assert "\noutputs:\n" not in readme
    assert "\nrouting:\n" not in readme
