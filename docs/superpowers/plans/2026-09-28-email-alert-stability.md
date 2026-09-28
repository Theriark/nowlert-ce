# Email Alerts and Workspace Stability Implementation Plan

> **For agentic workers:** Execute this plan inline, one task at a time. Steps use checkbox syntax for tracking.

**Goal:** Fix the reported Email Alerts refresh, loading, action, dropdown, preview, destination-save, delivery-route-label, and API saturation behaviors without changing unrelated UI.

**Architecture:** Preserve tab state in the URL while changing the application hash, render tab-specific Email Alerts data as soon as it is available, and update individual rule rows after actions instead of rebuilding the page. Keep route assignment edits local until the destination form is saved, resolve delivery route IDs against loaded routes, and group rate-limit errors into one clear recovery message.

**Tech Stack:** Vanilla JavaScript, CSS, Python pytest source-contract tests, GitHub Actions.

**Spec:** User report and screenshots in the September 28, 2026 conversation.

## Global Constraints

- Keep Email Alerts on its selected Rules, Groups, Mailboxes, or Activity tab after F5.
- Do not change existing rule, group, mailbox, route, or delivery behavior beyond the reported bugs.
- Keep browser password-manager behavior from obscuring ordinary group fields where the page can control it.
- Treat 429 responses as rate limiting, preserve usable UI state, and avoid repeated broad reloads for one action.
- Do not change the approved page titles, theme, or unrelated navigation.

## Review Focus

- Existing URL query parameters must survive view navigation and reload.
- Email Alerts initial loading must not wait for unrelated sections or Activity before rendering Groups.
- Rule status updates must not remove the focused control or move the viewport.
- Route assignment Done must not submit the destination or disable Save changes during a full workspace reload.
- Delivery history must resolve route names safely when the route is unavailable.
- Browser-generated Bitwarden warnings must be distinguished from Nowlert dialogs and errors.

---

### Task 1: Email Alerts Refresh and Interaction Stability

**Files:** `src/webui/app.js`, `src/webui/email_alerts.js`, `src/webui/email_alerts.css`, `tests/test_webui_reported_regressions.py`

- [x] Write and run failing tests for query-preserving navigation, tab-aware loading, rule toggle updates without full reload, group-field autocomplete suppression, and preview spacing.
- [x] Load Rules with overview/groups/rules, Groups with groups/rules, Mailboxes with mailbox/provider data, and Activity with its related context; show a loading status while that tab's data is pending.
- [x] Preserve search parameters when `navigate` updates the hash, and keep the selected `emailTab` in the URL.
- [x] Patch a toggled rule's in-memory state and its row controls after the API succeeds without replacing the page.
- [x] Add safe autocomplete attributes to the group dialog and add the requested gap below the preview security notice.
- [x] Run focused Email Alerts tests.

### Task 2: Destination Route Assignment Responsiveness

**Files:** `src/webui/dashboard.js`, `src/webui/app.js`, `tests/test_webui_reported_regressions.py`

- [x] Write and run a failing test proving Done closes the route picker without submitting the destination.
- [x] Keep selected route IDs in the editor state; submit them only when Save changes is clicked.
- [x] Update the destination and route view from the save response instead of reloading the entire workspace.
- [x] Run destination and route editor tests.

### Task 3: Delivery History Route Names

**Files:** `src/webui/destination_overview_acceptance.js`, `tests/test_webui_reported_regressions.py`

- [x] Write and run a failing test for rendering a route name from `state.routes` and a safe short-ID fallback.
- [x] Resolve the route label by ID and preserve the existing delivery tag design.
- [x] Run delivery history tests.

### Task 4: Workspace Reload Resilience

**Files:** `src/webui/app.js`, `tests/test_webui_reported_regressions.py`

- [x] Write and run a failing test requiring a visible loading state while Email Alerts data is pending and preservation of the requested view.
- [x] Ensure route changes and Email Alerts loading don't trigger redundant full workspace fetches or leave a blank Groups surface.
- [x] Keep recoverable 429 errors scoped to affected data and retain previously loaded state.
- [x] Run the full WebUI regression suite and the project test suite; focused suite passed (99 tests), while full suite exposed 84 broader failures in this Windows environment and is not green.
