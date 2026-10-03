"""Execute the real activity formatter against stored Unix timestamps."""
from pathlib import Path
import subprocess


def test_activity_time_uses_epoch_seconds_and_account_preferences():
    source = (Path(__file__).resolve().parents[1] / 'src/webui/email_alerts.js').read_text(encoding='utf-8')
    formatter = source[source.index('function emailActivityTime('):source.index('\nfunction emailRenderActivityItems(')]
    program = r'''
const assert = require('node:assert/strict');
const state = {preferences: {language: 'en-GB', timezone: 'Europe/Lisbon', time_format: '24'}};
const NativeDate = globalThis.Date;
class Date extends NativeDate {
  constructor(...args) { super(...(args.length ? args : ['2026-10-03T00:10:00Z'])); }
}
''' + formatter + r'''
assert.deepEqual(emailActivityTime(1790970658), {time: '20:50', date: '2 Oct'});
assert.deepEqual(emailActivityTime(1790970658000), emailActivityTime(1790970658));
assert.deepEqual(emailActivityTime('1790970658'), emailActivityTime(1790970658));
assert.deepEqual(emailActivityTime('2026-10-02T19:50:58Z'), emailActivityTime(1790970658));
assert.equal(emailActivityTime('2026-10-02T23:30:00Z').date, 'Today');
state.preferences.timezone = 'America/New_York';
assert.equal(emailActivityTime('2026-10-03T00:05:00Z').date, 'Today');
state.preferences.time_format = '12';
assert.equal(emailActivityTime(1790970658).time, '03:50 pm');
for (const value of [null, undefined, '', 'invalid', Infinity]) {
  assert.deepEqual(emailActivityTime(value), {time: 'Time unavailable', date: ''});
}
assert.equal(emailActivityTime(0).date, '31 Dec 1969');
'''
    result = subprocess.run(['node', '-e', program], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

