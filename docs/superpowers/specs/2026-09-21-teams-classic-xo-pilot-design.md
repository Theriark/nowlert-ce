# Microsoft Teams Classic Card — Xen Orchestra Pilot Design

## Goal

Add a user-selectable **Message style** to Microsoft Teams destinations with:

- **Modern Card** — current Teams Adaptive Card behavior, unchanged and default.
- **Classic Card** — a new Teams-native Adaptive Card presentation that follows the approved source-specific Nowlert Classic information hierarchy.

The first Classic implementation is **Xen Orchestra**. After real Teams acceptance of Xen Orchestra success, failure, and skipped cases, Classic coverage will be expanded source-by-source until it covers the same supported integrations as Discord Classic.

## Primary safety requirement

**Teams Modern must not change.**

The existing Teams Modern rendering path is production behavior and must remain isolated from the new Classic path.

The implementation must not change the current output of:

- `TeamsCardFormatter._render_teams_card()`;
- existing Teams source formatter `format()` methods when Modern is selected;
- current Teams delivery semantics;
- current Teams payload-size enforcement;
- current Teams destination secret handling;
- current Teams HTTP 202 acceptance semantics.

Existing Teams destinations that do not yet contain a message-style setting must normalize to **Modern** and render the same payload they render before this feature.

Classic-specific iteration after the pilot must be confined to the Classic renderer and must not require editing the Modern renderer.

## User experience

When creating or editing a Microsoft Teams destination, the destination editor exposes:

```text
Message style
[ Modern Card ▼ ]

Options:
- Modern Card
- Classic Card
```

Behavior:

- New Teams destinations default to `Modern Card`.
- Existing Teams destinations with no `message_style` setting behave as `Modern Card`.
- Users can switch an existing destination from Modern to Classic and back at any time.
- The selected style is stored per destination.
- Preview/test delivery and normal routed delivery use the same selected style.

The existing `Channel / destination` field and Teams webhook secret remain unchanged.

## Destination settings contract

Microsoft Teams gains one public setting:

```json
{
  "message_style": "modern"
}
```

Allowed values:

- `modern`
- `classic`

Normalization rules:

- missing value -> `modern`;
- empty value -> invalid unless normalized through the default path;
- unsupported value -> validation error;
- existing unrelated settings remain rejected.

This is deliberately parallel to the user-facing Modern/Classic choice already exposed by other Nowlert destinations, without changing Teams transport behavior.

## Rendering architecture

The feature uses two explicitly separate renderer paths.

```text
Teams destination
       |
       v
message_style
   /         \
modern      classic
  |            |
  |            +--> Teams Classic renderer
  |                  |
  |                  +--> XO Classic pilot
  |                  +--> later source-specific Classic renderers
  |
  +--> existing source-specific Teams formatter
       + existing TeamsCardFormatter
       + current Adaptive Card payload
```

### Modern path

Modern continues through the existing code:

```text
TeamsPlatformAdapter
 -> source-specific Teams formatter
 -> formatter.format(notification)
 -> TeamsCardFormatter._render_teams_card(...)
 -> current Adaptive Card JSON
```

The new feature must not modify the semantics or payload shape of this path.

### Classic path

Classic uses a new, separate Teams-native renderer.

The renderer consumes the same normalized notification data and follows the approved Discord Classic card's information hierarchy, ordering, lifecycle wording, and section intent, but emits **Microsoft Adaptive Card 1.4** elements.

It must not send:

- Discord `embeds`;
- Discord component types;
- Discord webhook flags;
- Discord attachment semantics;
- legacy Microsoft MessageCard payloads.

The Classic renderer should be independently editable so Teams-specific visual adjustments do not change Modern Teams cards.

## Xen Orchestra Classic pilot

The first Teams Classic card must match the approved Xen Orchestra Classic information model.

### Lifecycle

Use the approved XO Classic lifecycle states:

- Success -> `✅ Backup Successful`
- Failure/error/critical -> `❌ Backup Failed`
- Skipped/warning with skipped VMs -> `⏭️ Backup Skipped`

The card title follows:

```text
<lifecycle icon> <lifecycle> — <job name>
```

Examples:

```text
✅ Backup Successful — Daily Production Backup
❌ Backup Failed — Daily Production Backup
⏭️ Backup Skipped — Daily Production Backup
```

### Description

Success:

```text
<N> VM/VMs protected successfully with no failures.
```

Failure:

```text
Backup operation failed with <N> VM error/errors.
```

Skipped:

```text
<N> VM/VMs protected successfully and <N> VM/VMs were skipped by backup policy.
```

### Field order

The Classic Teams card preserves this order from the approved XO Classic card:

1. `⏱️ Duration`
2. `📦 Transfer Size`
3. `🚀 Transfer Speed`
4. `📁 Storage`
5. `✅ Successful VMs · <count>`
6. `❌ Failed VMs · <count>`
7. `⏭️ Skipped VMs · <count>`
8. `🆔 Job ID`

Empty sections are omitted.

Storage preserves the approved repository/mode transformation used by XO Classic.

VM sections preserve:

- VM name;
- VM size when available;
- failure/skipped error text when available;
- maximum visible VM count and bounded overflow text.

## Teams-native Classic layout

The XO Classic card remains an Adaptive Card 1.4 with `msteams.width = Full`.

Suggested Teams-native layout:

```text
┌──────────────────────────────────────────────┐
│ ✅ Backup Successful — Daily Backup          │
│ 3 VMs protected successfully...             │
├──────────────────────────────────────────────┤
│ ⏱️ Duration      📦 Transfer Size            │
│ 5 min            52.06 GiB                   │
│                                              │
│ 🚀 Transfer Speed                            │
│ 33.73 MiB/s                                  │
├──────────────────────────────────────────────┤
│ 📁 Storage                                   │
│ Repository · Full                            │
├──────────────────────────────────────────────┤
│ ✅ Successful VMs · 2                       │
│ VM-01 · 18 GiB                               │
│ VM-02 · 12 GiB                               │
├──────────────────────────────────────────────┤
│ ❌ Failed VMs · 1                           │
│ VM-03 · 22 GiB                               │
│ Error: Synthetic timeout                     │
├──────────────────────────────────────────────┤
│ 🆔 Job ID                                    │
│ JOB-123                                      │
├──────────────────────────────────────────────┤
│ 🦉 Nowlert CE • Classic Card                 │
└──────────────────────────────────────────────┘
```

The exact Adaptive Card element composition may be tuned after real Teams rendering, but those edits stay inside the Classic renderer.

Use native Teams elements such as:

- `Container`;
- `TextBlock`;
- `ColumnSet`;
- `FactSet` where it improves readability;
- separators and spacing supported by Adaptive Cards.

Do not force Discord's embed geometry where Teams renders it poorly.

## Classic source-of-truth rule

Discord Classic remains the approved content reference during rollout.

For Xen Orchestra, Teams Classic must preserve:

- the same lifecycle decision;
- title semantics;
- description semantics;
- field names;
- field ordering;
- source-specific values;
- omission rules.

Teams may use a different native layout where required by Adaptive Cards.

For the pilot, do **not** refactor the current Teams Modern renderer or the approved Discord Classic renderer merely to create a shared abstraction. Isolation and safe acceptance come first.

Once Teams Classic is validated across sources, a later refactor may extract a neutral shared Classic presentation model if that materially reduces duplication without changing approved output.

## Unsupported Classic sources during pilot

During the XO-only pilot:

- `message_style=classic` + source `xo` -> Teams XO Classic.
- `message_style=classic` + any source not yet implemented -> existing Teams Modern renderer as a temporary fallback.

The fallback is explicitly temporary and exists only while Classic is rolled out integration-by-integration.

Each later source implementation removes its fallback case.

When the full rollout is complete:

- all supported source integrations use their Teams Classic renderer;
- only unknown/generic events use the eventual generic Teams Classic fallback.

## Platform adapter behavior

`TeamsPlatformAdapter.preview()` must:

1. normalize Teams settings;
2. read `message_style`;
3. select Classic only when `message_style == "classic"` and a Classic renderer exists for the source;
4. otherwise use the existing Modern formatter path;
5. sanitize the selected payload;
6. enforce the existing Teams payload-size metadata.

`deliver()` remains unchanged in behavior:

- same HTTPS webhook URL resolution;
- same 15-second POST;
- same 28 KiB payload limit;
- same safe error behavior;
- same HTTP 202 semantics.

Preview metadata should include enough information to verify the selected presentation path during tests, for example:

```json
{
  "message_style": "classic",
  "formatter": "TeamsClassicXenOrchestraFormatter"
}
```

The exact metadata key naming may follow existing repository conventions.

## WebUI behavior

In `destinationDefinition("teams")`, add a select field after `Channel / destination`:

```text
Message style
- Modern Card
- Classic Card
```

Default is Modern.

Editing an existing destination must reflect its stored setting.

An older destination with no stored setting must display Modern.

No other Teams destination fields change.

## Testing

Implementation must be test-first.

### Settings tests

Prove:

- `normalize_output_settings("teams", {}) == {"message_style": "modern"}`;
- explicit `modern` is accepted;
- explicit `classic` is accepted;
- unsupported values are rejected.

### Modern regression gate

Before adding Classic production behavior, capture the existing Teams Modern payload for representative sources.

After implementation, prove that:

- a Teams destination with no `message_style` produces the same Modern payload as before;
- explicit `message_style=modern` produces the same payload;
- formatter selection for existing Modern sources is unchanged;
- payload-size metadata and sanitization remain unchanged.

This gate is mandatory because Classic must not alter current Teams cards.

### XO Classic tests

Cover at least:

- success;
- failure;
- skipped;
- successful VM list;
- failed VM list with error;
- skipped VM list with error;
- repository + mode storage rendering;
- Job ID;
- missing optional values;
- long VM lists/bounded output;
- payload remains within Teams 28 KiB limit.

Parity assertions should compare XO Classic semantic content/order against the approved Discord Classic XO contract, not against Discord transport JSON.

### Pilot fallback tests

Prove:

- Teams Classic + XO -> Classic renderer.
- Teams Classic + Grafana before Grafana Classic exists -> current Modern Grafana Teams renderer.
- Teams Modern + XO -> existing Modern XO renderer.

### WebUI tests

Prove the Teams destination editor exposes:

- Modern Card;
- Classic Card;
- Modern default;
- stored Classic selection when editing.

## Acceptance flow

After implementation and green CI:

1. deploy CE Development normally;
2. edit/create a Microsoft Teams Development destination;
3. select **Classic Card**;
4. route/fire a real Xen Orchestra success notification;
5. inspect the rendered card in Teams;
6. repeat with failure;
7. repeat with skipped VMs;
8. adjust only the Teams Classic renderer if visual tuning is required;
9. re-test until XO Classic is accepted;
10. then begin the next integration's Classic implementation.

Visual changes requested during this acceptance loop must not modify the Modern renderer unless a separate Modern-card change is explicitly requested.

## Expected implementation scope

Likely files:

- `src/outputs/settings.py`
- `src/outputs/platform.py`
- new Teams Classic formatter module, e.g. `src/formatters/teams_classic_v1.py`
- `src/webui/app.js`
- Teams/platform settings and formatter tests
- WebUI destination-editor tests
- `docs/platform-outputs.md`
- `CHANGELOG.md` if required by repository validation

The existing `src/formatters/teams_common.py` Modern renderer should not require modification for the XO pilot.

The existing `src/formatters/teams.py` Modern XO formatter should remain behaviorally unchanged.

## Non-goals for this pilot

- Do not implement Classic for every Teams integration yet.
- Do not redesign Teams Modern.
- Do not convert Teams to legacy Microsoft MessageCards.
- Do not change Teams transport behavior.
- Do not change Teams webhook credentials.
- Do not change Slack, Discord, or Generic Webhook behavior.
- Do not refactor all Classic presentation code during the pilot.
- Do not merge the temporary Modern fallback into the final full-coverage definition; it exists only during staged rollout.

## Success criteria

The pilot is successful when:

1. Teams destinations expose Modern/Classic selection.
2. Existing destinations remain Modern without migration work.
3. Modern Teams payloads remain unchanged.
4. XO Classic renders as a Teams-native Adaptive Card using the approved XO Classic information hierarchy.
5. XO success, failure, and skipped cases pass real Teams acceptance.
6. Teams Classic can be visually adjusted independently of Teams Modern.
7. The architecture is ready to add the remaining integrations one by one.
