// Statement with label, origin and verifiable citations (CHT-01, ADR-008;
// COPILOT_AND_CHAT_ARCHITECTURE.md §1, §5). Pure: no DOM, no storage.
// A FACT without a citation cannot be constructed; citations whose quote is not
// in the cited chunk are dropped by downgradeUnverified, and a FACT left without
// citations becomes NEEDS_CONFIRMATION.
import { LABELS, isLabel, isOrigin } from '../core/labels.js';

// Collapse every run of whitespace (including non-breaking spaces and line breaks) to one space, and trim.
export function normaliseWhitespace(s) {
  return String(s).replace(/\s+/g, ' ').trim();
}

// True when `quote` occurs in `chunkText` exactly, after whitespace normalisation of both.
export function verifyCitation(chunkText, quote) {
  if (typeof chunkText !== 'string' || typeof quote !== 'string') return false;
  const q = normaliseWhitespace(quote);
  if (q === '') return false;
  return normaliseWhitespace(chunkText).includes(q);
}

function isNonEmptyString(v) {
  return typeof v === 'string' && v.trim() !== '';
}

function makeCitation(c, i) {
  if (!c || typeof c !== 'object') throw new TypeError(`citation ${i} must be an object`);
  if (!isNonEmptyString(c.chunkId)) throw new TypeError(`citation ${i} needs a chunkId`);
  if (!isNonEmptyString(c.quote)) throw new TypeError(`citation ${i} needs a quote`);
  return Object.freeze({ chunkId: c.chunkId, quote: c.quote });
}

// Build an immutable statement. Throws on unknown label or origin, on FACT with no
// citations, and on NOT_FOUND without a scope (what was searched).
export function makeStatement({ text, label, origin, citations = [], scope } = {}) {
  if (!isNonEmptyString(text)) throw new TypeError('statement text must be a non-empty string');
  if (!isLabel(label)) throw new TypeError(`unknown label: ${String(label)}`);
  if (!isOrigin(origin)) throw new TypeError(`unknown origin: ${String(origin)}`);
  if (!Array.isArray(citations)) throw new TypeError('citations must be an array');
  const cites = Object.freeze(citations.map(makeCitation));
  if (label === LABELS.FACT && cites.length === 0) {
    throw new TypeError('a FACT needs at least one citation');
  }
  if (label === LABELS.NOT_FOUND && (!scope || typeof scope !== 'object')) {
    throw new TypeError('a NOT_FOUND statement needs a scope describing what was searched');
  }
  const statement = { text, label, origin, citations: cites };
  if (scope !== undefined) statement.scope = Object.freeze({ ...scope });
  return Object.freeze(statement);
}

function chunkTextOf(chunksById, chunkId) {
  if (chunksById instanceof Map) return chunksById.get(chunkId)?.text;
  if (chunksById && Object.prototype.hasOwnProperty.call(chunksById, chunkId)) return chunksById[chunkId]?.text;
  return undefined;
}

// Return a statement keeping only citations whose quote is found in the cited chunk.
// `chunksById` is a Map or plain object of chunkId → {text}. Dropped citations are counted
// in `droppedCitations`. A FACT with no remaining citation becomes NEEDS_CONFIRMATION.
export function downgradeUnverified(statement, chunksById) {
  const kept = statement.citations.filter((c) => verifyCitation(chunkTextOf(chunksById, c.chunkId), c.quote));
  const dropped = statement.citations.length - kept.length;
  if (dropped === 0) return statement;
  const label = statement.label === LABELS.FACT && kept.length === 0 ? LABELS.NEEDS_CONFIRMATION : statement.label;
  const next = makeStatement({ ...statement, label, citations: kept });
  return Object.freeze({ ...next, droppedCitations: dropped });
}
