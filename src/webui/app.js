"use strict";

const API = "/api/v2";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const VIEW_TITLES = {
  dashboard: "Dashboard",
  sources: "Sources",
  destinations: "Destinations",
  routes: "Routes",
  tokens: "API access",
  deliveries: "Delivery history",
  audit: "Audit log",
  users: "Users",
  settings: "Settings",
  updates: "Updates",
  inputs: "Inputs",
  backups: "Backups",
  data: "Data tools",
  account: "Security",
};
const OUTPUT_NAMES = {
  discord: "Discord",
  teams: "Microsoft Teams",
  slack: "Slack",
  webhook: "Generic webhook",
  mqtt: "MQTT",
  ntfy: "ntfy",
};
const OUTPUT_ICONS = {
  discord: "/ui/icons/discord.svg",
  mqtt: "/ui/icons/mqtt.svg",
  ntfy: "/ui/icons/ntfy.svg",
};
const SOURCE_ICONS = {
  xen_orchestra: "/ui/source-icons/xen-orchestra.png",
  xo: "/ui/source-icons/xen-orchestra.png",
  xenorchestra: "/ui/source-icons/xen-orchestra.png",
  redfish: "/ui/source-icons/redfish.jpg",
  restful: "/ui/source-icons/rest-api.svg",
  rest_api: "/ui/source-icons/rest-api.svg",
  grafana: "/ui/source-icons/grafana.png",
  portainer: "/ui/source-icons/portainer.png",
  proxmox: "/ui/source-icons/proxmox.png",
  qnap: "/ui/source-icons/qnap.png",
  synology: "/ui/source-icons/synology.png",
  truenas: "/ui/source-icons/truenas.png",
  unifi_network: "/ui/source-icons/unifi-network.png",
  unifi_protect: "/ui/source-icons/unifi-protect.png",
  unifi_drive: "/ui/source-icons/unifi-drive.png",
  zabbix: "/ui/source-icons/zabbix.png",
  supermicro: "/ui/source-icons/supermicro.png",
  hpe_ilo: "/ui/source-icons/hpe-ilo.png",
  dell_idrac: "/ui/source-icons/dell-idrac.png",
  home_assistant: "/ui/source-icons/home-assistant.png",
};
const GENERIC_SOURCE_ICON = "/ui/brand/nowlert-owl-v3.1.0.png";
const PRIORITIES = [
  ["critical", "Critical"],
  ["high", "High"],
  ["normal", "Normal"],
  ["low", "Low"],
  ["lowest", "Lowest"],
];
const SOURCE_CATEGORIES = {
  virtualization: { key: "virtualization", label: "Virtualization" },
  monitoring: { key: "monitoring", label: "Monitoring" },
  storage: { key: "storage", label: "Storage" },
  networking: { key: "networking", label: "Networking" },
  hardware: { key: "hardware", label: "Hardware" },
  automation: { key: "automation", label: "Automation" },
  containers: { key: "containers", label: "Containers" },
  security: { key: "security", label: "Security" },
  generic: { key: "generic", label: "Generic" },
};
const LANGUAGE_DEFAULT_TIMEZONES = {
  "en-GB": "Europe/London",
  "en-US": "America/New_York",
  "pt-PT": "Europe/Lisbon",
  "pt-BR": "America/Sao_Paulo",
  "es-ES": "Europe/Madrid",
  "fr-FR": "Europe/Paris",
  "de-DE": "Europe/Berlin",
  "it-IT": "Europe/Rome",
  "nl-NL": "Europe/Amsterdam",
  "pl-PL": "Europe/Warsaw",
  "cs-CZ": "Europe/Prague",
  "ro-RO": "Europe/Bucharest",
  "sv-SE": "Europe/Stockholm",
  "da-DK": "Europe/Copenhagen",
  "nb-NO": "Europe/Oslo",
  "fi-FI": "Europe/Helsinki",
  "el-GR": "Europe/Athens",
  "tr-TR": "Europe/Istanbul",
  "ru-RU": "Europe/Moscow",
  "uk-UA": "Europe/Kyiv",
  "ja-JP": "Asia/Tokyo",
  "zh-CN": "Asia/Shanghai",
};
const PT_TRANSLATIONS = {
  "Dashboard": "Painel",
  "Overview": "Visão geral",
  "Destinations": "Destinos",
  "Routes": "Rotas",
  "Applications": "Aplicações",
  "API access": "Acesso à API",
  "Event API tokens": "Tokens da API de eventos",
  "Delivery history": "Histórico de entregas",
  "Audit log": "Registo de auditoria",
  "Users": "Utilizadores",
  "Settings": "Definições",
  "Data tools": "Ferramentas de dados",
  "Account security": "Segurança da conta",
  "Workspace": "Área de trabalho",
  "Outputs": "Saídas",
  "Routing": "Encaminhamento",
  "Access": "Acesso",
  "Operations": "Operações",
  "Security": "Segurança",
  "Administration": "Administração",
  "Profile": "Perfil",
  "Add destination": "Adicionar destino",
  "Add route": "Adicionar rota",
  "Issue token": "Emitir token",
  "Add user": "Adicionar utilizador",
  "Destinations": "Destinos",
  "Active routes": "Rotas ativas",
  "Recent success": "Sucesso recente",
  "Recent deliveries": "Entregas recentes",
  "View all": "Ver tudo",
  "Source": "Origem",
  "Route": "Rota",
  "Destination": "Destino",
  "Filters": "Filtros",
  "Priority": "Prioridade",
  "Management": "Gestão",
  "Status": "Estado",
  "Time": "Hora",
  "Action": "Ação",
  "Resource": "Recurso",
  "Outcome": "Resultado",
  "Details": "Detalhes",
  "User": "Utilizador",
  "Role": "Função",
  "Last login": "Último início de sessão",
  "Language": "Idioma",
  "Timezone": "Fuso horário",
  "Time format": "Formato horário",
  "Save settings": "Guardar definições",
  "English (United Kingdom)": "Inglês (Reino Unido)",
  "Português (Portugal)": "Português (Portugal)",
  "24-hour": "24 horas",
  "12-hour (AM/PM)": "12 horas (AM/PM)",
  "Change password": "Alterar palavra-passe",
  "Current password": "Palavra-passe atual",
  "New password": "Nova palavra-passe",
  "Confirm new password": "Confirmar nova palavra-passe",
  "Update password": "Atualizar palavra-passe",
  "End session": "Terminar sessão",
  "Sign out": "Terminar sessão",
  "Create backup": "Criar cópia de segurança",
  "Download safe JSON": "Transferir JSON seguro",
  "Preview JSON import": "Pré-visualizar importação JSON",
  "Connected": "Ligado",
  "Offline": "Sem ligação",
  "Enabled": "Ativo",
  "Disabled": "Desativado",
  "Active": "Ativo",
  "Revoked": "Revogado",
  "Preview": "Pré-visualizar",
  "Edit": "Editar",
  "Disable": "Desativar",
  "Enable": "Ativar",
  "Delete": "Eliminar",
  "Reset password": "Repor palavra-passe",
};
const state = {
  user: null,
  csrf: "",
  currentView: "dashboard",
  destinations: [],
  privateDestinations: [],
  destinationErrors: [],
  destinationTestResults: {},
  routes: [],
  routeErrors: [],
  tokens: [],
  deliveries: [],
  audit: [],
  users: [],
  backups: [],
  backupTargets: [],
  externalBackups: [],
  externalBackupErrors: [],
  externalBackupsLoading: false,
  showAllBackups: false,
  showAllStoredBackups: false,
  housekeepingSettings: null,
  housekeepingStatus: null,
  sourceCategories: {},
  removedSources: [],
  integrations: [],
  integrationSettings: {},
  integrationSettingsErrors: [],
  routeSourceOptions: [],
  filteringOverview: null,
  routingFlowSnapshots: {},
  versionStatus: null,
  managedMounts: false,
  configuration: null,
  metrics: null,
  healthChecks: [],
  backupSettings: null,
  backupLastRun: null,
  workspaceErrors: [],
  workspaceLoadedAt: 0,
  historyRange: "1h",
  auditPageSize: 25,
  avatarEditor: { image: null, scale: 1, x: 0, y: 0, dragging: false, pointerX: 0, pointerY: 0 },
  preferences: { timezone: "Europe/Lisbon", language: "en-GB", time_format: "24" },
  pendingImport: null,
  sessionExpiresAt: null,
  sessionIdleExpiresAt: null,
  lastSessionKeepaliveAt: 0,
  confirmResolve: null,
  integrationSettingsBaseline: "",
};

const SESSION_IDLE_WARNING_MS = 5 * 60 * 1000;
const SESSION_KEEPALIVE_MIN_INTERVAL_MS = 5 * 60 * 1000;
const SESSION_ACTIVITY_DEBOUNCE_MS = 750;
const DESTINATION_STATE_SYNC_INTERVAL_MS = 5 * 1000;
let sessionActivityTimer = null;
let reauthPromise = null;
let reauthResolve = null;
let reauthUserId = "";
let destinationStateSyncPromise = null;

const byId = (id) => document.getElementById(id);

function element(tag, options = {}, children = []) {
  const item = document.createElement(tag);
  if (options.className) item.className = options.className;
  if (options.text !== undefined) item.textContent = String(options.text);
  if (options.title) item.title = options.title;
  if (options.type) item.type = options.type;
  if (options.value !== undefined) item.value = String(options.value);
  if (options.disabled) item.disabled = true;
  if (options.hidden) item.hidden = true;
  for (const [name, value] of Object.entries(options.attributes || {})) {
    item.setAttribute(name, String(value));
  }
  for (const [name, value] of Object.entries(options.dataset || {})) {
    item.dataset[name] = String(value);
  }
  const values = Array.isArray(children) ? children : [children];
  for (const child of values) {
    if (child === null || child === undefined) continue;
    item.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return item;
}

function actionButton(label, action, id, style = "secondary") {
  return element("button", {
    className: `button small ${style}`,
    text: label,
    type: "button",
    dataset: { action, id },
  });
}

function backupSvgIcon(name, className = "backup-action-icon") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("class", className);
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("stroke-width", "1.9");

  const definitions = {
    play: ["M8 5l11 7-11 7z"],
    edit: ["M4 20l4.5-1 10-10-3.5-3.5-10 10z", "M14 6l3.5 3.5"],
    trash: ["M5 7h14", "M9 7V4h6v3", "M8 10v7", "M12 10v7", "M16 10v7", "M6 7l1 14h10l1-14"],
    check: ["M5 12l4 4L19 6"],
    pause: ["M9 6v12", "M15 6v12"],
    clock: ["M12 7v5l3 2", "M12 3a9 9 0 1 1-9 9"],
    restore: ["M9 7H5V3", "M5 7a8 8 0 1 1-1 7"],
  };

  for (const pathData of definitions[name] || []) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathData);
    svg.append(path);
  }
  return svg;
}

function backupIconAction(action, id, label, icon, style = "secondary", iconOnly = false) {
  return element("button", {
    className: `button small ${style} backup-table-action${iconOnly ? " icon-only" : ""}`,
    type: "button",
    title: label,
    attributes: { "aria-label": label },
    dataset: { action, id },
  }, [
    backupSvgIcon(icon),
    iconOnly ? null : element("span", { text: label }),
  ]);
}

function backupTargetLastTest(item) {
  if (!item.last_test_at) {
    return element("span", { className: "backup-test-result muted", text: "Never" });
  }
  const children = [];
  if (item.last_test_outcome === "success") {
    children.push(backupSvgIcon("check", "backup-test-check"));
  } else if (item.last_test_outcome === "failed") {
    children.push(element("span", { className: "backup-test-failed", text: "!" }));
  }
  children.push(element("span", { text: formatTime(item.last_test_at) }));
  return element("span", { className: "backup-test-result" }, children);
}

function badge(label, style = "") {
  return element("span", { className: `badge ${style}`.trim(), text: label });
}

function initials(name) {
  return String(name || "N").trim().slice(0, 1).toUpperCase() || "N";
}

function avatarElement(user, large = false) {
  if (user && user.avatar_data) {
    return element("img", {
      className: `avatar avatar-image${large ? " large" : ""}`,
      attributes: { src: user.avatar_data, alt: `${user.username} profile picture` },
    });
  }
  return element("span", {
    className: `avatar${large ? " large" : ""}`,
    text: initials(user && user.username),
    attributes: { "aria-hidden": "true" },
  });
}

function applyAvatar(id, user) {
  const current = byId(id);
  const replacement = avatarElement(user, current.classList.contains("large"));
  replacement.id = id;
  current.replaceWith(replacement);
}

class APIError extends Error {
  constructor(status, message, path = "", code = "", reference = "") {
    const details = [];
    if (status) details.push(`HTTP ${status}`);
    if (path) details.push(`${API}${path}`);
    if (reference) details.push(`reference ${reference}`);
    super(`${message || "Request failed"}${details.length ? ` (${details.join(" · ")})` : ""}`);
    this.status = status;
    this.path = path;
    this.code = code;
    this.reference = reference;
  }
}

async function request(path, options = {}) {
  const method = String(options.method || "GET").toUpperCase();
  const headers = { Accept: "application/json" };
  let body;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (!SAFE_METHODS.has(method)) {
    const csrf = state.csrf;
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      method,
      headers,
      body,
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch (_error) {
    throw new APIError(0, "Nowlert is not reachable.", path, "network_error");
  }
  const raw = await response.text();
  let payload = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch (_error) {
      throw new APIError(response.status, "The server returned an invalid response.", path, "invalid_response");
    }
  }
  if (!response.ok) {
    const error = new APIError(
      response.status,
      payload && payload.error,
      path,
      payload && payload.code,
      payload && payload.reference,
    );
    if (
      response.status === 401
      && state.user
      && path !== "/session"
      && options.reauthenticate !== false
      && options._reauthRetry !== true
    ) {
      const restored = await requireReauthentication();
      if (restored) {
        return request(path, { ...options, _reauthRetry: true });
      }
    }
    throw error;
  }
  return payload;
}

function showError(id) {
  const item = byId(id);
  item.textContent = "The request could not be completed.";
  item.hidden = false;
}

function showValidationError(id, message) {
  const item = byId(id);
  item.textContent = message;
  item.hidden = false;
}

function clearError(id) {
  const item = byId(id);
  item.textContent = "";
  item.hidden = true;
}

function toast(message, style = "") {
  const item = element("div", { className: `toast ${style}`.trim(), text: message });
  byId("toast-region").append(item);
  window.setTimeout(() => item.remove(), 4200);
}

function empty(container, title, copy) {
  container.replaceChildren(
    element("div", { className: "empty-state" }, [
      element("strong", { text: title }),
      element("span", { text: copy }),
    ]),
  );
}

function formatTime(value) {
  if (value === null || value === undefined || value === "") return "Never";
  const number = Number(value);
  const date = new Date(number < 10_000_000_000 ? number * 1000 : number);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat(state.preferences.language || "en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: state.preferences.time_format === "12",
    timeZone: state.preferences.timezone || "Europe/Lisbon",
  }).format(date);
}

function relativeTime(value) {
  if (!value) return "Never";
  const seconds = Number(value) < 10_000_000_000 ? Number(value) : Number(value) / 1000;
  const delta = Math.round(seconds - Date.now() / 1000);
  const formatter = new Intl.RelativeTimeFormat(state.preferences.language || "en-GB", { numeric: "auto" });
  const absolute = Math.abs(delta);
  if (absolute < 60) return formatter.format(delta, "second");
  if (absolute < 3600) return formatter.format(Math.round(delta / 60), "minute");
  if (absolute < 86400) return formatter.format(Math.round(delta / 3600), "hour");
  return formatter.format(Math.round(delta / 86400), "day");
}

function isAdmin() {
  return state.user && state.user.role === "admin";
}

function ownResource(item) {
  if (!item || !state.user) return false;
  if (typeof item.owned === "boolean") return item.owned;
  return String(item.owner_user_id || "") === String(state.user.id || "");
}

function ensureSessionResilienceUi() {
  if (byId("session-warning") && byId("reauth-dialog")) return;

  const warning = element("div", {
    className: "session-warning",
    attributes: { id: "session-warning", role: "status", "aria-live": "polite" },
    hidden: true,
  }, [
    element("span", { attributes: { id: "session-warning-copy" }, text: "Session expires soon." }),
    element("button", {
      className: "button small primary",
      text: "Stay signed in",
      type: "button",
      attributes: { id: "session-stay-signed-in" },
    }),
  ]);

  // Keep the password field out of the browser top layer. Password-manager
  // inline menus use their own popover/top-layer UI and Chromium can disable
  // them when they are nested inside a native <dialog>.
  const dialog = element("div", {
    className: "session-reauth-overlay",
    attributes: {
      id: "reauth-dialog",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "reauth-title",
    },
    hidden: true,
  });
  const panel = element("div", {
    className: "modal small-modal session-reauth-modal",
  });
  const form = element("form", { attributes: { id: "reauth-form" } }, [
    element("div", { className: "modal-heading" }, [
      element("div", {}, [
        element("h2", { attributes: { id: "reauth-title" }, text: "Session expired" }),
        element("p", {
          className: "session-reauth-copy",
          attributes: { id: "reauth-copy" },
          text: "Your work is still here. Sign in again to continue.",
        }),
      ]),
    ]),
    element("label", {}, [
      element("span", { text: "Account" }),
      element("input", {
        type: "text",
        disabled: true,
        attributes: { id: "reauth-username", autocomplete: "username" },
      }),
    ]),
    element("label", {}, [
      element("span", { text: "Password" }),
      element("input", {
        type: "password",
        attributes: {
          id: "reauth-password",
          autocomplete: "current-password",
          required: "",
        },
      }),
    ]),
    element("label", {
      attributes: { id: "reauth-otp-field" },
      hidden: true,
    }, [
      element("span", { text: "Authenticator code" }),
      element("input", {
        type: "text",
        attributes: {
          id: "reauth-otp",
          inputmode: "numeric",
          autocomplete: "one-time-code",
          maxlength: "8",
        },
      }),
    ]),
    element("p", {
      className: "form-error",
      attributes: { id: "reauth-error", role: "alert" },
      hidden: true,
    }),
    element("div", { className: "modal-actions" }, [
      element("button", {
        className: "button secondary",
        text: "Sign out",
        type: "button",
        attributes: { id: "reauth-signout" },
      }),
      element("button", {
        className: "button primary",
        text: "Continue",
        type: "submit",
        attributes: { id: "reauth-submit" },
      }),
    ]),
  ]);
  panel.append(form);
  dialog.append(panel);
  document.body.append(warning, dialog);
}

function effectiveSessionExpiry() {
  const idle = Number(state.sessionIdleExpiresAt || 0);
  const absolute = Number(state.sessionExpiresAt || 0);
  if (idle && absolute) return Math.min(idle, absolute);
  return idle || absolute || 0;
}

function renderSessionExpiryLabel() {
  const label = byId("account-session");
  if (!label) return;
  const idle = state.sessionIdleExpiresAt || state.sessionExpiresAt;
  if (!idle) {
    label.textContent = "Session inactive";
    return;
  }
  if (state.sessionExpiresAt && Number(state.sessionExpiresAt) !== Number(idle)) {
    label.textContent = `Idle timeout ${formatTime(idle)} · maximum ${formatTime(state.sessionExpiresAt)}`;
    return;
  }
  label.textContent = `Session expires ${formatTime(idle)}`;
}

function applySessionMetadata(session) {
  if (!session) return;
  if (session.user) state.user = session.user;
  if (session.expires_at) state.sessionExpiresAt = session.expires_at;
  state.sessionIdleExpiresAt = session.idle_expires_at || session.expires_at || state.sessionIdleExpiresAt;
  if (session.csrf_token) {
    state.csrf = session.csrf_token;
  }
  state.lastSessionKeepaliveAt = Date.now();
  renderSessionExpiryLabel();
  updateSessionWarning();
}

function finishReauthentication(result) {
  const dialog = byId("reauth-dialog");
  if (dialog) dialog.hidden = true;
  byId("app-shell")?.removeAttribute("inert");
  document.body.classList.remove("session-reauth-open");
  const resolve = reauthResolve;
  reauthResolve = null;
  reauthPromise = null;
  reauthUserId = "";
  resolve?.(result);
}

async function submitReauthentication(event) {
  event.preventDefault();
  if (!state.user || !reauthPromise) return;
  const submit = byId("reauth-submit");
  const error = byId("reauth-error");
  const otpField = byId("reauth-otp-field");
  const expectedUserId = reauthUserId;
  submit.disabled = true;
  error.hidden = true;
  error.textContent = "";
  try {
    const body = {
      username: state.user.username,
      password: byId("reauth-password").value,
    };
    if (!otpField.hidden) body.otp = byId("reauth-otp").value.trim();
    const session = await request("/session", {
      method: "POST",
      body,
      reauthenticate: false,
    });
    if (String(session.user?.id || "") !== String(expectedUserId || "")) {
      try {
        await request("/session", { method: "DELETE", reauthenticate: false });
      } catch (_error) {
      }
      throw new Error("The signed-in account changed. Sign out and sign in again.");
    }
    applySessionMetadata(session);
    finishReauthentication(true);
  } catch (reauthError) {
    if (reauthError instanceof APIError && ["mfa_required", "mfa_invalid"].includes(reauthError.code)) {
      otpField.hidden = false;
      error.textContent = reauthError.code === "mfa_required"
        ? "Enter your authenticator code to continue."
        : "The authenticator code is invalid.";
      error.hidden = false;
      byId("reauth-otp").focus();
      return;
    }
    error.textContent = reauthError.message || "Sign-in failed.";
    error.hidden = false;
  } finally {
    submit.disabled = false;
  }
}

function requireReauthentication(message = "Your session expired. Sign in again to continue without losing your work.") {
  if (!state.user) return Promise.resolve(false);
  if (reauthPromise) return reauthPromise;
  ensureSessionResilienceUi();
  reauthUserId = String(state.user.id || "");
  byId("reauth-title").textContent = "Session expired";
  byId("reauth-copy").textContent = message;
  byId("reauth-username").value = state.user.username || "";
  byId("reauth-password").value = "";
  byId("reauth-otp").value = "";
  byId("reauth-otp-field").hidden = true;
  byId("reauth-error").hidden = true;
  byId("session-warning").hidden = true;
  reauthPromise = new Promise((resolve) => {
    reauthResolve = resolve;
  });
  const dialog = byId("reauth-dialog");
  dialog.hidden = false;
  byId("app-shell")?.setAttribute("inert", "");
  document.body.classList.add("session-reauth-open");
  window.setTimeout(() => byId("reauth-password")?.focus(), 0);
  return reauthPromise;
}

async function refreshSession({ promptOnExpiry = true } = {}) {
  if (!state.user) return false;
  try {
    const session = await request("/session", { reauthenticate: false });
    applySessionMetadata(session);
    return true;
  } catch (error) {
    if (error instanceof APIError && error.status === 401 && state.user && promptOnExpiry) {
      return requireReauthentication();
    }
    return false;
  }
}

function updateSessionWarning() {
  ensureSessionResilienceUi();
  const warning = byId("session-warning");
  if (!state.user || document.visibilityState === "hidden") {
    warning.hidden = true;
    return;
  }
  const expiry = effectiveSessionExpiry();
  if (!expiry) {
    warning.hidden = true;
    return;
  }
  const remaining = expiry * 1000 - Date.now();
  if (remaining <= 0) {
    warning.hidden = true;
    void requireReauthentication();
    return;
  }
  if (remaining <= SESSION_IDLE_WARNING_MS) {
    const minutes = Math.max(1, Math.ceil(remaining / 60000));
    byId("session-warning-copy").textContent = `Session expires in about ${minutes} minute${minutes === 1 ? "" : "s"}.`;
    warning.hidden = false;
    return;
  }
  warning.hidden = true;
}

function noteSessionActivity() {
  if (!state.user || document.visibilityState === "hidden" || reauthPromise) return;
  if (Date.now() - Number(state.lastSessionKeepaliveAt || 0) < SESSION_KEEPALIVE_MIN_INTERVAL_MS) return;
  if (sessionActivityTimer !== null) return;
  sessionActivityTimer = window.setTimeout(() => {
    sessionActivityTimer = null;
    void refreshSession();
  }, SESSION_ACTIVITY_DEBOUNCE_MS);
}

function expireSession(options = {}) {
  state.user = null;
  state.csrf = "";
  state.sessionExpiresAt = null;
  state.sessionIdleExpiresAt = null;
  state.lastSessionKeepaliveAt = 0;
  state.workspaceLoadedAt = 0;
  window.clearTimeout(sessionActivityTimer);
  sessionActivityTimer = null;
  const warning = byId("session-warning");
  if (warning) warning.hidden = true;
  if (reauthPromise) finishReauthentication(false);
  byId("app-shell").hidden = true;
  byId("bootstrap-view").hidden = true;
  byId("login-view").hidden = false;
  byId("login-password").value = "";
  byId("login-password").type = "password";
  const mfaField = byId("login-mfa-field");
  if (mfaField) mfaField.hidden = true;
  if (byId("login-otp")) byId("login-otp").value = "";
  const passwordToggle = byId("login-password-toggle");
  if (passwordToggle) {
    passwordToggle.setAttribute("aria-pressed", "false");
    passwordToggle.setAttribute("aria-label", "Show password");
    passwordToggle.title = "Show password";
    passwordToggle.classList.remove("is-visible");
  }
  byId("login-error").hidden = true;
  byId("login-username").focus();
  return options;
}

function showBootstrap(status) {
  state.user = null;
  state.csrf = "";
  byId("app-shell").hidden = true;
  byId("login-view").hidden = true;
  byId("bootstrap-view").hidden = false;
  const fragment = window.location.hash.slice(1);
  if (fragment.startsWith("setup=")) {
    byId("bootstrap-token").value = decodeURIComponent(fragment.slice(6));
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
  }
  byId("bootstrap-expiry").textContent = status.expires_at
    ? `This setup token expires ${formatTime(status.expires_at)}.`
    : "The setup token has expired. Restart Nowlert to rotate it, then check the new container output.";
  (byId("bootstrap-token").value ? byId("bootstrap-username") : byId("bootstrap-token")).focus();
}

function requestedAppView() {
  const requested = window.location.hash.slice(1);
  if (
    VIEW_TITLES[requested]
    && (!["users", "inputs", "backups", "data", "audit"].includes(requested) || isAdmin())
  ) {
    return requested;
  }
  return VIEW_TITLES[state.currentView] ? state.currentView : "dashboard";
}

function showApp(session) {
  state.user = session.user;
  applySessionMetadata(session);
  byId("login-view").hidden = true;
  if (byId("audit-nav")) byId("audit-nav").hidden = !isAdmin();
  if (byId("users-nav")) byId("users-nav").hidden = !isAdmin();
  if (byId("settings-nav")) byId("settings-nav").hidden = false;
  if (byId("inputs-nav")) byId("inputs-nav").hidden = !isAdmin();
  if (byId("backups-nav")) byId("backups-nav").hidden = !isAdmin();
  if (byId("data-nav")) byId("data-nav").hidden = !isAdmin();
  byId("add-destination-button").hidden = !isAdmin();
  byId("add-route-button").hidden = !isAdmin();
  byId("restart-header-button").hidden = !isAdmin();
  const name = state.user.username;
  const admin = isAdmin();
  for (const id of ["profile-avatar", "account-avatar"]) applyAvatar(id, state.user);
  for (const id of ["profile-name", "account-name"]) byId(id).textContent = name;

  const profileRole = byId("profile-role");
  profileRole.textContent = admin ? "Admin" : "User";
  delete profileRole.dataset.i18nSource;

  const accountRole = byId("account-role");
  accountRole.textContent = admin ? "Administrator" : "User";
  delete accountRole.dataset.i18nSource;
  renderSessionExpiryLabel();

  // Restore the requested page before the authenticated shell is revealed.
  // Routing Flow and Filtering wrappers synchronously hydrate their cached
  // snapshots during navigate(), so F5 never paints an empty Dashboard first.
  navigate(requestedAppView(), "replace");
  if (
    state.backupSettings
    || state.backups.length
    || state.externalBackups.length
  ) {
    renderAll();
  }
  byId("app-shell").hidden = false;
}

async function restoreSession(prefetchedSession = null) {
  let session;
  try {
    if (prefetchedSession) session = await prefetchedSession;
    else session = await request("/session");
  } catch (error) {
    if (error instanceof APIError && error.status === 401) {
      expireSession({ preserveCache: true });
      return;
    }
    if (error instanceof APIError && error.status === 429) {
      byId("login-error").textContent = "Nowlert is temporarily rate limited. Retrying…";
      byId("login-error").hidden = false;
      window.setTimeout(() => restoreSession(), 1500);
      return;
    }
    if (!(error instanceof APIError) || error.status !== 404) {
      byId("login-error").textContent = error.message || "Nowlert is not reachable.";
      byId("login-error").hidden = false;
    }
    return;
  }
  showApp(session);
  try {
    await loadWorkspace();
  } catch (error) {
    if (!(error instanceof APIError) || error.status !== 401) {
      state.workspaceErrors = [{
        component: "Workspace",
        message: error.message || "Request failed",
      }];
      renderWorkspaceErrors();
    }
  }
}

function toggleLoginPasswordVisibility() {
  const input = byId("login-password");
  const button = byId("login-password-toggle");
  if (!input || !button) return;
  const visible = input.type === "password";
  input.type = visible ? "text" : "password";
  button.setAttribute("aria-pressed", String(visible));
  button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
  button.title = visible ? "Hide password" : "Show password";
  button.classList.toggle("is-visible", visible);
}

async function login(event) {
  event.preventDefault();
  clearError("login-error");
  const submit = event.submitter;
  if (submit) submit.disabled = true;
  try {
    const mfaField = byId("login-mfa-field");
    const body = {
      username: byId("login-username").value.trim(),
      password: byId("login-password").value,
    };
    if (mfaField && !mfaField.hidden) body.otp = byId("login-otp").value.trim();
    const session = await request("/session", {
      method: "POST",
      body,
    });
    if (mfaField) mfaField.hidden = true;
    if (byId("login-otp")) byId("login-otp").value = "";
    showApp(session);
    await loadWorkspace();
  } catch (error) {
    if (error instanceof APIError && error.code === "mfa_required") {
      const mfaField = byId("login-mfa-field");
      if (mfaField) mfaField.hidden = false;
      clearError("login-error");
      byId("login-otp")?.focus();
      return;
    }
    showError("login-error", error);
  } finally {
    if (submit) submit.disabled = false;
  }
}

function mfaDigitInputs() {
  return [...document.querySelectorAll("[data-mfa-digit]")];
}

function syncMfaCodeDigits() {
  const code = mfaDigitInputs().map((input) => input.value).join("");
  const hidden = byId("mfa-enable-code");
  if (hidden) hidden.value = code;
  return code;
}

function resetMfaCodeDigits() {
  for (const input of mfaDigitInputs()) input.value = "";
  const hidden = byId("mfa-enable-code");
  if (hidden) hidden.value = "";
}

function handleMfaDigitInput(event) {
  const input = event.currentTarget;
  const digits = mfaDigitInputs();
  const index = digits.indexOf(input);
  const value = String(input.value || "").replace(/\D/g, "");
  if (value.length > 1 && index >= 0) {
    value.slice(0, digits.length - index).split("").forEach((digit, offset) => {
      digits[index + offset].value = digit;
    });
    syncMfaCodeDigits();
    digits[Math.min(digits.length - 1, index + value.length - 1)]?.focus();
    return;
  }
  input.value = value.slice(-1);
  syncMfaCodeDigits();
  if (input.value && index >= 0 && index < digits.length - 1) {
    digits[index + 1].focus();
    digits[index + 1].select();
  }
}

function handleMfaDigitKeydown(event) {
  const input = event.currentTarget;
  const digits = mfaDigitInputs();
  const index = digits.indexOf(input);
  if (event.key === "Backspace" && !input.value && index > 0) {
    digits[index - 1].focus();
    digits[index - 1].select();
  } else if (event.key === "ArrowLeft" && index > 0) {
    event.preventDefault();
    digits[index - 1].focus();
  } else if (event.key === "ArrowRight" && index >= 0 && index < digits.length - 1) {
    event.preventDefault();
    digits[index + 1].focus();
  }
}

function handleMfaDigitPaste(event) {
  const value = String(event.clipboardData?.getData("text") || "").replace(/\D/g, "").slice(0, 6);
  if (!value) return;
  event.preventDefault();
  const digits = mfaDigitInputs();
  digits.forEach((input, index) => { input.value = value[index] || ""; });
  syncMfaCodeDigits();
  const target = digits[Math.min(value.length, digits.length) - 1];
  target?.focus();
}

async function startMfaSetup() {
  clearError("mfa-enable-error");
  const response = await request("/account/mfa/setup", {
    method: "POST",
    body: {},
  });
  byId("mfa-secret-value").textContent = response.secret || "";
  const qr = byId("mfa-qr-code");
  if (qr) {
    qr.src = response.qr_code || "";
    qr.hidden = !response.qr_code;
  }
  resetMfaCodeDigits();
  return response;
}

async function openMfaDialog() {
  const dialog = byId("mfa-dialog");
  const setup = byId("mfa-setup-panel");
  const disable = byId("mfa-disable-panel");
  const summary = byId("mfa-dialog-summary");
  const detail = byId("mfa-dialog-detail");
  if (!dialog || !setup || !disable) return;
  clearError("mfa-enable-error");
  clearError("mfa-disable-error");

  const enabled = Boolean(state.user?.mfa_enabled);
  setup.hidden = enabled;
  disable.hidden = !enabled;
  dialog.classList.toggle("is-disable-mode", enabled);

  if (summary) {
    summary.textContent = enabled
      ? "Confirm your current password and authenticator code to disable MFA."
      : "Set up an authenticator app to add an extra layer of security to your account.";
  }
  if (detail) {
    detail.hidden = enabled;
    detail.textContent = "Scan the QR code or use the setup key below, then enter the 6-digit code from your app.";
  }

  if (enabled) {
    byId("mfa-disable-password").value = "";
    byId("mfa-disable-code").value = "";
    if (!dialog.open) dialog.showModal();
    byId("mfa-disable-password").focus();
    return;
  }

  if (!dialog.open) dialog.showModal();
  try {
    await startMfaSetup();
    mfaDigitInputs()[0]?.focus();
  } catch (error) {
    showError("mfa-enable-error", error);
  }
}

function closeMfaDialog() {
  const dialog = byId("mfa-dialog");
  if (dialog) dialog.classList.remove("is-disable-mode");
  resetMfaCodeDigits();
  const secret = byId("mfa-secret-value");
  if (secret) secret.textContent = "";
  const qr = byId("mfa-qr-code");
  if (qr) {
    qr.removeAttribute("src");
    qr.hidden = true;
  }
  if (dialog?.open) dialog.close();
}

async function confirmMfaSetup(event) {
  event.preventDefault();
  clearError("mfa-enable-error");
  const code = syncMfaCodeDigits();
  if (!/^\d{6}$/.test(code)) {
    showValidationError("mfa-enable-error", "Enter the complete six-digit authenticator code.");
    mfaDigitInputs().find((input) => !input.value)?.focus();
    return;
  }
  const submit = event.submitter;
  if (submit) submit.disabled = true;
  try {
    const response = await request("/account/mfa", {
      method: "PUT",
      body: { code },
    });
    state.user = response.user;
    closeMfaDialog();
    document.dispatchEvent(new Event("nowlert:account-updated"));
    toast("Multi-factor authentication enabled.");
  } catch (error) {
    showError("mfa-enable-error", error);
  } finally {
    if (submit) submit.disabled = false;
  }
}

async function disableMfa(event) {
  event.preventDefault();
  clearError("mfa-disable-error");
  const submit = event.submitter;
  if (submit) submit.disabled = true;
  try {
    const response = await request("/account/mfa", {
      method: "DELETE",
      body: {
        password: byId("mfa-disable-password").value,
        code: byId("mfa-disable-code").value.trim(),
      },
    });
    state.user = response.user;
    closeMfaDialog();
    document.dispatchEvent(new Event("nowlert:account-updated"));
    toast("Multi-factor authentication disabled.");
  } catch (error) {
    showError("mfa-disable-error", error);
  } finally {
    if (submit) submit.disabled = false;
  }
}

async function copyMfaSecret() {
  const value = byId("mfa-secret-value")?.textContent || "";
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    toast("MFA setup key copied.");
  } catch (_error) {
    toast("MFA setup key could not be copied.", "error");
  }
}

async function bootstrapAdministrator(event) {
  event.preventDefault();
  clearError("bootstrap-error");
  const submit = event.submitter;
  const password = byId("bootstrap-password").value;
  if (password !== byId("bootstrap-confirm").value) {
    showValidationError("bootstrap-error", "The passwords do not match.");
    return;
  }
  if (submit) submit.disabled = true;
  try {
    const session = await request("/bootstrap", {
      method: "POST",
      body: {
        token: byId("bootstrap-token").value.trim(),
        username: byId("bootstrap-username").value.trim(),
        password,
      },
    });
    byId("bootstrap-token").value = "";
    byId("bootstrap-password").value = "";
    byId("bootstrap-confirm").value = "";
    byId("bootstrap-view").hidden = true;
    showApp(session);
    await loadWorkspace();
  } catch (error) {
    showError("bootstrap-error", error);
  } finally {
    if (submit) submit.disabled = false;
  }
}

async function initialize(startupRequests = {}) {
  // Start authentication/bootstrap requests as soon as app.js executes, but
  // consume them only after every deferred WebUI layer has finished loading.
  // This keeps F5 fast without revealing the base shell before extensions exist.
  const sessionRequest = startupRequests.session || request("/session");
  void sessionRequest.catch(() => {});

  try {
    const status = await (startupRequests.bootstrap || request("/bootstrap"));
    if (status.required) {
      showBootstrap(status);
      return;
    }
  } catch (error) {
    if (!(error instanceof APIError) || error.status !== 404) {
      byId("login-error").textContent = error.message || "Nowlert is not reachable.";
      byId("login-error").hidden = false;
    }
  }
  await restoreSession(sessionRequest);
}

async function loadWorkspace() {
  const initialDeliveryRequest = typeof window.nowlertInitialDeliveryRequest === "function"
    ? window.nowlertInitialDeliveryRequest()
    : request("/deliveries");
  const initialAuditRequest = typeof window.nowlertInitialAuditRequest === "function"
    ? window.nowlertInitialAuditRequest()
    : request("/audit-events");

  const tasks = {
    integrations: ["Integrations", request("/integrations"), (value) => {
      state.integrations = value.integrations || [];
      state.routeSourceOptions = value.route_options || [];
    }],
    integrationSettings: ["Integration settings", request("/integration-settings"), (value) => {
      state.integrationSettings = value.settings || {};
      state.integrationSettingsErrors = value.errors || [];
    }],
    destinations: ["Destinations", request("/destinations"), (value) => {
      state.destinations = value.destinations || [];
      state.privateDestinations = Array.isArray(value.private_resources)
        ? value.private_resources
        : [];
      state.destinationErrors = value.errors || [];
    }],
    routes: ["Routes", request("/routes"), (value) => {
      state.routes = value.routes || [];
      state.routeErrors = value.errors || [];
    }],
    filters: ["Filtering", request("/filters"), (value) => {
      state.filteringOverview = value;
    }],
    tokens: ["Event API tokens", request("/tokens"), (value) => { state.tokens = value.tokens; }],
    deliveries: ["Delivery history", initialDeliveryRequest, (value) => { state.deliveries = value.deliveries || []; }],
    audit: ["Audit log", initialAuditRequest, (value) => { state.audit = value.audit_events || []; }],
    preferences: ["Regional settings", request("/preferences"), (value) => { state.preferences = value.preferences; }],
    metrics: ["Overview metrics", request(`/metrics/${state.historyRange}`), (value) => { state.metrics = value.metrics; }],
    version: ["Version status", request("/version"), (value) => { state.versionStatus = value.version; }],
  };
  if (isAdmin()) {
    tasks.users = ["Users", request("/users"), (value) => { state.users = value.users; }];
    tasks.backups = ["Backups", request("/backups"), (value) => { state.backups = value.backups; }];
    tasks.backupTargets = ["Backup destinations", request("/backup-targets"), (value) => {
      state.backupTargets = value.targets;
      state.managedMounts = value.managed_mounts;
    }];
    tasks.configuration = ["Configuration inventory", request("/configuration/inventory"), (value) => { state.configuration = value.configuration; }];
    tasks.backupSettings = ["Backup settings", request("/backup-settings"), (value) => {
      state.backupSettings = value.settings;
      state.backupLastRun = value.last_run;
    }];
    tasks.housekeeping = ["Housekeeping", request("/housekeeping"), (value) => {
      state.housekeepingSettings = value.settings;
      state.housekeepingStatus = value.status;
    }];
  }
  const entries = Object.values(tasks);
  const settled = await Promise.allSettled(entries.map(([, promise]) => promise));
  state.workspaceErrors = [];
  for (let index = 0; index < settled.length; index += 1) {
    const result = settled[index];
    const [label, , apply] = entries[index];
    if (result.status === "fulfilled") {
      apply(result.value);
      continue;
    }
    if (result.reason instanceof APIError && result.reason.status === 401) {
      throw result.reason;
    }
    state.workspaceErrors.push({
      component: label,
      message: result.reason && result.reason.message ? result.reason.message : "Request failed",
    });
  }
  if (!isAdmin()) {
    state.users = [];
    state.backups = [];
    state.backupTargets = [];
    state.managedMounts = false;
    state.configuration = null;
    state.backupSettings = null;
    state.backupLastRun = null;
    state.housekeepingSettings = null;
    state.housekeepingStatus = null;
    state.externalBackups = [];
    state.externalBackupErrors = [];
  }
  state.workspaceLoadedAt = Date.now();
  document.dispatchEvent(new CustomEvent("nowlert:workspace-loaded", {
    detail: {
      loadedAt: state.workspaceLoadedAt,
      failures: state.workspaceErrors.map((item) => item.component),
    },
  }));
  renderAll();
  const requestedView = requestedAppView();
  if (state.currentView !== requestedView) {
    navigate(requestedView, "replace");
  }
  if (state.currentView === "backups" && isAdmin()) {
    void loadExternalBackups({ silent: true });
  }
}

function renderAll() {
  renderWorkspaceErrors();
  renderDashboard();
  renderSources();
  renderDestinations();
  renderRoutes();
  renderTokens();
  renderDeliveries();
  renderAudit();
  renderUsers();
  renderBackups();
  renderBackupTargets();
  renderConfiguration();
  renderHealthChecks();
  renderBackupSettings();
  renderHousekeepingSettings();
  renderUpdates();
  renderPreferences();
  renderIntegrationSettings();
  applyLanguage();
}

function renderWorkspaceErrors() {
  const alert = byId("workspace-alert");
  const list = byId("workspace-alert-list");
  list.replaceChildren();
  const failures = [
    ...state.workspaceErrors,
    ...state.destinationErrors.map((item) => ({ component: "Destinations", message: item.message })),
    ...state.routeErrors.map((item) => ({ component: "Routes", message: item.message })),
  ];
  for (const failure of failures) {
    list.append(element("li", {
      text: `${failure.component}: ${failure.message}`,
    }));
  }
  alert.hidden = failures.length === 0;
}

function applyLanguage() {
  document.documentElement.lang = state.preferences.language || "en-GB";
  for (const item of document.querySelectorAll("body *")) {
    if (item.children.length || ["SCRIPT", "STYLE", "CODE", "PRE"].includes(item.tagName)) continue;
    const current = item.textContent.trim();
    if (!item.dataset.i18nSource && !Object.hasOwn(PT_TRANSLATIONS, current)) continue;
    if (!item.dataset.i18nSource) item.dataset.i18nSource = current;
    const source = item.dataset.i18nSource;
    item.textContent = state.preferences.language.startsWith("pt-") ? (PT_TRANSLATIONS[source] || source) : source;
  }
}

function navigate(view, historyMode = "push") {
  if (!VIEW_TITLES[view] || (["users", "inputs", "backups", "data", "audit"].includes(view) && !isAdmin())) view = "dashboard";
  state.currentView = view;
  for (const section of document.querySelectorAll(".view")) {
    section.hidden = section.dataset.page !== view;
  }
  for (const button of document.querySelectorAll("[data-view]")) {
    const active = button.dataset.view === view && button.classList.contains("nav-item");
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  byId("page-title").textContent = VIEW_TITLES[view];
  closeProfileMenu();
  const targetHash = `#${view}`;
  if (
    historyMode === "replace"
    || (historyMode === "none" && window.location.hash !== targetHash)
  ) {
    window.history.replaceState({ nowlertView: view }, "", targetHash);
  } else if (historyMode === "push" && window.location.hash !== targetHash) {
    window.history.pushState({ nowlertView: view }, "", targetHash);
  }
  byId("app-shell").classList.remove("nav-open");
  byId("mobile-menu").setAttribute("aria-expanded", "false");
  byId("main-content").focus({ preventScroll: true });
  if (view === "backups" && isAdmin()) {
    queueMicrotask(() => {
      loadExternalBackups({ silent: true }).catch((error) => {
        if (state.currentView === "backups") {
          toast(error.message || "Stored snapshots could not be refreshed.", "error");
        }
      });
    });
  }
  if (state.user && view === "destinations") {
    queueMicrotask(() => {
      refreshDestinationState().catch(() => {});
    });
  }
}

function renderDashboard() {
  const metrics = state.metrics || {};
  byId("metric-sources").textContent = metrics.sources ?? "—";
  byId("metric-destinations").textContent = metrics.destinations ?? "—";
  byId("metric-routes").textContent = metrics.routes ?? "—";
  byId("metric-tokens").textContent = metrics.applications ?? "—";
  byId("metric-success").textContent = metrics.success_percent === null || metrics.success_percent === undefined ? "—" : `${metrics.success_percent}%`;
  byId("metric-success-note").textContent = metrics.requests ? `${metrics.delivered} of ${metrics.requests} delivered` : "No requests in range";
  byId("metric-requests").textContent = metrics.requests ?? "—";
  byId("history-range").value = state.historyRange;
  renderFlow();
  const container = byId("dashboard-deliveries");
  container.replaceChildren();
  if (!state.deliveries.length) {
    empty(container, "No deliveries yet", "Submitted events will appear here after a route matches.");
    return;
  }
  for (const item of state.deliveries.slice(0, 6)) {
    const delivered = ["delivered", "success"].includes(item.outcome);
    const outcome = delivered ? "success" : item.retryable ? "warning" : "danger";
    container.append(element("div", { className: "activity-item" }, [
      element("span", { className: "event-indicator", text: delivered ? "✓" : "!" }),
      element("div", {}, [
        element("strong", { text: item.device_name ? `${item.device_name} · ${item.event_name || item.title}` : item.event_name || item.title || "Untitled event" }),
        element("small", { text: `${friendlyName(item.source)} · ${capitalize(item.severity)} · attempt ${item.attempt_number}` }),
      ]),
      element("div", {}, [badge(item.outcome, outcome), element("small", { text: relativeTime(item.completed_at || item.created_at) })]),
    ]));
  }
}

function capitalize(value) {
  const text = String(value || "");
  return text ? text[0].toUpperCase() + text.slice(1) : "—";
}

function integrationBySource(value) {
  const key = String(value || "").toLowerCase();
  return state.integrations.find((item) => item.id === key || (item.sources || []).includes(key)) || null;
}

function inputLabel(value) {
  const labels = { smtp: "SMTP", http: "HTTP", redfish: "Redfish" };
  return labels[String(value || "").toLowerCase()] || String(value || "Any input").toUpperCase();
}

function routeSourceDescriptor(source, inputType = "") {
  if (source === "*") {
    const input = inputLabel(inputType || "http");
    return { integration: "Fallback", input, label: `Fallback (${input})` };
  }
  const item = integrationBySource(source);
  const integration = item ? item.name : friendlyName(source);
  const input = inputLabel(inputType || "");
  return { integration, input, label: inputType ? `${integration} (${input})` : integration };
}

function friendlyName(value) {
  const item = integrationBySource(value);
  if (item) return item.name;
  const special = { home_assistant: "Home Assistant", hpe_ilo: "HPE iLO", dell_idrac: "Dell iDRAC", xen_orchestra: "Xen Orchestra", xo: "Xen Orchestra", xenorchestra: "Xen Orchestra", redfish: "Redfish", restful: "RESTful API", rest_api: "REST API", unifi_network: "UniFi Network", unifi_protect: "UniFi Protect", unifi_drive: "UniFi Drive" };
  const key = String(value || "").toLowerCase();
  return special[key] || String(value || "Unknown").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function outputIcon(type) {
  if (OUTPUT_ICONS[type]) return element("img", { className: "output-icon-image", attributes: { src: OUTPUT_ICONS[type], alt: "" } });
  const labels = { teams: "T", slack: "S", webhook: "↗" };
  return element("span", { className: `output-icon-fallback ${type}`, text: labels[type] || String(type || "?").slice(0, 1).toUpperCase(), attributes: { "aria-hidden": "true" } });
}

function sourceIcon(source) {
  const key = String(source || "").toLowerCase();
  return element("img", {
    className: "source-product-icon",
    attributes: {
      src: SOURCE_ICONS[key] || GENERIC_SOURCE_ICON,
      alt: "",
      loading: "lazy",
    },
    dataset: { sourceKey: key },
  });
}

function sourceInputType(source, routeInput = "") {
  if (routeInput) return inputLabel(routeInput);
  const observed = state.deliveries.find((item) => item.source === source && item.input_type);
  if (observed && observed.input_type) return inputLabel(observed.input_type);
  const integration = integrationBySource(source);
  if (integration && integration.inputs.length === 1) return integration.inputs[0].name;
  return integration ? integration.inputs.map((item) => item.name).join(", ") : "HTTP";
}

function sourceCategory(source) {
  const item = integrationBySource(source);
  const key = item ? item.category : "generic";
  return SOURCE_CATEGORIES[key] || SOURCE_CATEGORIES.generic;
}

function sourceIsActive(source) {
  return state.routes.some((route) =>
    route.enabled && (route.source === source || route.source === "*"));
}

const CREDENTIAL_OUTPUTS = new Set(["discord", "teams", "slack", "webhook"]);

function inputFlowState(inputType) {
  const key = String(inputType || "http").toLowerCase();
  const inventory = state.configuration && Array.isArray(state.configuration.inputs)
    ? state.configuration.inputs
    : null;
  if (!inventory) return { state: "active", detail: `${inputLabel(key)} status unavailable` };
  const item = inventory.find((candidate) => candidate.name === key);
  if (!item || item.configured === false) {
    return { state: "error", detail: `${inputLabel(key)} is not configured` };
  }
  if (!item.enabled) return { state: "disabled", detail: `${inputLabel(key)} is disabled` };
  const sync = state.configuration.sync || {};
  if (sync.ready === false) return { state: "error", detail: `${inputLabel(key)} configuration requires repair` };
  return { state: "active", detail: `${inputLabel(key)} is enabled` };
}

function routeFlowState(route) {
  if (!route) return { state: "error", detail: "Route is unavailable" };
  if (!route.enabled) return { state: "disabled", detail: "Route is disabled" };
  return { state: "active", detail: "Route is enabled" };
}

function destinationTestResult(destination) {
  if (!destination) return null;
  const transient = state.destinationTestResults[destination.id] || null;
  const persisted = destination.last_test_at
    ? {
        success: destination.last_test_outcome === "success",
        response_status: destination.last_test_response_status || null,
        error_code: destination.last_test_error_code || "",
        safe_error: destination.last_test_safe_error || "",
        tested_at: Number(destination.last_test_at) < 10_000_000_000
          ? Number(destination.last_test_at) * 1000
          : Number(destination.last_test_at),
      }
    : null;
  if (!persisted) return transient;
  if (!transient) return persisted;
  return Number(transient.tested_at || 0) >= Number(persisted.tested_at || 0)
    ? transient
    : persisted;
}

function destinationTestDetail(result) {
  if (!result) return "";
  if (result.safe_error) return result.safe_error;
  if (result.response_status === 202) {
    return "Destination accepted the request with HTTP 202; delivery is not confirmed";
  }
  if (result.response_status) return `Destination returned HTTP ${result.response_status}`;
  if (result.error_code) return friendlyName(result.error_code);
  return result.success ? "Destination test passed" : "Destination test failed";
}

function destinationFlowState(destination) {
  if (!destination) return { state: "error", detail: "Destination is missing" };
  if (!destination.enabled) return { state: "disabled", detail: "Destination is disabled" };
  if (CREDENTIAL_OUTPUTS.has(destination.output_type) && !destination.secret_configured) {
    return { state: "error", detail: "Destination credentials are unavailable" };
  }
  const testResult = destinationTestResult(destination);
  if (testResult && !testResult.success) {
    return {
      state: "error",
      detail: `Last destination test failed: ${destinationTestDetail(testResult)}`,
    };
  }
  if (testResult && testResult.success) {
    if (destination.output_type === "teams" && testResult.response_status === 202) {
      return {
        state: "active",
        detail: "Last Microsoft Teams test was accepted with HTTP 202; confirm it appeared in the channel",
      };
    }
    return {
      state: "active",
      detail: `Last destination test passed${testResult.response_status ? ` with HTTP ${testResult.response_status}` : ""}`,
    };
  }
  return { state: "active", detail: "Destination is enabled and configured" };
}

function destinationTestToast(delivery, outputType) {
  const detail = delivery.response_status
    ? `HTTP ${delivery.response_status}`
    : delivery.safe_error || delivery.error_code || "No status returned";
  if (!delivery.success) {
    return {
      message: `Test delivery failed (${detail}).`,
      style: "error",
    };
  }
  if (outputType === "teams" && delivery.response_status === 202) {
    return {
      message: "Microsoft Teams accepted the test (HTTP 202). Delivery is not confirmed; check the channel.",
      style: "",
    };
  }
  return {
    message: `Test delivery sent successfully (${detail}).`,
    style: "success",
  };
}

function updateDestinationState(updated) {
  if (!updated || !updated.id) return false;
  const index = state.destinations.findIndex((item) => item.id === updated.id);
  if (index < 0) return false;
  state.destinations[index] = {
    ...state.destinations[index],
    ...updated,
  };
  renderDestinations();
  renderFlow();
  return true;
}

async function refreshDestinationState() {
  if (!state.user || document.visibilityState === "hidden") return false;
  if (destinationStateSyncPromise) return destinationStateSyncPromise;

  const previous = JSON.stringify({
    destinations: state.destinations,
    privateResources: state.privateDestinations,
    errors: state.destinationErrors,
  });

  destinationStateSyncPromise = request("/destinations", {
    reauthenticate: false,
  }).then((value) => {
    const nextDestinations = value.destinations || [];
    const nextPrivateResources = Array.isArray(value.private_resources)
      ? value.private_resources
      : [];
    const nextErrors = value.errors || [];
    const current = JSON.stringify({
      destinations: nextDestinations,
      privateResources: nextPrivateResources,
      errors: nextErrors,
    });
    if (current === previous) return false;

    state.destinations = nextDestinations;
    state.privateDestinations = nextPrivateResources;
    state.destinationErrors = nextErrors;
    renderWorkspaceErrors();
    renderDestinations();
    renderFlow();
    document.dispatchEvent(new CustomEvent("nowlert:filtering-state-invalidated"));
    document.dispatchEvent(new CustomEvent("nowlert:routing-topology-changed"));
    return true;
  }).catch((error) => {
    if (error instanceof APIError && error.status === 401) return false;
    throw error;
  }).finally(() => {
    destinationStateSyncPromise = null;
  });

  return destinationStateSyncPromise;
}

function destinationFlowLabels(destination) {
  if (!destination) return { name: "Missing destination", detail: "Configuration error" };
  const platform = OUTPUT_NAMES[destination.output_type] || friendlyName(destination.output_type);
  const settings = destination.settings || {};
  const channel = String(settings.channel_name || settings.channel || "").trim();
  return {
    name: destination.name,
    detail: channel ? `${platform} · ${channel}` : platform,
  };
}

function combinedFlowState(...states) {
  if (states.some((item) => item.state === "error")) return "error";
  if (states.some((item) => item.state === "disabled")) return "disabled";
  return "active";
}

function flowSignal(status, detail, delayed = false) {
  const symbols = { active: "➜", disabled: "⊘︎", error: "✕" };
  return element("span", {
    className: `flow-arrow flow-${status}${delayed ? " delayed" : ""}`,
    text: symbols[status] || symbols.error,
    title: detail,
    attributes: { "aria-label": detail, role: "img" },
  });
}

function renderFlow() {
  const container = byId("dashboard-flow");
  container.replaceChildren();
  for (const route of state.routes) {
    const destination = state.destinations.find((item) => item.id === route.destination_id);
    const inputStatus = inputFlowState(route.input_type || "http");
    const routeStatus = routeFlowState(route);
    const destinationStatus = destinationFlowState(destination);
    const destinationLabels = destinationFlowLabels(destination);
    const firstStatus = combinedFlowState(inputStatus, routeStatus);
    const descriptor = routeSourceDescriptor(route.source, route.input_type);
    const integration = integrationBySource(route.source);
    const iconKey = route.source === "*" ? "generic" : integration ? integration.icon_key : route.source;
    const category = route.source === "*" ? SOURCE_CATEGORIES.generic : sourceCategory(route.source);
    container.append(element("div", { className: `flow-row source-${inputStatus.state}` }, [
      element("div", {
        className: `flow-node source-node category-${category.key} state-${inputStatus.state}`,
        title: inputStatus.detail,
      }, [sourceIcon(iconKey), element("div", {}, [element("strong", { text: descriptor.integration }), element("small", { text: descriptor.input })])]),
      element("div", {
        className: `flow-route state-${routeStatus.state}`,
        title: routeStatus.detail,
      }, [
        flowSignal(firstStatus, `${inputStatus.detail}; ${routeStatus.detail}`),
        element("div", {}, [element("strong", { text: route.name }), element("small", { text: filterSummary(route.filters, route.source) })]),
        flowSignal(destinationStatus.state, destinationStatus.detail, true),
      ]),
      element("div", {
        className: `flow-node destination-node state-${destinationStatus.state}`,
        title: destinationStatus.detail,
      }, [outputIcon(destination && destination.output_type), element("div", {}, [element("strong", { text: destinationLabels.name }), element("small", { text: destinationLabels.detail })])]),
    ]));
  }
  if (!container.children.length) empty(container, "No routing flow", "Create a destination and route to display it here.");
}

function discoveredSources() {
  return state.integrations.map((item) => item.id);
}

const INTEGRATION_SETTING_LABELS = {
  xo: "Xen Orchestra",
  zabbix: "Zabbix",
  dell_idrac: "Dell iDRAC",
  unifi_protect: "UniFi Protect",
  home_assistant: "Home Assistant",
  redfish: "Redfish transport",
};

const INTEGRATION_SETTING_HELP = {
  xo: "Control whether Xen Orchestra job and run identifiers are shown. Delivery selection belongs to Routes.",
  zabbix: "Control whether Zabbix problem identifiers are included in notifications.",
  dell_idrac: "Suppress successful IPMI session login/logout audits from trusted management clients. Failed authentication is never suppressed.",
  unifi_protect: "Map camera or console MAC addresses to readable names. Use one ‘MAC = Alias’ entry per line.",
  home_assistant: "Map Home Assistant endpoints and components to readable device names.",
  redfish: "Set the shared duplicate-event window for Dell iDRAC, HPE iLO, Supermicro, and generic Redfish.",
};

function renderIntegrationSettings() {
  const container = byId("integration-settings-list");
  if (!container) return;
  container.replaceChildren();
  for (const source of Object.keys(INTEGRATION_SETTING_LABELS)) {
    const failure = state.integrationSettingsErrors.find((item) => item.resource === source);
    const summary = integrationSettingSummary(source, state.integrationSettings[source] || {});
    container.append(element("article", { className: "resource-card compact-resource-card" }, [
      element("div", { className: "resource-card-heading" }, [
        element("div", {}, [
          element("strong", { text: INTEGRATION_SETTING_LABELS[source] }),
          element("small", { text: failure ? failure.message : summary }),
        ]),
        failure ? badge("Needs repair", "danger") : badge("Database", "success"),
      ]),
      element("div", { className: "resource-actions" }, [
        actionButton("Edit", "edit-integration-settings", source),
      ]),
    ]));
  }
}

function integrationSettingSummary(source, settings) {
  if (source === "xo") return `Job and run IDs ${settings.show_ids ? "shown" : "hidden"}`;
  if (source === "zabbix") return `Problem IDs ${settings.show_ids ? "shown" : "hidden"}`;
  if (source === "dell_idrac") return `${(settings.suppress_ipmi_session_audit_from || []).length} trusted client(s)`;
  if (source === "unifi_protect") return `${Object.keys(settings.device_aliases || {}).length} device alias(es)`;
  if (source === "home_assistant") {
    const aliases = settings.aliases || {};
    return `${Object.keys(aliases.endpoints || {}).length} endpoint and ${Object.keys(aliases.components || {}).length} component alias(es)`;
  }
  return `${Number(settings.deduplication_window_seconds || 0)} second deduplication window`;
}

function settingCheckbox(id, label, checked) {
  const input = element("input", { type: "checkbox" });
  input.id = id;
  input.checked = Boolean(checked);
  return element("label", { className: "switch-field" }, [input, element("span", { text: label })]);
}

function settingTextarea(id, label, value, placeholder, rows = 7) {
  const input = element("textarea", { attributes: { rows, placeholder } });
  input.id = id;
  input.value = value;
  return element("label", { className: "wide" }, [element("span", { text: label }), input]);
}

function integrationSettingsSnapshot() {
  const fields = byId("integration-settings-fields");
  if (!fields) return "";
  return JSON.stringify(
    [...fields.querySelectorAll("input, select, textarea")].map((field) => ({
      id: field.id,
      type: field.type,
      value: ["checkbox", "radio"].includes(field.type) ? field.checked : field.value,
    })),
  );
}

function integrationSettingsChanged() {
  return integrationSettingsSnapshot() !== state.integrationSettingsBaseline;
}

async function closeIntegrationSettings() {
  const dialog = byId("integration-settings-dialog");
  if (!dialog || !dialog.open) return;
  if (integrationSettingsChanged()) {
    const discard = await confirmAction(
      "Discard unsaved changes?",
      "The integration settings were changed. Exit without saving them?",
      "Discard changes",
    );
    if (!discard) return;
  }
  state.integrationSettingsBaseline = "";
  dialog.close("cancel");
}

function formatMac(value) {
  return String(value || "").replace(/[^0-9a-f]/gi, "").toUpperCase().match(/.{1,2}/g)?.join(":") || String(value || "");
}

function openIntegrationSettings(source) {
  const settings = state.integrationSettings[source];
  if (!settings) {
    toast("Integration settings are unavailable.", "error");
    return;
  }
  byId("integration-settings-source").value = source;
  byId("integration-settings-title").textContent = INTEGRATION_SETTING_LABELS[source] || friendlyName(source);
  byId("integration-settings-help").textContent = INTEGRATION_SETTING_HELP[source] || "";
  clearError("integration-settings-error");
  const fields = byId("integration-settings-fields");
  fields.replaceChildren();
  if (source === "xo") {
    fields.append(
      settingCheckbox("integration-xo-show-ids", "Show job and run IDs", settings.show_ids),
    );
  } else if (source === "zabbix") {
    fields.append(settingCheckbox("integration-zabbix-show-ids", "Show Zabbix problem IDs", settings.show_ids));
  } else if (source === "dell_idrac") {
    fields.append(settingTextarea(
      "integration-dell-trusted-ips",
      "Trusted client IP addresses",
      (settings.suppress_ipmi_session_audit_from || []).join("\n"),
      "192.0.2.164\n192.0.2.251",
    ));
  } else if (source === "unifi_protect") {
    const lines = Object.entries(settings.device_aliases || {}).map(([key, value]) => `${formatMac(key)} = ${value}`);
    fields.append(settingTextarea(
      "integration-unifi-aliases",
      "Device aliases",
      lines.join("\n"),
      "AC:8B:A9:0D:D8:AD = CAM-01 | Hall Out",
      10,
    ));
  } else if (source === "home_assistant") {
    const aliases = settings.aliases || {};
    const endpoints = Object.entries(aliases.endpoints || {}).map(([key, value]) => `${key} = ${value.device || ""}`);
    const components = Object.entries(aliases.components || {}).map(([key, value]) => `${key} = ${value.device || ""}${value.endpoint ? ` => ${value.endpoint}` : ""}`);
    fields.append(
      settingTextarea("integration-ha-endpoints", "Endpoint aliases", endpoints.join("\n"), "192.0.2.35 = HUB-01 | Hall Floor 1"),
      settingTextarea("integration-ha-components", "Component aliases", components.join("\n"), "homeassistant.components.ipp.coordinator = PRT-01 | Floor 1 => 192.0.2.157", 9),
    );
  } else if (source === "redfish") {
    const input = element("input", { type: "number", value: settings.deduplication_window_seconds, attributes: { min: 0, max: 86400, step: 1, required: "" } });
    input.id = "integration-redfish-window";
    fields.append(element("label", {}, [element("span", { text: "Deduplication window (seconds)" }), input]));
  }
  state.integrationSettingsBaseline = integrationSettingsSnapshot();
  byId("integration-settings-dialog").showModal();
}

function parseMappingLines(value, label, component = false) {
  const result = {};
  for (const rawLine of String(value || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const position = line.indexOf("=");
    if (position < 1) throw new Error(`${label} entries must use “key = value”.`);
    const key = line.slice(0, position).trim();
    const rawValue = line.slice(position + 1).trim();
    if (!key || !rawValue) throw new Error(`${label} entries require both a key and value.`);
    if (component) {
      const separator = rawValue.lastIndexOf("=>");
      const device = (separator >= 0 ? rawValue.slice(0, separator) : rawValue).trim();
      const endpoint = separator >= 0 ? rawValue.slice(separator + 2).trim() : "";
      if (!device) throw new Error(`${label} entries require a device name.`);
      if (separator >= 0 && !endpoint) throw new Error(`${label} entries require an endpoint after “=>”.`);
      result[key] = { device };
      if (endpoint) result[key].endpoint = endpoint;
    } else {
      result[key] = rawValue;
    }
  }
  return result;
}

async function saveIntegrationSettings(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    await closeIntegrationSettings();
    return;
  }
  const source = byId("integration-settings-source").value;
  let body;
  try {
    if (source === "xo") {
      body = {
        show_ids: byId("integration-xo-show-ids").checked,
      };
    } else if (source === "zabbix") {
      body = { show_ids: byId("integration-zabbix-show-ids").checked };
    } else if (source === "dell_idrac") {
      body = {
        suppress_ipmi_session_audit_from: byId("integration-dell-trusted-ips").value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      };
    } else if (source === "unifi_protect") {
      body = { device_aliases: parseMappingLines(byId("integration-unifi-aliases").value, "Device alias") };
    } else if (source === "home_assistant") {
      const endpoints = parseMappingLines(byId("integration-ha-endpoints").value, "Endpoint alias");
      body = {
        aliases: {
          endpoints: Object.fromEntries(Object.entries(endpoints).map(([key, device]) => [key, { device }])),
          components: parseMappingLines(byId("integration-ha-components").value, "Component alias", true),
        },
      };
    } else if (source === "redfish") {
      body = { deduplication_window_seconds: Number(byId("integration-redfish-window").value) };
    } else {
      throw new Error("Integration settings are not supported.");
    }
    const response = await request(`/integration-settings/${encodeURIComponent(source)}`, { method: "PUT", body });
    state.integrationSettings[source] = response.settings;
    state.integrationSettingsErrors = state.integrationSettingsErrors.filter((item) => item.resource !== source);
    state.integrationSettingsBaseline = "";
    byId("integration-settings-dialog").close();
    renderIntegrationSettings();
    toast(`${INTEGRATION_SETTING_LABELS[source]} settings saved.`);
  } catch (error) {
    showError("integration-settings-error", error);
  }
}

function renderSources() {
  const body = byId("source-table");
  body.replaceChildren();
  byId("source-empty").hidden = state.integrations.length > 0;
  if (!state.integrations.length) {
    byId("source-empty").replaceChildren(
      element("strong", { text: "No integrations available" }),
      element("span", { text: "The built-in integration catalogue could not be loaded." }),
    );
    return;
  }
  for (const integration of state.integrations) {
    const category = SOURCE_CATEGORIES[integration.category] || SOURCE_CATEGORIES.generic;
    const select = element("select", {
      dataset: { integrationCategory: integration.id },
      disabled: !isAdmin(),
      attributes: { "aria-label": `Category for ${integration.name}` },
    });
    for (const item of Object.values(SOURCE_CATEGORIES)) {
      select.append(element("option", { value: item.key, text: item.label }));
    }
    select.value = category.key;
    const details = element(
      "div",
      { className: "integration-input-chips" },
      integration.inputs.map((item) => badge(item.name, "input")),
    );
    body.append(element("tr", {}, [
      element("td", {}, [element("div", { className: "source-identity" }, [sourceIcon(integration.icon_key || integration.id), element("div", {}, [element("strong", { text: integration.name }), element("small", { text: "Built-in integration" })])])]),
      element("td", {}, details),
      element("td", {}, select),
    ]));
  }
}

async function saveSourceCategory(event) {
  const select = event.target.closest("[data-integration-category]");
  if (!select || !isAdmin()) return;
  const integrationId = select.dataset.integrationCategory;
  select.disabled = true;
  try {
    const response = await request("/integrations", {
      method: "PUT",
      body: { source: integrationId, category: select.value },
    });
    state.integrations = response.integrations || [];
    state.routeSourceOptions = response.route_options || [];
    renderSources();
    renderFlow();
    const integration = integrationBySource(integrationId);
    toast(`${integration ? integration.name : friendlyName(integrationId)} moved to ${SOURCE_CATEGORIES[select.value].label}.`);
  } catch (error) {
    renderSources();
    toast(error.message || "Integration category could not be saved.", "error");
  }
}

function renderDestinations() {
  const container = byId("destination-list");
  container.replaceChildren();
  if (!state.destinations.length) {
    empty(container, "No destinations", "Add an output to preview payloads and receive routed events.");
    return;
  }
  for (const item of state.destinations) {
    const editable = ownResource(item);
    const canTest = editable || isAdmin() || item.shared;
    const actions = element("div", { className: "resource-actions" });
    if (editable) {
      actions.append(
        actionButton("Edit", "edit-destination", item.id),
        actionButton("Send test", "test-destination-card", item.id, "primary"),
        actionButton("Preview", "preview-destination", item.id),
        actionButton("Delete", "delete-destination", item.id, "danger"),
      );
    } else {
      actions.append(actionButton("Preview", "preview-destination", item.id));
      if (canTest) {
        actions.append(actionButton("Send test", "test-destination-card", item.id, "primary"));
      }
    }
    const testResult = destinationTestResult(item);
    const metaItems = [
      element("button", {
        className: `badge status-button ${item.enabled ? "success" : "danger"}`,
        text: item.enabled ? "Enabled" : "Disabled",
        type: "button",
        disabled: !editable,
        dataset: { action: "toggle-destination", id: item.id },
      }),
      element("button", {
        className: `badge status-button ${item.shared ? "success" : "warning"}`,
        text: item.shared ? "Shared" : "Private",
        type: "button",
        disabled: !editable,
        dataset: { action: "toggle-destination-shared", id: item.id },
      }),
    ];
    const ownerUsername = String(
      item.owner_username || (ownResource(item) ? state.user?.username : "") || "",
    ).trim();
    if (ownerUsername) {
      metaItems.push(element("span", {
        className: "badge destination-owner-badge",
        text: ownerUsername,
      }));
    }
    if (!editable) {
      metaItems.push(element("span", {
        className: "badge destination-view-only-badge",
        text: "View only",
      }));
    }
    if (!item.secret_configured && ["discord", "teams", "slack", "webhook"].includes(item.output_type)) {
      metaItems.push(badge("Credentials required", "danger"));
    }
    if (testResult) {
      const resultBadge = badge(
        testResult.success ? "Last test passed" : "Last test failed",
        testResult.success ? "success" : "danger",
      );
      resultBadge.title = destinationTestDetail(testResult);
      metaItems.push(resultBadge);
    }
    const meta = element("div", { className: "resource-meta" }, metaItems);
    const testFailure = testResult && !testResult.success
      ? element("small", {
          className: "destination-test-detail",
          text: destinationTestDetail(testResult),
        })
      : null;
    container.append(element("article", { className: "resource-card" }, [
      element("div", { className: "resource-heading" }, [
        element("div", { className: "resource-identity" }, [
          element("span", { className: "resource-icon" }, outputIcon(item.output_type)),
          element("div", {}, [element("strong", { text: item.name }), element("small", { text: `${OUTPUT_NAMES[item.output_type] || friendlyName(item.output_type)} · ${item.settings.channel_name || "Channel not labelled"}` })]),
        ]),
      ]),
      meta,
      testFailure,
      actions,
    ]));
  }
}

function destinationName(id) {
  const item = state.destinations.find((candidate) => candidate.id === id);
  return item ? item.name : "Unavailable destination";
}

function destinationTypeName(id) {
  const item = state.destinations.find((candidate) => candidate.id === id);
  return item ? (OUTPUT_NAMES[item.output_type] || friendlyName(item.output_type)) : "Unavailable destination";
}

const ROUTE_ALL_EVENT_FILTERS = {
  severities: new Set([
    "debug",
    "information",
    "warning",
    "error",
    "critical",
    "failure",
  ]),
  statuses: new Set([
    "active",
    "resolved",
    "firing",
    "recovered",
    "success",
    "skipped",
    "failure",
  ]),
};

function routeFilterValuesForSource(source = "", key) {
  const fallback = ROUTE_ALL_EVENT_FILTERS[key];

  if (source === "*") {
    return fallback ? [...fallback] : [];
  }

  const integration = integrationBySource(source);

  if (!integration || !integration.route_filters) {
    return fallback ? [...fallback] : [];
  }

  const configured = integration.route_filters[key];

  if (!Array.isArray(configured)) return [];

  return [
    ...new Set(
      configured
        .map((value) => String(value || "").trim().toLowerCase())
        .filter(Boolean),
    ),
  ];
}

function routeSelectedSource() {
  const select = byId("route-source");
  if (!select) return "";

  const [source] = String(select.value || "").split("::", 2);
  return source || "";
}

function currentRouteFilterSelections() {
  const filters = {};

  for (const key of ["severities", "statuses"]) {
    const select = byId(`route-${key}`);
    if (!select) continue;

    const values = [...select.selectedOptions]
      .map((option) => option.value);

    if (values.length) {
      filters[key] = values;
    }
  }

  return filters;
}

function routeFilterHasAllEvents(key, values, source = "") {
  const availableValues = routeFilterValuesForSource(source, key);
  const available = new Set(availableValues);

  if (
    !available.size
    || !Array.isArray(values)
    || values.length !== available.size
  ) {
    return false;
  }

  const selected = new Set(
    values.map((value) => String(value || "").toLowerCase()),
  );

  return (
    selected.size === available.size
    && [...available].every((value) => selected.has(value))
  );
}

function routeAllowedFilterValues(
  key,
  filters = {},
  source = "",
) {
  const availableValues = routeFilterValuesForSource(source, key);
  const available = new Set(availableValues);

  if (!available.size) return [];

  const includedValues = (
    filters
    && Array.isArray(filters[key])
    && filters[key].length
  )
    ? filters[key]
    : availableValues;

  const excludedKey = `exclude_${key}`;
  const excludedValues = (
    filters
    && Array.isArray(filters[excludedKey])
  )
    ? filters[excludedKey]
    : [];

  const included = new Set(
    includedValues.map(
      (value) => String(value || "").toLowerCase(),
    ),
  );

  const excluded = new Set(
    excludedValues.map(
      (value) => String(value || "").toLowerCase(),
    ),
  );

  return availableValues.filter(
    (value) => included.has(value) && !excluded.has(value),
  );
}

function refreshRouteFilterLayout() {
  const grid = document.querySelector(".route-filter-grid");
  if (!grid) return;

  const fields = [...grid.children].filter(
    (field) => field.matches("label"),
  );

  for (const field of fields) {
    field.style.gridRow = "";
    field.style.gridColumn = "";
  }

  grid.style.gridAutoFlow = "row";
  grid.style.gridAutoRows = "auto";

  const columns = getComputedStyle(grid)
    .gridTemplateColumns
    .split(/\s+/)
    .filter(Boolean)
    .length;

  if (columns < 2) return;

  const visibleSelectors = [
    byId("route-severities"),
    byId("route-statuses"),
  ]
    .map((select) => select && select.closest("label"))
    .filter((field) => field && !field.hidden);

  visibleSelectors.forEach((field, index) => {
    field.style.gridRow = "1";
    field.style.gridColumn = String(index + 1);
  });

  const firstTextRow = visibleSelectors.length ? 2 : 1;
  const pairedFields = [
    ["route-hosts", "route-exclude_hosts"],
    ["route-events", "route-exclude_events"],
  ];

  pairedFields.forEach((ids, rowOffset) => {
    ids.forEach((id, columnOffset) => {
      const input = byId(id);
      const field = input && input.closest("label");
      if (!field || field.hidden) return;
      field.style.gridRow = String(firstTextRow + rowOffset);
      field.style.gridColumn = String(columnOffset + 1);
    });
  });
}

function scheduleRouteFilterLayout() {
  const grid = document.querySelector(".route-filter-grid");
  if (!grid) return;

  if (grid.dataset.layoutFrame) {
    window.cancelAnimationFrame(
      Number(grid.dataset.layoutFrame),
    );
  }

  const frame = window.requestAnimationFrame(() => {
    delete grid.dataset.layoutFrame;
    refreshRouteFilterLayout();
  });

  grid.dataset.layoutFrame = String(frame);

  if (grid.dataset.layoutResizeBound !== "1") {
    grid.dataset.layoutResizeBound = "1";
    window.addEventListener(
      "resize",
      scheduleRouteFilterLayout,
    );
  }
}

function refreshRouteFilterOptions(filters = {}) {
  const source = routeSelectedSource();

  for (const key of ["severities", "statuses"]) {
    const select = byId(`route-${key}`);
    if (!select) continue;

    const field = select.closest("label");
    const values = routeFilterValuesForSource(source, key);
    const selected = new Set(
      routeAllowedFilterValues(key, filters, source),
    );

    select.replaceChildren();

    for (const value of values) {
      const option = element("option", {
        value,
        text: capitalize(value),
      });
      option.selected = selected.has(value);
      option.setAttribute(
        "aria-selected",
        option.selected ? "true" : "false",
      );
      select.append(option);
    }

    select.disabled = values.length === 0;
    select.size = Math.max(values.length, 2);

    if (field) {
      field.hidden = values.length === 0;
    }
  }

  const sourceSelect = byId("route-source");
  if (sourceSelect) {
    sourceSelect.dataset.routeFilterSource = source;
  }

  scheduleRouteFilterLayout();
}

function filterSummary(filters, source = "") {
  const parts = [];

  const labels = {
    severities: "Include severity",
    statuses: "Include status",
    hosts: "Include host",
    events: "Include event",
    exclude_severities: "Exclude severity",
    exclude_statuses: "Exclude status",
    exclude_hosts: "Exclude host",
    exclude_events: "Exclude event",
  };

  const fullLabels = {
    severities: "All Severities",
    statuses: "All Statuses",
  };

  for (const key of Object.keys(labels)) {
    const values = filters && filters[key];
    if (!Array.isArray(values) || !values.length) continue;

    const enumeratedKey = key.startsWith("exclude_")
      ? key.slice("exclude_".length)
      : key;

    if (
      ["severities", "statuses"].includes(enumeratedKey)
      && !routeFilterValuesForSource(source, enumeratedKey).length
    ) {
      continue;
    }

    if (
      (key === "severities" || key === "statuses")
      && routeFilterHasAllEvents(key, values, source)
    ) {
      parts.push(fullLabels[key]);
      continue;
    }

    if (
      key === "exclude_severities"
      && routeFilterHasAllEvents(
        "severities",
        values,
        source,
      )
    ) {
      parts.push(`${labels[key]}: All Events`);
      continue;
    }

    if (
      key === "exclude_statuses"
      && routeFilterHasAllEvents(
        "statuses",
        values,
        source,
      )
    ) {
      parts.push(`${labels[key]}: All Events`);
      continue;
    }

    parts.push(
      `${labels[key]}: ${values.map(capitalize).join(", ")}`,
    );
  }

  const fullOnly = new Set(
    Object.values(fullLabels),
  );

  if (
    parts.length
    && parts.every((part) => fullOnly.has(part))
  ) {
    return "All Events";
  }

  if (
    parts.length === 1
    && filters
    && filters.severities
    && filters.severities.length === 1
    && filters.severities[0] === "critical"
  ) {
    return "Just Critical";
  }

  return parts.join(" · ") || "All Events";
}

function renderRoutes() {
  const body = byId("route-table");
  body.replaceChildren();
  byId("route-empty").hidden = state.routes.length > 0;
  if (!state.routes.length) {
    byId("route-empty").replaceChildren(element("strong", { text: "No routes" }), element("span", { text: "Create a route after adding a destination." }));
    return;
  }
  for (const item of state.routes) {
    const descriptor = routeSourceDescriptor(item.source, item.input_type);
    const name = isAdmin()
      ? element("button", { className: "route-name-button", text: item.name, type: "button", dataset: { action: "edit-route", id: item.id } })
      : element("strong", { text: item.name });
    const status = element("button", {
      className: `badge status-button ${item.enabled ? "success" : "warning"}`,
      text: item.enabled ? "Enabled" : "Disabled",
      type: "button",
      disabled: !isAdmin(),
      dataset: { action: "toggle-route", id: item.id },
    });
    body.append(element("tr", {}, [
      element("td", {}, name),
      element("td", { text: descriptor.integration }),
      element("td", { text: descriptor.input }),
      element("td", { text: destinationTypeName(item.destination_id) }),
      element("td", {}, element("small", { text: filterSummary(item.filters, item.source) })),
      element("td", { text: capitalize(item.priority_name || "normal") }),
      element("td", {}, status),
      element("td", {}, isAdmin() ? actionButton("Delete", "delete-route", item.id, "danger") : null),
    ]));
  }
}

function renderTokens() {
  const body = byId("token-table");
  body.replaceChildren();
  byId("token-empty").hidden = state.tokens.length > 0;
  if (!state.tokens.length) {
    byId("token-empty").replaceChildren(element("strong", { text: "No Event API tokens" }), element("span", { text: "Issue a source-scoped token only for an external application that posts to /api/v2/events." }));
    return;
  }
  for (const item of state.tokens) {
    const yamlManaged = item.management === "yaml";
    const unavailable = yamlManaged && item.credential_available === false;
    const revoked = Boolean(item.revoked_at);
    const inactive = item.enabled === false || unavailable;
    const actions = element("div", { className: "row-actions" });
    if (!revoked) {
      actions.append(
        actionButton("Delete", "delete-token", item.id, "danger"),
      );
      if (!yamlManaged) actions.prepend(actionButton("Rotate", "rotate-token", item.id));
    }
    body.append(element("tr", {}, [
      element("td", {}, [element("strong", { text: item.name }), element("small", { text: yamlManaged ? `Configured credential · ${item.credential_source}` : `Issued credential · version ${item.version}` })]),
      element("td", { text: item.source_scopes.map(friendlyName).join(", ") || "None" }),
      element("td", { text: `${item.rate_limit_per_minute}/min` }),
      element("td", { text: item.last_used_at ? relativeTime(item.last_used_at) : "Never used" }),
      element("td", {}, element("button", {
        className: `badge status-button ${unavailable || revoked ? "danger" : inactive ? "warning" : "success"}`,
        text: unavailable ? "Credential unavailable" : revoked ? "Revoked" : inactive ? "Inactive" : "Active",
        type: "button",
        disabled: unavailable || revoked,
        dataset: { action: "toggle-token", id: item.id },
      })),
      element("td", {}, actions),
    ]));
  }
}

function renderDeliveries() {
  const query = byId("delivery-search").value.trim().toLowerCase();
  const items = state.deliveries.filter((item) => JSON.stringify([item.source, item.device_name, item.event_name, item.title, item.outcome, item.safe_error, item.error_code]).toLowerCase().includes(query));
  const container = byId("delivery-list");
  container.replaceChildren();
  if (!items.length) {
    empty(container, query ? "No matching deliveries" : "No delivery history", query ? "Try a different search." : "Delivery attempts appear after matched events are submitted.");
    return;
  }
  for (const item of items) {
    const delivered = ["delivered", "success"].includes(item.outcome);
    const semantic = String(item.event_status || item.severity || item.outcome || "").toLowerCase();
    const semanticFailure = ["error", "failure", "failed", "critical", "severe"].includes(semantic);
    const semanticInformation = ["information", "info", "informational"].includes(semantic);
    const style = semanticFailure ? "danger" : semanticInformation ? "information" : delivered ? "success" : item.retryable ? "warning" : "danger";
    const error = item.safe_error || item.error_code || (delivered ? "Delivery completed" : "No transport error reported");
    const heading = item.device_name
      ? `${item.device_name} • ${item.event_name || item.title || "Event"}`
      : `${friendlyName(item.source)} • ${item.event_name || item.title || "Untitled event"}`;
    const statusText = capitalize(item.event_status || item.severity || item.outcome);
    container.append(element("article", { className: `timeline-item ${style}` }, [
      element("span", { className: "event-indicator", text: semanticFailure ? "!" : semanticInformation ? "i" : delivered ? "✓" : "!" }),
      element("div", {}, [
        element("strong", { text: heading }),
        element("small", { className: "delivery-context", text: `${friendlyName(item.source)} • ${semanticFailure ? "🚨" : "✓"} ${statusText}${item.device_name ? ` • 📍 ${item.device_name}` : ""}` }),
        element("p", { className: "event-description", text: item.event_description || error }),
        element("div", { className: "resource-meta" }, [badge(delivered ? "Delivered" : capitalize(item.outcome), delivered ? "success" : "danger"), badge(capitalize(item.severity), style), badge(statusText, style), badge(`Attempt ${item.attempt_number}`), badge(`Input ${item.input_type || sourceInputType(item.source)}`), item.response_status ? badge(`Destination HTTP ${item.response_status}`) : null]),
      ]),
      element("div", { className: "timeline-meta" }, [element("span", { text: formatTime(item.completed_at || item.created_at) }), item.retryable ? element("small", { text: "Retryable" }) : null]),
    ]));
  }
}

function auditActionLabel(value) {
  const parts = String(value || "")
    .split(".")
    .filter(Boolean)
    .map(capitalize);

  return parts.length ? parts.join(" · ") : "Unknown action";
}

function auditActorLabel(item) {
  if (item.actor_username) return item.actor_username;

  if (item.actor_user_id) {
    return `User ${String(item.actor_user_id).slice(0, 8)}`;
  }

  if (item.action === "session.login" && item.outcome !== "success") {
    return "Unauthenticated";
  }

  return "System";
}

function auditDetailValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

function auditDetailsText(details) {
  if (!details || typeof details !== "object") return "No additional details";

  const entries = Object.entries(details);
  if (!entries.length) return "No additional details";

  return entries
    .map(([key, value]) => `${friendlyName(key)}: ${auditDetailValue(value)}`)
    .join(" · ");
}

function renderAudit() {
  const query = byId("audit-search").value.trim().toLowerCase();

  const items = state.audit
    .filter((item) => JSON.stringify([
      item.action,
      item.actor_username,
      item.actor_user_id,
      item.resource_type,
      item.resource_id,
      item.outcome,
      item.details,
    ]).toLowerCase().includes(query))
    .slice(0, state.auditPageSize);

  const body = byId("audit-table");
  body.replaceChildren();
  byId("audit-empty").hidden = items.length > 0;

  if (!items.length) {
    byId("audit-empty").replaceChildren(
      element("strong", {
        text: query ? "No matching audit events" : "No audit events",
      }),
      element("span", {
        text: query
          ? "Try a different search."
          : "Security-relevant activity appears here.",
      }),
    );
    return;
  }

  for (const item of items) {
    const actor = auditActorLabel(item);
    const resource = friendlyName(item.resource_type);
    const resourceId = String(item.resource_id || "");

    body.append(element("tr", {}, [
      element("td", { text: formatTime(item.created_at) }),
      element("td", {}, [
        element("strong", { text: auditActionLabel(item.action) }),
        element("small", { text: item.action || "unknown" }),
      ]),
      element("td", {}, [
        element("strong", { text: actor }),
        item.actor_user_id
          ? element("small", {
              text: `ID ${String(item.actor_user_id).slice(0, 8)}`,
              title: String(item.actor_user_id),
            })
          : element("small", { text: "No authenticated user" }),
      ]),
      element("td", {}, [
        element("strong", { text: resource }),
        resourceId
          ? element("code", { text: resourceId, title: resourceId })
          : element("small", { text: "Platform-level action" }),
      ]),
      element(
        "td",
        {},
        badge(
          item.outcome,
          item.outcome === "success" ? "success" : "danger",
        ),
      ),
      element(
        "td",
        {},
        element("small", { text: auditDetailsText(item.details) }),
      ),
    ]));
  }
}

function renderUsers() {
  const body = byId("user-table");
  body.replaceChildren();
  if (!isAdmin()) return;
  for (const item of state.users) {
    const self = item.id === state.user.id;
    const actions = element("div", { className: "row-actions" });
    if (!self) {
      actions.append(
        actionButton("Reset password", "reset-user", item.id),
        actionButton("Delete", "delete-user", item.id, "danger"),
      );
    }
    body.append(element("tr", {}, [
      element("td", {}, element("div", { className: "user-cell" }, [avatarElement(item), element("div", {}, [element("strong", { text: item.username }), element("small", { text: self ? "Current account" : item.id.slice(0, 8) })])])),
      element("td", { text: item.role }),
      element("td", { text: formatTime(item.last_login_at) }),
      element("td", {}, element("button", {
        className: `badge status-button ${item.enabled ? "success" : "danger"}`,
        text: item.enabled ? "Enabled" : "Disabled",
        type: "button",
        disabled: self,
        dataset: { action: "toggle-user", id: item.id },
      })),
      element("td", {}, actions),
    ]));
  }
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function formatClockValue(value) {
  const [rawHour, rawMinute] = String(value || "00:00").split(":");
  const hour = Number(rawHour);
  const minute = String(rawMinute || "00").padStart(2, "0");
  if (state.preferences.time_format === "12") {
    return `${hour % 12 || 12}:${minute} ${hour < 12 ? "AM" : "PM"}`;
  }
  return `${String(hour).padStart(2, "0")}:${minute}`;
}

function renderClockOptions(select, selected) {
  if (!select) return;
  const current = String(selected || "00:00");
  const values = [];
  for (let hour = 0; hour < 24; hour += 1) {
    for (const minute of [0, 15, 30, 45]) {
      values.push(`${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`);
    }
  }
  if (!values.includes(current)) values.push(current);
  values.sort();
  select.replaceChildren(...values.map((value) =>
    element("option", { value, text: formatClockValue(value) })
  ));
  select.value = current;
}

function renderHousekeepingTimeOptions() {
  const value = state.housekeepingSettings?.time || "03:15";
  renderClockOptions(byId("housekeeping-time"), value);
}

function renderBackupTimeOptions() {
  const value = state.backupSettings?.time || "02:00";
  renderClockOptions(byId("backup-time"), value);
}

function backupSnapshotDetail(item) {
  const legacy = item.config_included ? "Full snapshot" : "Legacy state-only";
  const parts = [
    legacy,
    `${item.secret_files} file${Number(item.secret_files) === 1 ? "" : "s"}`,
    `DB schema ${item.schema_version}`,
  ];
  if (item.application_version) parts.push(`v${String(item.application_version).replace(/^v/i, "")}`);
  return parts.join(" · ");
}

function backupScheduleSummary() {
  const settings = state.backupSettings || {};
  const schedule = String(settings.schedule || "disabled");
  if (schedule === "disabled") {
    return { count: "0", detail: "Disabled" };
  }
  const time = formatClockValue(settings.time || "02:00");
  if (schedule === "daily") {
    return { count: "1", detail: `Daily · ${time}` };
  }
  if (schedule === "weekly") {
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    return { count: "1", detail: `Weekly · ${days[Number(settings.weekday || 0)]}, ${time}` };
  }
  return { count: "1", detail: `Monthly · day ${Number(settings.day || 1)}, ${time}` };
}

function backupNextRunLabel(settings) {
  const schedule = String(settings?.schedule || "disabled");
  const time = formatClockValue(settings?.time || "02:00");
  if (schedule === "disabled") return "Next run: Disabled";
  if (schedule === "daily") return `Next run: Daily at ${time}`;
  if (schedule === "weekly") {
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    return `Next run: ${days[Number(settings?.weekday || 0)]} at ${time}`;
  }
  return `Next run: Day ${Number(settings?.day || 1)} at ${time}`;
}

function backupSystemHealth() {
  const enabled = state.backupTargets.filter((item) => item.enabled);
  if (!enabled.length) {
    return { label: "Ready", note: "No external destinations enabled", healthy: true };
  }
  const writable = enabled.filter((item) => item.last_test_outcome === "success").length;
  const healthy = writable === enabled.length && state.externalBackupErrors.length === 0;
  return healthy
    ? { label: "Healthy", note: "All destinations writable", healthy: true }
    : { label: "Attention", note: `${writable} of ${enabled.length} destinations verified writable`, healthy: false };
}

function renderBackupOverview() {
  if (!isAdmin()) return;
  const counts = { local: 0, nfs: 0, smb: 0 };
  for (const item of state.backupTargets) {
    if (Object.hasOwn(counts, item.type)) counts[item.type] += 1;
  }
  const destinationTotal = state.backupTargets.length;
  const destinationNote = destinationTotal
    ? `${counts.local} local · ${counts.nfs} NFS · ${counts.smb} SMB`
    : "No destinations configured";
  const snapshotIds = new Set([
    ...state.backups.map((item) => item.id),
    ...state.externalBackups.map((item) => item.id),
  ]);
  const schedule = backupScheduleSummary();
  const health = backupSystemHealth();
  const allSnapshots = [...state.backups, ...state.externalBackups]
    .sort((left, right) => Number(right.created_at || 0) - Number(left.created_at || 0));
  const latest = allSnapshots[0];

  byId("backup-summary-destinations").textContent = String(destinationTotal);
  byId("backup-summary-destinations-note").textContent = destinationNote;
  byId("backup-summary-snapshots").textContent = String(snapshotIds.size);
  byId("backup-summary-snapshots-note").textContent = "Across all destinations";
  byId("backup-summary-schedule").textContent = schedule.count;
  byId("backup-summary-schedule-note").textContent = schedule.detail;
  byId("backup-summary-health").textContent = health.label;
  byId("backup-summary-health-note").textContent = health.note;
  byId("backup-last-backup").textContent = latest ? formatTime(latest.created_at) : "No backup yet";
  byId("backup-system-status").textContent = health.healthy ? "● All systems healthy" : "● Needs attention";
  byId("backup-system-status").classList.toggle("warning", !health.healthy);
}

function renderBackupRecoveryTable() {
  const body = byId("backup-recovery-table");
  if (!body) return;
  body.replaceChildren();
  const rows = state.showAllBackups ? state.backups : state.backups.slice(0, 4);
  if (!rows.length) {
    body.append(element("tr", {}, element("td", {
      text: "No local recovery snapshots yet.",
      attributes: { colspan: "5" },
    })));
  }
  for (const item of rows) {
    const type = String(item.backup_type || "manual").toUpperCase();
    body.append(element("tr", {}, [
      element("td", {}, [element("span", { className: "backup-row-dot", text: "●" }), formatTime(item.created_at)]),
      element("td", {}, badge(type, type === "SCHEDULED" ? "info" : "")),
      element("td", {}, [element("strong", { text: item.config_included ? "Full snapshot" : "Legacy state-only" }), element("small", { text: backupSnapshotDetail(item) })]),
      element("td", { text: formatBytes(item.size_bytes) }),
      element("td", {}, element("div", { className: "row-actions backup-row-actions" }, [
        backupIconAction("restore-backup", item.id, "Restore", "restore"),
        backupIconAction("delete-backup", item.id, "Delete", "trash", "danger"),
      ])),
    ]));
  }
  const button = byId("backup-view-all");
  if (button) {
    button.hidden = state.backups.length <= 4;
    const label = button.querySelector("span:last-child");
    if (label) label.textContent = state.showAllBackups ? "Show latest 4" : "View all snapshots";
  }
  const status = byId("backup-view-all-status");
  if (status) {
    const visible = rows.length;
    status.replaceChildren(
      document.createTextNode(`${visible} of ${state.backups.length} snapshots shown `),
      element("span", { text: "›", attributes: { "aria-hidden": "true" } }),
    );
  }
}

function renderStoredBackupTable() {
  const body = byId("backup-stored-table");
  if (!body) return;
  body.replaceChildren();
  const rows = state.showAllStoredBackups ? state.externalBackups : state.externalBackups.slice(0, 4);
  if (state.externalBackupsLoading && !state.externalBackups.length) {
    body.append(element("tr", {}, element("td", {
      text: "Checking configured backup destinations…",
      attributes: { colspan: "5" },
    })));
  } else if (!rows.length) {
    body.append(element("tr", {}, element("td", {
      text: "No stored copies discovered on configured destinations.",
      attributes: { colspan: "5" },
    })));
  }
  for (const item of rows) {
    const restoreId = `${item.target_id}:${item.id}`;
    const type = String(item.backup_type || "manual").toUpperCase();
    body.append(element("tr", {}, [
      element("td", {}, [element("span", { className: "backup-row-dot", text: "●" }), formatTime(item.created_at)]),
      element("td", {}, [badge(String(item.target_type || "").toUpperCase(), "info"), element("span", { className: "backup-target-name", text: ` ${item.target_name}` })]),
      element("td", {}, badge(type, type === "SCHEDULED" ? "info" : "")),
      element("td", { text: formatBytes(item.size_bytes) }),
      element("td", {}, backupIconAction("restore-external-backup", restoreId, "Restore", "restore")),
    ]));
  }
  const button = byId("backup-stored-view-all");
  if (button) {
    button.hidden = state.externalBackups.length <= 4;
    const label = button.querySelector("span:last-child");
    if (label) label.textContent = state.showAllStoredBackups ? "Show latest 4" : "View all stored copies";
  }
  const status = byId("backup-stored-view-all-status");
  if (status) {
    const visible = rows.length;
    status.replaceChildren(
      document.createTextNode(`${visible} of ${state.externalBackups.length} copies shown `),
      element("span", { text: "›", attributes: { "aria-hidden": "true" } }),
    );
  }

  const errors = byId("external-backup-list");
  if (errors) {
    errors.replaceChildren();
    errors.hidden = state.externalBackupErrors.length === 0;
    for (const failure of state.externalBackupErrors) {
      errors.append(element("div", { className: "backup-item external-backup-error" }, [
        element("div", {}, [
          element("strong", { text: failure.target_name }),
          element("small", { text: failure.message }),
        ]),
        badge("Unavailable", "warning"),
      ]));
    }
  }
}

function renderBackups() {
  if (!isAdmin()) return;
  renderBackupOverview();
  renderBackupRecoveryTable();
  renderStoredBackupTable();
}

function renderExternalBackups() {
  renderBackupOverview();
  renderStoredBackupTable();
}

function deduplicateExternalBackups(backups) {
  const preferredTarget = String(state.backupSettings?.target_id || "");
  const byBackupId = new Map();
  for (const item of backups) {
    const key = String(item.id || "");
    if (!key) continue;
    const current = byBackupId.get(key);
    if (
      !current
      || (
        preferredTarget
        && item.target_id === preferredTarget
        && current.target_id !== preferredTarget
      )
    ) {
      byBackupId.set(key, item);
    }
  }
  return [...byBackupId.values()].sort(
    (left, right) => Number(right.created_at || 0) - Number(left.created_at || 0),
  );
}

async function loadExternalBackups({ silent = false } = {}) {
  if (!isAdmin() || state.externalBackupsLoading) return;
  const targets = state.backupTargets.filter((item) => item.enabled);
  state.externalBackupsLoading = true;
  renderStoredBackupTable();
  try {
    const results = await Promise.allSettled(
      targets.map(async (target) => {
        const response = await request(`/backup-targets/${target.id}/backups`);
        return {
          target,
          backups: Array.isArray(response.backups) ? response.backups : [],
        };
      }),
    );
    const backups = [];
    const errors = [];
    results.forEach((result, index) => {
      const target = targets[index];
      if (result.status === "fulfilled") {
        for (const item of result.value.backups) {
          backups.push({
            ...item,
            target_id: target.id,
            target_name: target.name,
            target_type: target.type,
          });
        }
      } else {
        errors.push({
          target_id: target.id,
          target_name: target.name,
          message: result.reason?.message || "Backup destination is unavailable.",
        });
      }
    });
    state.externalBackups = deduplicateExternalBackups(backups);
    state.externalBackupErrors = errors;
    if (typeof qaSaveWorkspaceCache === "function") qaSaveWorkspaceCache();
    if (!silent && errors.length) {
      toast(
        `${errors.length} backup destination${errors.length === 1 ? "" : "s"} could not be inspected.`,
        "error",
      );
    }
  } finally {
    state.externalBackupsLoading = false;
    renderExternalBackups();
  }
}

function renderBackupTargets() {
  const body = byId("backup-target-table");
  if (!body) return;
  body.replaceChildren();
  for (const item of state.backupTargets) {
    const outcome = item.last_test_outcome;
    const status = !item.enabled ? "Disabled" : outcome === "success" ? "Writable" : outcome === "failed" ? "Test failed" : "Not tested";
    const style = !item.enabled ? "warning" : outcome === "success" ? "success" : outcome === "failed" ? "danger" : "warning";
    const location = item.type === "local"
      ? item.local_path
      : item.type === "nfs" ? item.remote_path : `${item.share_name}${item.remote_path ? `/${item.remote_path}` : ""}`;
    const actions = element("div", { className: "row-actions backup-row-actions" }, [
      backupIconAction("test-backup-target", item.id, "Test", "play"),
      backupIconAction("edit-backup-target", item.id, "Edit", "edit", "secondary", true),
      backupIconAction("delete-backup-target", item.id, "Delete", "trash", "danger", true),
    ]);
    body.append(element("tr", {}, [
      element("td", {}, badge(item.type.toUpperCase(), "info")),
      element("td", {}, [element("strong", { text: item.name }), item.last_error ? element("small", { text: item.last_error }) : null]),
      element("td", { text: item.host || "—" }),
      element("td", {}, element("code", { text: location, title: location })),
      element("td", {}, badge(status, style)),
      element("td", {}, backupTargetLastTest(item)),
      element("td", {}, actions),
    ]));
  }
  if (!state.backupTargets.length) {
    body.append(element("tr", {}, element("td", { text: "No backup destinations configured", attributes: { colspan: "7" } })));
  }
  renderBackupOverview();
}

function renderConfiguration() {
  if (!isAdmin() || !state.configuration) {
    return;
  }
  const configuration = state.configuration;
  const summary = configuration.summary;
  const sync = configuration.sync || { ready: true, errors: [] };
  byId("configuration-card-title").textContent = sync.ready ? "Configured inputs" : "Inputs require configuration repair";
  byId("configuration-card-copy").textContent = "SMTP, HTTP, and Redfish are managed independently. Click a status to change it, then restart Nowlert.";
  const badges = byId("configuration-summary");
  badges.replaceChildren(
    badge(`${summary.inputs} inputs`),
    badge(`${summary.outputs} destinations`),
    badge(`${summary.routes} routes`),
    badge(sync.ready ? "Synchronized" : "Repair required", sync.ready ? "success" : "danger"),
  );
  const inputs = byId("configuration-inputs");
  inputs.replaceChildren();
  if (!configuration.inputs.length) {
    inputs.append(element("small", { text: "No recognized YAML input sections were detected." }));
  } else {
    for (const item of configuration.inputs) {
      const detail = Object.entries(item.details || {}).map(([key, value]) => `${friendlyName(key)}: ${value}`).join(" · ");
      inputs.append(element("div", { className: "configuration-input" }, [
        element("div", {}, [element("strong", { text: item.label }), element("small", { text: detail || item.name })]),
        element("button", {
          className: `badge status-button ${item.enabled ? "success" : "warning"}`,
          text: item.enabled ? "Enabled" : "Disabled",
          type: "button",
          dataset: { action: "toggle-input", id: item.name },
        }),
      ]));
    }
  }
  const error = byId("configuration-errors");
  error.textContent = (sync.errors || []).join(" · ");
  error.hidden = !(sync.errors || []).length;
}

function renderHealthChecks() {
  const container = byId("health-check-list");
  container.replaceChildren();
  for (const item of state.healthChecks) {
    container.append(element("div", { className: "health-check" }, [
      element("span", { className: `health-indicator ${item.status}`, text: item.status === "healthy" ? "✓" : "!" }),
      element("div", {}, [element("strong", { text: item.name }), element("small", { text: item.detail })]),
      badge(capitalize(item.status), item.status === "healthy" ? "success" : item.status === "warning" ? "warning" : "danger"),
    ]));
  }
}


function renderBackupSettings() {
  if (!isAdmin() || !state.backupSettings) return;
  const settings = state.backupSettings;
  byId("backup-schedule").value = settings.schedule;
  renderBackupTimeOptions();
  byId("backup-weekday").value = String(settings.weekday);
  byId("backup-day").value = String(settings.day);
  const target = byId("backup-target");
  target.replaceChildren(element("option", { value: "", text: "Local state only" }));
  for (const item of state.backupTargets) {
    target.append(element("option", { value: item.id, text: `${item.name} (${item.type.toUpperCase()})` }));
  }
  target.value = settings.target_id || "";
  byId("backup-time-display").textContent = backupNextRunLabel(settings);
  renderBackupOverview();
}
function housekeepingRunDuration(run) {
  const started = Number(run?.started_at || 0);
  const completed = Number(run?.completed_at || 0);
  if (!started || !completed || completed < started) return "—";
  const seconds = Math.max(0, completed - started);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}m ${String(remainder).padStart(2, "0")}s`;
}

function renderHousekeepingRecentRuns(status) {
  const container = byId("housekeeping-recent-runs");
  if (!container) return;
  const recentRuns = Array.isArray(status.recent_runs) ? status.recent_runs : [];
  container.replaceChildren();

  if (!recentRuns.length) {
    container.append(element("div", { className: "housekeeping-runs-empty" }, [
      element("strong", { text: "No automatic housekeeping runs yet" }),
      element("small", { text: "Completed daily runs will appear here." }),
    ]));
    return;
  }

  for (const run of recentRuns) {
    const success = String(run.outcome || "").toLowerCase() === "success";
    const outcome = success ? "Completed successfully" : capitalize(run.outcome || "completed");
    const removed =
      `Removed ${Number(run.deliveries_deleted || 0).toLocaleString()} delivery records, ` +
      `${Number(run.audit_deleted || 0).toLocaleString()} audit records, and ` +
      `${Number(run.backup_runs_deleted || 0).toLocaleString()} backup run records.`;
    container.append(element("div", {
      className: `housekeeping-run-item ${success ? "is-success" : "is-warning"}`,
    }, [
      element("span", {
        className: "housekeeping-run-icon",
        text: success ? "✓" : "!",
        attributes: { "aria-hidden": "true" },
      }),
      element("span", { className: "housekeeping-run-copy" }, [
        element("strong", { text: formatTime(run.completed_at || run.started_at) }),
        element("span", { className: "housekeeping-run-outcome", text: outcome }),
        element("small", { text: removed }),
      ]),
      element("span", { className: "housekeeping-run-duration", text: housekeepingRunDuration(run) }),
    ]));
  }
}

function renderHousekeepingSettings() {
  if (!isAdmin() || !state.housekeepingSettings) return;
  const settings = state.housekeepingSettings;
  const enabled = settings.enabled === true;
  const status = state.housekeepingStatus || {};

  renderHousekeepingTimeOptions();
  byId("housekeeping-delivery-days").value = String(settings.delivery_history_days ?? 90);
  byId("housekeeping-audit-days").value = String(settings.audit_history_days ?? 365);
  byId("housekeeping-backup-run-days").value = String(settings.backup_run_history_days ?? 180);

  const timeSelect = byId("housekeeping-time");
  timeSelect.disabled = !enabled;
  const timeHelp = byId("housekeeping-time-help");
  if (timeHelp) {
    timeHelp.textContent = enabled
      ? "Displayed using your Regional Settings clock format."
      : "Disabled while housekeeping is turned off.";
  }

  const toggle = byId("housekeeping-toggle");
  toggle.classList.toggle("is-enabled", enabled);
  toggle.classList.toggle("is-disabled", !enabled);
  toggle.setAttribute("aria-pressed", String(enabled));
  toggle.setAttribute("aria-label", enabled ? "Disable housekeeping" : "Enable housekeeping");
  toggle.title = enabled ? "Click to disable housekeeping" : "Click to enable housekeeping";

  byId("housekeeping-status-icon").replaceChildren(
    backupSvgIcon(enabled ? "check" : "pause", "housekeeping-symbol"),
  );
  byId("housekeeping-status-title").textContent =
    enabled ? "Housekeeping is enabled" : "Housekeeping is disabled";
  byId("housekeeping-status-description").textContent = enabled
    ? "Automatic clean-up will run daily and remove records older than your configured retention periods."
    : "Automatic clean-up is turned off. Existing records will be kept until housekeeping is enabled again.";

  const nextRun = enabled && status.next_run_at
    ? formatTime(status.next_run_at)
    : "Not scheduled";
  byId("housekeeping-next-run").textContent = nextRun;

  const scheduleNote = byId("housekeeping-schedule-note");
  scheduleNote.classList.toggle("is-enabled", enabled);
  scheduleNote.classList.toggle("is-disabled", !enabled);
  byId("housekeeping-schedule-note-icon").replaceChildren(
    backupSvgIcon("clock", "housekeeping-symbol"),
  );
  byId("housekeeping-schedule-note-title").textContent = enabled
    ? "Housekeeping runs once per day."
    : "Housekeeping is currently disabled.";
  byId("housekeeping-schedule-note-copy").textContent = enabled
    ? `Next run: ${nextRun}.`
    : "Enable housekeeping to resume daily clean-up.";

  renderHousekeepingRecentRuns(status);
}
function renderUpdates() {
  const version = state.versionStatus || {};
  byId("running-version").textContent = version.running || "—";
  byId("available-version").textContent = version.available || "Not advertised";
  byId("update-status").textContent = version.update_available
    ? `Version ${version.available} is available. Review the release notes and deploy the versioned image.`
    : "Nowlert is up to date with the advertised version.";
}

function renderPreferences() {
  renderSessionExpiryLabel();
  if (!isAdmin()) return;
  byId("preference-language").value = state.preferences.language || "en-GB";
  byId("preference-timezone").value = state.preferences.timezone || "Europe/Lisbon";
  byId("preference-time-format").value = state.preferences.time_format || "24";
  document.documentElement.lang = state.preferences.language || "en-GB";
}

function applyLanguageDefaultTimezone() {
  const language = byId("preference-language").value;
  const timezone = LANGUAGE_DEFAULT_TIMEZONES[language];
  if (timezone) byId("preference-timezone").value = timezone;
}

async function savePreferences(event) {
  event.preventDefault();
  try {
    const response = await request("/preferences", {
      method: "PUT",
      body: {
        language: byId("preference-language").value,
        timezone: byId("preference-timezone").value,
        time_format: byId("preference-time-format").value,
      },
    });
    state.preferences = response.preferences;
    renderHousekeepingTimeOptions();
    renderBackupTimeOptions();
    await loadWorkspace();
    toast("Regional settings saved.");
  } catch (error) {
    toast(error.message || "Settings could not be saved.", "error");
  }
}

async function changeHistoryRange() {
  state.historyRange = byId("history-range").value;
  try {
    const response = await request(`/metrics/${state.historyRange}`);
    state.metrics = response.metrics;
    renderDashboard();
  } catch (error) {
    toast(error.message || "History could not be loaded.", "error");
  }
}


async function saveBackupSettings(event) {
  event.preventDefault();
  try {
    const response = await request("/backup-settings", {
      method: "PUT",
      body: {
        schedule: byId("backup-schedule").value,
        time: byId("backup-time").value,
        weekday: Number(byId("backup-weekday").value),
        day: Number(byId("backup-day").value),
        target_id: byId("backup-target").value,
        managed_mounts: true,
        external_enabled: false,
        external_type: "nfs",
        external_path: "",
      },
    });
    state.backupSettings = response.settings;
    renderBackupSettings();
    if (typeof qaSaveWorkspaceCache === "function") qaSaveWorkspaceCache();
    toast("Backup settings saved.");
  } catch (error) {
    toast(error.message || "Backup settings could not be saved.", "error");
  }
}
async function saveHousekeepingSettings(event) {
  event.preventDefault();
  try {
    const response = await request("/housekeeping", {
      method: "PUT",
      body: {
        enabled: state.housekeepingSettings.enabled === true,
        time: byId("housekeeping-time").value,
        delivery_history_days: Number(byId("housekeeping-delivery-days").value),
        audit_history_days: Number(byId("housekeeping-audit-days").value),
        backup_run_history_days: Number(byId("housekeeping-backup-run-days").value),
      },
    });
    state.housekeepingSettings = response.settings;
    state.housekeepingStatus = response.status;
    renderHousekeepingSettings();
    toast("Housekeeping settings saved.");
  } catch (error) {
    toast(error.message || "Housekeeping settings could not be saved.", "error");
  }
}

async function toggleHousekeeping() {
  if (!isAdmin() || !state.housekeepingSettings) return;
  const toggle = byId("housekeeping-toggle");
  const enabled = state.housekeepingSettings.enabled !== true;
  toggle.disabled = true;
  try {
    const response = await request("/housekeeping", {
      method: "PUT",
      body: {
        ...state.housekeepingSettings,
        enabled,
      },
    });
    state.housekeepingSettings = response.settings;
    state.housekeepingStatus = response.status;
    renderHousekeepingSettings();
    toast(enabled ? "Housekeeping enabled." : "Housekeeping disabled.");
  } catch (error) {
    toast(error.message || "Housekeeping state could not be changed.", "error");
  } finally {
    toggle.disabled = false;
  }
}
function updateBackupTargetFields() {
  const type = byId("backup-target-type").value;
  for (const item of document.querySelectorAll(".backup-remote-field")) item.hidden = type === "local";
  for (const item of document.querySelectorAll(".backup-nfs-field")) item.hidden = type !== "nfs";
  for (const item of document.querySelectorAll(".backup-smb-field")) item.hidden = type !== "smb";
  for (const item of document.querySelectorAll(".backup-local-field")) item.hidden = type !== "local";
  byId("backup-target-host").required = type !== "local";
  byId("backup-target-remote-path").required = type === "nfs";
  byId("backup-target-share").required = type === "smb";
  byId("backup-target-local-path").required = type === "local";
}

function openBackupTarget(id = "") {
  const item = state.backupTargets.find((candidate) => candidate.id === id);
  byId("backup-target-form").reset();
  clearError("backup-target-error");
  byId("backup-target-id").value = item ? item.id : "";
  byId("backup-target-name").value = item ? item.name : "";
  byId("backup-target-type").value = item ? item.type : "local";
  byId("backup-target-enabled").checked = item ? item.enabled : true;
  byId("backup-target-host").value = item ? item.host : "";
  byId("backup-target-remote-path").value = item && item.type === "nfs" ? item.remote_path : "";
  byId("backup-target-share").value = item ? item.share_name : "";
  byId("backup-target-smb-path").value = item && item.type === "smb" ? item.remote_path : "";
  byId("backup-target-local-path").value = item && item.type === "local" ? item.local_path : "";
  byId("backup-target-username").value = item ? item.username : "";
  byId("backup-target-domain").value = item ? item.domain : "";
  byId("backup-target-options").value = item ? item.mount_options : "";
  byId("backup-target-password").value = "";
  byId("backup-target-dialog-title").textContent = item ? `Edit ${item.name}` : "Add backup destination";
  updateBackupTargetFields();
  byId("backup-target-dialog").showModal();
}

async function saveBackupTarget(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("backup-target-dialog").close();
    return;
  }
  clearError("backup-target-error");
  const id = byId("backup-target-id").value;
  const type = byId("backup-target-type").value;
  try {
    await request(id ? `/backup-targets/${id}` : "/backup-targets", {
      method: id ? "PATCH" : "POST",
      body: {
        name: byId("backup-target-name").value.trim(),
        type,
        host: byId("backup-target-host").value.trim(),
        remote_path: type === "nfs" ? byId("backup-target-remote-path").value.trim() : byId("backup-target-smb-path").value.trim(),
        share_name: byId("backup-target-share").value.trim(),
        local_path: byId("backup-target-local-path").value.trim(),
        username: byId("backup-target-username").value.trim(),
        domain: byId("backup-target-domain").value.trim(),
        password: byId("backup-target-password").value,
        mount_options: byId("backup-target-options").value.trim(),
        enabled: byId("backup-target-enabled").checked,
      },
    });
    byId("backup-target-dialog").close();
    await loadWorkspace();
    if (state.currentView === "backups") {
      await loadExternalBackups({ silent: true });
    }
    toast(type === "local"
      ? (id ? "Backup destination updated." : "Backup destination added.")
      : "Remote backup destination saved with automatic managed mounting enabled.");
  } catch (error) {
    showError("backup-target-error", error);
  }
}


async function createRemoteBackup() {
  const targetId = byId("backup-target").value;
  if (!targetId) {
    toast("Select a remote backup destination first.", "error");
    return;
  }
  const response = await request("/backups/run", {
    method: "POST",
    body: { target_id: targetId },
  });
  await refreshBackupPanels();
  toast(
    response.run.outcome === "success" ? "Remote backup created." : "Remote backup failed.",
    response.run.outcome === "success" ? "success" : "error",
  );
}
function restartEnvironmentLabel() {
  const host = String(window.location.hostname || "").toLowerCase();
  if (host.startsWith("ce-dev-") || host.includes("development")) return "CE Development";
  if (host.startsWith("ce-stage-") || host.includes("staging") || host.includes("stage")) return "CE Stage";
  if (host.startsWith("ce-prod-") || host.includes("production") || host === "nowlert.theriark.com") return "CE Production";
  return "This instance";
}

function updateRestartDialogContext() {
  const reason = byId("restart-reason");
  const count = byId("restart-reason-count");
  const actor = byId("restart-triggered-by");
  const environment = byId("restart-environment");
  if (count) count.textContent = `${String(reason?.value || "").length}/500`;
  if (actor) {
    actor.textContent = state.user?.role === "admin"
      ? "Admin"
      : (state.user?.username || "User");
  }
  if (environment) environment.textContent = restartEnvironmentLabel();
}

async function restartPlatform(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("restart-dialog").close();
    return;
  }
  clearError("restart-error");
  try {
    await request("/reboot", {
      method: "POST",
      body: { reason: byId("restart-reason").value.trim() },
    });
    byId("restart-dialog").close();
    toast("Restart accepted. Nowlert will be briefly unavailable.", "success");
  } catch (error) {
    showError("restart-error", error);
  }
}

function updateAvatarSaveState(available) {
  const save = byId("avatar-save");
  if (!save) return;
  const enabled = Boolean(available);
  save.hidden = !enabled;
  save.disabled = !enabled;
}

async function saveAvatar(event) {
  event.preventDefault();
  if (!state.avatarEditor.image) {
    toast("Choose a picture first.", "error");
    return;
  }
  try {
    updateAvatarSaveState(false);
    const imageData = byId("avatar-canvas").toDataURL("image/png");
    const response = await request("/account/avatar", { method: "PUT", body: { image_data: imageData } });
    state.user = response.user;
    applyAvatar("profile-avatar", state.user);
    applyAvatar("account-avatar", state.user);
    byId("avatar-file").value = "";
    byId("avatar-editor").hidden = true;
    if (state.avatarEditor.image && typeof state.avatarEditor.image.close === "function") {
      state.avatarEditor.image.close();
    }
    state.avatarEditor.image = null;
    updateAvatarSaveState(false);
    toast("Profile picture updated.");
  } catch (error) {
    updateAvatarSaveState(Boolean(state.avatarEditor.image));
    toast(error.message || "Profile picture could not be saved.", "error");
  }
}

async function loadAvatarEditor() {
  const file = byId("avatar-file").files && byId("avatar-file").files[0];
  if (!file) return;
  const supportedType = ["image/png", "image/jpeg", "image/webp"].includes(file.type);
  const supportedExtension = !file.type && /\.(?:png|jpe?g|webp)$/i.test(file.name);
  if ((!supportedType && !supportedExtension) || file.size > 10 * 1024 * 1024) {
    toast("Choose a PNG, JPEG, or WebP image up to 10 MiB.", "error");
    byId("avatar-file").value = "";
    updateAvatarSaveState(false);
    return;
  }
  let image;
  if (state.avatarEditor.image && typeof state.avatarEditor.image.close === "function") {
    state.avatarEditor.image.close();
  }
  if ("createImageBitmap" in window) {
    try {
      image = await createImageBitmap(file, { imageOrientation: "from-image" });
    } catch (_error) {
      image = null;
    }
  }
  if (!image) {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("The picture could not be read."));
      reader.readAsDataURL(file);
    });
    image = new Image();
    image.decoding = "async";
    image.src = dataUrl;
    try {
      await image.decode();
    } catch (_error) {
      await new Promise((resolve, reject) => {
        if (image.complete && image.naturalWidth) {
          resolve();
          return;
        }
        image.onload = resolve;
        image.onerror = () => reject(new Error("The picture could not be decoded as PNG, JPEG, or WebP."));
      });
    }
  }
  state.avatarEditor.image = image;
  state.avatarEditor.scale = 1;
  byId("avatar-zoom").value = "1";
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  const base = Math.max(256 / width, 256 / height);
  state.avatarEditor.x = (256 - width * base) / 2;
  state.avatarEditor.y = (256 - height * base) / 2;
  byId("avatar-editor").hidden = false;
  drawAvatarEditor();
  updateAvatarSaveState(true);
}

function drawAvatarEditor() {
  const image = state.avatarEditor.image;
  if (!image) return;
  const canvas = byId("avatar-canvas");
  const context = canvas.getContext("2d");
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  const base = Math.max(canvas.width / width, canvas.height / height);
  const scale = base * state.avatarEditor.scale;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.save();
  context.beginPath();
  context.arc(canvas.width / 2, canvas.height / 2, canvas.width / 2, 0, Math.PI * 2);
  context.clip();
  context.drawImage(image, state.avatarEditor.x, state.avatarEditor.y, width * scale, height * scale);
  context.restore();
}

function zoomAvatarEditor() {
  const image = state.avatarEditor.image;
  if (!image) return;
  const previous = state.avatarEditor.scale;
  const next = Number(byId("avatar-zoom").value);
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  const base = Math.max(256 / width, 256 / height);
  const centerX = (128 - state.avatarEditor.x) / (base * previous);
  const centerY = (128 - state.avatarEditor.y) / (base * previous);
  state.avatarEditor.scale = next;
  state.avatarEditor.x = 128 - centerX * base * next;
  state.avatarEditor.y = 128 - centerY * base * next;
  drawAvatarEditor();
}

function moveAvatarEditor(event) {
  if (!state.avatarEditor.dragging) return;
  state.avatarEditor.x += event.clientX - state.avatarEditor.pointerX;
  state.avatarEditor.y += event.clientY - state.avatarEditor.pointerY;
  state.avatarEditor.pointerX = event.clientX;
  state.avatarEditor.pointerY = event.clientY;
  drawAvatarEditor();
}

function downloadDocument(documentValue) {
  const content = `${JSON.stringify(documentValue, null, 2)}\n`;
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = element("a", {
    attributes: {
      href: url,
      download: `nowlert-platform-${new Date().toISOString().slice(0, 10)}.json`,
    },
  });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function exportPlatform() {
  const response = await request("/portability/export");
  downloadDocument(response.document);
  toast("Safe platform export downloaded.");
}

async function selectedFile(id) {
  const input = byId(id);
  const file = input.files && input.files[0];
  if (!file) throw new Error("Choose a file first.");
  if (file.size < 1 || file.size > 1024 * 1024) {
    throw new Error("Import files must contain 1 to 1048576 bytes.");
  }
  return file.text();
}

function importPreviewCount(preview, key) {
  const summaryValue = Number(preview?.summary?.[key]);
  if (Number.isFinite(summaryValue)) return summaryValue;
  const items = preview?.[key];
  return Array.isArray(items) ? items.length : 0;
}

function importPreviewIssues(preview) {
  const normalize = (value) => String(
    value && typeof value === "object" ? (value.message || value.error || JSON.stringify(value)) : (value || ""),
  ).trim();
  return [
    ...(Array.isArray(preview?.errors) ? preview.errors : []).map((value) => ({
      kind: "error",
      text: normalize(value),
    })),
    ...(Array.isArray(preview?.warnings) ? preview.warnings : []).map((value) => ({
      kind: "warning",
      text: normalize(value),
    })),
  ].filter((item) => item.text);
}

function renderImportIssues(preview) {
  const list = byId("import-issue-list");
  const more = byId("import-issues-more");
  const count = byId("import-issue-count");
  if (!list || !more || !count) return;

  const all = importPreviewIssues(preview);
  count.textContent = String(all.length);
  const filter = byId("import-issue-filter")?.value || "all";
  const visible = filter === "all" ? all : all.filter((item) => item.kind === filter);
  list.replaceChildren();

  for (const [index, issue] of visible.entries()) {
    const row = element("div", { className: `reference-import-issue is-${issue.kind}` });
    row.append(
      element("span", { className: "reference-import-issue-index", text: String(index + 1) }),
      element("span", { className: "reference-import-issue-icon", text: issue.kind === "error" ? "!" : "△" }),
      element("span", { className: "reference-import-issue-text", text: issue.text }),
      element("small", { text: issue.kind === "error" ? "Error" : "Warning" }),
    );
    list.append(row);
  }

  list.scrollTop = 0;
  more.hidden = true;
  more.textContent = "";
}

function renderImportPreview(preview) {
  const fingerprint = String(preview?.fingerprint || "");
  const valid = preview?.valid === true;
  const errors = Array.isArray(preview?.errors) ? preview.errors.length : 0;
  const warnings = Array.isArray(preview?.warnings) ? preview.warnings.length : 0;

  const fingerprintValue = byId("import-metric-fingerprint");
  const fingerprintState = byId("import-metric-fingerprint-state");
  if (fingerprintValue) {
    fingerprintValue.textContent = fingerprint
      ? `${fingerprint.slice(0, 12)}${fingerprint.length > 12 ? "…" : ""}`
      : "—";
    fingerprintValue.title = fingerprint;
  }
  if (fingerprintState) {
    fingerprintState.textContent = fingerprint ? "Present" : "Missing";
    fingerprintState.className = fingerprint ? "is-present" : "is-missing";
  }

  const validValue = byId("import-metric-valid");
  const validState = byId("import-metric-valid-state");
  if (validValue) validValue.textContent = String(Boolean(preview?.valid));
  if (validState) {
    validState.textContent = valid ? "Valid" : "Invalid";
    validState.className = valid ? "is-valid" : "is-invalid";
  }

  if (byId("import-metric-errors")) byId("import-metric-errors").textContent = String(errors);
  if (byId("import-metric-warnings")) byId("import-metric-warnings").textContent = String(warnings);
  if (byId("import-metric-destinations")) {
    byId("import-metric-destinations").textContent = String(importPreviewCount(preview, "destinations"));
  }
  if (byId("import-metric-routes")) {
    byId("import-metric-routes").textContent = String(importPreviewCount(preview, "routes"));
  }

  byId("import-result").textContent = JSON.stringify(preview || {}, null, 2);
  renderImportIssues(preview || {});
}

async function copyImportPreview() {
  const value = byId("import-result")?.textContent || "";
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    toast("Configuration preview copied.");
  } catch (_error) {
    toast("Configuration preview could not be copied.", "error");
  }
}

async function previewImport(kind, portableFileId = "portable-file") {
  clearError("import-error");
  const portable = kind === "portable";
  const local = kind === "local_yaml";
  try {
    let body = {};
    if (!local) {
      const content = await selectedFile(portable ? portableFileId : "migration-file");
      if (portable) {
        let documentValue;
        try {
          documentValue = JSON.parse(content);
        } catch (_error) {
          throw new Error("The selected JSON document is invalid.");
        }
        body = { document: documentValue };
      } else {
        body = { yaml: content };
      }
    }
    const endpoint = local
      ? "/configuration/migration/preview"
      : portable ? "/portability/preview" : "/migrations/v1/preview";
    const response = await request(endpoint, { method: "POST", body });
    state.pendingImport = { kind, body, preview: response.preview, portableFileId };
    byId("import-title").textContent = local
      ? "Mounted configuration takeover"
      : portable ? "Import user configuration" : "v1.x YAML migration preview";
    byId("import-summary").textContent = response.preview.valid
      ? portable
        ? `Validated Nowlert export: ${response.preview.summary.destinations} destinations and ${response.preview.summary.routes} routes are ready to import.`
        : `${response.preview.summary.destinations} destinations and ${response.preview.summary.routes} routes are ready.${local ? " Applying this creates state and configuration backups, imports credentials server-side, and activates WebUI routing." : ""}`
      : `Preview completed. ${Array.isArray(response.preview.errors) ? response.preview.errors.length : 0} issue(s) must be resolved before this document can be applied.`;
    renderImportPreview(response.preview);
    byId("import-apply").disabled = !response.preview.valid;
    byId("import-dialog").showModal();
  } catch (error) {
    state.pendingImport = null;
    toast(error.message || "Import preview failed.", "error");
  }
}

async function applyImport() {
  const pending = state.pendingImport;
  if (!pending || !pending.preview.valid) return;
  const accepted = await confirmAction(
    "Apply the previewed import?",
    "Only the unchanged, fingerprinted document will be accepted. This creates new resources and never overwrites existing names.",
    "Apply import",
  );
  if (!accepted) return;
  try {
    const endpoint = pending.kind === "local_yaml"
      ? "/configuration/migration/apply"
      : pending.kind === "portable" ? "/portability/import" : "/migrations/v1/import";
    const body = {
      ...pending.body,
      fingerprint: pending.preview.fingerprint,
      confirm: true,
    };
    const response = await request(endpoint, { method: "POST", body });
    const result = response.migration || response.import;
    state.pendingImport = null;
    byId("import-dialog").close();
    byId("portable-file").value = "";
    const backupPortableFile = byId("backup-portable-file");
    if (backupPortableFile) backupPortableFile.value = "";
    const migrationFile = byId("migration-file");
    if (migrationFile) migrationFile.value = "";
    await loadWorkspace();
    toast(`${pending.kind === "local_yaml" ? "Activated" : "Imported"} ${result.destinations_created} destinations and ${result.routes_created} routes.`);
  } catch (error) {
    showError("import-error", error);
  }
}


async function refreshBackupPanels() {
  await loadWorkspace();
  await loadExternalBackups({ silent: true });
  renderBackupRecoveryTable();
  renderStoredBackupTable();
}

async function createBackup() {
  await request("/backups", { method: "POST", body: {} });
  await refreshBackupPanels();
  toast("Recovery snapshot created.");
}
async function restoreBackup(id) {
  const accepted = await confirmAction(
    "Restore this recovery snapshot?",
    `Restore ${id}. Nowlert verifies the snapshot, creates a safety backup first, restores the complete state, signs out every browser session, and restarts the service.`,
    "Restore and restart",
  );
  if (!accepted) return;
  await request(`/backups/${id}/restore`, {
    method: "POST",
    body: { confirmation: id },
  });
  expireSession();
  toast("Recovery snapshot restored. Nowlert is restarting.", "success");
  window.setTimeout(() => window.location.reload(), 3500);
}

async function restoreExternalBackup(targetId, backupId) {
  const target = state.backupTargets.find((item) => item.id === targetId);
  const targetName = target ? target.name : "backup destination";
  const accepted = await confirmAction(
    "Restore this stored recovery snapshot?",
    `Restore ${backupId} from ${targetName}. The snapshot is copied to local staging and verified first. Nowlert then creates a safety backup, restores the complete state, signs out every browser session, and restarts.`,
    "Restore and restart",
  );
  if (!accepted) return;
  await request(`/backup-targets/${targetId}/backups/${backupId}/restore`, {
    method: "POST",
    body: { confirmation: backupId },
  });
  expireSession();
  toast("Stored recovery snapshot restored. Nowlert is restarting.", "success");
  window.setTimeout(() => window.location.reload(), 3500);
}

async function setRoutingAuthority(authority) {
  const database = authority === "database";
  const accepted = await confirmAction(
    database ? "Use WebUI routing?" : "Use YAML fallback routing?",
    database
      ? "Legacy SMTP and webhook events will use the destinations and routes managed in this WebUI. A configuration backup is created first."
      : "Legacy SMTP and webhook events will immediately use the original destinations and routes retained in config.yaml. A configuration backup is created first.",
    database ? "Use WebUI routing" : "Use YAML routing",
  );
  if (!accepted) return;
  await request("/configuration/routing-authority", {
    method: "PUT",
    body: {
      authority,
      confirmation: `USE ${authority.toUpperCase()} ROUTING`,
    },
  });
  await loadWorkspace();
  toast(`${database ? "WebUI" : "YAML"} routing is now authoritative.`);
}

function formField(definition, value) {
  const label = element("label", { className: definition.wide ? "wide" : "" });
  label.append(element("span", { text: definition.label }));
  let input;
  if (definition.kind === "select") {
    input = element("select", { dataset: { field: definition.key, valueType: definition.valueType || "string" } });
    for (const choice of definition.choices) input.append(element("option", { value: choice[0], text: choice[1] }));
  } else if (definition.kind === "textarea") {
    input = element("textarea", { dataset: { field: definition.key, valueType: definition.valueType || "string" }, attributes: { rows: definition.rows || 3 } });
  } else {
    input = element("input", {
      type: definition.kind === "password" ? "password" : definition.kind === "number" ? "number" : "text",
      dataset: { field: definition.key, valueType: definition.valueType || "string" },
      attributes: definition.attributes || {},
    });
  }
  if (definition.kind === "checkbox") {
    label.className = "switch-field";
    label.replaceChildren();
    input = element("input", { type: "checkbox", dataset: { field: definition.key, valueType: "boolean" } });
    input.checked = Boolean(value === undefined ? definition.default : value);
    label.append(input, element("span", { text: definition.label }));
    if (definition.help) label.append(element("small", { text: definition.help }));
    return label;
  } else if (value !== undefined && value !== null) {
    input.value = definition.valueType === "json" ? JSON.stringify(value, null, 2) : definition.valueType === "list" && Array.isArray(value) ? value.join(", ") : String(value);
  } else if (definition.default !== undefined) {
    input.value = String(definition.default);
  }
  if (definition.required) input.required = true;
  label.append(input);
  if (definition.help) label.append(element("small", { text: definition.help }));
  return label;
}

function destinationDefinition(type) {
  const adminPrivate = isAdmin() ? [{ key: "allow_private_network", label: "Allow private-network target", kind: "checkbox", default: false }] : [];
  const presentation = { key: "channel_name", label: "Channel / destination" };
  const definitions = {
    discord: {
      help: "Discord components-v2 formatting with source-aware fallback.",
      settings: [presentation, { key: "components_v2", label: "Use Components v2", kind: "checkbox", default: true }],
      secrets: [{ key: "url", label: "Webhook URL", kind: "password", required: true, wide: true }],
    },
    teams: {
      help: "Microsoft Teams workflow or incoming webhook delivery.",
      settings: [
        presentation,
        {
          key: "message_style",
          label: "Message style",
          kind: "select",
          choices: [["modern", "Modern Card"], ["classic", "Classic Card"]],
          default: "modern",
        },
      ],
      secrets: [{ key: "url", label: "Webhook URL", kind: "password", required: true, wide: true }],
    },
    slack: {
      help: "Slack delivery with preserved Classic Cards and shared Modern image cards.",
      settings: [
        presentation,
        {
          key: "message_style",
          label: "Message style",
          kind: "select",
          choices: [["classic", "Classic Card"], ["modern", "Modern Card"]],
          default: "classic",
        },
        {
          key: "include_metadata",
          label: "Include event metadata",
          kind: "checkbox",
          default: true,
        },
      ],
      secrets: [{ key: "url", label: "Slack webhook URL", kind: "password", required: true, wide: true }],
    },
    webhook: {
      help: "Bounded JSON delivery with backend-owned Modern or Classic presentation.",
      settings: [
        presentation,
        {
          key: "message_style",
          label: "Message style",
          kind: "select",
          choices: [["modern", "Modern Card"], ["classic", "Classic Card"]],
          default: "modern",
        },
      ],
      secrets: [
        { key: "url", label: "Destination URL", kind: "password", required: true, wide: true },
      ],
    },
    mqtt: {
      help: "Publish the stable event envelope to a bounded MQTT topic.",
      settings: [
        presentation,
        { key: "host", label: "Broker host", required: true },
        { key: "port", label: "Port", kind: "number", valueType: "number", default: 8883, attributes: { min: 1, max: 65535 } },
        { key: "topic", label: "Topic", required: true, wide: true },
        { key: "qos", label: "QoS", kind: "select", valueType: "number", choices: [["0", "0"], ["1", "1"], ["2", "2"]], default: 1 },
        { key: "keepalive_seconds", label: "Keepalive (seconds)", kind: "number", valueType: "number", default: 60, attributes: { min: 10, max: 300 } },
        { key: "client_id", label: "Client ID" },
        { key: "tls", label: "Use TLS", kind: "checkbox", default: true },
        { key: "retain", label: "Retain messages", kind: "checkbox", default: false },
        ...adminPrivate,
      ],
      secrets: [{ key: "username", label: "Username", kind: "password" }, { key: "password", label: "Password", kind: "password" }],
    },
    ntfy: {
      help: "Publish to a hosted or self-hosted ntfy server.",
      settings: [
        presentation,
        { key: "server", label: "Server URL", required: true, wide: true },
        { key: "topic", label: "Topic", required: true },
        { key: "priority", label: "Priority", kind: "select", choices: [["min", "Minimum"], ["low", "Low"], ["default", "Default"], ["high", "High"], ["max", "Maximum"]], default: "default" },
        { key: "tags", label: "Tags", valueType: "list", help: "Comma-separated" },
        { key: "title", label: "Title template", default: "${title}" },
        { key: "timeout_seconds", label: "Timeout (seconds)", kind: "number", valueType: "number", default: 15, attributes: { min: 1, max: 30 } },
        { key: "include_action", label: "Include safe action link", kind: "checkbox", default: true },
        ...adminPrivate,
      ],
      secrets: [{ key: "token", label: "Access token", kind: "password", wide: true }, { key: "username", label: "Username", kind: "password" }, { key: "password", label: "Password", kind: "password" }],
    },
  };
  return definitions[type];
}

function renderDestinationFields(settings = {}) {
  const type = byId("destination-type").value;
  const definition = destinationDefinition(type);
  byId("destination-help").textContent = definition.help;
  const settingsContainer = byId("destination-settings");
  const secretsContainer = byId("destination-secrets");
  settingsContainer.replaceChildren(...definition.settings.map((field) => formField(field, settings[field.key])));
  secretsContainer.replaceChildren(...definition.secrets.map((field) => formField(field)));
  const editing = Boolean(byId("destination-id").value);
  const originalType = byId("destination-original-type").value;
  const typeChanged = editing && originalType && originalType !== type;
  for (const input of secretsContainer.querySelectorAll("[required]")) input.required = !editing || typeChanged;
  if (typeChanged) byId("destination-help").textContent += " New credentials are required because the destination type changed.";
}

function openDestination(id = "") {
  const item = state.destinations.find((candidate) => candidate.id === id);
  byId("destination-form").reset();
  clearError("destination-error");
  byId("destination-id").value = item ? item.id : "";
  byId("destination-original-type").value = item ? item.output_type : "";
  byId("destination-name").value = item ? item.name : "";
  byId("destination-type").value = item ? item.output_type : "discord";
  byId("destination-name").disabled = false;
  byId("destination-type").disabled = false;
  byId("destination-enabled").checked = item ? item.enabled : true;
  byId("destination-shared").checked = item ? item.shared : false;
  byId("destination-shared-field").hidden = item ? !ownResource(item) : false;
  byId("destination-dialog-title").textContent = item ? `Edit ${item.name}` : "Add destination";
  byId("destination-submit").textContent = item ? "Save changes" : "Add destination";
  renderDestinationFields(item ? item.settings : {});
  byId("destination-dialog").showModal();
}

function collectFields(container) {
  const result = {};
  for (const input of container.querySelectorAll("[data-field]")) {
    const key = input.dataset.field;
    const type = input.dataset.valueType;
    if (type === "boolean") {
      result[key] = input.checked;
    } else if (type === "number") {
      result[key] = Number(input.value);
    } else if (type === "list") {
      result[key] = splitList(input.value);
    } else if (type === "json" || type === "optional-json") {
      if (!input.value.trim() && type === "optional-json") continue;
      try {
        result[key] = JSON.parse(input.value || "{}");
      } catch (_error) {
        throw new Error(`${input.previousElementSibling.textContent} must contain valid JSON.`);
      }
    } else if (input.value.trim()) {
      result[key] = input.value.trim();
    }
  }
  return result;
}

async function saveDestination(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("destination-dialog").close();
    return;
  }
  clearError("destination-error");
  const id = byId("destination-id").value;
  const submit = byId("destination-submit");
  const name = byId("destination-name").value.trim();
  const duplicate = state.destinations.find((item) => item.id !== id && item.name.trim().toLowerCase() === name.toLowerCase());
  if (duplicate) {
    showValidationError("destination-error", `A destination named "${name}" already exists. Choose another name.`);
    return;
  }
  submit.disabled = true;
  try {
    const settings = collectFields(byId("destination-settings"));
    const secret = collectFields(byId("destination-secrets"));
    const payload = {
      name,
      output_type: byId("destination-type").value,
      settings,
      enabled: byId("destination-enabled").checked,
    };
    if (!byId("destination-shared-field").hidden) {
      payload.shared = byId("destination-shared").checked;
    }
    if (Object.keys(secret).length) payload.secret = secret;
    await request(id ? `/destinations/${id}` : "/destinations", { method: id ? "PATCH" : "POST", body: payload });
    byId("destination-dialog").close();
    await loadWorkspace();
    toast(id ? "Destination updated." : "Destination added.");
  } catch (error) {
    showError("destination-error", error);
  } finally {
    submit.disabled = false;
  }
}

function splitList(value) {
  return [...new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean))];
}

function setRouteOptions(selected = "") {
  const select = byId("route-destination");
  select.replaceChildren();
  for (const item of state.destinations.filter((candidate) => candidate.enabled || candidate.id === selected)) {
    select.append(element("option", { value: item.id, text: `${item.name} (${OUTPUT_NAMES[item.output_type] || item.output_type})` }));
  }
  if (selected) select.value = selected;
}

function setRouteSourceOptions(
  selectedSource = "",
  selectedInput = "",
) {
  const select = byId("route-source");
  select.replaceChildren();

  const currentValue = `${selectedSource}::${selectedInput}`;

  for (const option of state.routeSourceOptions) {
    const value = `${option.source}::${option.input_type}`;
    select.append(
      element("option", {
        value,
        text: option.label,
      }),
    );
  }

  if (
    selectedSource
    && ![...select.options].some(
      (option) => option.value === currentValue,
    )
  ) {
    const descriptor = routeSourceDescriptor(
      selectedSource,
      selectedInput,
    );
    select.append(
      element("option", {
        value: currentValue,
        text: `${descriptor.label} (legacy)`,
      }),
    );
  }

  if (selectedSource) {
    select.value = currentValue;
  }

  if (select.dataset.nce39FilterBound !== "1") {
    select.dataset.nce39FilterBound = "1";

    select.addEventListener("change", () => {
      const previousSource =
        select.dataset.routeFilterSource || "";
      const nextSource = routeSelectedSource();

      const filters = previousSource === nextSource
        ? currentRouteFilterSelections()
        : {};

      refreshRouteFilterOptions(filters);
    });
  }
}

function openRoute(id = "") {
  if (!state.destinations.length) {
    toast("Add a destination before creating a route.", "error");
    navigate("destinations");
    return;
  }
  const item = state.routes.find((candidate) => candidate.id === id);
  byId("route-form").reset();
  clearError("route-error");
  byId("route-id").value = item ? item.id : "";
  byId("route-name").value = item ? item.name : "";
  setRouteSourceOptions(item ? item.source : "zabbix", item ? item.input_type : "smtp");
  byId("route-priority").value = item ? (item.priority_name || "normal") : "normal";
  byId("route-enabled").checked = item ? item.enabled : true;
  setRouteOptions(item ? item.destination_id : "");
  refreshRouteFilterOptions(
    item && item.filters ? item.filters : {},
  );
  for (const key of ["hosts", "events", "exclude_hosts", "exclude_events"]) {
    byId(`route-${key}`).value = item && item.filters[key] ? item.filters[key].join(", ") : "";
  }
  byId("route-dialog-title").textContent = item ? `Edit ${item.name}` : "Add route";
  byId("route-dialog").showModal();
}

async function saveRoute(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("route-dialog").close();
    return;
  }
  clearError("route-error");
  const id = byId("route-id").value;
  const filters = {};
  const selectedSource = routeSelectedSource();

  for (const key of ["severities", "statuses"]) {
    const available = routeFilterValuesForSource(
      selectedSource,
      key,
    );

    if (!available.length) continue;

    const values = [...byId(`route-${key}`).selectedOptions]
      .map((option) => option.value);

    if (!values.length) {
      const label = key === "severities"
        ? "severity"
        : "status";

      showValidationError(
        "route-error",
        `Select at least one included ${label}.`,
      );
      return;
    }

    filters[key] = values;
  }

  for (const key of ["hosts", "events", "exclude_hosts", "exclude_events"]) {
    const values = splitList(byId(`route-${key}`).value);
    if (values.length) filters[key] = values;
  }
  const [source, inputType] = byId("route-source").value.split("::", 2);
  try {
    await request(id ? `/routes/${id}` : "/routes", {
      method: id ? "PATCH" : "POST",
      body: {
        name: byId("route-name").value.trim(),
        source,
        input_type: inputType,
        destination_id: byId("route-destination").value,
        priority: byId("route-priority").value,
        enabled: byId("route-enabled").checked,
        filters,
      },
    });
    byId("route-dialog").close();
    await loadWorkspace();
    toast(id ? "Route updated." : "Route added.");
  } catch (error) {
    showError("route-error", error);
  }
}

function openToken() {
  byId("token-form").reset();
  byId("token-rate").value = 60;
  const select = byId("token-sources");
  select.replaceChildren();
  if (isAdmin()) {
    select.append(element("option", { value: "*", text: "All sources (administrator only)" }));
  }
  for (const integration of state.integrations) {
    select.append(element("option", { value: integration.source || integration.id, text: integration.name }));
  }
  clearError("token-error");
  byId("token-dialog").showModal();
}

async function saveToken(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("token-dialog").close();
    return;
  }
  clearError("token-error");
  const sourceScopes = [
    ...new Set([
      ...[...byId("token-sources").selectedOptions].map((option) => option.value),
      ...splitList(byId("token-custom-sources").value),
    ]),
  ];
  if (!sourceScopes.length) {
    showValidationError("token-error", "Select at least one integration or enter a custom source identifier.");
    return;
  }
  try {
    const response = await request("/tokens", {
      method: "POST",
      body: {
        name: byId("token-name").value.trim(),
        source_scopes: sourceScopes,
        rate_limit_per_minute: Number(byId("token-rate").value),
      },
    });
    byId("token-dialog").close();
    revealSecret(response.value, response.token.name);
    await loadWorkspace();
  } catch (error) {
    showError("token-error", error);
  }
}

function revealSecret(value, name) {
  byId("secret-title").textContent = `${name} token`;
  byId("secret-value").textContent = value;
  byId("secret-dialog").showModal();
}

function openUser(id = "") {
  const item = state.users.find((candidate) => candidate.id === id);
  const dialog = byId("user-dialog");
  const form = byId("user-form");
  form.reset();
  clearError("user-error");
  form.dataset.mode = item ? "reset" : "create";
  form.dataset.id = item ? item.id : "";
  byId("user-name").value = item ? item.username : "";
  byId("user-name").disabled = Boolean(item);
  byId("user-role").closest("label").hidden = Boolean(item);
  dialog.querySelector("h2").textContent = item ? `Reset ${item.username}` : "Add user";
  form.querySelector(".button.primary").textContent = item ? "Reset password" : "Create user";
  dialog.showModal();
}

async function saveUser(event) {
  event.preventDefault();
  if (event.submitter && event.submitter.value === "cancel") {
    byId("user-dialog").close();
    return;
  }
  clearError("user-error");
  const form = byId("user-form");
  try {
    if (form.dataset.mode === "reset") {
      await request(`/users/${form.dataset.id}/password`, { method: "PUT", body: { password: byId("user-password").value } });
      toast("Password reset and active sessions revoked.");
    } else {
      await request("/users", { method: "POST", body: { username: byId("user-name").value.trim(), password: byId("user-password").value, role: byId("user-role").value } });
      toast("User created.");
    }
    byId("user-dialog").close();
    await loadWorkspace();
  } catch (error) {
    showError("user-error", error);
  }
}

function openPreview(id) {
  const item = state.destinations.find((candidate) => candidate.id === id);
  if (!item) return;
  byId("preview-form").reset();
  byId("preview-destination-id").value = id;
  byId("preview-title").textContent = `Preview ${item.name}`;
  const route = state.routes.find((candidate) => candidate.destination_id === id && candidate.source !== "*");
  byId("preview-source").value = route ? route.source : "home_assistant";
  byId("preview-result").hidden = true;
  byId("test-button").hidden = !isAdmin();
  clearError("preview-error");
  byId("preview-dialog").showModal();
}

function sampleEvent() {
  return {
    schema: "nowlert.event.v1",
    source: byId("preview-source").value.trim(),
    title: byId("preview-event-title").value.trim(),
    message: byId("preview-message").value.trim(),
    severity: byId("preview-severity").value,
    status: "active",
    metadata: { host: "webui-safe-preview" },
  };
}

function cardSampleEvent(destination) {
  const outputName =
    OUTPUT_NAMES[destination.output_type]
    || friendlyName(destination.output_type);
  return {
    schema: "nowlert.event.v1",
    source: "nowlert",
    title: `${destination.name} test delivery`,
    message: `This is a safe Nowlert test for the ${outputName} destination "${destination.name}".`,
    severity: "information",
    status: "active",
    category: "event",
    provider: "Nowlert",
    host: destination.name,
    metadata: {
      component: "Destination test",
      destination: destination.name,
      output: destination.output_type,
    },
  };
}

async function runPreview(event) {
  event.preventDefault();
  const action = event.submitter && event.submitter.value;
  if (action === "cancel") {
    byId("preview-dialog").close();
    return;
  }
  if (!action) return;
  clearError("preview-error");
  const destinationId = byId("preview-destination-id").value;
  try {
    const response = await request(`/destinations/${destinationId}/${action}`, { method: "POST", body: { event: sampleEvent() } });
    const result = byId("preview-result");
    const selectedDestination = state.destinations.find((candidate) => candidate.id === destinationId);
    const outputType = response.preview ? response.preview.output_type : selectedDestination && selectedDestination.output_type;
    result.textContent = `${OUTPUT_NAMES[outputType] || friendlyName(outputType)} preview\n\n${JSON.stringify(response, null, 2)}`;
    result.hidden = false;
    if (action === "test") {
      const delivery = response.result || {};
      state.destinationTestResults[destinationId] = {
        success: delivery.success === true,
        response_status: delivery.response_status || null,
        error_code: delivery.error_code || "",
        safe_error: delivery.safe_error || "",
        tested_at: Date.now(),
      };
      if (response.destination) {
        updateDestinationState(response.destination);
      } else {
        renderDestinations();
        renderFlow();
      }
      const notification = destinationTestToast(delivery, outputType);
      toast(notification.message, notification.style);
    }
  } catch (error) {
    showError("preview-error", error);
  }
}

function confirmAction(title, message, acceptLabel = "Confirm") {
  byId("confirm-title").textContent = title;
  byId("confirm-message").textContent = message;
  byId("confirm-accept").textContent = acceptLabel;
  byId("confirm-dialog").showModal();
  return new Promise((resolve) => {
    state.confirmResolve = resolve;
  });
}

function resolveConfirm(value) {
  byId("confirm-dialog").close();
  if (state.confirmResolve) state.confirmResolve(value);
  state.confirmResolve = null;
}

async function resourceAction(action, id) {
  try {
    if (action === "logout") {
      await logout();
      return;
    } else if (action === "run-health-checks") {
      const response = await request("/health-checks");
      state.healthChecks = response.checks;
      const audit = await request("/audit-events");
      state.audit = audit.audit_events;
      renderHealthChecks();
      renderAudit();
      toast("Health checks completed.");
      return;
    } else if (action === "remove-avatar") {
      const response = await request("/account/avatar", { method: "DELETE" });
      state.user = response.user;
      applyAvatar("profile-avatar", state.user);
      applyAvatar("account-avatar", state.user);
      byId("avatar-file").value = "";
      byId("avatar-editor").hidden = true;
      byId("avatar-zoom").value = "1";
      if (state.avatarEditor.image && typeof state.avatarEditor.image.close === "function") {
        state.avatarEditor.image.close();
      }
      state.avatarEditor.image = null;
      const avatarSave = byId("avatar-save");
      if (avatarSave) {
        avatarSave.hidden = true;
        avatarSave.disabled = true;
      }
      toast("Profile picture removed.");
      return;
    } else if (action === "export-platform") {
      await exportPlatform();
      return;
    } else if (action === "preview-backup-portable-import") {
      await previewImport("portable", "backup-portable-file");
      return;
    } else if (action === "preview-migration") {
      await previewImport("v1_yaml");
      return;
    } else if (action === "preview-local-migration") {
      await previewImport("local_yaml");
      return;
    } else if (action === "use-yaml-routing") {
      await setRoutingAuthority("yaml");
      return;
    } else if (action === "use-database-routing") {
      await setRoutingAuthority("database");
      return;
    } else if (action === "apply-import") {
      await applyImport();
      return;
    } else if (action === "toggle-housekeeping") {
      await toggleHousekeeping();
      return;
    } else if (action === "create-backup") {
      await createBackup();
      return;
    } else if (action === "create-remote-backup") {
      await createRemoteBackup();
      return;
    } else if (action === "refresh-external-backups") {
      await refreshBackupPanels();
      return;
    } else if (action === "view-all-backups") {
      state.showAllBackups = !state.showAllBackups;
      renderBackupRecoveryTable();
      return;
    } else if (action === "view-all-stored-backups") {
      state.showAllStoredBackups = !state.showAllStoredBackups;
      renderStoredBackupTable();
      return;
    } else if (action === "test-backup-target") {
      const response = await request(`/backup-targets/${id}/test`, { method: "POST", body: {} });
      const index = state.backupTargets.findIndex((item) => item.id === id);
      if (index >= 0) state.backupTargets[index] = response.target;
      renderBackupTargets();
      toast(response.target.last_test_outcome === "success" ? "Backup destination is writable." : response.target.last_error || "Backup destination test failed.", response.target.last_test_outcome === "success" ? "success" : "error");
      return;
    } else if (action === "delete-backup-target") {
      const accepted = await confirmAction("Delete backup destination?", "The destination record and stored credential are removed. Existing backup files are not deleted.", "Delete");
      if (!accepted) return;
      await request(`/backup-targets/${id}`, { method: "DELETE" });
      state.externalBackups = state.externalBackups.filter((item) => item.target_id !== id);
      state.externalBackupErrors = state.externalBackupErrors.filter((item) => item.target_id !== id);
      await loadWorkspace();
      if (state.currentView === "backups") renderExternalBackups();
      toast("Backup destination removed.");
      return;
    } else if (action === "restart-platform") {
      byId("restart-form").reset();
      clearError("restart-error");
      updateRestartDialogContext();
      byId("restart-dialog").showModal();
      return;
    } else if (action === "restore-backup") {
      await restoreBackup(id);
      return;
    } else if (action === "restore-external-backup") {
      const separator = id.indexOf(":");
      if (separator < 1) throw new Error("Stored backup identifier is invalid.");
      await restoreExternalBackup(id.slice(0, separator), id.slice(separator + 1));
      return;
    } else if (action === "delete-backup") {
      const accepted = await confirmAction(
        `Delete recovery snapshot ${id}?`,
        "This permanently deletes this local recovery snapshot. It cannot be restored after deletion.",
        "Delete snapshot",
      );
      if (!accepted) return;
      await request(`/backups/${id}`, { method: "DELETE" });
      state.backups = state.backups.filter((item) => item.id !== id);
      renderBackups();
      toast("Recovery snapshot deleted.");
    } else if (action === "toggle-destination") {
      const item = state.destinations.find((candidate) => candidate.id === id);
      const response = await request(`/destinations/${id}`, {
        method: "PATCH",
        body: { enabled: !item.enabled },
      });
      const updated = response.destination || { ...item, enabled: !item.enabled };
      updateDestinationState(updated);
      document.dispatchEvent(new CustomEvent("nowlert:filtering-state-invalidated"));
      document.dispatchEvent(new CustomEvent("nowlert:routing-topology-changed"));
      toast(`Destination ${updated.enabled ? "enabled" : "disabled"}.`);
      return;
    } else if (action === "toggle-destination-shared") {
      const item = state.destinations.find((candidate) => candidate.id === id);
      const response = await request(`/destinations/${id}`, {
        method: "PATCH",
        body: { shared: !item.shared },
      });
      const updated = response.destination || { ...item, shared: !item.shared };
      updateDestinationState(updated);
      toast(`Destination changed to ${updated.shared ? "shared" : "private"}.`);
      return;
    } else if (action === "test-destination-card") {
      const destination = state.destinations.find((candidate) => candidate.id === id);
      if (!destination) return;
      const response = await request(`/destinations/${id}/test`, {
        method: "POST",
        body: { event: cardSampleEvent(destination) },
      });
      const delivery = response.result || {};
      state.destinationTestResults[id] = {
        success: delivery.success === true,
        response_status: delivery.response_status || null,
        error_code: delivery.error_code || "",
        safe_error: delivery.safe_error || "",
        tested_at: Date.now(),
      };
      if (response.destination) {
        const index = state.destinations.findIndex(
          (item) => item.id === response.destination.id,
        );
        if (index >= 0) {
          state.destinations[index] = response.destination;
        }
      }
      renderDestinations();
      renderFlow();
      const notification = destinationTestToast(
        delivery,
        destination.output_type,
      );
      toast(notification.message, notification.style);
      return;
    } else if (action === "delete-destination") {
      const accepted = await confirmAction("Delete destination?", "Deletion is permanent and is rejected while a route still uses this destination.", "Delete");
      if (!accepted) return;
      await request(`/destinations/${id}`, { method: "DELETE" });
      toast("Destination deleted.");
    } else if (action === "toggle-route") {
      const item = state.routes.find((candidate) => candidate.id === id);
      await request(`/routes/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      toast(`Route ${item.enabled ? "disabled" : "enabled"}.`);
    } else if (action === "delete-route") {
      const accepted = await confirmAction("Delete route?", "Events will stop using this route immediately.", "Delete");
      if (!accepted) return;
      await request(`/routes/${id}`, { method: "DELETE" });
      toast("Route deleted.");
    } else if (action === "rotate-token") {
      const accepted = await confirmAction("Rotate application token?", "The current value stops working immediately.", "Rotate");
      if (!accepted) return;
      const response = await request(`/tokens/${id}/rotate`, { method: "POST", body: {} });
      revealSecret(response.value, response.token.name);
    } else if (action === "revoke-token") {
      const accepted = await confirmAction("Revoke application token?", "Revocation is immediate and cannot be undone.", "Revoke");
      if (!accepted) return;
      await request(`/tokens/${id}/revoke`, { method: "POST", body: {} });
      toast("Token revoked.");
    } else if (action === "toggle-token") {
      const item = state.tokens.find((candidate) => candidate.id === id);
      await request(`/tokens/${id}`, { method: "PATCH", body: { enabled: item.enabled === false } });
      toast(`Application ${item.enabled === false ? "enabled" : "disabled"}.`);
    } else if (action === "delete-token") {
      const accepted = await confirmAction("Delete application credential?", "The credential stops working immediately and cannot be recovered.", "Delete");
      if (!accepted) return;
      await request(`/tokens/${id}`, { method: "DELETE" });
      toast("Application credential deleted.");
    } else if (action === "toggle-input") {
      const item = state.configuration.inputs.find((candidate) => candidate.name === id);
      await request(`/configuration/inputs/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      toast(`Input ${item.enabled ? "disabled" : "enabled"}. Restart Nowlert to apply listener changes.`);
    } else if (action === "toggle-user") {
      const item = state.users.find((candidate) => candidate.id === id);
      const accepted = await confirmAction(`${item.enabled ? "Disable" : "Enable"} ${item.username}?`, item.enabled ? "Disabling the account revokes every active session." : "The user will be able to sign in again.", item.enabled ? "Disable" : "Enable");
      if (!accepted) return;
      await request(`/users/${id}`, { method: "PATCH", body: { enabled: !item.enabled } });
      toast(`User ${item.enabled ? "disabled" : "enabled"}.`);
    } else if (action === "delete-user") {
      const item = state.users.find((candidate) => candidate.id === id);
      if (!item) return;

      const accepted = await confirmAction(
        `Delete ${item.username}?`,
        "This permanently removes the account and its sessions, API tokens, routes, and delivery history. Deletion is blocked while the user still owns destinations, secrets, or backup destinations.",
        "Delete user",
      );
      if (!accepted) return;

      await request(`/users/${id}`, { method: "DELETE" });
      toast(`User ${item.username} deleted.`);
    }
    await loadWorkspace();
  } catch (error) {
    toast(error.message || "The action failed.", "error");
  }
}

async function changePassword(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  if (form.get("new_password") !== form.get("confirm_password")) {
    toast("New password confirmation does not match.", "error");
    return;
  }
  const accepted = await confirmAction("Change password and sign out?", "Every active session for this account will be revoked.", "Change password");
  if (!accepted) return;
  try {
    await request("/account/password", { method: "PUT", body: { current_password: form.get("current_password"), new_password: form.get("new_password") } });
    expireSession({ preserveCache: false });
    toast("Password changed. Sign in again.");
  } catch (error) {
    toast(error.message || "Password change failed.", "error");
  }
}

async function logout() {
  try {
    await request("/session", { method: "DELETE" });
  } catch (_error) {
  }
  expireSession({ preserveCache: false });
}

function toggleProfileMenu() {
  const menu = byId("profile-menu-popover");
  const open = menu.hidden;
  menu.hidden = !open;
  byId("profile-menu-button").setAttribute("aria-expanded", String(open));
  if (open) menu.querySelector("button").focus();
}

function closeProfileMenu() {
  const menu = byId("profile-menu-popover");
  if (!menu) return;
  menu.hidden = true;
  byId("profile-menu-button").setAttribute("aria-expanded", "false");
}

async function copySecret() {
  try {
    await navigator.clipboard.writeText(byId("secret-value").textContent);
    toast("Token copied.");
  } catch (_error) {
    toast("Copy was blocked. Select the token and copy it manually.", "error");
  }
}

async function handleClick(event) {
  const target = event.target.closest("button");
  if (!target) {
    if (!event.target.closest(".profile-menu")) closeProfileMenu();
    return;
  }
  if (target.dataset.view) {
    navigate(target.dataset.view);
    return;
  }
  if (target.dataset.closeDialog) {
    byId(target.dataset.closeDialog).close();
    return;
  }
  const action = target.dataset.action;
  const id = target.dataset.id || "";
  if (action === "toggle-profile-menu") toggleProfileMenu();
  else if (action === "edit-integration-settings") openIntegrationSettings(id);
  else if (action === "new-destination") openDestination();
  else if (action === "edit-destination") openDestination(id);
  else if (action === "preview-destination") openPreview(id);
  else if (action === "new-route") openRoute();
  else if (action === "edit-route") openRoute(id);
  else if (action === "new-token") openToken();
  else if (action === "new-user") openUser();
  else if (action === "reset-user") openUser(id);
  else if (action === "account-mfa") void openMfaDialog();
  else if (action === "new-backup-target") openBackupTarget();
  else if (action === "edit-backup-target") openBackupTarget(id);
  else if (action) await resourceAction(action, id);
}

function setSidebarCollapsed(collapsed) {
  const shell = byId("app-shell");
  const button = byId("sidebar-collapse-button");
  if (!shell || !button) return;
  shell.classList.toggle("sidebar-collapsed", Boolean(collapsed));
  button.setAttribute("aria-expanded", String(!collapsed));
  button.setAttribute(
    "aria-label",
    collapsed ? "Expand navigation" : "Collapse navigation",
  );
  button.title = collapsed ? "Expand navigation" : "Collapse navigation";
}

function bindEvents() {
  ensureSessionResilienceUi();
  window.setInterval(() => {
    if (
      !state.user
      || state.currentView !== "destinations"
      || document.visibilityState === "hidden"
    ) return;
    refreshDestinationState().catch(() => {});
  }, DESTINATION_STATE_SYNC_INTERVAL_MS);
  window.addEventListener("focus", () => {
    if (!state.user || state.currentView !== "destinations") return;
    refreshDestinationState().catch(() => {});
  });
  document.addEventListener("visibilitychange", () => {
    if (
      !state.user
      || state.currentView !== "destinations"
      || document.visibilityState !== "visible"
    ) return;
    refreshDestinationState().catch(() => {});
  });
  byId("bootstrap-form").addEventListener("submit", bootstrapAdministrator);
  byId("login-form").addEventListener("submit", login);
  byId("login-password-toggle")?.addEventListener("click", toggleLoginPasswordVisibility);
  byId("destination-form").addEventListener("submit", saveDestination);
  byId("destination-type").addEventListener("change", () => renderDestinationFields());
  byId("route-form").addEventListener("submit", saveRoute);
  byId("token-form").addEventListener("submit", saveToken);
  byId("user-form").addEventListener("submit", saveUser);
  byId("preview-form").addEventListener("submit", runPreview);
  byId("password-form").addEventListener("submit", changePassword);
  byId("mfa-enable-form")?.addEventListener("submit", confirmMfaSetup);
  byId("mfa-disable-form")?.addEventListener("submit", disableMfa);
  byId("mfa-close")?.addEventListener("click", closeMfaDialog);
  byId("mfa-copy-secret")?.addEventListener("click", copyMfaSecret);
  for (const input of mfaDigitInputs()) {
    input.addEventListener("input", handleMfaDigitInput);
    input.addEventListener("keydown", handleMfaDigitKeydown);
    input.addEventListener("paste", handleMfaDigitPaste);
  }
  byId("import-copy-preview")?.addEventListener("click", copyImportPreview);
  byId("import-issue-filter")?.addEventListener("change", () => {
    renderImportIssues(state.pendingImport?.preview || {});
  });
  byId("preferences-form").addEventListener("submit", savePreferences);
  byId("preference-language").addEventListener("change", applyLanguageDefaultTimezone);
  byId("integration-settings-form").addEventListener("submit", saveIntegrationSettings);
  byId("integration-settings-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeIntegrationSettings();
  });
  byId("backup-settings-form").addEventListener("submit", saveBackupSettings);
  byId("housekeeping-form")?.addEventListener("submit", saveHousekeepingSettings);
  byId("backup-target-form").addEventListener("submit", saveBackupTarget);
  byId("backup-target-type").addEventListener("change", updateBackupTargetFields);
  byId("restart-form").addEventListener("submit", restartPlatform);
  byId("restart-reason").addEventListener("input", updateRestartDialogContext);
  byId("avatar-form").addEventListener("submit", saveAvatar);
  byId("avatar-file").addEventListener("change", () => loadAvatarEditor().catch((error) => {
    updateAvatarSaveState(false);
    toast(error.message, "error");
  }));
  byId("avatar-zoom").addEventListener("input", zoomAvatarEditor);
  byId("avatar-canvas").addEventListener("pointerdown", (event) => {
    state.avatarEditor.dragging = true;
    state.avatarEditor.pointerX = event.clientX;
    state.avatarEditor.pointerY = event.clientY;
    byId("avatar-canvas").setPointerCapture(event.pointerId);
  });
  byId("avatar-canvas").addEventListener("pointermove", moveAvatarEditor);
  byId("avatar-canvas").addEventListener("pointerup", () => { state.avatarEditor.dragging = false; });
  byId("avatar-canvas").addEventListener("pointercancel", () => { state.avatarEditor.dragging = false; });
  byId("history-range").addEventListener("change", changeHistoryRange);
  byId("copy-secret").addEventListener("click", copySecret);
  byId("source-table").addEventListener("change", saveSourceCategory);
  byId("delivery-search").addEventListener("input", renderDeliveries);
  byId("audit-search").addEventListener("input", renderAudit);
  byId("audit-page-size").addEventListener("change", () => {
    state.auditPageSize = Number(byId("audit-page-size").value);
    renderAudit();
  });
  byId("confirm-cancel").addEventListener("click", () => resolveConfirm(false));
  byId("confirm-accept").addEventListener("click", () => resolveConfirm(true));
  byId("confirm-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    resolveConfirm(false);
  });
  byId("secret-dialog").addEventListener("close", () => {
    byId("secret-value").textContent = "";
  });
  byId("import-dialog").addEventListener("close", () => {
    state.pendingImport = null;
    byId("import-result").textContent = "";
    byId("portable-file").value = "";
    const backupPortableFile = byId("backup-portable-file");
    if (backupPortableFile) backupPortableFile.value = "";
    const migrationFile = byId("migration-file");
    if (migrationFile) migrationFile.value = "";
    clearError("import-error");
  });
  byId("mobile-menu").addEventListener("click", () => {
    const shell = byId("app-shell");
    const open = shell.classList.toggle("nav-open");
    byId("mobile-menu").setAttribute("aria-expanded", String(open));
  });
  byId("sidebar-collapse-button")?.addEventListener("click", () => {
    setSidebarCollapsed(!byId("app-shell").classList.contains("sidebar-collapsed"));
  });
  byId("session-stay-signed-in")?.addEventListener("click", () => {
    void refreshSession();
  });
  byId("reauth-form")?.addEventListener("submit", submitReauthentication);
  byId("reauth-signout")?.addEventListener("click", () => {
    finishReauthentication(false);
    void logout();
  });
  byId("reauth-dialog")?.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    byId("reauth-password")?.focus();
  });
  for (const eventName of ["pointerdown", "keydown", "input"]) {
    document.addEventListener(eventName, noteSessionActivity, true);
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") updateSessionWarning();
  });
  window.setInterval(updateSessionWarning, 15_000);
  document.addEventListener("click", handleClick);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !byId("profile-menu-popover").hidden) {
      closeProfileMenu();
      byId("profile-menu-button").focus();
    }
  });
  const navigateFromHistory = () => {
    const view = window.location.hash.slice(1);
    if (state.user && VIEW_TITLES[view] && state.currentView !== view) {
      navigate(view, "none");
    }
  };
  window.addEventListener("popstate", navigateFromHistory);
  window.addEventListener("hashchange", navigateFromHistory);
}

// Prefetch both startup requests during app.js execution. The authenticated
// shell remains gated below until DOMContentLoaded, after every deferred WebUI
// extension has executed, so cached pages can hydrate immediately without an
// old-interface flash.
const startupRequests = {
  session: request("/session"),
  bootstrap: request("/bootstrap"),
};
void startupRequests.session.catch(() => {});
void startupRequests.bootstrap.catch(() => {});

bindEvents();

let applicationStarted = false;
function startApplication() {
  if (applicationStarted) return;
  applicationStarted = true;
  void initialize(startupRequests);
}

// app.js is the first deferred script, while the production WebUI injects the
// Routing Flow, Filtering, ownership, header, and acceptance layers after it.
// DOMContentLoaded still gates the first authenticated paint; only the network
// requests are prefetched while those layers execute.
document.addEventListener("DOMContentLoaded", startApplication, { once: true });
window.addEventListener("load", startApplication, { once: true });
if (document.readyState === "complete") startApplication();