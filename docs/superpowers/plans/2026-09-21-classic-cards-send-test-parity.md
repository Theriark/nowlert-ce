# Classic Cards and Send-Test Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make destination-card Send test a Nowlert-owned notification across Discord, Teams, Slack, and Generic Webhook, and complete Teams Classic coverage for every supported source plus fallback.

**Architecture:** Keep Discord Classic v1 as the semantic source of truth. Extract its neutral Classic Card v1 conversion for reuse, render that neutral model with a new generic Teams Classic Adaptive Card renderer, and remove route-derived identity from destination-card Send test while leaving manual source preview intact.

**Tech Stack:** Python 3, pytest, vanilla JavaScript WebUI, Microsoft Adaptive Card 1.4, Discord embeds/Components V2, Slack Block Kit, Generic Webhook JSON.

**Spec:** docs/superpowers/specs/2026-09-21-classic-cards-send-test-parity-design.md

## Global Constraints

- Send test is always source `nowlert` and never inherits route integration identity.
- Send test must respect the destination's stored Modern/Classic presentation.
- Slack remains Classic-only.
- Discord Classic v1 is the approved Classic semantic source.
- Teams Modern formatter files and output remain unchanged.
- Teams Classic must cover all supported sources plus generic/Nowlert fallback.
- Existing Teams 28 KiB guard, sanitization, transport, and HTTP 202 behavior remain unchanged.
- Generic Webhook transport semantics remain unchanged.
- One implementation candidate is pushed before CI; after green CI merge to `development` and verify post-merge Development deployment.

## Review Focus

- A destination with an attached exact route still sends a Nowlert-owned test rather than the route source.
- Teams Classic unknown source uses Nowlert icon rather than rendering with no icon.
- Explicit Teams preview/test `message_style` override is honored without mutating stored settings.
- Consecutive inline fields are grouped into at most three Teams columns without reordering full-width sections.
- Secret-like strings in Classic content remain redacted before delivery.

---

### Task 1: Unify destination-card Send test identity

**Files:**
- Modify: `src/webui/app.js`
- Modify: `src/webui/enhancements.js`
- Modify: `tests/test_v232_operations.py`
- Modify: `tests/test_webui.py`

**Interfaces:**
- Produces: `cardSampleEvent(destination)` returning one `nowlert.event.v1` event with `source="nowlert"`.
- Manual preview continues to use `sampleEvent()`.

- [ ] Add tests that the destination-card event includes source `nowlert`, provider `Nowlert`, Destination test component, destination name, and output family.
- [ ] Add a regression that `enhancements.js` no longer overrides `cardSampleEvent` with route-aware source selection.
- [ ] Verify those tests fail on the current tree.
- [ ] Remove the route-aware `cardSampleEvent` override from `enhancements.js`.
- [ ] Keep/adjust base `cardSampleEvent` in `app.js` so it is the single destination-card test generator.
- [ ] Run focused WebUI tests and verify green.

### Task 2: Extract reusable Classic Card v1 conversion

**Files:**
- Create: `src/formatters/classic_card_v1.py`
- Modify: `src/outputs/platform.py`
- Modify: `tests/test_platform_outputs.py`

**Interfaces:**
- Produces: `classic_card_v1_from_discord_payload(payload: dict) -> dict`.
- Generic Webhook Classic continues to get its Discord Classic preview first, then converts through this helper.

- [ ] Move the exact neutral conversion currently in `WebhookPlatformAdapter._classic_card_from_discord_payload` into the new formatter helper.
- [ ] Keep a compatibility wrapper on `WebhookPlatformAdapter` so existing tests/callers remain valid.
- [ ] Add direct helper tests for missing embed, optional fields, inline default, footer, URL, and timestamp.
- [ ] Verify Generic Webhook Classic parity tests remain exact for all current Classic sources.

### Task 3: Generalize Teams Classic to all sources

**Files:**
- Rewrite: `src/formatters/teams_classic_v1.py`
- Modify: `src/outputs/teams.py`
- Modify: `src/outputs/platform.py`
- Modify: `src/outputs/service.py`
- Modify: `tests/test_platform_outputs.py`
- Modify: `tests/test_teams_classic_xo.py`

**Interfaces:**
- Produces: `TeamsClassicFormatter.format(notification) -> Adaptive Card 1.4 payload`.
- `TeamsOutput.classic_formatter` holds the single Classic renderer.
- Teams adapter uses Classic whenever normalized `message_style == "classic"`.

- [ ] Add parametrized failing tests over the full Classic source matrix plus unknown fallback.
- [ ] Assert every Teams Classic preview reports `rendered_style="classic"`, uses `TeamsClassicFormatter`, preserves title/description/field order from the approved Discord Classic model, and stays inside the Teams payload guard for synthetic fixtures.
- [ ] Add fallback icon tests for `nowlert` and unknown source.
- [ ] Add XO regression preserving Duration / Transfer Size / Transfer Speed as the first inline row, then Storage, VM sections, Job ID.
- [ ] Implement `TeamsClassicFormatter`: derive the neutral model from `render_classic_embed_v1`, map color to Teams semantic color, render inline fields in ordered groups of at most three columns, render non-inline fields as separated containers, preserve footer and safe action URL, use notification source icon or Nowlert fallback, sanitize payload.
- [ ] Replace XO-only registry with the single Classic formatter.
- [ ] Remove temporary Modern fallback for unimplemented Classic sources.
- [ ] Add Teams handling to `PlatformOutputService._with_message_style()`.
- [ ] Run Teams/platform tests and existing Teams Modern regressions.

### Task 4: Send-test presentation parity regressions

**Files:**
- Modify: `tests/test_platform_outputs.py`
- Modify: `tests/test_platform_api.py` if the existing service fixture makes style override coverage clearer there.

**Interfaces:**
- Consumes the unified Nowlert test event shape and existing destination settings.

- [ ] Add one Nowlert synthetic notification fixture matching `cardSampleEvent`.
- [ ] Assert Discord Modern uses Components V2 and Nowlert thumbnail identity.
- [ ] Assert Discord Classic uses a Classic embed and Nowlert thumbnail identity.
- [ ] Assert Teams Modern header uses Nowlert source image.
- [ ] Assert Teams Classic header uses Nowlert source image and Classic footer.
- [ ] Assert Slack Classic accessory uses Nowlert image.
- [ ] Assert Generic Webhook Modern presentation is `modern_card` and Classic presentation is `classic_card_v1`, both carrying the same destination-test title/body.
- [ ] Assert explicit Teams `message_style` override affects preview/test without changing the destination's stored settings.

### Task 5: Documentation, verification, PR, merge, deployment

**Files:**
- Modify: `docs/platform-outputs.md`
- Modify: `CHANGELOG.md`

- [ ] Document unified Nowlert-owned destination tests and full Teams Classic coverage.
- [ ] Update changelog.
- [ ] Run the complete repository CI through GitHub Actions on the one pushed implementation candidate.
- [ ] If red, inspect exact failure, make only the required correction, and wait for replacement CI.
- [ ] Whole-branch review: verify Teams Modern formatter files are unchanged and no unrelated platform behavior changed.
- [ ] Merge green PR into `development`.
- [ ] Verify exact post-merge CI and CE Development deployment are green.
