import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// The application reports 27.0.0, the version of the first public release.
// The Settings update check must not announce that same release as an update.
const source = readFileSync(new URL('../../src/webui/enhancements.js', import.meta.url), 'utf8');

function extract(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists`);
  // The functions live inside the enhancements IIFE, so their closing brace is indented.
  const end = source.indexOf('\n  }', start) + 4;
  return source.slice(start, end);
}

const newerVersion = vm.runInNewContext(
  `${extract('normaliseVersion')}\n${extract('versionKey')}\n${extract('newerVersion')}\nnewerVersion;`,
);

test('the running 27.0.0 release is not offered as its own update', () => {
  assert.equal(newerVersion('v27.0.0', '27.0.0'), false);
  assert.equal(newerVersion('27.0.0', '27.0.0'), false);
});

test('a later 27.x release is offered as an update', () => {
  assert.equal(newerVersion('v27.0.1', '27.0.0'), true);
  assert.equal(newerVersion('v27.1.0', '27.0.0'), true);
});

test('an older or invalid advertised version is never an update', () => {
  assert.equal(newerVersion('v3.1.6', '27.0.0'), false);
  assert.equal(newerVersion('latest', '27.0.0'), false);
  assert.equal(newerVersion('v27.0.0-rc.25', '27.0.0'), false);
});
