"use strict";

/* Cross-page UI consistency corrections layered after the accepted WebUI modules. */
(() => {
  const CHANNEL_DESTINATION_TYPES = new Set(["discord", "slack", "teams"]);
  const REFERENCE_PAGERS = new Set(["delivery-pagination", "audit-pagination"]);
  let scheduled = false;
  let userActionHome = null;

  function span(className = "", text = "") {
    const node = document.createElement("span");
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function shareIcon() {
    const wrapper = span("destination-share-icon");
    wrapper.setAttribute("aria-hidden", "true");
    wrapper.innerHTML = `
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <circle cx="18" cy="5" r="2"></circle>
        <circle cx="6" cy="12" r="2"></circle>
        <circle cx="18" cy="19" r="2"></circle>
        <path d="m8 11 8-5M8 13l8 5"></path>
      </svg>
    `;
    return wrapper;
  }

  function eyeIcon() {
    const wrapper = span("destination-view-icon");
    wrapper.setAttribute("aria-hidden", "true");
    wrapper.innerHTML = `
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <path d="M2.5 12s3.4-6 9.5-6 9.5 6 9.5 6-3.4 6-9.5 6-9.5-6-9.5-6Z"></path>
        <circle cx="12" cy="12" r="2.5"></circle>
      </svg>
    `;
    return wrapper;
  }

  function databaseIcon(className = "integration-behavior-database-icon") {
    const wrapper = span(className);
    wrapper.setAttribute("aria-hidden", "true");
    wrapper.innerHTML = `
      <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
        <ellipse cx="12" cy="5.5" rx="6.5" ry="2.8"></ellipse>
        <path d="M5.5 5.5v5c0 1.55 2.9 2.8 6.5 2.8s6.5-1.25 6.5-2.8v-5"></path>
        <path d="M5.5 10.5v5c0 1.55 2.9 2.8 6.5 2.8s6.5-1.25 6.5-2.8v-5"></path>
      </svg>
    `;
    return wrapper;
  }

  function syncDestinationStatusButton(button) {
    if (!button) return;
    const current = String(button.textContent || "").trim().toLowerCase();
    const enabled = current === "enabled" || current === "active";
    const stateName = enabled ? "active" : "disabled";
    if (
      button.dataset.consistencyState === stateName
      && button.querySelector(".destination-status-dot")
    ) return;

    button.dataset.consistencyState = stateName;
    button.className = `button small destination-status-control is-${stateName}`;
    button.setAttribute(
      "aria-label",
      enabled ? "Active destination. Click to disable." : "Disabled destination. Click to enable.",
    );
    button.replaceChildren(
      span("destination-status-dot"),
      span("destination-status-label", enabled ? "Active" : "Disabled"),
    );
  }

  function syncDestinationSharingButton(button) {
    if (!button) return;
    const current = String(button.textContent || "").trim().toLowerCase();
    const shared = current === "shared";
    const stateName = shared ? "shared" : "private";
    if (
      button.dataset.consistencySharing === stateName
      && button.querySelector(".destination-share-icon")
    ) return;

    button.dataset.consistencySharing = stateName;
    button.className = `button small destination-sharing-control is-${stateName}`;
    button.setAttribute(
      "aria-label",
      shared ? "Shared destination. Click to make private." : "Private destination. Click to share.",
    );
    button.replaceChildren(
      shareIcon(),
      span("destination-sharing-label", shared ? "Shared" : "Private"),
    );
  }

  function readOnlyStatus(label, className, icon = null) {
    const item = span(`badge ${className}`);
    if (icon) item.append(icon);
    item.append(span("destination-readonly-label", label));
    return item;
  }

  function syncMetadataPrivateSharing(card) {
    if (!card?.classList.contains("acceptance-private-destination")) return;
    const meta = card.querySelector(".resource-meta");
    if (!meta) return;

    let privateBadge = [...meta.children].find((item) => (
      String(item.textContent || "").trim().toLowerCase() === "private"
    ));
    if (!privateBadge) {
      privateBadge = readOnlyStatus("Private", "destination-sharing-control is-private", shareIcon());
      meta.prepend(privateBadge);
    } else if (!privateBadge.querySelector(".destination-share-icon")) {
      privateBadge.className = "badge destination-sharing-control is-private";
      privateBadge.setAttribute("aria-label", "Private destination");
      privateBadge.replaceChildren(
        shareIcon(),
        span("destination-sharing-label", "Private"),
      );
    }

    let active = meta.querySelector(".destination-private-active");
    if (!active) {
      active = readOnlyStatus("Active", "destination-status-control destination-private-active is-active");
      active.prepend(span("destination-status-dot"));
      meta.prepend(active);
    }

    const owner = [...meta.children].find((item) => (
      String(item.textContent || "").trim().toLowerCase().startsWith("owner:")
    ));
    if (owner && owner.textContent.trim() !== "Owner: User") {
      owner.textContent = "Owner: User";
    }
    if (owner) owner.classList.add("destination-owner-badge");

    const viewOnly = [...meta.children].find((item) => {
      const text = String(item.textContent || "").trim().toLowerCase();
      return text === "metadata only" || text === "view only";
    });
    if (viewOnly && !viewOnly.classList.contains("destination-view-only-badge")) {
      viewOnly.className = "badge destination-view-only-badge";
      viewOnly.replaceChildren(eyeIcon(), span("destination-readonly-label", "View only"));
    }
  }

  function destinationItemForCard(card) {
    const action = card.querySelector("[data-id]");
    const id = String(action?.dataset.id || card.dataset.privateDestinationId || "");
    if (!id || typeof state === "undefined" || !Array.isArray(state.destinations)) return null;
    return state.destinations.find((item) => String(item.id || "") === id) || null;
  }

  function syncDestinationSubtitle(card) {
    const item = destinationItemForCard(card);
    if (!item) return;
    const heading = card.querySelector(".resource-heading");
    const subtitle = heading?.querySelector("small");
    if (!subtitle) return;

    const provider = typeof OUTPUT_NAMES === "object" && OUTPUT_NAMES[item.output_type]
      ? OUTPUT_NAMES[item.output_type]
      : String(item.output_type || "Destination");
    const rawChannel = String(item.settings?.channel_name || "").replace(/^#+/, "");
    const channel = rawChannel ? `#${rawChannel}` : "";
    const desired = channel && CHANNEL_DESTINATION_TYPES.has(item.output_type)
      ? `${provider} - ${channel}`
      : provider;
    if (subtitle.textContent !== desired) subtitle.textContent = desired;
  }

  function syncDestinations() {
    const add = document.getElementById("add-destination-button");
    if (add && add.textContent !== "+ New destination") {
      add.textContent = "+ New destination";
    }

    for (const card of document.querySelectorAll("#view-destinations #destination-list > .resource-card")) {
      card.classList.add("destination-reference-card");
      syncDestinationStatusButton(card.querySelector('[data-action="toggle-destination"]'));
      syncDestinationSharingButton(card.querySelector('[data-action="toggle-destination-shared"]'));
      syncMetadataPrivateSharing(card);
      syncDestinationSubtitle(card);
    }
  }

  function channelValue(value) {
    return String(value || "").replace(/^#+/, "");
  }

  function syncDestinationChannelField() {
    const type = document.getElementById("destination-type")?.value || "";
    const settings = document.getElementById("destination-settings");
    const input = settings?.querySelector('[data-field="channel_name"]');
    if (!settings || !input) return;

    const existingWrapper = input.closest(".destination-channel-input");
    if (!CHANNEL_DESTINATION_TYPES.has(type)) {
      if (existingWrapper) existingWrapper.replaceWith(input);
      input.closest("label")?.classList.remove("destination-channel-field");
      return;
    }

    const label = input.closest("label");
    if (!label) return;
    label.classList.add("destination-channel-field");

    if (!existingWrapper) {
      const wrapper = document.createElement("div");
      wrapper.className = "destination-channel-input";
      const prefix = span("destination-channel-prefix", "#");
      input.before(wrapper);
      wrapper.append(prefix, input);
    }

    const normalized = channelValue(input.value);
    if (input.value !== normalized) input.value = normalized;
    if (input.dataset.channelPrefixBound !== "1") {
      input.dataset.channelPrefixBound = "1";
      input.addEventListener("input", () => {
        const value = channelValue(input.value);
        if (value !== input.value) input.value = value;
      });
    }
  }

  function installChannelCollection() {
    if (typeof collectFields !== "function" || collectFields.referenceChannelPrefix) return;
    const previousCollectFields = collectFields;
    const replacement = function collectFieldsWithChannelPrefix(container) {
      const result = previousCollectFields(container);
      if (container?.id !== "destination-settings") return result;
      const type = document.getElementById("destination-type")?.value || "";
      if (!CHANNEL_DESTINATION_TYPES.has(type) || !("channel_name" in result)) return result;
      const channel = channelValue(result.channel_name);
      result.channel_name = channel ? `#${channel}` : "";
      return result;
    };
    replacement.referenceChannelPrefix = true;
    collectFields = replacement;
  }

  function installDestinationFieldHook() {
    if (typeof renderDestinationFields !== "function" || renderDestinationFields.referenceChannelPrefix) return;
    const previousRenderDestinationFields = renderDestinationFields;
    const replacement = function renderDestinationFieldsWithChannelPrefix(...args) {
      const result = previousRenderDestinationFields(...args);
      syncDestinationChannelField();
      return result;
    };
    replacement.referenceChannelPrefix = true;
    renderDestinationFields = replacement;
  }

  function rememberUserActionHome(button) {
    if (!button || userActionHome) return;
    userActionHome = {
      parent: button.parentElement,
      next: button.nextSibling,
    };
  }

  function restoreUserAction(button) {
    if (!button || !userActionHome?.parent) return;
    const reference = userActionHome.next?.parentElement === userActionHome.parent
      ? userActionHome.next
      : null;
    userActionHome.parent.insertBefore(button, reference);
  }

  function syncUsers() {
    const section = document.getElementById("view-users");
    if (!section) return;
    section.querySelectorAll("#view-users .private-resource-count")
      .forEach((node) => node.remove());

    const toolbar = section.querySelector(":scope > .section-toolbar");
    const topbarActions = document.querySelector(".topbar-actions");
    const button = section?.querySelector('[data-action="new-user"]')
      || topbarActions?.querySelector('[data-action="new-user"]');
    if (!toolbar || !button) return;

    rememberUserActionHome(button);
    if (button.textContent !== "+ New user") button.textContent = "+ New user";

    const active = typeof state !== "undefined" && String(state.currentView || "") === "users";
    if (toolbar.hidden !== active) toolbar.hidden = active;
    if (active) {
      if (toolbar.getAttribute("aria-hidden") !== "true") toolbar.setAttribute("aria-hidden", "true");
    } else if (toolbar.hasAttribute("aria-hidden")) {
      toolbar.removeAttribute("aria-hidden");
    }

    if (active && topbarActions && button.parentElement !== topbarActions) {
      topbarActions.append(button);
    } else if (!active && button.parentElement === topbarActions) {
      restoreUserAction(button);
    }
  }

  function syncLiveCopy() {
    const dashboard = document.getElementById("ops-feed-age");
    if (dashboard) {
      const detail = String(dashboard.textContent || "");
      if (detail.startsWith("Data updated ")) {
        dashboard.textContent = `Updated ${detail.slice("Data updated ".length)}`;
      }
    }

    const flow = document.getElementById("rf-live-age");
    if (flow) {
      const detail = String(flow.textContent || "");
      if (detail.startsWith("Snapshot ")) {
        flow.textContent = `Updated ${detail.slice("Snapshot ".length)}`;
      }
    }
  }

  function pagerButton(text, label, disabled, action, className = "reference-pagination-control") {
    const button = element("button", {
      className,
      text,
      type: "button",
      disabled,
      attributes: { "aria-label": label },
    });
    if (!disabled) button.addEventListener("click", action);
    return button;
  }

  function referencePageNumbers(page, totalPages) {
    if (totalPages <= 5) return Array.from({ length: totalPages }, (_value, index) => index + 1);
    const start = Math.max(1, Math.min(page - 2, totalPages - 4));
    const end = Math.min(totalPages, start + 4);
    const values = [];
    if (start > 1) values.push("ellipsis");
    for (let value = start; value <= end; value += 1) values.push(value);
    if (end < totalPages) values.push("ellipsis");
    return values;
  }

  function installReferencePagination() {
    if (typeof qaPager !== "function" || qaPager.referencePagination) return;
    const previousQaPager = qaPager;

    const replacement = function qaPagerWithReferenceLayout(containerId, pagination, onPage) {
      if (!REFERENCE_PAGERS.has(containerId)) {
        return previousQaPager(containerId, pagination, onPage);
      }

      let container = byId(containerId);
      if (!container) {
        container = element("div", {
          className: "qa-pagination",
          attributes: { id: containerId, "aria-label": "Pagination" },
        });
        return container;
      }

      const page = Math.max(1, Number(pagination.page || 1));
      const pageSize = Math.max(1, Number(pagination.page_size || 25));
      const totalPages = Math.max(1, Number(pagination.total_pages || 1));
      const total = Math.max(0, Number(pagination.total || 0));
      const startItem = total ? ((page - 1) * pageSize) + 1 : 0;
      const endItem = total ? Math.min(page * pageSize, total) : 0;

      const navigatePage = (targetPage) => {
        const target = Math.max(1, Math.min(totalPages, Number(targetPage || 1)));
        if (target === page) return;
        let result;
        try {
          result = onPage(target);
        } catch (error) {
          if (typeof qaScrollPageBottom === "function") qaScrollPageBottom();
          throw error;
        }
        Promise.resolve(result).then(
          () => { if (typeof qaScrollPageBottom === "function") qaScrollPageBottom(); },
          () => { if (typeof qaScrollPageBottom === "function") qaScrollPageBottom(); },
        );
      };

      const range = span("reference-pagination-range", `${startItem} – ${endItem} of ${total}`);
      const pages = document.createElement("div");
      pages.className = "reference-pagination-pages";
      pages.append(
        pagerButton("«", "First page", page <= 1, () => navigatePage(1)),
        pagerButton("‹", "Previous page", page <= 1, () => navigatePage(page - 1)),
      );

      for (const value of referencePageNumbers(page, totalPages)) {
        if (value === "ellipsis") {
          pages.append(span("reference-pagination-ellipsis", "…"));
          continue;
        }
        const current = value === page;
        pages.append(pagerButton(
          String(value),
          `Page ${value}`,
          current,
          () => navigatePage(value),
          `reference-pagination-page${current ? " is-current" : ""}`,
        ));
      }

      pages.append(
        pagerButton("›", "Next page", page >= totalPages, () => navigatePage(page + 1)),
        pagerButton("»", "Last page", page >= totalPages, () => navigatePage(totalPages)),
      );

      const jump = document.createElement("div");
      jump.className = "reference-pagination-jump";
      jump.append(span("reference-pagination-label", "Go to page"));
      const jumpControls = document.createElement("div");
      jumpControls.className = "reference-pagination-jump-controls";
      const input = element("input", {
        className: "reference-pagination-input",
        type: "number",
        value: page,
        attributes: {
          min: "1",
          max: String(totalPages),
          step: "1",
          inputmode: "numeric",
          "aria-label": `Go to page, 1 to ${totalPages}`,
        },
      });
      const go = element("button", {
        className: "button primary reference-pagination-go",
        text: "Go",
        type: "button",
      });
      const jumpToInput = () => {
        const requested = Number(input.value);
        if (!Number.isInteger(requested) || requested < 1 || requested > totalPages) {
          input.value = String(page);
          input.setAttribute("aria-invalid", "true");
          return;
        }
        input.removeAttribute("aria-invalid");
        navigatePage(requested);
      };
      go.addEventListener("click", jumpToInput);
      input.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        jumpToInput();
      });
      jumpControls.append(input, go);
      jump.append(jumpControls);

      container.replaceChildren(range, pages, jump);
      container.dataset.referencePager = "1";
      container.dataset.referenceSignature = `${page}:${pageSize}:${totalPages}:${total}`;
      return container;
    };

    replacement.referencePagination = true;
    qaPager = replacement;
  }

  function syncReferencePagers() {
    if (typeof qaPager !== "function") return;
    const delivery = document.getElementById("delivery-pagination");
    if (delivery && delivery.dataset.referencePager !== "1" && typeof qaDeliveryPagination !== "undefined") {
      qaPager("delivery-pagination", qaDeliveryPagination, qaLoadDeliveryPage);
      if (typeof qaArrangePaginationFooter === "function") {
        qaArrangePaginationFooter("view-deliveries", "delivery-pagination");
      }
    }
    const audit = document.getElementById("audit-pagination");
    if (audit && audit.dataset.referencePager !== "1" && typeof qaAuditPagination !== "undefined") {
      qaPager("audit-pagination", qaAuditPagination, qaLoadAuditPage);
      if (typeof qaArrangePaginationFooter === "function") {
        qaArrangePaginationFooter("view-audit", "audit-pagination");
      }
    }
  }

  function syncDeliveryHistory() {
    document.querySelectorAll("#view-deliveries .delivery-history-detail-close")
      .forEach((node) => node.remove());
  }

  function syncAuditLog() {
    document.querySelectorAll("#view-audit .audit-log-detail-close")
      .forEach((node) => node.remove());
  }

  function syncFilteringTableHeading() {
    const second = document.querySelector(
      "#view-filtering .filtering-table thead th:nth-child(2)",
    );
    if (second && second.textContent !== "Configuration") {
      second.textContent = "Configuration";
    }
  }

  function syncIntegrationBehaviorHeading() {
    const panel = document.getElementById("filtering-deterministic-processing");
    const heading = panel?.querySelector(":scope > .panel-heading");
    if (!heading) return;

    const count = panel.querySelectorAll(".settings-resource-card").length;
    const signature = String(count);
    const expectedCount = `${count} integration${count === 1 ? "" : "s"}`;
    const currentTitle = heading.querySelector(".integration-behavior-heading-copy h3")?.textContent || "";
    const currentDescription = heading.querySelector(".integration-behavior-heading-copy p")?.textContent || "";
    const currentCount = heading.querySelector(".integration-behavior-count-label")?.textContent || "";
    if (
      heading.dataset.referenceHeading === signature
      && currentTitle === "Integration behavior"
      && currentDescription === "Configure how each integration handles and maps incoming data."
      && currentCount === expectedCount
    ) return;

    const main = document.createElement("div");
    main.className = "integration-behavior-heading-main";
    main.append(databaseIcon());
    const copy = document.createElement("div");
    copy.className = "integration-behavior-heading-copy";
    copy.append(
      element("h3", { text: "Integration behavior" }),
      element("p", { text: "Configure how each integration handles and maps incoming data." }),
    );
    main.append(copy);

    const countBadge = span("integration-behavior-count");
    countBadge.append(
      databaseIcon("integration-behavior-count-icon"),
      span("integration-behavior-count-label", expectedCount),
    );

    heading.replaceChildren(main, countBadge);
    heading.dataset.referenceHeading = signature;
  }

  function syncConsistency() {
    scheduled = false;
    syncDestinations();
    syncUsers();
    syncLiveCopy();
    syncDeliveryHistory();
    syncAuditLog();
    syncFilteringTableHeading();
    syncIntegrationBehaviorHeading();
    syncDestinationChannelField();
    syncReferencePagers();
  }

  function scheduleSync() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(syncConsistency);
  }

  installChannelCollection();
  installDestinationFieldHook();
  installReferencePagination();

  const previousNavigate = navigate;
  navigate = function navigateWithManagementConsistency(view, historyMode = "push") {
    const result = previousNavigate(view, historyMode);
    scheduleSync();
    return result;
  };

  const previousShowApp = showApp;
  showApp = function showAppWithManagementConsistency(session) {
    const result = previousShowApp(session);
    scheduleSync();
    return result;
  };

  document.addEventListener("change", (event) => {
    if (event.target?.id === "destination-type") window.requestAnimationFrame(syncDestinationChannelField);
  });

  const observer = new MutationObserver(scheduleSync);
  const shell = document.getElementById("app-shell");
  if (shell) {
    observer.observe(shell, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  document.addEventListener("DOMContentLoaded", scheduleSync, { once: true });
  scheduleSync();
})();
