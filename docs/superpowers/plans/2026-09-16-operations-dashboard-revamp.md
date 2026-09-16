# Operations Dashboard Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy Dashboard with the approved Operations Dashboard, extend Routing Flow to 3h/6h, and retire the old Dashboard Routing Flow without changing notification behavior.

**Architecture:** Add a final WebUI presentation layer that replaces only `#view-dashboard`, overrides the Dashboard renderer, and renders from the existing in-memory/API state. Extend the existing read-only Routing Flow range validation in the backend and inject the new Dashboard assets after all accepted CE layers.

**Tech Stack:** Vanilla JavaScript, CSS, Python WebUI service, pytest static/regression contracts.

**Spec:** `docs/superpowers/specs/2026-09-16-operations-dashboard-design.md`

## Global Constraints

- Start from `development` and work on a dedicated branch.
- One atomic commit for the complete change.
- One initial CI run; stop mutations while CI is running.
- Do not alter Routing Flow topology/layout/particle behavior beyond range options.
- Do not alter Filtering/Destination ownership, routing, ingestion, or delivery behavior.
- Use real state/API values; do not add demo metrics.

---

### Task 1: Extend Routing Flow history windows

**Files:**
- Modify: `src/api/routing_flow.py`
- Covered in: `tests/test_operations_dashboard_revamp.py`

**Interfaces:**
- Consumes: `/api/v2/routing-flow/<range>`.
- Produces: valid `3h` and `6h` snapshots using existing `delivery_snapshot` behavior.

- [x] Add `3h = 10800` and `6h = 21600` to the backend `WINDOWS` map.
- [x] Add Last 3 hours and Last 6 hours to the Routing Flow selector from the operations layer.
- [x] Add regression assertions for both range keys and labels.

### Task 2: Build the approved Operations Dashboard layer

**Files:**
- Create: `src/webui/operations_dashboard.js`
- Create: `src/webui/operations_dashboard.css`
- Covered in: `tests/test_operations_dashboard_revamp.py`

**Interfaces:**
- Consumes: existing global `state`, `request`, `navigate`, `renderDashboard`, source/output icon helpers, metrics/deliveries/filters/audit endpoints.
- Produces: approved Dashboard DOM and renderer; synchronized range controls; 30-second live refresh.

- [x] Replace `#view-dashboard` contents with the approved KPI / chart / activity / rankings / health / configuration layout.
- [x] Override `renderDashboard` so the legacy `renderFlow()` path is not executed.
- [x] Render all values from actual visible state and API payloads.
- [x] Add exact selected-reference styling and responsive fallbacks.
- [x] Add truthful live/update and health states without demo values.

### Task 3: Package the new WebUI layer after accepted extensions

**Files:**
- Modify: `src/webui/service.py`
- Test: `tests/test_operations_dashboard_revamp.py`

**Interfaces:**
- Consumes: WebUI asset whitelist and server-side HTML extension injection.
- Produces: `/ui/operations_dashboard.js` and `/ui/operations_dashboard.css`, loaded after Routing Flow and Filtering ownership layers.

- [x] Add both assets to the explicit WebUI asset map.
- [x] Inject the stylesheet after existing CE extension styles.
- [x] Inject the script last so it becomes the canonical Dashboard presentation layer.

### Task 4: Regression verification

**Files:**
- Create: `tests/test_operations_dashboard_revamp.py`

**Interfaces:**
- Produces: static regression contract for range support, approved information architecture, legacy Dashboard flow retirement, asset packaging, and layout structure.

- [x] Verify new JS syntax with `node --check`.
- [x] Verify modified Python syntax with `python3 -m py_compile`.
- [x] Run the focused regression test locally before creating the atomic GitHub commit.
- [ ] Run repository CI once on the atomic PR head and merge only after green.
- [ ] Verify post-merge Development CI and exact-SHA deployment.
