# Nowlert CE — Destination Filtering Decoupling Design

Date: 2026-09-13
Target repository: `Theriark/nowlert-ce`
Target base: current `development` (`3c0059e00accae755de09ee611975e61fce18403` at design time)

## Goal

Move notification filtering out of Routes into a standalone **Filtering** subsystem owned by Destinations, without changing the current route-selection behavior yet. This removes filtering as a blocker for a later routing redesign.

## User experience

### Filtering page

Add a top-level **Filtering** menu alongside Routes/API access. The page follows the existing API-access management style:

- page title **Filtering**;
- primary action **New filter**;
- table/list of destination filter policies;
- no wizard-step banners, architectural diagrams, or large instructional empty-state cards.

### Create filter

1. Click **New filter**.
2. Select one Destination.
3. Nowlert discovers the integrations currently enabled for that Destination.
4. Show **only those integrations**. Do not show unrelated catalogue integrations.
5. Each discovered integration has its own **Configure** action.
6. Clicking Configure opens only that integration's filter editor.
7. Save the integration filter, return to the integration list, then save the destination filter policy.

A Destination remains one output/channel. One Destination can receive several integrations, and each available integration can have its own independent filter configuration.

## Available-integration rule

The Filtering UI must never blindly list the complete integration catalogue.

For a selected Destination, derive available integrations from the current enabled routing relationships:

- include unique sources from **enabled routes** targeting that Destination;
- ignore disabled routes;
- dedicated routes expose only their own source;
- a wildcard/fallback route expands to built-in integrations compatible with that route's input type, because those integrations can currently reach that Destination;
- remove duplicates;
- do not surface a source that is not currently reachable to the Destination.

This route inspection is a temporary discovery adapter only. Filter records must not contain route IDs and the filter engine must not depend on Route objects.

If a previously configured integration is no longer reachable to a Destination, retain its saved policy as dormant state but do not show it as available. If that integration becomes reachable again later, the saved policy becomes active again.

## Filter ownership and persistence

Filtering is keyed by:

- `destination_id`
- canonical integration `source`

It is **not** keyed by `route_id`.

Add a destination-filter persistence layer separate from `RouteStore`. The persisted policy supports one or more OR clauses so existing route-filter behavior can be migrated without losing semantics. The WebUI normally edits a single clause for an integration; legacy multiple clauses may exist after migration and are evaluated as OR until the user replaces them from the new UI.

Default: no destination filter record/effective constraints means **allow all notifications** for that Destination + integration.

## Filter semantics

Each integration exposes a filter schema in the integration catalogue. A field is either:

- an enumerated choice field (severity/status/state/etc.); or
- a text/pattern field backed by normalized Notification properties or metadata.

Rules:

- all enum choices selected => no restriction for that field;
- zero enum choices selected => no restriction for that field;
- a strict subset selected => configured restriction;
- any non-empty text/pattern field => configured restriction;
- text fields accept comma-separated shell-style patterns, preserving current wildcard behavior;
- all configured fields inside one clause are ANDed;
- migrated multiple clauses are ORed;
- if no effective restriction remains, delete/omit the policy rather than storing a fake "configured" state.

Therefore the UI badge must show:

- **No filter / All notifications** when all choices or no choices are selected and no text field is restricted;
- **Configured** only when at least one effective restriction exists.

## Integration filter schemas

The initial UI covers every built-in integration currently in the catalogue. The implementation must only expose fields that are actually backed by the parser's normalized Notification/metadata contract; it must not invent fields that the parser never produces.

The approved UI shape is:

- **Xen Orchestra:** Status; Job / event; Job ID; Run ID; Mode; Repository; VM name where available from normalized notification data.
- **Zabbix:** Severity; Status; Host; Problem / event; Event type; Problem ID; Operational data.
- **Grafana:** Severity; Alert state; Alert name; Alert rule; Folder; Dashboard; Panel; Organization; Datasource; Labels.
- **Portainer:** Severity; Alert state; Instance/host; Alert name; Alert source; Metric; Source label; authentication method; username; created-by where present.
- **Proxmox:** Severity; State/status; Node/host; Category; Event type; VMID; Guest; Job ID; Storage.
- **QNAP:** Severity; NAS/host; Application; Category; Event type/title where normalized.
- **Synology:** Severity; Status/state; NAS/host; Package/source area; Category; Event type/title where normalized.
- **TrueNAS:** Severity; Host; Alert class/category; source/component where normalized; Event/title where normalized.
- **UniFi Network:** Severity; Device; Event name/type; Category; Site/network/client only when produced by the current parser.
- **UniFi Protect:** Severity; Camera/device; Alarm name; condition source/type; trigger/event fields currently normalized by the parser.
- **UniFi Drive:** Severity; Device; Event name/type; share/volume only when produced by the current parser.
- **Supermicro / HPE iLO / Dell iDRAC:** Severity; System/host; Message ID; Component/event category when normalized; Source IP.
- **Home Assistant:** Severity; Entity/device; Service; Event type; Category; other normalized component/domain/area fields only when produced by the parser.

The catalogue is the one UI contract for field labels, field type, enum values, and candidate Notification/metadata paths. The matching engine consumes the same schema so UI and runtime cannot drift.

## Runtime flow

Current routing continues to decide candidate destinations. Filtering is applied after route candidate selection and before destination delivery:

`notification -> route candidate selection -> destination/integration filter -> delivery`

`RouteStore` remains responsible for source/input routing, priority, fallback behavior, route enablement, and duplicate-destination suppression.

The new filter subsystem is responsible only for whether a normalized notification is allowed to reach a candidate Destination.

`PlatformDeliveryService` receives/injects the filter store and removes candidates rejected by the destination filter policy before sending.

`PlatformRoutingBridge` may continue discovering candidate owners from routes, but the final allow/block decision is always made by the destination filter service before delivery.

## Legacy route-filter migration

Existing filters must not be lost during upgrade.

Add schema migration 11 to create destination-filter storage. On startup, run an idempotent data migration:

1. find legacy routes with non-empty `filters_json`;
2. group them by `destination_id + canonical source`;
3. copy each route filter object into the destination policy as an OR clause;
4. complete the copy and clearing in one transaction;
5. clear those legacy `routes.filters_json` values only after their destination policy is safely stored.

After migration, route matching no longer evaluates `filters_json`. The legacy database column can remain physically present for compatibility in this change, but new route create/update/API/WebUI flows do not write or use it.

## Route UI/API changes

Routes become routing-only:

- remove the **Optional route filters** fieldset from Add/Edit Route;
- remove the Filters column from the Routes table;
- change route copy so it no longer promises event filtering;
- route API create/update no longer accepts active filter configuration;
- route serialization no longer presents filters as the current control surface;
- preserve source/input/destination/priority/enabled behavior unchanged.

## Filtering API

Add authenticated `/api/v2/filters` resources for:

- list visible destination filter policies;
- inspect one destination policy together with its currently available integrations;
- create/update one integration policy for a Destination;
- clear one integration policy;
- delete/clear a Destination's policies.

The server, not the browser, calculates available integrations. A write must be rejected if the requested source is not currently available to the Destination.

The response for a Destination includes the available integrations and their catalogue filter schema so the WebUI cannot configure unrelated integrations.

## Permissions

Use existing ownership rules. Reads follow Destination visibility. Filter mutations require the same effective write authority as changing the Destination/routing configuration; the initial WebUI exposes mutation controls to administrators consistently with current route/destination management.

## Audit

Audit filter mutations separately from route mutations, for example:

- `filter.update`
- `filter.clear`
- `filter.delete`

Audit details may contain Destination ID and source, but no secrets.

## Tests / acceptance

The change is complete only when tests prove:

1. route create/update/matching no longer depends on route filters;
2. existing route filters migrate to destination filters without changing allow/block behavior;
3. destination filters are evaluated before delivery;
4. no policy/all choices/zero choices means allow all;
5. subset enum or non-empty text pattern means Configured and filters correctly;
6. only integrations currently reachable to the selected Destination are returned;
7. disabled routes do not make an integration available;
8. wildcard routes expand only to compatible built-in integrations;
9. a write for an unavailable integration is rejected server-side;
10. Filtering UI follows the approved simple management flow;
11. configuring one integration never renders every integration's fields at once;
12. all built-in integrations expose their supported filter fields from the shared catalogue contract;
13. existing routing priority/fallback/deduplication behavior remains green;
14. schema version advances from 10 to 11;
15. full Python, WebUI JS, YAML/Compose, image-build CI remains green.

## Explicit non-goals

- Do not redesign the route acquisition/routing model yet.
- Do not change route priority/fallback semantics.
- Do not create a new destination model.
- Do not add unrelated integrations.
- Do not expose arbitrary raw metadata keys to the WebUI; expose only declared safe normalized filter fields.
- Do not make production/stage release changes in this task.
