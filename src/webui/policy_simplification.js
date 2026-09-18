"use strict";

(() => {
  const ADMIN_VIEWS = ["users", "settings", "updates", "data"];
  const LABELS = {
    users: "Users",
    settings: "Settings",
    updates: "Updates",
    data: "Data tools",
  };
  const SETTING_GROUPS = [
    [
      "Aliases & normalization",
      "Turn stable infrastructure identifiers into readable names before Filtering and formatting.",
      ["unifi_protect", "home_assistant"],
    ],
    [
      "Event processing",
      "Control deterministic transport processing that happens before destination Filtering.",
      ["redfish"],
    ],
  ];
  const SETTING_LABELS = {
    unifi_protect: "UniFi Protect",
    home_assistant: "Home Assistant",
    redfish: "Redfish transport",
  };
  const SETTING_DESCRIPTIONS = {
    unifi_protect: "Map camera and console identifiers to readable device names.",
    home_assistant: "Map Home Assistant endpoints and components to readable device names.",
    redfish: "Suppress duplicate Redfish events before destination Filtering.",
  };

  let filterDestinationId = "";
  let integrationListScrollTop = 0;

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
    if (
      button.children.length === 2
      && oldIcon?.textContent === icon
      && oldLabel?.textContent === label
    ) return;
    const iconNode = span(icon, "profile-menu-icon");
    iconNode.setAttribute("aria-hidden", "true");
    button.replaceChildren(iconNode, span(label, "profile-menu-label"));
  }

  function syncProfile() {
    document.querySelector("#profile-menu-button .profile-chevron")?.remove();
    document.getElementById("profile-settings")?.remove();
    profileRow(document.getElementById("profile-api-access"), "◇", "API access");
    profileRow(
      document.querySelector('#profile-menu-popover [data-view="account"]'),
      "◇",
      "Security",
    );
    profileRow(
      document.querySelector('#profile-menu-popover [data-action="logout"]'),
      "↪",
      "Sign out",
    );
  }

  function buildAdminTabs(section) {
    section.querySelector(".administration-tabs")?.remove();
    const tabs = element("div", {
      className: "row-actions administration-tabs",
      attributes: { "aria-label": "Administration sections" },
    });
    for (const view of ADMIN_VIEWS) {
      tabs.append(element("button", {
        className: `button small ${view === state.currentView ? "primary" : "secondary"}`,
        text: LABELS[view],
        type: "button",
        dataset: { view, administrationTab: view },
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
      if (
        !tabs
        || !ADMIN_VIEWS.every((candidate) => (
          tabs.querySelector(`[data-administration-tab="${candidate}"]`)
        ))
      ) buildAdminTabs(section);
    }
    for (const button of document.querySelectorAll("[data-administration-tab]")) {
      const active = button.dataset.administrationTab === view;
      button.classList.toggle("primary", active);
      button.classList.toggle("secondary", !active);
    }
    const nav = document.getElementById("administration-nav");
    if (nav) nav.classList.toggle("active", ADMIN_VIEWS.includes(view));
    if (ADMIN_VIEWS.includes(view)) {
      const pageTitle = document.getElementById("page-title");
      if (pageTitle) pageTitle.textContent = "Administration";
    }
  }

  function settingCard(source) {
    const settings = state.integrationSettings[source] || {};
    const error = (state.integrationSettingsErrors || []).find(
      (item) => item.resource === source,
    );
    const summary = error ? error.message : integrationSettingSummary(source, settings);
    return element("article", { className: "resource-card compact-resource-card settings-resource-card" }, [
      element("div", { className: "resource-card-heading" }, [
        element("div", { className: "settings-card-copy" }, [
          element("strong", { text: SETTING_LABELS[source] || friendlyName(source) }),
          element("span", {
            className: "settings-card-description",
            text: SETTING_DESCRIPTIONS[source] || "",
          }),
          element("small", { className: "settings-card-summary", text: summary }),
        ]),
        error ? badge("Needs repair", "danger") : badge("Database", "success"),
      ]),
      element("div", { className: "resource-actions" }, [
        actionButton("Edit", "edit-integration-settings", source),
      ]),
    ]);
  }

  function renderSimpleSettings() {
    const container = byId("integration-settings-list");
    if (!container) return;
    container.replaceChildren();
    container.classList.remove("resource-grid");
    container.classList.add("simplified-settings-groups");
    for (const [title, copy, sources] of SETTING_GROUPS) {
      const wrapper = element("section", { className: "settings-subsection" }, [
        element("div", { className: "settings-subsection-heading" }, [
          element("h4", { text: title }),
          element("p", { text: copy }),
        ]),
      ]);
      const grid = element("div", { className: "settings-subsection-grid" });
      sources.forEach((source) => grid.append(settingCard(source)));
      wrapper.append(grid);
      container.append(wrapper);
    }
    const heading = container.closest("article.panel")?.querySelector(".panel-heading > div");
    if (heading) {
      const eyebrow = heading.querySelector(".eyebrow");
      const title = heading.querySelector("h3");
      const description = heading.querySelector("p:not(.eyebrow)");
      if (eyebrow) eyebrow.textContent = "Deterministic processing";
      if (title) title.textContent = "Normalization and event processing";
      if (description) {
        description.textContent = "Configure readable aliases and transport processing. Delivery decisions belong only to Filtering.";
      }
    }
  }

  if (typeof renderIntegrationSettings === "function") {
    renderIntegrationSettings = renderSimpleSettings;
  }

  function syncShell(view = state.currentView) {
    syncProfile();
    syncAdmin(view);
    if (view === "settings") renderSimpleSettings();
  }

  const oldShowApp = showApp;
  showApp = function policyShowApp(session) {
    const result = oldShowApp(session);
    syncShell();
    return result;
  };

  const oldNavigate = navigate;
  navigate = function policyNavigate(view, mode = "push") {
    const result = oldNavigate(view, mode);
    syncShell(view);
    return result;
  };

  function normalized(value) {
    return String(value || "").trim().toLowerCase();
  }

  function isDellSessionSuppression(rule) {
    if (!rule || rule.action !== "block" || !rule.conditions) return false;
    const ids = new Set((rule.conditions.message_id || []).map(normalized));
    const ips = (rule.conditions.source_ip || []).map((item) => String(item).trim()).filter(Boolean);
    return ids.has("usr0030") && ids.has("usr0032") && ips.length > 0;
  }

  function regularDellBlockRules(integration) {
    const policyRules = Array.isArray(integration?.policy_rules) ? integration.policy_rules : [];
    return policyRules.filter(
      (rule) => rule.action === "block" && !isDellSessionSuppression(rule),
    );
  }

  function supportedDellPolicy(integration) {
    const policyRules = Array.isArray(integration?.policy_rules) ? integration.policy_rules : [];
    const regularBlocks = regularDellBlockRules(integration);
    return regularBlocks.length <= 1 && policyRules.every(
      (rule) => rule.action === "block",
    );
  }

  function dellTrustedIps(integration) {
    const values = [];
    const seen = new Set();
    for (const rule of integration?.policy_rules || []) {
      if (!isDellSessionSuppression(rule)) continue;
      for (const value of rule.conditions.source_ip || []) {
        const text = String(value).trim();
        if (!text || seen.has(text.toLowerCase())) continue;
        seen.add(text.toLowerCase());
        values.push(text);
      }
    }
    return values;
  }

  function inferOperator(values) {
    const list = (values || []).map(String);
    if (
      list.length
      && list.every((value) => (
        value.length >= 2
        && value.startsWith("*")
        && value.endsWith("*")
        && !/[?\[]/.test(value.slice(1, -1))
      ))
    ) return "contains";
    if (list.some((value) => /[*?\[]/.test(value))) return "wildcard";
    return "equals";
  }

  function displayTextValues(values, operator) {
    if (operator !== "contains") return (values || []).join(", ");
    return (values || []).map((value) => {
      const text = String(value);
      return text.startsWith("*") && text.endsWith("*")
        ? text.slice(1, -1)
        : text;
    }).join(", ");
  }

  function hydrateDellBlockRule(integration) {
    const blockRules = regularDellBlockRules(integration);
    if (blockRules.length !== 1) return;
    const conditions = blockRules[0].conditions || {};
    for (const field of integration.fields || []) {
      const values = Array.isArray(conditions[field.key]) ? conditions[field.key] : [];
      if (field.kind === "enum") {
        const selected = new Set(values.map(normalized));
        const inputs = document.querySelectorAll(
          `[data-filter-enum="${CSS.escape(field.key)}"]`,
        );
        for (const input of inputs) {
          input.checked = selected.has(normalized(input.value));
        }
      } else if (field.kind === "text") {
        const input = document.querySelector(
          `[data-filter-text="${CSS.escape(field.key)}"]`,
        );
        const operator = document.querySelector(
          `[data-filter-operator="${CSS.escape(field.key)}"]`,
        );
        if (!input) continue;
        const mode = inferOperator(values);
        input.value = displayTextValues(values, mode);
        if (operator) operator.value = mode;
      }
    }
  }

  function removeDellPolicyPanel() {
    document.getElementById("filter-dell-session-policy")?.remove();
  }

  function renderDellPolicyPanel(integration) {
    removeDellPolicyPanel();
    if (!integration || integration.source !== "dell_idrac") return;
    hydrateDellBlockRule(integration);

    const warning = byId("filter-legacy-warning");
    if (warning && supportedDellPolicy(integration)) {
      warning.hidden = true;
      warning.textContent = "";
    }

    const panel = element("section", {
      className: "filtering-source-policy",
      attributes: { id: "filter-dell-session-policy" },
    }, [
      element("div", { className: "filtering-source-policy-heading" }, [
        element("strong", { text: "Session audit suppression" }),
        element("p", {
          text: "Ignore successful iDRAC session login/logout events from trusted management clients. Failed authentication is never suppressed.",
        }),
      ]),
      element("label", { className: "filtering-source-policy-field" }, [
        element("span", { text: "Trusted management client IPs" }),
        element("textarea", {
          value: dellTrustedIps(integration).join("\n"),
          attributes: {
            id: "filter-dell-trusted-ips",
            rows: 4,
            placeholder: "192.0.2.164\n192.0.2.251",
          },
        }),
        element("small", {
          text: "One address per line. This policy applies only to USR0030 and USR0032 session audit events.",
        }),
      ]),
    ]);
    const actions = document.querySelector("#filter-editor-step .filtering-editor-actions");
    if (actions) actions.before(panel);
  }

  async function loadDellPolicyEditor(destinationId) {
    if (!destinationId) return;
    const payload = await request(`/filters/destinations/${destinationId}`);
    const integration = (payload.integrations || []).find(
      (item) => item.source === "dell_idrac",
    );
    if (!integration || byId("filter-editor-step")?.hidden) return;
    renderDellPolicyPanel(integration);
  }

  function trustedIpsFromEditor() {
    return String(byId("filter-dell-trusted-ips")?.value || "")
      .split(/\r?\n|,/)
      .map((value) => value.trim())
      .filter(Boolean);
  }

  const oldRequest = request;
  request = function policyRequest(path, options = {}) {
    const method = String(options?.method || "GET").toUpperCase();
    const destinationDellFilter = /\/filters\/destinations\/[^/]+\/sources\/dell_idrac$/.test(String(path || ""));
    const body = options?.body;
    const nativeRules = body && typeof body.rules === "object" && body.rules !== null
      ? body.rules
      : null;
    if (method !== "PUT" || !destinationDellFilter || nativeRules === null) {
      return oldRequest(path, options);
    }

    const incomingPolicy = Array.isArray(nativeRules.policy)
      ? nativeRules.policy
      : (Object.keys(nativeRules).length
          ? [{ action: "block", conditions: nativeRules }]
          : []);
    const policy = incomingPolicy.filter((rule) => !isDellSessionSuppression(rule));

    const trustedIps = trustedIpsFromEditor();
    if (trustedIps.length) {
      policy.push({
        action: "block",
        conditions: {
          message_id: ["USR0030", "USR0032"],
          source_ip: trustedIps,
        },
      });
    }
    const editorToggle = document.querySelector('[data-filter-toggle-context="editor"]');
    const transformed = {
      ...options,
      body: {
        ...body,
        rules: { policy },
        enabled: Boolean(editorToggle?.checked && policy.length),
      },
    };
    return oldRequest(path, transformed);
  };

  function restoreIntegrationScroll() {
    const dialog = byId("filtering-dialog");
    const step = byId("filter-integration-step");
    if (!dialog?.open || !step || step.hidden) return;
    window.requestAnimationFrame(() => {
      if (dialog.open && !step.hidden) dialog.scrollTop = integrationListScrollTop;
    });
  }

  const integrationStep = byId("filter-integration-step");
  if (integrationStep) {
    new MutationObserver(restoreIntegrationScroll).observe(integrationStep, {
      attributes: true,
      attributeFilter: ["hidden"],
    });
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-filter-action]");
    if (!button) return;
    const action = button.dataset.filterAction;
    const dialog = byId("filtering-dialog");
    const editor = byId("filter-editor-step");

    if (
      action === "close"
      && button.classList.contains("icon-button")
      && editor
      && !editor.hidden
    ) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const cancelButton = editor.querySelector('button[data-filter-action="back-integrations"]');
      if (cancelButton) cancelButton.click();
      return;
    }

    if (action === "manage-destination") {
      filterDestinationId = button.dataset.filterId || "";
      integrationListScrollTop = 0;
      return;
    }
    if (action === "continue-destination") {
      filterDestinationId = byId("filter-destination-select")?.value || "";
      integrationListScrollTop = 0;
      return;
    }
    if (action === "configure-integration") {
      integrationListScrollTop = dialog?.scrollTop || 0;
      const source = button.dataset.filterId || "";
      const listToggle = button.closest(".filtering-integration-row")
        ?.querySelector('input[data-filter-toggle-context="list"]');
      const expectedEnabled = Boolean(listToggle?.checked);
      window.setTimeout(() => {
        if (byId("filter-editor-step")?.hidden) return;
        const editorToggle = document.querySelector('[data-filter-toggle-context="editor"]');
        if (editorToggle) editorToggle.checked = expectedEnabled;
        if (source === "dell_idrac") {
          loadDellPolicyEditor(filterDestinationId).catch((error) => {
            toast(error.message || "Dell filtering policy could not be loaded.", "error");
          });
        } else {
          removeDellPolicyPanel();
        }
      }, 0);
      return;
    }
    if (action === "back-integrations") {
      removeDellPolicyPanel();
      return;
    }
    if (action === "close" || action === "finish") {
      integrationListScrollTop = 0;
      removeDellPolicyPanel();
    }
  }, true);

  document.addEventListener("change", (event) => {
    const toggle = event.target.closest('input[data-filter-toggle-context="list"]');
    if (!toggle) return;
    const source = toggle.dataset.filterToggle || "";
    if (!toggle.checked) {
      if (source === "dell_idrac") removeDellPolicyPanel();
      return;
    }
    const dialog = byId("filtering-dialog");
    integrationListScrollTop = dialog?.scrollTop || integrationListScrollTop;
    window.setTimeout(() => {
      if (byId("filter-editor-step")?.hidden) return;
      const editorToggle = document.querySelector('[data-filter-toggle-context="editor"]');
      if (editorToggle) editorToggle.checked = true;
      if (source === "dell_idrac") {
        loadDellPolicyEditor(filterDestinationId).catch((error) => {
          toast(error.message || "Dell filtering policy could not be loaded.", "error");
        });
      } else {
        removeDellPolicyPanel();
      }
    }, 0);
  });

  const popover = document.getElementById("profile-menu-popover");
  if (popover) {
    new MutationObserver(syncProfile).observe(popover, { childList: true, subtree: true });
  }
  syncShell();
})();