"""Regression coverage for the CE Development Dokploy deployment gate."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SWARM_DEPLOY = ROOT / ".github" / "scripts" / "dokploy_swarm_deploy.py"
DEVELOPMENT_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def load_module():
    scripts = str(SWARM_DEPLOY.parent)
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(
            "dokploy_swarm_deploy_test", SWARM_DEPLOY
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path and sys.path[0] == scripts:
            sys.path.pop(0)


def test_swarm_deploy_requires_immutable_commit_sha_tag():
    module = load_module()
    module.validate_sha_tag(
        "ghcr.io/theriark/nowlert-ce:sha-" + "a" * 40
    )
    with pytest.raises(module.DokployError):
        module.validate_sha_tag(
            "ghcr.io/theriark/nowlert-ce@sha256:" + "b" * 64
        )
    with pytest.raises(module.DokployError):
        module.validate_sha_tag("ghcr.io/theriark/nowlert-ce:development")


def test_application_deployment_failure_is_terminal(monkeypatch):
    module = load_module()
    monkeypatch.setattr(
        module,
        "list_application_deployments",
        lambda _application_id: [
            {
                "deploymentId": "new-deployment",
                "status": "error",
                "createdAt": "2026-09-14T19:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(
        module.shared,
        "read_deployment_logs",
        lambda _deployment_id: "registry denied",
    )

    with pytest.raises(module.DokployError, match="ended with error"):
        module.wait_application_deployment(
            "application-id", {"old-deployment"}, "", 30
        )


def test_deploy_waits_for_dokploy_record_before_health(monkeypatch):
    module = load_module()
    image = "ghcr.io/theriark/nowlert-ce:sha-" + "a" * 40
    events = []
    images = iter(["previous-image", image])

    monkeypatch.setattr(
        module.shared, "current_image", lambda _application_id: next(images)
    )
    monkeypatch.setattr(module.shared, "write_output", lambda *_args: None)
    monkeypatch.setattr(module, "list_application_deployments", lambda _id: [])

    def request_json(method, path, **_kwargs):
        if path == "application.update":
            events.append("update")
        if path == "application.deploy":
            events.append("deploy")
            return {"deploymentId": "new-deployment"}
        return {}

    monkeypatch.setattr(module.shared, "request_json", request_json)
    monkeypatch.setattr(
        module,
        "wait_application_deployment",
        lambda *_args: events.append("deployment-record"),
    )
    monkeypatch.setattr(
        module.shared,
        "wait_health",
        lambda *_args, **_kwargs: events.append("health"),
    )
    monkeypatch.setattr(
        module,
        "verify_teams_public_media",
        lambda *_args, **_kwargs: None,
    )

    module.deploy(
        argparse.Namespace(
            application_id="application-id",
            image=image,
            health_url="https://example.invalid/api/health",
            title="test",
            description="test",
            timeout=30,
            expected_version="3.1.6",
            noop_ok=False,
        )
    )

    assert events == ["update", "deploy", "deployment-record", "health"]


def test_teams_public_media_origin_is_derived_from_health_url():
    module = load_module()
    assert module.teams_public_media(
        argparse.Namespace(
            health_url="https://ce-dev-nowlert.theriark.dev/api/health"
        )
    ) == {
        "NOWLERT_TEAMS_PUBLIC_BASE_URL": (
            "https://ce-dev-nowlert.theriark.dev"
        )
    }

    with pytest.raises(module.DokployError):
        module.teams_public_media(
            argparse.Namespace(
                health_url="http://ce-dev-nowlert.theriark.dev/api/health"
            )
        )


def test_development_workflow_verifies_tag_digest_and_deploys_sha_tag():
    workflow = DEVELOPMENT_WORKFLOW.read_text(encoding="utf-8")

    assert "Verify Development SHA tag matches build digest" in workflow
    assert 'SHA_TAG="${IMAGE}:sha-${SOURCE_SHA}"' in workflow
    assert 'docker buildx imagetools inspect "${SHA_TAG}" --raw' in workflow
    assert "sha256sum" in workflow

    deploy_block = workflow.split(
        "- name: Deploy exact CE SHA tag to Development", 1
    )[1].split("- name: Record immutable Development result", 1)[0]
    assert "dokploy_swarm_deploy.py" in deploy_block
    assert '--image "${IMAGE}:sha-${SOURCE_SHA}"' in deploy_block
    assert "teams_modern_card=" in deploy_block
    assert '@${{ steps.build.outputs.digest }}' not in deploy_block
