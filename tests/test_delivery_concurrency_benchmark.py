"""Delivery concurrency benchmark smoke tests."""

from __future__ import annotations


def test_delivery_concurrency_benchmark_smoke():
    from scripts.benchmark_delivery_concurrency import run_delivery_benchmark

    result = run_delivery_benchmark(
        events=10,
        destinations=3,
        global_limit=8,
        per_destination_limit=2,
        delay_ms=2,
        slow_delay_ms=10,
        retry_delay_ms=1,
    )

    assert result["events"] == 10
    assert result["expected_deliveries"] == 30
    assert result["delivered"] == 30
    assert result["failed"] == 0
    assert result["lost_deliveries"] == 0
    assert result["duplicate_deliveries"] == 0
    assert result["max_active_global"] <= 8
    assert result["max_active_per_destination"] <= 2
    assert result["events_per_second"] > 0
    assert result["deliveries_per_second"] > 0



def test_delivery_concurrency_uses_tuned_defaults():
    from storage.delivery_concurrency import DeliveryConcurrencyController

    controller = DeliveryConcurrencyController()
    try:
        assert controller.global_limit == 40
        assert controller.per_destination_limit == 8
    finally:
        controller.shutdown()


def test_delivery_benchmark_uses_tuned_defaults():
    from scripts.benchmark_delivery_concurrency import run_delivery_benchmark

    result = run_delivery_benchmark(
        events=1,
        destinations=1,
        delay_ms=0,
        slow_delay_ms=0,
        retry_delay_ms=0,
    )

    assert result["global_limit"] == 40
    assert result["per_destination_limit"] == 8


def test_teams_render_benchmark_measures_modern_and_classic():
    from scripts.benchmark_delivery_concurrency import run_teams_render_benchmark

    result = run_teams_render_benchmark(iterations=20)

    assert result["modern"]["iterations"] == 20
    assert result["classic"]["iterations"] == 20
    assert result["modern"]["renders_per_second"] > 0
    assert result["classic"]["renders_per_second"] > 0
    assert result["modern"]["p95_ms"] >= 0
    assert result["classic"]["p95_ms"] >= 0
