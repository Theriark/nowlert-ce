# Filtering Ownership and Status Synchronization Design

## Goal

Make Filtering, Destinations, and Routing Flow reflect one consistent ownership/visibility model while preserving private user filtering and the existing runtime delivery behavior.

## Behavior

- Routing Flow column headings are `Integrations`, `Filters`, `Destinations` and align with their actual dynamic columns.
- Filtering table aligns the Filters column and separates the two Status controls.
- Filtering has a destination-level master enabled state. Disabling it bypasses all saved integration filters without deleting rules or changing individual integration enabled states. Re-enabling restores the exact individual states.
- The `Shared`/`Private` status in Filtering is the real Destination shared state. Admin clicks it to update the Destination; changes made in Destinations appear in Filtering automatically because both views read the same field.
- Normal users cannot change sharing.
- Admin-owned shared Destinations remain visible to normal users in Filtering as the default/system filtering layer. Users may see that filtering exists and whether it is active, but may not read Admin filter rules or modify them.
- A normal user may create/configure/enable/disable/delete filters for Destinations they own, including private Destinations.
- User-private filtering is not listed to Admin in Filtering. Admin may continue to see private Destination metadata in Destinations.
- Routing Flow shows Admin-managed shared filter nodes to normal users only when the real filter is configured and effectively enabled; rule contents remain private. User-owned private Destination/filter paths appear only in that user's Routing Flow.

## Data model

Use `settings_records` namespace `destination_filter_master_enabled`, keyed by Destination ID. Missing state means enabled for backward compatibility. A false value disables filtering for the whole Destination without changing per-source `destination_filter_enabled` state.

## API

The final access layer exposes:

- Filtering overview entries for owned Destinations with full integration details.
- Sanitized Filtering overview entries for visible Admin-owned shared Destinations with counts/state only and no rule payloads.
- No private-user filter metadata rows in Admin Filtering.
- Destination-level filter master state in the overview and destination filter view.
- An owner-only/admin-owner mutation endpoint for the master state.

Existing Destination PATCH remains the single source of truth for Shared/Private.

## Runtime

`AcceptanceFilterStore.matches()` first checks the destination master state. When disabled, the notification passes without evaluating integration filter rules. When enabled, existing per-integration filtering behavior remains unchanged.

## UI

Filtering UI permission checks use API-provided ownership/manage-filter flags instead of `role === admin`. Status pills are buttons only when the actor is allowed to change that state.

Routing Flow uses the true configured/enabled/master state even when rule details are restricted, and never substitutes fake configured/enabled values.

## Constraints

- Do not alter Route ownership/routing behavior.
- Do not expose Admin filter rules to normal users.
- Do not expose user-private filter rules or filter metadata to Admin Filtering.
- Preserve current dynamic Routing Flow layout and particle animation.
- One branch, one atomic commit, one CI run; if red, fix only the failing cause and rerun.
