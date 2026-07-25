#!/usr/bin/env python3
"""Validate local Markdown links and public-documentation drift."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "README.md",
    ROOT / "DOCKERHUB_README.md",
    ROOT / "docs" / "webui.md",
    ROOT / "docs" / "integrations-and-inputs.md",
    ROOT / "docs" / "current-configuration-model.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "version-history-2.3.3-to-2.5.2.md",
)

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
missing: list[str] = []

for document in FILES:
    if not document.is_file():
        missing.append(str(document.relative_to(ROOT)))
        continue

    text = document.read_text(encoding="utf-8")
    for raw in LINK_RE.findall(text):
        target = raw.split("#", 1)[0].strip()
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (document.parent / target).resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            missing.append(f"{document.relative_to(ROOT)} -> {raw}")
            continue
        if not resolved.exists():
            missing.append(f"{document.relative_to(ROOT)} -> {raw}")

if missing:
    print("ERROR: missing local documentation links:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")

for stale in (
    "teams-xen-orchestra-v1.9.6.png",
    "discord-xen-orchestra-v1.9.6.png",
):
    if stale in readme:
        raise SystemExit(f"ERROR: stale screenshot reference remains: {stale}")

for legacy in ("\noutputs:\n", "\nrouting:\n"):
    if legacy in dockerhub:
        raise SystemExit("ERROR: legacy WebUI-managed YAML example remains in Docker Hub text")

print("documentation_links=passed")
print("documentation_drift=passed")
