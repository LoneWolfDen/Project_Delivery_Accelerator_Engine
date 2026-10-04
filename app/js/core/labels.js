// Statement labels and origins (CHT-01, ADR-008; DATA_AND_STORAGE_ARCHITECTURE.md §2).
// Every statement shown to a user carries exactly one label and one origin.

export const LABELS = Object.freeze({
  FACT: 'FACT', // quoted from a stored source, with citation
  INFERENCE: 'INFERENCE', // derived; cites its basis where possible
  RECOMMENDATION: 'RECOMMENDATION',
  NOT_FOUND: 'NOT_FOUND', // searched and absent, with scope
  NEEDS_CONFIRMATION: 'NEEDS_CONFIRMATION',
});

export const ORIGINS = Object.freeze({
  DETERMINISTIC: 'deterministic',
  OPENROUTER: 'openrouter',
  COPILOT_PASTED: 'copilot-pasted',
  USER: 'user',
});

const LABEL_VALUES = new Set(Object.values(LABELS));
const ORIGIN_VALUES = new Set(Object.values(ORIGINS));

export function isLabel(value) {
  return LABEL_VALUES.has(value);
}

export function isOrigin(value) {
  return ORIGIN_VALUES.has(value);
}
