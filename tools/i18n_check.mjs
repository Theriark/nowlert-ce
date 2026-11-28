#!/usr/bin/env node
// Check the WebUI translation catalogues against the English source list.
//
//   node tools/i18n_check.mjs                  check every offered locale
//   node tools/i18n_check.mjs pt               check one catalogue
//   node tools/i18n_check.mjs --file X.json    check one catalogue file
//
// A catalogue must translate every source string, add no other key, keep
// every {0}, {1}, ... placeholder of the source exactly, and give a non-empty
// value. Exit status 1 lists the problems.

import {readFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const WEBUI = join(ROOT, "src", "webui");

export function offeredCatalogues() {
  const markup = readFileSync(join(WEBUI, "index.html"), "utf8");
  const select = markup.slice(markup.indexOf('id="preference-language"'));
  const values = [...select.slice(0, select.indexOf("</select>")).matchAll(/value="([a-z]{2})-[A-Z]{2}"/g)]
    .map((match) => match[1]);
  return [...new Set(values)].filter((code) => code !== "en").sort();
}

const placeholders = (text) => (String(text).match(/\{\d+\}/g) || []).sort().join(",");

export function catalogueProblems(source, catalogue) {
  const problems = [];
  if (!catalogue || typeof catalogue !== "object" || Array.isArray(catalogue)) return ["not a JSON object"];
  for (const key of source) {
    if (!Object.hasOwn(catalogue, key)) {
      problems.push(`missing: ${key}`);
      continue;
    }
    const value = catalogue[key];
    if (typeof value !== "string" || !value.trim()) problems.push(`empty: ${key}`);
    else if (placeholders(value) !== placeholders(key)) problems.push(`placeholders differ: ${key} -> ${value}`);
  }
  const known = new Set(source);
  for (const key of Object.keys(catalogue)) if (!known.has(key)) problems.push(`not in source: ${key}`);
  return problems;
}

export function readSource() {
  return JSON.parse(readFileSync(join(WEBUI, "i18n", "source.json"), "utf8"));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const source = readSource();
  const args = process.argv.slice(2);
  const targets = args[0] === "--file"
    ? [[args[1], args[1]]]
    : (args.length ? args : offeredCatalogues()).map((code) => [code, join(WEBUI, "i18n", `${code}.json`)]);
  let failed = false;
  for (const [label, file] of targets) {
    let problems;
    try {
      problems = catalogueProblems(source, JSON.parse(readFileSync(file, "utf8")));
    } catch (error) {
      problems = [`unreadable: ${error.message}`];
    }
    if (problems.length) {
      failed = true;
      console.log(`${label}: ${problems.length} problem(s)`);
      for (const problem of problems.slice(0, 50)) console.log(`  ${problem}`);
    } else {
      console.log(`${label}: ok (${source.length} strings)`);
    }
  }
  process.exit(failed ? 1 : 0);
}
