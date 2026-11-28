"""Stable v3.1.6 release records and the 27.0.0 application identity."""

from pathlib import Path

from version import VERSION


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_SCREENSHOTS = (
    "v3.1.0-dashboard.png",
    "v3.1.0-routing-flow.png",
    "v3.1.0-destinations.png",
)
CURRENT_PREVIEW = (
    "v27.0.0-rc.1/dashboard-live-admin-1440.png",
    "v27.0.0-rc.1/routing-flow-live-admin-1440.png",
    "v27.0.0-rc.1/destinations-list-admin-1440.png",
    "v27.0.0-rc.1/sign-in-empty-signed-out-1440.png",
)
# Withdrawn on 22 October 2026 and restored with their deployment labels
# masked on 2 November 2026 (docs/guides/screenshot-privacy.md). They stay
# history: listed in docs/README.md, never in the README or WebUI guide.
RESTORED_HISTORICAL_SCREENSHOTS = (
    "v3.1.0-delivery-history.png",
    "v3.1.0-discord-xen-orchestra.png",
    "v3.1.0-teams-xen-orchestra.png",
)
CURRENT_GUIDES = (
    "xen-orchestra-to-discord.md",
    "xen-orchestra-to-teams.md",
    "centralise-homelab-smtp-alerts.md",
    "dell-idrac-redfish-routing.md",
    "zabbix-webhook-to-discord.md",
)


def test_v316_release_identity_is_consistent():
    assert VERSION == "27.0.0"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    environment = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.6.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "releases" / "validation" / "v3.1.6-qa-checklist.md").read_text(encoding="utf-8")
    assert "stable-v3.1.6-F4C542" in readme
    assert "**Current Stable Release** | **v3.1.6**" in readme
    assert "current stable release is **v3.1.6**" in dockerhub.casefold()
    assert "theriark/nowlert-ce:3.1.6" in dockerhub
    assert "NOWLERT_IMAGE=theriark/nowlert-ce:27.0.0" in environment
    assert "${NOWLERT_IMAGE:-theriark/nowlert-ce:27.0.0}" in compose
    assert release.startswith("# Nowlert CE v3.1.6 release notes")
    assert checklist.startswith("# Nowlert CE v3.1.6 QA checklist")


def test_v316_historical_visual_examples_are_packaged_and_referenced():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    dockerhub = (ROOT / "DOCKERHUB_README.md").read_text(encoding="utf-8")
    webui = (ROOT / "docs" / "webui.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    for filename in HISTORICAL_SCREENSHOTS:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in docs_index
        # history stays out of the current presentation
        assert filename not in readme and filename not in dockerhub and filename not in webui
    for relative in CURRENT_PREVIEW:
        path = ROOT / "docs" / "images" / relative
        assert path.is_file(), relative
        assert path.stat().st_size > 0, relative
        assert f"docs/images/{relative}" in readme
        assert f"docs/images/{relative}" in dockerhub
    for filename in RESTORED_HISTORICAL_SCREENSHOTS:
        path = ROOT / "docs" / "images" / filename
        assert path.is_file() and path.stat().st_size > 0, filename
        assert filename in docs_index, filename
        assert filename not in readme and filename not in webui, filename
    assert "Historical v3.1.0" in docs_index


def test_v316_consolidated_guide_batch_is_packaged():
    guide_index = (ROOT / "docs" / "guides" / "README.md").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "integrations" / "README.md").is_file()
    for filename in CURRENT_GUIDES:
        path = ROOT / "docs" / "guides" / filename
        assert path.is_file(), filename
        assert path.stat().st_size > 0, filename
        assert filename in guide_index
        text = path.read_text(encoding="utf-8")
        for forbidden in ("\noutputs:\n", "\nrouting:\n", "\napi:\n  tokens:\n"):
            assert forbidden not in text, filename


def test_v316_release_safety_contract():
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert not (ROOT / ".github" / "workflows" / "finalize-release.yml").exists()
    assert '[[ "${GITHUB_REF}" == "refs/heads/development" ]]' in release
    assert "refs/remotes/origin/stage" in release
    assert "release_tags.py stage-candidate" in release
    assert "refs/heads/main" not in release
    assert "--method PATCH" not in release
    assert "production_reference_run_id" not in release
    assert "skopeo copy --all --preserve-digests" in release
    assert "a version tag is never moved" in release
    assert "      - main\n" not in ci
    assert "refs/heads/main" not in stage
    assert "--method PATCH" not in stage
    assert "Waiting for stage ref propagation" not in stage


def test_v316_documentation_validator_tracks_current_release():
    validator = (ROOT / "tools" / "validate_current_documentation.py").read_text(encoding="utf-8")
    assert 'ROOT / "docs" / "releases" / "v3.1.6.md"' in validator
    assert 'ROOT / "docs" / "releases" / "validation" / "v3.1.6-qa-checklist.md"' in validator
    assert "stable-v3.1.6-F4C542" in validator
    assert 'VERSION = "27.0.0"' in validator
    assert "promote-production-reference.yml" not in validator


def test_v316_deployment_docs_contain_stage_final_promotion_chain():
    deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v3.1.6.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "releases" / "validation" / "v3.1.6-qa-checklist.md").read_text(encoding="utf-8")
    normalized = " ".join(deployment.split()).casefold()
    assert "gh workflow run promote-stage.yml" in deployment
    assert "gh workflow run release.yml" in deployment
    assert "gh workflow run finalize-release.yml" not in deployment
    assert "gh workflow run docker-release.yml" not in deployment
    assert "promote-production-reference.yml" not in deployment
    assert "production reference" not in release.casefold()
    assert "production reference" not in checklist.casefold()
    assert "development -> stage -> release ce" in normalized
    assert "neither workflow moves a branch" in normalized
    assert "the gate script fast-forwards `stage` to the new candidate tag" in normalized
    assert "the gate script merges `stage` into `main`" in normalized
    assert "release ce owns the only stage -> `main` merge" not in normalized
    assert "--ref stage" not in deployment
    assert deployment.count("--ref development") == 2
    assert "ghcr.io/theriark/nowlert-ce:3.1.6" in deployment
    assert "docker.io/theriark/nowlert-ce:3.1.6" in deployment
    assert "no image rebuild" in normalized
    assert "there is no additional ce dokploy `production` deployment workflow" in normalized
