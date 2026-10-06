// Unit tests for app/js/domain/validate.js, app/js/core/ids.js and app/js/core/time.js (DAT-02).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateProject, validateSettings, validateMeta, NAME_MAX } from '../../app/js/domain/validate.js';
import { newId } from '../../app/js/core/ids.js';
import { nowIso } from '../../app/js/core/time.js';

const T = '2026-10-04T09:12:00.000Z';
const project = (over = {}) => ({ id: 'prj_0a1b2c3d-1111-2222-3333-444455556666', schema: 1, name: 'Migration', status: 'active', createdAt: T, updatedAt: T, ...over });

test('a valid project passes and gets read-time defaults', () => {
  const r = validateProject(project());
  assert.equal(r.ok, true);
  assert.deepEqual(r.errors, []);
  assert.equal(r.value.description, '');
});

test('every record requires id (or key), schema and updatedAt', () => {
  for (const field of ['id', 'schema', 'updatedAt']) {
    const rec = project();
    delete rec[field];
    const r = validateProject(rec);
    assert.equal(r.ok, false, field);
    assert.equal(r.value, undefined);
  }
  assert.equal(validateSettings({ value: 1, schema: 1, updatedAt: T }).ok, false);
  assert.equal(validateMeta({ schema: 1, updatedAt: T }).ok, false);
  assert.equal(validateProject(null).ok, false);
  assert.equal(validateProject(['x']).ok, false);
});

test('project field rules: name, status, id format, timestamps, schema', () => {
  assert.equal(validateProject(project({ name: '  ' })).ok, false);
  assert.equal(validateProject(project({ name: 'x'.repeat(NAME_MAX + 1) })).ok, false);
  assert.equal(validateProject(project({ status: 'deleted' })).ok, false);
  assert.equal(validateProject(project({ id: 'abc' })).ok, false);
  assert.equal(validateProject(project({ updatedAt: 'yesterday' })).ok, false);
  assert.equal(validateProject(project({ createdAt: 12345 })).ok, false);
  assert.equal(validateProject(project({ schema: 0 })).ok, false);
  assert.equal(validateProject(project({ schema: 1.5 })).ok, false);
  assert.equal(validateProject(project({ description: 5 })).ok, false);
});

test('V-13: a v1 record lacking every later optional field validates', () => {
  // `description` stands for fields added after v1: optional, defaulted on read.
  const r = validateProject(project());
  assert.equal('description' in project(), false);
  assert.equal(r.ok, true);
  assert.equal(r.value.description, '');
});

test('V-13: a record with an extra unknown field validates and keeps the field', () => {
  const r = validateProject(project({ addedInV7: { nested: true } }));
  assert.equal(r.ok, true);
  assert.deepEqual(r.value.addedInV7, { nested: true });
  assert.equal(validateSettings({ key: 'theme', value: 'dark', schema: 1, updatedAt: T, futureFlag: 1 }).ok, true);
  assert.equal(validateMeta({ key: 'install', schema: 1, updatedAt: T, somethingNew: 'x' }).ok, true);
});

test('settings refuse names that look like secrets and require a value', () => {
  for (const key of ['openrouterApiKey', 'apiKey', 'token', 'clientSecret', 'password', 'credentials']) {
    const r = validateSettings({ key, value: 'sk-or-TESTKEY', schema: 1, updatedAt: T });
    assert.equal(r.ok, false, key);
    assert.match(r.errors.join(), /secrets/);
  }
  assert.equal(validateSettings({ key: 'theme', schema: 1, updatedAt: T }).ok, false);
  assert.equal(validateSettings({ key: 'bad key!', value: 1, schema: 1, updatedAt: T }).ok, false);
  assert.equal(validateSettings({ key: 'presentationMode', value: false, schema: 1, updatedAt: T }).ok, true);
});

test('meta: the install record from migration 0001 validates; wrong types do not', () => {
  const install = { key: 'install', schema: 1, schemaVersion: 1, createdAt: T, updatedAt: T, createdByAppVersion: '0.1.0', lastOpenedAppVersion: '0.1.0', installId: 'ins_00' };
  assert.equal(validateMeta(install).ok, true);
  assert.equal(validateMeta({ ...install, schemaVersion: '1' }).ok, false);
  assert.equal(validateMeta({ ...install, installId: 7 }).ok, false);
});

test('validators do not mutate their input', () => {
  const rec = Object.freeze(project());
  assert.equal(validateProject(rec).ok, true);
});

test('newId gives <prefix>_<uuid> matching the diagnostics ID pattern; bad prefixes throw', () => {
  const id = newId('prj');
  assert.match(id, /^prj_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  assert.match(id, /^[a-z]+_[0-9a-f-]+$/);
  assert.notEqual(newId('prj'), newId('prj'));
  assert.equal(validateProject(project({ id })).ok, true);
  for (const bad of ['', 'P', 'prj_', 'toolongprefix', 'a b']) assert.throws(() => newId(bad), TypeError, bad);
});

test('nowIso returns an ISO UTC timestamp accepted by validators', () => {
  const t = nowIso();
  assert.match(t, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  assert.equal(validateProject(project({ updatedAt: t, createdAt: t })).ok, true);
});
