"use strict";

const emailAlertsState = {
  tab: "overview",
  loading: false,
  loaded: false,
  overview: null,
  groups: [],
  rules: [],
  mailboxes: [],
  activity: { messages: [], processing: [] },
};

const EMAIL_CLASSIFICATIONS = [
  ["urgent", "Urgent"],
  ["warning", "Warning"],
  ["information", "Information"],
  ["ignore", "Ignore"],
];

const EMAIL_RULE_FIELDS = [
  ["sender", "Sender"],
  ["sender_domain", "Sender domain"],
  ["recipient", "Recipient"],
  ["subject", "Subject"],
  ["body", "Body"],
  ["mailbox", "Mailbox"],
];

const EMAIL_RULE_OPERATORS = [
  ["equals", "Equals"],
  ["contains", "Contains"],
  ["starts_with", "Starts with"],
  ["ends_with", "Ends with"],
];

function emailOption(value, label) {
  return element("option", { value, text: label });
}

function emailBadge(label, tone = "") {
  return element("span", {
    className: `email-badge ${tone}`.trim(),
    text: label,
  });
}

function emailClassificationBadge(value) {
  const label = EMAIL_CLASSIFICATIONS.find(([key]) => key === value)?.[1]
    || "Unclassified";
  return emailBadge(label, `classification-${value || "none"}`);
}

function emailConnectionBadge(value, enabled = true) {
  if (!enabled) return emailBadge("Disabled", "state-disabled");
  const labels = {
    healthy: "Healthy",
    connecting: "Connecting",
    degraded: "Degraded",
    error: "Error",
    disconnected: "Disconnected",
  };
  return emailBadge(labels[value] || "Disconnected", `state-${value || "disconnected"}`);
}

function emailGroupName(id) {
  return emailAlertsState.groups.find((item) => item.id === id)?.name || "Unknown group";
}

function emailMailboxName(id) {
  const item = emailAlertsState.mailboxes.find((mailbox) => mailbox.id === id);
  return item ? (item.name || item.address) : "Unknown mailbox";
}

function emailRuleName(id) {
  return emailAlertsState.rules.find((item) => item.id === id)?.name || "Unknown rule";
}

function emailPrimaryAction() {
  const button = byId("email-primary-action");
  if (!button) return;
  const actions = {
    overview: ["Add rule", "new-rule"],
    groups: ["Add group", "new-group"],
    rules: ["Add rule", "new-rule"],
    mailboxes: ["Add mailbox", "new-mailbox"],
    activity: ["Refresh", "refresh"],
  };
  const [label, action] = actions[emailAlertsState.tab] || actions.overview;
  button.textContent = label;
  button.dataset.emailAction = action;
}

function emailSetTab(tab) {
  if (!["overview", "groups", "rules", "mailboxes", "activity"].includes(tab)) {
    tab = "overview";
  }
  emailAlertsState.tab = tab;
  for (const button of document.querySelectorAll("[data-email-tab]")) {
    const active = button.dataset.emailTab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  }
  emailPrimaryAction();
  emailRender();
}

async function emailLoad(force = false) {
  if (emailAlertsState.loading) return;
  if (emailAlertsState.loaded && !force) {
    emailRender();
    return;
  }
  emailAlertsState.loading = true;
  byId("email-alerts-loading").hidden = false;
  byId("email-alerts-error").hidden = true;
  try {
    const [overview, groups, rules, mailboxes, activity] = await Promise.all([
      request("/email-overview"),
      request("/email-groups"),
      request("/email-rules"),
      request("/email-mailboxes"),
      request("/email-activity"),
    ]);
    emailAlertsState.overview = overview.overview || {};
    emailAlertsState.groups = groups.groups || [];
    emailAlertsState.rules = rules.rules || [];
    emailAlertsState.mailboxes = mailboxes.mailboxes || [];
    emailAlertsState.activity = activity || { messages: [], processing: [] };
    emailAlertsState.loaded = true;
    emailRender();
  } catch (error) {
    const box = byId("email-alerts-error");
    box.textContent = error.message || "Email Alerts could not be loaded.";
    box.hidden = false;
  } finally {
    emailAlertsState.loading = false;
    byId("email-alerts-loading").hidden = true;
  }
}

function emailRender() {
  const root = byId("email-alerts-root");
  if (!root) return;
  if (!emailAlertsState.loaded) {
    root.replaceChildren();
    return;
  }
  const renderers = {
    overview: emailRenderOverview,
    groups: emailRenderGroups,
    rules: emailRenderRules,
    mailboxes: emailRenderMailboxes,
    activity: emailRenderActivity,
  };
  root.replaceChildren(renderers[emailAlertsState.tab]());
}

function emailMetric(label, value, copy) {
  return element("article", { className: "email-metric-card" }, [
    element("span", { text: label }),
    element("strong", { text: value }),
    element("small", { text: copy }),
  ]);
}

function emailRenderOverview() {
  const data = emailAlertsState.overview || {};
  const classifications = data.classifications || {};
  const metrics = element("div", { className: "email-metric-grid" }, [
    emailMetric("Mailboxes", data.mailboxes || 0, `${data.healthy_mailboxes || 0} healthy`),
    emailMetric("Groups", data.groups || 0, `${data.enabled_groups || 0} enabled`),
    emailMetric("Rules", data.rules || 0, `${data.enabled_rules || 0} enabled`),
    emailMetric("Recent messages", data.recent_messages || 0, "Latest retained mailbox metadata"),
  ]);

  const classificationRows = element("div", { className: "email-classification-grid" });
  for (const [key, label] of EMAIL_CLASSIFICATIONS) {
    classificationRows.append(
      element("div", { className: "email-classification-card" }, [
        emailClassificationBadge(key),
        element("strong", { text: classifications[key] || 0 }),
        element("small", { text: "Recent processing records" }),
      ]),
    );
  }

  const mailboxHealth = element("div", { className: "email-overview-list" });
  if (!emailAlertsState.mailboxes.length) {
    empty(mailboxHealth, "No mailboxes connected", "Add Gmail, Microsoft 365, or IMAP to start receiving email metadata.");
  } else {
    for (const mailbox of emailAlertsState.mailboxes.slice(0, 6)) {
      mailboxHealth.append(
        element("div", { className: "email-overview-row" }, [
          element("div", {}, [
            element("strong", { text: mailbox.name || mailbox.address }),
            element("small", { text: `${emailProviderLabel(mailbox.provider)} · ${mailbox.address}` }),
          ]),
          emailConnectionBadge(mailbox.connection_state, mailbox.enabled),
        ]),
      );
    }
  }

  const recent = element("div", { className: "email-overview-list" });
  const messages = emailAlertsState.activity.messages || [];
  if (!messages.length) {
    empty(recent, "No email activity yet", "Connected mailboxes will appear here after their first synchronization.");
  } else {
    for (const message of messages.slice(0, 6)) {
      recent.append(
        element("div", { className: "email-overview-row" }, [
          element("div", {}, [
            element("strong", { text: message.subject || "(No subject)" }),
            element("small", { text: `${message.sender || "Unknown sender"} · ${emailMailboxName(message.mailbox_id)}` }),
          ]),
          element("span", { className: "email-time", text: relativeTime(message.received_at) }),
        ]),
      );
    }
  }

  return element("div", { className: "email-overview-stack" }, [
    metrics,
    element("section", { className: "email-overview-split" }, [
      element("article", { className: "panel email-panel" }, [
        element("div", { className: "panel-heading" }, [
          element("div", {}, [
            element("p", { className: "eyebrow", text: "Classification" }),
            element("h3", { text: "Rule outcomes" }),
            element("p", { text: "Urgent, Warning, Information, and Ignore are the only Email Alert classifications." }),
          ]),
        ]),
        classificationRows,
      ]),
      element("article", { className: "panel email-panel" }, [
        element("div", { className: "panel-heading" }, [
          element("div", {}, [
            element("p", { className: "eyebrow", text: "Connections" }),
            element("h3", { text: "Mailbox health" }),
          ]),
        ]),
        mailboxHealth,
      ]),
    ]),
    element("article", { className: "panel email-panel" }, [
      element("div", { className: "panel-heading" }, [
        element("div", {}, [
          element("p", { className: "eyebrow", text: "Latest" }),
          element("h3", { text: "Recent mailbox messages" }),
          element("p", { text: "Only searchable metadata is synchronized by default; full message content remains on demand." }),
        ]),
        element("button", {
          className: "text-button",
          text: "View activity",
          type: "button",
          dataset: { emailTab: "activity" },
        }),
      ]),
      recent,
    ]),
  ]);
}

function emailRenderGroups() {
  const container = element("div", { className: "email-card-grid" });
  if (!emailAlertsState.groups.length) {
    empty(container, "No Email Alert groups", "Groups organise related rules and control the quiet window for repeated email alerts.");
    return container;
  }
  for (const group of emailAlertsState.groups) {
    const rules = emailAlertsState.rules.filter((rule) => rule.group_id === group.id);
    const enabledRules = rules.filter((rule) => rule.enabled).length;
    const actions = element("div", { className: "email-card-actions" }, [
      element("button", {
        className: "button small secondary",
        text: "Edit",
        type: "button",
        dataset: { emailAction: "edit-group", id: group.id },
      }),
      element("button", {
        className: "button small secondary",
        text: group.enabled ? "Disable" : "Enable",
        type: "button",
        dataset: { emailAction: "toggle-group", id: group.id },
      }),
      element("button", {
        className: "button small danger",
        text: "Delete",
        type: "button",
        dataset: { emailAction: "delete-group", id: group.id },
      }),
    ]);
    container.append(
      element("article", { className: "panel email-resource-card" }, [
        element("div", { className: "email-resource-heading" }, [
          element("div", {}, [
            element("h3", { text: group.name }),
            element("p", { text: group.description || "No description" }),
          ]),
          emailBadge(group.enabled ? "Enabled" : "Disabled", group.enabled ? "state-healthy" : "state-disabled"),
        ]),
        element("div", { className: "email-resource-meta" }, [
          element("span", { text: `${rules.length} rule${rules.length === 1 ? "" : "s"}` }),
          element("span", { text: `${enabledRules} active` }),
          element("span", { text: group.quiet_window_seconds ? `${Math.round(group.quiet_window_seconds / 60)} min quiet window` : "No quiet window" }),
        ]),
        actions,
      ]),
    );
  }
  return container;
}

function emailConditionSummary(condition) {
  const field = EMAIL_RULE_FIELDS.find(([key]) => key === condition.field)?.[1] || condition.field;
  const operator = EMAIL_RULE_OPERATORS.find(([key]) => key === condition.operator)?.[1] || condition.operator;
  return `${field} ${operator.toLowerCase()} “${condition.value}”`;
}

function emailRenderRules() {
  const panel = element("div", { className: "table-panel email-table-panel" });
  if (!emailAlertsState.rules.length) {
    empty(panel, "No Email Alert rules", "Create a rule to classify mailbox messages as Urgent, Warning, Information, or Ignore.");
    return panel;
  }
  const table = element("table", { className: "email-rules-table" });
  const head = element("thead");
  const headRow = element("tr");
  for (const label of ["Rule", "Group", "Classification", "Match", "Conditions", "Priority", "Status", "Actions"]) {
    headRow.append(element("th", { text: label }));
  }
  head.append(headRow);
  const body = element("tbody");
  for (const rule of emailAlertsState.rules) {
    const row = element("tr");
    row.append(
      element("td", {}, [element("strong", { text: rule.name })]),
      element("td", { text: emailGroupName(rule.group_id) }),
      element("td", {}, [emailClassificationBadge(rule.classification)]),
      element("td", { text: rule.match_mode === "all" ? "All (AND)" : "Any (OR)" }),
      element("td", {}, [
        element("div", { className: "email-condition-summary" },
          rule.conditions.map((condition) => element("span", { text: emailConditionSummary(condition) })),
        ),
      ]),
      element("td", { text: rule.priority }),
      element("td", {}, [emailBadge(rule.enabled ? "Enabled" : "Disabled", rule.enabled ? "state-healthy" : "state-disabled")]),
      element("td", {}, [
        element("div", { className: "row-actions email-row-actions" }, [
          element("button", { className: "text-button", text: "Edit", type: "button", dataset: { emailAction: "edit-rule", id: rule.id } }),
          element("button", { className: "text-button", text: rule.enabled ? "Disable" : "Enable", type: "button", dataset: { emailAction: "toggle-rule", id: rule.id } }),
          element("button", { className: "text-button danger-text", text: "Delete", type: "button", dataset: { emailAction: "delete-rule", id: rule.id } }),
        ]),
      ]),
    );
    body.append(row);
  }
  table.append(head, body);
  panel.append(element("div", { className: "table-scroll" }, [table]));
  return panel;
}

function emailProviderLabel(provider) {
  return {
    gmail: "Gmail",
    microsoft_365: "Microsoft 365",
    imap: "IMAP / IMAPS",
  }[provider] || provider;
}

function emailRenderMailboxes() {
  const container = element("div", { className: "email-card-grid" });
  if (!emailAlertsState.mailboxes.length) {
    empty(container, "No mailboxes connected", "Connect Gmail, Microsoft 365, or an IMAP/IMAPS mailbox.");
    return container;
  }
  for (const mailbox of emailAlertsState.mailboxes) {
    const actions = [
      element("button", {
        className: "button small secondary",
        text: "Sync now",
        type: "button",
        dataset: { emailAction: "sync-mailbox", id: mailbox.id },
        disabled: !mailbox.enabled,
      }),
    ];
    if (["gmail", "microsoft_365"].includes(mailbox.provider)) {
      actions.push(
        element("button", {
          className: "button small secondary",
          text: mailbox.connection_state === "healthy" ? "Reconnect" : "Connect",
          type: "button",
          dataset: { emailAction: "connect-mailbox", id: mailbox.id },
        }),
      );
    }
    actions.push(
      element("button", {
        className: "button small secondary",
        text: mailbox.enabled ? "Disable" : "Enable",
        type: "button",
        dataset: { emailAction: "toggle-mailbox", id: mailbox.id },
      }),
      element("button", {
        className: "button small danger",
        text: "Delete",
        type: "button",
        dataset: { emailAction: "delete-mailbox", id: mailbox.id },
      }),
    );

    const error = mailbox.last_error_safe
      ? element("p", { className: "email-safe-error", text: mailbox.last_error_safe })
      : null;

    container.append(
      element("article", { className: "panel email-resource-card" }, [
        element("div", { className: "email-resource-heading" }, [
          element("div", {}, [
            element("p", { className: "eyebrow", text: emailProviderLabel(mailbox.provider) }),
            element("h3", { text: mailbox.name || mailbox.address }),
            element("p", { text: mailbox.address }),
          ]),
          emailConnectionBadge(mailbox.connection_state, mailbox.enabled),
        ]),
        element("div", { className: "email-resource-meta" }, [
          element("span", { text: mailbox.secret_configured ? "Credentials configured" : "Credentials missing" }),
          element("span", { text: mailbox.last_sync_at ? `Last sync ${relativeTime(mailbox.last_sync_at)}` : "Never synchronized" }),
        ]),
        error,
        element("div", { className: "email-card-actions" }, actions),
      ]),
    );
  }
  return container;
}

function emailRenderActivity() {
  const messages = emailAlertsState.activity.messages || [];
  const panel = element("div", { className: "table-panel email-table-panel" });
  if (!messages.length) {
    empty(panel, "No Email Alert activity", "Mailbox messages will appear after synchronization. Classification activity begins when rules are evaluated.");
    return panel;
  }

  const table = element("table", { className: "email-activity-table" });
  const head = element("thead");
  const headRow = element("tr");
  for (const label of ["Received", "Mailbox", "Sender", "Subject", "Classification", "Rule", "Original"]) {
    headRow.append(element("th", { text: label }));
  }
  head.append(headRow);
  const body = element("tbody");
  for (const message of messages) {
    const processing = message.processing;
    const row = element("tr");
    const original = message.provider_deep_link
      ? element("a", {
          className: "text-button email-original-link",
          text: "Open",
          attributes: {
            href: message.provider_deep_link,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        })
      : element("span", { className: "muted", text: "Unavailable" });
    row.append(
      element("td", { text: formatTime(message.received_at) }),
      element("td", { text: emailMailboxName(message.mailbox_id) }),
      element("td", { text: message.sender || "Unknown sender" }),
      element("td", {}, [
        element("strong", { text: message.subject || "(No subject)" }),
        message.labels?.length
          ? element("small", { className: "email-labels", text: message.labels.join(" · ") })
          : null,
      ]),
      element("td", {}, [emailClassificationBadge(processing?.classification || "")]),
      element("td", { text: processing?.rule_id ? emailRuleName(processing.rule_id) : "Not evaluated" }),
      element("td", {}, [original]),
    );
    body.append(row);
  }
  table.append(head, body);
  panel.append(element("div", { className: "table-scroll" }, [table]));
  return panel;
}

function emailDialogHeading(title, copy, dialogId) {
  return element("div", { className: "modal-heading" }, [
    element("div", {}, [
      element("h2", { text: title }),
      element("p", { text: copy }),
    ]),
    element("button", {
      className: "icon-button",
      text: "×",
      type: "button",
      attributes: { "aria-label": "Close" },
      dataset: { emailAction: "close-dialog", dialog: dialogId },
    }),
  ]);
}

function emailLabel(label, control) {
  return element("label", {}, [
    element("span", { text: label }),
    control,
  ]);
}

function emailEnsureDialogs() {
  if (!byId("email-group-dialog")) {
    const dialog = element("dialog", {
      className: "modal email-dialog",
      attributes: { id: "email-group-dialog" },
    });
    const form = element("form", { className: "stack", attributes: { id: "email-group-form" } }, [
      emailDialogHeading("Email Alert group", "Organise related classification rules and optionally suppress repeats for a quiet window.", "email-group-dialog"),
      emailLabel("Name", element("input", { attributes: { id: "email-group-name", required: "", maxlength: "160" } })),
      emailLabel("Description", element("textarea", { attributes: { id: "email-group-description", rows: "3", maxlength: "1000" } })),
      emailLabel("Quiet window (minutes)", element("input", { type: "number", value: "0", attributes: { id: "email-group-quiet", min: "0", max: "10080", step: "1" } })),
      emailLabel("Status", (() => {
        const select = element("select", { attributes: { id: "email-group-enabled" } });
        select.append(emailOption("true", "Enabled"), emailOption("false", "Disabled"));
        return select;
      })()),
      element("p", { className: "form-error", attributes: { id: "email-group-error", role: "alert" }, hidden: true }),
      element("div", { className: "modal-actions" }, [
        element("button", { className: "button secondary", text: "Cancel", type: "button", dataset: { emailAction: "close-dialog", dialog: "email-group-dialog" } }),
        element("button", { className: "button primary", text: "Save group", type: "submit" }),
      ]),
    ]);
    dialog.append(form);
    document.body.append(dialog);
  }

  if (!byId("email-rule-dialog")) {
    const dialog = element("dialog", {
      className: "modal email-dialog email-rule-dialog",
      attributes: { id: "email-rule-dialog" },
    });
    const groupSelect = element("select", { attributes: { id: "email-rule-group", required: "" } });
    const classification = element("select", { attributes: { id: "email-rule-classification" } });
    for (const [key, label] of EMAIL_CLASSIFICATIONS) classification.append(emailOption(key, label));
    const matchMode = element("select", { attributes: { id: "email-rule-match-mode" } }, [
      emailOption("all", "All conditions (AND)"),
      emailOption("any", "Any condition (OR)"),
    ]);
    const form = element("form", { className: "stack", attributes: { id: "email-rule-form" } }, [
      emailDialogHeading("Email Alert rule", "Classify matching email metadata with simple, deterministic conditions.", "email-rule-dialog"),
      element("div", { className: "form-grid email-rule-grid" }, [
        emailLabel("Name", element("input", { attributes: { id: "email-rule-name", required: "", maxlength: "160" } })),
        emailLabel("Group", groupSelect),
        emailLabel("Classification", classification),
        emailLabel("Match mode", matchMode),
        emailLabel("Priority", element("input", { type: "number", value: "100", attributes: { id: "email-rule-priority", min: "0", max: "100000", step: "1" } })),
        emailLabel("Status", (() => {
          const select = element("select", { attributes: { id: "email-rule-enabled" } });
          select.append(emailOption("true", "Enabled"), emailOption("false", "Disabled"));
          return select;
        })()),
      ]),
      element("div", { className: "email-condition-editor" }, [
        element("div", { className: "email-condition-heading" }, [
          element("div", {}, [
            element("strong", { text: "Conditions" }),
            element("small", { text: "Sender, domain, recipient, subject, body, or mailbox." }),
          ]),
          element("button", { className: "button small secondary", text: "Add condition", type: "button", dataset: { emailAction: "add-condition" } }),
        ]),
        element("div", { attributes: { id: "email-rule-conditions" } }),
        element("small", { className: "email-body-rule-note", text: "Body conditions are evaluated only when message content is available. Phase 8 will retrieve content only when a body rule requires it." }),
      ]),
      element("p", { className: "form-error", attributes: { id: "email-rule-error", role: "alert" }, hidden: true }),
      element("div", { className: "modal-actions" }, [
        element("button", { className: "button secondary", text: "Cancel", type: "button", dataset: { emailAction: "close-dialog", dialog: "email-rule-dialog" } }),
        element("button", { className: "button primary", text: "Save rule", type: "submit" }),
      ]),
    ]);
    dialog.append(form);
    document.body.append(dialog);
  }

  if (!byId("email-mailbox-dialog")) {
    const dialog = element("dialog", {
      className: "modal email-dialog email-mailbox-dialog",
      attributes: { id: "email-mailbox-dialog" },
    });
    const provider = element("select", { attributes: { id: "email-mailbox-provider" } }, [
      emailOption("gmail", "Gmail"),
      emailOption("microsoft_365", "Microsoft 365 / Outlook"),
      emailOption("imap", "IMAP / IMAPS"),
    ]);
    const form = element("form", { className: "stack", attributes: { id: "email-mailbox-form" } }, [
      emailDialogHeading("Connect mailbox", "Nowlert synchronizes message metadata first and keeps credentials in the encrypted platform secret boundary.", "email-mailbox-dialog"),
      element("div", { className: "form-grid" }, [
        emailLabel("Provider", provider),
        emailLabel("Mailbox name", element("input", { attributes: { id: "email-mailbox-name", required: "", maxlength: "160", placeholder: "Operations inbox" } })),
        emailLabel("Email address", element("input", { type: "email", attributes: { id: "email-mailbox-address", required: "", maxlength: "320", placeholder: "alerts@example.com" } })),
      ]),
      element("div", { attributes: { id: "email-oauth-fields" } }, [
        element("div", { className: "form-grid" }, [
          emailLabel("OAuth client ID", element("input", { attributes: { id: "email-oauth-client-id", autocomplete: "off" } })),
          emailLabel("OAuth client secret", element("input", { type: "password", attributes: { id: "email-oauth-client-secret", autocomplete: "new-password" } })),
          emailLabel("Redirect URL", element("input", { attributes: { id: "email-oauth-redirect", readonly: "" } })),
        ]),
        element("div", { attributes: { id: "email-gmail-settings" } }, [
          emailLabel("Gmail label", element("input", { value: "INBOX", attributes: { id: "email-gmail-label", maxlength: "128" } })),
        ]),
        element("div", { className: "form-grid", attributes: { id: "email-microsoft-settings" }, hidden: true }, [
          emailLabel("Tenant", element("input", { value: "common", attributes: { id: "email-microsoft-tenant", maxlength: "128" } })),
          emailLabel("Folder", element("input", { value: "inbox", attributes: { id: "email-microsoft-folder", maxlength: "256" } })),
        ]),
      ]),
      element("div", { className: "form-grid", attributes: { id: "email-imap-fields" }, hidden: true }, [
        emailLabel("IMAP host", element("input", { attributes: { id: "email-imap-host", maxlength: "253", placeholder: "imap.example.com" } })),
        emailLabel("Port", element("input", { type: "number", value: "993", attributes: { id: "email-imap-port", min: "1", max: "65535" } })),
        emailLabel("Security", element("select", { attributes: { id: "email-imap-security" } }, [
          emailOption("ssl", "SSL / TLS"),
          emailOption("starttls", "STARTTLS"),
        ])),
        emailLabel("Folder", element("input", { value: "INBOX", attributes: { id: "email-imap-folder", maxlength: "512" } })),
        emailLabel("Username", element("input", { attributes: { id: "email-imap-username", autocomplete: "username" } })),
        emailLabel("Password / app password", element("input", { type: "password", attributes: { id: "email-imap-password", autocomplete: "new-password" } })),
      ]),
      element("p", { className: "email-mailbox-security-note", text: "OAuth and IMAP credentials are submitted once to Nowlert and stored only through the platform SecretStore. They are never returned by this API." }),
      element("p", { className: "form-error", attributes: { id: "email-mailbox-error", role: "alert" }, hidden: true }),
      element("div", { className: "modal-actions" }, [
        element("button", { className: "button secondary", text: "Cancel", type: "button", dataset: { emailAction: "close-dialog", dialog: "email-mailbox-dialog" } }),
        element("button", { className: "button primary", text: "Add mailbox", type: "submit" }),
      ]),
    ]);
    dialog.append(form);
    document.body.append(dialog);
    provider.addEventListener("change", emailMailboxProviderFields);
  }
}

function emailMailboxProviderFields() {
  const provider = byId("email-mailbox-provider")?.value || "gmail";
  byId("email-oauth-fields").hidden = provider === "imap";
  byId("email-imap-fields").hidden = provider !== "imap";
  byId("email-gmail-settings").hidden = provider !== "gmail";
  byId("email-microsoft-settings").hidden = provider !== "microsoft_365";
  if (provider === "imap") {
    const security = byId("email-imap-security").value;
    byId("email-imap-port").value = security === "ssl" ? "993" : "143";
  }
}

function emailOpenGroup(group = null) {
  emailEnsureDialogs();
  const form = byId("email-group-form");
  form.dataset.groupId = group?.id || "";
  byId("email-group-name").value = group?.name || "";
  byId("email-group-description").value = group?.description || "";
  byId("email-group-quiet").value = String(Math.round((group?.quiet_window_seconds || 0) / 60));
  byId("email-group-enabled").value = String(group?.enabled !== false);
  byId("email-group-error").hidden = true;
  byId("email-group-dialog").showModal();
  byId("email-group-name").focus();
}

function emailRefreshRuleGroupOptions(selected = "") {
  const select = byId("email-rule-group");
  select.replaceChildren();
  for (const group of emailAlertsState.groups) {
    select.append(emailOption(group.id, group.name));
  }
  if (selected) select.value = selected;
}

function emailAddCondition(condition = null) {
  const container = byId("email-rule-conditions");
  const row = element("div", { className: "email-condition-row" });
  const field = element("select", { dataset: { emailCondition: "field" } });
  for (const [key, label] of EMAIL_RULE_FIELDS) field.append(emailOption(key, label));
  const operator = element("select", { dataset: { emailCondition: "operator" } });
  for (const [key, label] of EMAIL_RULE_OPERATORS) operator.append(emailOption(key, label));
  const value = element("input", {
    dataset: { emailCondition: "value" },
    attributes: { required: "", maxlength: "2000", placeholder: "Value" },
  });
  const remove = element("button", {
    className: "icon-button",
    text: "×",
    type: "button",
    title: "Remove condition",
    attributes: { "aria-label": "Remove condition" },
    dataset: { emailAction: "remove-condition" },
  });
  row.append(field, operator, value, remove);
  container.append(row);
  field.value = condition?.field || "sender";
  operator.value = condition?.operator || "contains";
  value.value = condition?.value || "";
}

function emailOpenRule(rule = null) {
  emailEnsureDialogs();
  if (!emailAlertsState.groups.length) {
    toast("Create an Email Alert group before adding a rule.", "warning");
    emailSetTab("groups");
    return;
  }
  const form = byId("email-rule-form");
  form.dataset.ruleId = rule?.id || "";
  emailRefreshRuleGroupOptions(rule?.group_id || emailAlertsState.groups[0].id);
  byId("email-rule-name").value = rule?.name || "";
  byId("email-rule-classification").value = rule?.classification || "warning";
  byId("email-rule-match-mode").value = rule?.match_mode || "all";
  byId("email-rule-priority").value = String(rule?.priority ?? 100);
  byId("email-rule-enabled").value = String(rule?.enabled !== false);
  byId("email-rule-conditions").replaceChildren();
  const conditions = rule?.conditions?.length ? rule.conditions : [null];
  for (const condition of conditions) emailAddCondition(condition);
  byId("email-rule-error").hidden = true;
  byId("email-rule-dialog").showModal();
  byId("email-rule-name").focus();
}

function emailOpenMailbox() {
  emailEnsureDialogs();
  byId("email-mailbox-form").reset();
  byId("email-mailbox-provider").value = "gmail";
  byId("email-gmail-label").value = "INBOX";
  byId("email-microsoft-tenant").value = "common";
  byId("email-microsoft-folder").value = "inbox";
  byId("email-imap-port").value = "993";
  byId("email-imap-security").value = "ssl";
  byId("email-imap-folder").value = "INBOX";
  byId("email-oauth-redirect").value = `${window.location.origin}/ui/`;
  byId("email-mailbox-error").hidden = true;
  emailMailboxProviderFields();
  byId("email-mailbox-dialog").showModal();
}

function emailReadConditions() {
  const rows = [...byId("email-rule-conditions").querySelectorAll(".email-condition-row")];
  if (!rows.length) throw new Error("At least one condition is required.");
  return rows.map((row) => ({
    field: row.querySelector('[data-email-condition="field"]').value,
    operator: row.querySelector('[data-email-condition="operator"]').value,
    value: row.querySelector('[data-email-condition="value"]').value.trim(),
  }));
}

async function emailSaveGroup(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const id = form.dataset.groupId || "";
  const error = byId("email-group-error");
  error.hidden = true;
  const body = {
    name: byId("email-group-name").value.trim(),
    description: byId("email-group-description").value.trim(),
    quiet_window_seconds: Number(byId("email-group-quiet").value || 0) * 60,
    enabled: byId("email-group-enabled").value === "true",
  };
  try {
    await request(id ? `/email-groups/${id}` : "/email-groups", {
      method: id ? "PATCH" : "POST",
      body,
    });
    byId("email-group-dialog").close();
    toast(id ? "Email Alert group updated." : "Email Alert group created.", "success");
    await emailLoad(true);
  } catch (requestError) {
    error.textContent = requestError.message || "The group could not be saved.";
    error.hidden = false;
  }
}

async function emailSaveRule(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const id = form.dataset.ruleId || "";
  const error = byId("email-rule-error");
  error.hidden = true;
  try {
    const body = {
      name: byId("email-rule-name").value.trim(),
      group_id: byId("email-rule-group").value,
      classification: byId("email-rule-classification").value,
      match_mode: byId("email-rule-match-mode").value,
      priority: Number(byId("email-rule-priority").value || 100),
      enabled: byId("email-rule-enabled").value === "true",
      conditions: emailReadConditions(),
    };
    await request(id ? `/email-rules/${id}` : "/email-rules", {
      method: id ? "PATCH" : "POST",
      body,
    });
    byId("email-rule-dialog").close();
    toast(id ? "Email Alert rule updated." : "Email Alert rule created.", "success");
    await emailLoad(true);
  } catch (requestError) {
    error.textContent = requestError.message || "The rule could not be saved.";
    error.hidden = false;
  }
}

async function emailSaveMailbox(event) {
  event.preventDefault();
  const error = byId("email-mailbox-error");
  error.hidden = true;
  const provider = byId("email-mailbox-provider").value;
  const body = {
    provider,
    name: byId("email-mailbox-name").value.trim(),
    address: byId("email-mailbox-address").value.trim(),
    enabled: true,
  };
  if (provider === "gmail") {
    body.settings = {
      label: byId("email-gmail-label").value.trim() || "INBOX",
    };
    body.credential = {
      client_id: byId("email-oauth-client-id").value.trim(),
      client_secret: byId("email-oauth-client-secret").value,
      redirect_uri: byId("email-oauth-redirect").value,
    };
  } else if (provider === "microsoft_365") {
    body.settings = {
      tenant: byId("email-microsoft-tenant").value.trim() || "common",
      folder: byId("email-microsoft-folder").value.trim() || "inbox",
    };
    body.credential = {
      client_id: byId("email-oauth-client-id").value.trim(),
      client_secret: byId("email-oauth-client-secret").value,
      redirect_uri: byId("email-oauth-redirect").value,
    };
  } else {
    body.settings = {
      host: byId("email-imap-host").value.trim(),
      port: Number(byId("email-imap-port").value),
      security: byId("email-imap-security").value,
      folder: byId("email-imap-folder").value.trim() || "INBOX",
    };
    body.credential = {
      username: byId("email-imap-username").value,
      password: byId("email-imap-password").value,
    };
  }
  try {
    const response = await request("/email-mailboxes", { method: "POST", body });
    byId("email-mailbox-dialog").close();
    toast("Mailbox added.", "success");
    await emailLoad(true);
    if (["gmail", "microsoft_365"].includes(response.mailbox.provider)) {
      const connect = await request(`/email-mailboxes/${response.mailbox.id}/oauth-start`, {
        method: "POST",
        body: {},
      });
      window.location.assign(connect.oauth.authorization_url);
    }
  } catch (requestError) {
    error.textContent = requestError.message || "The mailbox could not be added.";
    error.hidden = false;
  }
}

async function emailAction(action, id, node) {
  try {
    if (action === "new-group") return emailOpenGroup();
    if (action === "new-rule") return emailOpenRule();
    if (action === "new-mailbox") return emailOpenMailbox();
    if (action === "refresh") return emailLoad(true);
    if (action === "close-dialog") {
      byId(node.dataset.dialog)?.close();
      return;
    }
    if (action === "add-condition") {
      emailAddCondition();
      return;
    }
    if (action === "remove-condition") {
      const row = node.closest(".email-condition-row");
      if (byId("email-rule-conditions").children.length > 1) row?.remove();
      return;
    }

    if (action === "edit-group") {
      return emailOpenGroup(emailAlertsState.groups.find((item) => item.id === id));
    }
    if (action === "toggle-group") {
      const item = emailAlertsState.groups.find((group) => group.id === id);
      await request(`/email-groups/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      await emailLoad(true);
      return;
    }
    if (action === "delete-group") {
      const item = emailAlertsState.groups.find((group) => group.id === id);
      if (!window.confirm(`Delete “${item?.name || "this group"}” and all rules in it?`)) return;
      await request(`/email-groups/${id}`, { method: "DELETE" });
      toast("Email Alert group deleted.", "success");
      await emailLoad(true);
      return;
    }

    if (action === "edit-rule") {
      return emailOpenRule(emailAlertsState.rules.find((item) => item.id === id));
    }
    if (action === "toggle-rule") {
      const item = emailAlertsState.rules.find((rule) => rule.id === id);
      await request(`/email-rules/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      await emailLoad(true);
      return;
    }
    if (action === "delete-rule") {
      const item = emailAlertsState.rules.find((rule) => rule.id === id);
      if (!window.confirm(`Delete rule “${item?.name || "this rule"}”?`)) return;
      await request(`/email-rules/${id}`, { method: "DELETE" });
      toast("Email Alert rule deleted.", "success");
      await emailLoad(true);
      return;
    }

    if (action === "sync-mailbox") {
      node.disabled = true;
      const response = await request(`/email-mailboxes/${id}/sync`, { method: "POST", body: {} });
      toast(`Mailbox synchronized: ${response.sync.created} new, ${response.sync.duplicates} duplicate.`, "success");
      await emailLoad(true);
      return;
    }
    if (action === "connect-mailbox") {
      const response = await request(`/email-mailboxes/${id}/oauth-start`, { method: "POST", body: {} });
      window.location.assign(response.oauth.authorization_url);
      return;
    }
    if (action === "toggle-mailbox") {
      const item = emailAlertsState.mailboxes.find((mailbox) => mailbox.id === id);
      await request(`/email-mailboxes/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      await emailLoad(true);
      return;
    }
    if (action === "delete-mailbox") {
      const item = emailAlertsState.mailboxes.find((mailbox) => mailbox.id === id);
      if (!window.confirm(`Delete mailbox “${item?.name || item?.address || "this mailbox"}” and its retained Email Alert data?`)) return;
      await request(`/email-mailboxes/${id}`, { method: "DELETE" });
      toast("Mailbox deleted.", "success");
      await emailLoad(true);
    }
  } catch (error) {
    toast(error.message || "Email Alerts action failed.", "danger");
  } finally {
    if (node && action === "sync-mailbox") node.disabled = false;
  }
}

async function emailHandleOAuthReturn() {
  if (!state.user) return;
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const oauthState = params.get("state");
  const providerError = params.get("error");
  if (!code && !providerError) return;
  try {
    if (providerError) {
      toast("Mailbox authorization was cancelled or denied.", "danger");
    } else if (oauthState) {
      await request("/email-mailboxes/oauth-complete", {
        method: "POST",
        body: { code, state: oauthState },
      });
      toast("Mailbox authorization completed.", "success");
    }
  } catch (error) {
    toast(error.message || "Mailbox authorization failed.", "danger");
  } finally {
    for (const key of ["code", "state", "scope", "authuser", "prompt", "error", "error_description", "session_state"]) {
      params.delete(key);
    }
    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ""}#email-alerts`;
    window.history.replaceState({ nowlertView: "email-alerts" }, "", url);
    navigate("email-alerts", "replace");
    await emailLoad(true);
  }
}

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-email-tab]");
  if (tab) {
    emailSetTab(tab.dataset.emailTab);
    return;
  }
  const action = event.target.closest("[data-email-action]");
  if (action) {
    event.preventDefault();
    void emailAction(action.dataset.emailAction, action.dataset.id || "", action);
  }
});

emailEnsureDialogs();
byId("email-group-form")?.addEventListener("submit", emailSaveGroup);
byId("email-rule-form")?.addEventListener("submit", emailSaveRule);
byId("email-mailbox-form")?.addEventListener("submit", emailSaveMailbox);
byId("email-imap-security")?.addEventListener("change", emailMailboxProviderFields);

const emailOriginalNavigate = navigate;
navigate = function navigateEmailAlerts(view, historyMode = "push") {
  const result = emailOriginalNavigate(view, historyMode);
  if (state.currentView === "email-alerts") void emailLoad();
  return result;
};

const emailOriginalShowApp = showApp;
showApp = function showAppWithEmailOAuth(session) {
  const result = emailOriginalShowApp(session);
  window.setTimeout(() => void emailHandleOAuthReturn(), 0);
  return result;
};
