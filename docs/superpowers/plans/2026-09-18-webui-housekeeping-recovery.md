# WebUI, Housekeeping, Data Tools, and Recovery Plan

**Date:** 2026-09-18  
**Target branch:** `development`

## Goal

Complete the seven requested changes in this order while preserving the current
database-authoritative model and existing ownership/security boundaries.

## 1. Sidebar sizing

Increase the Nowlert owl, expanded menu labels/icons, collapsed icons, CE label,
and active collapsed target so the control panel matches the supplied reference
at normal desktop scale.

## 2. Sidebar collapse motion

Replace non-animatable `display:none` transitions with width, opacity,
max-width, grid, and edition cross-fades. Keep reduced-motion support.

## 3. Routing Flow first paint

Restore the requested hash view before the authenticated shell is revealed.
Existing Routing Flow session cache then hydrates synchronously before network
refresh rather than waiting for the entire workspace request set.

## 4. Filtering first paint

Use the same early requested-view restoration so the existing cached Filtering
overview renders immediately and `/filters` refreshes in the background.

## 5. Housekeeping

Add schema 13 housekeeping run history, administrator settings, daily scheduler,
manual run, bounded batch deletion, and status reporting.

Defaults:

- Delivery History: 90 days
- Audit Log: 365 days
- completed backup-run records: 180 days
- daily run: 03:15
- 0 days: retain forever

Expired/revoked browser sessions are removed after a seven-day grace period.
Housekeeping writes one bounded audit event per run.

## 6. Data Tools

Introduce `nowlert.platform.v2` safe portability:

- destinations and public settings
- reusable routes and route assignments
- destination-owned filtering policies and enabled state

Exclude users, passwords, credentials, token material, sessions, Delivery
History, Audit Log, and recovery archives. Continue accepting v1 portable
documents for compatibility.

## 7. Complete recovery backups

Upgrade new snapshots to `nowlert.state-backup.v2`:

- complete SQLite state and retained history
- Nowlert-managed private secret files
- mounted bootstrap `config.yaml` when available
- app/database version metadata
- SHA-256 integrity manifest

Keep v1 snapshot readability. Stage and migrate older supported database copies
before restore.

Add Local/NFS/SMB snapshot discovery and restore. External restore copies to
private local staging, verifies every file/database, creates a pre-restore safety
snapshot, swaps state/config atomically, revokes sessions, and restarts the live
service.

## Verification

- Python test suite
- Python compilation
- JavaScript syntax validation
- WebUI first-paint/sidebar regression contracts
- schema migration tests
- housekeeping retention/API tests
- portability v1 compatibility and v2 filtering round trip
- complete local backup/config restore
- external restore after local snapshot removal
- CI image/deployment checks on the exact commit
