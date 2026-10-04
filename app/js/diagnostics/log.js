// Content-free diagnostics log (DGN-01; TARGET_ARCHITECTURE.md §22).
// log(level, code, module, refs) has no free-text parameter: the readable text comes from the
// error catalogue by code, and refs may only hold allow-listed keys with numbers or record IDs.
// So document text, prompts, file names or keys cannot be logged by construction.
import { isErrorCode } from './errors.js';

export const MAX_EVENTS = 500;
export const LEVELS = Object.freeze(['debug', 'info', 'warn', 'error']);
export const REF_KEYS = Object.freeze(['projectId', 'sourceId', 'itemId', 'reviewId', 'count', 'bytes', 'status']);
const ID_RE = /^[a-z]+_[0-9a-f-]+$/;
const MODULE_RE = /^[a-z][a-z0-9/-]{0,63}$/;

function checkRefs(refs) {
  if (refs === null || typeof refs !== 'object' || Array.isArray(refs)) throw new TypeError('refs must be an object');
  const out = {};
  for (const [key, value] of Object.entries(refs)) {
    if (!REF_KEYS.includes(key)) throw new TypeError(`refs key not allowed: ${key}`);
    const ok = (typeof value === 'number' && Number.isFinite(value)) || (typeof value === 'string' && ID_RE.test(value));
    if (!ok) throw new TypeError(`refs.${key} must be a number or a record ID`);
    out[key] = value;
  }
  return Object.freeze(out);
}

export function createLog({ max = MAX_EVENTS, now = () => Date.now() } = {}) {
  const events = [];
  const listeners = new Set();
  let seq = 0;

  return {
    log(level, code, module, refs = {}) {
      if (!LEVELS.includes(level)) throw new TypeError(`unknown level: ${String(level)}`);
      if (!isErrorCode(code)) throw new TypeError(`unknown error code: ${String(code)}`);
      if (typeof module !== 'string' || !MODULE_RE.test(module)) throw new TypeError('module must be a short module name');
      seq += 1;
      const event = Object.freeze({ seq, time: now(), level, code, module, refs: checkRefs(refs) });
      events.push(event);
      if (events.length > max) events.splice(0, events.length - max);
      for (const fn of [...listeners]) {
        try {
          fn(event);
        } catch {
          // A failing mirror (e.g. storage) must never break logging.
        }
      }
      return event;
    },
    getEvents() {
      return events.slice();
    },
    // Hook for mirroring events (DAT-03 persists them). Returns an unsubscribe function.
    onEvent(fn) {
      if (typeof fn !== 'function') throw new TypeError('listener must be a function');
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
  };
}

const appLog = createLog();

export const log = (level, code, module, refs) => appLog.log(level, code, module, refs);
export const getEvents = () => appLog.getEvents();
export const onEvent = (fn) => appLog.onEvent(fn);
