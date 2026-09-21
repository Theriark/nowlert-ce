# Delivery Concurrency and Benchmark Design

## Goal

Make Nowlert continue delivering unrelated notifications and destinations while one delivery is slow or retrying, without creating separate delivery engines for Modern and Classic cards.

## Approved concurrency model

All destination styles share the same delivery concurrency engine. Modern and Classic are benchmarked separately for rendering cost, but there is no style-specific worker pool or quota.

Initial production limits:

- global active deliveries: 32
- active deliveries per destination: 4

These are bounded defaults, not claims of optimal values. The benchmark harness must support testing alternate limits including global 8/16/32/64 and per-destination 1/2/4/8.

Delivery ordering is not guaranteed. Fast later notifications may complete before an earlier slow notification.

## Delivery semantics

Within one event, matched destinations are dispatched concurrently instead of sequentially.

Across multiple events, delivery work can also progress concurrently. A slow or retrying destination must not block unrelated destinations or later notifications while concurrency capacity exists.

The existing synchronous API contract remains in this phase: the request returns after its own delivery summary is complete. A durable asynchronous queue and immediate-ack ingestion are a separate future phase.

Retries remain local to one delivery job. A retry sleep must occupy only that job's destination/global slot and must not serialize the rest of the delivery pipeline.

## Concurrency controller

Introduce one process-wide bounded delivery controller shared by platform/API routing services.

The controller must:

- accept jobs keyed by destination id;
- run at most 32 jobs globally;
- run at most 4 jobs for the same destination;
- queue excess work without occupying global worker threads;
- avoid head-of-line blocking where many queued jobs for one slow destination prevent other destination ids from running;
- return Futures so one event can aggregate its own delivery outcomes;
- expose lightweight counters/snapshot data for benchmarks/tests;
- use only Python standard library concurrency primitives.

The scheduler should use one global ThreadPoolExecutor and a fair per-destination pending queue rather than one executor per destination, so destinations created/deleted over time do not leak worker pools.

## Database concurrency

The current Database.connect() holds the maintenance lock for the entire connection lifetime, serializing independent request/delivery threads.

Replace this with a maintenance-aware read gate:

- multiple normal database connections may coexist;
- maintenance remains exclusive;
- once maintenance is waiting, new normal connections should stop entering so maintenance cannot starve;
- a maintenance owner may open nested database connections;
- nested maintenance by the same thread remains valid;
- existing backup/restore, portability, and SecretStore maintenance contracts remain valid;
- SQLite busy_timeout continues to bound write contention.

Do not enable WAL in this phase. The existing backup/restore model is built around the main database file and WAL would require a separate consistency review. Benchmark first with concurrent short-lived connections and SQLite's existing busy timeout.

## Benchmarking

Add a repeatable benchmark harness covering two dimensions.

### Delivery concurrency

Synthetic events target real PlatformDeliveryService routing/destination objects with controllable adapter delays.

Report:

- event count
- destinations per event
- global limit
- per-destination limit
- total elapsed time
- events/sec
- deliveries/sec
- p50/p95/p99 event completion latency
- max observed global concurrency
- max observed per-destination concurrency
- delivered/failed/attempt count
- duplicate/lost delivery checks

Scenarios must include:

- 1, 5, 10, 25, and 50 simultaneous events;
- normal destinations;
- one deliberately slow destination;
- one retrying destination;
- mixed destinations.

### Card rendering

Benchmark Teams Modern and Teams Classic preview rendering separately using the same representative notification. Report renders/sec and p50/p95/p99 render latency.

Rendering differences are measured only; they do not change the shared delivery limits.

## Correctness gates

Tests must prove:

- two destinations of the same event can execute concurrently;
- a slow first destination cannot delay a fast second destination;
- per-destination concurrency never exceeds the configured limit;
- global concurrency never exceeds the configured limit;
- queued work from one destination does not starve another destination;
- multiple simultaneous events complete with no lost or duplicate deliveries;
- retries on one job do not serialize other jobs;
- normal database connections overlap;
- maintenance blocks new connections and waits for active connections;
- nested maintenance owner connections still work;
- existing delivery history, filtering, secret resolution, backup/restore, and ownership tests remain green.

## Non-goals

- No durable delivery queue in this phase.
- No immediate 202/204 response before delivery completion in this phase.
- No separate Modern/Classic worker pools.
- No change to destination HTTP timeouts or retry policy.
- No change to card formatters.
- No WAL migration in this phase.

## Acceptance

The change is ready when full CI is green, Development deployment is green, and benchmark output demonstrates that a slow delivery no longer serializes unrelated delivery work while configured global/per-destination limits are respected.
