import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Development walk finding F6 (THE-875): the Settings update copy must not say
// "up to date" when the GitHub check failed or no version is advertised.
const source = readFileSync(new URL('../../src/webui/enhancements.js', import.meta.url), 'utf8');
const start = source.indexOf('function updateStatusMessage(');
assert.notEqual(start, -1, 'updateStatusMessage exists');
// The function lives inside the enhancements IIFE, so its closing brace is indented.
const end = source.indexOf('\n  }', start) + 4;
const updateStatusMessage = vm.runInNewContext(`${source.slice(start, end)}\nupdateStatusMessage;`);

test('a failed check never claims the installation is up to date', () => {
  const message = updateStatusMessage({running: '3.1.6', available: '', check_error: 'GitHub returned HTTP 403'});
  assert.match(message, /could not be completed/);
  assert.doesNotMatch(message, /up to date/);
});

test('an available update names the version', () => {
  assert.match(updateStatusMessage({running: '3.1.6', available: '3.2.0', update_available: true}), /Version 3\.2\.0 is available/);
});

test('no advertised version explains that nothing newer is advertised', () => {
  const message = updateStatusMessage({running: '3.1.6', available: '', update_available: false});
  assert.match(message, /No newer version is advertised/);
  assert.doesNotMatch(message, /up to date/);
});

test('an advertised version equal to the running one is up to date', () => {
  assert.equal(
    updateStatusMessage({running: '3.1.6', available: '3.1.6', update_available: false}),
    'Nowlert is up to date with the advertised version.',
  );
});
