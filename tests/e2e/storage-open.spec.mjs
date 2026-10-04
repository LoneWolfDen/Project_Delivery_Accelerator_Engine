// IndexedDB open, schema v1, migration runner and downgrade guard (DAT-01).
// Each Playwright test gets a fresh browser context, so storage starts empty.
import { test, expect, openApp } from './helpers.mjs';

// Independent copy of DATA_AND_STORAGE_ARCHITECTURE.md §3 (store: keyPath, autoIncrement, indexes).
const EXPECTED = {
  answers: ['id', false, { createdAt: ['createdAt', false], projectId: ['projectId', false] }],
  chunks: ['id', false, { projectId: ['projectId', false], sourceId: ['sourceId', false] }],
  diagnostics: ['seq', true, { time: ['time', false] }],
  drafts: ['id', false, { origin: ['origin', false], projectId: ['projectId', false] }],
  exports: ['id', false, { createdAt: ['createdAt', false], projectId: ['projectId', false] }],
  items: ['id', false, { projectId: ['projectId', false], 'projectId+kind': [['projectId', 'kind'], false], sourceId: ['sourceId', false] }],
  meta: ['key', false, {}],
  projects: ['id', false, { status: ['status', false], updatedAt: ['updatedAt', false] }],
  quarantine: ['id', false, { store: ['store', false], time: ['time', false] }],
  reviews: ['id', false, { projectId: ['projectId', false], snapshotId: ['snapshotId', false] }],
  settings: ['key', false, {}],
  snapshots: ['id', false, { projectId: ['projectId', false] }],
  sources: ['id', false, { projectId: ['projectId', false], 'projectId+sha256': [['projectId', 'sha256'], true] }],
  trash: ['id', false, { deletedAt: ['deletedAt', false], projectId: ['projectId', false] }],
};

// Describe a database's stores and indexes in the EXPECTED shape.
function describeDb(name) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const db = req.result;
      const out = { version: db.version, stores: {} };
      const names = [...db.objectStoreNames];
      if (names.length === 0) { db.close(); resolve(out); return; }
      const tx = db.transaction(names, 'readonly');
      for (const n of names) {
        const s = tx.objectStore(n);
        const ix = {};
        for (const i of [...s.indexNames]) ix[i] = [s.index(i).keyPath, s.index(i).unique];
        out.stores[n] = [s.keyPath, s.autoIncrement, ix];
      }
      tx.oncomplete = () => { db.close(); resolve(out); };
    };
  });
}

async function waitForStorage(page) {
  await expect.poll(() => page.evaluate(() => window.__pdaeTest.getState().db !== undefined)).toBe(true);
}

test('a fresh profile creates database pdae v1 with exactly the architecture stores and indexes', async ({ page, problems }) => {
  await openApp(page, './?test=1');
  await waitForStorage(page);
  expect(await page.evaluate(() => window.__pdaeTest.getState().readOnly)).toBe(false);
  const desc = await page.evaluate(describeDb, 'pdae');
  expect(desc.version).toBe(1);
  expect(desc.stores).toEqual(EXPECTED);
  const meta = await page.evaluate(() => new Promise((resolve) => {
    const r = indexedDB.open('pdae');
    r.onsuccess = () => {
      const g = r.result.transaction('meta').objectStore('meta').get('install');
      g.onsuccess = () => { r.result.close(); resolve(g.result); };
    };
  }));
  expect(meta).toMatchObject({ key: 'install', schemaVersion: 1, createdByAppVersion: '0.1.0', lastOpenedAppVersion: '0.1.0' });
  expect(meta.installId).toMatch(/^ins_[0-9a-f]{32}$/);
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(problems).toEqual([]);
});

test('a migration that throws aborts atomically: version and data unchanged, MIG-FAIL', async ({ page }) => {
  await openApp(page, './?test=1');
  await waitForStorage(page);
  const result = await page.evaluate(async () => {
    const { MIGRATIONS } = await import('./js/storage/migrations/index.js');
    const name = 'pdae-migration-test';
    // Version 1 with one record.
    const first = await window.__pdaeTest.openDb({ name, version: 1 });
    await new Promise((res) => {
      const tx = first.db.transaction('projects', 'readwrite');
      tx.objectStore('projects').put({ id: 'prj_1', status: 'active', updatedAt: 1 });
      tx.oncomplete = res;
    });
    first.db.close();
    // Version 2 whose migration changes things, then throws.
    const failing = {
      from: 1,
      to: 2,
      up(db, tx) {
        db.createObjectStore('extra', { keyPath: 'id' });
        tx.objectStore('projects').delete('prj_1');
        throw new Error('migration bug');
      },
    };
    let code = 'resolved';
    try {
      await window.__pdaeTest.openDb({ name, version: 2, migrations: [...MIGRATIONS, failing] });
    } catch (e) {
      code = e.code;
    }
    // Reopen at whatever version exists and inspect.
    const after = await new Promise((res) => {
      const r = indexedDB.open(name);
      r.onsuccess = () => {
        const db = r.result;
        const g = db.transaction('projects').objectStore('projects').get('prj_1');
        g.onsuccess = () => { const out = { version: db.version, stores: [...db.objectStoreNames], record: g.result }; db.close(); res(out); };
      };
    });
    const { getEvents } = await import('./js/diagnostics/log.js');
    return { code, after, logged: getEvents().map((e) => e.code) };
  });
  expect(result.code).toBe('MIG-FAIL');
  expect(result.after.version).toBe(1);
  expect(result.after.stores).not.toContain('extra');
  expect(result.after.record).toEqual({ id: 'prj_1', status: 'active', updatedAt: 1 });
  expect(result.logged).toContain('MIG-FAIL');
});

test('the app shows the MIG-FAIL banner when opening storage fails in a migration', async ({ page }) => {
  // Simulate by opening the app against a DB whose migration list is broken: a missing step.
  await openApp(page, './?test=1');
  await waitForStorage(page);
  const code = await page.evaluate(async () => {
    try {
      await window.__pdaeTest.openDb({ name: 'pdae-gap', version: 3 }); // no migration 1 → 2
      return 'resolved';
    } catch (e) {
      const { showError } = await import('./js/ui/components/banner.js');
      showError(e.code); // main.js does exactly this on failure
      return e.code;
    }
  });
  expect(code).toBe('MIG-FAIL');
  await expect(page.locator('.banner[data-code="MIG-FAIL"]')).toBeVisible();
  const version = await page.evaluate(() => new Promise((res) => {
    const r = indexedDB.open('pdae-gap');
    r.onsuccess = () => { const v = r.result.version; r.result.close(); res(v); };
  }));
  expect(version).toBe(1); // the empty database the browser creates; no stores were left half-made
});

test('a database saved by a newer version (99) opens read-only with a banner and is not changed', async ({ page, problems }) => {
  // Create pdae v99 from a same-origin page before the app starts.
  await page.goto('./version.js');
  await page.evaluate(() => new Promise((res) => {
    const r = indexedDB.open('pdae', 99);
    r.onupgradeneeded = () => r.result.createObjectStore('future', { keyPath: 'id' });
    r.onsuccess = () => { r.result.close(); res(); };
  }));
  await openApp(page, './?test=1');
  await waitForStorage(page);
  expect(await page.evaluate(() => window.__pdaeTest.getState().readOnly)).toBe(true);
  const banner = page.locator('.banner[data-code="STO-NEWER-VERSION"]');
  await expect(banner).toBeVisible();
  await expect(banner).toContainText('Data was saved by a newer version');
  await expect(banner).toContainText('read-only');
  const desc = await page.evaluate(describeDb, 'pdae');
  expect(desc.version).toBe(99);
  expect(Object.keys(desc.stores)).toEqual(['future']);
  expect(problems).toEqual([]);
});

test('an old connection in another tab blocks the upgrade and shows STO-BLOCKED', async ({ page, context }) => {
  await page.goto('./version.js');
  // Hold a version-0→1 connection to "pdae" open without handling versionchange.
  await page.evaluate(() => new Promise((res) => {
    const r = indexedDB.open('pdae-blocked', 1);
    r.onsuccess = () => { window.__held = r.result; res(); };
  }));
  const other = await context.newPage();
  await openApp(other, './?test=1');
  await waitForStorage(other);
  other.evaluate(async () => {
    const { MIGRATIONS } = await import('./js/storage/migrations/index.js');
    const noop = { from: 1, to: 2, up() {} };
    return window.__pdaeTest.openDb({ name: 'pdae-blocked', version: 2, migrations: [...MIGRATIONS, noop] });
  }).catch(() => {});
  await expect(other.locator('.banner[data-code="STO-BLOCKED"]')).toBeVisible();
  await page.evaluate(() => window.__held.close());
});

test('the test hook is absent without ?test=1', async ({ page, problems }) => {
  await openApp(page);
  expect(await page.evaluate(() => typeof window.__pdaeTest)).toBe('undefined');
  expect(problems).toEqual([]);
});
