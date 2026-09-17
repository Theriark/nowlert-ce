"use strict";

(() => {
  let filterRefreshTimer = 0;
  let integrationOrder = [];
  let reorderingIntegrations = false;
  let privateDestinationMetadata = [];
  let privateDestinationMetadataSignature = "";

  function sourceFromRow(row) {
    return row.querySelector('input[data-filter-toggle]')?.dataset.filterToggle || "";
  }

  function stabilizeIntegrationOrder() {
    if (reorderingIntegrations) return;
    const list = document.getElementById("filter-integration-list");
    if (!list) return;
    const rows = [...list.querySelectorAll(":scope > .filtering-integration-row")];
    if (rows.length < 2) return;
    const sources = rows.map(sourceFromRow).filter(Boolean);
    if (!integrationOrder.length) {
      integrationOrder = [...sources];
      return;
    }
    for (const source of sources) {
      if (!integrationOrder.includes(source)) integrationOrder.push(source);
    }
    const position = new Map(integrationOrder.map((source, index) => [source, index]));
    const sorted = [...rows].sort((left, right) => (
      (position.get(sourceFromRow(left)) ?? Number.MAX_SAFE_INTEGER)
      - (position.get(sourceFromRow(right)) ?? Number.MAX_SAFE_INTEGER)
    ));
    if (sorted.every((row, index) => row === rows[index])) return;
    reorderingIntegrations = true;
    sorted.forEach((row) => list.append(row));
    reorderingIntegrations = false;
  }

  function resetIntegrationOrder() {
    integrationOrder = [];
  }

  function cleanupDestinationCards() {
    document.querySelectorAll(".destination-read-only").forEach((node) => node.remove());
  }

  function privateDestinationSignature(items) {
    return JSON.stringify((items || []).map((item) => [
      item.id || "",
      item.name || "",
      item.output_type || "",
      item.owner_username || "",
    ]));
  }

  function appendPrivateDestinationMetadata(items) {
    const list = document.getElementById("destination-list");
    if (!list) return;
    const resources = Array.isArray(items) ? items : [];
    const signature = privateDestinationSignature(resources);
    const existing = [...list.querySelectorAll(".acceptance-private-destination")];
    if (
      list.dataset.privateDestinationSignature === signature
      && existing.length === resources.length
    ) {
      return;
    }
    existing.forEach((node) => node.remove());
    for (const item of resources) {
      const icon = outputIcon(item.output_type);
      const card = element("article", { className: "resource-card acceptance-private-destination" }, [
        element("div", { className: "resource-card-heading" }, [
          element("div", { className: "resource-title" }, [
            icon,
            element("div", {}, [
              element("strong", { text: item.name || "Private destination" }),
              element("small", { text: friendlyName(item.output_type) }),
            ]),
          ]),
        ]),
        element("div", { className: "resource-meta" }, [
          badge("Private", "warning"),
          badge(`Owner: ${item.owner_username || "User"}`, ""),
          badge("Metadata only", ""),
        ]),
        element("p", {
          className: "field-help",
          text: "Configuration, credentials, integrations and filtering remain private to the owner.",
        }),
      ]);
      list.append(card);
    }
    list.dataset.privateDestinationSignature = signature;
  }

  async function refreshDestinationMetadata() {
    cleanupDestinationCards();
    if (!isAdmin()) {
      privateDestinationMetadata = [];
      privateDestinationMetadataSignature = privateDestinationSignature([]);
      appendPrivateDestinationMetadata([]);
      return;
    }
    try {
      const payload = await request("/destinations");
      const resources = Array.isArray(payload.private_resources)
        ? payload.private_resources
        : [];
      const signature = privateDestinationSignature(resources);
      if (signature === privateDestinationMetadataSignature) return;
      privateDestinationMetadata = resources;
      privateDestinationMetadataSignature = signature;
      appendPrivateDestinationMetadata(privateDestinationMetadata);
    } catch (_error) {
      // The normal Destination view remains usable if metadata refresh fails.
    }
  }

  function normalFilterRows(payload) {
    return (Array.isArray(payload.filters) ? payload.filters : [])
      .filter((policy) => Array.isArray(policy.integrations) && policy.integrations.length > 0);
  }

  function relocateLegacyVisibilityBadges() {
    for (const row of document.querySelectorAll("#filter-table > tr:not(.acceptance-private-filter)")) {
      row.querySelectorAll(".filtering-access-badge, .acceptance-visibility-badge")
        .forEach((node) => node.remove());
    }
  }

  function decorateConfiguredFilters(row, policy) {
    const integrations = Array.isArray(policy.integrations) ? policy.integrations : [];
    const activeCount = integrations.filter((item) => item.filter_enabled !== false).length;
    const configuredCount = integrations.length;
    const summary = row.querySelector(".filtering-overview-header strong");
    if (summary) {
      summary.textContent = activeCount
        ? `${configuredCount} configured · ${activeCount} active`
        : `${configuredCount} configured · disabled`;
    }
    const cards = [...row.querySelectorAll(".filtering-overview-integration")];
    cards.forEach((card, index) => {
      const marker = card.querySelector(".filtering-card-check");
      const integration = integrations[index];
      if (!marker || !integration) return;
      if (integration.filter_enabled === false) {
        marker.textContent = "○";
        marker.setAttribute("aria-label", "Filter disabled");
        card.classList.add("acceptance-filter-disabled");
      } else {
        marker.textContent = "✓";
        marker.setAttribute("aria-label", "Filter enabled");
        card.classList.remove("acceptance-filter-disabled");
      }
    });
    relocateLegacyVisibilityBadges();
  }

  function appendPrivateFilterMetadata(items) {
    const body = document.getElementById("filter-table");
    if (!body) return;
    body.querySelectorAll(".acceptance-private-filter").forEach((node) => node.remove());
    for (const item of items || []) {
      const icon = outputIcon(item.output_type);
      const destination = element("div", { className: "filtering-destination-summary" }, [
        icon,
        element("div", {}, [
          element("strong", { text: item.destination_name || "Private destination" }),
          element("small", { text: friendlyName(item.output_type) }),
        ]),
      ]);
      const row = element("tr", { className: "acceptance-private-filter" }, [
        element("td", {}, [destination]),
        element("td", {}, [
          element("strong", { text: "Private filtering configuration" }),
          element("small", { text: "Rules and integration assignments are hidden from administrators." }),
        ]),
        element("td", {}, [
          badge("Private", "warning"),
          badge(`Owner: ${item.owner_username || "User"}`, ""),
        ]),
        element("td", {}, [badge("Metadata only", "")]),
      ]);
      body.append(row);
    }
  }

  async function refreshFilteringAcceptance() {
    try {
      const payload = await request("/filters");
      const policies = normalFilterRows(payload);
      const rows = [...document.querySelectorAll("#filter-table > tr:not(.acceptance-private-filter)")];
      policies.forEach((policy, index) => {
        const row = rows[index];
        if (row) decorateConfiguredFilters(row, policy);
      });
      if (isAdmin()) appendPrivateFilterMetadata(payload.private_resources || []);
      else document.querySelectorAll(".acceptance-private-filter").forEach((node) => node.remove());
      relocateLegacyVisibilityBadges();
    } catch (_error) {
      // Core Filtering rendering remains available if decoration fails.
    }
  }

  function scheduleFilteringAcceptance() {
    window.clearTimeout(filterRefreshTimer);
    filterRefreshTimer = window.setTimeout(refreshFilteringAcceptance, 140);
  }

  function removeRetiredPermissionControls() {
    document.querySelectorAll('[data-action="destination-access"]').forEach((node) => node.remove());
    const dialog = document.getElementById("destination-access-dialog");
    if (dialog?.open) dialog.close();
    dialog?.remove();
  }

  function movePlatformActionsIntoContext() {
    const platformMenu = document.getElementById("platform-menu");
    const updateButton = document.getElementById("platform-check-updates");
    const restartButton = document.getElementById("platform-restart");
    const updateToolbar = document.querySelector("#view-updates .section-toolbar");
    const accountToolbar = document.querySelector("#view-account .section-toolbar");

    if (platformMenu) {
      platformMenu.hidden = true;
      platformMenu.style.display = "none";
      platformMenu.setAttribute("aria-hidden", "true");
    }
    if (updateButton && updateToolbar && updateButton.parentElement !== updateToolbar) {
      updateButton.removeAttribute("role");
      updateButton.className = "button secondary";
      updateToolbar.append(updateButton);
    }
    if (restartButton && accountToolbar && restartButton.parentElement !== accountToolbar) {
      restartButton.removeAttribute("role");
      restartButton.className = "button danger";
      accountToolbar.append(restartButton);
    }
  }

  function suppressProgrammaticMainFocusOutline() {
    const main = document.getElementById("main-content");
    if (!main) return;
    main.style.outline = "none";
  }

  const previousRenderFlow = typeof renderFlow === "function" ? renderFlow : null;
  if (previousRenderFlow) {
    renderFlow = function renderFlowAcceptance() {
      if (!byId("dashboard-flow")) return;
      return previousRenderFlow();
    };
  }

  const previousRenderDestinations = renderDestinations;
  renderDestinations = function renderDestinationsAcceptance() {
    const result = previousRenderDestinations();
    cleanupDestinationCards();
    if (isAdmin()) appendPrivateDestinationMetadata(privateDestinationMetadata);
    else appendPrivateDestinationMetadata([]);
    refreshDestinationMetadata();
    return result;
  };

  const previousRenderUsers = renderUsers;
  renderUsers = function renderUsersAcceptance() {
    const result = previousRenderUsers();
    removeRetiredPermissionControls();
    return result;
  };

  const previousNavigate = navigate;
  navigate = function navigateAcceptance(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    if (state.currentView === "destinations") refreshDestinationMetadata();
    if (state.currentView === "filtering") scheduleFilteringAcceptance();
    if (state.currentView === "users") removeRetiredPermissionControls();
    return result;
  };

  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-filter-action]")?.dataset.filterAction;
    if (["new-filter", "manage-destination", "continue-destination"].includes(action)) {
      resetIntegrationOrder();
    }
  }, true);

  document.addEventListener("DOMContentLoaded", () => {
    cleanupDestinationCards();
    removeRetiredPermissionControls();
    movePlatformActionsIntoContext();
    suppressProgrammaticMainFocusOutline();
    refreshDestinationMetadata();
    scheduleFilteringAcceptance();

    const integrationList = document.getElementById("filter-integration-list");
    if (integrationList) {
      new MutationObserver(stabilizeIntegrationOrder).observe(integrationList, {
        childList: true,
        subtree: false,
      });
    }
    const filterTable = document.getElementById("filter-table");
    if (filterTable) {
      new MutationObserver((mutations) => {
        const normalRowAdded = mutations.some((mutation) => (
          [...mutation.addedNodes].some((node) => (
            node.nodeType === Node.ELEMENT_NODE
            && !node.classList.contains("acceptance-private-filter")
          ))
        ));
        if (normalRowAdded) scheduleFilteringAcceptance();
      }).observe(filterTable, { childList: true, subtree: false });
      new MutationObserver(relocateLegacyVisibilityBadges).observe(filterTable, {
        childList: true,
        subtree: true,
      });
    }
    const userTable = document.getElementById("user-table");
    if (userTable) {
      new MutationObserver(removeRetiredPermissionControls).observe(userTable, {
        childList: true,
        subtree: true,
      });
    }
  });
})();
