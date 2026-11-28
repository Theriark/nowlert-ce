import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Audit log trend colours follow good news, not the card colour: fewer
// failures is green, fewer successes is red.
const read = name => readFileSync(new URL(`../../src/webui/${name}`, import.meta.url), 'utf8');
function functionSource(file, name, indent = '') {
  const source = read(file);
  const start = source.indexOf(`function ${name}(`);
  assert.notEqual(start, -1, `${name} exists in ${file}`);
  const end = source.indexOf(`\n${indent}}`, start);
  return source.slice(start, end + indent.length + 2);
}

const context = {};
vm.runInNewContext(
  ['trendQuality', 'trendData'].map(name => functionSource('audit_log_refinement.js', name, '  ')).join('\n'),
  context,
);

test('a drop in failures is good and a drop in successes is bad', () => {
  const failed = context.trendData(46, 100);
  const success = context.trendData(93, 100);
  assert.equal(failed.text, '↓ 54%');
  assert.equal(context.trendQuality('failed', failed.tone), 'good');
  assert.equal(success.text, '↓ 7%');
  assert.equal(context.trendQuality('success', success.tone), 'bad');
});

test('a rise in warnings is bad, a rise in successes is good, no change is neutral', () => {
  assert.equal(context.trendQuality('warning', context.trendData(12, 6).tone), 'bad');
  assert.equal(context.trendQuality('success', context.trendData(0, 0).tone), 'neutral');
  assert.equal(context.trendQuality('success', context.trendData(5, 0).tone), 'good');
});

test('the stylesheet colours trends by quality', () => {
  const styles = read('audit_log_refinement.css');
  assert.match(styles, /\.audit-refine-trend\.trend-good strong \{ color: #79e28d; \}/);
  assert.match(styles, /\.audit-refine-trend\.trend-bad strong \{ color: #ff7474; \}/);
  assert.doesNotMatch(styles, /\.audit-refine-trend\.is-success strong/);
});
