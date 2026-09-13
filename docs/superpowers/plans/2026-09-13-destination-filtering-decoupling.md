# Destination Filtering Decoupling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Nowlert CE notification filtering out of Routes into destination+integration policies with an independent Filtering WebUI and runtime filter engine.

**Architecture:** Keep current route selection, priority, fallback, input matching, and destination de-duplication intact. RouteStore selects candidate destination routes without evaluating route filters; DestinationFilterStore then evaluates a destination+canonical-source policy before delivery. Available integrations for the Filtering UI are derived server-side from enabled routes targeting the selected destination; filter records never contain route IDs.

**Tech Stack:** Python 3, SQLite migrations/storage, existing Nowlert Platform API, vanilla JavaScript WebUI, pytest/GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-destination-filtering-decoupling-design.md` (approved 2026-09-13)

## Global Constraints

- Base exactly current `development` SHA before implementation.
- Work only on a dedicated feature branch.
- Produce one atomic implementation commit before opening the PR/triggering PR CI.
- Do not redesign route acquisition, priority, fallback, destination model, or release workflows.
- Filtering is keyed only by `destination_id + canonical source`; never route ID.
- The server determines destination-available integrations from enabled routes.
- All enum values selected or none selected means no restriction.
- Only declared normalized parser fields may be exposed to the UI.
- Preserve legacy route-filter semantics by migrating to destination policies as OR clauses before clearing route `filters_json`.

---

### Task 1: Shared integration filtering catalogue

**Files:**
- Create: `src/integrations/filtering.py`
- Test: `tests/test_destination_filtering.py`

- [ ] Define per-integration schemas for all 15 built-in integrations with enum values sourced from the existing integration catalogue and safe normalized field candidate paths.
- [ ] Add helpers to canonicalize/serialize schemas and extract available built-in sources for a route input type.
- [ ] Add tests proving every built-in integration has a schema and no undeclared/raw arbitrary metadata surface is exposed.

### Task 2: Destination filter persistence, migration, and matching

**Files:**
- Create: `src/storage/filtering.py`
- Modify: `src/storage/migrations.py`
- Test: `tests/test_destination_filtering.py`

- [ ] Add schema migration 11 creating `destination_filters(destination_id, source, clauses_json, created_at, updated_at)` with destination FK cascade and lookup index.
- [ ] Implement `DestinationFilterStore` read/write/clear/list, server-side available integration discovery, enum/text normalization, pattern matching, dormant-policy retention, and audit events.
- [ ] Implement idempotent legacy migration: group non-empty route filters by destination+canonical source, expand wildcard routes by compatible input type, store clauses as OR, then clear route filters in the same transaction.
- [ ] Add `RoutingOnlyRouteStore` as a compatibility subclass: source/input matching remains routing-only at runtime and new create/update operations persist `{}` without changing the legacy `RouteStore` contract used by older tests/tools.
- [ ] Add tests for migration equivalence, all/none/subset semantics, text patterns, available sources, disabled routes, wildcard expansion, unavailable-source rejection, and schema version 11.

### Task 3: Runtime delivery integration

**Files:**
- Extend: `src/storage/filtering.py`
- Modify: `src/storage/routing_bridge.py`
- Test: `tests/test_destination_filtering.py`

- [ ] Add a filtered delivery service that evaluates destination policy after route candidate selection and before transport delivery.
- [ ] Treat intentional filter suppression as handled rather than transport failure while preserving real failure counts.
- [ ] Wire the routing bridge to one shared filter store and filtered delivery service.
- [ ] Add delivery tests proving rejected events do not call destination adapters and allowed events do.

### Task 4: Filtering Platform API and route API decoupling

**Files:**
- Create: `src/api/filtering.py`
- Modify: `src/api/service.py`
- Test: `tests/test_destination_filtering.py`

- [ ] Subclass the current Platform API, initialize DestinationFilterStore/filtered delivery, and expose authenticated `/api/v2/filters` resources.
- [ ] GET list returns configured destination policies; GET destination returns only currently available integrations with schema and saved policy state.
- [ ] PUT one destination+source upserts/replaces one UI clause; DELETE clears source or whole destination policies.
- [ ] Reject writes to integrations not currently reachable to the destination.
- [ ] Strip/deprecate route filters from route API writes and serialization while keeping source/input/destination/priority/enabled behavior.
- [ ] Add permission/audit/API contract tests.

### Task 5: Approved Filtering WebUI

**Files:**
- Create: `src/webui/filtering.js`
- Create: `src/webui/filtering.css`
- Modify: `src/webui/service.py` to serve and inject the Filtering extension after existing WebUI scripts/styles.
- Test: `tests/test_destination_filtering.py`

- [ ] Inject top-level Filtering navigation and API-access-style management view.
- [ ] New filter selects destination first; then fetch server-computed available integrations for that destination only.
- [ ] Integration list has Configure actions; configuring one integration renders only that integration's fields.
- [ ] Render enum fields as selectable chips and optional declared text/pattern fields through Add field.
- [ ] All or zero enum selections serialize as unrestricted; subset/text restrictions show Configured.
- [ ] Hide/remove route filter fieldset and Filters column; route form submits no filters.
- [ ] Load/render/refresh destination filter policies and mutation controls only for admins, preserving read visibility.

### Task 6: Regression coverage and atomic validation

**Files:**
- Update any tests that assert schema 10 or route-filter WebUI behavior.
- Add approved spec and this implementation plan under `docs/superpowers/` in the same atomic feature commit.

- [ ] Verify new tests cover every acceptance criterion from the approved design.
- [ ] Verify Python syntax and WebUI JS syntax by CI.
- [ ] Verify existing routing priority/fallback/deduplication tests remain unchanged and green.
- [ ] Create one tree and one commit containing the complete intended feature.
- [ ] Update feature branch ref once, open PR to `development`, and wait for CI.
- [ ] If red, inspect exact failure, change only the failing issue, push one corrective commit, and wait again.
- [ ] Merge only after green and verify development push CI plus Development image deployment.
