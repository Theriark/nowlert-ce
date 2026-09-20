"use strict";

(() => {
  const WEBHOOK_ICON = `data:image/svg+xml,${encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#f6c344" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M7.5 6h9M6.3 8.2l4.4 7.5M17.7 8.2l-4.4 7.5"/></g></svg>',
  )}`;
  if (typeof OUTPUT_ICONS === "object" && OUTPUT_ICONS) {
    OUTPUT_ICONS.webhook = WEBHOOK_ICON;
  }

  function installDestinationOverviewStyles() {
    if (document.getElementById("nowlert-destinations-overview-styles")) return;
    const style = document.createElement("style");
    style.id = "nowlert-destinations-overview-styles";
    style.textContent = `
#view-destinations #destination-list {
  align-items: start;
  gap: 0.85rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

#view-destinations #destination-list > .resource-card {
  background:
    radial-gradient(circle at 82% 4%, rgba(244, 197, 66, 0.11), transparent 42%),
    linear-gradient(145deg, rgba(29, 33, 38, 0.97), rgba(20, 24, 29, 0.97));
  border: 1px solid rgba(244, 197, 66, 0.15);
  border-radius: 14px;
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.18);
  min-height: 0 !important;
  overflow: hidden;
  padding: 0.92rem;
  position: relative;
  transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
}

#view-destinations #destination-list > .resource-card:hover {
  border-color: rgba(244, 197, 66, 0.28);
  box-shadow: 0 18px 38px rgba(0, 0, 0, 0.24);
  transform: translateY(-2px);
}

#view-destinations .resource-heading {
  align-items: center;
  min-height: 46px;
}

#view-destinations .resource-identity {
  gap: 0.68rem;
}

#view-destinations .resource-icon {
  background: linear-gradient(145deg, rgba(244, 197, 66, 0.12), rgba(255, 255, 255, 0.035));
  border: 1px solid rgba(244, 197, 66, 0.22);
  border-radius: 11px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.025);
  flex: 0 0 44px;
  height: 44px;
  width: 44px;
}

#view-destinations .resource-icon img,
#view-destinations .resource-icon svg,
#view-destinations .resource-icon > span {
  max-height: 28px;
  max-width: 28px;
}

#view-destinations .resource-identity strong {
  font-size: 0.84rem;
  line-height: 1.2;
}

#view-destinations .resource-identity small {
  font-size: 0.68rem;
  line-height: 1.35;
  margin-top: 0.16rem;
  text-transform: none;
}

#view-destinations .resource-meta {
  border-color: rgba(244, 197, 66, 0.1);
  gap: 0.38rem;
  margin: 0.72rem 0 0.76rem;
  padding: 0.58rem 0;
}

#view-destinations .resource-meta .badge,
#view-destinations .resource-meta .status-button {
  align-items: center;
  display: inline-flex;
  font-size: 0.6rem;
  gap: 0.28rem;
  letter-spacing: 0.035em;
  line-height: 1;
  min-height: 22px;
  padding: 0.28rem 0.45rem;
}

#view-destinations .resource-meta .status-button::before,
#view-destinations .resource-meta .badge.success::before,
#view-destinations .resource-meta .badge.warning::before,
#view-destinations .resource-meta .badge.danger::before {
  background: currentColor;
  border-radius: 999px;
  box-shadow: 0 0 8px currentColor;
  content: "";
  flex: 0 0 6px;
  height: 6px;
  opacity: 0.9;
  width: 6px;
}

#view-destinations .destination-test-detail {
  display: block;
  font-size: 0.68rem;
  line-height: 1.35;
  margin: -0.18rem 0 0.72rem;
}

#view-destinations .resource-actions {
  display: grid !important;
  gap: 0.42rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
}

#view-destinations .resource-actions .button {
  align-items: center;
  border-radius: 8px;
  display: inline-flex;
  font-size: 0.67rem;
  gap: 0.3rem;
  justify-content: center;
  min-height: 34px;
  min-width: 0;
  padding: 0.44rem 0.48rem;
  white-space: nowrap;
}

#view-destinations .resource-actions .button:only-child {
  grid-column: 1 / -1;
}

#view-destinations .resource-actions [data-action="preview-destination"]::before {
  content: "◉";
}

#view-destinations .resource-actions [data-action="test-destination-card"]::before {
  content: "➤";
}

#view-destinations .resource-actions [data-action="edit-destination"]::before {
  content: "✎";
}

#view-destinations .resource-actions [data-action="delete-destination"]::before {
  content: "⌫";
}

#view-destinations .resource-actions .button::before {
  font-size: 0.8rem;
  line-height: 1;
  opacity: 0.92;
}

#view-destinations .acceptance-private-destination .field-help {
  border-top: 1px solid rgba(244, 197, 66, 0.1);
  font-size: 0.68rem;
  line-height: 1.42;
  margin: 0;
  padding-top: 0.72rem;
}

@media (max-width: 1280px) {
  #view-destinations #destination-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  #view-destinations #destination-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  #view-destinations #destination-list {
    grid-template-columns: 1fr;
  }

  #view-destinations .resource-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
`;
    document.head.append(style);
  }

  installDestinationOverviewStyles();

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
      item.enabled === true,
    ]));
  }

  function syncPrivateDestinationMetadataFromState() {
    const resources = Array.isArray(state.privateDestinations)
      ? state.privateDestinations
      : [];
    privateDestinationMetadata = resources;
    privateDestinationMetadataSignature = privateDestinationSignature(resources);
    return resources;
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
        element("div", { className: "resource-heading" }, [
          element("div", { className: "resource-identity" }, [
            element("span", { className: "resource-icon" }, [icon]),
            element("div", {}, [
              element("strong", { text: item.name || "Private destination" }),
              element("small", { text: friendlyName(item.output_type) }),
            ]),
          ]),
        ]),
        element("div", { className: "resource-meta" }, [
          badge("Private", "warning"),
          badge(item.owner_username, "destination-owner-badge"),
          badge("View only", "destination-view-only-badge"),
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
      state.privateDestinations = resources;
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
    for (const row of document.querySelectorAll("#filter-table > tr.filtering-policy-row")) {
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
    const detailRow = row.nextElementSibling?.matches(".filtering-expanded-row")
      && row.nextElementSibling.dataset.filterDetailId === String(policy.destination_id)
      ? row.nextElementSibling
      : null;
    const cards = [...(detailRow || row).querySelectorAll(".filtering-overview-integration")];
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
          badge(item.owner_username, ""),
        ]),
        element("td", {}, [badge("Metadata only", "")]),
      ]);
      body.append(row);
    }
  }

  function applyFilteringAcceptance(payload) {
    if (!payload || state.currentView !== "filtering") return;
    const policies = normalFilterRows(payload);
    const rows = [...document.querySelectorAll("#filter-table > tr.filtering-policy-row")];
    policies.forEach((policy, index) => {
      const row = rows[index];
      if (row) decorateConfiguredFilters(row, policy);
    });
    if (isAdmin()) appendPrivateFilterMetadata(payload.private_resources || []);
    else document.querySelectorAll(".acceptance-private-filter").forEach((node) => node.remove());
    relocateLegacyVisibilityBadges();
  }

  async function refreshFilteringAcceptance() {
    try {
      const payload = await request("/filters");
      applyFilteringAcceptance(payload);
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

  function moveAuditHealthChecksIntoToolbar() {
    const auditView = document.getElementById("view-audit");
    if (!auditView) return;
    const toolbar = auditView.querySelector(".section-toolbar");
    const runChecks = auditView.querySelector('[data-action="run-health-checks"]');
    const healthPanel = auditView.querySelector(".health-panel");

    if (runChecks && toolbar && runChecks.parentElement !== toolbar) {
      runChecks.className = "button secondary";
      toolbar.append(runChecks);
    }
    if (healthPanel) {
      healthPanel.hidden = true;
      healthPanel.setAttribute("aria-hidden", "true");
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
    const list = document.getElementById("destination-list");
    const firstPaint = Boolean(list && list.dataset.destinationFirstPaint !== "1");
    if (firstPaint) list.classList.add("acceptance-destination-first-paint");

    syncPrivateDestinationMetadataFromState();
    const result = previousRenderDestinations();
    cleanupDestinationCards();
    if (isAdmin()) appendPrivateDestinationMetadata(privateDestinationMetadata);
    else appendPrivateDestinationMetadata([]);
    refreshDestinationMetadata();

    if (firstPaint) {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          list.classList.remove("acceptance-destination-first-paint");
          list.dataset.destinationFirstPaint = "1";
        });
      });
    }
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
    if (state.currentView === "audit") moveAuditHealthChecksIntoToolbar();
    return result;
  };

  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-filter-action]")?.dataset.filterAction;
    if (["new-filter", "manage-destination", "continue-destination"].includes(action)) {
      resetIntegrationOrder();
    }
  }, true);

  document.addEventListener("nowlert:filtering-rendered", event => {
    applyFilteringAcceptance(event.detail);
  });

  document.addEventListener("DOMContentLoaded", () => {
    cleanupDestinationCards();
    removeRetiredPermissionControls();
    movePlatformActionsIntoContext();
    moveAuditHealthChecksIntoToolbar();
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
            && node.classList.contains("filtering-policy-row")
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