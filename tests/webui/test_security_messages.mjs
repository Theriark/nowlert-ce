import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function fn(file, name) {
  const source = read(file);
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists`);
  const end = source.indexOf('\n}', start);
  return source.slice(source.slice(start - 6, start) === 'async ' ? start - 6 : start, end + 2);
}
function context(extra = {}) {
  const source = read('app.js');
  const start = source.indexOf('class APIError extends Error');
  const end = source.indexOf('\nasync function request(', start);
  return vm.createContext({API: '/api', Error, URL, ...extra, securitySource: source.slice(start, end)});
}
function evaluate(ctx, expression) {
  return vm.runInContext(`${ctx.securitySource}\n${expression}`, ctx);
}

test('UI error boundary hides arbitrary exceptions and server failures but retains validation', () => {
  const cases = [
    ["new Error('database password=secret')", 'Try again.'],
    ["{message: 'database password=secret'}", 'Try again.'],
    ["new APIError(500, 'database password=secret', '/private/token')", 'Try again.'],
    ["new APIError(400, 'Filter values must not exceed 256 characters.')", 'Filter values must not exceed 256 characters.'],
    ["new APIError(400, {secret: 'password'})", 'Try again.'],
    ["new APIError(400, 'x'.repeat(2048))", 'Try again.'],
    ["new APIError(400, 'private\\nstack trace')", 'Try again.'],
    ["new APIError(400, 'Invalid password=never-show; token=also-private')", 'Invalid password=<redacted>; token=<redacted>'],
    ["new APIError(400, 'Invalid Bearer private-value')", 'Invalid Bearer <redacted>'],
    ["new APIError(400, 'Invalid https://admin:private@mail.example/')", 'Invalid https://<redacted>@mail.example/'],
  ];
  for (const [error, expected] of cases) {
    assert.equal(evaluate(context(), `uiErrorMessage(${error}, 'Try again.');`), expected);
  }
});

test('quoted credential values redact escaped quotes and unclosed tails while retaining context', () => {
  const cases = [
    ['password="correct horse battery staple" failed', 'password=<redacted> failed'],
    ["token='two words' retry=3", 'token=<redacted> retry=3'],
    ['{"password": "two words", "attempt": 3}', '{"password": <redacted>, "attempt": 3}'],
    [String.raw`password="escaped \"quote\" and tail" retry=3`, 'password=<redacted> retry=3'],
    [String.raw`secret='escaped \'quote\' and tail' retry=3`, 'secret=<redacted> retry=3'],
    ['password="unclosed secret tail', 'password=<redacted>'],
    ['password="unclosed secret tail\\', 'password=<redacted>'],
    ['password="" retry=3', 'password=<redacted> retry=3'],
    ['password=single retry=3', 'password=<redacted> retry=3'],
    ['password must contain 12 characters; retry=3', 'password must contain 12 characters; retry=3'],
  ];
  for (const [message, expected] of cases) {
    assert.equal(evaluate(context(), `uiErrorMessage(new APIError(400, ${JSON.stringify(message)}));`), expected);
  }
});

test('showError preserves public validation feedback and hides internal errors', () => {
  for (const [error, expected] of [
    ["new APIError(400, 'Filter values must not exceed 256 characters.')", 'Filter values must not exceed 256 characters.'],
    ["new Error('private database path')", 'The request could not be completed.'],
  ]) {
    const node = {};
    evaluate(context({byId: () => node}), `${fn('app.js', 'showError')}\nshowError('error', ${error});`);
    assert.equal(node.textContent, expected);
    assert.equal(node.hidden, false);
  }
});

test('API request rejects untrusted error bodies without exposing them and keeps auth codes', async () => {
  for (const status of [400, 500]) {
    const ctx = context({SAFE_METHODS: new Set(['GET']), state: {}, fetch: async () => ({
      status, ok: false, text: async () => JSON.stringify({error: status === 400 ? 'Choose a destination.' : 'password=secret', code: 'mfa_required'}),
    })});
    const message = await evaluate(ctx, `${fn('app.js', 'request')}\nrequest('/destinations').catch(error => { if(error.code !== 'mfa_required') throw Error('auth code lost'); return uiErrorMessage(error, 'Request failed.'); });`);
    assert.equal(message, status === 400 ? 'Choose a destination.' : 'Request failed.');
  }
});

test('mail provider links accept only HTTPS URLs without embedded credentials', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,secret', 'http://mail.example/inbox', 'https://user:secret@mail.example/', '//mail.example/', {}, null]) {
    assert.equal(vm.runInNewContext(`${fn('email_alerts.js', 'emailProviderLink')}\nemailProviderLink(value);`, {URL, value}), '');
  }
  assert.equal(vm.runInNewContext(`${fn('email_alerts.js', 'emailProviderLink')}\nemailProviderLink('https://mail.example/inbox?id=123');`, {URL}), 'https://mail.example/inbox?id=123');
});

test('resource failure summaries retain the affected resource without displaying exception details', () => {
  const ctx = context();
  const result = evaluate(ctx, `resourceErrorMessage({code: 'destination_record_invalid', resource: 'Main destination', message: 'private sqlite path'});`);
  assert.equal(result, 'Destination "Main destination" could not be loaded.');
  assert.equal(evaluate(context(), `resourceErrorMessage({message: 'private sqlite path'});`), 'This resource could not be loaded.');
});

test('local import file validation remains actionable through the same UI boundary', async () => {
  const ctx = context({byId: () => ({files: []})});
  const result = await evaluate(ctx, `${fn('app.js', 'selectedFile')}\nselectedFile('import-file').catch(error => uiErrorMessage(error));`);
  assert.equal(result, 'Choose a file first.');
});
