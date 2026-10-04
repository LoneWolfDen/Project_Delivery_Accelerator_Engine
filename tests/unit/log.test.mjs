// Unit tests for app/js/diagnostics/log.js and errors.js (DGN-01).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createLog, log, getEvents, onEvent, MAX_EVENTS, REF_KEYS } from '../../app/js/diagnostics/log.js';
import { ERRORS, getError, isErrorCode } from '../../app/js/diagnostics/errors.js';

const REQUIRED_CODES = ['STO-OPEN-FAIL', 'STO-QUOTA', 'STO-WRITE-FAIL', 'MIG-FAIL', 'IMP-READ-FAIL', 'IMP-PARSE-FAIL', 'BAK-INVALID', 'AI-NET', 'AI-HTTP', 'APP-UNEXPECTED'];

test('catalogue has every required code with title and help, frozen', () => {
  for (const code of REQUIRED_CODES) {
    assert.ok(isErrorCode(code), code);
    assert.equal(ERRORS[code].code, code);
    assert.ok(ERRORS[code].title.length > 0 && ERRORS[code].help.length > 0, code);
  }
  assert.ok(Object.isFrozen(ERRORS) && Object.isFrozen(ERRORS['STO-QUOTA']));
  assert.equal(getError('NOPE').code, 'APP-UNEXPECTED');
  assert.equal(isErrorCode('toString'), false);
});

test('log has no free-text parameter: signature is (level, code, module, refs)', () => {
  const l = createLog();
  assert.equal(l.log.length, 3); // refs has a default; there is no fifth "message" parameter
  const e = l.log('error', 'STO-QUOTA', 'storage/db', { projectId: 'prj_0a1b', bytes: 1024 }, 'document text here');
  assert.deepEqual(Object.keys(e).sort(), ['code', 'level', 'module', 'refs', 'seq', 'time']);
  assert.ok(!JSON.stringify(l.getEvents()).includes('document text here'));
});

test('refs key `text` (and any key outside the allow-list) is rejected', () => {
  const l = createLog();
  for (const key of ['text', 'message', 'filename', 'prompt', 'key']) {
    assert.throws(() => l.log('error', 'IMP-PARSE-FAIL', 'import', { [key]: 1 }), /not allowed/, key);
  }
  assert.equal(l.getEvents().length, 0);
});

test("refs value 'free text' (or any non-ID string) is rejected; numbers and IDs are accepted", () => {
  const l = createLog();
  for (const value of ['free text', 'Budget.docx', 'prj_XYZ', '', 'sk-or-TESTKEY', NaN, Infinity, null, {}, ['src_1']]) {
    assert.throws(() => l.log('warn', 'IMP-READ-FAIL', 'import', { sourceId: value }), /number or a record ID/, String(value));
  }
  const e = l.log('info', 'IMP-READ-FAIL', 'import', { sourceId: 'src_9f3c-0a', count: 3, status: 404 });
  assert.deepEqual(e.refs, { sourceId: 'src_9f3c-0a', count: 3, status: 404 });
  assert.deepEqual([...REF_KEYS].sort(), ['bytes', 'count', 'itemId', 'projectId', 'reviewId', 'sourceId', 'status']);
});

test('unknown level, unknown code and free-text module are rejected', () => {
  const l = createLog();
  assert.throws(() => l.log('fatal', 'STO-QUOTA', 'storage'), /level/);
  assert.throws(() => l.log('error', 'Disk full!', 'storage'), /code/);
  assert.throws(() => l.log('error', 'STO-QUOTA', 'Could not save Budget.docx'), /module/);
  assert.throws(() => l.log('error', 'STO-QUOTA', 'storage', 'refs as text'), /refs must be an object/);
});

test('buffer is capped at 500 events, oldest dropped first', () => {
  const l = createLog();
  for (let i = 0; i < MAX_EVENTS + 25; i += 1) l.log('debug', 'APP-UNEXPECTED', 'test', { count: i });
  const events = l.getEvents();
  assert.equal(MAX_EVENTS, 500);
  assert.equal(events.length, 500);
  assert.equal(events[0].refs.count, 25);
  assert.equal(events.at(-1).refs.count, 524);
  assert.equal(events.at(-1).seq, 525);
});

test('events are frozen and getEvents returns a copy', () => {
  const l = createLog({ now: () => 1234 });
  l.log('info', 'STO-WRITE-FAIL', 'storage');
  const events = l.getEvents();
  assert.ok(Object.isFrozen(events[0]) && Object.isFrozen(events[0].refs));
  assert.equal(events[0].time, 1234);
  events.pop();
  assert.equal(l.getEvents().length, 1);
});

test('onEvent mirrors each event; a failing listener does not break logging; unsubscribe works', () => {
  const l = createLog();
  const seen = [];
  l.onEvent(() => { throw new Error('mirror down'); });
  const off = l.onEvent((e) => seen.push(e.code));
  l.log('error', 'AI-NET', 'ai');
  off();
  l.log('error', 'AI-HTTP', 'ai', { status: 500 });
  assert.deepEqual(seen, ['AI-NET']);
  assert.equal(l.getEvents().length, 2);
});

test('default app log exposes log/getEvents/onEvent', () => {
  const seen = [];
  const off = onEvent((e) => seen.push(e.code));
  log('warn', 'BAK-INVALID', 'backup');
  off();
  assert.equal(getEvents().at(-1).code, 'BAK-INVALID');
  assert.deepEqual(seen, ['BAK-INVALID']);
});
