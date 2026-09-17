"use strict";

(() => {
  delete VIEW_TITLES.sources;

  const SECTION_GROUPS = {
    account: {
      title: "Account security",
      subtitle: "Manage your profile picture, password, API access, and active account security settings.",
      tabs: [["account", "Security"], ["tokens", "API access"]],
    },
    settings: {
      title: "Settings",
      subtitle: "Configure regional preferences, integration-specific behavior, and updates.",
      tabs: [["settings", "Settings"], ["updates", "Updates"]],
    },
    backups: {
      title: "Backups",
      subtitle: "Configure backup destinations, schedules, snapshots, restore operations, and portable configuration.",
      tabs: [["backups", "Backups"], ["data", "Data tools"]],
    },
  };
  const SECTION_GROUP_BY_VIEW = new Map();
  for (const [groupKey, group] of Object.entries(SECTION_GROUPS)) {
    for (const [view] of group.tabs) SECTION_GROUP_BY_VIEW.set(view, groupKey);
  }
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
  let usersActionHome = null;

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
    primaryNav("sources")?.remove();
    primaryNav("tokens")?.remove();
    document.getElementById("administration-nav")?.remove();

    for (const id of ["settings-nav", "updates-nav", "inputs-nav", "data-nav"]) {
      const item = document.getElementById(id);
      if (item) item.hidden = true;
    }

    const backupsNav = document.getElementById("backups-nav") || primaryNav("backups");
    const usersNav = document.getElementById("users-nav") || primaryNav("users");
    if (backupsNav && usersNav && backupsNav.nextElementSibling !== usersNav) {
      backupsNav.after(usersNav);
    }
  }

  function installProfileItems() {
    document.querySelector("#profile-menu-button .profile-chevron")?.remove();
    document.getElementById("profile-api-access")?.remove();
    const popover = document.getElementById("profile-menu-popover");
    if (!popover) return;

    if (!document.getElementById("profile-settings")) {
      const settings = makeButton("Settings", "profile-menu-item");
      settings.id = "profile-settings";
      settings.dataset.view = "settings";
      const security = popover.querySelector('[data-view="account"]');
      if (security) security.before(settings);
      else popover.prepend(settings);
    }
  }

  function installSectionTabs() {
    document.querySelectorAll(".administration-tabs:not([data-section-group])")
      .forEach((tabs) => tabs.remove());

    for (const [groupKey, group] of Object.entries(SECTION_GROUPS)) {
      for (const [view] of group.tabs) {
        const section = document.getElementById(`view-${view}`);
        if (!section) continue;
        let tabs = section.querySelector(`:scope > .administration-tabs[data-section-group="${groupKey}"]`);
        if (!tabs) {
          tabs = document.createElement("div");
          tabs.className = "row-actions administration-tabs";
          tabs.dataset.sectionGroup = groupKey;
          tabs.setAttribute("aria-label", `${group.title} sections`);
          for (const [target, label] of group.tabs) {
            const button = makeButton(label, "button secondary small");
            button.dataset.view = target;
            button.dataset.sectionTab = target;
            tabs.append(button);
          }
          section.prepend(tabs);
        }
      }
    }
  }

  function rememberUsersAction() {
    const action = document.querySelector('#view-users [data-action="new-user"]');
    if (!action || usersActionHome?.node === action) return action;
    usersActionHome = {
      node: action,
      parent: action.parentElement,
      next: action.nextSibling,
    };
    return action;
  }

  function restoreUsersAction() {
    const home = usersActionHome;
    if (!home?.node || !home.parent) return;
    const reference = home.next && home.next.parentElement === home.parent ? home.next : null;
    home.parent.insertBefore(home.node, reference);
  }

  function syncUsersAction(view) {
    const action = rememberUsersAction();
    if (!action) return;
    if (view === "users") {
      const actions = document.querySelector(".topbar-actions");
      if (actions && action.parentElement !== actions) actions.append(action);
    } else if (usersActionHome?.node?.parentElement !== usersActionHome?.parent) {
      restoreUsersAction();
    }
  }

  function syncPageOwnership(view = state.currentView) {
    const admin = Boolean(isAdmin());
    const groupKey = SECTION_GROUP_BY_VIEW.get(view) || "";
    const group = groupKey ? SECTION_GROUPS[groupKey] : null;
    const auditNav = primaryNav("audit");
    const backupsNav = document.getElementById("backups-nav") || primaryNav("backups");
    const usersNav = document.getElementById("users-nav") || primaryNav("users");

    document.getElementById("administration-nav")?.remove();
    document.getElementById("profile-api-access")?.remove();
    if (auditNav) auditNav.hidden = !admin;
    if (backupsNav) backupsNav.hidden = !admin;
    if (usersNav) usersNav.hidden = !admin;

    for (const id of ["settings-nav", "updates-nav", "inputs-nav", "data-nav"]) {
      const item = document.getElementById(id);
      if (item) item.hidden = true;
    }

    if (backupsNav && usersNav && backupsNav.nextElementSibling !== usersNav) {
      backupsNav.after(usersNav);
    }

    const settings = document.getElementById("profile-settings");
    if (settings) settings.hidden = !admin;

    const addDestination = document.getElementById("add-destination-button");
    if (addDestination && state.user) addDestination.hidden = false;
    const addRoute = document.getElementById("add-route-button");
    if (addRoute) addRoute.hidden = true;

    setNavActive(backupsNav, groupKey === "backups");
    setNavActive(usersNav, view === "users");

    for (const button of document.querySelectorAll("[data-section-tab]")) {
      const active = button.dataset.sectionTab === view;
      button.classList.toggle("primary", active);
      button.classList.toggle("secondary", !active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    }

    const title = document.getElementById("page-title");
    const subtitle = document.getElementById("page-subtitle");
    const section = document.getElementById(`view-${view}`);
    const toolbar = section?.querySelector(":scope > .section-toolbar");

    if (group) {
      if (title) title.textContent = group.title;
      if (subtitle) {
        subtitle.textContent = group.subtitle;
        subtitle.hidden = false;
      }
      if (toolbar) {
        const childView = view !== groupKey;
        toolbar.hidden = !childView;
        if (childView) toolbar.removeAttribute("aria-hidden");
        else toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("page-data-toolbar", "administration-section-header");
        const copy = toolbar.querySelector(":scope > div");
        if (copy) copy.hidden = false;
      }
    } else if (view === "users") {
      if (title) title.textContent = "Users";
      if (subtitle) {
        subtitle.textContent = "Manage local accounts, roles, access state, and password resets.";
        subtitle.hidden = false;
      }
      if (toolbar) {
        toolbar.hidden = true;
        toolbar.setAttribute("aria-hidden", "true");
        toolbar.classList.remove("administration-section-header");
      }
    }

    syncUsersAction(view);
  }

  function scheduleFinalOwnershipSync() {
    if (finalOwnershipSyncQueued) return;
    finalOwnershipSyncQueued = true;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        finalOwnershipSyncQueued = false;
        installManagementNavigation();
        installProfileItems();
        installSectionTabs();
        syncPageOwnership(state.currentView);
      });
    });
  }

  function syncAccessShell() {
    installManagementNavigation();
    installProfileItems();
    installSectionTabs();
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
    if (!isAdmin() && ADMIN_ONLY_VIEWS.has(view)) view = "dashboard";
    const result = previousNavigate(view, historyMode);
    syncPageOwnership(view);
    scheduleFinalOwnershipSync();
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
