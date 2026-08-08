"""Guard the comprehensive README and current Nowlert documentation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_remains_comprehensive_and_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    assert len(lines) >= 1200

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
        "stable-v3.1.0-F4C542",
        "| **Current Stable Release** | **v3.1.0** |",
        "| **Next Planned Release** | **v3.x** |",
        "v3.1.0-dashboard.png",
        "v3.1.0-routing-flow.png",
        "v3.1.0-destinations.png",
        "v3.1.0-delivery-history.png",
        "v3.1.0-discord-xen-orchestra.png",
        "v3.1.0-teams-xen-orchestra.png",
        "platform_database_v1",
        "/nowlert/state",
        "Dedicated integration routes",
        "Fallback routes run only",
    ):
        assert value in readme

    assert "teams-xen-orchestra-v1.9.6.png" not in readme
    assert "discord-xen-orchestra-v1.9.6.png" not in readme
    assert "By v2.0, Nowlert is planned" not in readme
    assert "mounted `config.yaml` is the single configuration authority" not in readme
    assert "\noutputs:\n" not in readme
    assert "\nrouting:\n" not in readme
