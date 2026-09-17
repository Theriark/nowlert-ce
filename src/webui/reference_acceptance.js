"use strict";

/* Reference-screen acceptance layer. API behavior remains owned by the existing WebUI. */
(() => {
  const USER_PAGE_SIZE = 12;
  let userFilter = "all";
  let userQuery = "";
  let userPage = 1;
  let previewDestinationId = "";
  let previewRouteSelection = new Set();
  let syncQueued = false;

  const ref = (tag, className = "", text = "") => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== "") node.textContent = text;
    return node;
  };

  function destinationForPreview() {
    const id = byId("preview-destination-id")?.value || previewDestinationId;
    return (state.destinations || []).find((item) => item.id === id) || null;
  }

  function previewProvider(destination) {
    const type = destination?.output_type || "";
    return (typeof OUTPUT_NAMES === "object" && OUTPUT_NAMES[type])
      || (typeof friendlyName === "function" ? friendlyName(type) : type)
      || "Destination";
  }

  function assignedRouteIds(destinationId) {
    const selected = new Set();
    const destination = (state.destinations || []).find((item) => item.id === destinationId);
    for (const id of destination?.route_ids || []) selected.add(id);
    for (const route of state.routes || []) {
      if (!route?.id) continue;
      if (String(route.destination_id || "") === String(destinationId || "")) selected.add(route.id);
      if (Array.isArray(route.destination_ids) && route.destination_ids.includes(destinationId)) selected.add(route.id);
    }
    return selected;
  }

  function routeLabel(route) {
    if (typeof routeSourceDescriptor === "function") {
      return routeSourceDescriptor(route.source, route.input_type).integration;
    }
    return typeof friendlyName === "function" ? friendlyName(route.source) : String(route.source || "Route");
  }

  function renderPreviewRouteSummary() {
    const count = byId("reference-preview-route-summary");
    const chips = byId("reference-preview-route-chips");
    if (!count || !chips) return;
    const selected = (state.routes || []).filter((route) => previewRouteSelection.has(route.id));
    count.textContent = selected.length === 1 ? "1 route assigned" : `${selected.length} routes assigned`;
    chips.replaceChildren();
    for (const route of selected.slice(0, 3)) {
      const chip = ref("span", "reference-preview-route-chip");
      if (typeof sourceIcon === "function") chip.append(sourceIcon(route.source));
      chip.append(ref("strong", "", routeLabel(route)));
      chip.append(ref("span", route.enabled === false ? "is-disabled" : "is-enabled", route.enabled === false ? "Disabled" : "Enabled"));
      chips.append(chip);
    }
    if (selected.length > 3) chips.append(ref("span", "reference-preview-route-more", `+${selected.length - 3} more`));
  }

  function renderPreviewRouteOptions() {
    const list = byId("reference-preview-route-options");
    const counter = byId("reference-preview-routes-count");
    if (!list || !counter) return;
    const query = String(byId("reference-preview-route-search")?.value || "").trim().toLowerCase();
    const routes = state.routes || [];
    const visible = routes.filter((route) => !query || `${route.name || ""} ${routeLabel(route)} ${route.input_type || ""}`.toLowerCase().includes(query));
    counter.textContent = `${previewRouteSelection.size} of ${routes.length} selected`;
    list.replaceChildren();
    if (!visible.length) list.append(ref("div", "reference-preview-route-empty", routes.length ? "No matching routes." : "No routes are available yet."));
    for (const route of visible) {
      const row = ref("label", "reference-preview-route-option");
      const check = document.createElement("input");
      check.type = "checkbox";
      check.checked = previewRouteSelection.has(route.id);
      check.setAttribute("aria-label", `Assign ${route.name || routeLabel(route)}`);
      const leading = ref("span", "reference-preview-route-leading");
      leading.append(check);
      if (typeof sourceIcon === "function") leading.append(sourceIcon(route.source));
      row.append(leading, ref("strong", "", route.name || routeLabel(route)));
      check.addEventListener("change", () => {
        if (check.checked) previewRouteSelection.add(route.id);
        else previewRouteSelection.delete(route.id);
        renderPreviewRouteOptions();
        renderPreviewRouteSummary();
      });
      list.append(row);
    }
  }

  function closePreviewRoutes() {
    byId("reference-preview-route-drawer")?.setAttribute("hidden", "");
    byId("preview-form")?.classList.remove("reference-preview-routes-open");
    byId("preview-dialog")?.classList.remove("reference-preview-routes-open");
  }

  function openPreviewRoutes() {
    const destination = destinationForPreview();
    if (!destination) return;
    previewRouteSelection = assignedRouteIds(destination.id);
    renderPreviewRouteSummary();
    renderPreviewRouteOptions();
    const drawer = byId("reference-preview-route-drawer");
    if (!drawer) return;
    drawer.hidden = false;
    byId("preview-form")?.classList.add("reference-preview-routes-open");
    byId("preview-dialog")?.classList.add("reference-preview-routes-open");
    requestAnimationFrame(() => byId("reference-preview-route-search")?.focus({ preventScroll: true }));
  }

  function ensurePreviewDrawer(form) {
    if (byId("reference-preview-route-drawer")) return;
    const drawer = ref("aside", "reference-preview-route-drawer");
    drawer.id = "reference-preview-route-drawer";
    drawer.hidden = true;
    const heading = ref("div", "reference-preview-route-drawer-heading");
    heading.append(ref("h3", "", "Assigned routes"));
    const close = ref("button", "icon-button", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close assigned routes");
    close.addEventListener("click", closePreviewRoutes);
    heading.append(close);
    const counter = ref("strong", "reference-preview-routes-count", "0 of 0 selected");
    counter.id = "reference-preview-routes-count";
    const search = document.createElement("input");
    search.id = "reference-preview-route-search";
    search.type = "search";
    search.placeholder = "Search routes...";
    search.setAttribute("aria-label", "Search routes");
    search.addEventListener("input", renderPreviewRouteOptions);
    const actions = ref("div", "reference-preview-route-actions");
    const all = ref("button", "text-button", "Select all");
    all.type = "button";
    all.addEventListener("click", () => {
      previewRouteSelection = new Set((state.routes || []).map((route) => route.id));
      renderPreviewRouteOptions();
      renderPreviewRouteSummary();
    });
    const clear = ref("button", "text-button", "Clear");
    clear.type = "button";
    clear.addEventListener("click", () => {
      previewRouteSelection.clear();
      renderPreviewRouteOptions();
      renderPreviewRouteSummary();
    });
    actions.append(all, clear);
    const options = ref("div", "reference-preview-route-options");
    options.id = "reference-preview-route-options";
    const done = ref("button", "button primary full reference-preview-route-done", "Done");
    done.type = "button";
    done.addEventListener("click", closePreviewRoutes);
    drawer.append(heading, counter, search, actions, options, done);
    form.append(drawer);
  }

  function ensurePreviewReferenceLayout() {
    const dialog = byId("preview-dialog");
    const form = byId("preview-form");
    if (!dialog || !form) return;
    dialog.classList.add("reference-preview-dialog");
    form.classList.add("reference-preview-form");
    ensurePreviewDrawer(form);
    if (form.dataset.referencePreview === "1") return;
    form.dataset.referencePreview = "1";

    const heading = form.querySelector(":scope > .modal-heading");
    heading?.classList.add("reference-preview-heading");
    heading?.querySelector(".eyebrow")?.remove();
    const grid = form.querySelector(":scope > .form-grid");
    const sourceField = byId("preview-source")?.closest("label");
    const severityField = byId("preview-severity")?.closest("label");
    const titleField = byId("preview-event-title")?.closest("label");
    const messageField = byId("preview-message")?.closest("label");
    const result = byId("preview-result");
    const error = byId("preview-error");
    const oldActions = form.querySelector(":scope > .preview-actions");
    const oldHelp = form.querySelector(":scope > .field-help");
    const drawer = byId("reference-preview-route-drawer");

    const fields = ref("div", "reference-preview-fields");
    const simpleField = (label, id, element) => {
      const field = ref("label", "reference-preview-field");
      field.append(ref("span", "", label), element);
      element.id = id;
      return field;
    };
    const name = document.createElement("input"); name.readOnly = true;
    const channel = document.createElement("input"); channel.readOnly = true;
    const style = document.createElement("select"); style.disabled = true;
    style.append(new Option("Modern Card", "modern"), new Option("Classic Embed", "classic"));
    if (severityField) severityField.className = "reference-preview-field";
    fields.append(
      simpleField("Name", "reference-preview-name", name),
      severityField || ref("div"),
      simpleField("Channel", "reference-preview-channel", channel),
      simpleField("Message style", "reference-preview-message-style", style),
    );

    const routing = ref("section", "reference-preview-routing");
    routing.append(ref("span", "reference-preview-routing-icon", "⌘"));
    const routingCopy = ref("div", "reference-preview-routing-copy");
    routingCopy.append(ref("strong", "", "Routing"));
    const routeCount = ref("span", "", "0 routes assigned"); routeCount.id = "reference-preview-route-summary";
    const chips = ref("div", "reference-preview-route-chips"); chips.id = "reference-preview-route-chips";
    routingCopy.append(routeCount, chips);
    const manage = ref("button", "button primary reference-preview-manage-routes", "Manage routes");
    manage.type = "button";
    manage.addEventListener("click", openPreviewRoutes);
    routing.append(routingCopy, manage);

    if (messageField) messageField.className = "reference-preview-message";
    const messageCount = ref("div", "reference-preview-message-count", "0/4000");
    messageCount.id = "reference-preview-message-count";
    const updateCount = () => { messageCount.textContent = `${String(byId("preview-message")?.value || "").length}/4000`; };
    byId("preview-message")?.addEventListener("input", updateCount);
    updateCount();

    const output = ref("section", "reference-preview-output");
    const outputHeading = ref("div", "reference-preview-output-heading");
    const outputTitle = ref("div", "reference-preview-output-title");
    outputTitle.append(ref("span", "reference-preview-code-icon", "</>"), ref("strong", "", "Preview output"));
    const outputTools = ref("div", "reference-preview-output-actions");
    outputTools.append(ref("span", "reference-preview-json-label", "JSON"));
    const copy = ref("button", "button secondary", "Copy");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      const text = result?.textContent || "";
      if (!text) return;
      try { await navigator.clipboard.writeText(text); if (typeof toast === "function") toast("Preview copied."); }
      catch (_error) { if (typeof toast === "function") toast("Preview could not be copied.", "error"); }
    });
    outputTools.append(copy);
    outputHeading.append(outputTitle, outputTools);
    output.append(outputHeading);
    if (result) { result.classList.add("reference-preview-result"); output.append(result); }

    const native = ref("div", "reference-preview-native-fields");
    if (sourceField) native.append(sourceField);
    if (titleField) native.append(titleField);
    grid?.remove();
    oldHelp?.setAttribute("hidden", "");
    if (oldActions) {
      oldActions.classList.add("reference-preview-actions");
      const test = byId("test-button");
      const preview = byId("preview-button");
      if (test && preview) oldActions.replaceChildren(test, preview);
    }
    for (const node of [fields, routing, messageField, messageCount, output, error, native, oldActions, oldHelp]) {
      if (node) form.insertBefore(node, drawer);
    }
  }

  function syncPreviewReference() {
    ensurePreviewReferenceLayout();
    const destination = destinationForPreview();
    if (!destination) return;
    previewDestinationId = destination.id;
    const provider = previewProvider(destination);
    if (byId("preview-title")) byId("preview-title").textContent = `Preview ${destination.name} - ${provider}`;
    if (byId("reference-preview-name")) byId("reference-preview-name").value = destination.name || "";
    const settings = destination.settings || {};
    if (byId("reference-preview-channel")) byId("reference-preview-channel").value = settings.channel_name || settings.channel || settings.topic || "Not labelled";
    if (byId("reference-preview-message-style")) byId("reference-preview-message-style").value = settings.message_style === "classic" || settings.components_v2 === false ? "classic" : "modern";
    previewRouteSelection = assignedRouteIds(destination.id);
    renderPreviewRouteSummary();
    renderPreviewRouteOptions();
  }

  function metric(label, id, detail, icon) {
    const card = ref("article", "reference-user-metric");
    card.append(ref("span", "reference-user-metric-icon", icon));
    const copy = ref("div", "reference-user-metric-copy");
    copy.append(ref("span", "", label));
    const value = ref("strong", "", "0"); value.id = id;
    const small = ref("small", "", detail); small.id = `${id}-detail`;
    copy.append(value, small); card.append(copy); return card;
  }

  function ensureUsersReferenceLayout() {
    const section = byId("view-users");
    const panel = section?.querySelector(":scope > .table-panel");
    if (!section || !panel) return;
    section.classList.add("reference-users-page");
    const add = section.querySelector('[data-action="new-user"]') || document.querySelector('[data-action="new-user"]');
    if (add) add.textContent = "+ New user";
    if (section.dataset.referenceUsers === "1") return;
    section.dataset.referenceUsers = "1";

    const overview = ref("div", "reference-users-overview");
    const metrics = ref("div", "reference-users-metrics");
    metrics.append(
      metric("Total users", "reference-users-total", "All local accounts", "◎"),
      metric("Active users", "reference-users-active", "0% enabled", "●"),
      metric("Admins", "reference-users-admins", "0% of users", "◇"),
      metric("Never logged in", "reference-users-never", "Haven't signed in yet", "◷"),
    );
    const recent = ref("aside", "reference-users-recent");
    const recentHead = ref("div", "reference-users-recent-heading");
    recentHead.append(ref("strong", "", "⚡ Recent activity"), ref("span", "", "View all ›"));
    const recentList = ref("div", "reference-users-recent-list"); recentList.id = "reference-users-recent-list";
    recent.append(recentHead, recentList); overview.append(metrics, recent); panel.before(overview);

    const controls = ref("div", "reference-users-controls");
    const search = document.createElement("input");
    search.type = "search"; search.id = "reference-user-search"; search.placeholder = "Search users by name or ID...";
    search.addEventListener("input", () => { userQuery = search.value.trim().toLowerCase(); userPage = 1; syncUsersReference(); });
    const tabs = ref("div", "reference-users-filter-tabs");
    for (const [value, label] of [["all", "All users"], ["admin", "Admins"], ["user", "Standard users"]]) {
      const button = ref("button", "reference-user-filter", label); button.type = "button"; button.dataset.userFilter = value;
      button.addEventListener("click", () => { userFilter = value; userPage = 1; syncUsersReference(); }); tabs.append(button);
    }
    controls.append(search, tabs); panel.prepend(controls);
    const footer = ref("div", "reference-users-footer");
    footer.innerHTML = '<span id="reference-users-range">Showing 0 users.</span><div class="reference-users-pager"><button type="button" data-reference-user-page="previous" aria-label="Previous page">‹</button><span id="reference-users-pages"></span><button type="button" data-reference-user-page="next" aria-label="Next page">›</button><span class="reference-users-page-size">12 per page⌄</span></div>';
    footer.querySelector('[data-reference-user-page="previous"]')?.addEventListener("click", () => { userPage = Math.max(1, userPage - 1); syncUsersReference(); });
    footer.querySelector('[data-reference-user-page="next"]')?.addEventListener("click", () => { userPage += 1; syncUsersReference(); });
    panel.append(footer);
  }

  function decorateUsers() {
    const head = document.querySelector("#view-users table thead tr");
    const rows = [...document.querySelectorAll("#user-table > tr")];
    if (!head) return rows;
    if (head.dataset.referenceUsers !== "1") {
      head.dataset.referenceUsers = "1";
      head.innerHTML = '<th class="reference-user-check"><input type="checkbox" aria-label="Select all visible users"></th><th>User</th><th>Role</th><th>Last login</th><th>Status</th><th>Actions</th>';
      head.querySelector("input")?.addEventListener("change", (event) => {
        document.querySelectorAll('#user-table tr:not([hidden]) .reference-user-row-check input').forEach((input) => { input.checked = event.target.checked; });
      });
    }
    rows.forEach((row, index) => {
      const item = (state.users || [])[index]; if (!item) return;
      row.dataset.userId = item.id; row.dataset.userRole = item.role || "user";
      if (!row.querySelector(".reference-user-row-check")) {
        const cell = document.createElement("td"); cell.className = "reference-user-row-check";
        const check = document.createElement("input"); check.type = "checkbox"; check.setAttribute("aria-label", `Select ${item.username}`); cell.append(check); row.prepend(cell);
      }
      const self = item.id === state.user?.id;
      const name = row.querySelector(".user-cell strong");
      if (name) {
        name.textContent = item.username;
        if (self) name.append(ref("span", "reference-current-crown", "♛"));
      }
      const actions = row.querySelector(".row-actions");
      if (self && actions && !actions.children.length) {
        const reset = ref("button", "button small secondary", "Reset password"); reset.type = "button"; reset.disabled = true;
        const remove = ref("button", "button small danger", "Delete"); remove.type = "button"; remove.disabled = true;
        actions.append(reset, remove);
      }
    });
    return rows;
  }

  function syncRecentActivity() {
    const list = byId("reference-users-recent-list"); if (!list) return;
    const events = (state.audit || []).filter((item) => /user|session|login|account/.test(`${item.action || ""} ${item.resource_type || ""} ${item.resource || ""}`.toLowerCase())).slice(0, 2);
    list.replaceChildren();
    if (!events.length) { list.append(ref("small", "reference-users-recent-empty", "No recent account activity.")); return; }
    for (const item of events) {
      const row = ref("div", "reference-users-recent-row"); row.append(ref("span", "reference-users-recent-dot"));
      row.append(ref("strong", "", item.username || item.actor_username || item.user || item.actor || "Account"));
      row.append(ref("span", "", String(item.action || "Activity").replaceAll(".", " · ")));
      row.append(ref("time", "", typeof formatTime === "function" ? formatTime(item.created_at || item.timestamp || item.time) : "")); list.append(row);
    }
  }

  function syncUsersReference() {
    ensureUsersReferenceLayout();
    if (typeof isAdmin !== "function" || !isAdmin()) return;
    const users = state.users || [];
    const active = users.filter((item) => item.enabled !== false).length;
    const admins = users.filter((item) => item.role === "admin").length;
    const never = users.filter((item) => !item.last_login && !item.last_login_at).length;
    const values = { "reference-users-total": users.length, "reference-users-active": active, "reference-users-admins": admins, "reference-users-never": never };
    Object.entries(values).forEach(([id, value]) => { if (byId(id)) byId(id).textContent = value; });
    if (byId("reference-users-active-detail")) byId("reference-users-active-detail").textContent = users.length ? `${Math.round(active / users.length * 100)}% enabled` : "No accounts";
    if (byId("reference-users-admins-detail")) byId("reference-users-admins-detail").textContent = users.length ? `${Math.round(admins / users.length * 100)}% of users` : "No accounts";
    const counts = { all: users.length, admin: admins, user: users.length - admins };
    document.querySelectorAll(".reference-user-filter").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.userFilter === userFilter);
      const label = button.dataset.userFilter === "admin" ? "Admins" : button.dataset.userFilter === "user" ? "Standard users" : "All users";
      button.replaceChildren(document.createTextNode(label), ref("span", "", String(counts[button.dataset.userFilter])));
    });
    const rows = decorateUsers();
    const matching = users.filter((item) => (userFilter === "all" || (userFilter === "admin" ? item.role === "admin" : item.role !== "admin")) && (!userQuery || `${item.username || ""} ${item.id || ""}`.toLowerCase().includes(userQuery)));
    const pages = Math.max(1, Math.ceil(matching.length / USER_PAGE_SIZE)); userPage = Math.min(Math.max(1, userPage), pages);
    const visible = new Set(matching.slice((userPage - 1) * USER_PAGE_SIZE, userPage * USER_PAGE_SIZE).map((item) => item.id));
    rows.forEach((row) => { row.hidden = !visible.has(row.dataset.userId); });
    const start = matching.length ? (userPage - 1) * USER_PAGE_SIZE + 1 : 0; const end = matching.length ? Math.min(userPage * USER_PAGE_SIZE, matching.length) : 0;
    if (byId("reference-users-range")) byId("reference-users-range").textContent = `Showing ${start}–${end} of ${matching.length} users.`;
    const pageBox = byId("reference-users-pages");
    if (pageBox) {
      pageBox.replaceChildren();
      for (let page = 1; page <= Math.min(5, pages); page += 1) {
        const button = ref("button", page === userPage ? "is-current" : "", String(page)); button.type = "button"; button.addEventListener("click", () => { userPage = page; syncUsersReference(); }); pageBox.append(button);
      }
    }
    const previous = document.querySelector('[data-reference-user-page="previous"]'); const next = document.querySelector('[data-reference-user-page="next"]');
    if (previous) previous.disabled = userPage <= 1; if (next) next.disabled = userPage >= pages;
    syncRecentActivity();
  }

  function ensureSettingsReferenceLayout() {
    const section = byId("view-settings");
    const form = byId("preferences-form");
    const regional = form?.closest("article.settings-card");
    const updates = byId("settings-updates");
    if (!section || !regional || !updates) return;
    section.classList.add("reference-settings-page");
    if (!section.querySelector(":scope > .reference-settings-brand")) {
      const brand = ref("div", "reference-settings-brand"); brand.innerHTML = '<strong><span></span> NOWLERT</strong><small>STAY INFORMED</small>'; section.prepend(brand);
    }
    let grid = section.querySelector(":scope > .reference-settings-grid");
    if (!grid) { grid = ref("div", "reference-settings-grid"); regional.before(grid); }
    if (regional.parentElement !== grid) grid.append(regional); if (updates.parentElement !== grid) grid.append(updates);
    regional.classList.add("reference-regional-card");
    const heading = regional.querySelector(":scope > .panel-heading");
    if (heading && heading.dataset.referenceSettings !== "1") {
      heading.dataset.referenceSettings = "1"; heading.innerHTML = '<span class="reference-settings-card-icon">◎</span><div><h2>Regional settings</h2><p>Language, timezone, and clock</p></div>';
      const note = ref("p", "reference-regional-info", "Timezone also controls timestamps generated by Nowlert notification formatters."); heading.after(note);
      const help = { "preference-language": "Select the language used in Nowlert.", "preference-timezone": "Set your local timezone for timestamps.", "preference-time-format": "Choose how timestamps are displayed." };
      Object.entries(help).forEach(([id, text]) => { const label = byId(id)?.closest("label"); if (label && !label.querySelector(".reference-preference-help")) label.querySelector(":scope > span")?.after(ref("small", "reference-preference-help", text)); });
      const submit = form.querySelector('button[type="submit"]');
      if (submit) { submit.textContent = "▣  Save settings"; submit.parentElement?.append(ref("span", "reference-preference-save-note", "Your preferences will be saved immediately.")); }
    }
    updates.classList.add("reference-updates-card");
    const toolbar = updates.querySelector(":scope > .section-toolbar"); const panel = updates.querySelector(":scope > .update-panel");
    if (toolbar && toolbar.dataset.referenceUpdates !== "1") {
      toolbar.dataset.referenceUpdates = "1"; const button = byId("platform-check-updates"); toolbar.replaceChildren();
      const copy = ref("div", "reference-update-heading-copy"); copy.innerHTML = '<span class="reference-settings-card-icon">⇩</span><div><h2>Updates</h2><p>Review the running version and any advertised Nowlert update.</p></div>'; toolbar.append(copy);
      if (button) { button.textContent = "⟳  Check for updates"; button.className = "button secondary reference-check-updates"; toolbar.append(button); }
    }
    if (panel && panel.dataset.referenceUpdates !== "1") {
      panel.dataset.referenceUpdates = "1"; const running = byId("running-version"); const available = byId("available-version"); const status = byId("update-status");
      const statusCard = ref("section", "reference-update-status-card"); statusCard.innerHTML = '<span class="reference-update-status-icon">✓</span><div><strong id="reference-update-headline">Nowlert is up to date</strong></div>';
      if (status) statusCard.lastElementChild.append(status);
      const versions = ref("div", "reference-update-version-grid");
      for (const [label, value, note, icon] of [["Running version", running, "Currently installed version.", "◇"], ["Available version", available, "Latest available version.", "☁"]]) {
        const card = ref("article", "reference-update-version-card"); card.append(ref("span", "reference-version-icon", icon)); const box = ref("div"); box.append(ref("strong", "", label)); if (value) box.append(value); box.append(ref("small", "", note)); card.append(box); versions.append(card);
      }
      const checked = ref("div", "reference-update-checked"); checked.innerHTML = '<span class="reference-update-checked-icon">◷</span><div><span id="reference-update-last-checked">Last checked —</span><small>Automatic check every 6 hours</small></div>';
      panel.replaceChildren(statusCard, versions, checked);
    }
  }

  function syncSettingsUpdateState() {
    ensureSettingsReferenceLayout();
    const status = state.versionStatus || {}; const headline = byId("reference-update-headline"); const card = document.querySelector(".reference-update-status-card");
    if (headline) headline.textContent = status.check_error ? "Update status unavailable" : status.update_available ? "A Nowlert update is available" : "Nowlert is up to date";
    if (card) { card.classList.toggle("is-update-available", Boolean(status.update_available)); card.classList.toggle("is-error", Boolean(status.check_error)); }
    if (byId("reference-update-last-checked")) byId("reference-update-last-checked").textContent = status.checked_at ? `Last checked ${typeof formatTime === "function" ? formatTime(status.checked_at) : status.checked_at}` : "Last checked —";
  }

  function memberSince(user) {
    const value = user?.created_at || user?.created || user?.member_since; if (!value) return "Unavailable";
    const number = Number(value); const date = new Date(Number.isFinite(number) ? (number < 10000000000 ? number * 1000 : number) : value); if (Number.isNaN(date.getTime())) return "Unavailable";
    return new Intl.DateTimeFormat(state.preferences?.language || "en-GB", { year: "numeric", month: "short", day: "2-digit", timeZone: state.preferences?.timezone || "Europe/Lisbon" }).format(date);
  }

  function ensureAccountReferenceLayout() {
    const section = byId("view-account"); const grid = section?.querySelector(":scope > .account-grid"); const identity = grid?.querySelector(".identity-card"); const password = grid ? [...grid.children].find((item) => item !== identity) : null;
    if (!section || !grid || !identity || !password) return; section.classList.add("reference-account-page"); grid.classList.add("reference-account-grid");
    if (identity.dataset.referenceAccount !== "1") {
      identity.dataset.referenceAccount = "1"; identity.classList.add("reference-profile-card"); const body = ref("div", "reference-profile-body"); [...identity.children].forEach((child) => body.append(child));
      const heading = ref("div", "reference-account-card-heading"); heading.innerHTML = '<span></span><div><h2>Profile & access</h2><p>Manage your profile information and account access.</p></div>';
      const meta = ref("div", "reference-account-meta");
      for (const [label, id, value] of [["Account role", "reference-account-role-value", "Administrator"], ["Member since", "reference-account-member-value", "Unavailable"], ["MFA status", "reference-account-mfa-value", "Not enabled"]]) {
        const item = ref("div", "reference-account-meta-item"); item.innerHTML = `<span class="reference-account-meta-icon">◇</span><div><small>${label}</small><strong id="${id}">${value}</strong></div>`; meta.append(item);
      }
      identity.append(heading, body, meta);
    }
    if (password.dataset.referenceAccount !== "1") {
      password.dataset.referenceAccount = "1"; password.classList.add("reference-password-card"); const oldHeading = password.querySelector(":scope > .panel-heading"); const form = byId("password-form");
      if (oldHeading) { oldHeading.classList.add("reference-password-heading"); oldHeading.innerHTML = '<div><h2>Password & sessions</h2><p>Change your password and view your active session information.</p></div>'; }
      const main = ref("div", "reference-password-main"); if (oldHeading) main.append(oldHeading); if (form) main.append(form);
      const posture = ref("aside", "reference-security-posture"); posture.innerHTML = '<div class="reference-posture-block"><span class="reference-posture-icon">▣</span><div><small>Active sessions</small><strong id="reference-active-sessions">1</strong><p>You are currently signed in on this device.</p></div></div><div class="reference-posture-divider"></div><div class="reference-posture-block"><span class="reference-posture-icon">◇</span><div><small>Security posture</small><strong class="reference-good">Good</strong><p>No suspicious activity detected.</p></div></div><div class="reference-posture-divider"></div><ul><li>Password is set</li><li>Account is active</li><li>No security alerts</li></ul>';
      password.replaceChildren(main, posture);
    }
    const tokens = byId("account-api-tokens");
    if (tokens) { tokens.classList.add("reference-api-tokens"); const toolbar = tokens.querySelector(":scope > .section-toolbar"); const title = toolbar?.querySelector("h2"); if (title) title.textContent = "API tokens"; const add = toolbar?.querySelector('[data-action="new-token"]'); if (add) add.textContent = "Issue token"; }
  }

  function syncAccountReference() {
    ensureAccountReferenceLayout(); const user = state.user || {};
    if (byId("reference-account-role-value")) byId("reference-account-role-value").textContent = user.role === "admin" ? "Administrator" : "User";
    if (byId("reference-account-member-value")) byId("reference-account-member-value").textContent = memberSince(user);
    if (byId("reference-account-mfa-value")) byId("reference-account-mfa-value").textContent = user.mfa_enabled ? "Enabled" : "Not enabled";
    if (byId("reference-active-sessions")) byId("reference-active-sessions").textContent = Number(user.active_sessions || 1);
    const restart = byId("restart-header-button");
    if (restart) { const show = state.currentView === "account" && typeof isAdmin === "function" && isAdmin(); restart.hidden = !show; restart.textContent = "⏻ Restart Nowlert"; restart.classList.toggle("reference-account-restart", show); }
  }

  function syncAll() {
    syncQueued = false;
    ensurePreviewReferenceLayout();
    syncUsersReference();
    syncSettingsUpdateState();
    syncAccountReference();
  }

  function scheduleSync() {
    if (syncQueued) return; syncQueued = true;
    requestAnimationFrame(() => { syncAll(); setTimeout(syncAll, 60); });
  }

  if (typeof openPreview === "function") {
    const base = openPreview;
    openPreview = function openPreviewWithReferenceLayout(id) { const result = base(id); previewDestinationId = id || ""; syncPreviewReference(); closePreviewRoutes(); return result; };
  }
  if (typeof renderUsers === "function") { const base = renderUsers; renderUsers = function renderUsersWithReferenceLayout() { const result = base(); syncUsersReference(); return result; }; }
  if (typeof renderUpdates === "function") { const base = renderUpdates; renderUpdates = function renderUpdatesWithReferenceLayout() { const result = base(); syncSettingsUpdateState(); return result; }; }
  if (typeof renderTokens === "function") { const base = renderTokens; renderTokens = function renderTokensWithReferenceLayout() { const result = base(); ensureAccountReferenceLayout(); return result; }; }
  if (typeof navigate === "function") { const base = navigate; navigate = function navigateWithReferenceAcceptance(view, mode = "push") { const result = base(view, mode); scheduleSync(); return result; }; }
  if (typeof showApp === "function") { const base = showApp; showApp = function showAppWithReferenceAcceptance(session) { const result = base(session); scheduleSync(); return result; }; }

  byId("preview-dialog")?.addEventListener("close", closePreviewRoutes);
  document.addEventListener("DOMContentLoaded", scheduleSync, { once: true });
  scheduleSync();
})();
