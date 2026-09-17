"use strict";

/* Cross-page UI consistency corrections layered after the accepted WebUI modules. */
(() => {
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

  function syncDestinations() {
    const add = document.getElementById("add-destination-button");
    if (add && add.textContent !== "+ New destination") {
      add.textContent = "+ New destination";
    }

    for (const card of document.querySelectorAll("#view-destinations #destination-list > .resource-card")) {
      syncDestinationStatusButton(card.querySelector('[data-action="toggle-destination"]'));
      syncDestinationSharingButton(card.querySelector('[data-action="toggle-destination-shared"]'));
    }
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
    const toolbar = section?.querySelector(":scope > .section-toolbar");
    const topbarActions = document.querySelector(".topbar-actions");
    const button = section?.querySelector('[data-action="new-user"]')
      || topbarActions?.querySelector('[data-action="new-user"]');
    if (!section || !toolbar || !button) return;

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

  function syncDeliveryHistory() {
    document.querySelector(
      '#view-deliveries [data-delivery-workbench-action="close-detail"]',
    )?.remove();
  }

  function syncIntegrationBehaviorHeading() {
    const panel = document.getElementById("filtering-deterministic-processing");
    const heading = panel?.querySelector(":scope > .panel-heading");
    if (!heading) return;

    const eyebrow = heading.querySelector(".eyebrow");
    const title = heading.querySelector("h3");
    const description = heading.querySelector("p:not(.eyebrow)");
    if (eyebrow && !eyebrow.hidden) eyebrow.hidden = true;
    if (description && !description.hidden) description.hidden = true;
    if (title && title.textContent !== "Integration behavior") {
      title.textContent = "Integration behavior";
    }
  }

  function syncConsistency() {
    scheduled = false;
    syncDestinations();
    syncUsers();
    syncLiveCopy();
    syncDeliveryHistory();
    syncIntegrationBehaviorHeading();
  }

  function scheduleSync() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(syncConsistency);
  }

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
