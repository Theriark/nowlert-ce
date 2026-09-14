# Independent Routes and Destination Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Routes independent reusable traffic definitions and move one-to-many/many-to-many Route assignment into Destinations without breaking existing deliveries during the schema 11 -> 12 cutover.

**Architecture:** Replace `routes.destination_id` with a normalized `route_destinations(route_id, destination_id)` junction table. `RouteStore` matches traffic only; `RouteDestinationStore` resolves matched Routes into deterministic Destination candidates; Destination Filtering and delivery consume those candidates. Destination POST/PATCH owns `route_ids`; Route POST/PATCH no longer requires a Destination, while legacy singular `destination_id` requests remain temporarily compatible.

**Tech Stack:** Python 3.13, SQLite, pytest, vanilla JavaScript/HTML/CSS WebUI, existing `/api/v2` platform API, GitHub Actions/Docker.

**Spec:** `docs/superpowers/specs/2026-09-14-route-destination-many-to-many-design.md`

## Global Constraints

- Preserve all existing Route IDs, Destination IDs, Destination Filter policies, Delivery History IDs, priorities, enabled states, ownership, and current delivery topology through migration.
- Preserve dedicated-route-vs-wildcard fallback behavior.
- Preserve at-most-one delivery per Destination when several matched Routes reach the same Destination.
- Allow one matched Route to deliver once to every enabled bound Destination.
- Destination Filtering remains keyed by `destination_id + source`; relationship changes never delete saved filter rules.
- Destination Add/Edit is the only WebUI surface that mutates Route assignments.
- New Destinations start with zero selected Routes; all eligible Routes are automatically available to choose.
- Do not modify Stage/Production promotion workflows.
- Do not add integrations or output types.
- Do not make unrelated refactors.
- Development workflow constraint: all implementation work is squashed/assembled into **one coherent atomic implementation commit** before opening the PR; only that commit triggers the PR CI run.

---

## File Structure

**Create**
- `src/storage/route_destinations.py` — relationship persistence, permission validation, candidate expansion, assignment replacement.
- `tests/test_route_destination_relationships.py` — focused schema/store/runtime relationship acceptance tests.
- `tests/test_route_destination_webui.py` — static/UI contract tests for Destination selector and Route UI simplification.

**Modify**
- `src/storage/migrations.py` — schema 12 rebuild + relationship seeding.
- `src/storage/routes.py` — independent `Route` model and matching.
- `src/storage/delivery.py` — candidate-based delivery/history recording.
- `src/storage/filtering.py` — relationship-based availability and filter runtime.
- `src/storage/configuration_sync.py` — independent Route CRUD plus legacy YAML/API compatibility.
- `src/storage/destinations.py` — shared/private validation against relationship table where required.
- `src/storage/health.py` — relationship-aware health checks.
- `src/storage/portability.py` — `route_refs` export/import plus legacy `destination_ref` compatibility.
- `src/api/platform.py` — API serialization/input contracts for independent Routes and Destination `route_ids`.
- `src/webui/index.html` — Destination Routes selector shell and Routes table/dialog copy/columns.
- `src/webui/app.js` — selector state, destination save/load, Route UI, dashboard flow.
- `src/webui/styles.css` and/or existing active WebUI override CSS — compact searchable selector styling only if needed.
- Existing tests that explicitly assert singular `route.destination_id` — update to relationship semantics without weakening coverage.

---

### Task 1: Schema 12 and relationship store

**Files:**
- Modify: `src/storage/migrations.py`
- Create: `src/storage/route_destinations.py`
- Create: `tests/test_route_destination_relationships.py`
- Modify: `tests/test_state_database.py`

**Interfaces:**
- Produces `RouteDestinationCandidate(route: Route, destination_id: str)`.
- Produces `RouteDestinationStore(database, audit=None, clock=time.time)` with:
  - `route_ids_for_destination(actor, destination_id) -> tuple[str, ...]`
  - `destination_ids_for_route(actor, route_id) -> tuple[str, ...]`
  - `replace_for_destination(actor, destination_id, route_ids) -> tuple[str, ...]`
  - `expand(actor, routes) -> list[RouteDestinationCandidate]`
- Schema 12 creates `route_destinations` and removes physical `routes.destination_id` while preserving historical `delivery_attempts.destination_id`.

- [ ] **Step 1: Add migration tests that prove current topology survives 11 -> 12**

Create fixtures at schema 11 with two Routes, two Destinations, one delivery attempt, one destination filter, then assert after `Database.migrate()`:

```python
with database.connect() as connection:
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 12
    columns = {row[1] for row in connection.execute("PRAGMA table_info(routes)")}
    assert "destination_id" not in columns
    bindings = connection.execute(
        "SELECT route_id, destination_id FROM route_destinations ORDER BY route_id"
    ).fetchall()
    assert [(row[0], row[1]) for row in bindings] == expected_bindings
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
```

Also assert the pre-existing `delivery_attempts.route_id`, `delivery_attempts.destination_id`, and `destination_filters` row are unchanged.

- [ ] **Step 2: Run focused migration tests and verify RED**

Run:

```bash
python -m pytest -q tests/test_route_destination_relationships.py tests/test_state_database.py
```

Expected: failures because schema 12/table/store do not exist.

- [ ] **Step 3: Add migration 12**

Implement a transaction-safe SQLite rebuild in `src/storage/migrations.py`. The migration statements must:

```sql
CREATE TABLE route_destination_seed AS
SELECT id AS route_id, destination_id FROM routes;

CREATE TABLE routes_new (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    source TEXT NOT NULL,
    filters_json TEXT NOT NULL DEFAULT '{}',
    priority INTEGER NOT NULL DEFAULT 100,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    configuration_key TEXT,
    input_type TEXT NOT NULL DEFAULT '',
    UNIQUE (owner_user_id, name_normalized)
);
```

Copy all Route columns except `destination_id`. Rebuild `delivery_attempts` with its current complete column set so its foreign key points at `routes_new` after rename. Recreate current route/delivery indexes and the partial unique `routes_configuration_key` index. Then create:

```sql
CREATE TABLE route_destinations (
    route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    destination_id TEXT NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (route_id, destination_id)
);
CREATE INDEX route_destinations_destination
ON route_destinations(destination_id, route_id);
CREATE INDEX route_destinations_route
ON route_destinations(route_id, destination_id);
```

Seed from `route_destination_seed` using `unixepoch()` and drop the seed table.

- [ ] **Step 4: Implement `RouteDestinationStore`**

Create:

```python
@dataclass(frozen=True)
class RouteDestinationCandidate:
    route: Route
    destination_id: str
```

`replace_for_destination()` must validate the whole requested set before mutating:

```python
normalized = tuple(dict.fromkeys(str(item) for item in route_ids))
# destination must be writable
# every route must exist and be visible/eligible
# normal user: route.owner_user_id == actor.user_id
# binding is valid when route owner owns destination OR destination.shared
# then one transaction: delete existing bindings for destination, insert normalized
```

`expand()` must join only enabled Destinations, preserve Route input order, and de-duplicate by Destination ID:

```python
seen = set()
result = []
for route in routes:
    for destination_id in self._enabled_destination_ids(route.id):
        if destination_id in seen:
            continue
        seen.add(destination_id)
        result.append(RouteDestinationCandidate(route, destination_id))
return result
```

- [ ] **Step 5: Add relationship store tests**

Cover:

```python
assert store.replace_for_destination(admin, discord.id, [route_a.id, route_b.id]) == (
    route_a.id,
    route_b.id,
)
assert store.destination_ids_for_route(admin, route_a.id) == (discord.id,)
assert store.route_ids_for_destination(admin, discord.id) == (route_a.id, route_b.id)
```

Also prove invalid Route IDs do not partially replace the previous set, deleting Route cascades bindings, deleting Destination cascades bindings, and disabled Destination is omitted by `expand()` without deleting the binding.

- [ ] **Step 6: Run focused schema/store tests GREEN**

```bash
python -m pytest -q tests/test_route_destination_relationships.py tests/test_state_database.py
```

Expected: PASS.

---

### Task 2: Independent Route model and compatibility layer

**Files:**
- Modify: `src/storage/routes.py`
- Modify: `src/storage/configuration_sync.py`
- Modify: existing Route storage/configuration tests

**Interfaces:**
- `Route` no longer has `destination_id`.
- `RouteStore.create(actor, owner_user_id, name, source, *, input_type="", filters=None, priority=100, enabled=True) -> Route`.
- `RouteStore.update(..., destination_id=...)` no longer owns canonical relationship mutation.
- Configuration service may accept legacy singular `destination_id` and translate it to bindings using `RouteDestinationStore`.

- [ ] **Step 1: Write failing Route independence tests**

Add:

```python
route = routes.create(actor, actor.user_id, "XO HTTP", "xen_orchestra", input_type="http")
assert route.source == "xen_orchestra"
assert not hasattr(route, "destination_id")
assert relationships.destination_ids_for_route(actor, route.id) == ()
```

Add a matching test proving enabled Routes can match with zero Destinations, and wildcard fallback is unchanged.

- [ ] **Step 2: Run focused tests RED**

```bash
python -m pytest -q tests/test_route_destination_relationships.py tests/test_platform_resources.py tests/test_v240_integrations_and_routing.py
```

- [ ] **Step 3: Refactor `Route` and `RouteStore`**

Use:

```python
@dataclass(frozen=True)
class Route:
    id: str
    owner_user_id: str
    name: str
    source: str
    filters: dict[str, tuple[str, ...]]
    priority: int
    enabled: bool
    created_at: int
    updated_at: int
    input_type: str = ""
```

`RouteStore.matching()` queries only Routes/users and applies current source/input/filter compatibility plus existing dedicated-over-wildcard fallback. Remove destination joins and destination de-duplication from this layer.

`list_visible_safe()` must use `DISTINCT` and relationship joins only for the existing shared-Destination visibility case; own Routes remain visible even when unassigned.

- [ ] **Step 4: Convert configuration synchronization**

Instantiate/use `RouteDestinationStore` in `UnifiedConfigurationService`. Canonical `create_route()` no longer requires `destination_id`. Legacy YAML import still has output/target; import Route first, resolve imported Destination, then insert one binding.

Legacy API compatibility rule:

```python
legacy_destination_id = data.get("destination_id")
route = route_store.create(...)
if legacy_destination_id:
    relationships.replace_for_destination_for_route_compat(...)
```

For updates, singular `destination_id` is allowed only when current assignment count <= 1; if count > 1, raise a conflict/value error instead of erasing relationships.

- [ ] **Step 5: Run Route/configuration tests GREEN**

```bash
python -m pytest -q tests/test_route_destination_relationships.py tests/test_platform_resources.py tests/test_unified_configuration.py tests/test_v240_integrations_and_routing.py tests/test_v251_fallback_routing_webui.py
```

Expected: PASS.

---

### Task 3: Candidate-based delivery and Destination Filtering

**Files:**
- Modify: `src/storage/delivery.py`
- Modify: `src/storage/filtering.py`
- Modify: `src/storage/routing_bridge.py` if constructor wiring is required
- Modify/Create tests: `tests/test_platform_delivery.py`, `tests/test_route_destination_relationships.py`, Filtering tests

**Interfaces:**
- `RouteDestinationStore.expand(actor, matched_routes)` produces candidates.
- `DeliveryHistoryStore.record(..., route, destination_id, notification, ...)` receives Destination explicitly.
- `PlatformDeliveryService` receives `relationships: RouteDestinationStore`.

- [ ] **Step 1: Add failing runtime tests**

Prove one Route -> three Destinations yields three deliveries:

```python
relationships.replace_for_destination(admin, discord.id, [route.id])
relationships.replace_for_destination(admin, teams.id, [route.id])
relationships.replace_for_destination(admin, slack.id, [route.id])
summary = service.deliver(owner.actor, notification)
assert (summary.matched_routes, summary.delivered, summary.failed) == (3, 3, 0)
```

Prove two matched Routes -> same Destination yields one delivery and winning history `route_id` is the first Route under priority/name order.

Prove disabling Route or Destination stops delivery but preserves the binding.

- [ ] **Step 2: Run runtime tests RED**

```bash
python -m pytest -q tests/test_platform_delivery.py tests/test_route_destination_relationships.py
```

- [ ] **Step 3: Convert delivery to explicit candidates**

`PlatformDeliveryService.deliver()` becomes:

```python
routes = self.routes.matching(actor, actor.user_id, notification)
candidates = self.relationships.expand(actor, routes)
for candidate in candidates:
    delivery_id = uuid.uuid4().hex
    outcome, count = self._deliver_candidate(actor, candidate, notification, delivery_id)
```

`_deliver_candidate()` resolves `candidate.destination_id`. `DeliveryHistoryStore.record()` inserts `route.id` and the explicit `destination_id`.

Keep `DeliverySummary.matched_routes` field name for public response compatibility, but set its value to `len(candidates)` after expansion/deduplication.

- [ ] **Step 4: Convert Filtering availability/runtime**

`DestinationFilterStore.available_sources()` queries:

```sql
SELECT routes.source, routes.input_type
FROM route_destinations
JOIN routes ON routes.id = route_destinations.route_id
JOIN users ON users.id = routes.owner_user_id
WHERE route_destinations.destination_id = ?
  AND routes.enabled = 1
  AND users.enabled = 1
ORDER BY routes.priority, routes.name_normalized
```

`migrate_legacy_route_filters()` loads all bound Destination IDs for each pending Route and writes the normalized clauses to each `(destination_id, source)` policy before clearing `filters_json`.

`FilteredPlatformDeliveryService` filters resolved candidates by `candidate.destination_id`, not `route.destination_id`.

- [ ] **Step 5: Run delivery + filtering tests GREEN**

```bash
python -m pytest -q tests/test_platform_delivery.py tests/test_route_destination_relationships.py tests/test_destination_filtering.py tests/test_destination_filtering_toggle.py
```

Use actual existing Filtering test filenames if they differ; include every test module containing `DestinationFilterStore` or `FilteredPlatformDeliveryService`.

Expected: PASS.

---

### Task 4: API and Destination-owned relationship mutation

**Files:**
- Modify: `src/api/platform.py`
- Modify: `src/storage/configuration_sync.py`
- Modify: `src/storage/destinations.py`
- Modify: API/resource tests

**Interfaces:**
- Route JSON adds `destination_ids: list[str]`, `destination_count: int`; canonical Route write does not require `destination_id`.
- Destination JSON adds `route_ids: list[str]`.
- Destination POST/PATCH accepts optional `route_ids`.

- [ ] **Step 1: Add failing API tests**

Assert Route POST without Destination succeeds:

```python
response = api("POST", "/routes", {
    "name": "XO HTTP",
    "source": "xen_orchestra",
    "input_type": "http",
    "priority": "normal",
    "enabled": True,
})
assert response.status == 201
assert response.body["destination_ids"] == []
assert response.body["destination_count"] == 0
```

Assert Destination PATCH atomically assigns two Routes:

```python
response = api("PATCH", f"/destinations/{destination.id}", {"route_ids": [route_a.id, route_b.id]})
assert response.status == 200
assert response.body["route_ids"] == [route_a.id, route_b.id]
```

Add invalid Route ID test proving original assignments remain untouched. Add legacy singular `destination_id` create compatibility and multi-bound update conflict test.

- [ ] **Step 2: Run API tests RED**

```bash
python -m pytest -q tests/test_platform_api.py tests/test_platform_api_http.py tests/test_platform_resources.py
```

- [ ] **Step 3: Update serializers and accepted fields**

Route serializer computes assignment metadata from `RouteDestinationStore`. Destination serializer computes sorted `route_ids`.

Route create/update accepted canonical fields omit Destination; retain legacy `destination_id` in accepted payload only for compatibility translation.

Destination create/update accepted fields include `route_ids`.

- [ ] **Step 4: Implement Destination save semantics**

Before write:

```python
requested_route_ids = data.get("route_ids", _UNSET)
if requested_route_ids is not _UNSET:
    relationships.validate_for_destination(actor, destination_id_or_owner_context, requested_route_ids)
```

For PATCH, preserve `original_bindings`, perform current Destination update, then `replace_for_destination()`. If binding replacement fails after Destination mutation, restore the original Destination snapshot and original binding set before raising. If `route_ids` omitted, leave bindings unchanged.

Destination delete no longer scans Routes for references; junction/filter foreign keys handle cleanup.

Changing shared -> private must query relationship rows and reject if any bound Route belongs to another owner.

- [ ] **Step 5: Run API/resource tests GREEN**

```bash
python -m pytest -q tests/test_platform_api.py tests/test_platform_api_http.py tests/test_platform_resources.py tests/test_unified_configuration.py
```

Expected: PASS.

---

### Task 5: Destination selector and Route WebUI simplification

**Files:**
- Modify: `src/webui/index.html`
- Modify: `src/webui/app.js`
- Modify: active WebUI CSS file(s) only as required
- Create: `tests/test_route_destination_webui.py`
- Update existing static WebUI tests if they assert old Route Destination UI

**Interfaces:**
- Destination form maintains selected Route IDs and submits `route_ids`.
- Route form no longer contains `route-destination`.
- Routes table uses read-only `Used by` count.

- [ ] **Step 1: Add failing WebUI contract tests**

Assert source contains:

```python
assert 'id="destination-routes"' in index
assert 'id="destination-route-search"' in index
assert 'data-action="destination-routes-select-all"' in index
assert 'data-action="destination-routes-clear"' in index
assert 'id="route-destination"' not in index
assert '<th>Used by</th>' in index
assert 'route_ids:' in app
assert 'destination_count' in app
```

Also assert the old copy `Connect integrations and inputs to destinations` is gone.

- [ ] **Step 2: Run WebUI contract test RED**

```bash
python -m pytest -q tests/test_route_destination_webui.py
```

- [ ] **Step 3: Add Destination Routes selector shell**

Place after Connection/presentation and before credentials:

```html
<section class="destination-routes-section">
  <div class="form-section-heading"><span>Routes</span></div>
  <p class="field-help">Select which routes may deliver notifications to this destination.</p>
  <div id="destination-routes" class="route-multiselect">
    <button id="destination-routes-toggle" type="button" class="select-like" aria-expanded="false">No routes selected</button>
    <div id="destination-routes-popover" class="route-multiselect-popover" hidden>
      <input id="destination-route-search" type="search" placeholder="Search routes">
      <div class="route-multiselect-actions">
        <button type="button" data-action="destination-routes-select-all">Select all</button>
        <button type="button" data-action="destination-routes-clear">Clear</button>
      </div>
      <div id="destination-route-options"></div>
    </div>
  </div>
</section>
```

- [ ] **Step 4: Implement selector state/rendering in `app.js`**

Maintain a `Set` for the currently edited Destination, initialized from `destination.route_ids || []`. Filter available options by search text. Each row shows Route name, friendly source/integration, input, priority, and status badge. Disabled Routes remain selectable.

Closed summary:

```javascript
function destinationRouteSummary(count) {
  if (!count) return "No routes selected";
  return count === 1 ? "1 route selected" : `${count} routes selected`;
}
```

Destination save sends:

```javascript
route_ids: [...selectedDestinationRouteIds],
```

- [ ] **Step 5: Simplify Routes page**

Remove Destination selector from Route dialog and save payload. Routes table header becomes `Used by`; row rendering uses:

```javascript
const count = Number(item.destination_count || 0);
const usedBy = count === 0 ? "Unassigned" : count === 1 ? "1 destination" : `${count} destinations`;
```

Change page copy to: `Define which integration and input traffic qualifies for delivery.`

- [ ] **Step 6: Run WebUI tests and JavaScript syntax GREEN**

```bash
python -m pytest -q tests/test_route_destination_webui.py tests/test_webui_*.py
node --check src/webui/app.js
```

Expected: PASS.

---

### Task 6: Dashboard, health, portability, and compatibility surfaces

**Files:**
- Modify: `src/webui/app.js`
- Modify: `src/storage/health.py`
- Modify: `src/storage/portability.py`
- Modify: related dashboard/health/portability tests

**Interfaces:**
- Dashboard flow uses `route.destination_ids` or Destination `route_ids` to render one edge per active relationship.
- Safe JSON exports Destination `route_refs`; old Route `destination_ref` remains importable.

- [ ] **Step 1: Add failing dashboard/health/portability tests**

Portability new-format assertion:

```python
exported = export_safe_json(...)
assert "destination_ref" not in exported_route
assert exported_destination["route_refs"] == [expected_route_ref]
```

Legacy import fixture still contains Route `destination_ref` and must preview/import successfully into a relationship.

Health test proves an unassigned enabled Route is not unhealthy. A binding to a disabled Destination must retain existing warning semantics if the current health contract treats that as unhealthy.

- [ ] **Step 2: Run focused tests RED**

```bash
python -m pytest -q tests/test_portability.py tests/test_health.py tests/test_dashboard_webui.py
```

Use actual existing module names discovered in the repo; include all tests referencing `destination_ref`, `route.destination_id`, dashboard flow, or route health.

- [ ] **Step 3: Convert dashboard flow**

Replace singular lookup:

```javascript
for (const route of state.routes) {
  for (const destinationId of (route.destination_ids || [])) {
    const destination = state.destinations.find((item) => item.id === destinationId);
    // render the existing source -> route -> destination flow entry
  }
}
```

No flow edge for unassigned Routes.

- [ ] **Step 4: Convert health queries**

Replace direct `routes.destination_id` joins with `route_destinations JOIN destinations`. Do not treat a Route with zero relationship rows as invalid.

- [ ] **Step 5: Convert portability**

Export independent Routes first. Export each Destination with `route_refs` derived from relationship rows. Import resolves/creates Routes and Destinations, validates every relationship reference during preview, then writes relationships after resources exist.

Backward compatibility path:

```python
legacy_ref = route_payload.get("destination_ref")
if legacy_ref:
    pending_relationships.append((route_ref, legacy_ref))
```

New-format `destination.route_refs` also appends pending relationships. Validate all refs before live mutation.

- [ ] **Step 6: Run focused tests GREEN**

```bash
python -m pytest -q tests/test_portability.py tests/test_health.py tests/test_dashboard_webui.py
```

Expected: PASS using actual module names.

---

### Task 7: Full regression verification and single atomic implementation commit

**Files:**
- All implementation/test files above
- Do not change unrelated workflows or release files

**Interfaces:**
- This task produces the final branch state only; no new runtime interfaces.

- [ ] **Step 1: Search for stale direct relationship assumptions**

Run repository searches and eliminate remaining runtime/UI dependencies on singular Route Destination ownership:

```bash
grep -R "route\.destination_id\|routes\.destination_id\|route-destination\|destination_ref" -n src tests \
  --exclude-dir='__pycache__'
```

Allowed remaining occurrences must be intentional compatibility/import tests or delivery-history fields, not canonical Route runtime logic.

- [ ] **Step 2: Run the full automated suite**

```bash
python -m pytest -q
```

Expected: all tests pass, zero failures.

- [ ] **Step 3: Run CI-equivalent syntax/config checks**

```bash
python -m compileall -q src scripts tools .github/scripts
node --check src/webui/app.js
node --check src/webui/filtering.js
python - <<'PY'
from pathlib import Path
import yaml
for name in (
    "config/config.example.yaml",
    "docker-compose.yml",
    "compose.production.yaml",
    ".github/workflows/ci.yml",
    ".github/workflows/promote-stage.yml",
    ".github/workflows/finalize-release.yml",
):
    value = yaml.safe_load(Path(name).read_text(encoding="utf-8"))
    assert isinstance(value, dict), name
    print("validated", name)
PY
docker compose -f compose.production.yaml config >/dev/null
docker build --tag nowlert:route-destination-ci .
```

Expected: every command exits 0.

- [ ] **Step 4: Verify migration integrity explicitly**

Run the schema 11 -> 12 focused test and confirm both checks are asserted:

```bash
python -m pytest -q tests/test_route_destination_relationships.py -k 'migration or foreign_key or integrity'
```

Expected: PASS.

- [ ] **Step 5: Verify the implementation diff is scoped**

```bash
git diff --stat development...HEAD
git diff --name-only development...HEAD
```

Confirm every changed file belongs to the approved spec and no Stage/Production workflow/release file is modified.

- [ ] **Step 6: Create one atomic implementation commit**

Do **not** commit per task. After all red/green cycles and full verification are complete, stage the complete implementation and create exactly one commit:

```bash
git add src tests
git commit -m "Decouple routes from destinations"
```

If docs generated during execution need to travel with the implementation, stage only the approved plan/spec files intentionally; do not pull unrelated design-branch history into the implementation branch.

- [ ] **Step 7: Open one PR against `development` and wait**

Open a PR titled `Decouple routes from destinations`. Do not push further changes while the first PR CI run is active. If CI is red, diagnose and fix only that failure, then wait for the replacement run to turn green. If green, merge to `development`.

- [ ] **Step 8: Verify post-merge Development deployment**

Confirm the `development` push workflow completes:

- tests;
- Python/WebUI syntax;
- YAML/Compose validation;
- production image build;
- Build and publish Development image;
- image version/owl verification;
- exact CE digest deployment;
- immutable Development result recording.

Only then report the feature deployed.
