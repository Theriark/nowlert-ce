#!/usr/bin/env python3
"""Validate notification and WebUI assets actually referenced by Nowlert."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".png", ".svg", ".jpg", ".jpeg", ".webp"}

missing: list[str] = []
notification_assets: set[Path] = set()


# Read icon mappings without importing the full application configuration.
presentation_path = ROOT / "src" / "formatters" / "presentation.py"
tree = ast.parse(
    presentation_path.read_text(encoding="utf-8"),
    filename=str(presentation_path),
)

for node in ast.walk(tree):
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        continue

    value = node.value
    if not isinstance(value, ast.Dict):
        continue

    for item in value.values:
        if not (
            isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ):
            continue

        relative = Path(item.value)
        if relative.suffix.casefold() not in IMAGE_SUFFIXES:
            continue

        notification_assets.add(
            ROOT / "assets" / "icons" / relative
        )


# WebUIService is the authority mapping /ui URLs to packaged files.
service_path = ROOT / "src" / "webui" / "service.py"
spec = importlib.util.spec_from_file_location(
    "_nowlert_packaged_webui_service",
    service_path,
)

if spec is None or spec.loader is None:
    raise SystemExit("ERROR: Could not load WebUI asset service.")

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class Configuration:
    @staticmethod
    def get(*_keys, default=None):
        return default


service = module.WebUIService(
    Configuration(),
    root=ROOT,
    platform_available=True,
)

webui_assets = {
    ROOT / relative
    for relative, _content_type, _cache_control
    in service.assets.values()
}


for path in sorted(notification_assets | webui_assets):
    if not path.is_file():
        missing.append(str(path.relative_to(ROOT)))


if missing:
    print("ERROR: required packaged assets are missing:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)


print(f"notification_icon_assets={len(notification_assets)}")
print(f"webui_assets={len(webui_assets)}")
print("packaged_icon_validation=passed")
