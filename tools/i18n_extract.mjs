#!/usr/bin/env node
// List the English interface strings of the WebUI.
//
// Scans src/webui/*.js string and template literals and the text and
// translatable attributes of src/webui/index.html, keeps what reads as
// interface text, and prints the sorted list as JSON. Template literals become
// patterns with {0}, {1}, ... in place of each ${...} expression.
//
//   node tools/i18n_extract.mjs            print the list
//   node tools/i18n_extract.mjs --write    rewrite src/webui/i18n/source.json

import {readFileSync, readdirSync, writeFileSync} from "node:fs";
import {dirname, join} from "node:path";
import {fileURLToPath} from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const WEBUI = join(ROOT, "src", "webui");

// Files that hold no interface text of their own.
const SKIP_FILES = new Set(["i18n.js", "routing_pulse_model.js", "delivery_chart_model.js"]);

export function literals(source) {
  const found = [];
  let index = 0;
  const length = source.length;
  function readQuoted(quote) {
    let text = "";
    index += 1;
    while (index < length && source[index] !== quote) {
      if (source[index] === "\\") {
        const next = source[index + 1];
        text += {n: "\n", t: "\t", r: "", "'": "'", '"': '"', "\\": "\\", "`": "`", $: "$"}[next] ?? next;
        index += 2;
        continue;
      }
      if (source[index] === "\n") return null;
      text += source[index];
      index += 1;
    }
    index += 1;
    return text;
  }
  function readTemplate() {
    let text = "";
    let slot = 0;
    index += 1;
    while (index < length && source[index] !== "`") {
      if (source[index] === "\\") {
        const next = source[index + 1];
        text += {n: "\n", t: "\t", "`": "`", $: "$", "\\": "\\"}[next] ?? next;
        index += 2;
        continue;
      }
      if (source[index] === "$" && source[index + 1] === "{") {
        let depth = 1;
        let inner = "";
        index += 2;
        while (index < length && depth > 0) {
          const char = source[index];
          if (char === "{") depth += 1;
          else if (char === "}") depth -= 1;
          else if (char === "'" || char === '"') {
            const value = readQuoted(char);
            if (value !== null) found.push(value);
            continue;
          } else if (char === "`") {
            const nested = readTemplate();
            if (nested !== null) found.push(nested);
            continue;
          }
          if (depth > 0) inner += char;
          index += 1;
        }
        text += `{${slot}}`;
        slot += 1;
        continue;
      }
      text += source[index];
      index += 1;
    }
    index += 1;
    return text;
  }
  while (index < length) {
    const char = source[index];
    const next = source[index + 1];
    if (char === "/" && next === "/") {
      while (index < length && source[index] !== "\n") index += 1;
      continue;
    }
    if (char === "/" && next === "*") {
      const end = source.indexOf("*/", index + 2);
      index = end < 0 ? length : end + 2;
      continue;
    }
    if (char === "/" && /[=(,:;!&|?{}\[\n]\s*$/.test(source.slice(Math.max(0, index - 20), index))) {
      // Regular expression literal: skip it.
      index += 1;
      let inClass = false;
      while (index < length) {
        const value = source[index];
        if (value === "\\") { index += 2; continue; }
        if (value === "[") inClass = true;
        else if (value === "]") inClass = false;
        else if (value === "/" && !inClass) break;
        else if (value === "\n") break;
        index += 1;
      }
      index += 1;
      continue;
    }
    if (char === "'" || char === '"') {
      const value = readQuoted(char);
      if (value !== null) found.push(value);
      continue;
    }
    if (char === "`") {
      const value = readTemplate();
      if (value !== null) found.push(value);
      continue;
    }
    index += 1;
  }
  return found;
}

const NOT_TEXT = [
  /^\s*$/,
  /^[\w.-]+$/, // identifiers, keys, class names, single words in lower case
  /^[#./\\]/, // selectors, paths
  /^(https?:|mailto:|data:|\/\/)/,
  /[<>]/, // markup
  /^[\[(]|^\{(?!\d+\})/, // code, but not a leading {0} placeholder
  /;\s*$/, /:\s*[^ ]+;/, // CSS
  /^[a-z0-9-]+(\s+[a-z0-9-]+)+$/, // space-separated class lists
  /^[a-z][\w-]*\[/, // attribute selectors
  /^(GET|POST|PUT|PATCH|DELETE)$/,
  /^\{\d+\}$/, // a lone placeholder
  /^[\d\s.,:%{}()+-]+$/, // numbers and placeholders only
  /^[a-z0-9_{}-]+( [a-z0-9_{}-]+)*$/, // class lists, also with placeholders
  /^[a-z][\w-]*(\s*[,>+~]\s*[a-z][\w-]*)+/, // CSS selector lists
  /^[a-z]+ [a-z]+:[a-z-]+/, // "thead th:last-child"
];
// Single capitalised words are interface text ("Dashboard", "Delete").
const SINGLE_WORD = /^[A-Z][a-zA-Z]+$/;
// Counts are interface text even in lower case ("1 destination",
// "{0} of {1} selected"); class lists have more hyphens than words.
const COUNT_PHRASE = /^(\d+|\{\d+\})( of (\d+|\{\d+\}))?( [a-z]+(-[a-z]+)?)+\.?$/;

export function isText(value) {
  const text = value.trim();
  if (text.length < 2 || text.length > 400) return false;
  if (SINGLE_WORD.test(text) || COUNT_PHRASE.test(text)) return true;
  if (NOT_TEXT.some((pattern) => pattern.test(text))) return false;
  if (!/[A-Za-z]{2}/.test(text)) return false;
  // Needs a capital letter or a sentence-like space: "No routes", "Save".
  return /[A-Z]/.test(text) || / [a-z]+ /.test(` ${text} `);
}

function htmlStrings(markup) {
  const found = [];
  const body = markup.replace(/<script[\s\S]*?<\/script>/g, "").replace(/<style[\s\S]*?<\/style>/g, "");
  for (const match of body.matchAll(/>([^<>]+)</g)) found.push(match[1].replace(/\s+/g, " ").trim());
  for (const match of body.matchAll(/\s(?:placeholder|title|aria-label|alt)="([^"]*)"/g)) found.push(match[1]);
  return found.map((value) => value.replace(/&amp;/g, "&").replace(/&nbsp;/g, " ").replace(/&#39;/g, "'").replace(/&quot;/g, '"'));
}

export function extract() {
  const strings = new Set();
  for (const name of readdirSync(WEBUI).sort()) {
    if (!name.endsWith(".js") || SKIP_FILES.has(name)) continue;
    const source = readFileSync(join(WEBUI, name), "utf8")
      .replace(/\/\/ i18n-extract: skip-start[\s\S]*?\/\/ i18n-extract: skip-end/g, "");
    for (const value of literals(source)) {
      // Markup written into innerHTML: its text and attributes are interface text.
      const parts = /<[a-z][^>]*>/i.test(value) ? htmlStrings(value) : [value];
      for (const part of parts) {
        const text = part.replace(/\s+/g, " ").trim();
        if (isText(text)) strings.add(text);
      }
    }
  }
  for (const value of htmlStrings(readFileSync(join(WEBUI, "index.html"), "utf8"))) {
    if (isText(value)) strings.add(value.trim());
  }
  return [...strings].sort((left, right) => left.localeCompare(right, "en"));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const list = extract();
  if (process.argv.includes("--write")) {
    writeFileSync(join(WEBUI, "i18n", "source.json"), `${JSON.stringify(list, null, 1)}\n`);
    console.error(`${list.length} strings written`);
  } else {
    console.log(JSON.stringify(list, null, 1));
  }
}
