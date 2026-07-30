"""v2.5.2 packaged image-asset validation contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docker_image_validates_actual_runtime_asset_mappings():
    dockerfile = (ROOT / "Dockerfile").read_text(
        encoding="utf-8"
    )
    validator = ROOT / "tools" / "validate_packaged_icons.py"

    assert validator.is_file()
    assert (
        "RUN python3 "
        "/nowlert/tools/validate_packaged_icons.py"
    ) in dockerfile

    assert (
        "/nowlert/src/webui/source-icons/"
        "xen-orchestra.png"
    ) not in dockerfile

    source = validator.read_text(encoding="utf-8")
    assert "WebUIService" in source
    assert "presentation.py" in source
    assert "packaged_icon_validation=passed" in source
