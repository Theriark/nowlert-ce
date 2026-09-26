# Prototype WebUI Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task by task. Do not delegate; this session is configured for native implementation.

**Goal:** Port the approved Nowlert CE prototype UI into the real `development` WebUI, preserve application behavior and layouts, remove legacy blue/cyan background bleed, verify the rendered result against the prototype, and push the verified implementation to `development`.

**Architecture:** Selectively port the prototype's dashboard and routing-flow rendering/styles plus its chart and routing-pulse models. Add the approved shared visual treatment as a final, audited stylesheet. Register every new asset in `WebUIService`'s allowlist and in dependency order. Keep app APIs, stored data, authentication, routing/filter behavior, and filter card geometry unchanged.

**Tech Stack:** Python 3.13, pytest, browser-side JavaScript/CSS, Node.js 24, existing CE WebUI runtime.

**Approved design:** `docs/superpowers/specs/2026-09-26-prototype-webui-port-design.md`

## Global Constraints

- Work on the already checked out `development` branch and preserve its existing application wiring.
- Do not port the prototype as a static bundle or overwrite unrelated CE functionality.
- Do not change Routing Flow filter criteria, filter data, layout geometry, graph layout, or operational semantics.
- Keep semantic status colors (including Critical and Shared) intact.
- Remove obsolete affected blue/cyan surface fills at their source where practical; do not hide them under another background layer.
- Dashboard graph stays a thin cumulative yellow step line with delivery pulses and persistent glow, with no dots and no replay control. Keep the plotted series and labels consistent, animate on dashboard entry/login/refresh, and respect reduced motion.
- Verify the running UI visually before claiming success or pushing. Push only the completed, verified change to `origin/development`; do not release to production.

## Review Focus

- Are the visual requirements and exclusions explicit enough to implement without changing approved layouts or routing/filter behavior?
- Does each implementation task have a failing test before its code change and a concrete verification command?
- Does the plan explicitly audit all menu and nested-card backgrounds for old blue/cyan bleed, rather than checking only Dashboard and Routing Flow?
- Are asset allowlisting, load order, cache versioning, docs, full tests, local visual comparison, commit, and push covered?

---

### Task 1: Add deterministic chart and pulse model tests

**Files:**
- Create `tests/webui/test_delivery_chart_model.mjs`
- Create `tests/webui/test_routing_pulse_model.mjs`
- Modify `.github/workflows/ci.yml`

- [ ] Write Node tests for cumulative bucket totals, step-path labels/coordinates, delivery pulse timing, and animation restart decisions. Include checks that the graph rendering contract does not require dots or a replay button.
- [ ] Write Node tests for direct, filtered, and mixed route topologies; cover filter content and geometry separately with DOM/CSS presentation regressions in Task 3.
- [ ] Run both tests before implementations and confirm they fail because the models/tests are not yet integrated.
- [ ] Add Node 24 test execution to CI after Node setup, keeping the existing syntax checks.
- [ ] Run `node --test tests/webui/test_delivery_chart_model.mjs tests/webui/test_routing_pulse_model.mjs` and confirm expected initial failures.

### Task 2: Implement the Dashboard chart model and renderer

**Files:**
- Create `src/webui/delivery_chart_model.js`
- Modify `src/webui/operations_dashboard.js`
- Modify `src/webui/operations_dashboard.css`
- Modify `src/webui/operations_acceptance.css`
- Modify `tests/test_operations_dashboard_revamp.py`
- Modify `docs/webui.md`

- [ ] Implement the tested `window.NowlertDeliveryChart` functions: `buildCumulativeSeries`, `buildStepPath`, `pulseDelay`, and `shouldAnimateRender`.
- [ ] Port the prototype's cumulative step graph and delivery pulses while retaining existing dashboard history controls, refresh, first-paint snapshot behavior, live feed, labels, and event totals.
- [ ] Remove replay UI and point markers; use the approved thin yellow line, continuous soft glow, and accessible reduced-motion behavior. Restart its entrance animation on dashboard entry, login, and refresh.
- [ ] Port approved dashboard card accents, header spacing/alignment, Workspace Summary alignment, and the same detail pulse behavior for System Health and Workspace Summary that the dashboard uses for Recent Activity.
- [ ] Update the old graph expectations in `tests/test_operations_dashboard_revamp.py` to the approved graph and assert existing range/feed contracts remain intact.
- [ ] Update current WebUI docs to describe the delivered graph and behavior.
- [ ] Run `node --test tests/webui/test_delivery_chart_model.mjs`, `python -m pytest -q tests/test_operations_dashboard_revamp.py tests/test_dashboard_acceptance_followup.py tests/test_dashboard_acceptance_polish.py`, and relevant dashboard syntax checks.

### Task 3: Implement Routing Flow pulse model and rendering

**Files:**
- Create `src/webui/routing_pulse_model.js`
- Modify `src/webui/routing_flow.js`
- Modify `src/webui/routing_flow.css`
- Modify `tests/test_routing_flow_presentation.py`
- Modify `tests/test_routing_flow_layout.py`
- Modify `docs/webui.md`

- [ ] Implement tested `window.NowlertRoutingPulseModel.resolveNodeModes(graph)` to classify direct-only nodes as yellow, filter-only nodes as grey, and shared endpoints as mixed when both route types exist.
- [ ] Port the prototype's approved soft pulse rendering and line/glow dimensions without multiplying decorative lines or changing graph links, positions, filter card geometry/chips/metrics, or filter behavior.
- [ ] Remove yellow corner stripes from the five Routing Flow metric cards; retain the approved accents on routing cards and Recent Deliveries header.
- [ ] Preserve the prototype-approved filter visual treatment and all current filter presentation behavior.
- [ ] Add presentation regressions for direct/filtered/mixed pulse classes, metric-card accent exclusion, and unchanged filter geometry/content contracts.
- [ ] Run `node --test tests/webui/test_routing_pulse_model.mjs` and `python -m pytest -q tests/test_routing_flow_presentation.py tests/test_routing_flow_layout.py tests/test_routing_flow_runtime_telemetry.py tests/test_filtering_routing_acceptance_regressions.py`.

### Task 4: Port and audit shared surface styling

**Files:**
- Create `src/webui/visual_refinement.css`
- Modify affected legacy surface rules in `src/webui/styles.css`, `src/webui/operations_dashboard.css`, `src/webui/routing_flow.css`, `src/webui/audit_log_refinement.css`, `src/webui/email_alerts.css`, `src/webui/enhancements.css`, `src/webui/management_consistency.css`, `src/webui/professional.css`, and other files found by the surface audit
- Create `tests/test_webui_prototype_theme.py`

- [ ] Port the prototype's approved charcoal panel backgrounds, yellow upper-left accents, title/divider treatment, and page-specific exceptions.
- [ ] Search every loaded WebUI stylesheet for old blue/cyan surface fills and identify each box/panel that remains visible across menus and nested menus.
- [ ] Remove or replace affected legacy fills at their source while keeping semantic blue/cyan meanings (for example Information, links, and provider identity) where they are not background surfaces.
- [ ] Keep the Routing Flow filter exception and metric-card stripe exclusion explicit.
- [ ] Add regression checks covering representative menus and nested cards, no unintended legacy surface colors, approved accent placement, semantic-color retention, and the filter/metric exceptions.
- [ ] Run the new theme tests plus existing relevant visual-contract tests (`tests/test_unified_page_headers.py`, `tests/test_audit_log_refinement.py`, `tests/test_email_alert_rules_ux.py`, `tests/test_webui_backups_layout_round13.py`, `tests/test_webui_backups_housekeeping_round14.py`, and `tests/test_webui_backups_compact_round19.py`, `tests/test_management_consistency_ui.py`).

### Task 5: Register assets, load order, and cache version

**Files:**
- Modify `src/webui/service.py`
- Modify `tests/test_webui.py`
- Modify `.github/workflows/ci.yml`

- [ ] Add both model scripts and the shared stylesheet to the strict WebUI asset allowlist.
- [ ] Inject chart model before Dashboard code, pulse model before Routing Flow code, and shared visual CSS after affected page styles.
- [ ] Bump `UI_BUILD` once to a fresh cache version and assert injection order/cache query behavior in tests.
- [ ] Add/adjust service contract checks for the new assets and ensure unknown assets remain rejected.
- [ ] Run `python -m pytest -q tests/test_webui.py tests/test_webui_refresh_cache.py tests/test_webui_first_paint_round11.py` plus `node --check` on every changed JavaScript asset.

### Task 6: Full application and visual verification

**Files:**
- Any implementation files requiring corrections from verification
- `docs/webui.md` if verification reveals a documentation mismatch

- [ ] Run full `python -m pytest -q`, Python compile checks, Node syntax checks, and both new Node test files.
- [ ] Start the development WebUI locally and compare Dashboard and Routing Flow with the approved prototype at the same viewport and interaction state.
- [ ] Visit every menu and representative nested card; inspect for old blue/cyan fills showing through, missing approved background/accents, clipping, spacing drift, or semantic color regressions.
- [ ] Check dashboard animation after login/refresh/navigation, verify graph pulse and no replay/dots, and test reduced-motion behavior.
- [ ] Check direct, filtered, and mixed Routing Flow routes and verify filters remain unchanged.
- [ ] Correct any observed mismatch, rerun the relevant tests, and repeat the visual check until the approved result is met.
- [ ] Review the final diff, ensure no unrelated changes, then create a final implementation commit and push the verified branch to `origin/development`.

## Final acceptance checklist

- [ ] All previously approved Dashboard and Routing Flow behavior matches the prototype.
- [ ] All affected menus and nested panels use the approved surface color, with no old blue/cyan background bleed.
- [ ] No routing, filtering, API, authentication, or stored-data behavior changed.
- [ ] Full tests, syntax checks, and visual checks pass.
- [ ] The implementation is pushed to `development`; no production deployment was triggered.

