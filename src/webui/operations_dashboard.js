"use strict";

/* Approved Operations Dashboard presentation layered over the existing CE data model. */
(() => {
  const DASHBOARD_VIEW = "dashboard";
  const REFRESH_MS = 30_000;
  const RANGE_SECONDS = {
    "10m": 600,
    "1h": 3_600,
    "1d": 86_400,
    "1m": 31 * 86_400,
    "1y": 366 * 86_400,
  };
  const RANGE_LABELS = {
    "10m": "Last 10 minutes",
    "1h": "Last 1 hour",
    "1d": "Last 24 hours",
    "1m": "Last 1 month",
    "1y": "Last 1 year",
  };
  const DASHBOARD_SNAPSHOT_SCHEMA = 1;
  const DASHBOARD_SNAPSHOT_MAX_AGE_MS = 10 * 60_000;
  const DASHBOARD_SNAPSHOT_PREFIX = "nowlert.dashboard-first-paint";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const ICON_PATHS = {
    integrations: "M8 3v6M16 3v6M5 9h14v3a7 7 0 0 1-7 7v2M9 21h6",
    destinations: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-3a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
    routes: "M4 7h13M14 4l3 3-3 3M20 17H7M10 14l-3 3 3 3",
    success: "M20 6 9 17l-5-5",
    failure: "M12 9v4M12 17h.01M10.3 3.8 2.8 17a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L14.7 3.8a2 2 0 0 0-4.4 0Z",
    key: "M21 2 13.6 9.4a5 5 0 1 0 1 1L17 13h2v2h2v-2l2-2V7l-2-2Z",
    filter: "M3 4h18l-7 8v7l-4 2v-9Z",
    share: "M18 8a3 3 0 1 0-2.8-4M6 15a3 3 0 1 0 0 6M18 14a3 3 0 1 0 0 6M8.7 16.4l6.6-3.2M8.7 19.6l6.6-3.2",
    audit: "M6 3h9l3 3v15H6Zm8 0v4h4M9 12h6M9 16h6",
    api: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7ZM19 12h2M3 12h2M12 3v2M12 19v2M18.4 5.6l-1.4 1.4M7 17l-1.4 1.4M18.4 18.4 17 17M7 7 5.6 5.6",
    delivery: "m3 11 18-8-8 18-2-7Z",
    storage: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Zm0 0v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6m-16 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6",
    retry: "M20 7h-6a7 7 0 1 0 5.5 11.3M20 7l-3-3M20 7l-3 3",
  };

  let filterSnapshot = null;
  let dashboardDeliveries = [];
  let refreshTimer = null;
  let clockTimer = null;
  let refreshBusy = false;
  let refreshPending = false;
  let lastUpdatedAt = 0;

  function node(tag, className = "", text = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== "") item.textContent = String(text);
    return item;
  }

  function dashboardSnapshotIdentity(session) {
    const user = session?.user || state.user;
    const value = user?.id ?? user?.username ?? "";
    return String(value || "").trim();
  }

  function dashboardSnapshotKey(session, range) {
    const identity = dashboardSnapshotIdentity(session);
    if (!identity || !Object.hasOwn(RANGE_LABELS, range)) return "";
    return `${DASHBOARD_SNAPSHOT_PREFIX}:v${DASHBOARD_SNAPSHOT_SCHEMA}:${encodeURIComponent(identity)}:${range}`;
  }

  function restoreDashboardSnapshot(session, range) {
    const key = dashboardSnapshotKey(session, range);
    if (!key) return false;

    let snapshot;
    try {
      snapshot = JSON.parse(window.sessionStorage.getItem(key) || "null");
    } catch (_error) {
      return false;
    }

    const savedAt = Number(snapshot?.saved_at || 0);
    if (
      !snapshot
      || snapshot.schema !== DASHBOARD_SNAPSHOT_SCHEMA
      || snapshot.range !== range
      || dashboardSnapshotIdentity(session) !== String(snapshot.user_id || "")
      || !Number.isFinite(savedAt)
      || savedAt <= 0
      || Date.now() - savedAt > DASHBOARD_SNAPSHOT_MAX_AGE_MS
      || !Array.isArray(snapshot.deliveries)
      || !Array.isArray(snapshot.audit)
      || !snapshot.metrics
      || typeof snapshot.metrics !== "object"
    ) {
      return false;
    }

    dashboardDeliveries = snapshot.deliveries;
    state.metrics = snapshot.metrics;
    state.audit = snapshot.audit;
    filterSnapshot = snapshot.filters && typeof snapshot.filters === "object"
      ? snapshot.filters
      : null;
    lastUpdatedAt = savedAt;
    return true;
  }

  function saveDashboardSnapshot(range) {
    const session = { user: state.user };
    const key = dashboardSnapshotKey(session, range);
    if (!key) return;

    try {
      window.sessionStorage.setItem(key, JSON.stringify({
        schema: DASHBOARD_SNAPSHOT_SCHEMA,
        user_id: dashboardSnapshotIdentity(session),
        range,
        saved_at: Date.now(),
        deliveries: Array.isArray(dashboardDeliveries) ? dashboardDeliveries : [],
        metrics: state.metrics && typeof state.metrics === "object" ? state.metrics : {},
        audit: Array.isArray(state.audit) ? state.audit : [],
        filters: filterSnapshot,
      }));
    } catch (_error) {
      // A live refresh remains authoritative if browser storage is unavailable.
    }
  }

  function clearDashboardSnapshots(user = state.user) {
    const session = { user };
    for (const range of Object.keys(RANGE_LABELS)) {
      const key = dashboardSnapshotKey(session, range);
      if (!key) continue;
      try {
        window.sessionStorage.removeItem(key);
      } catch (_error) {
        return;
      }
    }
  }

  function svgIcon(name, className = "") {
    const item = document.createElementNS(SVG_NS, "svg");
    item.setAttribute("viewBox", "0 0 24 24");
    item.setAttribute("aria-hidden", "true");
    if (className) item.setAttribute("class", className);
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", ICON_PATHS[name] || ICON_PATHS.integrations);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "1.8");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    item.append(path);
    return item;
  }

  function dashboardMarkup() {
    return `
      <div class="ops-kpi-grid" aria-label="Operations summary">
        <article class="ops-kpi-card ops-kpi-config" data-kpi="integrations">
          <div class="ops-kpi-icon">${iconMarkup("integrations")}</div>
          <div class="ops-kpi-copy"><span>Integrations</span><strong id="ops-kpi-integrations">—</strong><small>Connected sources</small></div>
          <div class="ops-kpi-delta"><strong>LIVE</strong><small>current state</small></div>
        </article>
        <article class="ops-kpi-card ops-kpi-config" data-kpi="destinations">
          <div class="ops-kpi-icon">${iconMarkup("destinations")}</div>
          <div class="ops-kpi-copy"><span>Destinations</span><strong id="ops-kpi-destinations">—</strong><small>Active destinations</small></div>
          <div class="ops-kpi-delta"><strong>LIVE</strong><small>current state</small></div>
        </article>
        <article class="ops-kpi-card ops-kpi-config" data-kpi="routes">
          <div class="ops-kpi-icon">${iconMarkup("routes")}</div>
          <div class="ops-kpi-copy"><span>Routes</span><strong id="ops-kpi-routes">—</strong><small>Active routing rules</small></div>
          <div class="ops-kpi-delta"><strong>LIVE</strong><small>current state</small></div>
        </article>
        <article class="ops-kpi-card ops-kpi-success" data-kpi="success">
          <div class="ops-kpi-icon">${iconMarkup("success")}</div>
          <div class="ops-kpi-copy"><span>Success Rate</span><strong id="ops-kpi-success">—</strong><small id="ops-kpi-success-note">No deliveries in range</small></div>
          <div class="ops-kpi-delta" id="ops-success-delta"><strong>—</strong><small>vs. previous window</small></div>
        </article>
        <article class="ops-kpi-card ops-kpi-failure" data-kpi="failures">
          <div class="ops-kpi-icon">${iconMarkup("failure")}</div>
          <div class="ops-kpi-copy"><span>Failures</span><strong id="ops-kpi-failures">—</strong><small id="ops-kpi-failures-note">No failed deliveries</small></div>
          <div class="ops-kpi-delta" id="ops-failure-delta"><strong>—</strong><small>vs. previous window</small></div>
        </article>
      </div>

      <section class="ops-main-grid" aria-label="Delivery operations">
        <article class="panel ops-delivery-panel">
          <div class="ops-panel-heading">
            <div><h2>Delivery Performance</h2><p>Alert delivery outcomes over time</p></div>
            <label class="ops-range"><span>Range</span><select id="history-range" aria-label="Dashboard history range">${rangeOptions()}</select></label>
          </div>
          <div id="dashboard-delivery-chart" class="ops-delivery-chart" role="img" aria-label="Delivery performance chart"></div>
          <div id="dashboard-chart-summary" class="ops-chart-summary" aria-live="polite"></div>
        </article>

        <article class="panel ops-activity-panel">
          <div class="ops-panel-heading"><div><h2>Recent Activity</h2><p>Latest alert delivery events</p></div><button id="ops-activity-view-all" class="text-button" type="button">View all</button></div>
          <div id="dashboard-deliveries" class="ops-activity-list"></div>
        </article>
      </section>

      <section class="ops-insights-grid" aria-label="Operations insights">
        <article class="panel ops-insight-panel">
          <div class="ops-panel-heading"><div><h2>Top Integrations</h2><p>Most active alert sources</p></div><button id="ops-integrations-view-all" class="text-button" type="button">View all</button></div>
          <div id="dashboard-top-sources" class="ops-ranking"></div>
        </article>
        <article class="panel ops-insight-panel">
          <div class="ops-panel-heading"><div><h2>Top Destinations</h2><p>Most used notification targets</p></div><button id="ops-destinations-view-all" class="text-button" type="button">View all</button></div>
          <div id="dashboard-top-destinations" class="ops-ranking"></div>
        </article>
        <article class="panel ops-health-panel">
          <div class="ops-panel-heading"><div><h2>System Health</h2><p>Current system status</p></div><button id="ops-health-details" class="text-button" type="button">Details</button></div>
          <div id="dashboard-system-health" class="ops-health-list"></div>
        </article>
      </section>

      <section class="panel ops-configuration" aria-label="Configuration summary">
        <div class="ops-config-heading"><h2>Configuration</h2><p>Key configuration items</p></div>
        <div class="ops-config-item"><span class="ops-config-icon">${iconMarkup("key")}</span><div><span>API Tokens</span><strong id="ops-config-tokens">—</strong><small>Active API tokens</small></div></div>
        <div class="ops-config-item"><span class="ops-config-icon">${iconMarkup("filter")}</span><div><span>Active Filters</span><strong id="ops-config-filters">—</strong><small>Event filtering rules</small></div></div>
        <div class="ops-config-item"><span class="ops-config-icon">${iconMarkup("share")}</span><div><span>Shared Destinations</span><strong id="ops-config-shared">—</strong><small>Shared with other users</small></div></div>
        <div class="ops-config-item"><span class="ops-config-icon">${iconMarkup("audit")}</span><div><span>Audit Issues</span><strong id="ops-config-audit">—</strong><small>Requires attention</small></div></div>
      </section>
    `;
  }

  function iconMarkup(name) {
    const path = ICON_PATHS[name] || ICON_PATHS.integrations;
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>`;
  }

  function rangeOptions() {
    return Object.entries(RANGE_LABELS)
      .map(([value, label]) => `<option value="${value}">${label}</option>`)
      .join("");
  }

  function installDashboard() {
    const section = byId("view-dashboard");
    if (!section || section.dataset.operationsDashboard === "1") return;
    section.dataset.operationsDashboard = "1";
    section.classList.add("ops-dashboard");
    section.innerHTML = dashboardMarkup();

    const pageTitle = byId("page-title");
    if (pageTitle) {
      pageTitle.dataset.dashboardSubtitle = "Monitor your alert delivery pipeline and system health";
    }

    const topbarActions = document.querySelector(".topbar-actions");
    if (topbarActions && !byId("ops-dashboard-top-actions")) {
      const controls = node("div", "ops-dashboard-top-actions");
      controls.id = "ops-dashboard-top-actions";
      controls.innerHTML = `
        <label class="ops-global-range"><span class="sr-only">Dashboard range</span><span class="ops-calendar" aria-hidden="true">▣</span><select id="ops-dashboard-range">${rangeOptions()}</select></label>
        <span class="ops-live" data-live-contract="data-feed" aria-live="polite"><span class="ops-live-dot" aria-hidden="true"></span><span><strong id="ops-feed-state">Connecting</strong><small id="ops-feed-age">Waiting for dashboard data</small></span></span>
      `;
      topbarActions.prepend(controls);
    }

    byId("history-range")?.addEventListener("change", event => setRange(event.currentTarget.value));
    byId("ops-dashboard-range")?.addEventListener("change", event => setRange(event.currentTarget.value));
    byId("ops-activity-view-all")?.addEventListener("click", () => navigate("deliveries"));
    byId("ops-integrations-view-all")?.addEventListener("click", () => navigate("routing-flow"));
    byId("ops-destinations-view-all")?.addEventListener("click", () => navigate("destinations"));
    byId("ops-health-details")?.addEventListener("click", () => navigate("audit"));

    syncDashboardChrome();
  }

  function syncDashboardChrome() {
    const active = state.currentView === DASHBOARD_VIEW;
    document.querySelector(".topbar")?.classList.toggle("ops-dashboard-topbar", active);
    const controls = byId("ops-dashboard-top-actions");
    if (controls) controls.hidden = !active;
    if (active) syncRangeControls();
  }

  function syncRangeControls() {
    const value = Object.hasOwn(RANGE_LABELS, state.historyRange) ? state.historyRange : "1h";
    const chart = byId("history-range");
    const global = byId("ops-dashboard-range");
    if (chart) chart.value = value;
    if (global) global.value = value;
  }

  async function setRange(value) {
    if (!Object.hasOwn(RANGE_LABELS, value)) return;
    state.historyRange = value;
    syncRangeControls();
    await refreshDashboardData(true);
  }

  function attemptTime(item) {
    const value = Number(item.completed_at || item.created_at || 0);
    return value < 10_000_000_000 ? value : Math.floor(value / 1000);
  }

  function latestAttempts() {
    const latest = new Map();
    for (const item of dashboardDeliveries) {
      const key = item.delivery_id || item.id;
      const current = latest.get(key);
      if (!current || Number(item.attempt_number || 0) >= Number(current.attempt_number || 0)) {
        latest.set(key, item);
      }
    }
    return [...latest.values()];
  }

  function attemptsBetween(start, end) {
    return latestAttempts().filter(item => {
      const timestamp = attemptTime(item);
      return timestamp >= start && timestamp < end;
    });
  }

  function attemptsForRange() {
    const seconds = RANGE_SECONDS[state.historyRange] || RANGE_SECONDS["1h"];
    const end = Math.floor(Date.now() / 1000) + 1;
    return attemptsBetween(end - seconds, end);
  }

  function classifyAttempt(item) {
    const outcome = String(item.outcome || "").toLowerCase();
    if (["delivered", "success"].includes(outcome)) return "delivered";
    if (item.retryable || ["retry", "retrying", "retry_scheduled", "pending"].includes(outcome)) return "retry";
    return "failed";
  }

  function routeDestinationIds(route) {
    if (Array.isArray(route.destination_ids)) return route.destination_ids;
    return route.destination_id ? [route.destination_id] : [];
  }

  function activeTopology() {
    const destinations = (state.destinations || []).filter(item => item.enabled !== false);
    const destinationIds = new Set(destinations.map(item => item.id));
    const routes = (state.routes || []).filter(route => (
      route.enabled !== false
      && routeDestinationIds(route).some(id => destinationIds.has(id))
    ));
    const integrations = new Set(routes.map(route => String(route.source || "").trim()).filter(Boolean));
    return { integrations: integrations.size, destinations: destinations.length, routes: routes.length };
  }

  function successStats(attempts) {
    const delivered = attempts.filter(item => classifyAttempt(item) === "delivered").length;
    const retry = attempts.filter(item => classifyAttempt(item) === "retry").length;
    const failed = attempts.filter(item => classifyAttempt(item) === "failed").length;
    const total = attempts.length;
    const successRate = total ? (delivered / total) * 100 : null;
    return { delivered, retry, failed, total, successRate };
  }

  function formatPercent(value, digits = 1) {
    return value === null || value === undefined || !Number.isFinite(value) ? "—" : `${value.toFixed(digits)}%`;
  }

  function renderKpis(attempts) {
    const topology = activeTopology();
    const stats = successStats(attempts);
    byId("ops-kpi-integrations").textContent = String(topology.integrations);
    byId("ops-kpi-destinations").textContent = String(topology.destinations);
    byId("ops-kpi-routes").textContent = String(topology.routes);
    byId("ops-kpi-success").textContent = formatPercent(stats.successRate);
    byId("ops-kpi-success-note").textContent = stats.total ? `${stats.delivered.toLocaleString()} delivered` : "No deliveries in range";
    byId("ops-kpi-failures").textContent = stats.failed.toLocaleString();
    byId("ops-kpi-failures-note").textContent = `${stats.failed.toLocaleString()} failed ${stats.failed === 1 ? "delivery" : "deliveries"}`;

    const seconds = RANGE_SECONDS[state.historyRange] || RANGE_SECONDS["1h"];
    const now = Math.floor(Date.now() / 1000) + 1;
    const previous = successStats(attemptsBetween(now - (2 * seconds), now - seconds));
    renderDelta("ops-success-delta", stats.successRate, previous.successRate, true);
    renderDelta("ops-failure-delta", stats.failed, previous.failed, false);
  }

  function renderDelta(id, current, previous, percentage) {
    const container = byId(id);
    if (!container) return;
    const strong = container.querySelector("strong");
    const note = container.querySelector("small");
    container.classList.remove("negative", "positive");
    if (current === null || previous === null || previous === undefined || !Number.isFinite(Number(previous))) {
      strong.textContent = "—";
      note.textContent = "vs. previous window";
      return;
    }
    const delta = Number(current) - Number(previous);
    strong.textContent = `${delta > 0 ? "▲ +" : delta < 0 ? "▼ " : "±"}${percentage ? Math.abs(delta).toFixed(1) + "%" : Math.abs(delta).toLocaleString()}`;
    container.classList.toggle("negative", percentage ? delta < 0 : delta > 0);
    container.classList.toggle("positive", percentage ? delta > 0 : delta < 0);
    note.textContent = "vs. previous window";
  }

  function bucketLabel(timestamp) {
    const range = state.historyRange;
    const date = new Date(timestamp * 1000);
    const options = range === "1y"
      ? { month: "short" }
      : range === "1m"
        ? { day: "2-digit", month: "short" }
        : { hour: "2-digit", minute: "2-digit" };
    return new Intl.DateTimeFormat(state.preferences.language || "en-GB", {
      ...options,
      hour12: state.preferences.time_format === "12",
      timeZone: state.preferences.timezone || "Europe/Lisbon",
    }).format(date);
  }

  function renderDeliveryChart(attempts) {
    const container = byId("dashboard-delivery-chart");
    const summary = byId("dashboard-chart-summary");
    if (!container || !summary) return;
    container.replaceChildren();
    summary.replaceChildren();

    const seconds = RANGE_SECONDS[state.historyRange] || RANGE_SECONDS["1h"];
    const bucketCount = state.historyRange === "10m" ? 20 : state.historyRange === "1h" ? 36 : state.historyRange === "1d" ? 24 : state.historyRange === "1m" ? 31 : 24;
    const now = Math.floor(Date.now() / 1000);
    const start = now - seconds;
    const bucketSeconds = seconds / bucketCount;
    const buckets = Array.from({ length: bucketCount }, (_, index) => ({
      start: start + index * bucketSeconds,
      delivered: 0,
      failed: 0,
      retry: 0,
    }));
    for (const item of attempts) {
      const index = Math.min(bucketCount - 1, Math.max(0, Math.floor((attemptTime(item) - start) / bucketSeconds)));
      buckets[index][classifyAttempt(item)] += 1;
    }

    const width = 980, height = 330;
    const padding = { top: 22, right: 18, bottom: 48, left: 54 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const maximum = Math.max(1, ...buckets.map(bucket => bucket.delivered + bucket.failed + bucket.retry));
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("preserveAspectRatio", "none");
    svg.setAttribute("aria-hidden", "true");

    for (let line = 0; line <= 3; line += 1) {
      const y = padding.top + (plotHeight * line) / 3;
      const grid = document.createElementNS(SVG_NS, "line");
      grid.setAttribute("x1", padding.left); grid.setAttribute("x2", width - padding.right);
      grid.setAttribute("y1", y); grid.setAttribute("y2", y); grid.setAttribute("class", "ops-chart-grid");
      svg.append(grid);
      const label = document.createElementNS(SVG_NS, "text");
      label.setAttribute("x", padding.left - 14); label.setAttribute("y", y + 4); label.setAttribute("text-anchor", "end"); label.setAttribute("class", "ops-chart-axis");
      label.textContent = String(Math.round(maximum * (1 - line / 3)));
      svg.append(label);
    }

    const slot = plotWidth / bucketCount;
    const barWidth = Math.max(4, Math.min(13, slot * 0.55));
    const failedPoints = [], retryPoints = [];
    buckets.forEach((bucket, index) => {
      const x = padding.left + index * slot + (slot - barWidth) / 2;
      const baseline = padding.top + plotHeight;
      const deliveredHeight = (bucket.delivered / maximum) * plotHeight;
      const bar = document.createElementNS(SVG_NS, "rect");
      bar.setAttribute("x", x); bar.setAttribute("width", barWidth); bar.setAttribute("rx", 2);
      bar.setAttribute("y", baseline - Math.max(bucket.delivered ? 3 : 1, deliveredHeight));
      bar.setAttribute("height", Math.max(bucket.delivered ? 3 : 1, deliveredHeight));
      bar.setAttribute("class", bucket.delivered ? "ops-chart-bar" : "ops-chart-zero");
      svg.append(bar);
      const centerX = x + barWidth / 2;
      failedPoints.push(`${centerX},${baseline - Math.max(1.5, (bucket.failed / maximum) * plotHeight)}`);
      retryPoints.push(`${centerX},${baseline - Math.max(4, (bucket.retry / maximum) * plotHeight)}`);

      if (index % Math.max(1, Math.floor(bucketCount / 7)) === 0 || index === bucketCount - 1) {
        const label = document.createElementNS(SVG_NS, "text");
        label.setAttribute("x", centerX); label.setAttribute("y", height - 14); label.setAttribute("text-anchor", "middle"); label.setAttribute("class", "ops-chart-axis ops-chart-time");
        label.textContent = bucketLabel(bucket.start);
        svg.append(label);
      }
    });
    for (const [points, cls] of [[retryPoints, "ops-chart-retry-line"], [failedPoints, "ops-chart-failed-line"]]) {
      const polyline = document.createElementNS(SVG_NS, "polyline");
      polyline.setAttribute("points", points.join(" "));
      polyline.setAttribute("fill", "none");
      polyline.setAttribute("class", cls);
      svg.append(polyline);
    }
    container.append(svg);

    const stats = successStats(attempts);
    summary.append(
      summaryMetric("delivered", "Delivered", stats.delivered),
      summaryMetric("failed", "Failed", stats.failed),
      summaryMetric("retry", "Retry", stats.retry),
      summaryMetric("success", "Success rate", formatPercent(stats.successRate)),
      summaryMetric("attempts", "Total attempts", stats.total),
    );
  }

  function summaryMetric(kind, label, value) {
    const item = node("div", `ops-summary-metric ${kind}`);
    const labelRow = node("span", "ops-summary-label");
    if (["delivered", "failed", "retry"].includes(kind)) labelRow.append(node("i", `ops-summary-dot ${kind}`));
    labelRow.append(document.createTextNode(label));
    item.append(labelRow, node("strong", "", typeof value === "number" ? value.toLocaleString() : value));
    return item;
  }

  function renderRecentActivity() {
    const container = byId("dashboard-deliveries");
    if (!container) return;
    container.replaceChildren();
    const items = latestAttempts().sort((a, b) => attemptTime(b) - attemptTime(a)).slice(0, 5);
    if (!items.length) {
      container.append(emptyState("No recent activity", "Delivered notifications will appear here."));
      return;
    }
    for (const item of items) {
      const row = node("div", "ops-activity-row");
      const visual = sourceIcon(item.source);
      visual.classList.add("ops-activity-icon");
      const copy = node("div", "ops-activity-copy");
      const title = item.device_name ? `${item.device_name} · ${item.event_name || item.title || "Notification"}` : item.event_name || item.title || "Notification";
      copy.append(node("strong", "", title), node("small", "", friendlyName(item.source)));
      const severity = node("span", `ops-severity severity-${String(item.severity || "info").toLowerCase()}`, capitalize(item.severity || "Info"));
      const attempt = node("span", "ops-attempt", `Attempt ${item.attempt_number || 1}`);
      const outcomeClass = classifyAttempt(item);
      const outcome = node("span", `ops-outcome ${outcomeClass}`, String(item.outcome || outcomeClass).toUpperCase());
      const time = node("small", "ops-activity-time", relativeTime(item.completed_at || item.created_at));
      row.append(visual, copy, severity, attempt, outcome, time);
      container.append(row);
    }
  }

  function renderRankings(attempts) {
    const sourceCounts = new Map();
    const destinationCounts = new Map();
    for (const item of attempts) {
      const source = String(item.source || "*");
      sourceCounts.set(source, (sourceCounts.get(source) || 0) + 1);
      const destination = item.destination_id || "";
      if (destination) destinationCounts.set(destination, (destinationCounts.get(destination) || 0) + 1);
    }
    const sources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const destinations = [...destinationCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    renderSourceRanking(byId("dashboard-top-sources"), sources);
    renderDestinationRanking(byId("dashboard-top-destinations"), destinations);
  }

  function renderSourceRanking(container, entries) {
    if (!container) return;
    container.replaceChildren();
    if (!entries.length) { container.append(emptyState("No top integrations", "Activity will appear after events are delivered.")); return; }
    const total = entries.reduce((sum, [, count]) => sum + count, 0) || 1;
    entries.forEach(([source, count], index) => {
      const row = node("div", "ops-ranking-row");
      const rank = node("span", "ops-rank", index + 1);
      const visual = sourceIcon(source); visual.classList.add("ops-ranking-icon");
      const name = node("strong", "ops-ranking-name", friendlyName(source));
      const track = node("span", "ops-ranking-track");
      const fill = node("i", "ops-ranking-fill"); fill.style.width = `${Math.max(4, (count / total) * 100)}%`; track.append(fill);
      const countNode = node("span", "ops-ranking-count", count.toLocaleString());
      const percent = node("span", "ops-ranking-percent", `${Math.round((count / total) * 100)}%`);
      row.append(rank, visual, name, track, countNode, percent);
      container.append(row);
    });
  }

  function renderDestinationRanking(container, entries) {
    if (!container) return;
    container.replaceChildren();
    if (!entries.length) { container.append(emptyState("No top destinations", "Destination activity will appear after events are delivered.")); return; }
    const destinationMap = new Map((state.destinations || []).map(item => [item.id, item]));
    const total = entries.reduce((sum, [, count]) => sum + count, 0) || 1;
    entries.forEach(([id, count], index) => {
      const destination = destinationMap.get(id);
      const row = node("div", "ops-ranking-row");
      const rank = node("span", "ops-rank", index + 1);
      const visual = destination ? outputIcon(destination.output_type) : svgIcon("destinations", "ops-ranking-icon");
      visual.classList.add("ops-ranking-icon");
      const name = node("strong", "ops-ranking-name", destination?.name || "Unresolved destination");
      const track = node("span", "ops-ranking-track");
      const fill = node("i", "ops-ranking-fill"); fill.style.width = `${Math.max(4, (count / total) * 100)}%`; track.append(fill);
      const countNode = node("span", "ops-ranking-count", count.toLocaleString());
      const percent = node("span", "ops-ranking-percent", `${Math.round((count / total) * 100)}%`);
      row.append(rank, visual, name, track, countNode, percent);
      container.append(row);
    });
  }

  function emptyState(title, copy) {
    const wrapper = node("div", "ops-empty");
    wrapper.append(node("strong", "", title), node("span", "", copy));
    return wrapper;
  }

  function normalizedHealthStatus(value) {
    const status = String(value || "").toLowerCase();
    if (["healthy", "ok", "success", "passed", "pass"].includes(status)) return "healthy";
    if (["error", "failed", "failure", "critical"].includes(status)) return "error";
    return "warning";
  }

  function currentHealth(attempts) {
    const failures = successStats(attempts).failed;
    const workspaceIssues = (state.workspaceErrors || []).length;
    const auditIssues = (state.audit || []).filter(item => {
      const outcome = String(item.outcome || item.status || "").toLowerCase();
      return ["error", "failed", "failure", "warning"].includes(outcome);
    }).length;
    const storageCheck = (state.healthChecks || []).find(item => /storage|disk|database/i.test(`${item.key || ""} ${item.name || ""}`));
    return [
      { icon: "api", name: "API", detail: workspaceIssues ? `${workspaceIssues} workspace request issue${workspaceIssues === 1 ? "" : "s"}` : "API service is running normally", status: workspaceIssues ? "warning" : "healthy" },
      { icon: "delivery", name: "Deliveries", detail: failures ? `${failures} terminal failure${failures === 1 ? "" : "s"} in range` : "Alert delivery pipeline is operational", status: failures ? "warning" : "healthy" },
      { icon: "audit", name: "Audit", detail: auditIssues ? `${auditIssues} recorded issue${auditIssues === 1 ? "" : "s"}` : "No recorded audit issues", status: auditIssues ? "warning" : "healthy" },
      { icon: "storage", name: "Storage", detail: storageCheck?.detail || (storageCheck ? "Storage check completed" : "Run health checks for storage detail"), status: storageCheck ? normalizedHealthStatus(storageCheck.status) : "warning" },
    ];
  }

  function renderHealth(attempts) {
    const container = byId("dashboard-system-health");
    if (!container) return;
    container.replaceChildren();
    for (const item of currentHealth(attempts)) {
      const row = node("div", "ops-health-row");
      const visual = node("span", "ops-health-icon"); visual.append(svgIcon(item.icon));
      const copy = node("div", "ops-health-copy"); copy.append(node("strong", "", item.name), node("small", "", item.detail));
      const status = node("span", `ops-health-status ${item.status}`, item.status === "healthy" ? "Healthy" : item.status === "error" ? "Error" : "Warning");
      status.prepend(node("i", "ops-health-dot"));
      row.append(visual, copy, status);
      container.append(row);
    }
  }

  function activeTokenCount() {
    return (state.tokens || []).filter(item => item.enabled !== false && !item.revoked_at && String(item.status || "").toLowerCase() !== "revoked").length;
  }

  function activeFilterCount() {
    const policies = Array.isArray(filterSnapshot?.filters) ? filterSnapshot.filters : [];
    return policies.reduce((sum, policy) => {
      if (Number.isFinite(Number(policy.active_count))) return sum + Number(policy.active_count);
      const integrations = Array.isArray(policy.integrations) ? policy.integrations : [];
      return sum + integrations.filter(item => item.filter_enabled).length;
    }, 0);
  }

  function renderConfiguration(attempts) {
    byId("ops-config-tokens").textContent = activeTokenCount().toLocaleString();
    byId("ops-config-filters").textContent = activeFilterCount().toLocaleString();
    byId("ops-config-shared").textContent = (state.destinations || []).filter(item => item.shared).length.toLocaleString();
    byId("ops-config-audit").textContent = currentHealth(attempts).filter(item => item.status !== "healthy").length.toLocaleString();
  }

  function renderOperationsDashboard() {
    installDashboard();
    syncDashboardChrome();
    syncRangeControls();
    const attempts = attemptsForRange();
    renderKpis(attempts);
    renderDeliveryChart(attempts);
    renderRecentActivity();
    renderRankings(attempts);
    renderHealth(attempts);
    renderConfiguration(attempts);
    updateLiveAge();
  }

  async function refreshDashboardData(force = false) {
    if (!state.user || (!force && state.currentView !== DASHBOARD_VIEW)) return;
    if (refreshBusy) {
      if (force) refreshPending = true;
      return;
    }

    refreshBusy = true;
    const requestedRange = state.historyRange;
    try {
      const jobs = await Promise.allSettled([
        request(`/metrics/${requestedRange}`, { dashboardFeed: true }),
        request("/deliveries", { dashboardFeed: true }),
        request("/filters", { dashboardFeed: true }),
        request("/audit-events", { dashboardFeed: true }),
      ]);

      // A range change can happen while this batch is in flight. Never paint
      // the old batch over the newly selected window.
      if (requestedRange !== state.historyRange) {
        refreshPending = true;
        return;
      }

      if (jobs[0].status === "fulfilled") state.metrics = jobs[0].value.metrics;
      if (jobs[1].status === "fulfilled") dashboardDeliveries = jobs[1].value.deliveries || [];
      if (jobs[2].status === "fulfilled") filterSnapshot = jobs[2].value;
      if (jobs[3].status === "fulfilled") state.audit = jobs[3].value.audit_events || [];
      lastUpdatedAt = Date.now();
      if (jobs[0].status === "fulfilled" && jobs[1].status === "fulfilled") {
        saveDashboardSnapshot(requestedRange);
      }
      renderOperationsDashboard();
    } finally {
      refreshBusy = false;
      if (refreshPending && state.user && state.currentView === DASHBOARD_VIEW) {
        refreshPending = false;
        window.queueMicrotask(() => refreshDashboardData(true));
      }
    }
  }

  function updateLiveAge() {
    const item = byId("ops-live-age");
    if (!item) return;
    if (!lastUpdatedAt) { item.textContent = "Waiting for data"; return; }
    const seconds = Math.max(0, Math.floor((Date.now() - lastUpdatedAt) / 1000));
    item.textContent = seconds < 5 ? "Updated just now" : `Updated ${seconds}s ago`;
  }

  const previousRenderDashboard = renderDashboard;
  renderDashboard = function operationsDashboardRender() {
    // Do not call the legacy renderer: this intentionally retires the old Dashboard Routing Flow.
    renderOperationsDashboard();
  };

  const previousNavigate = navigate;
  navigate = function operationsDashboardNavigate(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    syncDashboardChrome();
    if (view === DASHBOARD_VIEW) {
        refreshDashboardData(false);
    }
    return result;
  };

  const previousShowApp = showApp;
  showApp = function operationsDashboardShowApp(session) {
    restoreDashboardSnapshot(session, state.historyRange);
    return previousShowApp(session);
  };

  const previousExpireSession = expireSession;
  expireSession = function operationsDashboardExpireSession() {
    clearDashboardSnapshots(state.user);
    filterSnapshot = null;
    dashboardDeliveries = [];
    refreshPending = false;
    lastUpdatedAt = 0;
    return previousExpireSession();
  };

  installDashboard();
  // The base renderer is retained only as a diagnostic reference for future removals.
  void previousRenderDashboard;
  refreshTimer = window.setInterval(() => refreshDashboardData(false), REFRESH_MS);
  clockTimer = window.setInterval(updateLiveAge, 1_000);
  window.addEventListener("beforeunload", () => {
    window.clearInterval(refreshTimer);
    window.clearInterval(clockTimer);
  });
})();