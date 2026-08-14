#!/usr/bin/env python3
"""Validate local Markdown links and public-documentation drift."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ROOT / "README.md",
    ROOT / "DOCKERHUB_README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "current-configuration-model.md",
    ROOT / "docs" / "data-portability.md",
    ROOT / "docs" / "database-authoritative-resources.md",
    ROOT / "docs" / "deployment.md",
    ROOT / "docs" / "integrations-and-inputs.md",
    ROOT / "docs" / "platform-api.md",
    ROOT / "docs" / "platform-outputs.md",
    ROOT / "docs" / "platform-routing.md",
    ROOT / "docs" / "platform-state.md",
    ROOT / "docs" / "releases" / "v3.1.1.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "v3.1.1-qa-checklist.md",
    ROOT / "docs" / "webui.md",
)

CURRENT_SCREENSHOTS = (
    "v3.1.1-dashboard.png",
    "v3.1.1-routes.png",
    "v3.1.1-route-editor.png",
    "v3.1.1-users.png",
    "v3.1.1-backups.png",
    "v3.1.1-delivery-history.png",
    "v3.1.1-audit-log.png",
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

for filename in CURRENT_SCREENSHOTS:
    path = ROOT / "docs" / "images" / filename
    if not path.is_file() or path.stat().st_size == 0:
        missing.append(str(path.relative_to(ROOT)))

if missing:
    print("ERROR: missing current documentation files/links:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
api = (ROOT / "docs" / "platform-api.md").read_text(encoding="utf-8")
deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
release = (ROOT / "docs" / "releases" / "v3.1.1.md").read_text(encoding="utf-8")
version = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
environment = (ROOT / ".env.example").read_text(encoding="utf-8")
compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")

required_pairs = (
    (readme, "stable-v3.1.1-F4C542"),
    (readme, "**v3.1.1**"),
    (dockerhub.casefold(), "current stable release is **v3.1.1**"),
    (version, 'VERSION = "3.1.1"'),
    (environment, "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.1"),
    (compose, "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.1}"),
    (release, "NCE-32"),
    (deployment, "promote-production-reference.yml"),
    (deployment, "docker-release.yml"),
    (api, "DELETE | `/api/v2/users/{id}`"),
    (api, "DELETE | `/api/v2/backups/{id}`"),
)
for document, required in required_pairs:
    if required not in document:
        raise SystemExit(f"ERROR: current documentation contract missing: {required}")

for stale in (
    "stable-v3.1.0-F4C542",
    "teams-xen-orchestra-v1.9.6.png",
    "discord-xen-orchestra-v1.9.6.png",
):
    if stale in readme:
        raise SystemExit(f"ERROR: stale README reference remains: {stale}")

if "current stable release is **v3.1.0**" in dockerhub.casefold():
    raise SystemExit("ERROR: Docker Hub text still advertises v3.1.0 as current")

for legacy in ("\noutputs:\n", "\nrouting:\n"):
    if legacy in dockerhub:
        raise SystemExit("ERROR: legacy WebUI-managed YAML example remains in Docker Hub text")

for stale_claim in (
    "Nowlert v2.5.2 packages",
    "mounted `config.yaml` is the single configuration authority",
):
    if stale_claim in webui:
        raise SystemExit(f"ERROR: stale WebUI documentation remains: {stale_claim}")

if "The mounted file is authoritative" in api:
    raise SystemExit("ERROR: platform API still claims legacy YAML authority")

print("documentation_links=passed")
print("documentation_release_identity=passed")
print("documentation_screenshots=passed")
print("documentation_drift=passed")
