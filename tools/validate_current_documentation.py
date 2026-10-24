#!/usr/bin/env python3
"""Validate local Markdown links and public-documentation drift."""

from __future__ import annotations

import re
import runpy
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
    ROOT / "docs" / "integrations" / "README.md",
    ROOT / "docs" / "guides" / "README.md",
    ROOT / "docs" / "guides" / "xen-orchestra-to-discord.md",
    ROOT / "docs" / "guides" / "xen-orchestra-to-teams.md",
    ROOT / "docs" / "guides" / "centralise-homelab-smtp-alerts.md",
    ROOT / "docs" / "guides" / "dell-idrac-redfish-routing.md",
    ROOT / "docs" / "guides" / "zabbix-webhook-to-discord.md",
    ROOT / "docs" / "platform-api.md",
    ROOT / "docs" / "platform-outputs.md",
    ROOT / "docs" / "platform-routing.md",
    ROOT / "docs" / "platform-state.md",
    ROOT / "docs" / "presentation-contract.md",
    ROOT / "docs" / "releases" / "v3.1.6.md",
    ROOT / "docs" / "roadmap.md",
    ROOT / "docs" / "smtp-security.md",
    ROOT / "docs" / "releases" / "validation" / "v3.1.6-qa-checklist.md",
    ROOT / "docs" / "webui.md",
)
FILES = tuple(dict.fromkeys((*FILES, *(
    path for path in (ROOT / "docs").rglob("*.md")
    if "releases" not in path.relative_to(ROOT).parts
    and not path.name.startswith("version-history")
))))

UNCHANGED_RUNTIME_GUIDES = (
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

HISTORICAL_SCREENSHOTS = (
    "v3.1.0-dashboard.png",
    "v3.1.0-routing-flow.png",
    "v3.1.0-destinations.png",
)

# The README and Docker Hub preview show captures of the current candidate UI;
# historical captures are listed only in docs/README.md. Only captures that show
# no account, owner, destination or channel name may appear there while that
# disclosure question is open (docs/guides/screenshot-privacy.md).
CURRENT_PREVIEW = (
    "v27.0.0-rc.1/sign-in-empty-signed-out-390.png",
    "v27.0.0-rc.1/dashboard-live-admin-390.png",
    "v27.0.0-rc.1/routing-flow-live-admin-390.png",
)
CURRENT_CAPTURE_RE = re.compile(r"images/(v27\.0\.0-rc\.1/[\w.-]+\.png)")

RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

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

for filename in (*HISTORICAL_SCREENSHOTS, *CURRENT_PREVIEW):
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
release = (ROOT / "docs" / "releases" / "v3.1.6.md").read_text(encoding="utf-8")
checklist = (ROOT / "docs" / "releases" / "validation" / "v3.1.6-qa-checklist.md").read_text(encoding="utf-8")
version = (ROOT / "src" / "version.py").read_text(encoding="utf-8")
environment = (ROOT / ".env.example").read_text(encoding="utf-8")
compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
guide_index = (ROOT / "docs" / "guides" / "README.md").read_text(encoding="utf-8")
integration_index = (ROOT / "docs" / "integrations" / "README.md").read_text(encoding="utf-8")

required_pairs = (
    (readme, "stable-v3.1.6-F4C542"),
    (readme, "**v3.1.6**"),
    (dockerhub.casefold(), "current stable release is **v3.1.6**"),
    (version, 'VERSION = "3.1.6"'),
    (environment, "NOWLERT_IMAGE=theriark/nowlert-ce:3.1.6"),
    (compose, "${NOWLERT_IMAGE:-theriark/nowlert-ce:3.1.6}"),
    (release, "# Nowlert CE v3.1.6 release notes"),
    (checklist, "# Nowlert CE v3.1.6 QA checklist"),
    (deployment, 'version="v3.1.6"'),
    (deployment, "ghcr.io/theriark/nowlert-ce:3.1.6"),
    (deployment, "docker.io/theriark/nowlert-ce:3.1.6"),
    (deployment, "Development -> Stage -> Finalize CE Release"),
    (deployment, "no second Docker-alias workflow"),
    (api, "DELETE | `/api/v2/users/{id}`"),
    (api, "DELETE | `/api/v2/backups/{id}`"),
    (docs_index, "current v3.1.6 release line"),
    (docs_index, "Historical v3.1.0"),
    (guide_index, "xen-orchestra-to-discord.md"),
    (guide_index, "xen-orchestra-to-teams.md"),
    (guide_index, "centralise-homelab-smtp-alerts.md"),
    (guide_index, "dell-idrac-redfish-routing.md"),
    (guide_index, "zabbix-webhook-to-discord.md"),
    (integration_index, "../redfish.md"),
    (integration_index, "../guides/README.md"),
)
for document, required in required_pairs:
    if required not in document:
        raise SystemExit(f"ERROR: current documentation contract missing: {required}")

if "gh workflow run docker-release.yml" in deployment:
    raise SystemExit("ERROR: obsolete standalone Docker Release Aliases step remains")

for label, document in (("README.md", readme), ("DOCKERHUB_README.md", dockerhub)):
    for relative in CURRENT_PREVIEW:
        if f"docs/images/{relative}" not in document:
            raise SystemExit(f"ERROR: {label} preview does not show current capture {relative}")
    if "images/v3.1.0-" in document:
        raise SystemExit(f"ERROR: {label} preview still embeds a historical capture")
    unreviewed = sorted(set(CURRENT_CAPTURE_RE.findall(document)) - set(CURRENT_PREVIEW))
    if unreviewed:
        raise SystemExit(f"ERROR: {label} preview embeds captures with test-data names: {unreviewed}")

for document in UNCHANGED_RUNTIME_GUIDES:
    text = document.read_text(encoding="utf-8")
    relative = document.relative_to(ROOT)
    if not text.startswith("# "):
        raise SystemExit(f"ERROR: runtime guide missing document title: {relative}")
    if "Nowlert v3.1.1" in text:
        raise SystemExit(f"ERROR: stale runtime guide identity remains in {relative}: Nowlert v3.1.1")

for stale in (
    "stable-v3.1.5-F4C542",
    "| **Current Stable Release** | **v3.1.5** |",
    'version="v3.1.5"',
    "ghcr.io/theriark/nowlert-ce:3.1.5",
    "docker.io/theriark/nowlert-ce:3.1.5",
):
    if stale in readme or stale in dockerhub or stale in deployment:
        raise SystemExit(f"ERROR: stale current-release reference remains: {stale}")

for legacy in ("\noutputs:\n", "\nrouting:\n"):
    if legacy in dockerhub:
        raise SystemExit("ERROR: legacy WebUI-managed YAML example remains in Docker Hub text")

for path in (ROOT / "docs" / "guides").glob("*.md"):
    if path.name == "README.md":
        continue
    text = path.read_text(encoding="utf-8")
    for legacy in ("\noutputs:\n", "\nrouting:\n", "\napi:\n  tokens:\n"):
        if legacy in text:
            raise SystemExit(f"ERROR: legacy WebUI-managed YAML example remains in {path.relative_to(ROOT)}")

for stale_claim in (
    "Nowlert v2.5.2 packages",
    "mounted `config.yaml` is the single configuration authority",
):
    if stale_claim in webui:
        raise SystemExit(f"ERROR: stale WebUI documentation remains: {stale_claim}")

if "The mounted file is authoritative" in api:
    raise SystemExit("ERROR: platform API still claims legacy YAML authority")

schema = runpy.run_path(str(ROOT / "src/storage/migrations.py"))["LATEST_SCHEMA_VERSION"]
for relative in (
    "README.md", "DOCKERHUB_README.md", "docs/platform-state.md",
    "docs/current-configuration-model.md", "docs/webui.md",
):
    text = (ROOT / relative).read_text(encoding="utf-8")
    if f"Current development uses database schema **{schema}**" not in text:
        raise SystemExit(f"ERROR: current development schema drift in {relative}; expected {schema}")

privacy = (ROOT / "docs/guides/screenshot-privacy.md").read_text(encoding="utf-8")
for asset in re.findall(r"^- `(images/[^`]+)`", privacy, re.MULTILINE):
    withdrawn_path = ROOT / "docs" / asset
    # An empty placeholder may remain where the withdrawing tool could
    # overwrite but not delete the file; any content means the capture is back.
    if withdrawn_path.exists() and withdrawn_path.stat().st_size > 0:
        raise SystemExit(f"ERROR: withdrawn private capture remains: {asset}")
    for document in FILES:
        if document.name != "screenshot-privacy.md" and "releases" not in document.relative_to(ROOT).parts:
            if asset in document.read_text(encoding="utf-8"):
                raise SystemExit(f"ERROR: withdrawn capture reference in {document.relative_to(ROOT)}: {asset}")

inventory = set(re.findall(r"^\| `(images/[^`]+)` \| retained \|", privacy, re.MULTILINE))
for path in sorted((ROOT / "docs" / "images").rglob("*")):
    if path.is_file() and path.suffix.lower() in RASTER_SUFFIXES and path.stat().st_size > 0:
        relative = path.relative_to(ROOT / "docs").as_posix()
        if relative not in inventory:
            raise SystemExit(f"ERROR: raster without a screenshot-privacy inventory row: {relative}")
for relative in sorted(inventory):
    if not (ROOT / "docs" / relative).is_file():
        raise SystemExit(f"ERROR: screenshot-privacy inventory row without a file: {relative}")

for document in FILES:
    if "releases" in document.relative_to(ROOT).parts:
        continue
    text = document.read_text(encoding="utf-8")
    if re.search(r"Profile\s*→\s*API tokens", text):
        raise SystemExit(f"ERROR: token navigation omits Security in {document.relative_to(ROOT)}")
    if re.search(r"token[^\n]* in Settings|In \*\*Settings\*\*, create an application token", text):
        raise SystemExit(f"ERROR: obsolete Settings token navigation in {document.relative_to(ROOT)}")

print("documentation_links=passed")
print("documentation_release_identity=passed")
print("documentation_screenshots=passed")
print("documentation_guides=passed")
print("documentation_drift=passed")
print(f"documentation_development_schema={schema}")
print("documentation_withdrawn_captures=passed")
print("documentation_screenshot_inventory=passed")
