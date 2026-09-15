# Admin/User Destination Access and Navigation Design

Date: 2026-09-15
Target repository: `Theriark/nowlert-ce`
Target base: `development` at `902c05884384426289d0c85a1b22c61f6a793d9a`

## Goal

Simplify the Nowlert CE WebUI around the resources users actually manage while introducing a clear separation between administrator-managed shared Destinations and user-owned private Destinations.

The design must make user-private Destinations genuinely private at the Nowlert application/API boundary, allow administrators to grant narrowly scoped edit rights on shared Destinations, keep Filtering destination-owned, and remove obsolete top-level management surfaces for Routes, Sources, Inputs, API access, Settings, Updates, and Data tools.

## Core product model

Nowlert exposes three user-facing concepts:

1. **Destinations** are delivery endpoints.
2. **Filtering** belongs to a Destination and controls which notifications reach it.
3. **Routes** are internal/system routing paths and are not a user-managed resource.

SMTP, HTTP, and Redfish inputs remain available platform capabilities. They are not independently enabled/disabled from the WebUI.

## Roles

There are two roles:

- `admin`: platform administrator;
- `user`: normal user.

Role alone does not grant an administrator visibility into a normal user's private Destination configuration. Administrator authority over shared/platform resources remains strong, but private user resources have an application-level privacy boundary.

## Destination classes

### Administrator/shared Destinations

An administrator may create a Destination and choose whether it is shared.

A shared Destination is visible to normal users. Visibility alone is read-only.

For each normal user and each shared Destination, an administrator may grant two independent permissions:

- `can_edit_destination`
- `can_manage_filters`

The four supported combinations are therefore:

| Edit Destination | Manage Filtering | Result |
|---|---|---|
| false | false | read-only Destination and read-only Filtering |
| true | false | Destination editing allowed; Filtering read-only |
| false | true | Destination read-only; Filtering editing allowed |
| true | true | both Destination and Filtering editing allowed |

`can_edit_destination` allows the user to update normal editable Destination configuration, enabled state, credentials replacement, test delivery, and assigned system Routes. It does **not** allow the user to:

- change `shared` state;
- change ownership;
- grant/revoke permissions;
- delete the shared Destination;
- enable administrator-only network/security options such as private-network delivery.

`can_manage_filters` allows the user to create, update, enable/disable, and clear Destination-owned integration filters for that shared Destination. It does not imply Destination edit permission.

Administrators retain full management rights over administrator-owned/shared Destinations and their Filtering.

### User-owned private Destinations

A normal user may create their own Destination.

A user-created Destination is always:

- owned by the creating user;
- private (`shared = false`);
- editable by its owner;
- deletable by its owner;
- testable by its owner;
- assignable to the available system Routes;
- fully filterable by its owner.

A normal user cannot:

- create a Destination for another owner;
- make their Destination shared;
- grant Destination permissions;
- grant Filtering permissions;
- use administrator-only delivery/network settings.

Ownership itself grants the user Destination-edit and Filtering-management rights. No ACL row is required for the owner.

## Private-resource privacy boundary

A normal user's private Destination is private at the Nowlert WebUI/API authorization boundary.

Administrators may know that a user owns private resources for account/administrative purposes, but they must not receive:

- private Destination names;
- output configuration;
- credentials or secret metadata;
- assigned Route IDs;
- Destination-owned Filtering rules;
- private delivery/event contents;
- private resource-specific audit details.

The Users administration surface may expose aggregate metadata such as `private_destination_count` for an account. It must not enumerate those private Destinations.

Normal users see their own private Destinations plus shared Destinations.

Administrators see administrator-owned Destinations and shared Destinations. A private Destination owned by a non-admin user is excluded from normal administrator Destination/filter/detail APIs, even if the administrator knows its ID.

This is an **application-level privacy boundary**. A host/root operator who directly reads the Nowlert state volume is outside the WebUI/API authorization model. Application-managed private backups remain non-downloadable through the normal WebUI/API, preserving the existing recovery boundary. Credential-free Data tools exports must not include non-admin private Destination configuration.

## Destination permission persistence

Add schema migration 13 with a dedicated ACL table, for example:

```sql
CREATE TABLE destination_user_permissions (
    destination_id TEXT NOT NULL
        REFERENCES destinations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,
    can_edit_destination INTEGER NOT NULL DEFAULT 0
        CHECK (can_edit_destination IN (0, 1)),
    can_manage_filters INTEGER NOT NULL DEFAULT 0
        CHECK (can_manage_filters IN (0, 1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY (destination_id, user_id)
)
```

Rules:

- ACL rows apply only to shared Destinations.
- Only administrators can create, update, or delete ACL rows.
- A user's own private Destination never needs an ACL row.
- Revoking sharing from a Destination removes its ACL rows.
- Disabling/deleting a user automatically removes their ACL rows through the foreign key relationship where applicable.
- Permission checks must be performed server-side. UI hiding is never the security boundary.

## Authorization helpers

Do not weaken the generic ownership policy globally because it is used by several resource types.

Introduce Destination-specific authorization helpers with explicit semantics:

- `can_view_destination(actor, destination)`
- `can_edit_destination(actor, destination)`
- `can_manage_destination_filters(actor, destination)`
- `require_view_destination(...)`
- `require_edit_destination(...)`
- `require_manage_destination_filters(...)`

Rules:

- owner can view/edit/manage filters on their own private Destination;
- any authenticated user can view a shared Destination;
- administrator can manage administrator-owned/shared Destinations;
- administrator does **not** automatically gain view/edit/filter access to a non-admin private Destination;
- an ACL can grant Destination editing and/or Filtering management only for a shared Destination.

Internal runtime delivery is not an HTTP administrator read and must continue to resolve private Destination configuration through a dedicated internal/system access path without exposing it to administrator API responses.

## Destination API behavior

### List/read

For a normal user, Destination listing returns:

- their own private Destinations;
- all shared Destinations.

For an administrator, Destination listing returns:

- administrator-owned Destinations;
- all shared Destinations;
- no non-admin private Destination details.

Serialized Destination responses include effective capability flags for the current actor, for example:

```json
{
  "can_edit": true,
  "can_manage_filters": false,
  "can_delete": false,
  "can_change_sharing": false
}
```

The WebUI renders from these effective permissions rather than duplicating authorization logic.

### Create

Normal-user POST behavior is forced server-side to:

- owner = authenticated user;
- shared = false.

Supplying another `owner_user_id` or `shared=true` must not bypass this rule.

Administrator creation preserves existing administrator capabilities.

### Update

For a shared Destination, a granted normal user may update only the fields covered by Destination edit permission.

Sharing, ownership, deletion, permission management, and administrator-only network controls remain administrator-only.

For a private user-owned Destination, the owner may update its normal fields but may not set `shared=true`.

### Delete

- owner may delete their own private Destination;
- administrator may delete administrator-owned/shared Destinations;
- administrator may not delete a non-admin private Destination through the normal Destination API;
- a permission grant on a shared Destination never grants delete authority.

## Shared Destination permissions API

Expose an administrator-only permission resource suitable for the Users administration UI.

The API should allow an administrator to list shared Destinations together with a selected user's effective grants and update the two booleans atomically.

The API must reject:

- non-admin callers;
- private Destination targets;
- invalid/disabled target users where existing account policy disallows grants;
- attempts to grant permissions to the Destination owner when ownership already provides authority.

Permission mutations are audited without including credentials or filter contents.

## Routes become system routing paths

Routes remain in the database and runtime but are not user-owned controls from a product perspective.

The existing ownership column may remain for compatibility; it must no longer prevent a normal user from assigning an enabled system Route to a Destination they are authorized to edit.

Changes required:

- direct Route create/update/delete remains administrator-only/internal;
- normal users may receive safe enabled Route option metadata needed by the Destination editor;
- Destination assignment no longer rejects a Route because its stored `owner_user_id` differs from the Destination owner;
- runtime expansion/delivery must not skip a private Destination merely because its assigned Route has a different stored owner;
- a user cannot mutate the Route itself through the assignment capability.

This removes the current conflict where a private Destination cannot use a Route owned by someone else. Routes are plumbing; Destinations are ownership/security boundaries.

## Filtering model

Filtering remains keyed by:

- `destination_id`
- canonical integration source

There are no per-user duplicate filter copies.

For a private user-owned Destination, the owner has full Filtering rights.

For a shared Destination:

- every authenticated user may read the current Destination Filtering configuration;
- editing is read-only by default;
- `can_manage_filters` grants mutations for that user;
- administrators retain management rights on administrator/shared resources.

The Filtering API must replace blanket administrator-only mutation checks with the Destination-specific Filtering permission check.

The Filtering UI must show clear state badges/icons:

- `Private` for the user's own private Destination;
- `Shared` for shared Destinations;
- `Read only` when visible but not mutable;
- `Can edit` when the actor has effective Filtering management rights.

No independent "share filter" switch exists. Sharing is inherited from the Destination; permission to modify shared Filtering is controlled by the ACL.

## Delivery history and audit privacy

Delivery History remains a common user-facing page.

Normal users may see delivery history associated with resources visible to them under the final Destination visibility rules.

Administrator Delivery History must not expose payload/content from non-admin private Destinations. Administrator views may cover administrator-owned/shared Destinations and platform-safe aggregate information.

Audit Log becomes administrator-only in both UI and API authorization.

Administrator Audit Log must not expose private non-admin Destination/filter/secret details. Private-resource audit records may remain stored internally, but administrator serialization must exclude or safely redact records that would reveal private Destination identity/configuration/content.

## Data portability and backups

Data tools remain administrator-only but move under Administration.

Credential-free platform export must omit non-admin private Destination configuration, private Destination filters, and private Destination relationships that would reveal those private resources.

Application-managed state backups keep their existing disaster-recovery role. They remain private server-side snapshots and are not downloadable through normal WebUI/API endpoints. Host/root access is outside this application-level authorization design.

## WebUI information architecture

### Common sidebar

Authenticated users see:

1. Dashboard
2. Destinations
3. Filtering
4. Delivery history

### Administrator-only sidebar

Administrators additionally see:

5. Audit log
6. Administration
7. Backups

`Administration` is one top-level page containing three internal sections/tabs:

- Users
- Updates
- Data tools

The existing standalone Users, Updates, and Data tools navigation items are removed.

### Removed sidebar surfaces

The following are not top-level sidebar items:

- Sources (already retired)
- Routes (already retired)
- API access
- Settings
- Inputs
- Users
- Updates
- Data tools

The Inputs management view is retired. SMTP, HTTP, and Redfish listener availability remains platform/bootstrap behavior; no WebUI enable/disable control remains.

Legacy hashes/links for retired top-level pages should redirect to the closest supported destination instead of presenting broken views.

## Profile menu

The profile chip remains the control that opens the account menu, but the visible top chevron/arrow is removed.

The profile menu contains:

- API access
- Settings
- Security
- Sign out

API access continues to manage the signed-in user's own Event API tokens.

Settings moves from the sidebar into the profile menu. Existing sensitive/admin-only settings remain protected by their existing backend authorization; moving the entry point does not grant normal users administrator platform-setting authority.

Security remains the account-security/password surface.

## Administration > Users

The Users section retains account management and adds shared Destination permissions.

When an administrator selects/edits a user, show a `Shared Destination permissions` area listing only shared Destinations that are valid grant targets.

Each row exposes two independent toggles:

- Edit destination
- Manage filtering

The UI also shows only safe private-resource account metadata, such as:

- `Private destinations: 3`

It must not list private Destination names or configuration.

## Destinations WebUI

### Normal user

The page shows:

- own private Destinations;
- shared Destinations.

`Add destination` is available.

For an own private Destination:

- `Private` badge;
- edit/delete/test/manage-routes controls available;
- no sharing control;
- no permission-management control.

For a shared Destination:

- `Shared` badge;
- read-only by default;
- edit controls only when `can_edit` is true;
- no delete/share/permission controls for normal users.

### Administrator

The page shows administrator-owned/shared Destinations only. Non-admin private Destination details do not appear.

Administrators manage shared-Destination ACLs from Administration > Users rather than from the normal Destination editor.

## Filtering WebUI

Filtering follows the same visible Destination set as Destinations.

Cards/rows visually communicate:

- Private vs Shared;
- Read only vs Can edit.

Mutation controls render only when `can_manage_filters` is true. Read-only users can inspect the effective filter rules but cannot save, enable/disable, clear, or create them.

## Dashboard privacy

Dashboard resource lists, rankings, flow maps, and recent activity must obey the same visibility boundary as the corresponding resource pages.

Administrator aggregate counts may indicate that private user resources exist, but names, configuration, filters, event content, or private flow relationships must not be exposed.

## Inputs retirement

Remove the Inputs navigation item and user-facing Inputs management view/handlers.

Do not remove SMTP, HTTP, or Redfish listener implementations or their bootstrap configuration.

No WebUI request may enable/disable those listeners. Existing listener process/bootstrap configuration remains authoritative.

## Existing Routes/Sources retirement compatibility

Preserve the prior removal of Sources and Routes from normal navigation.

Filtering must remain independent of a Routes view DOM anchor.

Destination route assignment continues to use the internal system Route catalogue.

## Audit events

Add/retain bounded audit actions such as:

- `destination.permission.update`
- `destination.create`
- `destination.update`
- `destination.delete`
- `destination.routes_update`
- `filter.update`
- `filter.clear`
- `filter.enable`
- `filter.disable`

Permission audit details may include target user ID, shared Destination ID, and booleans, but never credentials or filter contents.

Private-resource audit serialization must respect the privacy boundary described above.

## Migration and compatibility

Advance schema version from 12 to 13 for the ACL table.

Do not destructively rewrite existing Destination ownership or sharing state during migration.

Newly created normal-user Destinations follow the new always-private rule. Historical records remain intact and are governed by the final authorization code.

Legacy UI hashes for Inputs/API access/Settings/Users/Updates/Data tools should resolve to their new supported parent/menu locations.

## Testing and acceptance

The change is complete only when automated tests prove all of the following:

1. normal user can create a Destination only for themselves;
2. normal-user creation is always private even if `shared=true` is submitted;
3. normal user can edit/delete/test their own private Destination;
4. normal user can assign enabled system Routes to their own private Destination without Route-owner mismatch failures;
5. delivery through those assigned Routes reaches the private Destination correctly;
6. normal user cannot share their private Destination;
7. normal user cannot manage ACLs;
8. admin Destination list excludes non-admin private Destination details;
9. admin direct GET/PATCH/filter access to a non-admin private Destination is rejected;
10. Users administration may report private-Destination counts without names/configuration;
11. shared Destination is visible to a normal user by default but read-only;
12. `can_edit_destination` grants shared Destination editing without granting filter mutation;
13. `can_manage_filters` grants filter mutation without granting Destination editing;
14. both grants together enable both capabilities;
15. neither grant permits delete/share/permission-management operations;
16. filter reads remain available on visible shared Destinations;
17. Filtering UI clearly marks Private/Shared and Read only/Can edit states;
18. Destination UI uses server-returned capability flags rather than role-only guesses;
19. administrator-only Audit API rejects normal users;
20. admin Delivery History/Audit/Data export do not expose non-admin private Destination contents;
21. profile dropdown contains API access, Settings, Security, and Sign out;
22. profile chevron/arrow is absent;
23. standalone API access and Settings sidebar items are absent;
24. Administration contains Users, Updates, and Data tools;
25. Administration, Backups, and Audit log are admin-only sidebar entries;
26. Inputs sidebar/view/toggle controls are absent while listener implementations remain intact;
27. Dashboard does not leak private Destination names/config/filter/event details;
28. existing shared/admin Destination behavior remains green;
29. schema migration 13 upgrades existing databases safely;
30. complete Python/WebUI/Compose/image-build CI remains green.

## Delivery workflow constraint

Implementation must follow the project's mandatory GitHub workflow:

- start from current `development`;
- use one implementation branch;
- assemble the entire intended change before publishing the final branch commit;
- final implementation PR must contain **one atomic commit**;
- allow exactly one PR CI run for that commit;
- if red, diagnose only that failure and amend/replace the atomic commit rather than starting unrelated work;
- merge only when green;
- then wait for the single post-merge Development CI/deployment to become green;
- do not make unrelated changes while either run is active.

The design/spec branch itself is not opened as a PR and therefore does not trigger the repository's pull-request CI. The final implementation branch must include this approved specification together with the implementation in its one atomic commit.
