"use strict";

const emailAlertsState = {
  tab: "rules",
  loading: false,
  loaded: false,
  overview: null,
  groups: [],
  rules: [],
  mailboxes: [],
  providers: {},
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

function emailSetTab(tab) {
  if (!["rules", "mailboxes", "activity"].includes(tab)) {
    tab = "rules";
  }
  emailAlertsState.tab = tab;
  for (const button of document.querySelectorAll("[data-email-tab]")) {
    const active = button.dataset.emailTab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  }
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
    const [overview, groups, rules, mailboxes, providers, activity] = await Promise.all([
      request("/email-overview"),
      request("/email-groups"),
      request("/email-rules"),
      request("/email-mailboxes"),
      request("/email-mailbox-providers"),
      request("/email-activity"),
    ]);
    emailAlertsState.overview = overview.overview || {};
    emailAlertsState.groups = groups.groups || [];
    emailAlertsState.rules = rules.rules || [];
    emailAlertsState.mailboxes = mailboxes.mailboxes || [];
    emailAlertsState.providers = providers.providers || {};
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

function emailRenderRuleTable() {
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

function emailRenderRules() {
  const stats = emailAlertsState.overview || {};
  const classifications = stats.classifications || {};
  const enabledGroups = emailAlertsState.groups.filter((group) => group.enabled).length;
  const enabledRules = emailAlertsState.rules.filter((rule) => rule.enabled).length;

  const classificationRows = element("div", { className: "email-classification-grid" });
  for (const [key] of EMAIL_CLASSIFICATIONS) {
    classificationRows.append(
      element("div", { className: "email-classification-card" }, [
        emailClassificationBadge(key),
        element("strong", { text: classifications[key] || 0 }),
        element("small", { text: "Recent processing records" }),
      ]),
    );
  }

  return element("div", { className: "email-workspace-stack" }, [
    element("article", { className: "panel email-panel email-config-panel" }, [
      element("div", { className: "panel-heading" }, [
        element("div", {}, [
          element("p", { className: "eyebrow", text: "Organisation" }),
          element("h3", { text: "Groups" }),
          element("p", {
            text: `${emailAlertsState.groups.length} group${emailAlertsState.groups.length === 1 ? "" : "s"} · ${enabledGroups} enabled. Groups organise related rules and their quiet windows.`,
          }),
        ]),
        element("button", {
          className: "button primary",
          text: "+ Add group",
          type: "button",
          dataset: { emailAction: "new-group" },
        }),
      ]),
      emailRenderGroups(),
    ]),
    element("article", { className: "panel email-panel email-config-panel" }, [
      element("div", { className: "panel-heading" }, [
        element("div", {}, [
          element("p", { className: "eyebrow", text: "Classification" }),
          element("h3", { text: "Rules" }),
          element("p", {
            text: `${emailAlertsState.rules.length} rule${emailAlertsState.rules.length === 1 ? "" : "s"} · ${enabledRules} enabled. Classify matching email as Urgent, Warning, Information, or Ignore.`,
          }),
        ]),
        element("button", {
          className: "button primary",
          text: "+ Add rule",
          type: "button",
          dataset: { emailAction: "new-rule" },
          disabled: emailAlertsState.groups.length === 0,
          attributes: {
            title: emailAlertsState.groups.length
              ? "Add Email Alert rule"
              : "Add a group before creating a rule",
          },
        }),
      ]),
      classificationRows,
      emailRenderRuleTable(),
    ]),
  ]);
}

function emailProviderLabel(provider) {
  return {
    gmail: "Gmail",
    microsoft_365: "Microsoft 365",
    imap: "IMAP / IMAPS",
  }[provider] || provider;
}

function emailProviderConfigured(provider) {
  if (provider === "imap") return true;
  return emailAlertsState.providers?.[provider]?.configured === true;
}

function emailDefaultMailboxProvider() {
  if (emailProviderConfigured("gmail")) return "gmail";
  if (emailProviderConfigured("microsoft_365")) return "microsoft_365";
  return "imap";
}

function emailMailboxConnectButton(provider, label, primary = false) {
  const configured = emailProviderConfigured(provider);
  return element("button", {
    className: `button ${primary ? "primary" : "secondary"}`,
    text: label,
    type: "button",
    dataset: {
      emailAction: "new-mailbox",
      provider,
    },
    disabled: !configured,
    attributes: {
      title: configured
        ? `Connect ${emailProviderLabel(provider)}`
        : `${emailProviderLabel(provider)} OAuth is not configured on this Nowlert instance`,
    },
  });
}

function emailMailboxEmptyState(compact = false) {
  return element("div", {
    className: `empty-state email-mailbox-connect-empty${compact ? " compact" : ""}`,
  }, [
    element("strong", { text: "No mailboxes connected" }),
    element("span", {
      text: "Connect a mailbox so Nowlert can synchronize alert metadata and classify incoming messages.",
    }),
    element("div", { className: "email-mailbox-connect-actions" }, [
      emailMailboxConnectButton("gmail", "Connect Gmail", true),
      emailMailboxConnectButton("microsoft_365", "Connect Microsoft 365"),
      emailMailboxConnectButton("imap", "Connect IMAP / IMAPS"),
    ]),
    (
      emailProviderConfigured("gmail") && emailProviderConfigured("microsoft_365")
        ? null
        : element("small", {
            className: "email-mailbox-provider-status",
            text: "OAuth providers are enabled once the Nowlert administrator configures the instance application credentials.",
          })
    ),
  ]);
}

function emailRenderMailboxCards() {
  const container = element("div", { className: "email-card-grid" });
  if (!emailAlertsState.mailboxes.length) {
    container.classList.add("email-mailbox-connect-grid");
    container.replaceChildren(emailMailboxEmptyState(false));
    return container;
  }
  for (const mailbox of emailAlertsState.mailboxes) {
    const owned = String(mailbox.owner_user_id || "") === String(state.user?.id || "");
    const editable = owned || state.user?.role === "admin";
    const oauthProvider = ["gmail", "microsoft_365"].includes(mailbox.provider);
    const syncReady = editable && mailbox.enabled && (
      !oauthProvider
      || ["healthy", "degraded"].includes(mailbox.connection_state)
    );
    const actions = [];
    if (editable) {
      actions.push(
        element("button", {
          className: "button small secondary",
          text: "Edit",
          type: "button",
          dataset: { emailAction: "edit-mailbox", id: mailbox.id },
        }),
        element("button", {
          className: "button small secondary",
          text: "Sync now",
          type: "button",
          dataset: { emailAction: "sync-mailbox", id: mailbox.id },
          disabled: !syncReady,
          attributes: {
            title: syncReady
              ? "Synchronize mailbox metadata now"
              : (
                oauthProvider
                  ? "Connect and authorize this mailbox before synchronizing it"
                  : "Enable this mailbox before synchronizing it"
              ),
          },
        }),
      );
      if (oauthProvider) {
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
    }

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
          element("button", {
            className: `badge status-button ${mailbox.shared ? "success" : "warning"}`,
            text: mailbox.shared ? "Shared" : "Private",
            type: "button",
            disabled: !owned,
            dataset: owned
              ? { emailAction: "toggle-mailbox-shared", id: mailbox.id }
              : {},
            attributes: {
              title: owned
                ? (mailbox.shared ? "Make this mailbox private" : "Share this mailbox with other users")
                : "Only the mailbox owner can change visibility",
            },
          }),
          !editable ? emailBadge("View only", "state-disabled") : null,
          editable
            ? element("span", { text: mailbox.secret_configured ? "Credentials configured" : "Credentials missing" })
            : null,
          element("span", { text: mailbox.last_sync_at ? `Last sync ${relativeTime(mailbox.last_sync_at)}` : "Never synchronized" }),
        ]),
        error,
        element("div", { className: "email-card-actions" }, actions),
      ]),
    );
  }
  return container;
}

function emailRenderMailboxes() {
  const mailboxes = emailAlertsState.mailboxes;
  const healthy = mailboxes.filter(
    (mailbox) => mailbox.enabled && mailbox.connection_state === "healthy",
  ).length;
  const attention = mailboxes.filter(
    (mailbox) => mailbox.enabled && mailbox.connection_state !== "healthy",
  ).length;
  const shared = mailboxes.filter((mailbox) => mailbox.shared).length;

  const metrics = element("div", { className: "email-metric-grid" }, [
    emailMetric(
      "Mailboxes",
      mailboxes.length,
      "Visible to this account",
    ),
    emailMetric(
      "Healthy",
      healthy,
      "Background synchronization operating",
    ),
    emailMetric(
      "Needs attention",
      attention,
      "Enabled mailbox connections not healthy",
    ),
    emailMetric(
      "Shared",
      shared,
      "Visible to other Nowlert users",
    ),
  ]);

  return element("div", { className: "email-workspace-stack" }, [
    metrics,
    element("article", { className: "panel email-panel email-config-panel" }, [
      element("div", { className: "panel-heading" }, [
        element("div", {}, [
          element("p", { className: "eyebrow", text: "Connections" }),
          element("h3", { text: "Mailboxes" }),
          element("p", {
            text: "Connection health, synchronization state, credentials, and Private/Shared visibility are managed here.",
          }),
        ]),
        element("button", {
          className: "button primary",
          text: "+ Connect mailbox",
          type: "button",
          dataset: { emailAction: "new-mailbox" },
        }),
      ]),
      emailRenderMailboxCards(),
    ]),
  ]);
}

function emailWhyExplanation(processing) {
  if (!processing) {
    return element("span", { className: "muted", text: "No processing record" });
  }
  const details = processing.details || {};
  const matched = Array.isArray(details.matched_conditions)
    ? details.matched_conditions
    : [];
  const items = [];
  if (processing.group_id) {
    items.push(
      element("strong", {
        text: `${emailGroupName(processing.group_id)} · ${processing.rule_id ? emailRuleName(processing.rule_id) : "No rule"}`,
      }),
    );
  }
  if (matched.length) {
    const summary = matched
      .filter((item) => item && item.matched !== false)
      .slice(0, 3)
      .map((item) => emailConditionSummary(item))
      .join(" · ");
    if (summary) items.push(element("span", { text: summary }));
  } else if (details.reason) {
    items.push(
      element("span", {
        text: String(details.reason).replaceAll("_", " "),
      }),
    );
  }
  if (details.resulting_severity) {
    items.push(
      element("small", {
        text: `Resulting severity: ${capitalize(details.resulting_severity)}`,
      }),
    );
  }
  if (!items.length) {
    items.push(element("span", { text: processing.action || "Processed" }));
  }
  return element("div", { className: "email-why" }, items);
}

function emailActivityMessage(id) {
  return (emailAlertsState.activity.messages || [])
    .find((item) => item.id === id);
}

function emailOpenRuleFromActivity(message) {
  if (!message) return;
  const processing = message.processing || {};
  let field = "subject";
  let operator = "contains";
  let value = message.subject || "";
  if (message.sender_domain) {
    field = "sender_domain";
    operator = "equals";
    value = message.sender_domain;
  } else if (message.sender) {
    field = "sender";
    operator = "equals";
    value = message.sender;
  }
  const classification = ["urgent", "warning", "information"].includes(processing.classification)
    ? processing.classification
    : "warning";
  const groupId = emailAlertsState.groups.some((item) => item.id === processing.group_id)
    ? processing.group_id
    : (emailAlertsState.groups[0]?.id || "");
  emailOpenRule({
    id: "",
    group_id: groupId,
    name: `Alert like: ${(message.subject || message.sender || "email").slice(0, 120)}`,
    classification,
    match_mode: "all",
    priority: 100,
    enabled: true,
    conditions: [{ field, operator, value }],
  });
}

function emailRenderActivityTable() {
  const messages = emailAlertsState.activity.messages || [];
  const panel = element("div", { className: "table-panel email-table-panel" });
  if (!messages.length) {
    empty(
      panel,
      "No Email Alert activity",
      "Only email that Nowlert evaluated, suppressed, ignored, promoted, replayed, or failed is shown here. This is not a mailbox replica.",
    );
    return panel;
  }

  const table = element("table", { className: "email-activity-table" });
  const head = element("thead");
  const headRow = element("tr");
  for (const label of ["Received", "Mailbox", "Sender", "Subject", "Classification", "Why Nowlert reacted", "Original", "Actions"]) {
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
          text: "Open Original Email",
          attributes: {
            href: message.provider_deep_link,
            target: "_blank",
            rel: "noopener noreferrer",
          },
        })
      : element("span", { className: "muted", text: "Unavailable" });

    const actions = [
      element("button", {
        className: "text-button",
        text: "Preview",
        type: "button",
        dataset: { emailAction: "preview-message", id: message.id },
      }),
      processing?.rule_id
        ? element("button", {
            className: "text-button",
            text: "Edit Rule",
            type: "button",
            dataset: { emailAction: "edit-activity-rule", id: message.id },
          })
        : null,
      element("button", {
        className: "text-button",
        text: "Alert me like this",
        type: "button",
        dataset: { emailAction: "alert-like-this", id: message.id },
      }),
      element("button", {
        className: "text-button",
        text: "Mute Similar",
        type: "button",
        dataset: { emailAction: "mute-similar", id: message.id },
      }),
      message.sender
        ? element("button", {
            className: "text-button",
            text: "Ignore Sender",
            type: "button",
            dataset: { emailAction: "ignore-sender", id: message.id },
          })
        : null,
      processing?.rule_id
        ? element("button", {
            className: "text-button",
            text: "Change Severity",
            type: "button",
            dataset: { emailAction: "change-severity", id: message.id },
          })
        : null,
      element("button", {
        className: "text-button",
        text: "Reprocess",
        type: "button",
        dataset: { emailAction: "reprocess-message", id: message.id },
      }),
      element("button", {
        className: "text-button",
        text: "Force replay",
        type: "button",
        dataset: { emailAction: "force-reprocess-message", id: message.id },
      }),
    ].filter(Boolean);

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
      element("td", {}, [emailWhyExplanation(processing)]),
      element("td", {}, [original]),
      element("td", {}, [
        element("div", { className: "row-actions email-row-actions email-activity-actions" }, actions),
      ]),
    );
    body.append(row);
  }
  table.append(head, body);
  panel.append(
    element("p", {
      className: "email-activity-scope-note",
      text: "Activity contains only messages that participated in Nowlert processing. Message previews are sanitized and attachments are never retained.",
    }),
    element("div", { className: "table-scroll" }, [table]),
  );
  return panel;
}

function emailRenderActivity() {
  return element("article", { className: "panel email-panel email-config-panel" }, [
    element("div", { className: "panel-heading" }, [
      element("div", {}, [
        element("p", { className: "eyebrow", text: "Processing" }),
        element("h3", { text: "Activity" }),
        element("p", {
          text: "Review only email that participated in Nowlert processing; this is not a mailbox replica.",
        }),
      ]),
      element("button", {
        className: "button secondary",
        text: "Refresh",
        type: "button",
        dataset: { emailAction: "refresh" },
      }),
    ]),
    emailRenderActivityTable(),
  ]);
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
        element("small", { className: "email-body-rule-note", text: "Body conditions retrieve message content only when an enabled body rule requires it. Attachments are never used for matching." }),
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
        emailLabel("Visibility", element("select", { attributes: { id: "email-mailbox-shared" } }, [
          emailOption("false", "Private"),
          emailOption("true", "Shared"),
        ])),
      ]),
      element("div", { className: "form-grid", attributes: { id: "email-imap-fields" }, hidden: true }, [
        emailLabel("IMAP host", element("input", { attributes: { id: "email-imap-host", maxlength: "253", placeholder: "imap.example.com" } })),
        emailLabel("Port", element("input", { type: "number", value: "993", attributes: { id: "email-imap-port", min: "1", max: "65535" } })),
        emailLabel("Security", element("select", { attributes: { id: "email-imap-security" } }, [
          emailOption("ssl", "SSL / TLS"),
          emailOption("starttls", "STARTTLS"),
        ])),
        emailLabel("Username", element("input", { attributes: { id: "email-imap-username", autocomplete: "username" } })),
        emailLabel("Password / app password", element("input", { type: "password", attributes: { id: "email-imap-password", autocomplete: "new-password" } })),
      ]),
      element("div", {
        className: "email-mailbox-folder-editor",
        attributes: { id: "email-mailbox-folder-editor" },
        hidden: true,
      }, [
        emailLabel("Folder", element("select", {
          attributes: { id: "email-mailbox-folder" },
        })),
        element("div", { className: "email-mailbox-folder-actions" }, [
          element("button", {
            className: "button small secondary",
            text: "Scan folders",
            type: "button",
            dataset: { emailAction: "scan-mailbox-folders" },
            attributes: { id: "email-mailbox-folder-scan" },
          }),
          element("small", {
            className: "muted",
            text: "Folders are read directly from the connected mailbox and are never guessed.",
            attributes: { id: "email-mailbox-folder-help" },
          }),
        ]),
      ]),
      element("p", {
        className: "email-mailbox-provider-hint",
        attributes: { id: "email-mailbox-provider-hint" },
        text: "After saving this connection, Nowlert redirects you to Google to sign in and grant read-only Gmail access.",
      }),
      element("p", { className: "email-mailbox-security-note", text: "For Gmail and Microsoft 365, Nowlert stores only the mailbox authorization tokens in the owner-scoped SecretStore. OAuth application credentials are configured once by the Nowlert administrator and are never requested from mailbox users. IMAP credentials are stored in the same secret boundary." }),
      element("p", { className: "form-error", attributes: { id: "email-mailbox-error", role: "alert" }, hidden: true }),
      element("div", { className: "modal-actions" }, [
        element("button", { className: "button secondary", text: "Cancel", type: "button", dataset: { emailAction: "close-dialog", dialog: "email-mailbox-dialog" } }),
        element("button", {
          className: "button primary",
          text: "Continue to Google",
          type: "submit",
          attributes: { id: "email-mailbox-submit" },
        }),
      ]),
    ]);
    dialog.append(form);
    document.body.append(dialog);
    provider.addEventListener("change", emailMailboxProviderFields);
  }
}

function emailEnsurePhase9Dialogs() {
  if (!byId("email-preview-dialog")) {
    const dialog = element("dialog", {
      className: "modal email-dialog email-preview-dialog",
      attributes: { id: "email-preview-dialog" },
    });
    const frame = element("iframe", {
      className: "email-preview-frame",
      attributes: {
        id: "email-preview-frame",
        title: "Sanitized email preview",
        sandbox: "",
        referrerpolicy: "no-referrer",
      },
    });
    dialog.append(
      emailDialogHeading(
        "Sanitized email preview",
        "Active content, remote images and attachment payloads are blocked before this preview reaches your browser.",
        "email-preview-dialog",
      ),
      element("div", {
        className: "email-preview-security",
        attributes: { id: "email-preview-security" },
      }),
      frame,
      element("div", { className: "email-preview-attachments" }, [
        element("strong", { text: "Attachments" }),
        element("div", { attributes: { id: "email-preview-attachments" } }),
      ]),
      element("div", { className: "modal-actions" }, [
        element("button", {
          className: "button secondary",
          text: "Close",
          type: "button",
          dataset: { emailAction: "close-dialog", dialog: "email-preview-dialog" },
        }),
      ]),
    );
    document.body.append(dialog);
  }

  if (!byId("email-severity-dialog")) {
    const dialog = element("dialog", {
      className: "modal email-dialog email-severity-dialog",
      attributes: { id: "email-severity-dialog" },
    });
    const select = element("select", {
      attributes: { id: "email-severity-value" },
    }, [
      emailOption("urgent", "Urgent"),
      emailOption("warning", "Warning"),
      emailOption("information", "Information"),
    ]);
    const form = element("form", {
      className: "stack",
      attributes: { id: "email-severity-form" },
    }, [
      emailDialogHeading(
        "Change rule severity",
        "This updates the matched rule for future email. Reprocess the current Activity item separately if you need to apply the new severity now.",
        "email-severity-dialog",
      ),
      emailLabel("Severity", select),
      element("p", {
        className: "form-error",
        attributes: { id: "email-severity-error", role: "alert" },
        hidden: true,
      }),
      element("div", { className: "modal-actions" }, [
        element("button", {
          className: "button secondary",
          text: "Cancel",
          type: "button",
          dataset: { emailAction: "close-dialog", dialog: "email-severity-dialog" },
        }),
        element("button", {
          className: "button primary",
          text: "Change severity",
          type: "submit",
        }),
      ]),
    ]);
    dialog.append(form);
    document.body.append(dialog);
  }
}

async function emailOpenPreview(messageId) {
  emailEnsurePhase9Dialogs();
  const dialog = byId("email-preview-dialog");
  const frame = byId("email-preview-frame");
  const security = byId("email-preview-security");
  const attachments = byId("email-preview-attachments");
  frame.srcdoc = "<p>Loading sanitized preview…</p>";
  security.replaceChildren();
  attachments.replaceChildren();
  dialog.showModal();
  try {
    const response = await request(`/email-messages/${messageId}/preview`);
    const preview = response.preview || {};
    frame.srcdoc = preview.html || "<p>No previewable message body.</p>";
    security.replaceChildren(
      emailBadge(
        `${Number(preview.active_content_blocked || 0)} active-content item${Number(preview.active_content_blocked || 0) === 1 ? "" : "s"} blocked`,
        "state-healthy",
      ),
      emailBadge(
        `${Number(preview.remote_content_blocked || 0)} remote-content item${Number(preview.remote_content_blocked || 0) === 1 ? "" : "s"} blocked`,
        "state-healthy",
      ),
      element("span", {
        text: "Sandboxed · no scripts · no remote images · no attachment payloads",
      }),
    );
    const items = Array.isArray(preview.attachments) ? preview.attachments : [];
    if (!items.length) {
      attachments.append(
        element("span", { className: "muted", text: "No attachments reported." }),
      );
    } else {
      for (const item of items) {
        attachments.append(
          element("div", { className: "email-preview-attachment" }, [
            element("div", {}, [
              element("strong", { text: item.name || "Unnamed attachment" }),
              element("small", {
                text: `${item.content_type || "unknown type"} · ${formatBytes(Number(item.size_bytes || 0))}`,
              }),
            ]),
            emailBadge(
              item.within_policy ? "Within policy · not retained" : "Blocked by policy · not retained",
              item.within_policy ? "state-healthy" : "state-error",
            ),
          ]),
        );
      }
    }
  } catch (error) {
    frame.srcdoc = "<p>Preview unavailable.</p>";
    security.replaceChildren(
      element("span", {
        className: "email-safe-error",
        text: error.message || "The message preview could not be loaded.",
      }),
    );
  }
}

function emailOpenSeverity(message) {
  if (!message?.processing?.rule_id) {
    toast("This Activity item does not have a matched rule.", "warning");
    return;
  }
  emailEnsurePhase9Dialogs();
  const form = byId("email-severity-form");
  form.dataset.messageId = message.id;
  const current = message.processing.classification;
  byId("email-severity-value").value = ["urgent", "warning", "information"].includes(current)
    ? current
    : "warning";
  byId("email-severity-error").hidden = true;
  byId("email-severity-dialog").showModal();
}

async function emailSaveSeverity(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const error = byId("email-severity-error");
  error.hidden = true;
  try {
    const response = await request(
      `/email-messages/${form.dataset.messageId}/change-severity`,
      {
        method: "POST",
        body: { classification: byId("email-severity-value").value },
      },
    );
    byId("email-severity-dialog").close();
    toast(
      `Rule “${response.rule?.name || "matched rule"}” updated. Future matches use ${capitalize(response.rule?.classification || "the new severity")}.`,
      "success",
    );
    await emailLoad(true);
  } catch (requestError) {
    error.textContent = requestError.message || "The severity could not be changed.";
    error.hidden = false;
  }
}

function emailMailboxProviderFields() {
  const form = byId("email-mailbox-form");
  const provider = byId("email-mailbox-provider")?.value || "gmail";
  const editing = Boolean(form?.dataset.mailboxId);
  const oauth = provider !== "imap";
  const configured = emailProviderConfigured(provider);

  byId("email-imap-fields").hidden = provider !== "imap";
  byId("email-mailbox-folder-editor").hidden = !editing;

  byId("email-mailbox-provider").disabled = editing;
  byId("email-mailbox-address").disabled = editing;
  byId("email-mailbox-shared").disabled = (
    editing
    && form?.dataset.ownerId
    && String(form.dataset.ownerId) !== String(state.user?.id || "")
  );

  for (const id of ["email-imap-host", "email-imap-username"]) {
    const input = byId(id);
    if (!input) continue;
    input.disabled = provider !== "imap";
    input.required = provider === "imap";
  }
  const password = byId("email-imap-password");
  if (password) {
    password.disabled = provider !== "imap";
    password.required = provider === "imap" && !editing;
    password.placeholder = editing
      ? "Leave blank to keep the current password"
      : "";
  }

  const hint = byId("email-mailbox-provider-hint");
  if (hint) {
    if (editing) {
      hint.textContent = provider === "gmail"
        ? "Edit the mailbox name, visibility, and scanned Gmail label. OAuth authorization remains unchanged."
        : provider === "microsoft_365"
          ? "Edit the mailbox name, visibility, and scanned Microsoft 365 folder. OAuth authorization remains unchanged."
          : "Edit the IMAP connection safely. Leave the password blank to keep the stored password, then scan folders before saving a new folder.";
    } else if (oauth && !configured) {
      hint.textContent = `${emailProviderLabel(provider)} connections are not configured on this Nowlert instance. An administrator must configure the OAuth application once at deployment level.`;
    } else {
      hint.textContent = provider === "gmail"
        ? "Continue to Google to sign in and grant Nowlert read-only Gmail access. Folder selection is available after the mailbox is connected."
        : provider === "microsoft_365"
          ? "Continue to Microsoft to sign in and grant Nowlert read-only Mail access. Folder selection is available after the mailbox is connected."
          : "Nowlert connects directly to the IMAP/IMAPS server with the username and password or app password below. Folder selection is available after the mailbox is connected.";
    }
  }

  const folderEditor = byId("email-mailbox-folder-editor");
  const folderLabel = folderEditor?.querySelector("label > span");
  if (folderLabel && editing) {
    folderLabel.textContent = provider === "gmail"
      ? "Inbox label"
      : provider === "microsoft_365"
        ? "Inbox folder"
        : "Folder";
  }

  const folderHelp = byId("email-mailbox-folder-help");
  if (folderHelp && editing) {
    folderHelp.textContent = provider === "gmail"
      ? "Choose a top-level Gmail label scanned from this account."
      : provider === "microsoft_365"
        ? "Choose a top-level Microsoft 365 mail folder scanned from this account."
        : "Choose a top-level IMAP folder scanned from the configured server.";
  }

  const submit = byId("email-mailbox-submit");
  if (submit) {
    submit.textContent = editing
      ? "Save changes"
      : provider === "gmail"
        ? "Continue to Google"
        : provider === "microsoft_365"
          ? "Continue to Microsoft"
          : "Connect mailbox";
    submit.disabled = !editing && !configured;
  }

  if (provider === "imap" && !editing && !form?.dataset.portTouched) {
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
    toast("Add an Email Alert group before creating a rule.", "warning");
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

function emailResetMailboxFolderOptions(text = "Scan folders to choose") {
  const select = byId("email-mailbox-folder");
  select.replaceChildren(emailOption("", text));
  select.value = "";
  select.disabled = true;
}

function emailOpenMailbox(provider = "") {
  emailEnsureDialogs();
  const form = byId("email-mailbox-form");
  const selectedProvider = ["gmail", "microsoft_365", "imap"].includes(provider)
    ? provider
    : emailDefaultMailboxProvider();
  form.reset();
  form.dataset.mailboxId = "";
  form.dataset.ownerId = "";
  form.dataset.portTouched = "";
  byId("email-mailbox-provider").value = selectedProvider;
  byId("email-imap-port").value = "993";
  byId("email-imap-security").value = "ssl";
  byId("email-mailbox-shared").value = "false";
  byId("email-mailbox-error").hidden = true;
  emailResetMailboxFolderOptions();
  byId("email-mailbox-dialog").querySelector("h2").textContent = "Connect mailbox";
  emailMailboxProviderFields();
  byId("email-mailbox-dialog").showModal();
  byId("email-mailbox-address")?.focus();
}

function emailPopulateMailboxFolders(result) {
  const select = byId("email-mailbox-folder");
  const folders = Array.isArray(result?.folders) ? result.folders : [];
  select.replaceChildren();
  for (const folder of folders) {
    if (!folder?.id) continue;
    select.append(emailOption(String(folder.id), String(folder.name || folder.id)));
  }
  const selected = String(result?.selected || "");
  if (
    selected
    && ![...select.options].some((option) => option.value === selected)
  ) {
    select.append(emailOption(selected, selected));
  }
  if (!select.options.length) {
    select.append(emailOption("", "No selectable folders found"));
  }
  select.value = selected || select.options[0]?.value || "";
  select.disabled = !folders.length;
}

function emailMailboxImapScanPayload() {
  const body = {
    settings: {
      host: byId("email-imap-host").value.trim(),
      port: Number(byId("email-imap-port").value),
      security: byId("email-imap-security").value,
    },
    credential: {},
  };
  const username = byId("email-imap-username").value.trim();
  const password = byId("email-imap-password").value;
  if (username) body.credential.username = username;
  if (password) body.credential.password = password;
  return body;
}

async function emailScanMailboxFolders({ manual = true } = {}) {
  const form = byId("email-mailbox-form");
  const mailboxId = form?.dataset.mailboxId || "";
  if (!mailboxId) return;

  const scan = byId("email-mailbox-folder-scan");
  const select = byId("email-mailbox-folder");
  const provider = byId("email-mailbox-provider").value;
  if (scan) scan.disabled = true;
  select.disabled = true;
  if (manual) {
    select.replaceChildren(emailOption("", "Scanning mailbox folders…"));
  }
  try {
    const response = provider === "imap" && manual
      ? await request(`/email-mailboxes/${mailboxId}/folders`, {
          method: "POST",
          body: emailMailboxImapScanPayload(),
        })
      : await request(`/email-mailboxes/${mailboxId}/folders`);

    const result = response.folders || {};
    if (provider === "imap" && result.username) {
      byId("email-imap-username").value = result.username;
    }
    emailPopulateMailboxFolders(result);
  } catch (error) {
    emailResetMailboxFolderOptions("Folder scan unavailable");
    const formError = byId("email-mailbox-error");
    formError.textContent = error.message || "Mailbox folders could not be scanned.";
    formError.hidden = false;
  } finally {
    if (scan) scan.disabled = false;
  }
}

function emailOpenMailboxEdit(mailbox) {
  if (!mailbox) return;
  emailEnsureDialogs();
  const form = byId("email-mailbox-form");
  form.reset();
  form.dataset.mailboxId = mailbox.id;
  form.dataset.ownerId = mailbox.owner_user_id || "";
  form.dataset.portTouched = "";

  byId("email-mailbox-provider").value = mailbox.provider;
  byId("email-mailbox-name").value = mailbox.name || "";
  byId("email-mailbox-address").value = mailbox.address || "";
  byId("email-mailbox-shared").value = String(Boolean(mailbox.shared));
  byId("email-mailbox-error").hidden = true;
  emailResetMailboxFolderOptions("Loading mailbox folders…");

  if (mailbox.provider === "imap") {
    byId("email-imap-host").value = mailbox.settings?.host || "";
    byId("email-imap-port").value = String(mailbox.settings?.port || 993);
    byId("email-imap-security").value = mailbox.settings?.security || "ssl";
    byId("email-imap-username").value = "";
    byId("email-imap-password").value = "";
  }

  byId("email-mailbox-dialog").querySelector("h2").textContent = "Edit mailbox";
  emailMailboxProviderFields();
  byId("email-mailbox-dialog").showModal();
  byId("email-mailbox-name")?.focus();
  void emailScanMailboxFolders({ manual: false });
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
  const form = event.currentTarget;
  const mailboxId = form.dataset.mailboxId || "";
  const editing = Boolean(mailboxId);
  const error = byId("email-mailbox-error");
  error.hidden = true;
  const provider = byId("email-mailbox-provider").value;

  try {
    if (editing) {
      const folder = byId("email-mailbox-folder").value;
      if (!folder) {
        throw new Error("Scan and select a mailbox folder before saving.");
      }
      const body = {
        name: byId("email-mailbox-name").value.trim(),
      };
      if (
        String(form.dataset.ownerId || "")
        === String(state.user?.id || "")
      ) {
        body.shared = byId("email-mailbox-shared").value === "true";
      }
      if (provider === "gmail") {
        body.settings = { label: folder };
      } else if (provider === "microsoft_365") {
        body.settings = { folder };
      } else {
        body.settings = {
          host: byId("email-imap-host").value.trim(),
          port: Number(byId("email-imap-port").value),
          security: byId("email-imap-security").value,
          folder,
        };
        body.credential = {
          username: byId("email-imap-username").value.trim(),
        };
        const password = byId("email-imap-password").value;
        if (password) body.credential.password = password;
      }
      await request(`/email-mailboxes/${mailboxId}`, {
        method: "PATCH",
        body,
      });
      byId("email-mailbox-dialog").close();
      toast("Mailbox updated.", "success");
      await emailLoad(true);
      return;
    }

    const body = {
      provider,
      name: byId("email-mailbox-name").value.trim(),
      address: byId("email-mailbox-address").value.trim(),
      enabled: true,
      shared: byId("email-mailbox-shared").value === "true",
    };
    if (provider === "imap") {
      body.settings = {
        host: byId("email-imap-host").value.trim(),
        port: Number(byId("email-imap-port").value),
        security: byId("email-imap-security").value,
      };
      body.credential = {
        username: byId("email-imap-username").value.trim(),
        password: byId("email-imap-password").value,
      };
    }

    const response = await request("/email-mailboxes", {
      method: "POST",
      body,
    });
    byId("email-mailbox-dialog").close();
    toast("Mailbox added.", "success");
    await emailLoad(true);
    if (["gmail", "microsoft_365"].includes(response.mailbox.provider)) {
      const connect = await request(
        `/email-mailboxes/${response.mailbox.id}/oauth-start`,
        { method: "POST", body: {} },
      );
      window.location.assign(connect.oauth.authorization_url);
    }
  } catch (requestError) {
    error.textContent = requestError.message || (
      editing
        ? "The mailbox could not be updated."
        : "The mailbox could not be added."
    );
    error.hidden = false;
  }
}

async function emailAction(action, id, node) {
  try {
    if (action === "new-group") return emailOpenGroup();
    if (action === "new-rule") return emailOpenRule();
    if (action === "new-mailbox") return emailOpenMailbox(node?.dataset.provider || "");
    if (action === "edit-mailbox") {
      return emailOpenMailboxEdit(
        emailAlertsState.mailboxes.find((mailbox) => mailbox.id === id),
      );
    }
    if (action === "scan-mailbox-folders") {
      await emailScanMailboxFolders({ manual: true });
      return;
    }
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

    if (action === "preview-message") {
      await emailOpenPreview(id);
      return;
    }
    if (action === "edit-activity-rule") {
      const message = emailActivityMessage(id);
      const rule = emailAlertsState.rules.find(
        (item) => item.id === message?.processing?.rule_id,
      );
      if (!rule) {
        toast("The matched rule is no longer available.", "warning");
        return;
      }
      emailOpenRule(rule);
      return;
    }
    if (action === "alert-like-this") {
      emailOpenRuleFromActivity(emailActivityMessage(id));
      return;
    }
    if (action === "mute-similar" || action === "ignore-sender") {
      const label = action === "mute-similar" ? "Mute Similar" : "Ignore Sender";
      if (!window.confirm(`${label} will create a high-priority Ignore rule. Continue?`)) return;
      const response = await request(
        `/email-messages/${id}/${action}`,
        { method: "POST", body: {} },
      );
      toast(`Ignore rule “${response.rule?.name || label}” created.`, "success");
      await emailLoad(true);
      return;
    }
    if (action === "change-severity") {
      emailOpenSeverity(emailActivityMessage(id));
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
    if (action === "toggle-mailbox-shared") {
      const item = emailAlertsState.mailboxes.find((mailbox) => mailbox.id === id);
      if (!item || String(item.owner_user_id || "") !== String(state.user?.id || "")) return;
      await request(`/email-mailboxes/${id}`, { method: "PATCH", body: { shared: !item.shared } });
      toast(item.shared ? "Mailbox is now private." : "Mailbox is now shared.", "success");
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
    if (action === "reprocess-message" || action === "force-reprocess-message") {
      const force = action === "force-reprocess-message";
      if (
        force
        && !window.confirm(
          "Force replay bypasses the Email Alert group quiet window. Continue?"
        )
      ) return;
      node.disabled = true;
      const response = await request(`/email-messages/${id}/reprocess`, {
        method: "POST",
        body: { bypass_quiet_window: force },
      });
      const result = response.result || {};
      const summary = result.reason === "routed"
        ? `Routed to ${result.delivered} destination${result.delivered === 1 ? "" : "s"}.`
        : result.reason === "quiet_window"
          ? "Reprocessing matched a rule but was suppressed by the group quiet window."
          : result.reason === "classification_ignore"
            ? "Reprocessing matched an Ignore rule."
            : result.reason === "no_matching_rule"
              ? "No enabled Email Alert rule matched this message."
              : result.reason === "no_matching_route"
                ? "The email was promoted, but no Email Alerts route is assigned to a destination."
                : result.reason === "delivery_failed"
                  ? "The email was promoted, but destination delivery failed."
                  : "Email Alert reprocessing completed.";
      toast(summary, result.failed ? "danger" : "success");
      await emailLoad(true);
      return;
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
      if (oauthState) {
        const failed = await request("/email-mailboxes/oauth-failed", {
          method: "POST",
          body: { state: oauthState, error: providerError },
        });
        toast(
          failed.mailbox?.last_error_safe || "Mailbox authorization failed.",
          "danger",
        );
      } else {
        toast("Mailbox authorization was cancelled or denied.", "danger");
      }
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
    emailAlertsState.tab = "mailboxes";
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
emailEnsurePhase9Dialogs();
byId("email-group-form")?.addEventListener("submit", emailSaveGroup);
byId("email-rule-form")?.addEventListener("submit", emailSaveRule);
byId("email-mailbox-form")?.addEventListener("submit", emailSaveMailbox);
byId("email-severity-form")?.addEventListener("submit", emailSaveSeverity);
byId("email-imap-security")?.addEventListener("change", () => {
  const form = byId("email-mailbox-form");
  if (form) form.dataset.portTouched = "";
  emailMailboxProviderFields();
});
byId("email-imap-port")?.addEventListener("input", () => {
  const form = byId("email-mailbox-form");
  if (form) form.dataset.portTouched = "true";
});

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
