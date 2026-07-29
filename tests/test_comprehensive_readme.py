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
        "stable-v3.0.0-blue",
        "| **Current Stable Release** | **v3.0.0** |",
        "| **Next Planned Release** | **v3.x** |",
        "v2.5.2-overview.png",
        "v2.5.2-routing-flow.png",
        "v2.5.2-sources.png",
        "v2.5.2-destinations.png",
        "v2.5.2-inputs.png",
        "v2.5.2-settings.png",
        "v2.5.2-discord-idrac.png",
        "v2.5.2-teams.png",
        "platform_database_v1",
        "/notifinho/state",
        "Dedicated integration routes",
        "Fallback routes run only",
    ):
        assert value in readme

    assert "teams-xen-orchestra-v1.9.6.png" not in readme
    assert "discord-xen-orchestra-v1.9.6.png" not in readme
    assert "By v2.0, Notifinho is planned" not in readme
    assert "mounted `config.yaml` is the single configuration authority" not in readme
    assert "\noutputs:\n" not in readme
    assert "\nrouting:\n" not in readme
