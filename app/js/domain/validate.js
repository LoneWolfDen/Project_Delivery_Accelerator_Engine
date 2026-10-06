// Record validators (DAT-02; DATA_AND_STORAGE_ARCHITECTURE.md §3, §9). Pure.
// Each validator returns { ok, errors[], value } where value has read-time defaults applied.
// Schema-evolution rule (V-13): fields added after schema v1 are optional with defaults applied
// here on read, and unknown fields are ignored (kept as-is). Making a field required, renaming it
// or changing its type needs a new migration item with upRecord.

const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/;
const PROJECT_ID_RE = /^prj_[0-9a-f-]{8,64}$/;
const SETTING_KEY_RE = /^[a-zA-Z][a-zA-Z0-9._-]{0,63}$/;
// Secrets are never stored (TARGET_ARCHITECTURE.md §23): refuse setting names that look like one.
const SECRET_KEY_RE = /key|token|secret|password|credential/i;
export const PROJECT_STATUSES = Object.freeze(['active', 'trashed']);
export const NAME_MAX = 200;

function isIso(v) {
  return typeof v === 'string' && ISO_RE.test(v) && !Number.isNaN(Date.parse(v));
}

function isObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function base(record, errors, keyField) {
  if (!isObject(record)) {
    errors.push('record must be an object');
    return false;
  }
  if (keyField === 'id' && typeof record.id !== 'string') errors.push('id is required');
  if (keyField === 'key' && typeof record.key !== 'string') errors.push('key is required');
  if (!Number.isInteger(record.schema) || record.schema < 1) errors.push('schema must be a positive integer');
  if (!isIso(record.updatedAt)) errors.push('updatedAt must be an ISO timestamp');
  return true;
}

function result(errors, value) {
  return errors.length ? { ok: false, errors, value: undefined } : { ok: true, errors: [], value };
}

export function validateProject(record) {
  const errors = [];
  if (!base(record, errors, 'id')) return result(errors);
  if (typeof record.id === 'string' && !PROJECT_ID_RE.test(record.id)) errors.push('id must look like prj_<uuid>');
  if (typeof record.name !== 'string' || record.name.trim() === '') errors.push('name is required');
  else if (record.name.length > NAME_MAX) errors.push(`name must be at most ${NAME_MAX} characters`);
  if (!PROJECT_STATUSES.includes(record.status)) errors.push('status must be active or trashed');
  if (!isIso(record.createdAt)) errors.push('createdAt must be an ISO timestamp');
  if (record.description !== undefined && typeof record.description !== 'string') errors.push('description must be text');
  return result(errors, { description: '', ...record });
}

export function validateSettings(record) {
  const errors = [];
  if (!base(record, errors, 'key')) return result(errors);
  if (typeof record.key === 'string') {
    if (!SETTING_KEY_RE.test(record.key)) errors.push('key must be a short setting name');
    else if (SECRET_KEY_RE.test(record.key)) errors.push('secrets must never be stored in settings');
  }
  if (!('value' in record) || record.value === undefined) errors.push('value is required');
  return result(errors, { ...record });
}

export function validateMeta(record) {
  const errors = [];
  if (!base(record, errors, 'key')) return result(errors);
  if (record.schemaVersion !== undefined && !Number.isInteger(record.schemaVersion)) errors.push('schemaVersion must be an integer');
  for (const f of ['createdByAppVersion', 'lastOpenedAppVersion', 'installId']) {
    if (record[f] !== undefined && typeof record[f] !== 'string') errors.push(`${f} must be text`);
  }
  return result(errors, { ...record });
}
