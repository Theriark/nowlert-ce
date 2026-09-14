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

    if previous == args.image and args.noop_ok:
        print(f"No image change required for {args.application_id}: {args.image}")
    else:
        before = {
            shared.record_id(record)
            for record in list_application_deployments(args.application_id)
        }
        shared.request_json(
            "POST",
            "application.update",
            payload={"applicationId": args.application_id, "dockerImage": args.image},
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-id", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--title", default="Immutable Swarm image deployment")
    parser.add_argument("--description", default="Managed by GitHub Actions")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--expected-version", default="")
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
