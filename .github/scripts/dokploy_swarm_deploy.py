#!/usr/bin/env python3
"""Deploy immutable commit-tagged images through Dokploy Swarm safely."""

from __future__ import annotations

import argparse
import re
import sys
import time

import dokploy_release as shared


SHA_TAG_RE = re.compile(
    r"^ghcr\.io/theriark/nowlert-ce:sha-[0-9a-f]{40}$"
)
DokployError = shared.DokployError


def merge_environment(current: str, values: dict[str, str]) -> str:
    """Upsert selected environment variables without disturbing unrelated entries."""
    managed = set(values)
    written: set[str] = set()
    lines: list[str] = []
    for raw_line in (current or "").splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#") and "=" in raw_line:
            key = raw_line.split("=", 1)[0].strip()
            if key in managed:
                if key not in written:
                    lines.append(f"{key}={values[key]}")
                    written.add(key)
                continue
        lines.append(raw_line)
    for key, value in values.items():
        if key not in written:
            lines.append(f"{key}={value}")
    return "\n".join(lines).rstrip("\n") + "\n"


def application_environment(application_id: str) -> str:
    response = shared.request_json(
        "GET",
        "application.one",
        query={"applicationId": application_id},
    )
    value = shared.find_key(response, "env")
    return value if isinstance(value, str) else ""


def datadog_identity(args: argparse.Namespace) -> dict[str, str]:
    values = {
        "DD_SERVICE": str(getattr(args, "dd_service", "") or "").strip(),
        "DD_ENV": str(getattr(args, "dd_env", "") or "").strip(),
        "DD_VERSION": str(getattr(args, "dd_version", "") or "").strip(),
    }
    supplied = [value for value in values.values() if value]
    if supplied and len(supplied) != len(values):
        raise DokployError(
            "Datadog identity requires --dd-service, --dd-env, and --dd-version together"
        )
    if not supplied:
        return {}
    for key in ("DD_SERVICE", "DD_ENV"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", values[key]):
            raise DokployError(f"{key} must use lowercase Datadog-safe characters")
    if not re.fullmatch(r"[0-9a-f]{40}", values["DD_VERSION"]):
        raise DokployError("DD_VERSION must be the exact 40-character source SHA")
    return values


def datadog_runtime_security(args: argparse.Namespace) -> dict[str, str]:
    if not bool(getattr(args, "dd_runtime_sca", False)):
        return {}

    agent_host = str(getattr(args, "dd_agent_host", "") or "").strip()
    trace_agent_port = int(getattr(args, "dd_trace_agent_port", 0) or 0)

    if not agent_host:
        raise DokployError(
            "Datadog Runtime SCA requires --dd-agent-host"
        )
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", agent_host):
        raise DokployError(
            "DD_AGENT_HOST must use lowercase DNS-safe characters"
        )
    if not 1 <= trace_agent_port <= 65535:
        raise DokployError(
            "Datadog Runtime SCA requires --dd-trace-agent-port in 1..65535"
        )

    return {
        "NOWLERT_DDTRACE_ENABLED": "true",
        "DD_APPSEC_SCA_ENABLED": "true",
        "DD_IAST_ENABLED": "false",
        "DD_AGENT_HOST": agent_host,
        "DD_TRACE_AGENT_PORT": str(trace_agent_port),
    }


def verify_datadog_identity(application_id: str, expected: dict[str, str]) -> None:
    if not expected:
        return
    environment = application_environment(application_id)
    observed: dict[str, str] = {}
    for raw_line in environment.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if key in expected:
            observed[key] = value
    if observed != expected:
        raise DokployError(
            f"Dokploy Datadog identity mismatch: observed {observed}, expected {expected}"
        )
    print(
        "PASS: Datadog identity "
        f"service={expected['DD_SERVICE']} env={expected['DD_ENV']} "
        f"version={expected['DD_VERSION']}"
    )


def verify_datadog_runtime_security(
    application_id: str,
    expected: dict[str, str],
) -> None:
    if not expected:
        return
    environment = application_environment(application_id)
    observed: dict[str, str] = {}
    for raw_line in environment.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if key in expected:
            observed[key] = value
    if observed != expected:
        raise DokployError(
            "Dokploy Datadog Runtime SCA mismatch: "
            f"observed {observed}, expected {expected}"
        )
    print(
        "PASS: Datadog Runtime SCA enabled, IAST explicitly disabled, "
        f"agent={expected['DD_AGENT_HOST']}:{expected['DD_TRACE_AGENT_PORT']}"
    )


def validate_sha_tag(image: str) -> None:
    if not SHA_TAG_RE.fullmatch(image):
        raise DokployError(
            "Dokploy Swarm deployment image must be an immutable Nowlert commit tag "
            "ghcr.io/theriark/nowlert-ce:sha-<40 lowercase hexadecimal characters>"
        )


def list_application_deployments(application_id: str):
    response = shared.request_json(
        "GET",
        "deployment.allByType",
        query={"id": application_id, "type": "application"},
    )
    return shared.deployment_records(response)


def wait_application_deployment(
    application_id: str,
    before: set[str],
    deployment_id: str,
    timeout_seconds: int,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_logs = ""
    if deployment_id:
        shared.write_output("deployment_id", deployment_id)

    while time.monotonic() < deadline:
        records = list_application_deployments(application_id)
        if not deployment_id:
            candidates = [
                record for record in records if shared.record_id(record) not in before
            ]
            if candidates:
                candidates.sort(key=shared.record_sort_key, reverse=True)
                deployment_id = shared.record_id(candidates[0])
                shared.write_output("deployment_id", deployment_id)
                print(
                    f"Detected application deployment {deployment_id} for {application_id}"
                )

        if deployment_id:
            matching = next(
                (
                    record
                    for record in records
                    if shared.record_id(record) == deployment_id
                ),
                None,
            )
            status = shared.record_status(matching or {})
            try:
                last_logs = shared.read_deployment_logs(deployment_id)
            except DokployError:
                pass

            if status in shared.TERMINAL_FAILURE:
                if last_logs:
                    print(last_logs[-8000:])
                raise DokployError(
                    f"Application {application_id} deployment {deployment_id} ended with {status}"
                )
            if status in shared.TERMINAL_SUCCESS:
                if last_logs:
                    print(last_logs[-8000:])
                shared.write_output("deployment_id", deployment_id)
                print(
                    f"PASS: Dokploy application deployment {deployment_id} ended with {status}"
                )
                return deployment_id

        time.sleep(5)

    if last_logs:
        print(last_logs[-8000:])
    raise DokployError(
        f"Timed out waiting for Dokploy application {application_id} deployment to finish"
    )


def deploy(args: argparse.Namespace) -> None:
    validate_sha_tag(args.image)
    previous = shared.current_image(args.application_id)
    shared.write_output("previous_image", previous)
    shared.write_output("deployed_image", args.image)

    identity = datadog_identity(args)
    runtime_security = datadog_runtime_security(args)
    managed_environment = {**identity, **runtime_security}
    current_env = (
        application_environment(args.application_id) if managed_environment else ""
    )
    merged_env = (
        merge_environment(current_env, managed_environment)
        if managed_environment
        else current_env
    )
    environment_changed = bool(
        managed_environment and merged_env != current_env
    )

    if previous == args.image and not environment_changed and args.noop_ok:
        print(f"No image change required for {args.application_id}: {args.image}")
    else:
        before = {
            shared.record_id(record)
            for record in list_application_deployments(args.application_id)
        }
        update_payload = {
            "applicationId": args.application_id,
            "dockerImage": args.image,
        }
        if managed_environment:
            update_payload["env"] = merged_env
        shared.request_json(
            "POST",
            "application.update",
            payload=update_payload,
        )
        trigger = shared.request_json(
            "POST",
            "application.deploy",
            payload={
                "applicationId": args.application_id,
                "title": args.title,
                "description": args.description,
            },
        )
        deployment_id = shared.find_key(trigger, "deploymentId")
        wait_application_deployment(
            args.application_id,
            before,
            str(deployment_id) if deployment_id is not None else "",
            args.timeout,
        )

    shared.wait_health(
        args.health_url,
        args.timeout,
        expected_version=args.expected_version,
    )
    observed = shared.current_image(args.application_id)
    if observed != args.image:
        raise DokployError(
            f"Dokploy application {args.application_id} reports {observed}, expected {args.image}"
        )
    print(f"PASS: Dokploy application image is exactly {observed}")
    verify_datadog_identity(args.application_id, identity)
    verify_datadog_runtime_security(args.application_id, runtime_security)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--title", default="Immutable Swarm image deployment")
    parser.add_argument("--description", default="Managed by GitHub Actions")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--expected-version", default="")
    parser.add_argument("--dd-service", default="")
    parser.add_argument("--dd-env", default="")
    parser.add_argument("--dd-version", default="")
    parser.add_argument("--dd-agent-host", default="")
    parser.add_argument("--dd-trace-agent-port", type=int, default=0)
    parser.add_argument("--dd-runtime-sca", action="store_true")
    parser.add_argument("--noop-ok", action="store_true")
    return parser


def main() -> int:
    try:
        deploy(build_parser().parse_args())
        return 0
    except DokployError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
