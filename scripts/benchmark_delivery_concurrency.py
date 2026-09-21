#!/usr/bin/env python3
"""Benchmark bounded Nowlert delivery concurrency and Teams card rendering."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
import threading
import time

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from api.security import hash_password
from models import Notification
from outputs.platform import TeamsPlatformAdapter
from storage.database import Database
from storage.delivery import DeliveryHistoryStore, DeliveryResult, PlatformDeliveryService
from storage.delivery_concurrency import DeliveryConcurrencyController
from storage.destinations import Destination, DestinationStore
from storage.route_destinations import RouteDestinationStore
from storage.routes import RouteStore
from storage.secrets import SecretStore
from storage.users import UserStore


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _latency_stats(values: list[float]) -> dict:
    return {
        "p50_ms": round(_percentile(values, 0.50) * 1000, 3),
        "p95_ms": round(_percentile(values, 0.95) * 1000, 3),
        "p99_ms": round(_percentile(values, 0.99) * 1000, 3),
        "mean_ms": round(statistics.fmean(values) * 1000, 3) if values else 0.0,
    }


def _fast_hash(password: str) -> str:
    return hash_password(password, salt=b"\x05" * 16, iterations=1_000)


def run_delivery_benchmark(
    *,
    events: int = 25,
    destinations: int = 3,
    global_limit: int = 50,
    per_destination_limit: int = 10,
    delay_ms: float = 5,
    slow_delay_ms: float = 50,
    retry_delay_ms: float = 5,
) -> dict:
    events = max(1, int(events))
    destinations = max(1, int(destinations))
    delay = max(0.0, float(delay_ms)) / 1000
    slow_delay = max(delay, float(slow_delay_ms) / 1000)
    retry_delay = max(0.0, float(retry_delay_ms)) / 1000

    with tempfile.TemporaryDirectory(prefix="nowlert-delivery-benchmark-") as temporary:
        database = Database(Path(temporary) / "nowlert.db")
        database.migrate()
        users = UserStore(database, password_hasher=_fast_hash)
        owner = users.bootstrap_admin(
            "benchmark-admin",
            "correct horse battery staple",
        )
        destination_store = DestinationStore(database)
        route_store = RouteStore(database)
        relationships = RouteDestinationStore(database)
        secrets = SecretStore(database)
        history = DeliveryHistoryStore(database)

        route = route_store.create(
            owner.actor,
            owner.id,
            "benchmark route",
            "grafana",
        )
        created = []
        for index in range(destinations):
            role = "normal"
            if index == 0:
                role = "slow"
            elif index == 1 and destinations > 2:
                role = "retry"
            destination = destination_store.create(
                owner.actor,
                owner.id,
                f"{index:02d}-{role}",
                "webhook",
                settings={},
            )
            relationships.replace_for_destination(
                owner.actor,
                destination.id,
                [route.id],
            )
            created.append(destination)

        controller = DeliveryConcurrencyController(
            global_limit=global_limit,
            per_destination_limit=per_destination_limit,
            maximum_pending=max(4096, events * destinations * 2),
        )
        lock = threading.Lock()
        active_global = 0
        active_by_destination = defaultdict(int)
        max_active_global = 0
        max_active_by_destination = defaultdict(int)
        calls = defaultdict(int)
        successful_pairs: set[tuple[str, str]] = set()
        duplicate_deliveries = 0

        def adapter(target, _secret, notification):
            nonlocal active_global, max_active_global, duplicate_deliveries
            pair = (target.id, notification.title)
            with lock:
                calls[pair] += 1
                attempt = calls[pair]
                active_global += 1
                active_by_destination[target.id] += 1
                max_active_global = max(max_active_global, active_global)
                max_active_by_destination[target.id] = max(
                    max_active_by_destination[target.id],
                    active_by_destination[target.id],
                )
            try:
                if target.name.endswith("-slow"):
                    time.sleep(slow_delay)
                else:
                    time.sleep(delay)
                if target.name.endswith("-retry") and attempt == 1:
                    return DeliveryResult(
                        False,
                        retryable=True,
                        response_status=503,
                        error_code="synthetic_retry",
                    )
                with lock:
                    if pair in successful_pairs:
                        duplicate_deliveries += 1
                    successful_pairs.add(pair)
                return DeliveryResult(True, response_status=204)
            finally:
                with lock:
                    active_global -= 1
                    active_by_destination[target.id] -= 1

        service = PlatformDeliveryService(
            route_store,
            destination_store,
            secrets,
            history,
            {"webhook": adapter},
            relationships=relationships,
            maximum_attempts=2,
            retry_delays=(0, retry_delay),
            sleeper=time.sleep,
            concurrency=controller,
        )

        barrier = threading.Barrier(events + 1)
        event_latencies = [0.0] * events
        summaries = [None] * events

        def send(index: int):
            barrier.wait()
            started = time.perf_counter()
            summaries[index] = service.deliver(
                owner.actor,
                Notification(
                    source="grafana",
                    status="warning",
                    title=f"benchmark-event-{index:04d}",
                    body="Synthetic delivery concurrency benchmark.",
                    metadata={"severity": "warning"},
                ),
            )
            event_latencies[index] = time.perf_counter() - started

        started = time.perf_counter()
        with ThreadPoolExecutor(
            max_workers=events,
            thread_name_prefix="benchmark-event",
        ) as event_pool:
            futures = [event_pool.submit(send, index) for index in range(events)]
            barrier.wait()
            for future in futures:
                future.result()
        elapsed = time.perf_counter() - started
        snapshot = controller.snapshot()
        controller.shutdown()

        expected_deliveries = events * destinations
        delivered = sum(summary.delivered for summary in summaries if summary is not None)
        failed = sum(summary.failed for summary in summaries if summary is not None)
        attempts = sum(summary.attempts for summary in summaries if summary is not None)
        lost_deliveries = max(0, expected_deliveries - len(successful_pairs))

        result = {
            "events": events,
            "destinations": destinations,
            "global_limit": int(global_limit),
            "per_destination_limit": int(per_destination_limit),
            "elapsed_seconds": round(elapsed, 6),
            "events_per_second": round(events / elapsed, 3) if elapsed else 0.0,
            "deliveries_per_second": (
                round(expected_deliveries / elapsed, 3) if elapsed else 0.0
            ),
            "expected_deliveries": expected_deliveries,
            "delivered": delivered,
            "failed": failed,
            "attempts": attempts,
            "lost_deliveries": lost_deliveries,
            "duplicate_deliveries": duplicate_deliveries,
            "max_active_global": max(max_active_global, snapshot.max_active),
            "max_active_per_destination": max(
                [snapshot.max_active_per_destination, *max_active_by_destination.values()]
            ),
        }
        result.update(_latency_stats(event_latencies))
        return result


def _benchmark_notification() -> Notification:
    return Notification(
        source="xo",
        category="backup",
        status="success",
        title="Benchmark backup",
        body="Benchmark backup completed successfully.",
        job_name="Benchmark backup",
        job_id="benchmark-job",
        mode="full",
        repository="NFS | Benchmark | Repository-01",
        duration="5 min",
        transfer_size="52.06 GiB",
        transfer_speed="33.73 MiB/s",
        vm_total=3,
        vm_success=3,
        successful_vms=["VM-01", "VM-02", "VM-03"],
        vm_details={
            "VM-01": {"size": "18 GiB"},
            "VM-02": {"size": "12 GiB"},
            "VM-03": {"size": "22 GiB"},
        },
        metadata={
            "provider": "Xen Orchestra",
            "severity": "information",
            "host": "benchmark-xo",
        },
    )


def _teams_destination(style: str) -> Destination:
    return Destination(
        id=f"benchmark-{style}",
        owner_user_id="benchmark-owner",
        name=f"Benchmark Teams {style}",
        output_type="teams",
        settings={"message_style": style},
        shared=False,
        enabled=True,
        secret_configured=False,
        created_at=0,
        updated_at=0,
    )


def run_teams_render_benchmark(*, iterations: int = 500) -> dict:
    iterations = max(1, int(iterations))
    adapter = TeamsPlatformAdapter()
    notification = _benchmark_notification()
    result = {}
    for style in ("modern", "classic"):
        destination = _teams_destination(style)
        timings = []
        for _ in range(iterations):
            started = time.perf_counter()
            adapter.preview(destination, notification)
            timings.append(time.perf_counter() - started)
        elapsed = sum(timings)
        metrics = {
            "iterations": iterations,
            "elapsed_seconds": round(elapsed, 6),
            "renders_per_second": (
                round(iterations / elapsed, 3) if elapsed else 0.0
            ),
        }
        metrics.update(_latency_stats(timings))
        result[style] = metrics
    return result


def _matrix(args) -> dict:
    event_results = []
    for count in (1, 5, 10, 25, 50):
        event_results.append(
            run_delivery_benchmark(
                events=count,
                destinations=args.destinations,
                global_limit=args.global_limit,
                per_destination_limit=args.per_destination_limit,
                delay_ms=args.delay_ms,
                slow_delay_ms=args.slow_delay_ms,
                retry_delay_ms=args.retry_delay_ms,
            )
        )

    limit_results = []
    for global_limit in (8, 16, 32, 64):
        for per_destination_limit in (1, 2, 4, 8):
            limit_results.append(
                run_delivery_benchmark(
                    events=args.events,
                    destinations=args.destinations,
                    global_limit=global_limit,
                    per_destination_limit=per_destination_limit,
                    delay_ms=args.delay_ms,
                    slow_delay_ms=args.slow_delay_ms,
                    retry_delay_ms=args.retry_delay_ms,
                )
            )

    return {
        "event_matrix": event_results,
        "limit_matrix": limit_results,
        "teams_render": run_teams_render_benchmark(
            iterations=args.render_iterations
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=25)
    parser.add_argument("--destinations", type=int, default=3)
    parser.add_argument("--global-limit", type=int, default=50)
    parser.add_argument("--per-destination-limit", type=int, default=10)
    parser.add_argument("--delay-ms", type=float, default=5)
    parser.add_argument("--slow-delay-ms", type=float, default=50)
    parser.add_argument("--retry-delay-ms", type=float, default=5)
    parser.add_argument("--render-iterations", type=int, default=500)
    parser.add_argument("--matrix", action="store_true")
    args = parser.parse_args()

    if args.matrix:
        result = _matrix(args)
    else:
        result = {
            "delivery": run_delivery_benchmark(
                events=args.events,
                destinations=args.destinations,
                global_limit=args.global_limit,
                per_destination_limit=args.per_destination_limit,
                delay_ms=args.delay_ms,
                slow_delay_ms=args.slow_delay_ms,
                retry_delay_ms=args.retry_delay_ms,
            ),
            "teams_render": run_teams_render_benchmark(
                iterations=args.render_iterations
            ),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
