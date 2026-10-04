// Unit tests for app/js/core/labels.js and app/js/domain/statement.js (CHT-01).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { LABELS, ORIGINS, isLabel, isOrigin } from '../../app/js/core/labels.js';
import {
  makeStatement,
  normaliseWhitespace,
  verifyCitation,
  downgradeUnverified,
} from '../../app/js/domain/statement.js';

const CHUNK = 'The migration must complete before 30 June.\nVendor sign-off   is pending.';
const chunks = new Map([['c1', { text: CHUNK }]]);
const goodCite = { chunkId: 'c1', quote: 'Vendor sign-off is pending.' };

test('LABELS and ORIGINS are frozen with the five labels and four origins', () => {
  assert.deepEqual(Object.values(LABELS).sort(), ['FACT', 'INFERENCE', 'NEEDS_CONFIRMATION', 'NOT_FOUND', 'RECOMMENDATION']);
  assert.deepEqual(Object.values(ORIGINS).sort(), ['copilot-pasted', 'deterministic', 'openrouter', 'user']);
  assert.ok(Object.isFrozen(LABELS) && Object.isFrozen(ORIGINS));
  assert.throws(() => { 'use strict'; LABELS.FACT = 'X'; }, TypeError);
  assert.ok(isLabel('FACT') && !isLabel('fact') && isOrigin('user') && !isOrigin('copilot'));
});

test('FACT without a citation throws', () => {
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.FACT, origin: ORIGINS.DETERMINISTIC }), /FACT needs/);
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.FACT, origin: ORIGINS.DETERMINISTIC, citations: [] }), /FACT needs/);
});

test('FACT with a citation is built and frozen', () => {
  const s = makeStatement({ text: 'Sign-off pending', label: LABELS.FACT, origin: ORIGINS.DETERMINISTIC, citations: [goodCite] });
  assert.equal(s.label, 'FACT');
  assert.deepEqual(s.citations, [goodCite]);
  assert.ok(Object.isFrozen(s) && Object.isFrozen(s.citations) && Object.isFrozen(s.citations[0]));
});

test('unknown label or origin throws', () => {
  assert.throws(() => makeStatement({ text: 'x', label: 'GUESS', origin: ORIGINS.USER }), /unknown label/);
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.RECOMMENDATION, origin: 'copilot' }), /unknown origin/);
});

test('empty text and malformed citations throw', () => {
  assert.throws(() => makeStatement({ text: '  ', label: LABELS.RECOMMENDATION, origin: ORIGINS.USER }), /text/);
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.FACT, origin: ORIGINS.USER, citations: [{ chunkId: 'c1' }] }), /quote/);
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.FACT, origin: ORIGINS.USER, citations: [{ quote: 'q' }] }), /chunkId/);
  assert.throws(() => makeStatement({ text: 'x', label: LABELS.FACT, origin: ORIGINS.USER, citations: 'c1' }), /array/);
  assert.throws(() => makeStatement(), /text/);
});

test('NOT_FOUND requires a scope', () => {
  assert.throws(() => makeStatement({ text: 'No budget found', label: LABELS.NOT_FOUND, origin: ORIGINS.DETERMINISTIC }), /scope/);
  const s = makeStatement({
    text: 'No budget found',
    label: LABELS.NOT_FOUND,
    origin: ORIGINS.DETERMINISTIC,
    scope: { sources: 3, keywords: ['budget'] },
  });
  assert.deepEqual(s.scope, { sources: 3, keywords: ['budget'] });
  assert.ok(Object.isFrozen(s.scope));
});

test('INFERENCE, RECOMMENDATION and NEEDS_CONFIRMATION may have no citations', () => {
  for (const label of [LABELS.INFERENCE, LABELS.RECOMMENDATION, LABELS.NEEDS_CONFIRMATION]) {
    assert.equal(makeStatement({ text: 'x', label, origin: ORIGINS.OPENROUTER }).citations.length, 0);
  }
});

test('normaliseWhitespace collapses spaces, tabs, line breaks and non-breaking spaces', () => {
  assert.equal(normaliseWhitespace('  a\t\tb\r\n c d  '), 'a b c d');
});

test('whitespace variants of a quote verify', () => {
  assert.equal(verifyCitation(CHUNK, 'Vendor sign-off is pending.'), true);
  assert.equal(verifyCitation(CHUNK, 'Vendor\nsign-off is   pending.'), true);
  assert.equal(verifyCitation(CHUNK, '30 June. Vendor'), true); // across the line break
});

test('quotes not in the chunk, changed wording or empty quotes do not verify', () => {
  assert.equal(verifyCitation(CHUNK, 'Vendor sign-off is complete.'), false);
  assert.equal(verifyCitation(CHUNK, 'vendor sign-off is pending.'), false); // case matters: exact match
  assert.equal(verifyCitation(CHUNK, '   '), false);
  assert.equal(verifyCitation(undefined, 'x'), false);
});

test('FACT whose only quote is not in the chunk is downgraded to NEEDS_CONFIRMATION', () => {
  const s = makeStatement({
    text: 'Sign-off done',
    label: LABELS.FACT,
    origin: ORIGINS.OPENROUTER,
    citations: [{ chunkId: 'c1', quote: 'Vendor sign-off is complete.' }],
  });
  const d = downgradeUnverified(s, chunks);
  assert.equal(d.label, LABELS.NEEDS_CONFIRMATION);
  assert.equal(d.citations.length, 0);
  assert.equal(d.droppedCitations, 1);
  assert.equal(s.label, LABELS.FACT, 'original statement is not mutated');
});

test('citation to an unknown chunk is dropped', () => {
  const s = makeStatement({ text: 't', label: LABELS.FACT, origin: ORIGINS.OPENROUTER, citations: [{ chunkId: 'c9', quote: 'Vendor' }] });
  assert.equal(downgradeUnverified(s, { c1: { text: CHUNK } }).label, LABELS.NEEDS_CONFIRMATION);
  // Inherited object keys must not count as chunks.
  const p = makeStatement({ text: 't', label: LABELS.FACT, origin: ORIGINS.OPENROUTER, citations: [{ chunkId: 'toString', quote: 'function' }] });
  assert.equal(downgradeUnverified(p, {}).label, LABELS.NEEDS_CONFIRMATION);
});

test('FACT keeps its label when at least one citation verifies; bad ones are dropped', () => {
  const s = makeStatement({
    text: 't',
    label: LABELS.FACT,
    origin: ORIGINS.COPILOT_PASTED,
    citations: [goodCite, { chunkId: 'c1', quote: 'invented sentence' }],
  });
  const d = downgradeUnverified(s, chunks);
  assert.equal(d.label, LABELS.FACT);
  assert.deepEqual(d.citations, [goodCite]);
  assert.equal(d.droppedCitations, 1);
});

test('fully verified statement is returned unchanged', () => {
  const s = makeStatement({ text: 't', label: LABELS.FACT, origin: ORIGINS.DETERMINISTIC, citations: [goodCite] });
  assert.equal(downgradeUnverified(s, chunks), s);
});

test('INFERENCE with an unverified citation keeps its label and loses the citation', () => {
  const s = makeStatement({ text: 't', label: LABELS.INFERENCE, origin: ORIGINS.OPENROUTER, citations: [{ chunkId: 'c1', quote: 'nope' }] });
  const d = downgradeUnverified(s, chunks);
  assert.equal(d.label, LABELS.INFERENCE);
  assert.equal(d.citations.length, 0);
});

test('modules import nothing outside app/js/core and app/js/domain', () => {
  for (const [file, allowed] of [
    ['app/js/core/labels.js', []],
    ['app/js/domain/statement.js', ['../core/labels.js']],
  ]) {
    const src = fs.readFileSync(new URL(`../../${file}`, import.meta.url), 'utf8');
    const imports = [...src.matchAll(/^\s*import\b[^'"]*['"]([^'"]+)['"]/gm)].map((m) => m[1]);
    assert.deepEqual(imports, allowed, file);
  }
});
