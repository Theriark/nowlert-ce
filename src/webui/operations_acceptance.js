"use strict";

/* Final acceptance corrections for Operations Dashboard and Routing Flow. */
(() => {
  const DASHBOARD_FEED_KEYS = ["metrics", "deliveries", "filters", "audit"];
  const DASHBOARD_LIVE_MS = 70_000;
  const DASHBOARD_STALE_MS = 120_000;
  const FLOW_LIVE_MS = 15_000;
  const DASHBOARD_RANGES = new Set(["10m", "1h", "1d", "1m", "1y"]);
  const FLOW_RANGES = new Set(["10m", "1h", "1d", "1m", "1y"]);
  const WORKSPACE_SUMMARY_ITEMS = [
    { key: "tokens", valueId: "ops-config-tokens" },
    { key: "filters", valueId: "ops-config-filters" },
    { key: "shared", valueId: "ops-config-shared" },
    { key: "audit", valueId: "ops-config-audit" },
  ];
  const dashboardFeeds = Object.fromEntries(
    DASHBOARD_FEED_KEYS.map(key => [key, { lastAttempt: 0, lastSuccess: 0, ok: null }]),
  );

  let dashboardLastCompleteAt = 0;
  let dashboardRefreshBatch = null;
  let flowLastAttempt = 0;
  let flowLastSuccess = 0;
  let flowLatestOk = null;
  let lastUserKey = "";
  let statusClock = null;

  function element(tag, className = "", text = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== "") item.textContent = String(text);
    return item;
  }

  function ageText(timestamp, now = Date.now()) {
    if (!timestamp) return "never";
    const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
    if (seconds < 5) return "just now";
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    return `${Math.floor(minutes / 60)}h ago`;
  }

  function authenticatedUserKey() {
    if (!state.user) return "";
    const identity = state.user.id ?? state.user.username ?? "";
    return identity === "" ? "" : encodeURIComponent(String(identity));
  }

  function storageKey(scope) {
    const user = authenticatedUserKey();
    return user ? `nowlert:${user}:${scope}` : "";
  }

  function readStoredRange(scope) {
    const key = storageKey(scope);
    if (!key) return "";
    try {
      return window.localStorage.getItem(key) || "";
    } catch (_error) {
      return "";
    }
  }

  function readStoredRangeForSession(session, scope) {
    const identity = session?.user?.id ?? session?.user?.username ?? "";
    if (identity === "") return "";
    const key = `nowlert:${encodeURIComponent(String(identity))}:${scope}`;
    try {
      return window.localStorage.getItem(key) || "";
    } catch (_error) {
      return "";
    }
  }

  function cachedDashboardTimestamp() {
    const user = authenticatedUserKey();
    const range = Object.hasOwn(
      { "10m": true, "1h": true, "1d": true, "1m": true, "1y": true },
      state.historyRange,
    ) ? state.historyRange : "1h";
    if (!user) return 0;
    try {
      const key = `nowlert.dashboard-first-paint:v1:${user}:${range}`;
      const snapshot = JSON.parse(window.sessionStorage.getItem(key) || "null");
      const savedAt = Number(snapshot?.saved_at || 0);
      return Number.isFinite(savedAt) && savedAt > 0 ? savedAt : 0;
    } catch (_error) {
      return 0;
    }
  }

  function workspaceDashboardTimestamp() {
    const loadedAt = Number(state.workspaceLoadedAt || 0);
    if (!loadedAt || !state.metrics || !state.filteringOverview) return 0;
    const failures = new Set((state.workspaceErrors || []).map(item => item.component));
    if (
      failures.has("Overview metrics")
      || failures.has("Delivery history")
      || failures.has("Filtering")
      || failures.has("Audit log")
    ) return 0;
    return loadedAt;
  }

  function writeStoredRange(scope, value) {
    const key = storageKey(scope);
    if (!key) return;
    try {
      window.localStorage.setItem(key, value);
    } catch (_error) {
      // Browser storage is optional. The range still works for the current page.
    }
  }

  function bindRange(select, scope, allowed) {
    if (!select || select.dataset.rangePersistence === "1") return;
    select.dataset.rangePersistence = "1";
    select.addEventListener("change", () => {
      if (allowed.has(select.value)) writeStoredRange(scope, select.value);
    });
  }

  function restoreRange(select, scope, allowed) {
    if (!select || !state.user) return;
    const stored = readStoredRange(scope);
    if (!allowed.has(stored) || stored === select.value) return;
    if (![...select.options].some(option => option.value === stored)) return;
    select.value = stored;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function bindRangePersistence() {
    const dashboard = byId("ops-dashboard-range");
    const flow = byId("rf-range");
    bindRange(dashboard, "dashboard-range", DASHBOARD_RANGES);
    bindRange(flow, "routing-flow-range", FLOW_RANGES);
  }

  function restorePersistedRanges(view = state.currentView) {
    if (!state.user) return;
    bindRangePersistence();
    if (view === "dashboard") {
      restoreRange(byId("ops-dashboard-range"), "dashboard-range", DASHBOARD_RANGES);
    }
    if (view === "routing-flow") {
      restoreRange(byId("rf-range"), "routing-flow-range", FLOW_RANGES);
    }
  }

  function compactPercentages() {
    for (const item of document.querySelectorAll(
      "#ops-kpi-success, #ops-success-delta strong, #ops-failure-delta strong, .ops-summary-metric.success strong",
    )) {
      const current = item.textContent;
      const compact = current.replace(/(\d+)\.0%/g, "$1%");
      if (compact !== current) item.textContent = compact;
    }
  }

  function ensureDashboardStatus() {
    const container = document.querySelector(".ops-live");
    if (!container) return null;
    if (container.dataset.liveContract !== "data-feed") {
      const dot = element("span", "ops-live-dot");
      dot.setAttribute("aria-hidden", "true");
      const copy = element("span");
      const label = element("strong", "", "Connecting");
      label.id = "ops-feed-state";
      const age = element("small", "", "Waiting for dashboard data");
      age.id = "ops-feed-age";
      copy.append(label, age);
      byId("ops-live-age")?.removeAttribute("id");
      container.replaceChildren(dot, copy);
      container.dataset.liveContract = "data-feed";
      container.setAttribute("aria-live", "polite");
      container.title = "Live means Nowlert successfully refreshed Dashboard metrics, deliveries, filtering, and audit data within the freshness window; it is not an external integration heartbeat.";
    }
    return container;
  }

  function dashboardFeedStatus(now = Date.now()) {
    const states = DASHBOARD_FEED_KEYS.map(key => dashboardFeeds[key]);
    const attempted = states.filter(item => item.lastAttempt);
    if (!attempted.length) {
      const readyAt = Math.max(
        workspaceDashboardTimestamp(),
        cachedDashboardTimestamp(),
      );
      if (readyAt && now - readyAt <= DASHBOARD_LIVE_MS) {
        return { name: "Live", kind: "live", detail: `Data updated ${ageText(readyAt, now)}` };
      }
      if (readyAt && now - readyAt <= DASHBOARD_STALE_MS) {
        return { name: "Stale", kind: "stale", detail: `Last good data ${ageText(readyAt, now)}` };
      }
      return { name: "Connecting", kind: "connecting", detail: "Waiting for dashboard data" };
    }

    const allAttempted = states.every(item => item.lastAttempt);
    const allSucceeded = states.every(item => item.lastSuccess);
    const allLatestOk = states.every(item => item.ok === true);
    const successes = states.map(item => item.lastSuccess).filter(Boolean);
    const newestSuccess = successes.length ? Math.max(...successes) : 0;
    const oldestSuccess = allSucceeded ? Math.min(...successes) : 0;

    if (allAttempted && allSucceeded && allLatestOk && now - oldestSuccess <= DASHBOARD_LIVE_MS) {
      return { name: "Live", kind: "live", detail: `Data updated ${ageText(oldestSuccess, now)}` };
    }
    if (!newestSuccess && allAttempted) {
      return { name: "Offline", kind: "offline", detail: "Dashboard data unavailable" };
    }
    if (newestSuccess && now - newestSuccess > DASHBOARD_STALE_MS) {
      return { name: "Stale", kind: "stale", detail: `Last good data ${ageText(newestSuccess, now)}` };
    }
    if (allAttempted) {
      return {
        name: "Degraded",
        kind: "degraded",
        detail: dashboardLastCompleteAt
          ? `Partial data · last complete ${ageText(dashboardLastCompleteAt, now)}`
          : `Partial data · last good ${ageText(newestSuccess, now)}`,
      };
    }
    return { name: "Connecting", kind: "connecting", detail: "Waiting for all dashboard data" };
  }

  function updateDashboardStatus() {
    const container = ensureDashboardStatus();
    if (!container) return;
    const status = dashboardFeedStatus();
    container.classList.remove("is-live", "is-degraded", "is-stale", "is-offline", "is-connecting");
    container.classList.add(`is-${status.kind}`);
    byId("ops-feed-state").textContent = status.name;
    byId("ops-feed-age").textContent = status.detail;
  }

  function dashboardFeedKey(path) {
    const value = String(path || "");
    if (value.startsWith("/metrics/")) return "metrics";
    if (value === "/deliveries") return "deliveries";
    if (value === "/filters") return "filters";
    if (value === "/audit-events") return "audit";
    return "";
  }

  function beginDashboardRefreshRequest(key) {
    if (state.currentView !== "dashboard") return null;
    if (!dashboardRefreshBatch) {
      dashboardRefreshBatch = {
        started: new Set(),
        pending: new Set(),
        results: new Map(),
      };
    }
    const batch = dashboardRefreshBatch;
    batch.started.add(key);
    batch.pending.add(key);
    return batch;
  }

  function commitDashboardRefreshBatch(batch) {
    if (!batch || dashboardRefreshBatch !== batch) return;
    if (batch.pending.size) return;
    dashboardRefreshBatch = null;
    if (!DASHBOARD_FEED_KEYS.every(key => batch.started.has(key))) return;

    const now = Date.now();
    for (const key of DASHBOARD_FEED_KEYS) {
      const feed = dashboardFeeds[key];
      const ok = batch.results.get(key) === true;
      feed.lastAttempt = now;
      feed.ok = ok;
      if (ok) feed.lastSuccess = now;
    }
    if (DASHBOARD_FEED_KEYS.every(key => batch.results.get(key) === true)) {
      dashboardLastCompleteAt = now;
    }
    updateDashboardStatus();
  }

  function finishDashboardRefreshRequest(batch, key, ok) {
    if (!batch || dashboardRefreshBatch !== batch) return;
    batch.results.set(key, Boolean(ok));
    batch.pending.delete(key);
    commitDashboardRefreshBatch(batch);
  }

  function ensureRoutingFlowStatus() {
    const toolbar = document.querySelector("#view-routing-flow .rf-toolbar");
    const range = byId("rf-range")?.closest(".rf-range");
    if (!toolbar || !range) return null;
    let container = byId("rf-live-status");
    if (!container) {
      container = element("span", "rf-live-status is-connecting");
      container.id = "rf-live-status";
      container.setAttribute("aria-live", "polite");
      container.title = "Live means Nowlert received a successful fresh Routing Flow snapshot within the last 15 seconds; it is not an integration or destination heartbeat.";
      const dot = element("span", "rf-live-dot");
      dot.setAttribute("aria-hidden", "true");
      const copy = element("span", "rf-live-copy");
      const label = element("strong", "", "Connecting");
      label.id = "rf-live-label";
      const age = element("small", "", "Waiting for snapshot");
      age.id = "rf-live-age";
      copy.append(label, age);
      container.append(dot, copy);
      toolbar.insertBefore(container, range);
    }
    return container;
  }

  function cachedRoutingFlowTimestamp() {
    const range = byId("rf-range")?.value || "1d";
    const cached = state.routingFlowSnapshots && state.routingFlowSnapshots[range];
    if (!cached) return 0;
    const raw = Number(cached.generated_at || cached.generatedAt || 0);
    if (!Number.isFinite(raw) || raw <= 0) return Date.now();
    return raw < 10_000_000_000 ? raw * 1000 : raw;
  }

  function routingFlowStatus(now = Date.now()) {
    if (!flowLastAttempt && !flowLastSuccess) {
      const cachedAt = cachedRoutingFlowTimestamp();
      if (cachedAt) {
        flowLastSuccess = cachedAt;
        flowLatestOk = true;
      }
    }
    if (!flowLastAttempt && !flowLastSuccess) {
      return { name: "Connecting", kind: "connecting", detail: "Waiting for snapshot" };
    }
    if (flowLatestOk === true && flowLastSuccess && now - flowLastSuccess <= FLOW_LIVE_MS) {
      return { name: "Live", kind: "live", detail: `Snapshot ${ageText(flowLastSuccess, now)}` };
    }
    if (flowLastSuccess) {
      return { name: "Stale", kind: "stale", detail: `Retrying · last good ${ageText(flowLastSuccess, now)}` };
    }
    if (flowLatestOk === false) {
      return { name: "Offline", kind: "offline", detail: "No successful snapshot" };
    }
    return { name: "Connecting", kind: "connecting", detail: "Waiting for snapshot" };
  }

  function updateRoutingFlowStatus() {
    const container = ensureRoutingFlowStatus();
    if (!container) return;
    const status = routingFlowStatus();
    container.classList.remove("is-live", "is-stale", "is-offline", "is-connecting");
    container.classList.add(`is-${status.kind}`);
    byId("rf-live-label").textContent = status.name;
    byId("rf-live-age").textContent = status.detail;
  }

  function ensureDashboardToolbar() {
    const dashboard = byId("view-dashboard");
    const controls = byId("ops-dashboard-top-actions");
    if (!dashboard || !controls) return null;

    let toolbar = dashboard.querySelector(":scope > .ops-dashboard-toolbar");
    if (!toolbar) {
      toolbar = element("div", "section-toolbar ops-dashboard-toolbar");
      const copy = element("div", "ops-dashboard-toolbar-copy");
      copy.append(
        element("h2", "", "Dashboard"),
        element("p", "", "Monitor your alert delivery pipeline and system health."),
      );
      toolbar.append(copy);
      dashboard.prepend(toolbar);
    }

    const live = controls.querySelector(".ops-live");
    const range = byId("ops-dashboard-range")?.closest("label");
    if (live && range && (controls.firstElementChild !== live || live.nextElementSibling !== range)) {
      controls.append(live, range);
    }
    const unifiedHeaderOwnsControls = document.querySelector(".topbar.page-command-bar");
    if (!unifiedHeaderOwnsControls && controls.parentElement !== toolbar) toolbar.append(controls);
    controls.hidden = state.currentView !== "dashboard";
    byId("page-title")?.removeAttribute("data-dashboard-subtitle");
    return toolbar;
  }

  function polishDashboardRange() {
    const select = byId("ops-dashboard-range");
    const control = select?.closest("label");
    if (!control) return;
    control.querySelector(".ops-calendar")?.remove();
    if (control.classList.contains("ops-global-range")) {
      control.classList.remove("ops-global-range");
      control.classList.add("rf-range", "ops-dashboard-range-control");
    }
  }

  function workspaceSummaryStatus(key, value) {
    const count = Number.parseInt(String(value || "0").replace(/,/g, ""), 10) || 0;
    if (key === "tokens") return { label: count ? "Healthy" : "No tokens", tone: count ? "healthy" : "neutral" };
    if (key === "filters") return { label: count ? "Active" : "No filters", tone: count ? "healthy" : "neutral" };
    if (key === "shared") return { label: count ? "Shared" : "Not shared", tone: count ? "shared" : "neutral" };
    return { label: count ? "Review" : "Clear", tone: count ? "review" : "healthy" };
  }

  function ensureWorkspaceSummary() {
    const strip = document.querySelector("#view-dashboard .ops-configuration");
    if (!strip) return;

    let summary = strip.querySelector(":scope > .ops-config-heading");
    if (!summary) {
      summary = element("div", "ops-config-heading");
      strip.prepend(summary);
    }
    if (summary.dataset.workspaceSummary !== "1") {
      summary.className = "ops-config-heading ops-workspace-summary";
      const icon = element("span", "ops-workspace-summary-icon");
      icon.setAttribute("aria-hidden", "true");
      for (let index = 0; index < 4; index += 1) icon.append(element("i"));
      const copy = element("span", "ops-workspace-summary-copy");
      copy.append(
        element("strong", "", "Workspace Summary"),
        element("small", "", "Quick overview of configuration and collaboration"),
      );
      summary.replaceChildren(icon, copy);
      summary.dataset.workspaceSummary = "1";
    }

    for (const { key, valueId } of WORKSPACE_SUMMARY_ITEMS) {
      const value = byId(valueId);
      const item = value?.closest(".ops-config-item");
      if (!value || !item) continue;
      let status = item.querySelector(`[data-summary-status="${key}"]`);
      if (!status) {
        status = element("span", "ops-config-status");
        status.setAttribute("data-summary-status", key);
        item.append(status);
      }
      const next = workspaceSummaryStatus(key, value.textContent);
      const nextClass = `ops-config-status is-${next.tone}`;
      if (status.className !== nextClass) status.className = nextClass;
      if (status.dataset.statusLabel !== next.label) {
        const dot = element("i", "ops-config-status-dot");
        dot.setAttribute("aria-hidden", "true");
        status.replaceChildren(dot, document.createTextNode(next.label));
        status.dataset.statusLabel = next.label;
      }
    }
  }

  function polishAdministrationTabs() {
    for (const view of ["users", "settings", "updates", "data"]) {
      const section = byId(`view-${view}`);
      const toolbar = section?.querySelector(":scope > .section-toolbar");
      const tabs = section?.querySelector(":scope > .administration-tabs");
      if (!toolbar || !tabs || toolbar.nextElementSibling === tabs) continue;
      toolbar.after(tabs);
    }
  }

  function polishDashboardStructure() {
    document.querySelector("#view-dashboard .ops-delivery-panel .ops-range")?.remove();
    document.querySelectorAll("#view-dashboard .ops-kpi-config .ops-kpi-delta").forEach(item => item.remove());

    const integrationNote = document.querySelector('[data-kpi="integrations"] .ops-kpi-copy small');
    const destinationNote = document.querySelector('[data-kpi="destinations"] .ops-kpi-copy small');
    const routeNote = document.querySelector('[data-kpi="routes"] .ops-kpi-copy small');
    if (integrationNote && integrationNote.textContent !== "Used by active routes") integrationNote.textContent = "Used by active routes";
    if (destinationNote && destinationNote.textContent !== "Enabled destinations") destinationNote.textContent = "Enabled destinations";
    if (routeNote && routeNote.textContent !== "Enabled routing rules") routeNote.textContent = "Enabled routing rules";

    polishDashboardRange();
    ensureWorkspaceSummary();
    ensureDashboardToolbar();
    ensureDashboardStatus();
    bindRangePersistence();
    compactPercentages();
  }

  const previousRequest = request;
  request = async function operationsAcceptanceRequest(path, options = {}) {
    if (!options.dashboardFeed) return previousRequest(path, options);
    const key = dashboardFeedKey(path);
    if (!key || state.currentView !== "dashboard") return previousRequest(path, options);
    syncAuthenticatedUser();
    const batch = beginDashboardRefreshRequest(key);
    try {
      const response = await previousRequest(path, options);
      finishDashboardRefreshRequest(batch, key, true);
      return response;
    } catch (error) {
      finishDashboardRefreshRequest(batch, key, false);
      throw error;
    }
  };

  const previousFetch = window.fetch.bind(window);
  window.fetch = async function operationsAcceptanceFetch(input, init = {}) {
    const url = typeof input === "string" ? input : (input && input.url) || String(input || "");
    const routingFlowRequest = url.includes("/api/v2/routing-flow/");
    if (!routingFlowRequest) return previousFetch(input, init);
    flowLastAttempt = Date.now();
    updateRoutingFlowStatus();
    try {
      const response = await previousFetch(input, init);
      flowLatestOk = response.ok;
      if (response.ok) flowLastSuccess = Date.now();
      updateRoutingFlowStatus();
      return response;
    } catch (error) {
      if (error?.name !== "AbortError") flowLatestOk = false;
      updateRoutingFlowStatus();
      throw error;
    }
  };

  const previousNavigate = navigate;
  navigate = function operationsAcceptanceNavigate(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    window.queueMicrotask(() => {
      polishDashboardStructure();
      polishAdministrationTabs();
      ensureRoutingFlowStatus();
      restorePersistedRanges(view);
      updateDashboardStatus();
      updateRoutingFlowStatus();
    });
    return result;
  };

  const previousShowApp = showApp;
  showApp = function operationsAcceptanceShowApp(session) {
    // Restore the Dashboard window before wrapped showApp() calls navigate().
    // That prevents the first Dashboard request and first paint from using the
    // default 1h window before the persisted selection is applied.
    const storedDashboardRange = readStoredRangeForSession(session, "dashboard-range");
    if (DASHBOARD_RANGES.has(storedDashboardRange)) {
      state.historyRange = storedDashboardRange;
    }
    const result = previousShowApp(session);
    syncAuthenticatedUser();
    return result;
  };

  function resetLiveState() {
    for (const key of DASHBOARD_FEED_KEYS) {
      dashboardFeeds[key] = { lastAttempt: 0, lastSuccess: 0, ok: null };
    }
    dashboardLastCompleteAt = 0;
    dashboardRefreshBatch = null;
    flowLastAttempt = 0;
    flowLastSuccess = 0;
    flowLatestOk = null;
    updateDashboardStatus();
    updateRoutingFlowStatus();
  }

  function syncAuthenticatedUser() {
    const current = authenticatedUserKey();
    if (current === lastUserKey) return;
    lastUserKey = current;
    resetLiveState();
    if (!current) return;
    restorePersistedRanges("dashboard");
    restorePersistedRanges("routing-flow");
  }

  polishDashboardStructure();
  polishAdministrationTabs();
  ensureRoutingFlowStatus();
  bindRangePersistence();

  document.addEventListener("nowlert:workspace-loaded", () => {
    updateDashboardStatus();
  });

  const dashboard = byId("view-dashboard");
  if (dashboard) {
    new MutationObserver(() => {
      polishDashboardStructure();
    }).observe(dashboard, { childList: true, subtree: true, characterData: true });
  }

  statusClock = window.setInterval(() => {
    syncAuthenticatedUser();
    updateDashboardStatus();
    updateRoutingFlowStatus();
  }, 1_000);

  window.addEventListener("beforeunload", () => {
    window.clearInterval(statusClock);
  });
})();