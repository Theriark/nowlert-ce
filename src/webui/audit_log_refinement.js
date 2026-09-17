"use strict";

/* Final Audit Log fidelity and metadata refinement. */
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

  const previousRenderAudit = renderAudit;
  const previousLoadAuditPage =
    typeof qaLoadAuditPage === "function" ? qaLoadAuditPage : null;
  const previousNavigate = navigate;

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

  function requestEntries(item) {
    return detailEntries(item).filter(([key]) => REQUEST_KEYS.has(String(key).toLowerCase()));
  }

  function responseEntries(item) {
    return detailEntries(item).filter(([key]) => {
      const normalized = String(key).toLowerCase();
      return RESPONSE_KEYS.has(normalized)
        || normalized.startsWith("response_")
        || normalized.startsWith("error_");
    });
  }

  function displayKey(key) {
    let value = String(key || "");
    if (value.startsWith("request_")) value = value.slice("request_".length);
    if (value.startsWith("response_")) value = value.slice("response_".length);
    return typeof friendlyName === "function" ? friendlyName(value) : value.replaceAll("_", " ");
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
    const outcome = String(item?.outcome || "unknown").toLowerCase();
    if (["failed", "failure", "error", "denied", "invalid"].includes(outcome)) return "danger";
    if (["warning", "warn", "pending", "retrying"].includes(outcome)) return "warning";
    if (["success", "ok", "healthy", "delivered"].includes(outcome)) return "success";
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
    const primary = make("strong", options.tone ? `audit-refine-tone ${options.tone}` : "", displayValue(value));
    valueNode.append(primary);
    if (options.secondary) {
      valueNode.append(make("small", "", options.secondary));
    }
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

  function sectionCard(title, rows, emptyTitle, emptyText) {
    const section = make("section", "audit-refine-section");
    section.append(make("strong", "audit-refine-section-title", title));
    section.append(listCard(rows, emptyTitle, emptyText));
    return section;
  }

  function detailRows(entries) {
    return entries.map(([key, value]) => detailRow(displayKey(key), value));
  }

  function summaryDetail(item) {
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    for (const key of ["safe_error", "message", "description", "detail", "note"] ) {
      if (details[key] !== undefined && details[key] !== null && details[key] !== "") {
        return [key, details[key]];
      }
    }
    return null;
  }

  function overviewBody(item) {
    const stack = make("div", "audit-refine-stack");
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    const duration = details.duration_ms ?? details.duration ?? item?.duration_ms ?? "";
    const summary = summaryDetail(item);
    const primaryRows = [
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
      primaryRows.push(detailRow("Duration", `${displayValue(duration)}${suffix}`));
    }
    if (summary) primaryRows.push(detailRow("Details", summary[1]));

    const omittedKeys = new Set(["duration", "duration_ms"]);
    if (summary) omittedKeys.add(summary[0]);
    const additional = detailEntries(item).filter(([key]) => !omittedKeys.has(key));

    stack.append(listCard(primaryRows, "No event details", "No audit details were recorded."));
    stack.append(sectionCard(
      "Additional information",
      detailRows(additional),
      "No additional information",
      "No additional metadata was recorded for this event.",
    ));
    return stack;
  }

  function detailsBody(item) {
    return listCard(
      detailRows(detailEntries(item)),
      "No structured details",
      "No structured audit metadata was recorded for this event.",
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
      detailRow("Action", item.action || "unknown"),
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

  function refineAudit() {
    refineRunChecks();
    refineRows();
    refineDetailBody();
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
