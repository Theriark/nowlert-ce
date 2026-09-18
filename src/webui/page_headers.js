"use strict";

/* Unified page command headers for the accepted CE management surfaces. */
(() => {
  const ADMIN_VIEWS = new Set(["users", "settings", "updates", "data"]);
  const DATA_TOOLBAR_VIEWS = new Set(["audit"]);
  const PAGE_COPY = {
    dashboard: "Monitor your alert delivery pipeline and system health.",
    "routing-flow": "Visualize active routes, filters, and destinations.",
    destinations: "Configure delivery targets for Discord, Microsoft Teams, Slack, and generic webhooks.",
    filtering: "Control which notifications can reach each destination.",
    deliveries: "Review final delivery outcomes, retries, response status, and safe transport errors for routed events.",
    audit: "Review security-relevant actions, health checks, outcomes, and operational details.",
    backups: "Configure backup destinations, schedules, snapshots, restore operations, and portable configuration.",
    tokens: "Allow external applications to submit events to /api/v2/events.",
    account: "Manage your profile information and account access.",
  };
  const ADMIN_COPY = "Manage Nowlert users, settings, updates, and portable configuration.";
  const homes = new Map();
  const moved = new Set();
  let scheduled = false;
  let observer = null;

  function activeView() {
    return String(state?.currentView || "dashboard");
  }

  function viewSection(view) {
    return document.getElementById(`view-${view}`);
  }

  function directToolbar(section) {
    if (!section) return null;
    return section.querySelector(":scope > .section-toolbar");
  }

  function ensureTopbar() {
    const topbar = document.querySelector(".topbar");
    const title = document.getElementById("page-title");
    const actions = topbar?.querySelector(".topbar-actions");
    if (!topbar || !title || !actions) return null;

    topbar.classList.add("page-command-bar");
    actions.classList.add("page-command-actions");

    let copy = topbar.querySelector(":scope > .page-command-copy");
    if (!copy) {
      copy = document.createElement("div");
      copy.className = "page-command-copy";
      const mobile = document.getElementById("mobile-menu");
      if (mobile?.nextSibling) topbar.insertBefore(copy, mobile.nextSibling);
      else topbar.insertBefore(copy, actions);
      copy.append(title);
    } else if (title.parentElement !== copy) {
      copy.prepend(title);
    }

    let subtitle = document.getElementById("page-subtitle");
    if (!subtitle) {
      subtitle = document.createElement("p");
      subtitle.id = "page-subtitle";
      copy.append(subtitle);
    }

    return { topbar, title, subtitle, actions };
  }

  function rememberHome(node) {
    if (!node || homes.has(node)) return;
    homes.set(node, {
      parent: node.parentElement,
      next: node.nextSibling,
    });
  }

  function restoreNode(node) {
    const home = homes.get(node);
    if (!home?.parent) return;
    const reference = home.next && home.next.parentElement === home.parent
      ? home.next
      : null;
    home.parent.insertBefore(node, reference);
  }

  function reconcileMoved(desired, actions) {
    for (const node of [...moved]) {
      if (desired.has(node)) continue;
      restoreNode(node);
      moved.delete(node);
    }

    for (const node of desired) {
      if (!node) continue;
      rememberHome(node);
      if (node.parentElement !== actions) actions.append(node);
      moved.add(node);
    }
  }

  function toolbarCopy(toolbar) {
    const paragraph = toolbar?.querySelector(":scope > div > p, :scope > p");
    return String(paragraph?.textContent || "").trim();
  }

  function expectedTitle(view) {
    if (ADMIN_VIEWS.has(view)) return "Administration";
    if (view === "tokens") return "API access";
    if (view === "account") return "Profile";
    return VIEW_TITLES?.[view] || document.getElementById("page-title")?.textContent || "Nowlert";
  }

  function expectedSubtitle(view, toolbar) {
    if (ADMIN_VIEWS.has(view)) return ADMIN_COPY;
    return PAGE_COPY[view] || toolbarCopy(toolbar);
  }

  function setDataToolbar(toolbar, enabled) {
    if (!toolbar) return;
    toolbar.classList.toggle("page-data-toolbar", enabled);
    if (enabled) {
      toolbar.hidden = false;
      toolbar.removeAttribute("aria-hidden");
      const copy = toolbar.querySelector(":scope > div");
      if (copy) copy.hidden = true;
      return;
    }
    const copy = toolbar.querySelector(":scope > div");
    if (copy) copy.hidden = false;
  }

  function syncDeliveryPanelControls(section) {
    if (!section) return;
    const panelHeader = section.querySelector('[data-panel-header="deliveries"]');
    if (!panelHeader) return;

    let controls = panelHeader.querySelector(":scope > .delivery-panel-controls");
    if (!controls) {
      controls = document.createElement("div");
      controls.className = "delivery-panel-controls";
      panelHeader.append(controls);
    }

    const search = section.querySelector("#delivery-search")?.closest(".search-field");
    const bottom = section.querySelector('[data-qa-bottom="delivery-pagination"]');
    if (search && search.parentElement !== controls) controls.append(search);
    if (bottom && bottom.parentElement !== controls) controls.append(bottom);
  }

  function syncAuditHealthResults(section) {
    const healthPanel = section?.querySelector(".health-panel");
    if (!healthPanel) return;
    healthPanel.hidden = false;
    healthPanel.removeAttribute("aria-hidden");
    healthPanel.classList.add("audit-health-results");
    const heading = healthPanel.querySelector(":scope > .panel-heading");
    if (heading) heading.hidden = true;
  }

  function syncBackupAction(section) {
    if (!section) return;
    const action = section.querySelector('[data-action="new-backup-target"]');
    const panelHeading = section.querySelector(".backup-targets-card > .panel-heading");
    if (!action || !panelHeading || action.parentElement === panelHeading) return;
    action.className = "button primary";
    panelHeading.append(action);
  }

  function syncAdministration(section, toolbar) {
    if (!section || !toolbar) return;
    toolbar.hidden = false;
    toolbar.removeAttribute("aria-hidden");
    toolbar.classList.remove("page-data-toolbar");
    toolbar.classList.add("administration-section-header");

    const tabs = section.querySelector(":scope > .administration-tabs");
    if (tabs && tabs.nextElementSibling !== toolbar) {
      section.insertBefore(tabs, toolbar);
    }
  }

  function normalActionNodes(view, section) {
    const nodes = [];
    if (view === "dashboard") {
      nodes.push(document.getElementById("ops-dashboard-top-actions"));
    } else if (view === "routing-flow") {
      nodes.push(
        document.getElementById("rf-live-status"),
        document.getElementById("rf-range")?.closest(".rf-range"),
      );
    } else if (view === "destinations") {
      nodes.push(document.getElementById("add-destination-button"));
    } else if (view === "filtering") {
      nodes.push(document.getElementById("add-filter-button"));
    } else if (view === "audit") {
      nodes.push(section?.querySelector('[data-action="run-health-checks"]'));
    } else if (view === "tokens") {
      nodes.push(section?.querySelector('[data-action="new-token"]'));
    } else if (view === "account") {
      nodes.push(document.getElementById("restart-header-button"));
    }
    return nodes.filter(Boolean);
  }

  function syncPageHeader() {
    scheduled = false;
    const chrome = ensureTopbar();
    if (!chrome) return;

    const view = activeView();
    const section = viewSection(view);
    const toolbar = directToolbar(section);
    const desired = new Set();

    if (view === "account") delete chrome.title.dataset.i18nSource;
    chrome.title.textContent = expectedTitle(view);
    chrome.subtitle.textContent = expectedSubtitle(view, toolbar);
    chrome.subtitle.hidden = !chrome.subtitle.textContent;
    chrome.topbar.dataset.pageView = view;

    document.querySelectorAll(".administration-section-header").forEach((node) => {
      if (node !== toolbar) node.classList.remove("administration-section-header");
    });

    if (view === "deliveries") syncDeliveryPanelControls(section);
    if (view === "audit") syncAuditHealthResults(section);
    if (view === "backups") syncBackupAction(section);

    if (ADMIN_VIEWS.has(view)) {
      syncAdministration(section, toolbar);
    } else {
      if (toolbar) toolbar.classList.remove("administration-section-header");
      if (DATA_TOOLBAR_VIEWS.has(view)) {
        setDataToolbar(toolbar, true);
      } else if (toolbar) {
        setDataToolbar(toolbar, false);
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
      }

      for (const node of normalActionNodes(view, section)) desired.add(node);
    }

    if (view === "backups") {
      const status = section?.querySelector(".backup-heading-status");
      if (status) desired.add(status);
    }

    reconcileMoved(desired, chrome.actions);

    const platformMenu = document.getElementById("platform-menu");
    if (platformMenu) {
      platformMenu.hidden = true;
      platformMenu.style.display = "none";
    }
  }

  function scheduleSync() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(syncPageHeader);
  }

  function bindObserver() {
    observer?.disconnect();
    observer = new MutationObserver((mutations) => {
      const watchedIds = new Set([
        "ops-dashboard-top-actions",
        "rf-live-status",
        "rf-range",
        "platform-restart",
        "platform-check-updates",
      ]);
      const relevant = mutations.some((mutation) => (
        [...mutation.addedNodes, ...mutation.removedNodes].some((node) => {
          if (node.nodeType !== Node.ELEMENT_NODE) return false;
          if (watchedIds.has(node.id)) return true;
          if (node.matches?.("[data-qa-bottom]")) return true;
          return [...node.querySelectorAll("[id], [data-qa-bottom]")].some((child) => (
            watchedIds.has(child.id) || child.matches("[data-qa-bottom]")
          ));
        })
      ));
      if (relevant) syncPageHeader();
    });
    const shell = document.getElementById("app-shell");
    if (shell) observer.observe(shell, { childList: true, subtree: true });
  }

  const previousNavigate = navigate;
  navigate = function navigateWithUnifiedPageHeader(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    syncPageHeader();
    return result;
  };

  const previousShowApp = showApp;
  showApp = function showAppWithUnifiedPageHeader(session) {
    const result = previousShowApp(session);
    syncPageHeader();
    return result;
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindObserver();
    syncPageHeader();
  });
})();

/* Selected Audit Log workbench acceptance. */
(() => {
  let selectedAuditKey = "";
  let activeAuditTab = "overview";
  let controlsBound = false;
  const filters = {
    action: "",
    outcome: "",
    range: "7d",
    sort: "newest",
  };

  const originalRenderAudit = renderAudit;
  const originalRenderHealthChecks =
    typeof renderHealthChecks === "function" ? renderHealthChecks : null;
  const originalLoadAuditPage =
    typeof qaLoadAuditPage === "function" ? qaLoadAuditPage : null;

  function auditTimestamp(item) {
    const value = item?.created_at || 0;
    const number = Number(value);
    if (!Number.isFinite(number) || number <= 0) return 0;
    return number < 10_000_000_000 ? number * 1000 : number;
  }

  function auditKey(item, index = 0) {
    return String(
      item?.id
      || item?.audit_id
      || `${item?.created_at || 0}:${item?.action || "unknown"}:${item?.resource_id || "none"}:${item?.actor_user_id || index}`,
    );
  }

  function auditTone(value) {
    const normalized = String(value || "").toLowerCase();
    if (["failure", "failed", "error", "danger", "critical"].includes(normalized)) return "danger";
    if (["warning", "warn", "pending", "retrying"].includes(normalized)) return "warning";
    if (["success", "ok", "healthy", "delivered"].includes(normalized)) return "success";
    return "information";
  }

  function auditIcon(action) {
    const value = String(action || "").toLowerCase();
    if (value.startsWith("destination.")) return "▣";
    if (value.startsWith("session.")) return "♙";
    if (value.startsWith("health.")) return "♡";
    if (value.startsWith("user.")) return "♙";
    if (value.includes("config") || value.includes("settings")) return "⚙";
    if (value.includes("route")) return "↗";
    if (value.includes("backup")) return "▤";
    return "◇";
  }

  function shortAuditId(value, length = 16) {
    const text = String(value || "");
    if (!text) return "—";
    return text.length > length ? `${text.slice(0, length)}…` : text;
  }

  function auditActor(item) {
    if (typeof auditActorLabel === "function") return auditActorLabel(item);
    return item?.actor_username || item?.actor_user_id || "System";
  }

  function auditDetails(item) {
    if (typeof auditDetailsText === "function") return auditDetailsText(item?.details);
    if (!item?.details) return "No additional details";
    if (typeof item.details === "string") return item.details;
    return Object.entries(item.details)
      .map(([key, value]) => `${friendlyName(key)}: ${detailValue(value)}`)
      .join(" · ");
  }

  function detailValue(value) {
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

  function selectControl(id, label, options) {
    const wrapper = element("label", { className: "audit-log-select" });
    wrapper.append(element("span", { className: "sr-only", text: label }));
    const select = element("select", { attributes: { id, "aria-label": label } });
    for (const [value, text] of options) {
      select.append(element("option", { value, text }));
    }
    wrapper.append(select);
    return wrapper;
  }

  function setSelectOptions(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    const normalized = [...new Set(values.filter(Boolean).map((value) => String(value)))];
    normalized.sort((left, right) => left.localeCompare(right));
    if (current && !normalized.includes(current)) normalized.unshift(current);
    select.replaceChildren(element("option", { value: "", text: emptyLabel }));
    for (const value of normalized) {
      const text = select.id === "audit-log-action-filter"
        ? auditActionLabel(value)
        : friendlyName(value);
      select.append(element("option", { value, text }));
    }
    select.value = current;
  }

  function summaryCard(id, icon, label, tone, note) {
    return element("article", { className: `audit-log-summary-card ${tone}` }, [
      element("span", { className: "audit-log-summary-icon", text: icon, attributes: { "aria-hidden": "true" } }),
      element("div", { className: "audit-log-summary-copy" }, [
        element("strong", { attributes: { id }, text: "0" }),
        element("span", { text: label }),
        element("small", { text: note }),
      ]),
    ]);
  }

  function ensureAuditLayout() {
    const view = byId("view-audit");
    if (!view || byId("audit-log-workbench")) return;

    const search = byId("audit-search");
    const searchField = search?.closest(".search-field") || null;
    const legacyTablePanel = view.querySelector(":scope > .table-panel");
    const legacyHealthPanel = view.querySelector(":scope > .health-panel");
    const healthList = byId("health-check-list");
    const auditFooter = view.querySelector(":scope > .audit-footer");
    if (!search || !searchField || !legacyTablePanel || !auditFooter) return;

    view.classList.add("audit-log-revamp");
    search.placeholder = "Search action, outcome, user, resource, or details...";

    const summary = element("section", {
      className: "audit-log-summary",
      attributes: { id: "audit-log-summary", "aria-label": "Audit event summary" },
    }, [
      summaryCard("audit-log-success-count", "✓", "Successful events", "success", "Loaded page"),
      summaryCard("audit-log-warning-count", "!", "Warning events", "warning", "Loaded page"),
      summaryCard("audit-log-failed-count", "×", "Failed events", "danger", "Loaded page"),
      summaryCard("audit-log-total-count", "▥", "Total events", "total", "All pages"),
    ]);

    const healthStrip = element("section", {
      className: "audit-log-health-strip",
      hidden: true,
      attributes: { id: "audit-log-health-strip", "aria-label": "Latest Nowlert health checks" },
    });
    const healthHeading = element("div", { className: "audit-log-health-heading" }, [
      element("strong", { text: "Health checks" }),
      element("span", { attributes: { id: "audit-log-health-count" }, text: "0 checks" }),
    ]);
    healthStrip.append(healthHeading);
    if (healthList) healthStrip.append(healthList);

    if (legacyHealthPanel) {
      legacyHealthPanel.classList.add("audit-log-legacy-health");
      legacyHealthPanel.setAttribute("aria-hidden", "true");
    }

    const controls = element("div", {
      className: "audit-log-filters",
      attributes: { id: "audit-log-filters", "aria-label": "Audit log filters" },
    });
    controls.append(searchField);
    controls.append(
      selectControl("audit-log-action-filter", "Filter by action", [["", "All actions"]]),
      selectControl("audit-log-outcome-filter", "Filter by outcome", [["", "All outcomes"]]),
      selectControl("audit-log-range-filter", "Filter by date range", [
        ["all", "All dates"],
        ["1d", "Last 24 hours"],
        ["7d", "Last 7 days"],
        ["30d", "Last 30 days"],
      ]),
    );
    const clear = element("button", {
      className: "button secondary audit-log-clear",
      text: "Clear filters",
      type: "button",
      attributes: { id: "audit-log-clear-filters" },
    });
    controls.append(clear);

    const workbench = element("div", {
      className: "audit-log-workbench",
      attributes: { id: "audit-log-workbench" },
    });

    const listPanel = element("section", {
      className: "audit-log-list-panel",
      attributes: { "aria-label": "Audit events" },
    });
    const columns = element("div", { className: "audit-log-columns", attributes: { "aria-hidden": "true" } }, [
      element("button", { className: "audit-log-sort-time", text: "Time ↓", type: "button", attributes: { id: "audit-log-time-sort", tabindex: "-1" } }),
      element("span", { text: "Action" }),
      element("span", { text: "User" }),
      element("span", { text: "Resource" }),
      element("span", { text: "Outcome" }),
      element("span", { text: "" }),
    ]);
    const listScroll = element("div", { className: "audit-log-list-scroll" });
    const list = element("div", { className: "audit-log-list", attributes: { id: "audit-log-list" } });
    listScroll.append(list);
    const listFooter = element("div", {
      className: "audit-log-list-footer",
      attributes: { id: "audit-log-list-footer" },
    });
    listFooter.append(auditFooter);
    listPanel.append(columns, listScroll, listFooter);

    const detail = element("aside", {
      className: "audit-log-detail",
      attributes: { id: "audit-log-detail", "aria-label": "Selected audit event details" },
    });
    workbench.append(listPanel, detail);

    legacyTablePanel.hidden = true;
    legacyTablePanel.setAttribute("aria-hidden", "true");
    view.append(summary, healthStrip, controls, workbench);

    byId("audit-log-range-filter").value = filters.range;
    bindAuditControls();
    syncAuditPagination();
    syncHealthStrip();
  }

  function bindAuditControls() {
    if (controlsBound) return;
    controlsBound = true;

    const search = byId("audit-search");
    if (search) search.addEventListener("input", renderAuditWorkbench);

    for (const [id, key] of [
      ["audit-log-action-filter", "action"],
      ["audit-log-outcome-filter", "outcome"],
      ["audit-log-range-filter", "range"],
    ]) {
      byId(id)?.addEventListener("change", (event) => {
        filters[key] = event.target.value;
        selectedAuditKey = "";
        renderAuditWorkbench();
      });
    }

    byId("audit-log-clear-filters")?.addEventListener("click", () => {
      filters.action = "";
      filters.outcome = "";
      filters.range = "7d";
      if (search) search.value = "";
      byId("audit-log-action-filter").value = "";
      byId("audit-log-outcome-filter").value = "";
      byId("audit-log-range-filter").value = "7d";
      selectedAuditKey = "";
      renderAuditWorkbench();
    });

    byId("audit-log-time-sort")?.addEventListener("click", () => {
      filters.sort = filters.sort === "newest" ? "oldest" : "newest";
      renderAuditWorkbench();
    });
  }

  function refreshAuditFilterOptions() {
    const items = state.audit || [];
    setSelectOptions(
      byId("audit-log-action-filter"),
      items.map((item) => item.action),
      "All actions",
    );
    setSelectOptions(
      byId("audit-log-outcome-filter"),
      items.map((item) => item.outcome),
      "All outcomes",
    );
  }

  function filteredAuditItems() {
    const query = String(byId("audit-search")?.value || "").trim().toLowerCase();
    const now = Date.now();
    const rangeMs = {
      "1d": 24 * 60 * 60 * 1000,
      "7d": 7 * 24 * 60 * 60 * 1000,
      "30d": 30 * 24 * 60 * 60 * 1000,
    }[filters.range] || 0;

    const items = (state.audit || []).filter((item) => {
      if (filters.action && String(item.action || "") !== filters.action) return false;
      if (filters.outcome && String(item.outcome || "") !== filters.outcome) return false;
      if (rangeMs) {
        const timestamp = auditTimestamp(item);
        if (timestamp && timestamp < now - rangeMs) return false;
      }
      if (!query) return true;
      return JSON.stringify([
        item.action,
        item.actor_username,
        item.actor_user_id,
        item.resource_type,
        item.resource_id,
        item.outcome,
        item.details,
      ]).toLowerCase().includes(query);
    });

    items.sort((left, right) => {
      const delta = auditTimestamp(right) - auditTimestamp(left);
      return filters.sort === "oldest" ? -delta : delta;
    });
    return items;
  }

  function updateAuditSummary() {
    const items = state.audit || [];
    const counts = { success: 0, warning: 0, danger: 0 };
    for (const item of items) {
      const tone = auditTone(item.outcome);
      if (tone in counts) counts[tone] += 1;
    }
    const total = typeof qaAuditPagination !== "undefined"
      ? Number(qaAuditPagination.total || items.length)
      : items.length;
    const values = {
      "audit-log-success-count": counts.success,
      "audit-log-warning-count": counts.warning,
      "audit-log-failed-count": counts.danger,
      "audit-log-total-count": total,
    };
    for (const [id, value] of Object.entries(values)) {
      const node = byId(id);
      if (node) node.textContent = String(value);
    }
  }

  function auditActionCell(item) {
    const cell = element("span", { className: "audit-log-action-cell" });
    cell.append(element("span", { className: "audit-log-action-icon", text: auditIcon(item.action), attributes: { "aria-hidden": "true" } }));
    cell.append(element("span", { className: "audit-log-action-copy" }, [
      element("strong", { text: auditActionLabel(item.action) }),
      element("small", { text: item.action || "unknown" }),
    ]));
    return cell;
  }

  function renderAuditRows(items) {
    const list = byId("audit-log-list");
    if (!list) return;
    list.replaceChildren();

    if (!items.length) {
      list.append(element("div", { className: "audit-log-empty" }, [
        element("strong", { text: "No matching audit events" }),
        element("span", { text: "Change the search or filters to show audit activity." }),
      ]));
      return;
    }

    items.forEach((item, index) => {
      const key = auditKey(item, index);
      const row = element("div", {
        className: `audit-log-row${key === selectedAuditKey ? " selected" : ""}`,
        attributes: {
          role: "button",
          tabindex: "0",
          "aria-pressed": key === selectedAuditKey ? "true" : "false",
          "data-audit-log-key": key,
        },
      });
      const user = auditActor(item);
      row.append(
        element("span", { className: "audit-log-time", text: formatTime(item.created_at) }),
        auditActionCell(item),
        element("span", { className: "audit-log-user-cell" }, [
          element("strong", { text: user }),
          item.actor_user_id ? element("small", { text: `ID ${shortAuditId(item.actor_user_id, 10)}` }) : null,
        ]),
        element("span", { className: "audit-log-resource-cell" }, [
          element("strong", { text: friendlyName(item.resource_type || "Platform") }),
          element("small", { text: shortAuditId(item.resource_id || "Platform-level action") }),
        ]),
        badge(capitalize(item.outcome || "unknown"), auditTone(item.outcome)),
      );
      const more = element("button", {
        className: "audit-log-row-more",
        text: "⋮",
        type: "button",
        attributes: { "aria-label": `Inspect ${auditActionLabel(item.action)} audit event` },
      });
      more.addEventListener("click", (event) => {
        event.stopPropagation();
        selectedAuditKey = key;
        activeAuditTab = "overview";
        renderAuditWorkbench();
      });
      row.append(more);
      const select = () => {
        selectedAuditKey = key;
        activeAuditTab = "overview";
        renderAuditWorkbench();
      };
      row.addEventListener("click", select);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
      list.append(row);
    });
  }

  function detailRow(label, value, extra = null) {
    const row = element("div", { className: "audit-log-detail-row" }, [
      element("span", { text: label }),
      element("strong", { text: value || "—" }),
    ]);
    if (extra) row.append(extra);
    return row;
  }

  async function copyAuditValue(value, label) {
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

  function detailEntries(item) {
    if (!item?.details || typeof item.details !== "object" || Array.isArray(item.details)) return [];
    return Object.entries(item.details);
  }

  function renderKeyValueTab(item, predicate, emptyCopy) {
    const entries = detailEntries(item).filter(([key]) => predicate(key));
    if (!entries.length) {
      return element("div", { className: "audit-log-detail-empty-card" }, [
        element("strong", { text: "No additional data" }),
        element("span", { text: emptyCopy }),
      ]);
    }
    return element("section", { className: "audit-log-detail-card audit-log-detail-kv" }, [
      ...entries.map(([key, value]) => detailRow(friendlyName(key), detailValue(value))),
    ]);
  }

  function renderOverviewTab(item) {
    const resourceCopy = item.resource_id
      ? element("button", { className: "audit-log-copy-icon", text: "⧉", type: "button", attributes: { "aria-label": "Copy resource ID" } })
      : null;
    if (resourceCopy) resourceCopy.addEventListener("click", () => copyAuditValue(item.resource_id, "Resource ID"));

    const details = item.details && typeof item.details === "object" ? item.details : {};
    const duration = details.duration_ms ?? details.duration ?? item.duration_ms ?? "";
    return element("div", { className: "audit-log-overview" }, [
      element("section", { className: "audit-log-detail-card audit-log-detail-kv" }, [
        detailRow("Timestamp", formatTime(item.created_at)),
        detailRow("Action", auditActionLabel(item.action)),
        detailRow("User", auditActor(item)),
        detailRow("Resource type", friendlyName(item.resource_type || "Platform")),
        detailRow("Resource ID", item.resource_id || "Platform-level action", resourceCopy),
        detailRow("Outcome", capitalize(item.outcome || "unknown")),
        duration !== "" ? detailRow("Duration", `${detailValue(duration)}${String(duration).match(/^\d+(\.\d+)?$/) ? " ms" : ""}`) : null,
        detailRow("Details", auditDetails(item)),
      ]),
      element("section", { className: "audit-log-detail-card audit-log-additional" }, [
        element("strong", { text: "Additional information" }),
        element("div", { className: "audit-log-detail-empty-card compact" }, [
          element("span", { text: detailEntries(item).length ? "Use the Details, Request, and Response tabs to inspect recorded safe metadata." : "No additional details were recorded for this event." }),
        ]),
      ]),
    ]);
  }

  function renderDetailsTab(item) {
    const entries = detailEntries(item);
    if (!entries.length) {
      return element("div", { className: "audit-log-detail-empty-card" }, [
        element("strong", { text: "No structured details" }),
        element("span", { text: auditDetails(item) }),
      ]);
    }
    return element("section", { className: "audit-log-detail-card audit-log-detail-kv" }, [
      ...entries.map(([key, value]) => detailRow(friendlyName(key), detailValue(value))),
    ]);
  }

  function renderRelatedTab(item) {
    const card = element("section", { className: "audit-log-detail-card audit-log-detail-kv" }, [
      detailRow("Action", item.action || "unknown"),
      detailRow("Actor ID", item.actor_user_id || "—"),
      detailRow("Resource type", item.resource_type || "Platform"),
      detailRow("Resource ID", item.resource_id || "—"),
    ]);
    if (item.resource_id) {
      const copy = element("button", {
        className: "button secondary small audit-log-related-copy",
        text: "Copy resource ID",
        type: "button",
      });
      copy.addEventListener("click", () => copyAuditValue(item.resource_id, "Resource ID"));
      card.append(copy);
    }
    return card;
  }

  function renderActiveTab(item, container) {
    container.replaceChildren();
    if (activeAuditTab === "details") {
      container.append(renderDetailsTab(item));
      return;
    }
    if (activeAuditTab === "request") {
      container.append(renderKeyValueTab(
        item,
        (key) => /request|method|path|endpoint|ip|user_agent|client|source|url/i.test(key),
        "This event did not record safe request context.",
      ));
      return;
    }
    if (activeAuditTab === "response") {
      container.append(renderKeyValueTab(
        item,
        (key) => /response|status|error|retry|safe|code|result/i.test(key),
        "This event did not record safe response context.",
      ));
      return;
    }
    if (activeAuditTab === "related") {
      container.append(renderRelatedTab(item));
      return;
    }
    container.append(renderOverviewTab(item));
  }

  function renderAuditDetail(item) {
    const panel = byId("audit-log-detail");
    if (!panel) return;
    panel.replaceChildren();

    if (!item) {
      panel.append(element("div", { className: "audit-log-detail-empty" }, [
        element("strong", { text: "Select an audit event" }),
        element("span", { text: "Choose an event on the left to inspect the recorded security and operational context." }),
      ]));
      return;
    }

    const header = element("div", { className: "audit-log-detail-heading" }, [
      element("div", {}, [
        element("strong", { text: "Event details" }),
        element("small", { text: "Detailed information about the selected audit event." }),
      ]),
    ]);
    const close = element("button", {
      className: "icon-button audit-log-detail-close",
      text: "×",
      type: "button",
      attributes: { "aria-label": "Clear selected audit event" },
    });
    close.addEventListener("click", () => {
      selectedAuditKey = "";
      renderAuditWorkbench();
    });
    header.append(badge(capitalize(item.outcome || "unknown"), auditTone(item.outcome)), close);

    const identity = element("section", { className: "audit-log-detail-identity" }, [
      element("span", { className: "audit-log-detail-icon", text: auditIcon(item.action), attributes: { "aria-hidden": "true" } }),
      element("div", {}, [
        element("strong", { text: auditActionLabel(item.action) }),
        element("small", { text: item.action || "unknown" }),
      ]),
      element("div", { className: "audit-log-detail-time" }, [
        element("strong", { text: formatTime(item.created_at) }),
      ]),
    ]);

    const tabs = element("div", {
      className: "audit-log-detail-tabs",
      attributes: { id: "audit-log-detail-tabs", role: "tablist", "aria-label": "Audit event detail sections" },
    });
    for (const [key, label] of [
      ["overview", "Overview"],
      ["details", "Details"],
      ["request", "Request"],
      ["response", "Response"],
      ["related", "Related"],
    ]) {
      const tab = element("button", {
        className: key === activeAuditTab ? "active" : "",
        text: label,
        type: "button",
        attributes: { role: "tab", "aria-selected": key === activeAuditTab ? "true" : "false" },
      });
      tab.addEventListener("click", () => {
        activeAuditTab = key;
        renderAuditDetail(item);
      });
      tabs.append(tab);
    }

    const body = element("div", { className: "audit-log-detail-body", attributes: { id: "audit-log-detail-body" } });
    renderActiveTab(item, body);
    panel.append(header, identity, tabs, body);
  }

  function syncAuditPagination() {
    const view = byId("view-audit");
    const target = byId("audit-log-list-footer");
    if (!view || !target) return;
    const row = view.querySelector('.qa-pagination-row[data-qa-pager="audit-pagination"]');
    if (row && row.parentElement !== target) target.prepend(row);
  }

  function syncHealthStrip() {
    const strip = byId("audit-log-health-strip");
    if (!strip) return;
    const checks = Array.isArray(state.healthChecks) ? state.healthChecks : [];
    strip.hidden = checks.length === 0;
    const count = byId("audit-log-health-count");
    if (count) count.textContent = `${checks.length} check${checks.length === 1 ? "" : "s"}`;
  }

  function renderAuditWorkbench() {
    ensureAuditLayout();
    if (!byId("audit-log-workbench")) return;

    refreshAuditFilterOptions();
    filters.action = byId("audit-log-action-filter")?.value || filters.action;
    filters.outcome = byId("audit-log-outcome-filter")?.value || filters.outcome;
    filters.range = byId("audit-log-range-filter")?.value || filters.range;

    const sortButton = byId("audit-log-time-sort");
    if (sortButton) sortButton.textContent = filters.sort === "newest" ? "Time ↓" : "Time ↑";

    const items = filteredAuditItems();
    const keyed = items.map((item, index) => [auditKey(item, index), item]);
    if (!keyed.some(([key]) => key === selectedAuditKey)) {
      selectedAuditKey = keyed.length ? keyed[0][0] : "";
      activeAuditTab = "overview";
    }

    updateAuditSummary();
    renderAuditRows(items);
    renderAuditDetail(keyed.find(([key]) => key === selectedAuditKey)?.[1] || null);
    syncAuditPagination();
    syncHealthStrip();
  }

  renderAudit = function renderAuditWithSelectedWorkbench() {
    originalRenderAudit();
    renderAuditWorkbench();
  };

  if (originalLoadAuditPage) {
    qaLoadAuditPage = async function qaLoadAuditPageWithSelectedWorkbench(page) {
      const result = await originalLoadAuditPage(page);
      renderAuditWorkbench();
      return result;
    };
  }

  if (originalRenderHealthChecks) {
    renderHealthChecks = function renderHealthChecksWithSelectedAuditWorkbench() {
      originalRenderHealthChecks();
      syncHealthStrip();
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureAuditLayout();
    renderAuditWorkbench();
  });
})();
