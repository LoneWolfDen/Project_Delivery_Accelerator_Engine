// Repositories with validation and optimistic concurrency, in a real browser (DAT-02).
// Each test uses its own database 'pdae-repo-test' in a fresh browser context.
import { test, expect, openApp } from './helpers.mjs';

test.beforeEach(async ({ page }) => {
  await openApp(page, './?test=1');
  await expect.poll(() => page.evaluate(() => window.__pdaeTest.getState().db !== undefined)).toBe(true);
  await page.evaluate(async () => {
    const { db } = await window.__pdaeTest.openDb({ name: 'pdae-repo-test' });
    const { projectsRepo } = await import('./js/storage/repos/projects.js');
    const { settingsRepo } = await import('./js/storage/repos/settings.js');
    const { withTx } = await import('./js/storage/repos/make-repo.js');
    const { newId } = await import('./js/core/ids.js');
    const { nowIso } = await import('./js/core/time.js');
    const project = (name) => ({ id: newId('prj'), schema: 1, name, status: 'active', createdAt: nowIso(), updatedAt: nowIso() });
    const count = (store) => withTx(db, [store], 'readonly', (tx, request) => request(tx.objectStore(store).count()));
    const codeOf = async (promise) => {
      try {
        await promise;
        return 'resolved';
      } catch (e) {
        return e.code ?? e.name;
      }
    };
    window.__t = { db, projectsRepo, settingsRepo, withTx, project, count, codeOf };
  });
});

test('put then get round-trips a project with defaults; the repo sets updatedAt', async ({ page, problems }) => {
  const r = await page.evaluate(async () => {
    const { db, projectsRepo, project } = window.__t;
    const rec = { ...project('Cloud migration'), updatedAt: '2000-01-01T00:00:00.000Z' };
    const stored = await projectsRepo.put(db, rec);
    return { stored, read: await projectsRepo.get(db, rec.id), missing: await projectsRepo.get(db, 'prj_00000000') };
  });
  expect(r.read).toEqual({ ...r.stored, description: '' });
  expect(r.stored.updatedAt > '2000-01-01T00:00:00.000Z').toBe(true);
  expect(r.missing).toBeUndefined();
  expect(problems).toEqual([]);
});

test('updating with the updatedAt you read succeeds and moves updatedAt forward', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, projectsRepo, project } = window.__t;
    const first = await projectsRepo.put(db, project('A'));
    const second = await projectsRepo.put(db, { ...first, name: 'A renamed' }, { expectUpdatedAt: first.updatedAt });
    return { first, second, read: await projectsRepo.get(db, first.id) };
  });
  expect(r.read.name).toBe('A renamed');
  expect(r.second.updatedAt > r.first.updatedAt).toBe(true);
});

test('a stale expectUpdatedAt rejects with STO-CONFLICT and nothing is overwritten', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, projectsRepo, project, codeOf } = window.__t;
    const v1 = await projectsRepo.put(db, project('Original'));
    // Tab A and tab B both read v1; tab B saves first.
    await projectsRepo.put(db, { ...v1, name: 'Saved by tab B' }, { expectUpdatedAt: v1.updatedAt });
    const staleCode = await codeOf(projectsRepo.put(db, { ...v1, name: 'Saved by tab A' }, { expectUpdatedAt: v1.updatedAt }));
    const noExpectCode = await codeOf(projectsRepo.put(db, { ...v1, name: 'Blind overwrite' }));
    const deletedCode = await codeOf(projectsRepo.put(db, project('Never stored'), { expectUpdatedAt: v1.updatedAt }));
    return { staleCode, noExpectCode, deletedCode, read: await projectsRepo.get(db, v1.id) };
  });
  expect(r.staleCode).toBe('STO-CONFLICT');
  expect(r.noExpectCode).toBe('STO-CONFLICT');
  expect(r.deletedCode).toBe('STO-CONFLICT');
  expect(r.read.name).toBe('Saved by tab B');
});

test('an invalid record is rejected with STO-INVALID and nothing is written', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, projectsRepo, settingsRepo, project, count, codeOf } = window.__t;
    const before = await count('projects');
    let errors = null;
    const badName = await codeOf(projectsRepo.put(db, { ...project('x'), name: '' }).catch((e) => { errors = e.errors; throw e; }));
    const badStatus = await codeOf(projectsRepo.put(db, { ...project('x'), status: 'gone' }));
    const secret = await codeOf(settingsRepo.put(db, { key: 'openrouterApiKey', value: 'sk-or-TESTKEY', schema: 1 }));
    return { before, after: await count('projects'), settings: await count('settings'), badName, badStatus, secret, errors };
  });
  expect(r.badName).toBe('STO-INVALID');
  expect(r.errors).toContain('name is required');
  expect(r.badStatus).toBe('STO-INVALID');
  expect(r.secret).toBe('STO-INVALID');
  expect(r.after).toBe(r.before);
  expect(r.settings).toBe(0);
});

test('list returns all or by index; invalid stored records are skipped and counted', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, projectsRepo, withTx, project } = window.__t;
    await projectsRepo.put(db, project('One'));
    await projectsRepo.put(db, { ...project('Two'), status: 'trashed' });
    // A damaged record written behind the repo's back, as storage corruption would.
    await withTx(db, ['projects'], 'readwrite', (tx) => {
      tx.objectStore('projects').put({ id: 'prj_ffffffff', name: 42 });
    });
    const all = await projectsRepo.list(db);
    const active = await projectsRepo.list(db, 'status', 'active');
    let getCode = 'resolved';
    try {
      await projectsRepo.get(db, 'prj_ffffffff');
    } catch (e) {
      getCode = e.code;
    }
    return { all: all.map((p) => p.name).sort(), invalid: all.invalid, active: active.map((p) => p.name), getCode };
  });
  expect(r.all).toEqual(['One', 'Two']);
  expect(r.invalid).toBe(1);
  expect(r.active).toEqual(['One']);
  expect(r.getCode).toBe('STO-INVALID');
});

test('withTx is all-or-nothing: an error after some writes leaves the store unchanged', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, withTx, project, count, codeOf } = window.__t;
    const code = await codeOf(
      withTx(db, ['projects'], 'readwrite', async (tx, request) => {
        await request(tx.objectStore('projects').put(project('first')));
        await request(tx.objectStore('projects').put(project('second')));
        throw new Error('something failed half-way');
      }),
    );
    return { code, count: await count('projects') };
  });
  expect(r.code).toBe('STO-WRITE-FAIL');
  expect(r.count).toBe(0);
});

test('settings round-trip: one record per setting', async ({ page }) => {
  const r = await page.evaluate(async () => {
    const { db, settingsRepo } = window.__t;
    await settingsRepo.put(db, { key: 'theme', value: 'dark', schema: 1 });
    const t = await settingsRepo.get(db, 'theme');
    await settingsRepo.put(db, { ...t, value: 'light' }, { expectUpdatedAt: t.updatedAt });
    return (await settingsRepo.get(db, 'theme')).value;
  });
  expect(r).toBe('light');
});
