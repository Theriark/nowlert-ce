"""Current v2.5.2 public-documentation contract."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_stable_documentation_uses_v252_and_current_screenshots():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

    assert "v2.5.2" in readme
    assert "v2.5.2" in dockerhub

    for name in (
        "v2.5.2-overview.png",
        "v2.5.2-routing-flow.png",
        "v2.5.2-sources.png",
        "v2.5.2-destinations.png",
        "v2.5.2-inputs.png",
        "v2.5.2-settings.png",
        "v2.5.2-discord-idrac.png",
        "v2.5.2-teams.png",
    ):
        assert (ROOT / "docs" / "images" / name).is_file()
        assert name in readme

    assert "teams-xen-orchestra-v1.9.6.png" not in readme
    assert "discord-xen-orchestra-v1.9.6.png" not in readme


def test_dockerhub_does_not_publish_legacy_yaml_authority_examples():
    content = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

    assert "database-authoritative" in content.casefold()
    assert "config.yaml" in content
    assert "\noutputs:\n" not in content
    assert "\nrouting:\n" not in content
    assert "mounted `config.yaml` is the single configuration authority" not in content


def test_public_config_matches_production_state_mount():
    config = yaml.safe_load(
        (ROOT / "config" / "config.example.yaml").read_text(encoding="utf-8")
    )
    assert config["platform"]["configuration_model"] == "platform_database_v1"
    assert config["platform"]["state_dir"] == "/nowlert/state"

    for removed in ("outputs", "routing", "notifications", "presentation", "home_assistant", "redfish"):
        assert removed not in config

    assert "tokens" not in config["api"]
    assert "backups" not in config["platform"]
    assert "language" not in config["webui"]


def test_current_docs_and_roadmap_exist():
    required = (
        "docs/current-configuration-model.md",
        "docs/integrations-and-inputs.md",
        "docs/roadmap.md",
        "docs/version-history-2.3.3-to-2.5.2.md",
        "docs/webui.md",
    )
    for relative in required:
        assert (ROOT / relative).is_file(), relative
