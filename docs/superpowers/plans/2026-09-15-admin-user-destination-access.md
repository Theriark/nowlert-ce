# Admin/User Destination Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Admin/User Destination ownership, shared-Destination ACL, privacy, Filtering permissions, and WebUI navigation model without changing notification parser/output behavior.

**Architecture:** Keep the existing generic ownership layer intact and add a Destination-specific permission service backed by a new ACL table. The API extension in `src/api/filtering.py` becomes the authorization boundary for private/shared Destination exposure, delegated shared-Destination edits, Filtering mutations, route assignment, admin privacy, and permission management. The WebUI is reshaped through a small dedicated access/navigation module plus capability-driven Filtering rendering so the large legacy application file is not unnecessarily rewritten.

**Tech Stack:** Python 3.13, SQLite migrations, existing Nowlert platform API/storage layer, vanilla JavaScript/CSS WebUI, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-15-admin-user-destination-access-design.md`

## Global Constraints

- Target base is `development` at `902c05884384426289d0c85a1b22c61f6a793d9a`.
- All implementation and regression tests must land in **one atomic implementation commit** on one dedicated feature branch.
- Do not trigger CI until that complete implementation commit is ready and the PR is opened.
- Do not modify Stage/Production release workflows or deployment definitions.
- Routes remain runtime/system plumbing; do not reintroduce a user-facing Routes management surface.
- Sources remain retired from the user-facing WebUI.
- SMTP, HTTP, and Redfish listeners remain platform capabilities; only the Inputs management WebUI is retired.
- User-created Destinations are always private and self-owned.
- Administrators must not receive non-admin private Destination configuration/content through normal WebUI/API responses.
- Shared-Destination permissions are independent: `can_edit_destination` and `can_manage_filters`.
- UI hiding is never the authorization boundary; every mutation/read restriction is enforced server-side.
- Preserve existing destination credentials as write-only/non-returned secret values.

---

### Task 1: Add Destination permission persistence and authorization service

**Files:**
- Modify: `src/storage/migrations.py`
- Create: `src/storage/destination_permissions.py`
- Test: `tests/test_destination_access_permissions.py`

**Interfaces:**
- Produces: `DestinationPermissionStore(database, audit=None, clock=time.time)`.
- Produces: `capabilities(actor, destination_id) -> dict` with `can_view`, `can_edit`, `can_manage_filters`, `can_delete`, `can_change_sharing`, `private`, and `shared` booleans.
- Produces: `require_view(actor, destination_id)`, `require_edit(actor, destination_id)`, `require_filter(actor, destination_id)`.
- Produces: `list_for_user(admin_actor, user_id) -> list[dict]`, `set_for_user(admin_actor, user_id, destination_id, *, can_edit_destination, can_manage_filters)`, `private_destination_count(admin_actor, user_id)`, and helpers for visible/private Destination IDs.

- [ ] **Step 1: Write failing migration and ACL tests**

Add tests that migrate a fresh DB to schema 13, verify the `destination_user_permissions` table and FKs, and exercise all four shared-Destination permission combinations. Tests must also assert that an administrator cannot view a non-admin private Destination through the new Destination-specific permission service, while its owner can.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run:

```bash
pytest -q tests/test_destination_access_permissions.py
```

Expected: failure because schema 13 and `DestinationPermissionStore` do not exist.

- [ ] **Step 3: Implement migration 13**

Append migration 13 in `src/storage/migrations.py` creating `destination_user_permissions` with the composite primary key, destination/user cascading FKs, bounded boolean columns, and an index suitable for user permission lookup.

- [ ] **Step 4: Implement `DestinationPermissionStore`**

Implement server-side capability calculation with these exact rules:

```text
owner private/shared destination -> view/edit/filter/delete
shared destination, non-owner -> view; edit/filter only from ACL
admin-owned destination -> admin full rights
non-admin private destination, admin caller -> no view/edit/filter/delete
shared ACL never grants delete or sharing changes
normal user never changes sharing
```

Only administrators may call ACL list/set methods. ACL set rejects private Destinations, disabled users, owner grants, and non-boolean permission values. Setting both grants false removes the row. Permission changes write `destination.permission.update` audit records containing only Destination ID, user ID, and booleans.

- [ ] **Step 5: Run focused permission tests**

Expected: all Task 1 tests pass.

---

### Task 2: Enforce private/shared Destination behavior at the API boundary

**Files:**
- Modify: `src/api/filtering.py`
- Modify: `src/storage/route_destinations.py`
- Test: `tests/test_destination_access_permissions.py`
- Test: `tests/test_route_destination_api.py`

**Interfaces:**
- Consumes: `DestinationPermissionStore` from Task 1.
- Produces: Destination serialization capability fields: `can_edit`, `can_manage_filters`, `can_delete`, `can_change_sharing`, `private`, `shared`.
- Produces: administrator-only `/api/v2/users/{user_id}/destination-permissions` GET/PUT resource.

- [ ] **Step 1: Add failing API tests for user-owned private Destinations**

Test that a normal user can POST a Destination, that any submitted foreign owner or `shared=true` cannot produce a foreign/shared resource, and that the resulting Destination is editable/deletable/testable by its owner. Test that the same private Destination is absent from administrator Destination listing and direct administrator GET/PATCH is rejected.

- [ ] **Step 2: Add failing tests for shared Destination delegation**

Create an admin-owned shared Destination and a normal user. Assert read-only access by default. Grant only `can_edit_destination` and prove Destination update succeeds while filter mutation still fails. Grant only `can_manage_filters` and prove the inverse. Grant both and prove both succeed. Confirm ACL never grants delete or sharing changes.

- [ ] **Step 3: Integrate the permission store into `PlatformAPI`**

Instantiate the store in `src/api/filtering.py`. Override Destination list/create/read/update/action behavior as needed so that:

- normal-user create is forced to authenticated owner and `shared=false`;
- administrator list excludes non-admin private details;
- direct reads obey Destination-specific privacy;
- shared delegated edits use a narrowly scoped internal owner-authorized operation while auditing the real actor;
- share/owner/delete restrictions remain enforced independently from edit grants;
- every serialized Destination includes effective capability flags.

- [ ] **Step 4: Make Routes system-assignment plumbing**

Adjust `RouteDestinationStore` so an actor authorized to edit a Destination can assign enabled system Routes without route-owner equality. Do not grant Route mutation. Remove the old private-Destination/foreign-route prohibition from the API extension. Runtime expansion must not discard a private Destination merely because its assigned Route has another stored owner.

- [ ] **Step 5: Restrict direct Route mutation to administrators**

Normal authenticated users may receive only safe enabled Route option metadata required by the Destination picker. POST/PATCH/DELETE Route operations remain administrator-only/internal.

- [ ] **Step 6: Run Destination and route-assignment tests**

Run:

```bash
pytest -q tests/test_destination_access_permissions.py tests/test_route_destination_api.py tests/test_route_destination_relationships.py
```

Expected: all tests pass, including cross-owner system Route assignment to a private user Destination.

---

### Task 3: Apply Destination permissions to Filtering

**Files:**
- Modify: `src/api/filtering.py`
- Modify: `src/webui/filtering.js`
- Test: `tests/test_destination_access_permissions.py`
- Test: `tests/test_destination_filtering.py`
- Test: `tests/test_filtering_reference_ui.py`

**Interfaces:**
- Consumes: Destination capability service.
- Produces: Filtering overview/destination payload capability metadata.

- [ ] **Step 1: Add failing Filtering authorization tests**

Prove that an owner can mutate filters on their own private Destination, a normal user can read filters on a shared Destination, a shared Destination is read-only without ACL, and only the `can_manage_filters` grant enables PUT/DELETE/enable-disable filter actions.

- [ ] **Step 2: Replace blanket admin mutation checks**

In `/api/v2/filters` resource handlers, require Destination-specific filter permission instead of `_require_admin(actor)`. Guard every filter detail read with `require_view`. Include `private/shared/can_manage_filters` metadata in overview and detail responses.

- [ ] **Step 3: Make Filtering UI capability-driven**

Replace role-only `canEditFilters()` logic with per-Destination capability checks. Display `Private`/`Shared` and `Read only`/`Can edit` indicators. Hide New/Configure/Delete/enable-disable/save controls when the selected Destination is read-only, while keeping rule inspection available.

- [ ] **Step 4: Run Filtering tests**

Run:

```bash
pytest -q tests/test_destination_access_permissions.py tests/test_destination_filtering.py tests/test_filtering_reference_ui.py tests/test_filtering_ui_polish.py
```

Expected: all pass.

---

### Task 4: Enforce administrator privacy across Audit, Delivery History, Dashboard, and Data export

**Files:**
- Modify: `src/api/filtering.py`
- Test: `tests/test_destination_access_permissions.py`
- Test: `tests/test_platform_portability.py`
- Test: `tests/test_platform_api.py`

**Interfaces:**
- Consumes: private Destination ID lookup from `DestinationPermissionStore`.
- Produces: privacy-filtered admin responses and admin-only Audit API.

- [ ] **Step 1: Add failing privacy regression tests**

Create an admin Destination, a shared Destination, and a non-admin private Destination with delivery/filter/audit data. Assert admin normal APIs expose the first two but not the private Destination name/config/routes/filter rules/delivery contents/audit details. Assert normal-user calls to Audit endpoints are rejected.

- [ ] **Step 2: Make Audit API administrator-only and privacy-filtered**

Require admin for audit endpoints. Exclude/redact events tied to non-admin private Destination IDs so resource identity, configuration, filters, or private event contents do not leak.

- [ ] **Step 3: Privacy-filter Delivery History and dashboard data**

Filter admin delivery/history responses and dashboard flow/recent-activity source data against non-admin private Destination IDs. Aggregate counts may include safe existence/count information only where the spec permits; never include private names, payloads, filter details, or route relationships.

- [ ] **Step 4: Privacy-filter credential-free Data tools export**

Ensure administrator safe portability export omits non-admin private Destination configuration, corresponding destination filters, and route-destination relationships that reveal private resources. Preserve full server-side backup behavior unchanged.

- [ ] **Step 5: Run privacy and portability tests**

Run:

```bash
pytest -q tests/test_destination_access_permissions.py tests/test_platform_portability.py tests/test_platform_api.py
```

Expected: all pass.

---

### Task 5: Add Admin user permission management API metadata

**Files:**
- Modify: `src/api/filtering.py`
- Test: `tests/test_destination_access_permissions.py`

**Interfaces:**
- Produces: Users GET payload field `private_destination_count`.
- Produces: `/api/v2/users/{user_id}/destination-permissions` GET/PUT.

- [ ] **Step 1: Add failing Users administration tests**

Assert the administrator sees a private Destination count for each user but never names/configuration. Assert only admins can list/update shared Destination grants.

- [ ] **Step 2: Implement the Users metadata and ACL API**

Extend admin Users serialization with `private_destination_count`. Permission GET returns only shared Destination targets and the two grant booleans. Permission PUT updates both booleans atomically.

- [ ] **Step 3: Run focused tests**

Expected: Users/ACL tests pass.

---

### Task 6: Restructure WebUI navigation and Administration without rewriting core app.js

**Files:**
- Create: `src/webui/access_control.js`
- Create: `src/webui/access_control.css`
- Modify: `src/webui/service.py`
- Test: `tests/test_access_navigation_ui.py`
- Test: `tests/test_webui.py`
- Test: `tests/test_source_ui_retirement.py`
- Test: `tests/test_route_ui_retirement.py`

**Interfaces:**
- Produces: top-level common navigation `Dashboard`, `Destinations`, `Filtering`, `Delivery history`.
- Produces admin additions `Audit log`, `Administration`, `Backups`.
- Produces profile menu `API access`, `Settings`, `Security`, `Sign out` with no chevron.
- Produces Administration tabs `Users`, `Updates`, `Data tools`.

- [ ] **Step 1: Add failing WebUI structure tests**

Assert API access/Settings/Inputs/Users/Updates/Data tools are absent from top-level navigation after the runtime module installs; admin gets Administration/Audit/Backups; normal user does not. Assert profile menu contains API access, Settings, Security, Sign out and has no `profile-chevron`. Assert Inputs legacy navigation is retired without removing HTTP/SMTP/Redfish backend code.

- [ ] **Step 2: Implement `access_control.js`**

Use existing DOM nodes and application view IDs rather than duplicating their forms. Create a dynamic `Administration` view with tabs and move/re-host the Users, Updates, and Data tools content there so existing IDs and event handlers remain valid. Remove obsolete sidebar entries and inject profile-menu links. Map legacy hashes to their supported parent destinations.

- [ ] **Step 3: Implement capability-aware Destination presentation**

After destination rendering, use server-returned capability flags to show `Private`/`Shared` and `Read only`/`Can edit` state and suppress edit/delete/test/route-assignment/share controls the actor lacks. Normal users retain `Add destination`; sharing controls are removed for them.

- [ ] **Step 4: Add Administration > Users shared-Destination grants UI**

When an admin manages a user, fetch that user's shared Destination permission rows. Render `Edit destination` and `Manage filtering` toggles and safe `Private destinations: N` metadata. Never enumerate user-private Destination details.

- [ ] **Step 5: Register the new WebUI assets**

Whitelist `access_control.js/css` in `WebUIService` and inject them after the existing route/filter/source-retirement modules so final navigation normalization wins deterministically.

- [ ] **Step 6: Run WebUI tests**

Run:

```bash
pytest -q tests/test_access_navigation_ui.py tests/test_webui.py tests/test_source_ui_retirement.py tests/test_route_ui_retirement.py tests/test_filtering_reference_ui.py
```

Expected: all pass.

---

### Task 7: Final regression verification and atomic GitHub delivery

**Files:**
- All files changed by Tasks 1-6.

**Interfaces:**
- Produces one feature-branch commit and one PR.

- [ ] **Step 1: Run syntax checks**

Run Python compilation for modified/new Python files and `node --check` for modified/new JavaScript files.

- [ ] **Step 2: Run the complete automated test suite**

Run:

```bash
pytest -q
```

Expected: 0 failures.

- [ ] **Step 3: Review the complete diff against the approved spec**

Confirm there are no Stage/Production changes, no parser/output behavior changes, no user-facing Routes/Sources/Inputs CRUD reintroduced, and no private-resource data exposed to Admin APIs.

- [ ] **Step 4: Create exactly one implementation commit**

Create the feature branch `feat/admin-user-destination-access` directly from the approved `development` SHA and write the complete implementation/tests as one tree/commit:

```text
feat: add private user destinations and shared access controls
```

Do not push intermediate commits.

- [ ] **Step 5: Open one PR to `development` and wait for its single CI run**

Do not amend, merge, or trigger another workflow while the run is in progress. If it fails, inspect only that failure before making the minimum necessary correction.

- [ ] **Step 6: Merge only after PR CI is green**

Merge to `development` and then wait for the one push-triggered Development CI/deployment workflow to finish green, including exact-SHA image deployment verification.

- [ ] **Step 7: Run acceptance**

After Development is deployed, validate the admin and normal-user navigation, profile menu, private/shared Destination behavior, ACL combinations, Filtering read/edit states, private-resource isolation, system Route assignment, removed Inputs UI, and the previously fixed Destination route-checkbox/close-button behavior from this conversation.