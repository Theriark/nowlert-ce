# Nowlert CE — Independent Routes and Destination Route Assignment Design

Date: 2026-09-14
Target repository: `Theriark/nowlert-ce`
Target base: current `development` (`53d53d75e2a211f0b8555dabdedc31915954595d` at design time)

## Goal

Decouple Routes from Destinations so a Route is a reusable traffic definition and a Destination chooses one or more Routes that may deliver to it.

The target model is:

`notification -> matching route(s) -> route/destination bindings -> destination filter -> delivery`

A Route may exist with zero Destinations. One Route may feed several Destinations, and one Destination may select several Routes.

This removes the current extra workflow where a Route must be created specifically for one Destination and duplicated when identical traffic must be sent to several outputs.

## Current constraint being removed

Today `routes.destination_id` is mandatory in SQLite and in the `Route` model. Route creation validates one Destination, route matching joins directly to Destinations, delivery resolves `route.destination_id`, Add/Edit Route requires a Destination, dashboard flow assumes one Route -> one Destination, and Destination Filtering discovers available integrations through that same direct column.

The existing model therefore cannot represent an independent Route or one Route feeding multiple Destinations without duplication.

## Chosen architecture

Use a true many-to-many relationship with a junction table.

- `routes` owns Route identity and matching properties only.
- `destinations` owns output/channel configuration only.
- `route_destinations` owns the relationship between them.
- Destination Filtering stays keyed by `destination_id + source` and never becomes Route-owned again.

Rejected alternatives:

1. **Store route IDs as JSON inside each Destination.** Rejected because it loses foreign-key integrity, complicates deletes/imports, and makes relationship queries harder.
2. **Keep `routes.destination_id` and duplicate Routes per Destination.** Rejected because it preserves the unnecessary step and prevents Route reuse.

## Database migration

Advance the schema from version 11 to 12.

### New relationship table

Create:

```sql
CREATE TABLE route_destinations (
    route_id TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    destination_id TEXT NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (route_id, destination_id)
)
```

Create indexes for `destination_id, route_id` and `route_id, destination_id` lookup.

### Remove mandatory destination from Routes

The physical `routes.destination_id NOT NULL` dependency must be removed; otherwise an unassigned Route remains impossible.

Because `delivery_attempts.route_id` references `routes`, migration 12 must rebuild `routes` and `delivery_attempts` transactionally instead of dropping the column in place:

1. copy all current `(route_id, destination_id)` pairs into a temporary seed table;
2. create `routes_new` with every current Route column except `destination_id`;
3. copy every Route ID and all Route metadata unchanged;
4. create/copy `delivery_attempts_new`, preserving every historical `route_id` and `destination_id` value;
5. drop old `delivery_attempts`, then old `routes`;
6. rename the new tables to their canonical names;
7. recreate the current route/delivery indexes and Route `configuration_key` uniqueness constraint;
8. create `route_destinations` and seed one relationship for every former `routes.destination_id`;
9. verify foreign keys and database integrity in tests.

The existing `Database.migrate()` pre-migration database backup remains the safety net. No existing Route ID, Destination ID, Delivery History reference, Destination Filter policy, priority, enabled state, or ownership value may change.

Existing installations must therefore start after upgrade with the same delivery topology they had immediately before migration.

## Route domain model

`Route` becomes independent and no longer contains `destination_id`.

It retains its current owner, name, source, input type, priority, enabled state, timestamps/configuration key, and existing `filters_json` compatibility column until that legacy surface is removed separately.

Add `RouteDestinationStore`, responsible only for relationships. It must:

- list Route IDs assigned to one Destination;
- list Destination IDs assigned to one Route;
- replace all Route assignments for one Destination atomically;
- expand matched Routes into eligible Destination candidates;
- return assignment metadata for API/UI/health;
- enforce ownership/sharing rules;
- audit relationship changes.

`RouteStore` must not absorb Destination configuration responsibilities.

## Visibility, ownership, and permissions

Preserve the existing effective access model while moving it to the junction table:

- Route writes require the Route owner/admin according to current ownership rules;
- Destination writes require the Destination owner/admin according to current rules;
- a relationship is valid when the Route owner owns the Destination or the Destination is shared;
- a normal user may assign only Routes they own to a Destination they are allowed to edit;
- an administrator may manage any relationship that satisfies the ownership/shared rule;
- a non-admin Route listing may continue to include the user's own Routes plus readable Routes bound to shared Destinations, using `DISTINCT` relationship joins rather than `routes.destination_id`;
- changing a Destination from shared to private must be rejected while foreign-owner Route bindings still exist.

## Runtime matching and delivery

### Route matching

`RouteStore.matching()` stops joining Destinations. It returns enabled Route definitions that match the notification source/input and any still-supported legacy Route compatibility conditions, ordered by current priority/name semantics.

Preserve wildcard fallback exactly:

- if at least one dedicated source Route matches, wildcard Routes remain fallback-only and are excluded;
- wildcard Routes are selected only when no dedicated source Route matches.

### Route/Destination candidates

After Route matching, `RouteDestinationStore` resolves each selected Route through `route_destinations` to enabled Destinations.

Use an explicit immutable candidate value containing `route` and `destination_id`; do not mutate or clone a Route to inject a temporary destination.

If several matched Routes resolve to the same Destination, emit at most one candidate for that Destination. The first Route under existing priority/name order wins. This preserves deterministic duplicate suppression.

One Route assigned to Discord, Teams, and Slack therefore resolves to three candidates and may create three deliveries from one notification.

### Destination Filtering

Destination Filtering remains between candidate resolution and adapter delivery.

Every Filtering query that currently reads `routes.destination_id` moves to `route_destinations`:

- available integrations for a Destination come only from enabled Routes bound to that Destination;
- wildcard Route expansion continues using the integrations compatible with that Route's input type;
- a saved filter becomes dormant when its Route is unbound/disabled and becomes active again if that relationship returns;
- changing relationships never deletes saved filter rules;
- the filter decision remains keyed by Destination + integration source.

`DestinationFilterStore.migrate_legacy_route_filters()` must also stop requiring `routes.destination_id`. After schema 12, any still-pending legacy Route filter is migrated to every currently bound Destination for that Route before `filters_json` is cleared.

Runtime order is:

`notification -> matching Routes -> bound Destinations -> one candidate per Destination -> Destination Filter -> adapter delivery`

### Delivery history and summary

`DeliveryHistoryStore.record()` receives the actual `destination_id` from the candidate instead of reading it from the Route. History continues recording both Route ID and Destination ID.

Keep the public ingestion response shape stable. Existing `matched` continues to mean the number of resolved delivery candidates after relationship expansion and duplicate suppression, so its relationship to delivered/failed outcomes remains useful when one Route feeds multiple Destinations.

## Route CRUD/API

New Route create/update requests no longer require `destination_id`. All currently supported non-Destination Route fields remain unchanged.

Canonical Route responses include:

- all current Route definition fields except singular `destination_id`;
- `destination_ids`: an array of current assignments;
- `destination_count`: the length of that array.

Relationship mutation is not exposed from the Route WebUI.

For one compatibility window:

- legacy Route **create** may still send `destination_id`; the server creates the independent Route and one relationship;
- legacy Route **update** may send `destination_id` only when the Route currently has zero or one Destination assignment; it replaces that single assignment;
- if a legacy update sends `destination_id` for a Route already assigned to multiple Destinations, return a conflict rather than silently deleting relationships.

The new WebUI never sends singular `destination_id`.

In `platform_database_v1`, Route CRUD must stop constructing YAML route entries that require output/target. Legacy YAML import remains supported: each old route entry with output/target imports as one independent Route plus one `route_destinations` row.

## Destination CRUD/API

Destination create/edit is the canonical relationship-management surface.

Destination responses include `route_ids`, sorted deterministically.

Destination POST/PATCH accepts `route_ids` as a list of unique Route IDs. Before any state is changed, validate the complete list and permissions. Replacement is all-or-nothing.

Because current Destination configuration writes pass through the configuration synchronization layer while relationship rows live in SQLite, the service must provide application-level atomicity: preserve the original Destination snapshot and original binding set, validate first, and restore both before surfacing an error if either the Destination write or relationship replacement fails. A failed save must not leave a partially replaced assignment set.

Changing Destination type, name, credentials, or presentation does not change Route assignments unless `route_ids` is explicitly supplied.

Destination deletion no longer fails because a Route points to it. Deletion cascades only that Destination's relationship rows and Destination Filter rows; Route definitions remain.

Audit relationship replacement as `destination.routes_update`, recording Destination ID plus added/removed Route IDs and never secrets.

## Destination WebUI

Add a **Routes** section to Add/Edit Destination, after **Connection and presentation** and before **Write-only credentials**.

Use a custom searchable checkbox popover, not a native multi-select.

Closed state:

- label: **Routes**;
- summary: `No routes selected`, `1 route selected`, or `N routes selected`.

Open state:

- search field;
- **Select all** and **Clear** controls;
- one checkbox row per eligible Route;
- each row shows Route name, integration/source, input type, priority, and Enabled/Disabled badge.

Behavior:

- every eligible Route is automatically available as a choice;
- existing migrated relationships are preselected;
- a newly created Route automatically appears as an available choice on eligible Destinations without editing that Route;
- a new Destination starts with no Route selected;
- zero selected Routes is valid and means the Destination receives no routed notifications;
- disabled Routes may remain selected but do not deliver until enabled;
- saving the Destination sends the selected `route_ids` in the same Destination save operation.

The Destination WebUI is the only UI surface that mutates Route assignments.

## Routes WebUI

The Routes page becomes a traffic-definition page.

- remove the Destination selector from Add/Edit Route;
- change page copy so Routes describe which integration/input traffic qualifies rather than where it is sent;
- remove the current Destination column;
- add a read-only **Used by** column showing `Unassigned`, `1 destination`, or `N destinations` from `destination_count`;
- retain current Route name, integration/input, priority, enabled state, and any still-supported compatibility controls;
- an unassigned Route is valid and remains visible/editable.

No relationship checkbox/edit control appears on the Routes page.

## Dashboard and health

Dashboard Routing Flow must support one Route branching to several Destinations. Render one Route->Destination flow entry per active relationship. Unassigned Routes do not create a delivery edge.

Active Route metrics continue counting enabled Route definitions, whether currently assigned or not.

An unassigned Route is not a platform-health error. Health checks that currently join `routes.destination_id` move to `route_destinations` and continue detecting genuinely unavailable/disabled bound Destinations.

## Filtering UI compatibility

The current Filtering overview remains active-only and collapsed by default.

Configure Filtering continues to show integrations currently reachable to a Destination. "Reachable" now means an enabled Route is bound to that Destination through `route_destinations`.

No Filtering UI redesign is part of this task; only relationship lookup/runtime adaptation changes.

## Portability / backup / import

Database backups naturally include the new schema after migration.

Safe JSON/Data Tools uses Destination-owned relationship representation:

- exported Routes contain no `destination_ref`;
- each exported Destination includes `route_refs`, an array of portable Route references;
- import creates/validates Routes and Destinations first, then restores Destination `route_refs` atomically.

Backward compatibility:

- old exports where a Route contains singular `destination_ref` remain accepted;
- each old `destination_ref` is translated into one relationship during preview/import;
- invalid relationship references fail preview before live state is mutated;
- secret-redaction guarantees remain unchanged.

## Delete, disable, and edit semantics

- Delete Route -> cascade its relationship rows; Destinations remain.
- Delete Destination -> cascade its relationship rows and Destination Filters; Routes remain.
- Disable Route -> assignments remain stored but produce no candidates.
- Disable Destination -> assignments remain stored but produce no delivery.
- Re-enable either side -> stored relationships resume automatically.
- Rename Route/Destination -> relationships remain because IDs do not change.

## Test and acceptance contract

The implementation is complete only when automated tests prove:

1. schema 11 -> 12 migration preserves all Route IDs, Destination IDs, existing one-to-one assignments, Delivery History IDs, and Destination Filter policies;
2. fresh databases create independent Routes and the relationship table correctly;
3. migration leaves `PRAGMA foreign_key_check` and integrity checks clean;
4. a Route can be created with zero Destinations;
5. one Route can be assigned to multiple Destinations;
6. one Destination can select multiple Routes;
7. deleting a Destination leaves its Routes intact;
8. deleting a Route leaves Destinations intact;
9. assignment replacement is atomic and rejects invalid/private relationships;
10. changing shared -> private is rejected while foreign-owner bindings exist;
11. disabled Route/Destination assignments remain stored but do not deliver;
12. dedicated-vs-wildcard fallback behavior is unchanged;
13. several matched Routes reaching the same Destination produce at most one delivery to that Destination;
14. one matched Route assigned to several Destinations delivers once to each eligible Destination;
15. Destination Filtering availability derives from enabled relationship rows, including wildcard input expansion;
16. Destination Filtering is applied to each resolved candidate before delivery;
17. dormant filters survive unbinding/rebinding;
18. pending legacy Route filters migrate through relationship rows after schema 12 without losing clauses;
19. Delivery History records the winning Route ID and actual Destination ID;
20. Route API/WebUI no longer requires Destination selection;
21. Destination API/WebUI can read and atomically replace multiple Route assignments;
22. legacy singular `destination_id` API compatibility follows the explicit zero/one-vs-multiple rule above;
23. Dashboard flow renders one-to-many relationships;
24. safe JSON export/import round-trips `route_refs` and imports old `destination_ref` data;
25. the full existing automated test suite remains green;
26. Python syntax, WebUI JavaScript syntax, YAML/Compose validation, and production image build remain green.

## Cutover strategy

This is one functional cutover delivered in one implementation commit, but work inside that commit must be developed/tested in this order:

1. schema migration and `RouteDestinationStore`;
2. independent Route model and legacy import/Route-filter migration compatibility;
3. candidate expansion, duplicate suppression, delivery history, and Destination Filtering conversion;
4. Route/Destination API serialization and mutation conversion;
5. Destination Routes selector;
6. Routes UI simplification;
7. dashboard, health, and portability updates;
8. full migration/runtime/WebUI regression suite.

The final implementation follows the standing workflow: fresh implementation branch, one coherent atomic implementation commit, one PR CI run, no unrelated changes, merge only after green, then verify the normal CE Development deployment.

## Explicit non-goals

- Do not redesign Destination Filtering rules or presentation.
- Do not change notification parser/integration semantics.
- Do not change Route priority values or wildcard fallback policy.
- Do not add output types or integrations.
- Do not modify Stage/Production promotion workflows.
- Do not delete delivery/audit history.
- Do not automatically assign every Route to a new Destination; Routes are automatically **available to choose**, not automatically selected.
