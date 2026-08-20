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
    ROOT / "docs" / "presentation-contract.md",
    ROOT / "docs" / "releases" / "v3.1.2.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "smtp-security.md",
    ROOT / "docs" / "v3.1.2-qa-checklist.md",
    ROOT / "docs" / "webui.md",
)

CURRENT_RELEASE_GUIDES = (
    ROOT / "docs" / "current-configuration-model.md",
    ROOT / "docs" / "data-portability.md",
    ROOT / "docs" / "database-authoritative-resources.md",
    ROOT / "docs" / "integrations-and-inputs.md",
    ROOT / "docs" / "platform-api.md",
    ROOT / "docs" / "platform-outputs.md",
    ROOT / "docs" / "platform-routing.md",
    ROOT / "docs" / "platform-state.md",
    ROOT / "docs" / "presentation-contract.md",
    ROOT / "docs" / "smtp-security.md",
    ROOT / "docs" / "webui.md",
)

CURRENT_SCREENSHOTS = (
    "v3.1.0-dashboard.png",
    "v3.1.0-routing-flow.png",
    "v3.1.0-destinations.png",
    "v3.1.0-delivery-history.png",
    "v3.1.0-discord-xen-orchestra.png",
    "v3.1.0-teams-xen-orchestra.png",
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
docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
api = (ROOT / "docs" / "platform-api.md").read_text(encoding="utf-8")
deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
release = (ROOT / "docs" / "releases" / "v3.1.2.md").read_text(encoding="utf-8")
checklist = (ROOT / "docs" / "v3.1.2-qa-checklist.md").read_text(encoding="utf-8")
version = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
environment = (ROOT / ".env.example").read_text(encoding="utf-8")
compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

required_pairs = (
    (readme, "stable-v3.1.2-F4C542"),
    (readme, "**v3.1.2**"),
    (dockerhub.casefold(), "current stable release is **v3.1.2**"),
    (version, 'VERSION = "3.1.2"'),
    (environment, "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.2"),
    (compose, "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.2}"),
    (release, "# Nowlert CE v3.1.2 release notes"),
    (checklist, "# Nowlert CE v3.1.2 QA checklist"),
    (changelog, "## 3.1.2 - 2026-08-20"),
    (deployment, 'version="v3.1.2"'),
    (deployment, 'tag="v3.1.2"'),
    (deployment, "ghcr.io/theriark/nowlert-ce:3.1.2"),
    (deployment, "docker.io/theriark/nowlert-ce:3.1.2"),
    (deployment, "promote-production-reference.yml"),
    (deployment, "docker-release.yml"),
    (api, "DELETE | `/api/v2/users/{id}`"),
    (api, "DELETE | `/api/v2/backups/{id}`"),
    (docs_index, "current v3.1.2 release line"),
    (docs_index, "does not introduce a\nvisual redesign"),
)
for document, required in required_pairs:
    if required not in document:
        raise SystemExit(f"ERROR: current documentation contract missing: {required}")

for document in CURRENT_RELEASE_GUIDES:
    text = document.read_text(encoding="utf-8")
    relative = document.relative_to(ROOT)
    if "Nowlert v3.1.2" not in text:
        raise SystemExit(
            f"ERROR: current guide does not identify v3.1.2: {relative}"
        )
    if "Nowlert v3.1.1" in text:
        raise SystemExit(
            f"ERROR: stale current guide identity remains in {relative}: Nowlert v3.1.1"
        )

for stale in (
    "stable-v3.1.1-F4C542",
    "| **Current Stable Release** | **v3.1.1** |",
    'version="v3.1.1"',
    'tag="v3.1.1"',
    "ghcr.io/theriark/nowlert-ce:3.1.1",
    "docker.io/theriark/nowlert-ce:3.1.1",
    "teams-xen-orchestra-v1.9.6.png",
    "discord-xen-orchestra-v1.9.6.png",
):
    if stale in readme or stale in dockerhub or stale in deployment:
        raise SystemExit(f"ERROR: stale current-release reference remains: {stale}")

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
