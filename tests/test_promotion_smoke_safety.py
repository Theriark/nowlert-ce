"""Safety contract for notification-silent release promotions."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / ".github" / "scripts" / "dokploy_release.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("nowlert_dokploy_release", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_promotion_workflow_yaml_is_valid() -> None:
    for relative in (
        ".github/workflows/promote-stage.yml",
        ".github/workflows/promote-production-reference.yml",
        ".github/workflows/finalize-release.yml",
    ):
        payload = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        assert isinstance(payload, dict), relative


def test_automatic_promotion_workflows_have_zero_delivery_test_paths() -> None:
    forbidden = (
        "run-schedule",
        "stage_ce_qa_schedule_id",
        "prodref_ce_smoke_schedule_id",
        "schedule-id",
        "zabbix",
        "portainer",
        "firing",
        "resolved",
        "/api/v2",
        "smtp",
    )

    for relative in (
        ".github/workflows/promote-stage.yml",
        ".github/workflows/promote-production-reference.yml",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        folded = content.casefold()
        assert "promotion-smoke" in content
        assert "notification delivery tests: disabled" in folded
        assert "--evidence-type silent-promotion-smoke" in content
        for value in forbidden:
            assert value not in folded, (relative, value)


def test_promotion_smoke_function_is_passive_and_read_only() -> None:
    helper = load_helper()
    smoke = inspect.getsource(helper.promotion_smoke)
    folded = smoke.casefold()

    assert "wait_health(" in smoke
    assert "current_image(" in smoke
    assert "notification delivery tests disabled" in folded

    for forbidden in (
        "request_json(",
        "run_schedule(",
        "schedule.runmanually",
        "urllib.request",
        "post",
        "smtp",
        "/api/v2",
        "firing",
        "resolved",
    ):
        assert forbidden not in folded, forbidden

    health = inspect.getsource(helper.wait_health).casefold()
    assert "urllib.request.request(" in health
    assert "data=" not in health
    assert 'method="post"' not in health

    image_lookup = inspect.getsource(helper.current_image).casefold()
    assert '"get"' in image_lookup
    assert '"post"' not in image_lookup


def test_release_finalization_rejects_delivery_qa_for_new_promotion_chain() -> None:
    finalizer = (
        ROOT / ".github" / "scripts" / "finalize_release.py"
    ).read_text(encoding="utf-8")
    workflow = (
        ROOT / ".github" / "workflows" / "finalize-release.yml"
    ).read_text(encoding="utf-8")

    assert "STAGE CE SILENT PROMOTION SMOKE PASSED" in finalizer
    assert "PRODUCTION REFERENCE CE SILENT PROMOTION SMOKE PASSED" in finalizer
    assert "SILENT_PROMOTION_FORBIDDEN_LOG_FRAGMENTS" in finalizer
    assert "qa_schedule_deployment_id" not in workflow
    assert "Notification delivery tests during promotions: disabled" in workflow

def test_legacy_schedule_runner_remains_available_but_is_not_auto_promoted() -> None:
    helper = load_helper()
    assert callable(helper.run_schedule)

    stage = (ROOT / ".github" / "workflows" / "promote-stage.yml").read_text(
        encoding="utf-8"
    )
    prodref = (
        ROOT / ".github" / "workflows" / "promote-production-reference.yml"
    ).read_text(encoding="utf-8")
    assert "run-schedule" not in stage
    assert "run-schedule" not in prodref
