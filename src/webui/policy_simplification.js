"use strict";

(() => {
  const ADMIN_VIEWS = ["users", "settings", "updates", "data"];
  const LABELS = { users: "Users", settings: "Settings", updates: "Updates", data: "Data tools" };
  const SETTING_GROUPS = [
    ["Aliases & normalization", "Turn stable infrastructure identifiers into readable names before Filtering and formatting.", ["unifi_protect", "home_assistant"]],
    ["Event processing", "Control deterministic processing that happens before destination Filtering.", ["redfish"]],
  ];
  const SETTING_LABELS = { unifi_protect: "UniFi Protect", home_assistant: "Home Assistant", redfish: "Redfish transport" };
  let destinationId = "";
  let destination = null;
  let integration = null;
  let rules = [];
  let policyDialog = null;

  function span(text, cls = "") {
    const node = document.createElement("span");
    node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }

  function profileRow(button, icon, label) {
    if (!button) return;
    button.classList.add("profile-menu-item");
    button.setAttribute("role", "menuitem");
    const oldIcon = button.querySelector(":scope > .profile-menu-icon");
    const oldLabel = button.querySelector(":scope > .profile-menu-label");
    if (button.children.length === 2 && oldIcon?.textContent === icon && oldLabel?.textContent === label) return;
    const iconNode = span(icon, "profile-menu-icon");
    iconNode.setAttribute("aria-hidden", "true");
    button.replaceChildren(iconNode, span(label, "profile-menu-label"));
  }

  function syncProfile() {
    document.querySelector("#profile-menu-button .profile-chevron")?.remove();
    document.getElementById("profile-settings")?.remove();
    profileRow(document.getElementById("profile-api-access"), "◇", "API access");
    profileRow(document.querySelector('#profile-menu-popover [data-view="account"]'), "◇", "Security");
    profileRow(document.querySelector('#profile-menu-popover [data-action="logout"]'), "↪", "Sign out");
  }

  function buildAdminTabs(section) {
    section.querySelector(".administration-tabs")?.remove();
    const tabs = element("div", { className: "row-actions administration-tabs", attributes: { "aria-label": "Administration sections" } });
    for (const view of ADMIN_VIEWS) {
      tabs.append(element("button", {
        className: `button small ${view === state.currentView ? "primary" : "secondary"}`,
        text: LABELS[view], type: "button", dataset: { view, administrationTab: view },
      }));
    }
    section.prepend(tabs);
  }

  function syncAdmin(view = state.currentView) {
    if (!isAdmin()) return;
    for (const name of ADMIN_VIEWS) {
      const section = document.getElementById(`view-${name}`);
      if (!section) continue;
      const tabs = section.querySelector(".administration-tabs");
      if (!tabs || !ADMIN_VIEWS.every((v) => tabs.querySelector(`[data-administration-tab="${v}"]`))) buildAdminTabs(section);
    }
    for (const button of document.querySelectorAll("[data-administration-tab]")) {
      const active = button.dataset.administrationTab === view;
      button.classList.toggle("primary", active);
      button.classList.toggle("secondary", !active);
    }
    const nav = document.getElementById("administration-nav");
    if (nav) nav.classList.toggle("active", ADMIN_VIEWS.includes(view));
    if (ADMIN_VIEWS.includes(view)) document.getElementById("page-title").textContent = "Administration";
  }

  function settingCard(source) {
    const settings = state.integrationSettings[source] || {};
    const error = (state.integrationSettingsErrors || []).find((item) => item.resource === source);
    return element("article", { className: "resource-card compact-resource-card" }, [
      element("div", { className: "resource-card-heading" }, [
        element("div", {}, [
          element("strong", { text: SETTING_LABELS[source] || friendlyName(source) }),
          element("small", { text: error ? error.message : integrationSettingSummary(source, settings) }),
        ]),
        error ? badge("Needs repair", "danger") : badge("Database", "success"),
      ]),
      element("div", { className: "resource-actions" }, [actionButton("Edit", "edit-integration-settings", source)]),
    ]);
  }

  function renderSimpleSettings() {
    const container = byId("integration-settings-list");
    if (!container) return;
    container.replaceChildren();
    container.classList.add("simplified-settings-groups");
    for (const [title, copy, sources] of SETTING_GROUPS) {
      const wrapper = element("section", { className: "settings-subsection" }, [
        element("div", { className: "settings-subsection-heading" }, [element("h4", { text: title }), element("p", { text: copy })]),
      ]);
      const grid = element("div", { className: "resource-grid settings-subsection-grid" });
      sources.forEach((source) => grid.append(settingCard(source)));
      wrapper.append(grid);
      container.append(wrapper);
    }
    const heading = container.closest("article.panel")?.querySelector(".panel-heading > div");
    if (heading) {
      heading.querySelector(".eyebrow").textContent = "Deterministic processing";
      heading.querySelector("h3").textContent = "Normalization and event processing";
      heading.querySelector("p:not(.eyebrow)").textContent = "Configure readable aliases and transport processing. Delivery decisions belong only to Filtering.";
    }
  }

  if (typeof renderIntegrationSettings === "function") renderIntegrationSettings = renderSimpleSettings;

  function syncShell(view = state.currentView) {
    syncProfile();
    syncAdmin(view);
    if (view === "settings") renderSimpleSettings();
  }

  const oldShowApp = showApp;
  showApp = function policyShowApp(session) { const result = oldShowApp(session); syncShell(); return result; };
  const oldNavigate = navigate;
  navigate = function policyNavigate(view, mode = "push") { const result = oldNavigate(view, mode); syncShell(view); return result; };

  function normalizeRules(item) {
    if (Array.isArray(item.policy_rules) && item.policy_rules.length) return structuredClone(item.policy_rules);
    if (item.rules && Object.keys(item.rules).length) return [{ action: "allow", conditions: structuredClone(item.rules) }];
    return (item.legacy_clauses || []).map((conditions) => ({ action: "allow", conditions: structuredClone(conditions) }));
  }

  function ensureDialog() {
    if (policyDialog) return policyDialog;
    policyDialog = document.createElement("dialog");
    policyDialog.id = "policy-filter-dialog";
    policyDialog.className = "modal policy-filter-modal";
    policyDialog.innerHTML = `
      <div class="modal-heading"><div><p class="eyebrow">Deterministic destination policy</p><h2 id="policy-title">Filtering policy</h2><p id="policy-subtitle" class="field-help"></p></div><button class="icon-button" type="button" data-policy="close">×</button></div>
      <div class="policy-explainer"><strong>BLOCK wins.</strong><span>ALLOW rules restrict delivery only when at least one ALLOW rule exists.</span></div>
      <div id="policy-rules" class="policy-rule-list"></div>
      <div class="policy-add-actions"><button class="button secondary small" type="button" data-policy="add-allow">＋ Allow rule</button><button class="button secondary small" type="button" data-policy="add-block">＋ Block rule</button></div>
      <div class="modal-actions"><button class="button danger" type="button" data-policy="clear">Remove filtering</button><span class="filtering-action-spacer"></span><button class="button secondary" type="button" data-policy="close">Cancel</button><button class="button primary" type="button" data-policy="save">Save policy</button></div>`;
    document.body.append(policyDialog);
    policyDialog.addEventListener("click", onPolicyClick);
    return policyDialog;
  }

  function field(key) { return (integration?.fields || []).find((item) => item.key === key); }

  function renderRules() {
    const root = byId("policy-rules");
    root.replaceChildren();
    rules.forEach((rule, index) => {
      const card = element("article", { className: `policy-rule policy-rule-${rule.action}`, dataset: { ruleIndex: index } });
      const select = document.createElement("select");
      select.dataset.ruleAction = index;
      for (const action of ["allow", "block"]) {
        const option = element("option", { text: action.toUpperCase(), value: action });
        option.selected = rule.action === action;
        select.append(option);
      }
      card.append(element("div", { className: "policy-rule-heading" }, [
        element("div", { className: "policy-rule-title" }, [element("span", { className: `policy-action-chip ${rule.action}`, text: rule.action.toUpperCase() }), element("strong", { text: `Rule ${index + 1}` })]),
        select,
        element("button", { className: "button danger small", text: "Remove rule", type: "button", dataset: { policy: "remove-rule", ruleIndex: index } }),
      ]));
      const conditions = element("div", { className: "policy-condition-list" });
      for (const [key, values] of Object.entries(rule.conditions || {})) {
        const descriptor = field(key);
        if (!descriptor) continue;
        const input = element("input", { type: "text", value: (values || []).join(", "), dataset: { condition: key, ruleIndex: index }, attributes: { placeholder: "value, wildcard*, another value" } });
        conditions.append(element("label", { className: "policy-condition" }, [element("strong", { text: descriptor.label }), input, element("button", { className: "button secondary small", text: "Remove", type: "button", dataset: { policy: "remove-condition", ruleIndex: index, condition: key } })]));
      }
      card.append(conditions);
      const add = document.createElement("select");
      add.dataset.addCondition = index;
      add.append(element("option", { value: "", text: "Add condition…" }));
      (integration?.fields || []).filter((item) => !(item.key in (rule.conditions || {}))).forEach((item) => add.append(element("option", { value: item.key, text: item.label })));
      card.append(element("div", { className: "policy-add-condition" }, [add, element("button", { className: "button secondary small", text: "Add condition", type: "button", dataset: { policy: "add-condition", ruleIndex: index } })]));
      root.append(card);
    });
    if (!rules.length) root.append(element("div", { className: "empty-state" }, [element("strong", { text: "No filtering rules" }), element("span", { text: "With no rules, every normalized event is delivered." })]));
  }

  function readRules() {
    rules = rules.map((rule, index) => {
      const card = byId("policy-rules").querySelector(`[data-rule-index="${index}"]`);
      const action = card?.querySelector("[data-rule-action]")?.value === "block" ? "block" : "allow";
      const conditions = {};
      for (const input of card?.querySelectorAll("[data-condition]") || []) {
        const values = input.value.split(",").map((value) => value.trim()).filter(Boolean);
        if (values.length) conditions[input.dataset.condition] = values;
      }
      return { action, conditions };
    });
  }

  async function openPolicy(id, source) {
    const payload = await request(`/filters/destinations/${id}`);
    integration = (payload.integrations || []).find((item) => item.source === source);
    if (!integration) return toast("Integration is not available for this destination.", "error");
    destination = payload.destination;
    rules = normalizeRules(integration);
    if (!rules.length) rules = [{ action: "allow", conditions: {} }];
    const dialog = ensureDialog();
    byId("policy-title").textContent = integration.name || friendlyName(source);
    byId("policy-subtitle").textContent = `${destination.name} · ${friendlyName(destination.output_type)}`;
    renderRules();
    dialog.showModal();
  }

  async function savePolicy() {
    readRules();
    const policy = rules.filter((rule) => Object.keys(rule.conditions).length);
    if (!policy.length) return clearPolicy();
    await request(`/filters/destinations/${destination.id}/sources/${integration.source}`, { method: "PUT", body: { rules: { policy }, enabled: true } });
    toast(`Filtering policy saved for ${integration.name}.`);
    policyDialog.close();
    document.getElementById("filtering-dialog")?.close();
    navigate("filtering", "replace");
  }

  async function clearPolicy() {
    await request(`/filters/destinations/${destination.id}/sources/${integration.source}`, { method: "DELETE" });
    toast(`Filtering removed for ${integration.name}.`);
    policyDialog.close();
    document.getElementById("filtering-dialog")?.close();
    navigate("filtering", "replace");
  }

  async function onPolicyClick(event) {
    const button = event.target.closest("[data-policy]");
    if (!button) return;
    const action = button.dataset.policy;
    const index = Number(button.dataset.ruleIndex);
    if (action === "close") return policyDialog.close();
    if (action === "add-allow" || action === "add-block") { readRules(); rules.push({ action: action === "add-block" ? "block" : "allow", conditions: {} }); return renderRules(); }
    if (action === "remove-rule") { readRules(); rules.splice(index, 1); return renderRules(); }
    if (action === "remove-condition") { readRules(); delete rules[index].conditions[button.dataset.condition]; return renderRules(); }
    if (action === "add-condition") { readRules(); const key = policyDialog.querySelector(`[data-add-condition="${index}"]`)?.value; if (key) rules[index].conditions[key] = []; return renderRules(); }
    try {
      button.disabled = true;
      if (action === "save") await savePolicy();
      if (action === "clear") await clearPolicy();
    } catch (error) { toast(error.message || "Filtering policy could not be updated.", "error"); }
    finally { button.disabled = false; }
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter-action]");
    if (!button) return;
    if (button.dataset.filterAction === "manage-destination") { destinationId = button.dataset.filterId || ""; return; }
    if (button.dataset.filterAction === "continue-destination") { destinationId = byId("filter-destination-select")?.value || ""; return; }
    if (button.dataset.filterAction !== "configure-integration") return;
    const id = destinationId || byId("filter-destination-select")?.value || "";
    const source = button.dataset.filterId || "";
    if (!id || !source) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openPolicy(id, source).catch((error) => toast(error.message || "Filtering policy could not be loaded.", "error"));
  }, true);

  const popover = document.getElementById("profile-menu-popover");
  if (popover) new MutationObserver(syncProfile).observe(popover, { childList: true, subtree: true });
  syncShell();
})();
