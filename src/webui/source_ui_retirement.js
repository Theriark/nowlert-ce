"use strict";

(() => {
  delete VIEW_TITLES.sources;

  const ADMIN_CHILD_VIEWS = new Set(["users", "updates", "data"]);
  const ADMIN_ONLY_VIEWS = new Set([
    "users",
    "updates",
    "data",
    "audit",
    "backups",
    "settings",
    "inputs",
  ]);
  let filteringAccess = null;
  let filteringRefreshTimer = 0;
  let filteringRoleRestore = null;
  let permissionDialogUserId = "";

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

  function installAdministrationNavigation() {
    const sourcesNav = document.querySelector('#primary-nav [data-view="sources"]');
    if (sourcesNav) sourcesNav.remove();

    const tokensNav = primaryNav("tokens");
    if (tokensNav) tokensNav.remove();

    for (const id of ["users-nav", "settings-nav", "updates-nav", "inputs-nav", "data-nav"]) {
      const item = document.getElementById(id);
      if (item) item.hidden = true;
    }

    let adminNav = document.getElementById("administration-nav");
    if (!adminNav) {
      adminNav = document.createElement("button");
      adminNav.id = "administration-nav";
      adminNav.type = "button";
      adminNav.className = "nav-item";
      adminNav.dataset.view = "users";
      const icon = document.createElement("span");
      icon.className = "nav-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "⚙";
      const label = document.createElement("span");
      label.textContent = "Administration";
      adminNav.append(icon, label);
      const audit = primaryNav("audit");
      const backups = primaryNav("backups");
      if (audit) audit.after(adminNav);
      else if (backups) backups.before(adminNav);
      else document.getElementById("primary-nav")?.append(adminNav);
    }
  }

  function installProfileItems() {
    document.querySelector("#profile-menu-button .profile-chevron")?.remove();
    const popover = document.getElementById("profile-menu-popover");
    if (!popover) return;

    if (!document.getElementById("profile-api-access")) {
      const apiAccess = makeButton("API access", "profile-menu-item");
      apiAccess.id = "profile-api-access";
      apiAccess.dataset.view = "tokens";
      popover.prepend(apiAccess);
    }
    if (!document.getElementById("profile-settings")) {
      const settings = makeButton("Settings", "profile-menu-item");
      settings.id = "profile-settings";
      settings.dataset.view = "settings";
      const security = popover.querySelector('[data-view="account"]');
      if (security) security.before(settings);
      else popover.prepend(settings);
    }
  }

  function installAdministrationTabs() {
    const labels = {
      users: "Users",
      updates: "Updates",
      data: "Data tools",
    };
    for (const view of ADMIN_CHILD_VIEWS) {
      const section = document.getElementById(`view-${view}`);
      if (!section || section.querySelector(".administration-tabs")) continue;
      const tabs = document.createElement("div");
      tabs.className = "row-actions administration-tabs";
      tabs.setAttribute("aria-label", "Administration sections");
      for (const target of ADMIN_CHILD_VIEWS) {
        const button = makeButton(labels[target], "button secondary small");
        button.dataset.view = target;
        button.dataset.administrationTab = target;
        tabs.append(button);
      }
      section.prepend(tabs);
    }
  }

  function syncAdministrationState(view = state.currentView) {
    const admin = Boolean(isAdmin());
    const adminNav = document.getElementById("administration-nav");
    const auditNav = primaryNav("audit");
    const backupsNav = document.getElementById("backups-nav") || primaryNav("backups");
    if (adminNav) adminNav.hidden = !admin;
    if (auditNav) auditNav.hidden = !admin;
    if (backupsNav) backupsNav.hidden = !admin;

    for (const id of ["users-nav", "settings-nav", "updates-nav", "inputs-nav", "data-nav"]) {
      const item = document.getElementById(id);
      if (item) item.hidden = true;
    }

    const settings = document.getElementById("profile-settings");
    if (settings) settings.hidden = !admin;

    const addDestination = document.getElementById("add-destination-button");
    if (addDestination && state.user) addDestination.hidden = false;
    const addRoute = document.getElementById("add-route-button");
    if (addRoute) addRoute.hidden = true;

    if (adminNav) {
      const active = ADMIN_CHILD_VIEWS.has(view);
      adminNav.classList.toggle("active", active);
      if (active) adminNav.setAttribute("aria-current", "page");
      else adminNav.removeAttribute("aria-current");
    }
    for (const button of document.querySelectorAll("[data-administration-tab]")) {
      const active = button.dataset.administrationTab === view;
      button.classList.toggle("primary", active);
      button.classList.toggle("secondary", !active);
    }
    if (ADMIN_CHILD_VIEWS.has(view)) {
      const title = document.getElementById("page-title");
      if (title) title.textContent = "Administration";
    }
  }

  function syncAccessShell() {
    installAdministrationNavigation();
    installProfileItems();
    installAdministrationTabs();
    syncAdministrationState();
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
    if (!isAdmin() && ADMIN_ONLY_VIEWS.has(view)) view = "dashboard";
    const result = previousNavigate(view, historyMode);
    syncAdministrationState(view);
    if (view === "filtering") queueFilteringDecoration();
    return result;
  };

  if (state.currentView === "sources") navigate("destinations", "replace");
  if (state.currentView === "routes") navigate("destinations", "replace");
  if (state.currentView === "inputs") navigate("dashboard", "replace");

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

  function restoreFilteringRole() {
    if (!filteringRoleRestore) return;
    state.user.role = filteringRoleRestore;
    filteringRoleRestore = null;
    syncAccessShell();
  }

  function elevateFilteringUntilDialogCloses() {
    if (!state.user || state.user.role === "admin") return;
    if (!filteringRoleRestore) filteringRoleRestore = state.user.role;
    state.user.role = "admin";
    const dialog = document.getElementById("filtering-dialog");
    if (dialog && dialog.dataset.accessRoleRestoreBound !== "true") {
      dialog.dataset.accessRoleRestoreBound = "true";
      dialog.addEventListener("close", restoreFilteringRole);
    }
    window.setTimeout(() => {
      const current = document.getElementById("filtering-dialog");
      if (filteringRoleRestore && (!current || !current.open)) restoreFilteringRole();
    }, 2500);
  }

  async function decorateFiltering() {
    if (!state.user || state.user.role === "admin" || filteringRoleRestore) return;
    try {
      filteringAccess = await request("/filters");
    } catch (_error) {
      return;
    }
    const policies = (Array.isArray(filteringAccess.filters) ? filteringAccess.filters : [])
      .filter((policy) => Array.isArray(policy.integrations) && policy.integrations.length > 0);
    const rows = [...document.querySelectorAll("#filter-table tr")];
    policies.forEach((policy, index) => {
      const row = rows[index];
      if (!row) return;
      const destinationCell = row.children[0];
      const actions = row.children[3];
      if (destinationCell && !destinationCell.querySelector(".filtering-access-badge")) {
        const accessBadge = badge(policy.shared ? "👥 Shared" : "🔒 Private", policy.shared ? "success" : "warning");
        accessBadge.classList.add("filtering-access-badge");
        destinationCell.append(accessBadge);
      }
      if (!actions) return;
      actions.replaceChildren();
      const button = makeButton(
        policy.can_manage_filters ? "✎ Configure" : "View",
        `button small ${policy.can_manage_filters ? "primary" : "secondary"}`,
      );
      button.dataset.filterAction = "manage-destination";
      button.dataset.filterId = policy.destination_id;
      button.dataset.accessCanManage = policy.can_manage_filters ? "true" : "false";
      actions.append(button);
      if (policy.can_manage_filters) {
        const remove = makeButton("Delete", "button small danger");
        remove.dataset.filterAction = "delete-destination-filter";
        remove.dataset.filterId = policy.destination_id;
        remove.dataset.accessCanManage = "true";
        actions.append(remove);
      } else {
        actions.append(badge("Read only", "warning"));
      }
    });
    const add = document.getElementById("add-filter-button");
    if (add) {
      add.hidden = !(Array.isArray(filteringAccess.destinations) && filteringAccess.destinations.length);
      add.dataset.accessCanManage = add.hidden ? "false" : "true";
    }
  }

  function queueFilteringDecoration() {
    window.clearTimeout(filteringRefreshTimer);
    filteringRefreshTimer = window.setTimeout(decorateFiltering, 80);
  }

  document.addEventListener("click", (event) => {
    const accessAction = event.target.closest('[data-action="destination-access"]');
    if (accessAction) {
      event.preventDefault();
      openDestinationAccess(accessAction.dataset.id);
      return;
    }

    if (!state.user || state.user.role === "admin") return;
    const filterAction = event.target.closest("[data-filter-action]");
    if (!filterAction) return;
    const action = filterAction.dataset.filterAction;
    if (action === "new-filter" && filterAction.dataset.accessCanManage === "true") {
      elevateFilteringUntilDialogCloses();
      return;
    }
    if (
      ["manage-destination", "delete-destination-filter"].includes(action)
      && filterAction.dataset.accessCanManage === "true"
    ) {
      elevateFilteringUntilDialogCloses();
    }
  }, true);

  const baseRenderAll = renderAll;
  renderAll = function renderAllWithAccessShell() {
    const result = baseRenderAll();
    syncAccessShell();
    queueFilteringDecoration();
    return result;
  };

  document.addEventListener("DOMContentLoaded", () => {
    syncAccessShell();
    installPermissionDialog();
    const filterTable = document.getElementById("filter-table");
    if (filterTable) {
      new MutationObserver(queueFilteringDecoration).observe(filterTable, {
        childList: true,
        subtree: true,
      });
    }
    queueFilteringDecoration();
  });
})();
