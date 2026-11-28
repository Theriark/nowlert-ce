import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Scheduled backups show Day of week only for a weekly schedule and Day of
// month only for a monthly one.
const source = readFileSync(new URL('../../src/webui/app.js', import.meta.url), 'utf8');
const start = source.indexOf('function syncBackupScheduleFields(');
const code = source.slice(start, source.indexOf('\n}', start) + 2);

function scheduleContext(schedule) {
  const weekdayLabel = {hidden: false};
  const dayLabel = {hidden: false};
  const nodes = {
    'backup-schedule': {value: schedule},
    'backup-weekday': {closest: () => weekdayLabel},
    'backup-day': {closest: () => dayLabel},
  };
  const context = {byId: id => nodes[id] || null};
  vm.runInNewContext(code, context);
  context.syncBackupScheduleFields();
  return {weekday: weekdayLabel.hidden, day: dayLabel.hidden};
}

test('each schedule shows only the fields that apply to it', () => {
  assert.deepEqual(scheduleContext('weekly'), {weekday: false, day: true});
  assert.deepEqual(scheduleContext('monthly'), {weekday: true, day: false});
  assert.deepEqual(scheduleContext('daily'), {weekday: true, day: true});
  assert.deepEqual(scheduleContext('disabled'), {weekday: true, day: true});
});
