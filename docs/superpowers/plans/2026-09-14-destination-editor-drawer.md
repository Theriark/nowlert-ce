# Destination Editor Drawer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved compact destination editor and Assigned routes drawer for every Nowlert CE destination type without changing backend routing or destination contracts.

**Architecture:** Keep `dashboard.js` as the owner of destination `route_ids` persistence and reuse the existing destination form IDs. Enhance the form after page load from `destination_routes.js`, move the existing type selector into a provider card, transform the route picker into a right-side drawer, and scope all new presentation rules to `destination_routes.css`.

**Tech Stack:** Vanilla JavaScript, HTML DOM APIs, CSS, Python pytest static/runtime WebUI contract tests.

**Spec:** `docs/superpowers/specs/2026-09-14-destination-editor-drawer-design.md`

## Global Constraints

- Work from a fresh branch created from `development`.
- Produce one atomic commit for the entire requested change.
- Do not alter backend APIs, routing semantics, deployment workflows, or unrelated files.
- Preserve current destination support for Discord, Microsoft Teams, Slack, Generic webhook, MQTT, and ntfy.
- Preserve destination-owned many-to-many route assignments and the current `saveDestination` handler.
- Do not trigger extra GitHub Actions runs; validate locally before the single push/commit.

---

### Task 1: Lock the destination editor UI contract

**Files:**
- Create: `tests/test_destination_editor_drawer_ui.py`

**Interfaces:**
- Consumes: packaged `src/webui/destination_routes.js` and `src/webui/destination_routes.css`.
- Produces: a static contract requiring the provider card, Routing summary, Credentials heading, right-hand Assigned routes drawer, search/actions/Done controls, responsive two-column layout, and support metadata for all six output types.

- [ ] **Step 1: Write the failing test**

Create assertions for `destination-editor-main`, `destination-provider-card`, `destination-routing-summary`, `destination-credentials-heading`, Manage routes, Shared with users, the Assigned routes drawer/search/Done controls, the desktop two-column CSS grid, and all six destination type metadata entries.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_destination_editor_drawer_ui.py -q`

Expected: FAIL because the current route picker has no destination editor shell or right-hand drawer.

### Task 2: Build the destination editor and Assigned routes drawer

**Files:**
- Modify: `src/webui/destination_routes.js`
- Modify: `src/webui/destination_routes.css`

**Interfaces:**
- Consumes: existing global `state`, `byId`, `element`, `outputIcon`, `sourceIcon`, `friendlyName`, `routeSourceDescriptor`, `renderDestinationFields`, `openDestination`, `saveDestination`, `saveRoute`, and `routeAssignmentSelection` from the existing WebUI.
- Produces: `destinationEditorEnsureLayout()`, `destinationEditorRefreshDynamicFields()`, `routeAssignmentOpenDrawer()`, `routeAssignmentCloseDrawer()`, and overrides for `routeAssignmentEnsureDestinationPicker()` / `routeAssignmentRenderOptions()` that preserve existing DOM IDs.

- [ ] **Step 1: Implement the provider-focused editor shell**

Move the existing form content into `#destination-editor-main`, add the provider card, reuse `#destination-type` inside it, keep the native enabled checkbox as state, expose a visual Enabled / Disabled button, and add Routing/Credentials/sharing presentation sections without replacing existing form field IDs.

- [ ] **Step 2: Implement provider-specific presentation**

Add metadata for Discord, Teams, Slack, webhook, MQTT, and ntfy. Rename the generic presentation label contextually and map Discord's existing `components_v2` boolean to a `Modern Card` / `Classic Embed` selector.

- [ ] **Step 3: Replace the popover presentation with a drawer**

Keep the route-assignment anchors, render the route list with actual source icons and route metadata, add selected count/search/select-all/clear/Done, and update the left Routing summary live as selection changes. Done must close only the drawer.

- [ ] **Step 4: Add scoped responsive styling**

Implement the approved compact charcoal/cyan visual treatment only inside the destination editor. Use a two-column grid while routes are open on desktop and an overlay drawer under 760px.

### Task 3: Verify compatibility before the single commit

**Files:**
- Test: `tests/test_destination_editor_drawer_ui.py`
- Existing test: `tests/test_destination_route_picker_runtime.py`

**Interfaces:**
- Consumes: final destination editor JS/CSS.
- Produces: evidence that the new contract and existing route-picker stability contract both remain valid.

- [ ] **Step 1: Run the new focused test**

Run: `python -m pytest tests/test_destination_editor_drawer_ui.py -q`

Expected: PASS.

- [ ] **Step 2: Validate JavaScript syntax**

Run: `node --check src/webui/destination_routes.js`

Expected: exit 0.

- [ ] **Step 3: Validate the existing route-picker contract**

Run the existing destination-route-picker assertions, including stable DOM anchors, external styles, scrollability, and capture-phase submit handler binding.

Expected: PASS.

- [ ] **Step 4: Create one atomic commit**

Include the spec, plan, test, JS, and CSS in one commit on `feature/destination-editor-drawer`. Do not make intermediate GitHub commits.

- [ ] **Step 5: Wait for the single CI run**

Do not make any additional changes while the run is in progress. If it fails, diagnose only that failure, fix it in the minimum corrective commit, and wait for the resulting run to become green before continuing.

- [ ] **Step 6: Merge to development only after green**

Merge the feature PR into `development`, then verify the expected Development post-merge workflow/image run without triggering any extra workflow manually.
