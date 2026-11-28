import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

import {extract} from "../../tools/i18n_extract.mjs";
import {catalogueProblems, offeredCatalogues, readSource} from "../../tools/i18n_check.mjs";

const webui = (name) => new URL(`../../src/webui/${name}`, import.meta.url);
const engineSource = readFileSync(webui("i18n.js"), "utf8");
const source = readSource();
const catalogue = (code) => JSON.parse(readFileSync(webui(`i18n/${code}.json`), "utf8"));

test("the source list holds every English interface string of the scripts and the page", () => {
  // A new English string in a script or in index.html that is not in
  // source.json (and so not in the catalogues) fails here. Regenerate with
  // node tools/i18n_extract.mjs --write and translate it in every catalogue.
  const current = extract();
  const listed = new Set(source);
  const known = new Set(current);
  assert.deepEqual(current.filter((text) => !listed.has(text)), [], "strings missing from source.json");
  assert.deepEqual(source.filter((text) => !known.has(text)), [], "strings in source.json that the WebUI no longer has");
});

test("every language the picker offers has a complete catalogue", () => {
  const offered = offeredCatalogues();
  assert.equal(offered.length, 19);
  const engineCodes = [...engineSource.split("const CATALOGUE_CODES", 2)[1].split("]);", 1)[0].matchAll(/"([a-z]{2})"/g)]
    .map((match) => match[1])
    .sort();
  assert.deepEqual(engineCodes, offered);
  for (const code of offered) {
    assert.deepEqual(catalogueProblems(source, catalogue(code)), [], `${code}.json`);
  }
});

test("the checker reports a missing key and a changed placeholder", () => {
  const sample = ["Save", "User {0} created."];
  assert.deepEqual(catalogueProblems(sample, {Save: "Guardar", "User {0} created.": "Utilizador {0} criado."}), []);
  assert.deepEqual(catalogueProblems(sample, {Save: "Guardar"}), ["missing: User {0} created."]);
  assert.deepEqual(
    catalogueProblems(sample, {Save: "Guardar", "User {0} created.": "Utilizador criado."}),
    ["placeholders differ: User {0} created. -> Utilizador criado."],
  );
});

function engine() {
  const window = {};
  const context = vm.createContext({
    window,
    state: {preferences: {language: "en-GB"}},
    byId: () => null,
    navigate() {},
    renderPreferences() {},
    applyLanguage() {},
    document: {readyState: "loading", documentElement: {}, addEventListener() {}},
  });
  vm.runInContext(engineSource, context);
  return window.nowlertI18n;
}

test("catalogue patterns keep names and numbers and translate known parts", () => {
  const {compile, translateText} = engine();
  const compiled = compile(catalogue("pt"));
  const pt = catalogue("pt");
  assert.equal(translateText("Dashboard", compiled), pt.Dashboard);
  assert.equal(translateText("Enabled · 1 active route", compiled), pt["Enabled · 1 active route"]);
  assert.equal(
    translateText("Page 2 of 7 · 140 items", compiled),
    pt["Page {0} of {1} · {2} items"].replace("{0}", "2").replace("{1}", "7").replace("{2}", "140"),
  );
  // Text that is not an interface string (a name, user data) stays as it is.
  assert.equal(translateText("ops-alerts-primary", compiled), null);
  // A pattern made only of placeholders never matches arbitrary text.
  assert.equal(compile({"{0} {1}": "{1} {0}"}).patterns.length, 0);
});
