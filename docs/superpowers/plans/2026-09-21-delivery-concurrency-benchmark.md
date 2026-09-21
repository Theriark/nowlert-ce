# Delivery Concurrency and Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace sequential destination fan-out and globally serialized database connections with bounded concurrent delivery, then benchmark event throughput and Modern/Classic rendering.

**Architecture:** Add a process-wide fair delivery scheduler with a 32-job global limit and 4-job per-destination limit. PlatformDeliveryService submits every candidate to that controller and aggregates Futures; Database replaces its connection-long maintenance RLock with an exclusive-maintenance/concurrent-connection gate. A benchmark script exercises delivery and Teams card-rendering paths.

**Tech Stack:** Python 3.13 standard library ThreadPoolExecutor/Future/Condition, SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-09-21-delivery-concurrency-benchmark-design.md`

## Global Constraints

- One shared delivery engine for Modern and Classic.
- Default global active-delivery limit is 32.
- Default per-destination active-delivery limit is 4.
- Ordering is not guaranteed.
- Existing synchronous request/summary semantics remain.
- Retry delays and destination HTTP timeouts remain unchanged.
- No WAL change.
- Maintenance/backup/restore and SecretStore contracts must remain valid.
- No card formatter changes.

## Review Focus

- Many jobs queued for one slow destination must not consume all global worker threads and starve another destination.
- A maintenance waiter must eventually acquire exclusivity even while normal traffic continues opening connections.
- SecretStore.resolve() opens a database connection from inside database.maintenance(); that reentrant owner path must not deadlock.
- Exceptions raised by a delivery Future must remain converted to safe failed delivery outcomes rather than escape the event handler.
- Controller shutdown/test isolation must not leave non-daemon executor work hanging at interpreter exit.

---

### Task 1: Make normal database connections concurrent while preserving exclusive maintenance

**Files:**
- Modify: `src/storage/database.py`
- Modify: `tests/test_state_database.py`
- Modify: `tests/test_platform_portability.py`

**Interfaces:**
- `Database.connect()` remains the public context manager.
- `Database.maintenance()` remains the public exclusive context manager.
- No caller API changes.

- [ ] Add `test_database_allows_two_normal_connections_to_overlap` using Events: hold one connection open in thread A, verify thread B enters a second connection before A releases it. Current code must fail because the RLock serializes them.
- [ ] Add `test_database_maintenance_waits_for_active_connection_then_blocks_new_connections`: hold a normal connection, start maintenance, verify maintenance waits; once maintenance is waiting, start a third connection and verify it does not overtake maintenance.
- [ ] Add `test_database_maintenance_owner_can_open_nested_connection` and nested-maintenance coverage.
- [ ] Run the focused tests and observe RED.
- [ ] Replace `_maintenance_lock` with a Condition-backed gate tracking active connections, per-thread connection counts, maintenance owner/depth, and maintenance waiters. Give waiting maintenance writer preference. Keep a small path/file-mode lock around filesystem preparation/chmod.
- [ ] Run focused database/portability/secret tests and observe GREEN.

### Task 2: Add bounded fair delivery concurrency and concurrent fan-out

**Files:**
- Create: `src/storage/delivery_concurrency.py`
- Modify: `src/storage/delivery.py`
- Modify: `tests/test_platform_delivery.py`
- Modify: `tests/test_filtering.py` only if an existing filtered-delivery assertion depends on sequential ordering.

**Interfaces:**
- Create `DeliveryConcurrencyController(global_limit=32, per_destination_limit=4, maximum_pending=4096)`.
- `submit(destination_id: str, function: Callable, *args, **kwargs) -> Future`.
- `snapshot() -> DeliveryConcurrencySnapshot` with active/pending totals and observed maxima.
- `shutdown(wait=True)` for isolated tests.
- Create lazy process-wide `default_delivery_concurrency()`.
- Add optional `concurrency: DeliveryConcurrencyController | None = None` to `PlatformDeliveryService.__init__`.

- [ ] Add a two-destination regression where destination A blocks on an Event and destination B must start before A is released. Current sequential fan-out must fail.
- [ ] Add a multi-event regression using one destination and an injected controller with per-destination limit 2; verify max active for that destination is exactly 2 even with 8 simultaneous event threads.
- [ ] Add a global-limit regression with multiple destination ids and verify max active never exceeds an injected global limit of 3.
- [ ] Add a fairness regression: queue more than the per-destination limit for slow destination A, then submit fast destination B and verify B starts without waiting for A's backlog to drain.
- [ ] Add retry isolation: one delivery sleeps/retries while another destination completes before the retry is released.
- [ ] Run focused tests and observe RED.
- [ ] Implement a fair scheduler using one ThreadPoolExecutor(max_workers=global_limit), per-destination deques, round-robin ready destination ids, active counters, and outer Futures. Pending jobs must not occupy worker threads until both a global slot and destination slot are available.
- [ ] Change `_deliver_candidates` to submit all candidates first, then aggregate each Future's `(outcome, attempts)`. Generate one delivery_id per candidate exactly as before.
- [ ] Preserve safe failure handling if a future unexpectedly raises: count it failed and record/return the normal safe delivery failure path rather than crashing the request.
- [ ] Run all delivery/filtering/history tests and observe GREEN.

### Task 3: Add repeatable throughput and Modern/Classic render benchmark

**Files:**
- Create: `scripts/benchmark_delivery_concurrency.py`
- Create: `tests/test_delivery_concurrency_benchmark.py`

**Interfaces:**
- CLI accepts `--events`, `--destinations`, `--global-limit`, `--per-destination-limit`, `--delay-ms`, `--slow-delay-ms`, `--retry-delay-ms`, and `--render-iterations`.
- Expose pure helpers `run_delivery_benchmark(...)->dict` and `run_teams_render_benchmark(...)->dict` for smoke tests.
- JSON output includes elapsed, throughput, p50/p95/p99, max concurrency, delivery counts, and render Modern/Classic metrics.

- [ ] Add a smoke test for `run_delivery_benchmark(events=10, destinations=3, global_limit=8, per_destination_limit=2, delay_ms=2, slow_delay_ms=10)`; assert expected delivery count, zero duplicates/loss, and measured max concurrency stays within limits.
- [ ] Add a render smoke test with both Teams styles and assert both complete the requested iteration count.
- [ ] Run tests and observe RED because benchmark helpers do not exist.
- [ ] Implement the benchmark with a temporary real Nowlert Database/Route/Destination/DeliveryHistory setup and synthetic adapters. Launch event deliveries with a barrier so event requests start together.
- [ ] Implement percentile calculation without third-party packages.
- [ ] Add an optional quick matrix invoked by `--matrix`: events 1/5/10/25/50 at default 32/4 plus a limit sweep 8/16/32/64 x 1/2/4/8.
- [ ] Print one compact JSON document suitable for CI/log comparison.
- [ ] Run benchmark smoke tests GREEN.

### Task 4: Documentation, full verification, CI benchmark evidence, merge

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/platform-outputs.md`
- Include spec and this plan in their docs paths on the implementation branch.

- [ ] Document bounded concurrent delivery: 32 global, 4 per destination, no ordering guarantee, Modern/Classic shared scheduler.
- [ ] Document that synchronous ingress semantics remain in this phase.
- [ ] Add changelog entry.
- [ ] Push one implementation candidate to a dedicated branch and open a PR to `development`.
- [ ] Wait for exact-head CI. If red, debug only concrete failures and push the minimum corrective commit.
- [ ] From the green CI test logs, record the benchmark smoke metrics. If CI logs do not expose benchmark output, run the exact benchmark command on the Development host using the connector/CLI fallback rather than inventing numbers.
- [ ] Whole-branch review: no card formatter changes, no timeout/retry changes, no WAL change, no loss/duplicate regression.
- [ ] Squash merge green PR to `development`.
- [ ] Verify exact post-merge CI and CE Development deployment are green.
