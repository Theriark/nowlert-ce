"use strict";

/* Interface translations and the regional language list.
 *
 * Every English interface string of the WebUI is listed in
 * src/webui/i18n/source.json (tools/i18n_extract.mjs builds it from the
 * scripts and index.html). Each offered language has a catalogue
 * src/webui/i18n/<code>.json, served at /ui/i18n/<code>.json, that translates
 * every one of them; tools/i18n_check.mjs and the WebUI tests keep them
 * complete. Strings with {0}, {1}, ... are patterns: "User {0} created."
 * matches "User alice created." and keeps "alice".
 *
 * The page is translated in place: every text node and the placeholder,
 * title, aria-label and alt attributes whose text is a known interface
 * string are replaced, and a MutationObserver translates whatever the page
 * renders later. The English source of each node is remembered, so switching
 * back to English restores it. Names, user data and anything that is not a
 * known interface string stay as they are.
 */
(() => {
  const CATALOGUE_CODES = new Set([
    "cs", "da", "de", "el", "es", "fi", "fr", "it", "ja", "nb",
    "nl", "pl", "pt", "ro", "ru", "sv", "tr", "uk", "zh",
  ]);
  const ATTRIBUTES = ["placeholder", "title", "aria-label", "alt"];
  const SKIP_SELECTOR = [
    "script", "style", "code", "pre", "textarea", "#preference-language",
    "[data-i18n-skip]", "[contenteditable='true']",
  ].join(", ");
  // A node the page keeps resetting is left alone after this many
  // translations within one second, so two observers can never loop.
  const LOOP_LIMIT = 20;

  const catalogues = new Map();
  const loading = new Map();
  const textSources = new WeakMap();
  const attributeSources = new WeakMap();
  const loopCounts = new WeakMap();
  let active = null;
  let activeCode = "";
  let observer = null;

  function catalogueCode() {
    const language = String(state.preferences?.language || "en-GB");
    const base = language.split("-")[0].toLowerCase();
    return CATALOGUE_CODES.has(base) ? base : "";
  }

  function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function compile(data) {
    const exact = new Map();
    const patterns = [];
    for (const [source, target] of Object.entries(data || {})) {
      if (typeof target !== "string") continue;
      if (!/\{\d+\}/.test(source)) {
        exact.set(source, target);
        continue;
      }
      const literal = source.replace(/\{\d+\}/g, "");
      // A pattern made only of placeholders and punctuation ("{0} {1}")
      // would match any text, including names; it is not used.
      if ((literal.match(/\p{L}/gu) || []).length < 2) continue;
      const slots = [];
      const expression = source.split(/(\{\d+\})/).map((part) => {
        const slot = part.match(/^\{(\d+)\}$/);
        if (slot) {
          slots.push(slot[1]);
          return "([\\s\\S]*?)";
        }
        return escapeRegExp(part);
      }).join("");
      patterns.push({ regex: new RegExp(`^${expression}$`), slots, target, weight: literal.length });
    }
    patterns.sort((left, right) => right.weight - left.weight);
    return { exact, patterns };
  }

  function translateText(text, catalogue, depth = 0) {
    const exact = catalogue.exact.get(text);
    if (exact !== undefined) return exact;
    if (depth > 2 || text.length > 600) return null;
    for (const pattern of catalogue.patterns) {
      const match = text.match(pattern.regex);
      if (!match) continue;
      const values = {};
      pattern.slots.forEach((slot, index) => {
        const value = match[index + 1];
        values[slot] = translateText(value, catalogue, depth + 1) ?? value;
      });
      return pattern.target.replace(/\{(\d+)\}/g, (_whole, slot) => values[slot] ?? "");
    }
    return null;
  }

  function normalized(text) {
    return text.replace(/\s+/g, " ").trim();
  }

  function looping(node) {
    const now = Date.now();
    const entry = loopCounts.get(node);
    if (!entry || now - entry.since > 1000) {
      loopCounts.set(node, { since: now, count: 1 });
      return false;
    }
    entry.count += 1;
    return entry.count > LOOP_LIMIT;
  }

  function skipped(element) {
    return Boolean(element && element.closest(SKIP_SELECTOR));
  }

  function translateTextNode(node) {
    const record = textSources.get(node);
    const source = record && node.data === record.rendered ? record.source : node.data;
    const key = normalized(source);
    if (!active || !key || !/\p{L}/u.test(key)) {
      if (record && node.data === record.rendered) node.data = record.source;
      textSources.delete(node);
      return;
    }
    const target = translateText(key, active);
    if (target === null) {
      if (record && node.data === record.rendered) node.data = record.source;
      textSources.delete(node);
      return;
    }
    const leading = source.match(/^\s*/)[0];
    const trailing = source.match(/\s*$/)[0];
    const rendered = `${leading}${target}${trailing}`;
    if (node.data !== rendered) {
      if (looping(node)) return;
      node.data = rendered;
    }
    textSources.set(node, { source, rendered });
  }

  function translateAttributes(element) {
    let records = attributeSources.get(element);
    for (const name of ATTRIBUTES) {
      if (!element.hasAttribute(name)) continue;
      const current = element.getAttribute(name);
      const record = records?.[name];
      const source = record && current === record.rendered ? record.source : current;
      const target = active ? translateText(normalized(source), active) : null;
      const rendered = target === null ? source : target;
      if (current !== rendered) {
        if (looping(element)) continue;
        element.setAttribute(name, rendered);
      }
      if (target === null) {
        if (records) delete records[name];
        continue;
      }
      if (!records) {
        records = {};
        attributeSources.set(element, records);
      }
      records[name] = { source, rendered };
    }
  }

  function translateTree(root) {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      if (!skipped(root.parentElement)) translateTextNode(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
    const element = root.nodeType === Node.DOCUMENT_NODE ? root.body : root;
    if (!element || skipped(element)) return;
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode: (node) => (skipped(node.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) translateTextNode(node);
    translateAttributes(element);
    for (const item of element.querySelectorAll("[placeholder], [title], [aria-label], [alt]")) {
      if (!skipped(item)) translateAttributes(item);
    }
  }

  // Narrow layouts label table cells with CSS content ("Status"). Those
  // rules are repeated with the translated text in a constructed style sheet
  // (the page's Content-Security-Policy allows no inline style element).
  let contentSheet = null;
  function translateStyleContent() {
    if (typeof CSSStyleSheet !== "function" || !("adoptedStyleSheets" in document)) return;
    const rules = [];
    const collect = (list, wrap) => {
      for (const rule of list || []) {
        if (rule.cssRules && rule.media) {
          collect(rule.cssRules, (text) => wrap(`@media ${rule.media.mediaText} { ${text} }`));
          continue;
        }
        const match = rule.style?.content?.match(/^"(.*)"$/);
        if (!match) continue;
        const target = translateText(match[1], active);
        if (target !== null) rules.push(wrap(`${rule.selectorText} { content: ${JSON.stringify(target)}; }`));
      }
    };
    if (active) {
      for (const sheet of document.styleSheets) {
        let list;
        try { list = sheet.cssRules; } catch { continue; }
        collect(list, (text) => text);
      }
    }
    if (!contentSheet) {
      contentSheet = new CSSStyleSheet();
      document.adoptedStyleSheets = [...document.adoptedStyleSheets, contentSheet];
    }
    contentSheet.replaceSync(rules.join("\n"));
  }

  function observe() {
    if (observer || typeof MutationObserver !== "function") return;
    observer = new MutationObserver((records) => {
      if (!active) return;
      for (const record of records) {
        if (record.type === "characterData") translateTree(record.target);
        else if (record.type === "attributes") {
          if (!skipped(record.target)) translateAttributes(record.target);
        } else {
          for (const node of record.addedNodes) translateTree(node);
        }
      }
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRIBUTES,
    });
  }

  function loadCatalogue(code) {
    if (catalogues.has(code)) return Promise.resolve(catalogues.get(code));
    if (typeof fetch !== "function") return Promise.reject(new Error("fetch is unavailable"));
    if (!loading.has(code)) {
      loading.set(code, fetch(`/ui/i18n/${code}.json`, { credentials: "same-origin", cache: "no-cache" })
        .then((response) => {
          if (!response.ok) throw new Error(`catalogue ${code}: HTTP ${response.status}`);
          return response.json();
        })
        .then((data) => {
          const catalogue = compile(data);
          catalogues.set(code, catalogue);
          return catalogue;
        })
        .finally(() => loading.delete(code)));
    }
    return loading.get(code);
  }

  function useCatalogue(code, catalogue) {
    activeCode = code;
    active = catalogue;
    if (document.body) {
      observe();
      translateTree(document.body);
    }
    translateStyleContent();
  }

  // en-US and pt-BR exist only so an older saved value still displays. The
  // hidden attribute does not hide an <option> in every browser, so an alias
  // that is not the saved value is taken out of the list (and put back before
  // the next render) instead of showing "English" or "Português" twice.
  const regionalDetachedLanguageAliases = new Map();

  function regionalRestoreLanguageAliases() {
    const select = byId("preference-language");
    if (!select) return;
    for (const [value, option] of regionalDetachedLanguageAliases) {
      const canonical = select.querySelector(`option[value="${value === "en-US" ? "en-GB" : "pt-PT"}"]`);
      select.insertBefore(option, canonical ? canonical.nextSibling : null);
    }
    regionalDetachedLanguageAliases.clear();
  }

  function regionalNormalizeLanguageLabels() {
    const select = byId("preference-language");
    if (!select) return;

    const languageLabels = {
      "en-GB": "English",
      "en-US": "English",
      "pt-PT": "Português",
      "pt-BR": "Português",
    };

    for (const option of [...select.options]) {
      option.hidden = option.value === "en-US" || option.value === "pt-BR";
      if (languageLabels[option.value]) {
        option.textContent = languageLabels[option.value];
      }
      delete option.dataset.i18nSource;
      if (option.hidden && select.value !== option.value) {
        regionalDetachedLanguageAliases.set(option.value, option);
        option.remove();
      }
    }
  }

  applyLanguage = function applyLanguageWithCatalogues() {
    const language = String(state.preferences?.language || "en-GB");
    document.documentElement.lang = language;
    const code = catalogueCode();
    if (!code) {
      if (active || activeCode) useCatalogue("", null);
      return;
    }
    if (code === activeCode && active) {
      translateTree(document.body);
      return;
    }
    if (catalogues.has(code)) {
      useCatalogue(code, catalogues.get(code));
      return;
    }
    loadCatalogue(code)
      .then((catalogue) => {
        if (catalogueCode() === code) useCatalogue(code, catalogue);
      })
      .catch(() => {
        // The page stays in English if a catalogue cannot be loaded.
      });
  };

  // The catalogue matcher, for the WebUI tests.
  window.nowlertI18n = { compile, translateText };

  window.nowlertTranslate = (text) => {
    if (!active) return text;
    const target = translateText(normalized(String(text ?? "")), active);
    return target === null ? text : target;
  };

  const regionalOriginalNavigate = navigate;
  navigate = function navigateWithRegionalDraftReset(view, historyMode = "push") {
    const leavingSettings = state.currentView === "settings" && view !== "settings";
    if (leavingSettings) renderPreferences();
    const result = regionalOriginalNavigate(view, historyMode);
    if (view === "settings") renderPreferences();
    regionalNormalizeLanguageLabels();
    applyLanguage();
    return result;
  };

  const regionalOriginalRenderPreferences = renderPreferences;
  renderPreferences = function renderPreferencesWithLanguageLabels() {
    regionalRestoreLanguageAliases();
    const result = regionalOriginalRenderPreferences();
    regionalNormalizeLanguageLabels();
    return result;
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      regionalNormalizeLanguageLabels();
      renderPreferences();
      applyLanguage();
    }, { once: true });
  } else {
    regionalNormalizeLanguageLabels();
    renderPreferences();
    applyLanguage();
  }
})();
