"""Round-52 contracts for canonical Datadog service identity in CE Development."""

from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / ".github" / "scripts"
SWARM_DEPLOY = SCRIPT_DIR / "dokploy_swarm_deploy.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def load_swarm_deploy():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location("nowlert_swarm_deploy", SWARM_DEPLOY)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_merge_environment_preserves_unrelated_values_and_upserts_datadog_identity():
    module = load_swarm_deploy()

    merged = module.merge_environment(
        "TZ=Europe/Lisbon\nFOO=bar\nDD_SERVICE=old-name\n",
        {
            "DD_SERVICE": "nowlert-ce",
            "DD_ENV": "development",
            "DD_VERSION": "a" * 40,
        },
    )

    assert merged == (
        "TZ=Europe/Lisbon\n"
        "FOO=bar\n"
        "DD_SERVICE=nowlert-ce\n"
        "DD_ENV=development\n"
        f"DD_VERSION={'a' * 40}\n"
    )




def test_merge_environment_collapses_duplicate_datadog_keys():
    module = load_swarm_deploy()

    merged = module.merge_environment(
        "DD_SERVICE=old-one\nTZ=Europe/Lisbon\nDD_SERVICE=old-two\n",
        {"DD_SERVICE": "nowlert-ce"},
    )

    assert merged == "DD_SERVICE=nowlert-ce\nTZ=Europe/Lisbon\n"
\n\ndef test_datadog_identity_requires_complete_lowercase_identity():
    module = load_swarm_deploy()
    valid = Namespace(
        dd_service="nowlert-ce",
        dd_env="development",
        dd_version="b" * 40,
    )
    assert module.datadog_identity(valid) == {
        "DD_SERVICE": "nowlert-ce",
        "DD_ENV": "development",
        "DD_VERSION": "b" * 40,
    }

    with pytest.raises(module.DokployError):
        module.datadog_identity(
            Namespace(dd_service="nowlert-ce", dd_env="", dd_version="b" * 40)
        )
    with pytest.raises(module.DokployError):
        module.datadog_identity(
            Namespace(dd_service="Nowlert-CE", dd_env="development", dd_version="b" * 40)
        )


def test_development_workflow_passes_exact_datadog_identity():
    workflow = CI.read_text(encoding="utf-8")
    marker = "- name: Deploy exact CE SHA tag to Development"
    assert marker in workflow
    deploy = workflow[workflow.index(marker):]

    assert '--dd-service "nowlert-ce"' in deploy
    assert '--dd-env "development"' in deploy
    assert '--dd-version "${SOURCE_SHA}"' in deploy
