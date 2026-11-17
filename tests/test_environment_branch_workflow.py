"""Environment branch and immutable CE promotion contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return (
        ROOT / ".github" / "workflows" / name
    ).read_text(encoding="utf-8")


def test_environment_branch_and_immutable_promotion_contract():
    ci = workflow("ci.yml")
    stage = workflow("promote-stage.yml")
    release = workflow("release.yml")

    assert "- development" in ci
    assert "- main" not in ci

    # A successful push CI on development must build, publish, and deploy the
    # Development image directly. There is no standalone Development workflow.
    assert "needs: tests" in ci
    assert "github.event_name == 'push'" in ci
    assert "github.ref == 'refs/heads/development'" in ci
    assert "docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7" in ci
    assert "ghcr.io/theriark/nowlert-ce" in ci
    assert ":development" in ci
    assert "environment: development" in ci
    assert "DOKPLOY_CE_DEVELOPMENT_APPLICATION_ID" in ci
    assert "DOKPLOY_EE_DEVELOPMENT_APPLICATION_ID" not in ci
    assert "Development immutable image:" in ci
    assert not (ROOT / ".github" / "workflows" / "docker-development.yml").exists()

    # Stage promotion proves the Development image came from a successful
    # development CI push run, not a removed standalone Development workflow.
    assert "actions/workflows/ci.yml/runs?branch=development&event=push" in stage
    assert '"$(jq -r \'.event\' <<<"${RUN}")" == "push"' in stage

    # Stage promotion owns only the Stage branch. It must never write main.
    assert "contents: write" in stage
    assert "refs/heads/development" in stage
    assert "refs/heads/stage" in stage
    assert "refs/heads/main" not in stage
    assert "git/refs/heads/main" not in stage
    assert "force=false" in stage
    assert "force=true" not in stage
    assert "Waiting for stage ref propagation" in stage
    assert "cannot fast-forward" in stage

    assert not (ROOT / ".github" / "workflows" / "promote-production-reference.yml").exists()
    # The release and candidate workflows are folded into the two buttons.
    for removed in ("finalize-release.yml", "prepare-rc.yml"):
        assert not (ROOT / ".github" / "workflows" / removed).exists(), removed
    assert not (ROOT / ".github" / "scripts" / "finalize_release.py").exists()

    # The release runs from development, releases the stage head and owns the
    # only Stage -> main update: a merge commit, never a force push, and never
    # main into development.
    assert "environment: stage" in release
    assert "contents: write" in release
    assert "packages: write" in release
    assert '[[ "${GITHUB_REF}" == "refs/heads/development" ]]' in release
    assert 'STAGE_SHA="$(git rev-parse refs/remotes/origin/stage)"' in release
    assert 'git merge-base --is-ancestor "${STAGE_SHA}" "${MAIN_SHA}"' in release
    assert '-f "parents[]=${MAIN_SHA}"' in release
    assert '-f "parents[]=${STAGE_SHA}"' in release
    assert "git/refs/heads/main" in release
    assert "git/refs/heads/development" not in release
    assert "-F force=false" in release
    assert "force=true" not in release
    assert "production_reference_run_id" not in release
    assert "CE_PRODREF_APPLICATION_ID" not in release
    assert "CE_RELEASE_TOKEN" not in release
    assert "GH_TOKEN: ${{ github.token }}" in release

    # release.yml is the only stable publication workflow. It reuses the
    # digest Stage runs, publishes both registries and verifies every alias
    # without rebuilding the image.
    assert not (ROOT / ".github" / "workflows" / "docker-release.yml").exists()
    assert "docker/build-push-action" not in release
    assert "docker/login-action@dbcb813823bdd20940b903addbd779551569679f # v4" in release
    assert "DOCKERHUB_USERNAME" in release
    assert "DOCKERHUB_TOKEN" in release
    assert "skopeo copy --all --preserve-digests" in release
    assert '"${IMAGE_REPOSITORY}:${VERSION}"' in release
    assert '"${IMAGE_REPOSITORY}:latest"' in release
    assert '"${DOCKERHUB_REPOSITORY}:${VERSION}"' in release
    assert '"${DOCKERHUB_REPOSITORY}:latest"' in release
    assert "DOCKERHUB_REPOSITORY: docker.io/theriark/nowlert-ce" in release
    assert "Rebuild performed: no" in release
