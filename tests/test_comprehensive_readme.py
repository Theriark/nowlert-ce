"""Guard the comprehensive README and current Nowlert documentation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_remains_comprehensive_and_current():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    # The v3.1.1 rewrite removes accumulated historical release prose from the
    # project front page while retaining the complete current product/operator
    # contract.
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
        "stable-v3.1.1-F4C542",
        "| **Current Stable Release** | **v3.1.1** |",
        "v3.1.1-dashboard.png",
        "v3.1.1-routes.png",
        "v3.1.1-delivery-history.png",
        "v3.1.1-audit-log.png",
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

    assert "stable-v3.1.0-F4C542" not in readme
    assert "| **Current Stable Release** | **v3.1.0** |" not in readme
    assert "teams-xen-orchestra-v1.9.6.png" not in readme
    assert "discord-xen-orchestra-v1.9.6.png" not in readme
    assert "mounted `config.yaml` is the single configuration authority" not in readme
    assert "\noutputs:\n" not in readme
    assert "\nrouting:\n" not in readme
