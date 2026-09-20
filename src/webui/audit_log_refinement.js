"use strict";

/* Audit Log fidelity, real metrics, persistent health summary, and semantic detail tabs. */
(() => {
  const REQUEST_KEYS = new Set([
    "request_method",
    "request_path",
    "request_client",
    "request_user_agent",
    "method",
    "path",
    "endpoint",
    "client",
    "client_ip",
    "remote_ip",
    "ip",
    "user_agent",
    "url",
  ]);
  const RESPONSE_KEYS = new Set([
    "response_status",
    "status_code",
    "error_code",
    "retryable",
    "safe_error",
    "result",
    "status",
  ]);
  const SUMMARY_KEYS = new Set([
    "safe_error",
    "message",
    "description",
    "detail",
    "note",
  ]);
  const SUCCESS_OUTCOMES = new Set([
    "success",
    "ok",
    "healthy",
    "delivered",
    "accepted",
    "completed",
  ]);
  const WARNING_OUTCOMES = new Set([
    "warning",
    "warn",
    "pending",
    "retrying",
  ]);
  const FAILED_OUTCOMES = new Set([
    "failed",
    "failure",
    "error",
    "denied",
    "invalid",
  ]);
  const ANALYTICS_TTL_MS = 60_000;
  const AUDIT_ANALYTICS_STORAGE_VERSION = "v1";
  const HEALTH_STORAGE_VERSION = "v1";

  const previousRenderAudit = renderAudit;
  const previousLoadAuditPage =
    typeof qaLoadAuditPage === "function" ? qaLoadAuditPage : null;
  const previousNavigate = navigate;
  const previousResourceAction =
    typeof resourceAction === "function" ? resourceAction : null;

  let auditAnalytics = null;
  let analyticsPromise = null;
  let healthPromise = null;
  let initialHealthAttempted = false;

  function make(tag, className = "", text = "") {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== "") node.textContent = String(text);
    return node;
  }

  function auditKey(item, index = 0) {
    return String(
      item?.id
      || item?.audit_id
      || `${item?.created_at || 0}:${item?.action || "unknown"}:${item?.resource_id || "none"}:${item?.actor_user_id || index}`,
    );
  }

  function selectedAuditItem() {
    const selected = document.querySelector(
      "#view-audit .audit-log-row.selected[data-audit-log-key]",
    );
    const key = selected?.dataset.auditLogKey || "";
    const items = Array.isArray(state?.audit) ? state.audit : [];
    if (!key) return items[0] || null;
    return items.find((item, index) => auditKey(item, index) === key) || null;
  }

  function detailEntries(item) {
    if (!item?.details || typeof item.details !== "object" || Array.isArray(item.details)) {
      return [];
    }
    return Object.entries(item.details).filter(([, value]) => (
      value !== undefined && value !== null && value !== ""
    ));
  }

  function normalizedDetailKey(key) {
    return String(key || "").toLowerCase();
  }

  function isRequestKey(key) {
    const normalized = normalizedDetailKey(key);
    return REQUEST_KEYS.has(normalized) || normalized.startsWith("request_");
  }

  function isResponseKey(key) {
    const normalized = normalizedDetailKey(key);
    return RESPONSE_KEYS.has(normalized)
      || normalized.startsWith("response_")
      || normalized.startsWith("error_");
  }

  function requestEntries(item) {
    return detailEntries(item).filter(([key]) => isRequestKey(key));
  }

  function responseEntries(item) {
    return detailEntries(item).filter(([key]) => isResponseKey(key));
  }

  function generalEntries(item) {
    return detailEntries(item).filter(([key]) => (
      !isRequestKey(key)
      && !isResponseKey(key)
      && !SUMMARY_KEYS.has(normalizedDetailKey(key))
      && !["duration", "duration_ms"].includes(normalizedDetailKey(key))
    ));
  }

  function displayKey(key) {
    let value = String(key || "");
    if (value.startsWith("request_")) value = value.slice("request_".length);
    if (value.startsWith("response_")) value = value.slice("response_".length);
    return typeof friendlyName === "function"
      ? friendlyName(value)
      : value.replaceAll("_", " ");
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === "") return "—";
    if (typeof value === "boolean") return value ? "Yes" : "No";
    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch (_error) {
        return String(value);
      }
    }
    return String(value);
  }

  function actorLabel(item) {
    if (typeof auditActorLabel === "function") return auditActorLabel(item);
    return item?.actor_username || item?.actor_user_id || "System";
  }

  function actionLabel(item) {
    if (typeof auditActionLabel === "function") return auditActionLabel(item?.action);
    return typeof friendlyName === "function"
      ? friendlyName(item?.action || "unknown")
      : String(item?.action || "unknown");
  }

  function outcomeTone(item) {
    const outcome = normalizedDetailKey(item?.outcome);
    if (FAILED_OUTCOMES.has(outcome)) return "danger";
    if (WARNING_OUTCOMES.has(outcome)) return "warning";
    if (SUCCESS_OUTCOMES.has(outcome)) return "success";
    return "information";
  }

  async function copyValue(value, label) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(String(value || ""));
      } else {
        const helper = document.createElement("textarea");
        helper.value = String(value || "");
        helper.style.position = "fixed";
        helper.style.opacity = "0";
        document.body.append(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
      }
      toast(`${label} copied.`, "success");
    } catch (_error) {
      toast(`${label} could not be copied.`, "error");
    }
  }

  function detailRow(label, value, options = {}) {
    const row = make("div", "audit-refine-row");
    const labelNode = make("span", "audit-refine-label", label);
    const valueNode = make("span", "audit-refine-value");
    const primary = make(
      "strong",
      options.tone ? `audit-refine-tone ${options.tone}` : "",
      displayValue(value),
    );
    valueNode.append(primary);
    if (options.secondary) valueNode.append(make("small", "", options.secondary));
    row.append(labelNode, valueNode);
    if (options.copyValue) {
      const copy = make("button", "audit-refine-copy", "⧉");
      copy.type = "button";
      copy.setAttribute("aria-label", `Copy ${label}`);
      copy.addEventListener("click", () => copyValue(options.copyValue, label));
      row.append(copy);
    }
    return row;
  }

  function emptyState(title, text) {
    const empty = make("div", "audit-refine-empty");
    empty.append(make("strong", "", title), make("span", "", text));
    return empty;
  }

  function listCard(rows, emptyTitle, emptyText) {
    if (!rows.length) return emptyState(emptyTitle, emptyText);
    const card = make("section", "audit-refine-list");
    rows.forEach((row) => card.append(row));
    return card;
  }

  function detailRows(entries) {
    return entries.map(([key, value]) => detailRow(displayKey(key), value));
  }

  function summaryDetail(item) {
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    const isFailure = outcomeTone(item) === "danger";
    const order = isFailure
      ? ["safe_error", "message", "description", "detail", "note"]
      : ["message", "description", "detail", "note"];
    for (const key of order) {
      if (details[key] !== undefined && details[key] !== null && details[key] !== "") {
        return [key, details[key]];
      }
    }
    return null;
  }

  function overviewBody(item) {
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    const duration = details.duration_ms ?? details.duration ?? item?.duration_ms ?? "";
    const summary = summaryDetail(item);
    const rows = [
      detailRow("Timestamp", formatTime(item.created_at)),
      detailRow("Action", actionLabel(item), { secondary: item.action || "unknown" }),
      detailRow("User", actorLabel(item), {
        secondary: item.actor_user_id ? `ID: ${item.actor_user_id}` : "",
      }),
      detailRow("Resource type", friendlyName(item.resource_type || "Platform")),
      detailRow("Resource ID", item.resource_id || "Platform-level action", {
        copyValue: item.resource_id || "",
      }),
      detailRow("Outcome", capitalize(item.outcome || "unknown"), {
        tone: outcomeTone(item),
      }),
    ];
    if (duration !== "") {
      const suffix = /^\d+(\.\d+)?$/.test(String(duration)) ? " ms" : "";
      rows.push(detailRow("Duration", `${displayValue(duration)}${suffix}`));
    }
    if (summary) {
      rows.push(detailRow(outcomeTone(item) === "danger" ? "Failure" : "Summary", summary[1]));
    }
    return listCard(rows, "No event details", "No audit details were recorded.");
  }

  function detailsBody(item) {
    return listCard(
      detailRows(generalEntries(item)),
      "No event-specific metadata",
      "This event has no additional safe metadata outside its request, response, and correlation context.",
    );
  }

  function requestBody(item) {
    return listCard(
      detailRows(requestEntries(item)),
      "No request metadata",
      "No safe request context was recorded for this event. Historical events are not backfilled.",
    );
  }

  function responseBody(item) {
    return listCard(
      detailRows(responseEntries(item)),
      "No response metadata",
      "No safe response context was recorded for this event.",
    );
  }

  function relatedBody(item) {
    const rows = [
      detailRow("Event ID", item?.id ?? item?.audit_id ?? "—"),
      detailRow("Actor ID", item.actor_user_id || "—"),
      detailRow("Resource type", item.resource_type || "Platform"),
      detailRow("Resource ID", item.resource_id || "—", {
        copyValue: item.resource_id || "",
      }),
    ];
    return listCard(rows, "No related context", "No related identifiers were recorded.");
  }

  function activeTab() {
    const label = document.querySelector(
      "#view-audit .audit-log-detail-tabs button.active",
    )?.textContent;
    return String(label || "Overview").trim().toLowerCase();
  }

  function refineDetailBody() {
    const body = document.getElementById("audit-log-detail-body");
    const item = selectedAuditItem();
    if (!body || !item) return;
    const tab = activeTab();
    if (tab === "details") body.replaceChildren(detailsBody(item));
    else if (tab === "request") body.replaceChildren(requestBody(item));
    else if (tab === "response") body.replaceChildren(responseBody(item));
    else if (tab === "related") body.replaceChildren(relatedBody(item));
    else body.replaceChildren(overviewBody(item));
  }

  function refineRows() {
    document.querySelectorAll("#view-audit .audit-log-row-more").forEach((node) => node.remove());
    const columns = document.querySelector("#view-audit .audit-log-columns");
    const last = columns?.lastElementChild;
    if (last && !String(last.textContent || "").trim()) last.remove();
  }

  function refineRunChecks() {
    const button = document.querySelector('[data-action="run-health-checks"]');
    if (!button || button.dataset.auditRunChecks === "ready") return;
    button.dataset.auditRunChecks = "ready";
    button.className = "button primary audit-run-checks";
    button.replaceChildren();

    const icon = make("span", "audit-run-checks-icon", "▶");
    icon.setAttribute("aria-hidden", "true");
    const copy = make("span", "audit-run-checks-copy");
    copy.append(
      make("strong", "", "Run checks"),
      make("small", "", "Execute all health checks"),
    );
    button.append(icon, copy);
  }

  function auditTimestamp(item) {
    const value = Number(item?.created_at || 0);
    if (!Number.isFinite(value) || value <= 0) return 0;
    return value < 10_000_000_000 ? value * 1000 : value;
  }

  function metricBucket(outcome) {
    const normalized = normalizedDetailKey(outcome);
    if (SUCCESS_OUTCOMES.has(normalized)) return "success";
    if (WARNING_OUTCOMES.has(normalized)) return "warning";
    if (FAILED_OUTCOMES.has(normalized)) return "failed";
    return "other";
  }

  function blankCounts() {
    return { success: 0, warning: 0, failed: 0, other: 0 };
  }

  function countEvents(events, startMs, endMs) {
    const counts = blankCounts();
    for (const item of events) {
      const timestamp = auditTimestamp(item);
      if (!timestamp || timestamp < startMs || timestamp >= endMs) continue;
      counts[metricBucket(item.outcome)] += 1;
    }
    return counts;
  }

  function summaryCards() {
    return {
      success: document.getElementById("audit-log-success-count")?.closest(".audit-log-summary-card"),
      warning: document.getElementById("audit-log-warning-count")?.closest(".audit-log-summary-card"),
      failed: document.getElementById("audit-log-failed-count")?.closest(".audit-log-summary-card"),
      total: document.getElementById("audit-log-total-count")?.closest(".audit-log-summary-card"),
    };
  }

  function ensureSummaryMetricChrome() {
    const cards = summaryCards();
    for (const [key, card] of Object.entries(cards)) {
      if (!card) continue;
      const copy = card.querySelector(".audit-log-summary-copy");
      const note = copy?.querySelector("small");
      if (note) note.textContent = key === "total" ? "All pages" : "Last 7 days";
      if (key === "total") continue;
      if (!auditAnalytics) {
        const value = copy?.querySelector("strong");
        if (value) value.textContent = "—";
      }
      if (!card.querySelector(".audit-refine-trend")) {
        const trend = make("span", "audit-refine-trend is-neutral");
        trend.append(make("strong", "", "—"), make("small", "", "vs. previous 7 days"));
        card.append(trend);
      }
    }
    if (!auditAnalytics) {
      const knownTotal = typeof qaAuditPagination !== "undefined"
        ? Number(qaAuditPagination.total || 0)
        : 0;
      const total = document.getElementById("audit-log-total-count");
      if (total && knownTotal) total.textContent = String(knownTotal);
    }
  }

  function trendData(current, previous) {
    if (previous === 0 && current === 0) return { text: "→ 0%", tone: "neutral" };
    if (previous === 0) return { text: "↑ New", tone: "up" };
    const percent = Math.round(((current - previous) / previous) * 100);
    if (percent > 0) return { text: `↑ ${percent}%`, tone: "up" };
    if (percent < 0) return { text: `↓ ${Math.abs(percent)}%`, tone: "down" };
    return { text: "→ 0%", tone: "neutral" };
  }

  function auditAnalyticsStorageKey() {
    const identity = state?.user?.id || state?.user?.username || "";
    return identity
      ? `nowlert:audit-analytics:${AUDIT_ANALYTICS_STORAGE_VERSION}:${encodeURIComponent(String(identity))}`
      : "";
  }

  function normalizedAuditAnalytics(value) {
    if (!value || typeof value !== "object") return null;
    const current = value.current;
    const previous = value.previous;
    if (!current || !previous) return null;
    const number = (candidate) => {
      const parsed = Number(candidate);
      return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
    };
    const loadedAt = Number(value.loadedAt || 0);
    if (!Number.isFinite(loadedAt) || loadedAt <= 0) return null;
    return {
      loadedAt,
      total: number(value.total),
      current: {
        success: number(current.success),
        warning: number(current.warning),
        failed: number(current.failed),
        other: number(current.other),
      },
      previous: {
        success: number(previous.success),
        warning: number(previous.warning),
        failed: number(previous.failed),
        other: number(previous.other),
      },
    };
  }

  function readAuditAnalytics() {
    const key = auditAnalyticsStorageKey();
    if (!key) return null;
    try {
      return normalizedAuditAnalytics(
        JSON.parse(window.sessionStorage.getItem(key) || "null"),
      );
    } catch (_error) {
      return null;
    }
  }

  function persistAuditAnalytics(value) {
    const key = auditAnalyticsStorageKey();
    const normalized = normalizedAuditAnalytics(value);
    if (!key || !normalized) return;
    try {
      window.sessionStorage.setItem(key, JSON.stringify(normalized));
    } catch (_error) {
      // Analytics first-paint cache is optional.
    }
  }

  function restoreAuditAnalytics() {
    if (auditAnalytics) return auditAnalytics;
    const cached = readAuditAnalytics();
    if (!cached) return null;
    auditAnalytics = cached;
    return auditAnalytics;
  }

  function applyAuditAnalytics() {
    ensureSummaryMetricChrome();
    if (!auditAnalytics) return;
    const values = {
      success: auditAnalytics.current.success,
      warning: auditAnalytics.current.warning,
      failed: auditAnalytics.current.failed,
      total: auditAnalytics.total,
    };
    for (const [key, value] of Object.entries(values)) {
      const id = key === "failed" ? "audit-log-failed-count" : `audit-log-${key}-count`;
      const node = document.getElementById(id);
      if (node) node.textContent = String(value);
    }
    for (const key of ["success", "warning", "failed"]) {
      const card = summaryCards()[key];
      const trend = card?.querySelector(".audit-refine-trend");
      if (!trend) continue;
      const data = trendData(auditAnalytics.current[key], auditAnalytics.previous[key]);
      trend.className = `audit-refine-trend is-${key} direction-${data.tone}`;
      const value = trend.querySelector("strong");
      if (value) value.textContent = data.text;
    }
  }

  async function fetchAuditAnalytics(force = false) {
    if (analyticsPromise) {
      const inflight = analyticsPromise;
      await inflight;
      if (!force) return auditAnalytics;
    }
    const now = Date.now();
    const knownTotal = typeof qaAuditPagination !== "undefined"
      ? Number(qaAuditPagination.total || 0)
      : 0;
    if (
      !force
      && auditAnalytics
      && now - auditAnalytics.loadedAt < ANALYTICS_TTL_MS
      && (!knownTotal || knownTotal === auditAnalytics.total)
    ) {
      applyAuditAnalytics();
      return auditAnalytics;
    }

    analyticsPromise = (async () => {
      const all = [];
      let page = 1;
      let totalPages = 1;
      let total = knownTotal;
      const cutoff = now - (14 * 24 * 60 * 60 * 1000);

      do {
        const response = await request(`/audit-events/page/${page}/size/500`);
        const events = Array.isArray(response?.audit_events) ? response.audit_events : [];
        all.push(...events);
        const pagination = response?.pagination || {};
        total = Number(pagination.total || total || all.length);
        totalPages = Math.max(1, Number(pagination.total_pages || 1));
        const oldest = events.length ? auditTimestamp(events[events.length - 1]) : 0;
        if (!events.length || (oldest && oldest < cutoff)) break;
        page += 1;
      } while (page <= totalPages);

      const currentStart = now - (7 * 24 * 60 * 60 * 1000);
      auditAnalytics = {
        loadedAt: Date.now(),
        total,
        current: countEvents(all, currentStart, now + 1),
        previous: countEvents(all, cutoff, currentStart),
      };
      persistAuditAnalytics(auditAnalytics);
      applyAuditAnalytics();
      return auditAnalytics;
    })().catch((_error) => {
      const totalNode = document.getElementById("audit-log-total-count");
      if (totalNode && knownTotal) totalNode.textContent = String(knownTotal);
      return null;
    }).finally(() => {
      analyticsPromise = null;
    });
    return analyticsPromise;
  }

  function healthStorageKey() {
    const identity = state?.user?.id || state?.user?.username || "anonymous";
    return `nowlert:audit-health:${HEALTH_STORAGE_VERSION}:${encodeURIComponent(String(identity))}`;
  }

  function healthCounts(checks) {
    const counts = { healthy: 0, warning: 0, error: 0 };
    for (const check of checks || []) {
      const status = normalizedDetailKey(check?.status);
      if (status === "healthy") counts.healthy += 1;
      else if (status === "warning") counts.warning += 1;
      else counts.error += 1;
    }
    return counts;
  }

  function makeHealthSnapshot(checks, durationMs, completedAt = Date.now()) {
    const safeChecks = (Array.isArray(checks) ? checks : []).map((check) => ({
      key: String(check?.key || "unknown"),
      name: String(check?.name || friendlyName(check?.key || "Health check")),
      status: ["healthy", "warning", "error"].includes(normalizedDetailKey(check?.status))
        ? normalizedDetailKey(check.status)
        : "error",
      detail: String(check?.detail || "No detail reported"),
    }));
    return {
      completedAt: Number(completedAt || Date.now()),
      durationMs: Math.max(0, Number(durationMs || 0)),
      checks: safeChecks,
      counts: healthCounts(safeChecks),
    };
  }

  function readHealthSnapshot() {
    try {
      const raw = window.localStorage.getItem(healthStorageKey());
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.checks) || !parsed.checks.length) return null;
      return makeHealthSnapshot(parsed.checks, parsed.durationMs, parsed.completedAt);
    } catch (_error) {
      return null;
    }
  }

  function persistHealthSnapshot(snapshot) {
    if (!snapshot) return;
    state.auditHealthSnapshot = snapshot;
    try {
      window.localStorage.setItem(healthStorageKey(), JSON.stringify(snapshot));
    } catch (_error) {
      // Safe health snapshot persistence is optional; current-session state still works.
    }
  }

  function healthStatusCopy(snapshot) {
    if (!snapshot) return { label: "Loading latest health", tone: "loading" };
    if (snapshot.counts.error > 0) return { label: "Completed with failures", tone: "error" };
    if (snapshot.counts.warning > 0) return { label: "Completed with warnings", tone: "warning" };
    return { label: "Completed successfully", tone: "healthy" };
  }

  function healthDurationText(durationMs) {
    const value = Math.max(0, Number(durationMs || 0));
    if (value < 1000) return `${Math.round(value)}ms`;
    if (value < 10_000) return `${(value / 1000).toFixed(1)}s`;
    return `${Math.round(value / 1000)}s`;
  }

  function healthCheckIcon(status) {
    if (status === "healthy") return "✓";
    if (status === "warning") return "!";
    return "×";
  }

  function renderHealthDashboard() {
    const strip = document.getElementById("audit-log-health-strip");
    if (!strip) return;
    strip.hidden = false;
    strip.removeAttribute("hidden");
    strip.classList.add("audit-health-dashboard-host");

    const snapshot = state.auditHealthSnapshot || readHealthSnapshot();
    if (snapshot && !state.auditHealthSnapshot) {
      state.auditHealthSnapshot = snapshot;
      if (!Array.isArray(state.healthChecks) || !state.healthChecks.length) {
        state.healthChecks = snapshot.checks;
      }
    }

    const legacyHealthList = document.getElementById("health-check-list");
    const dashboard = make("div", "audit-health-dashboard");
    const checksPanel = make("section", "audit-health-checks-panel");
    const checksHeading = make("div", "audit-health-panel-heading");
    const headingCopy = make("span", "audit-health-heading-copy");
    headingCopy.append(
      make("strong", "", "Health checks"),
      make("small", "", "Latest real operational checks across Nowlert."),
    );
    const headingIcon = make("span", "audit-health-heading-icon", "⌁");
    headingIcon.setAttribute("aria-hidden", "true");
    checksHeading.append(headingIcon, headingCopy);
    checksPanel.append(checksHeading);

    const checks = snapshot?.checks || [];
    const cards = make("div", "audit-health-cards");
    if (checks.length) {
      for (const check of checks) {
        const card = make("article", `audit-health-card is-${check.status}`);
        const icon = make("span", "audit-health-card-icon", healthCheckIcon(check.status));
        const copy = make("span", "audit-health-card-copy");
        copy.append(
          make("strong", "", check.name),
          make("small", "", check.detail),
          make("span", "audit-health-card-status", capitalize(check.status)),
        );
        card.append(icon, copy);
        cards.append(card);
      }
    } else {
      const loading = make("div", "audit-health-loading");
      loading.append(
        make("strong", "", "Preparing health checks"),
        make("span", "", "Nowlert is loading the latest operational health state."),
      );
      cards.append(loading);
    }
    checksPanel.append(cards);

    const latest = make("section", "audit-health-latest-panel");
    latest.append(make("strong", "audit-health-latest-title", "Latest health check run"));
    if (snapshot) {
      const status = healthStatusCopy(snapshot);
      const statusRow = make("div", `audit-health-latest-status is-${status.tone}`);
      statusRow.append(
        make("span", "audit-health-latest-status-icon", healthCheckIcon(
          status.tone === "healthy" ? "healthy" : status.tone === "warning" ? "warning" : "error",
        )),
        make("span", "audit-health-latest-status-copy"),
      );
      statusRow.lastElementChild.append(
        make("strong", "", status.label),
        make("small", "", formatTime(snapshot.completedAt)),
      );
      latest.append(statusRow);

      const stats = make("div", "audit-health-latest-stats");
      const statItems = [
        ["◷", healthDurationText(snapshot.durationMs), "Duration", "neutral"],
        ["✓", snapshot.counts.healthy, "Passed", "healthy"],
        ["!", snapshot.counts.warning, "Warnings", "warning"],
        ["×", snapshot.counts.error, "Failed", "error"],
      ];
      for (const [icon, value, label, tone] of statItems) {
        const stat = make("div", `audit-health-stat is-${tone}`);
        stat.append(
          make("span", "audit-health-stat-icon", icon),
          make("strong", "", value),
          make("small", "", label),
        );
        stats.append(stat);
      }
      latest.append(stats);
    } else {
      latest.append(emptyState(
        "No saved health run yet",
        "A safe initial health run is being performed so this summary can stay visible.",
      ));
    }

    dashboard.append(checksPanel, latest);
    strip.replaceChildren();
    if (legacyHealthList) {
      legacyHealthList.hidden = true;
      legacyHealthList.classList.add("audit-health-legacy-list");
      strip.append(legacyHealthList);
    }
    strip.append(dashboard);
  }

  async function refreshAuditPageAfterHealth() {
    if (typeof qaLoadAuditPage === "function") {
      const page = typeof qaAuditPage !== "undefined" ? qaAuditPage : 1;
      await qaLoadAuditPage(page);
    } else {
      const audit = await request("/audit-events");
      state.audit = audit?.audit_events || [];
      renderAudit();
    }
  }

  async function ensureHealthSnapshot() {
    const existing = state.auditHealthSnapshot || readHealthSnapshot();
    if (existing) {
      state.auditHealthSnapshot = existing;
      if (!Array.isArray(state.healthChecks) || !state.healthChecks.length) {
        state.healthChecks = existing.checks;
      }
      renderHealthDashboard();
      return existing;
    }
    if (Array.isArray(state.healthChecks) && state.healthChecks.length) {
      const snapshot = makeHealthSnapshot(state.healthChecks, 0, Date.now());
      persistHealthSnapshot(snapshot);
      renderHealthDashboard();
      return snapshot;
    }
    if (healthPromise || initialHealthAttempted) return healthPromise;

    initialHealthAttempted = true;
    const started = performance.now();
    healthPromise = request("/health-checks").then(async (response) => {
      state.healthChecks = Array.isArray(response?.checks) ? response.checks : [];
      const snapshot = makeHealthSnapshot(
        state.healthChecks,
        performance.now() - started,
        Date.now(),
      );
      persistHealthSnapshot(snapshot);
      renderHealthDashboard();
      await refreshAuditPageAfterHealth();
      await fetchAuditAnalytics(true);
      return snapshot;
    }).catch((_error) => {
      renderHealthDashboard();
      return null;
    }).finally(() => {
      healthPromise = null;
    });
    return healthPromise;
  }

  function refineAudit() {
    refineRunChecks();
    refineRows();
    refineDetailBody();
    restoreAuditAnalytics();
    ensureSummaryMetricChrome();
    applyAuditAnalytics();
    renderHealthDashboard();
    if (state?.user && state.currentView === "audit") {
      void fetchAuditAnalytics();
      void ensureHealthSnapshot();
    }
  }

  function scheduleRefine() {
    window.requestAnimationFrame(refineAudit);
  }

  renderAudit = function renderAuditWithFinalRefinement(...args) {
    const result = previousRenderAudit(...args);
    scheduleRefine();
    return result;
  };

  if (previousLoadAuditPage) {
    qaLoadAuditPage = async function qaLoadAuditPageWithFinalRefinement(page) {
      const result = await previousLoadAuditPage(page);
      scheduleRefine();
      return result;
    };
  }

  navigate = function navigateWithFinalAuditRefinement(...args) {
    const result = previousNavigate(...args);
    scheduleRefine();
    return result;
  };

  if (previousResourceAction) {
    resourceAction = async function resourceActionWithAuditHealth(action, id) {
      if (action !== "run-health-checks") {
        return previousResourceAction(action, id);
      }
      const started = performance.now();
      const result = await previousResourceAction(action, id);
      if (Array.isArray(state.healthChecks) && state.healthChecks.length) {
        persistHealthSnapshot(makeHealthSnapshot(
          state.healthChecks,
          performance.now() - started,
          Date.now(),
        ));
      }
      renderHealthDashboard();
      await refreshAuditPageAfterHealth();
      await fetchAuditAnalytics(true);
      scheduleRefine();
      return result;
    };
  }

  document.addEventListener("click", (event) => {
    if (event.target.closest(
      "#view-audit .audit-log-row, #view-audit .audit-log-detail-tabs button, #view-audit #audit-log-time-sort, #view-audit #audit-log-clear-filters, #view-audit .audit-log-detail-close, [data-action='run-health-checks']",
    )) {
      scheduleRefine();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if (
      event.target.closest("#view-audit .audit-log-row")
      && (event.key === "Enter" || event.key === " ")
    ) {
      scheduleRefine();
    }
  }, true);

  document.addEventListener("change", (event) => {
    if (event.target.closest("#view-audit .audit-log-filters")) scheduleRefine();
  }, true);

  document.addEventListener("input", (event) => {
    if (event.target.id === "audit-search") scheduleRefine();
  }, true);

  document.addEventListener("DOMContentLoaded", scheduleRefine);
})();