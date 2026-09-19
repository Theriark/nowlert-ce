"""Round-54 contracts for Datadog Runtime SCA in CE Development."""

from __future__ import annotations

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / ".github" / "scripts"
SWARM_DEPLOY = SCRIPT_DIR / "dokploy_swarm_deploy.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def load_swarm_deploy():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "nowlert_swarm_deploy_runtime_sca",
            SWARM_DEPLOY,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_runtime_sca_dependencies_are_exactly_pinned():
    requirements = set(
        (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    )

    assert {
        "ddtrace==4.15.1",
        "bytecode==0.19.0",
        "ddtrace-internal==0.1.0",
        "envier==0.6.1",
        "opentelemetry-api==1.44.0",
        "wrapt==2.4.1",
    } <= requirements


def test_runtime_sca_contract_enables_sca_and_keeps_iast_off():
    module = load_swarm_deploy()

    assert module.datadog_runtime_security(
        Namespace(dd_runtime_sca=False)
    ) == {}
    assert module.datadog_runtime_security(
        Namespace(
            dd_runtime_sca=True,
            dd_agent_host="datadog-agent",
            dd_trace_agent_port=8126,
        )
    ) == {
        "NOWLERT_DDTRACE_ENABLED": "true",
        "DD_APPSEC_SCA_ENABLED": "true",
        "DD_IAST_ENABLED": "false",
        "DD_AGENT_HOST": "datadog-agent",
        "DD_TRACE_AGENT_PORT": "8126",
    }


def test_runtime_sca_requires_agent_transport():
    module = load_swarm_deploy()

    try:
        module.datadog_runtime_security(
            Namespace(
                dd_runtime_sca=True,
                dd_agent_host="",
                dd_trace_agent_port=8126,
            )
        )
    except module.DokployError as exc:
        assert "--dd-agent-host" in str(exc)
    else:
        raise AssertionError("missing Datadog Agent host must fail")

    try:
        module.datadog_runtime_security(
            Namespace(
                dd_runtime_sca=True,
                dd_agent_host="datadog-agent",
                dd_trace_agent_port=0,
            )
        )
    except module.DokployError as exc:
        assert "--dd-trace-agent-port" in str(exc)
    else:
        raise AssertionError("invalid Datadog trace port must fail")


def test_startup_wraps_python_only_when_datadog_is_enabled():
    script = (ROOT / "start.sh").read_text(encoding="utf-8")

    assert (
        'if [ "${NOWLERT_DDTRACE_ENABLED:-false}" = "true" ]; then'
        in script
    )
    assert "command -v ddtrace-run" in script
    assert "exec ddtrace-run python3 main.py" in script
    assert script.endswith("exec python3 main.py\n")


def test_development_workflow_activates_runtime_sca_only():
    workflow = CI.read_text(encoding="utf-8")
    marker = "- name: Deploy exact CE SHA tag to Development"
    assert marker in workflow
    deploy = workflow[workflow.index(marker):]

    assert "--dd-runtime-sca" in deploy
    assert '--dd-service "nowlert-ce"' in deploy
    assert '--dd-env "development"' in deploy
    assert '--dd-version "${SOURCE_SHA}"' in deploy
    assert '--dd-agent-host "datadog-agent"' in deploy
    assert "--dd-trace-agent-port 8126" in deploy
    assert "--dd-iast" not in deploy
