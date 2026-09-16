# Filtering Ownership and Status Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize Filtering ownership/status with Destinations and Routing Flow while adding non-destructive destination-level filter enable/disable and normal-user private filtering management.

**Architecture:** Extend the final acceptance access layer with a destination-level filtering master switch stored in `settings_records`; make the Filtering overview owner-aware and sanitize shared Admin filtering for normal users. Update the existing Filtering UI to use API permissions and synchronized status actions, and update Routing Flow to use real restricted filter state without exposing rule contents.

**Tech Stack:** Python 3, SQLite settings_records, vanilla JavaScript/CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-filtering-ownership-status-sync-design.md`

## Global Constraints

- Preserve current Route/Destination delivery behavior except destination-level filter bypass when explicitly disabled.
- Preserve private rule contents across users.
- Do not show user-private filter metadata in Admin Filtering.
- Preserve Routing Flow layout and particle animation.
- One atomic commit and one initial CI run.

---

### Task 1: Add destination-level filtering master state

**Files:**
- Modify: `src/api/access_acceptance.py`
- Test: `tests/test_access_acceptance.py`

**Interfaces:**
- Produces: `AcceptanceFilterStore.destination_filtering_enabled(destination_id) -> bool`
- Produces: `AcceptanceFilterStore.set_destination_filtering_enabled(actor, destination_id, enabled) -> bool`

- [ ] Add failing tests proving default enabled, disable bypasses rules, re-enable restores rules, and per-source states remain unchanged.
- [ ] Implement settings-backed master state and runtime `matches()` short-circuit.
- [ ] Add API read/write exposure for the master state.
- [ ] Run targeted tests.

### Task 2: Make Filtering overview ownership-aware

**Files:**
- Modify: `src/api/access_acceptance.py`
- Test: `tests/test_access_acceptance.py`
- Test: `tests/test_acceptance_access_ui.py`

**Interfaces:**
- Owned Destination rows expose full configured integrations and `can_manage_filters=true`.
- Shared Admin-owned rows visible to normal users expose only sanitized counts/state, no rules.

- [ ] Add failing tests for normal-user own private filter management and sanitized Admin-shared rows.
- [ ] Remove Admin private-filter metadata from Filtering response.
- [ ] Implement sanitized shared Admin rows.
- [ ] Run targeted tests.

### Task 3: Update Filtering UI permissions and synchronized status controls

**Files:**
- Create: `src/webui/filtering_ownership_sync.js`
- Create: `src/webui/filtering_ownership_sync.css`
- Modify: `src/webui/service.py`
- Test: `tests/test_acceptance_access_ui.py`
- Test: `tests/test_filtering_ownership_sync.py`

**Interfaces:**
- Uses `owned`, `can_manage_filters`, `filtering_enabled`, `shared` from `/filters`.
- Uses Destination PATCH for sharing.
- Uses destination filtering master endpoint for Active/Disabled.

- [ ] Add failing static UI regression assertions.
- [ ] Layer owner-permission controls after the existing Filtering UI without rewriting its editor.
- [ ] Render Active/Disabled and Shared/Private as separated status controls.
- [ ] Wire master enable/disable and sharing actions.
- [ ] Restore New filter / Configure / Delete controls for normal users on owned Destinations.
- [ ] Remove Admin private-filter metadata rows at the API boundary.
- [ ] Run JS syntax and targeted tests.

### Task 4: Correct Routing Flow restricted state and headings

**Files:**
- Modify: `src/api/routing_flow.py`
- Extend: `src/webui/filtering_ownership_sync.js`
- Test: `tests/test_routing_flow.py` through compatibility plus `tests/test_filtering_ownership_sync.py`

**Interfaces:**
- Restricted policies expose booleans only: actual configured/effective enabled state, no rule values.

- [ ] Add failing tests for restricted configured/enabled truth and headings.
- [ ] Use real policy existence/per-source state plus destination master state.
- [ ] Rename headings from the post-routing-flow UI extension while preserving the working layout/particle implementation byte-for-byte.
- [ ] Run targeted tests and JS syntax.

### Task 5: Final verification and one atomic commit

**Files:**
- Include design and plan docs plus all implementation/test files.

- [ ] Run Python syntax checks for changed Python files.
- [ ] Run Node syntax checks for changed JS files.
- [ ] Run all locally available targeted tests.
- [ ] Review diff for unrelated changes.
- [ ] Create one atomic Git commit/tree on `feature/filtering-ownership-status-sync`.
- [ ] Open one PR and wait for the single CI run.
- [ ] If green, merge to `development` and verify post-merge Development CI/deployment.
