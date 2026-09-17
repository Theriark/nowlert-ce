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
    backups: "Configure backup destinations, schedules, snapshots, and restore operations.",
    tokens: "Allow external applications to submit events to /api/v2/events.",
    account: "Manage your profile picture, password, and active account security settings.",
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

    const legacyRestart = document.getElementById("restart-header-button");
    if (legacyRestart) {
      legacyRestart.hidden = true;
      legacyRestart.setAttribute("aria-hidden", "true");
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
      nodes.push(document.getElementById("platform-restart"));
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
    scheduleSync();
    return result;
  };

  const previousShowApp = showApp;
  showApp = function showAppWithUnifiedPageHeader(session) {
    const result = previousShowApp(session);
    scheduleSync();
    return result;
  };

  document.addEventListener("DOMContentLoaded", () => {
    bindObserver();
    scheduleSync();
  });
})();
