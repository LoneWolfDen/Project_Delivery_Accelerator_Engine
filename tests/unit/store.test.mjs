// Unit tests for app/js/ui/store.js (UI-02).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createStore, getState, update, subscribe } from '../../app/js/ui/store.js';

test('getState returns the initial state, frozen', () => {
  const s = createStore({ a: 1 });
  assert.deepEqual(s.getState(), { a: 1 });
  assert.ok(Object.isFrozen(s.getState()));
});

test('update shallow-merges into a new frozen state without mutating the old one', () => {
  const s = createStore({ a: 1, b: 2 });
  const before = s.getState();
  const after = s.update({ b: 3, c: 4 });
  assert.deepEqual(after, { a: 1, b: 3, c: 4 });
  assert.deepEqual(before, { a: 1, b: 2 });
  assert.notEqual(after, before);
  assert.ok(Object.isFrozen(after));
  assert.equal(s.getState(), after);
});

test('subscribers receive (state, previous) on every update', () => {
  const s = createStore({ n: 0 });
  const calls = [];
  s.subscribe((state, prev) => calls.push([state.n, prev.n]));
  s.update({ n: 1 });
  s.update({ n: 2 });
  assert.deepEqual(calls, [[1, 0], [2, 1]]);
});

test('unsubscribe stops notifications', () => {
  const s = createStore();
  let count = 0;
  const off = s.subscribe(() => { count += 1; });
  s.update({ x: 1 });
  off();
  s.update({ x: 2 });
  assert.equal(count, 1);
});

test('a throwing subscriber does not stop the others; its error is re-thrown after', () => {
  const s = createStore();
  let reached = false;
  s.subscribe(() => { throw new Error('boom'); });
  s.subscribe(() => { reached = true; });
  assert.throws(() => s.update({ x: 1 }), /boom/);
  assert.equal(reached, true);
  assert.deepEqual(s.getState(), { x: 1 });
});

test('subscribe rejects non-functions', () => {
  assert.throws(() => createStore().subscribe('x'), TypeError);
});

test('default app store exposes getState/update/subscribe with an initial null route', () => {
  assert.deepEqual(getState(), { route: null });
  const seen = [];
  const off = subscribe((s) => seen.push(s.route));
  update({ route: { name: 'help', params: {} } });
  off();
  assert.deepEqual(seen, [{ name: 'help', params: {} }]);
});
