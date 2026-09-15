# Filtering and Settings Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Filtering the single destination delivery-policy authority, simplify Settings to normalization/input-processing configuration, and finish the Administration/profile menu cleanup.

**Architecture:** Extend destination filter persistence/API/UI to model ordered rule actions (`allow` / `block`) while preserving legacy filter payloads as `allow`. Retire router-global Dell suppression and presentation toggles, migrate legacy settings safely, and reorganize the WebUI shell so Settings is an Administration child and the profile menu only contains API access, Security, and Sign out.

**Tech Stack:** Python 3, SQLite settings/destination filter stores, vanilla JavaScript WebUI, pytest, GitHub Actions/Docker deployment gates.

**Spec:** `docs/superpowers/specs/2026-09-15-filtering-settings-simplification-design.md`

## Global Constraints

- Full payload is parsed/normalized deterministically before destination Filtering.
- Filtering exposes stable normalized fields only; arbitrary raw JSON paths are not user-configurable.
- BLOCK matches override ALLOW matches.
- Legacy single-clause filters remain valid as ALLOW filters.
- Existing destination ownership/delegation permissions remain unchanged.
- UniFi/Home Assistant aliases and Redfish deduplication remain Settings concerns.
- XO/Zabbix presentation toggles and Dell router-global suppression are retired.
- No Sources, Routes, Inputs, API access, Users, Settings, Updates, or Data tools standalone sidebar items are reintroduced.
- Actual implementation is delivered as one atomic feature commit after tests are assembled.

---

### Task 1: Add action-aware destination filtering

**Files:**
- Modify: `src/storage/filtering.py`
- Modify: `src/storage/filtering_toggle.py`
- Modify: `src/api/filtering.py`
- Test: `tests/test_destination_filtering.py`
- Test: `tests/test_destination_access_control.py`

**Interfaces:**
- Consumes: current destination/source filter policy persistence in `destination_filters.clauses_json`.
- Produces: public filter policy with `rules` entries shaped as `{action: "allow"|"block", conditions: {...}}`, plus backward compatibility for legacy `rules` objects.

- [ ] **Step 1: Write failing storage tests**

Add tests proving:

```python
assert store.matches(actor, destination_id, dell_login_from_trusted_ip) is False
assert store.matches(actor, destination_id, dell_login_from_other_ip) is True
assert store.matches(actor, destination_id, allowed_matching_event) is True
assert store.matches(actor, destination_id, allowed_nonmatching_event) is False
```

and BLOCK wins when both BLOCK and ALLOW match.

- [ ] **Step 2: Verify those tests fail**

Run:

```bash
pytest -q tests/test_destination_filtering.py -k "block or allow"
```

Expected: failures because current policies contain only clauses with implicit allow semantics.

- [ ] **Step 3: Implement action-aware policy normalization and matching**

Persist action-aware rules in the existing JSON column using a versioned document, while decoding current clause lists as ALLOW rules. Normalize action to exactly `allow` or `block`; reject unknown actions. Matching algorithm:

```python
block_rules = [rule for rule in rules if rule["action"] == "block"]
allow_rules = [rule for rule in rules if rule["action"] == "allow"]
if any(matches(rule) for rule in block_rules):
    return False
if allow_rules:
    return any(matches(rule) for rule in allow_rules)
return True
```

Keep `filter_enabled` behavior non-destructive.

- [ ] **Step 4: Extend API read/write compatibility**

`PUT /api/v2/filters/destinations/{id}/sources/{source}` accepts `policy` with action-aware rules, while still accepting existing `rules` as one ALLOW rule for compatibility. API responses expose action-aware rules for the new UI without breaking legacy readers.

- [ ] **Step 5: Run focused tests**

```bash
pytest -q tests/test_destination_filtering.py tests/test_destination_access_control.py
```

Expected: all pass.

---

### Task 2: Move Dell trusted-client suppression into Filtering

**Files:**
- Modify: `src/storage/settings.py`
- Modify: `src/storage/configuration_sync.py`
- Modify: `src/router.py`
- Modify: `src/api/filtering.py`
- Test: `tests/test_redfish.py`
- Test: `tests/test_unified_configuration.py`
- Test: `tests/test_router.py`
- Test: `tests/test_destination_filtering.py`

**Interfaces:**
- Consumes: legacy `notifications.dell_idrac.suppress_ipmi_session_audit_from` and database integration setting.
- Produces: idempotent Dell BLOCK rules using `message_id in {USR0030, USR0032}` AND `source_ip in trusted_ips` for destinations with Dell available.

- [ ] **Step 1: Write failing migration and router tests**

Assert the router no longer has/uses `_notification_suppressed`, and a configured trusted IP is represented by destination filter policy rather than a global Settings decision.

- [ ] **Step 2: Verify failures**

```bash
pytest -q tests/test_redfish.py tests/test_router.py tests/test_unified_configuration.py tests/test_destination_filtering.py -k "trusted or suppress or migration"
```

- [ ] **Step 3: Add idempotent migration**

During database-authoritative synchronization/API filter-store initialization, read legacy trusted IPs once, create equivalent BLOCK rules for every destination where Dell iDRAC is available, avoid duplicate signatures, then rewrite/remove the obsolete Dell integration setting.

- [ ] **Step 4: Remove router-global suppression**

Delete the early `if self._notification_suppressed(notification): return True` branch and the helper implementation. Database routing now relies on destination Filtering only.

- [ ] **Step 5: Verify focused tests**

Run the same focused pytest command; expected all pass.

---

### Task 3: Retire XO/Zabbix presentation switches and simplify Settings backend

**Files:**
- Modify: `src/storage/settings.py`
- Modify: `src/storage/configuration_sync.py`
- Modify: `src/formatters/teams.py`
- Modify: `src/formatters/discord.py`
- Modify: `src/formatters/teams_zabbix.py`
- Modify: `src/formatters/discord_zabbix.py`
- Test: `tests/test_presentation_contract.py`
- Test: `tests/test_unified_configuration.py`

**Interfaces:**
- Consumes: normalized XO/Zabbix IDs already present on notifications.
- Produces: deterministic formatter output independent of `show_ids` settings.

- [ ] **Step 1: Write failing formatter/settings tests**

Assert changing/removing legacy `show_ids` cannot alter rendered output, and normalized settings no longer expose XO/Zabbix presentation controls.

- [ ] **Step 2: Verify failures**

```bash
pytest -q tests/test_presentation_contract.py tests/test_unified_configuration.py -k "show_ids or deterministic"
```

- [ ] **Step 3: Remove formatter configuration branches**

Choose the existing default deterministic presentation as the canonical formatter contract; IDs continue to exist in normalized notification data and filtering schemas.

- [ ] **Step 4: Make Settings migration tolerant then canonical**

Legacy rows/config may contain `show_ids`; migration accepts and strips them, but newly persisted/default integration settings contain only UniFi aliases, Home Assistant aliases, and Redfish processing configuration.

- [ ] **Step 5: Run focused tests**

Expected all pass.

---

### Task 4: Update Filtering WebUI for ALLOW/BLOCK policies

**Files:**
- Modify: `src/webui/filtering.js`
- Modify: `src/webui/filtering.css`
- Test: `tests/test_filtering_reference_ui.py`
- Test: `tests/test_filtering_ui_polish.py`

**Interfaces:**
- Consumes: action-aware filter policy from `/api/v2/filters/...`.
- Produces: editor that clearly creates ALLOW and BLOCK rules and summaries showing action.

- [ ] **Step 1: Write failing static UI contract tests**

Require visible `Allow` / `Block` rule actions and updated summary copy; reject the old single-rule-only editor contract.

- [ ] **Step 2: Verify tests fail**

```bash
pytest -q tests/test_filtering_reference_ui.py tests/test_filtering_ui_polish.py
```

- [ ] **Step 3: Implement editor**

Add a rule-action selector and rule list. Each rule holds an action and condition map; fields inside one rule are AND, multiple rules are OR within each action. Summaries display `ALLOW` or `BLOCK` chips. Keep owner/delegated read-only behavior intact.

- [ ] **Step 4: Save action-aware policy through API**

Use the new `policy` body. Legacy responses are upgraded in-memory to a single ALLOW rule.

- [ ] **Step 5: Run UI tests**

Expected all pass.

---

### Task 5: Simplify Administration Settings and profile menu

**Files:**
- Modify: `src/webui/access_control.js`
- Modify: `src/webui/index.html`
- Modify: `src/webui/app.js`
- Modify: `src/webui/styles.css`
- Modify: `src/webui/qa_patch.css` only if needed for current menu overrides
- Test: `tests/test_admin_user_webui_access.py`
- Test: `tests/test_webui.py`

**Interfaces:**
- Consumes: existing `view-settings`, integration settings editor, profile menu.
- Produces: Administration tabs `Users | Settings | Updates | Data tools`; profile menu `API access | Security | Sign out` with aligned icon/text structure.

- [ ] **Step 1: Write failing WebUI shell tests**

Require:

```text
Administration: Users | Settings | Updates | Data tools
Profile: API access | Security | Sign out
```

and assert `profile-settings` is absent while API access contains the same icon/text structure as existing profile items.

- [ ] **Step 2: Verify failures**

```bash
pytest -q tests/test_admin_user_webui_access.py tests/test_webui.py -k "administration or profile or settings"
```

- [ ] **Step 3: Move Settings into Administration**

Add `settings` to the Administration child-view set and tab labels. Keep it admin-only. Remove its dynamic profile entry.

- [ ] **Step 4: Normalize profile menu markup/styles**

Create API access with an icon span plus label span and reuse the same row structure/spacing as Security and Sign out. Do not restore the chevron.

- [ ] **Step 5: Simplify Settings content**

Rename/restructure the integration section into:

```text
Aliases & normalization
- UniFi Protect device aliases
- Home Assistant endpoint aliases
- Home Assistant component aliases

Event processing
- Redfish duplicate-event window
```

Remove XO, Zabbix, and Dell cards/dialogs and the `Notification policies and aliases` heading.

- [ ] **Step 6: Run WebUI tests**

Expected all pass.

---

### Task 6: Full verification and atomic integration

**Files:**
- Add/update regression tests only as required by failures attributable to this feature.

- [ ] **Step 1: Run the complete automated suite**

```bash
pytest -q
```

Expected: zero failures.

- [ ] **Step 2: Validate Python syntax**

```bash
python -m compileall -q src tests
```

Expected: exit 0.

- [ ] **Step 3: Validate WebUI JavaScript syntax**

Run the repository's CI-equivalent Node syntax checks against all WebUI JS files. Expected: exit 0.

- [ ] **Step 4: Assemble one atomic implementation commit**

All source and regression-test changes are committed together on the isolated feature branch with message:

```text
Simplify filtering and administration settings
```

- [ ] **Step 5: Open one PR to `development` and wait for CI**

Do not make unrelated changes. If CI fails, fix only the demonstrated feature regression and re-squash back to one feature commit before the next run.

- [ ] **Step 6: Merge only after green CI**

After merge, wait for the Development push workflow to pass tests, image build/publish, SHA-to-digest verification, image version/owl verification, exact SHA deployment, and immutable result recording.

- [ ] **Step 7: Resume full acceptance**

Start with Administration/profile/Settings/Filtering simplification, then continue the previously defined Admin/User destination permission and privacy acceptance.
