import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), "utf8");
const app = read("app.js");
const titles = app.match(/const VIEW_TITLES = \{[\s\S]*?\n\};/)[0];
const navigate = app.slice(app.indexOf("function navigate(view,"), app.indexOf("\nfunction renderDashboard()"));
const flow = read("routing_flow.js");
const wrapper = flow.slice(flow.indexOf("  const previousNavigate=navigate;"), flow.indexOf("  const previousExpire=expireSession;"));
const languageSelect = read("index.html").match(/<select id="preference-language">([\s\S]*?)<\/select>/)[1];
const languages = [...languageSelect.matchAll(/value="([^"]+)"/g)].map(match => match[1]);

for (const regionalFirst of [true, false]) {
  test(`page title survives translation after view render; regional wrapper first=${regionalFirst}`, () => {
    const title = { textContent: "Destinations", dataset: { i18nSource: "Destinations" }, children: [], tagName: "H1", closest: () => null };
    const element = { classList: { remove() {} }, setAttribute() {}, focus() {} };
    const context = vm.createContext({
      title, URL, CustomEvent: class {},
      state: { currentView: "destinations", user: {}, preferences: { language: "en-GB" } },
      byId: id => id === "page-title" ? title : id === "preference-language" ? null : element,
      document: { readyState: "loading", documentElement: {}, addEventListener() {}, dispatchEvent() {}, querySelectorAll: selector => selector === "body *" ? [title] : [] },
      window: { location: { href: "https://example.test/#destinations", hash: "#destinations" }, history: { state: {}, replaceState() {}, pushState() {} } },
      isAdmin: () => true, closeProfileMenu() {}, renderPreferences() {}, queueMicrotask() {},
      PT_TRANSLATIONS: {}, applyLanguage() {}, sync() {}, PAGE: "routing-flow",
    });
    // Real view rendering can run translation before navigate assigns its new title.
    vm.runInContext(`${titles}\nVIEW_TITLES["routing-flow"]="Routing Flow";\n${navigate}\nfunction renderCurrentView(){ applyLanguage(); }`, context);
    for (const script of regionalFirst ? [read("i18n.js"), wrapper] : [wrapper, read("i18n.js")]) vm.runInContext(script, context);
    const views = vm.runInContext("Object.keys(VIEW_TITLES)", context);
    for (const language of languages) {
      context.state.preferences.language = language;
      for (const view of ["destinations", "routing-flow", ...views, "routing-flow"]) {
        context.navigate(view, "none");
        const expected = vm.runInContext(`VIEW_TITLES[${JSON.stringify(view)}]`, context);
        assert.equal(title.dataset.i18nSource, expected, `${language}/${view}: stale translation source`);
        const settled = title.textContent;
        context.applyLanguage();
        context.applyLanguage();
        assert.equal(title.textContent, settled, `${language}/${view}: delayed translation changed the title`);
        if (view === "routing-flow") assert.equal(title.textContent, "Routing Flow");
      }
    }
  });
}
