"use strict";

(() => {
  delete VIEW_TITLES.sources;

  const ADMIN_ONLY_VIEWS = new Set([
    "users",
    "updates",
    "data",
    "audit",
    "backups",
    "settings",
    "inputs",
  ]);
  let permissionDialogUserId = "";
  let finalOwnershipSyncQueued = false;

  function primaryNav(view) {
    return document.querySelector(`#primary-nav [data-view="${view}"]`);
  }

  function makeButton(label, className = "button secondary") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    return button;
  }

  function setNavActive(item, active) {
    if (!item) return;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  }

  function installManagementNavigation() {
    const admin = Boolean(isAdmin());
    primaryNav("sources")?.remove();
    primaryNav("tokens")?.remove();
    document.getElementById("administration-nav")?.remove();
    document.getElementById("profile-api-access")?.remove();
    document.getElementById("profile-settings")?.remove();

    const auditNav = primaryNav("audit");
    const backupsNav = document.getElementById("backups-nav") || primaryNav("backups");
    const usersNav = document.getElementById("users-nav") || primaryNav("users");
    const settingsNav = document.getElementById("settings-nav") || primaryNav("settings");
    const updatesNav = document.getElementById("updates-nav") || primaryNav("updates");
    const inputsNav = document.getElementById("inputs-nav") || primaryNav("inputs");
    const dataNav = document.getElementById("data-nav") || primaryNav("data");

    if (auditNav) auditNav.hidden = !admin;
    if (backupsNav) backupsNav.hidden = !admin;
    if (usersNav) usersNav.hidden = !admin;
    if (settingsNav) settingsNav.hidden = !admin;
    if (updatesNav) updatesNav.hidden = !admin;
    if (inputsNav) inputsNav.hidden = true;
    if (dataNav) dataNav.hidden = true;

    if (auditNav && backupsNav && auditNav.nextElementSibling !== backupsNav) {
      auditNav.after(backupsNav);
    }
    if (backupsNav && usersNav && backupsNav.nextElementSibling !== usersNav) {
      backupsNav.after(usersNav);
    }
    if (usersNav && settingsNav && usersNav.nextElementSibling !== settingsNav) {
      usersNav.after(settingsNav);
    }
    if (settingsNav && updatesNav && settingsNav.nextElementSibling !== updatesNav) {
      settingsNav.after(updatesNav);
    }
  }

  function installProfileItems() {
    document.querySelector("#profile-menu-button .profile-chevron")?.remove();
    document.getElementById("profile-api-access")?.remove();
    document.getElementById("profile-settings")?.remove();
  }

  function removeNestedManagementTabs() {
    document.querySelectorAll(".administration-tabs").forEach((tabs) => tabs.remove());
  }

  function prepareEmbeddedToolbar(toolbar, title) {
    if (!toolbar) return;
    toolbar.hidden = false;
    toolbar.removeAttribute("aria-hidden");
    toolbar.classList.remove("administration-section-header", "page-data-toolbar");
    const copy = toolbar.querySelector(":scope > div");
    if (copy) copy.hidden = false;
    const heading = toolbar.querySelector("h2");
    if (heading && title) heading.textContent = title;
  }

  function embedAccountApiTokens() {
    const accountSection = document.getElementById("view-account");
    const tokenSection = document.getElementById("view-tokens");
    const accountGrid = accountSection?.querySelector(":scope > .account-grid");
    if (!accountSection || !tokenSection || !accountGrid) return;

    let container = accountSection.querySelector(":scope > #account-api-tokens");
    if (!container) {
      container = document.createElement("section");
      container.id = "account-api-tokens";
      container.className = "embedded-management-block";
      container.style.display = "grid";
      container.style.gap = "16px";
      container.style.marginTop = "16px";
      accountGrid.after(container);
    }

    const toolbar = tokenSection.querySelector(":scope > .section-toolbar")
      || container.querySelector(":scope > .section-toolbar");
    const panel = tokenSection.querySelector(":scope > .table-panel")
      || container.querySelector(":scope > .table-panel");
    if (toolbar) {
      prepareEmbeddedToolbar(toolbar, "API tokens");
      const action = tokenSection.querySelector('[data-action="new-token"]')
        || container.querySelector('[data-action="new-token"]')
        || document.querySelector('[data-action="new-token"]');
      if (action && action.parentElement !== toolbar) toolbar.append(action);
      if (toolbar.parentElement !== container) container.append(toolbar);
    }
    if (panel && panel.parentElement !== container) container.append(panel);

    tokenSection.hidden = true;
    tokenSection.setAttribute("aria-hidden", "true");
  }

  function embedBackupDataTools() {
    const backupsSection = document.getElementById("view-backups");
    const dataSection = document.getElementById("view-data");
    const backupsGrid = backupsSection?.querySelector(":scope > .data-tools-grid");
    const scheduleCard = backupsGrid?.querySelector(".backup-schedule-card");
    if (!backupsSection || !dataSection || !backupsGrid || !scheduleCard) return;

    let container = backupsGrid.querySelector(":scope > #backup-data-tools");
    if (!container) {
      container = document.createElement("section");
      container.id = "backup-data-tools";
      container.className = "embedded-management-block";
      container.style.gridColumn = "1 / -1";
      container.style.display = "grid";
      container.style.gap = "16px";
      scheduleCard.after(container);
    }

    const toolbar = dataSection.querySelector(":scope > .section-toolbar")
      || container.querySelector(":scope > .section-toolbar");
    const dataGrid = dataSection.querySelector(":scope > .data-tools-grid")
      || container.querySelector(":scope > .data-tools-grid");
    if (toolbar) {
      prepareEmbeddedToolbar(toolbar, "Data tools");
      if (toolbar.parentElement !== container) container.append(toolbar);
    }
    if (dataGrid && dataGrid.parentElement !== container) container.append(dataGrid);

    dataSection.hidden = true;
    dataSection.setAttribute("aria-hidden", "true");
  }

  function syncPageOwnership(view = state.currentView) {
    const admin = Boolean(isAdmin());
    const auditNav = primaryNav("audit");
    const backupsNav = document.getElementById("backups-nav") || primaryNav("backups");
    const usersNav = document.getElementById("users-nav") || primaryNav("users");
    const settingsNav = document.getElementById("settings-nav") || primaryNav("settings");
    const updatesNav = document.getElementById("updates-nav") || primaryNav("updates");

    document.getElementById("administration-nav")?.remove();
    document.getElementById("profile-api-access")?.remove();
    document.getElementById("profile-settings")?.remove();
    removeNestedManagementTabs();
    embedAccountApiTokens();
    embedBackupDataTools();

    if (auditNav) auditNav.hidden = !admin;
    if (backupsNav) backupsNav.hidden = !admin;
    if (usersNav) usersNav.hidden = !admin;
    if (settingsNav) settingsNav.hidden = !admin;
    if (updatesNav) updatesNav.hidden = !admin;

    setNavActive(backupsNav, view === "backups");
    setNavActive(usersNav, view === "users");
    setNavActive(settingsNav, view === "settings");
    setNavActive(updatesNav, view === "updates");

    const addDestination = document.getElementById("add-destination-button");
    if (addDestination && state.user) addDestination.hidden = false;
    const addRoute = document.getElementById("add-route-button");
    if (addRoute) addRoute.hidden = true;

    const title = document.getElementById("page-title");
    const subtitle = document.getElementById("page-subtitle");
    const section = document.getElementById(`view-${view}`);
    const toolbar = section?.querySelector(":scope > .section-toolbar");
    const toolbarCopy = toolbar?.querySelector(":scope > div");

    const setPageCopy = (heading, copy) => {
      if (title) title.textContent = heading;
      if (subtitle) {
        subtitle.textContent = copy;
        subtitle.hidden = !copy;
      }
    };

    if (view === "account") {
      setPageCopy(
        "Account security",
        "Manage your profile picture, password, API tokens, and active account security settings.",
      );
      if (toolbar) {
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("administration-section-header", "page-data-toolbar");
      }
    } else if (view === "backups") {
      setPageCopy(
        "Backups",
        "Configure backup destinations, schedules, snapshots, restore operations, and portable configuration.",
      );
      if (toolbar) {
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("administration-section-header", "page-data-toolbar");
      }
    } else if (view === "users") {
      setPageCopy("Users", "Manage local accounts, roles, access state, and password resets.");
      if (toolbar) {
        toolbar.hidden = false;
        toolbar.removeAttribute("aria-hidden");
        toolbar.classList.remove("administration-section-header", "page-data-toolbar");
        if (toolbarCopy) toolbarCopy.hidden = true;
      }
    } else if (view === "settings") {
      setPageCopy("Settings", "Configure regional preferences and integration-specific behavior.");
      if (toolbar) {
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("administration-section-header", "page-data-toolbar");
        if (toolbarCopy) toolbarCopy.hidden = false;
      }
    } else if (view === "updates") {
      setPageCopy("Updates", "Review the running version and any advertised Nowlert update.");
      if (toolbar) {
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("administration-section-header", "page-data-toolbar");
        if (toolbarCopy) toolbarCopy.hidden = false;
      }
    }
  }

  function scheduleFinalOwnershipSync() {
    if (finalOwnershipSyncQueued) return;
    finalOwnershipSyncQueued = true;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        finalOwnershipSyncQueued = false;
        installManagementNavigation();
        installProfileItems();
        removeNestedManagementTabs();
        embedAccountApiTokens();
        embedBackupDataTools();
        syncPageOwnership(state.currentView);
      });
    });
  }

  function syncAccessShell() {
    installManagementNavigation();
    installProfileItems();
    removeNestedManagementTabs();
    embedAccountApiTokens();
    embedBackupDataTools();
    syncPageOwnership();
    scheduleFinalOwnershipSync();
  }

  const previousShowApp = showApp;
  showApp = function showAppWithAccessShell(session) {
    const result = previousShowApp(session);
    syncAccessShell();
    return result;
  };

  const previousNavigate = navigate;
  navigate = function accessShellNavigate(view, historyMode = "push") {
    if (view === "sources") view = "destinations";
    if (view === "routes") view = "destinations";
    if (view === "inputs") view = "dashboard";
    if (view === "tokens") view = "account";
    if (view === "data") view = "backups";
    if (!isAdmin() && ADMIN_ONLY_VIEWS.has(view)) view = "dashboard";
    const result = previousNavigate(view, historyMode);
    syncPageOwnership(view);
    scheduleFinalOwnershipSync();
    return result;
  };

  if (state.currentView === "sources") navigate("destinations", "replace");
  if (state.currentView === "routes") navigate("destinations", "replace");
  if (state.currentView === "inputs") navigate("dashboard", "replace");
  if (state.currentView === "tokens") navigate("account", "replace");
  if (state.currentView === "data") navigate("backups", "replace");

  const baseRenderDestinations = renderDestinations;
  renderDestinations = function renderDestinationsWithPermissions() {
    baseRenderDestinations();
    if (isAdmin()) return;
    const cards = [...document.querySelectorAll("#destination-list > .resource-card")];
    (state.destinations || []).forEach((item, index) => {
      const card = cards[index];
      if (!card) return;
      const actions = card.querySelector(".resource-actions");
      const meta = card.querySelector(".resource-meta");
      const statusButtons = [...card.querySelectorAll(".status-button")];
      const canEdit = item.can_edit_destination === true;
      if (statusButtons[0]) statusButtons[0].disabled = !canEdit;
      if (statusButtons[1]) statusButtons[1].disabled = true;
      if (canEdit && actions) {
        if (!actions.querySelector('[data-action="test-destination-card"]')) {
          actions.append(actionButton("Send test", "test-destination-card", item.id, "primary"));
        }
        if (!actions.querySelector('[data-action="edit-destination"]')) {
          actions.append(actionButton("Edit", "edit-destination", item.id));
        }
        if (item.owned === true && !actions.querySelector('[data-action="delete-destination"]')) {
          actions.append(actionButton("Delete", "delete-destination", item.id, "danger"));
        }
      } else if (item.shared && meta && !meta.querySelector(".destination-read-only")) {
        const readOnly = badge("Read only", "warning");
        readOnly.classList.add("destination-read-only");
        meta.append(readOnly);
      }
    });
  };

  const baseRenderUsers = renderUsers;
  renderUsers = function renderUsersWithDestinationAccess() {
    baseRenderUsers();
    if (!isAdmin()) return;
    const rows = [...document.querySelectorAll("#user-table tr")];
    (state.users || []).forEach((item, index) => {
      const row = rows[index];
      if (!row) return;
      const identity = row.querySelector(".user-cell > div:last-child");
      if (identity && item.role === "user" && !identity.querySelector(".private-resource-count")) {
        const count = document.createElement("small");
        count.className = "private-resource-count";
        count.textContent = `${Number(item.private_destination_count || 0)} private destination${Number(item.private_destination_count || 0) === 1 ? "" : "s"}`;
        identity.append(count);
      }
      if (item.role !== "user") return;
      const actions = row.querySelector(".row-actions");
      if (!actions || actions.querySelector('[data-action="destination-access"]')) return;
      const access = actionButton("Destination access", "destination-access", item.id);
      actions.prepend(access);
    });
  };

  function installPermissionDialog() {
    if (document.getElementById("destination-access-dialog")) return;
    const dialog = document.createElement("dialog");
    dialog.id = "destination-access-dialog";
    dialog.className = "modal";

    const heading = document.createElement("div");
    heading.className = "modal-heading";
    const copy = document.createElement("div");
    const eyebrow = document.createElement("p");
    eyebrow.className = "eyebrow";
    eyebrow.textContent = "Shared destination permissions";
    const title = document.createElement("h2");
    title.id = "destination-access-title";
    title.textContent = "Destination access";
    copy.append(eyebrow, title);
    const closeTop = makeButton("×", "icon-button");
    closeTop.setAttribute("aria-label", "Close");
    closeTop.addEventListener("click", () => dialog.close());
    heading.append(copy, closeTop);

    const privacy = document.createElement("p");
    privacy.id = "destination-access-private-summary";
    privacy.className = "field-help";

    const panel = document.createElement("div");
    panel.className = "table-panel";
    const scroll = document.createElement("div");
    scroll.className = "table-scroll";
    const table = document.createElement("table");
    table.innerHTML = "<thead><tr><th>Shared destination</th><th>Edit destination</th><th>Manage filtering</th></tr></thead><tbody id=\"destination-access-table\"></tbody>";
    scroll.append(table);
    panel.append(scroll);

    const emptyState = document.createElement("div");
    emptyState.id = "destination-access-empty";
    emptyState.className = "empty-state";
    emptyState.hidden = true;

    const actions = document.createElement("div");
    actions.className = "modal-actions";
    const close = makeButton("Close", "button secondary");
    close.addEventListener("click", () => dialog.close());
    actions.append(close);

    dialog.append(heading, privacy, panel, emptyState, actions);
    document.body.append(dialog);
  }

  async function openDestinationAccess(userId) {
    if (!isAdmin()) return;
    installPermissionDialog();
    permissionDialogUserId = userId;
    try {
      const payload = await request(`/users/${userId}/destination-permissions`);
      const dialog = document.getElementById("destination-access-dialog");
      const user = payload.user || {};
      document.getElementById("destination-access-title").textContent = `Destination access — ${user.username || "User"}`;
      const count = Number(user.private_destination_count || 0);
      document.getElementById("destination-access-private-summary").textContent = `${count} private destination${count === 1 ? "" : "s"} owned by this user. Private names, configuration, credentials, routing, filters and delivery contents are hidden from administrators.`;
      const body = document.getElementById("destination-access-table");
      const emptyState = document.getElementById("destination-access-empty");
      body.replaceChildren();
      const destinations = Array.isArray(payload.destinations) ? payload.destinations : [];
      emptyState.hidden = destinations.length > 0;
      if (!destinations.length) {
        emptyState.replaceChildren(
          Object.assign(document.createElement("strong"), { textContent: "No shared destinations" }),
          Object.assign(document.createElement("span"), { textContent: "Create or share an administrator destination before granting delegated access." }),
        );
      }
      for (const item of destinations) {
        const row = document.createElement("tr");
        const name = document.createElement("td");
        const strong = document.createElement("strong");
        strong.textContent = item.name;
        const small = document.createElement("small");
        small.textContent = friendlyName(item.output_type);
        name.append(strong, small);
        const editCell = document.createElement("td");
        const filterCell = document.createElement("td");
        const edit = document.createElement("input");
        edit.type = "checkbox";
        edit.checked = item.can_edit_destination === true;
        edit.setAttribute("aria-label", `Allow destination editing for ${item.name}`);
        const filtering = document.createElement("input");
        filtering.type = "checkbox";
        filtering.checked = item.can_manage_filters === true;
        filtering.setAttribute("aria-label", `Allow filtering management for ${item.name}`);
        const save = async () => {
          edit.disabled = true;
          filtering.disabled = true;
          try {
            await request(`/users/${permissionDialogUserId}/destination-permissions`, {
              method: "PUT",
              body: {
                destination_id: item.destination_id,
                can_edit_destination: edit.checked,
                can_manage_filters: filtering.checked,
              },
            });
            toast(`Access updated for ${item.name}.`);
          } catch (error) {
            toast(error.message || "Destination access could not be updated.", "error");
            await openDestinationAccess(permissionDialogUserId);
          } finally {
            edit.disabled = false;
            filtering.disabled = false;
          }
        };
        edit.addEventListener("change", save);
        filtering.addEventListener("change", save);
        editCell.append(edit);
        filterCell.append(filtering);
        row.append(name, editCell, filterCell);
        body.append(row);
      }
      if (!dialog.open) dialog.showModal();
    } catch (error) {
      toast(error.message || "Destination access could not be loaded.", "error");
    }
  }

  document.addEventListener("click", (event) => {
    const accessAction = event.target.closest('[data-action="destination-access"]');
    if (!accessAction) return;
    event.preventDefault();
    openDestinationAccess(accessAction.dataset.id);
  }, true);

  const baseRenderAll = renderAll;
  renderAll = function renderAllWithAccessShell() {
    const result = baseRenderAll();
    syncAccessShell();
    return result;
  };

  document.addEventListener("DOMContentLoaded", () => {
    syncAccessShell();
    installPermissionDialog();
  });
})();