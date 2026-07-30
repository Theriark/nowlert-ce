"""v2.5.2 Routing Flow and notification icon regressions."""

from pathlib import Path

from formatters.presentation import PresentationMixin


ROOT = Path(__file__).resolve().parents[1]


def test_disabled_flow_signal_is_typographic_and_warning_coloured():
    script = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "src/webui/enhancements.css").read_text(encoding="utf-8")
    assert 'disabled: "⊘︎"' in script
    assert 'disabled: "⛔"' not in script
    assert ".flow-arrow.flow-disabled" in styles
    assert "color: var(--warning)" in styles


def test_destination_flow_uses_destination_name_then_platform_and_channel():
    script = (ROOT / "src/webui/app.js").read_text(encoding="utf-8")
    assert "function destinationFlowLabels(destination)" in script
    assert "name: destination.name" in script
    assert "`${platform} · ${channel}`" in script
    assert "destinationLabels.name" in script
    assert "destinationLabels.detail" in script


def test_discord_uses_padded_variants_for_requested_integrations():
    expected = {
        "xo": "discord/xen-orchestra.png",
        "grafana": "discord/grafana.png",
        "truenas": "discord/truenas.png",
        "portainer": "discord/portainer.png",
        "home_assistant": "discord/home-assistant.png",
        "supermicro": "discord/supermicro.png",
        "zabbix": "discord/zabbix.png",
    }
    assert expected.items() <= PresentationMixin.DISCORD_PRODUCT_ICONS.items()
    formatter = PresentationMixin.__new__(PresentationMixin)
    for source, relative in expected.items():
        assert formatter._discord_product_icon_url(source) == (
            f"nowlert-asset://{relative}"
        )
        assert (ROOT / "assets/icons" / relative).is_file()


def test_teams_keeps_regular_official_assets():
    formatter = PresentationMixin.__new__(PresentationMixin)
    icon = formatter._product_icon_url("zabbix")
    assert icon.startswith("https://")
    assert icon.endswith("/zabbix.png")
    assert "/discord/" not in icon


def test_docker_image_contract_copies_and_checks_icon_assets():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    validator_path = ROOT / "tools" / "validate_packaged_icons.py"

    assert "COPY assets /nowlert/assets" in dockerfile
    assert "COPY src /nowlert/src" in dockerfile
    assert "COPY tools /nowlert/tools" in dockerfile
    assert (
        "RUN python3 /nowlert/tools/validate_packaged_icons.py"
        in dockerfile
    )

    # The Dockerfile must validate the runtime asset maps rather than
    # duplicating every icon path or inventing a second WebUI icon tree.
    assert "/nowlert/src/webui/source-icons/" not in dockerfile

    validator = validator_path.read_text(encoding="utf-8")
    assert "presentation.py" in validator
    assert "WebUIService" in validator
    assert "notification_assets" in validator
    assert "webui_assets" in validator
    assert "packaged_icon_validation=passed" in validator


def test_discord_components_and_legacy_embed_use_discord_icon_resolver():
    common = (ROOT / "src/formatters/discord_common.py").read_text(encoding="utf-8")
    assert "self._discord_product_icon_url(data.source)" in common
    presentation = (ROOT / "src/formatters/presentation.py").read_text(encoding="utf-8")
    assert "url = self._discord_product_icon_url(source)" in presentation

def test_settings_cards_use_full_workspace_width():
    styles = (ROOT / "src/webui/styles.css").read_text(
        encoding="utf-8"
    )

    expected = """.settings-card {
  box-sizing: border-box;
  max-width: none;
  width: 100%;
}"""

    assert expected in styles
    assert """.settings-card {
  max-width: 900px;
}""" not in styles
