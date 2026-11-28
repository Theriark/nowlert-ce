import test from "node:test";
import assert from "node:assert/strict";
import {existsSync, readFileSync} from "node:fs";

// After each Development deploy, CI checks that the served scripts contain
// exact snippets (require_contains / require_not_contains). A code change that
// rewrites such a snippet passes the PR checks and then fails the deploy, so
// every snippet is checked against the repository scripts here.
const root = new URL("../../", import.meta.url);
const ci = readFileSync(new URL(".github/workflows/ci.yml", root), "utf8").replace(/\r\n/g, "\n");

test("every live bundle snippet matches the repository script it names", () => {
  const files = {};
  const download = /(\w+)="\$\(\s*\n\s*curl[^\n]*\n(?:[^\n]*\n){0,3}?\s*"\$\{BASE_URL\}\/ui\/([\w.-]+\.(?:js|css))(?:\?[^"]*)?"/g;
  for (const match of ci.matchAll(download)) files[match[1]] = match[2];
  const problems = [];
  let checked = 0;
  for (const line of ci.split("\n")) {
    const match = line.match(/require_(not_)?contains "([^"]+)" (?:'([^']*)'|"((?:[^"\\]|\\.)*)") "\$\{(\w+)\}"/);
    if (!match || !files[match[5]]) continue;
    const [, negated, label, single, double, variable] = match;
    const needle = single ?? double.replace(/\\(.)/g, "$1");
    const path = new URL(`src/webui/${files[variable]}`, root);
    assert.ok(existsSync(path), `${files[variable]} exists`);
    const present = readFileSync(path, "utf8").replace(/\r\n/g, "\n").includes(needle);
    checked += 1;
    if (Boolean(negated) === present) problems.push(`${label}: ${needle} (${files[variable]})`);
  }
  assert.ok(checked > 20, `found ${checked} snippets`);
  assert.deepEqual(problems, []);
});
