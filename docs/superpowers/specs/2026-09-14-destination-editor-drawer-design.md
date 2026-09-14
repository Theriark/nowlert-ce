# Destination Editor + Assigned Routes Drawer Design

**Date:** 2026-09-14

## Goal

Replace the current generic destination modal route-picker presentation with the approved compact destination editor and right-hand Assigned routes drawer, while preserving Nowlert CE's existing destination and route API contracts.

## Scope

The editor applies consistently to every supported destination type: Discord, Microsoft Teams, Slack, Generic webhook, MQTT, and ntfy. Each type keeps its existing settings and credentials; only their presentation changes.

The existing destination-owned many-to-many routing model remains authoritative. Route assignment is still persisted through the existing `route_ids` payload handled by the current `saveDestination` implementation in `dashboard.js`. This change must not add a second routing contract or move assignments back into the Route editor.

## Approved interaction

- The editor opens as a compact dark dialog with a provider identity card, destination name, provider-specific settings, Routing summary, Credentials card, sharing control, and Cancel / Save changes actions.
- The provider identity card shows the current destination type, a type-specific icon and description, and an Enabled / Disabled state control.
- The existing destination-type selector remains usable from the provider identity card so the current type-change capability is preserved.
- Discord maps the existing `components_v2` boolean to a UI-facing Message style selector: `Modern Card` when enabled and `Classic Embed` when disabled. No backend setting is added.
- Routing shows the assigned-route count plus a concise integration summary. `Manage routes` opens a right-hand drawer.
- The drawer contains Assigned routes heading/copy, selected count, search, Select all, Clear, route rows with real source icons, route metadata/status, a close control, and Done.
- Done closes the drawer only. Destination persistence still occurs only when Save changes is submitted.
- The route drawer is responsive: a second desktop column and a full-editor overlay on narrow screens.
- Existing write-only credential behavior, configured-credential copy, sharing behavior, validation, duplicate-name handling, and CSRF/API behavior remain unchanged.

## Visual direction

Use the approved reference's charcoal surfaces, compact spacing, cyan action accent, green configured/enabled states, muted secondary text, bordered cards, and dense route rows. The redesign is scoped to the destination editor and does not recolor the rest of the WebUI.

## Compatibility constraints

- Preserve IDs consumed by `app.js`, `qa_patch.js`, and `dashboard.js`.
- Preserve `destination-routes-fieldset`, `destination-routes`, `destination-routes-toggle`, `destination-routes-popover`, `destination-route-search`, `destination-route-options`, `destination-routes-select-all`, and `destination-routes-clear` anchors.
- Keep the stable submit capture binding so the current `saveDestination` / `saveRoute` wrappers remain the submitted handlers.
- Keep external route-assignment CSS; do not restore dynamically injected CSS.
- Do not alter backend storage, API schemas, routing semantics, destination secrets, deployment workflows, or release metadata.
