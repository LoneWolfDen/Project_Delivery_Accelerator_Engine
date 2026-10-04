// Open the IndexedDB database and run migrations (DAT-01; DATA_AND_STORAGE_ARCHITECTURE.md §7).
// - Migrations run inside the upgradeneeded (versionchange) transaction; if any throws, the
//   transaction is aborted, the database stays at its old version, and openDb rejects with MIG-FAIL.
// - Downgrade guard: a database newer than this app opens read-only and a banner explains why.
// - Another tab holding an old connection blocks the upgrade: a banner asks to close it.
import { SCHEMA_VERSION } from '../../version.js';
import { DB_NAME } from './schema.js';
import { MIGRATIONS } from './migrations/index.js';
import { log } from '../diagnostics/log.js';
import { showError } from '../ui/components/banner.js';

export class StorageError extends Error {
  constructor(code) {
    super(code);
    this.name = 'StorageError';
    this.code = code;
  }
}

function runMigrations(db, tx, oldVersion, newVersion, migrations) {
  let version = oldVersion;
  while (version < newVersion) {
    const step = migrations.find((m) => m.from === version);
    if (!step || step.to !== version + 1) throw new Error(`no migration from version ${version}`);
    step.up(db, tx, log);
    version = step.to;
  }
}

function openExisting(name) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(new StorageError('STO-OPEN-FAIL'));
  });
}

// Resolves { db, readOnly }. Rejects with StorageError code MIG-FAIL or STO-OPEN-FAIL.
export function openDb({ name = DB_NAME, version = SCHEMA_VERSION, migrations = MIGRATIONS } = {}) {
  return new Promise((resolve, reject) => {
    let migrationFailed = false;
    let req;
    try {
      req = indexedDB.open(name, version);
    } catch {
      reject(new StorageError('STO-OPEN-FAIL'));
      return;
    }
    req.onupgradeneeded = (event) => {
      try {
        runMigrations(req.result, req.transaction, event.oldVersion, version, migrations);
      } catch {
        migrationFailed = true;
        log('error', 'MIG-FAIL', 'storage/db', { count: event.oldVersion });
        req.transaction.abort();
      }
    };
    req.onblocked = () => {
      log('warn', 'STO-BLOCKED', 'storage/db');
      showError('STO-BLOCKED');
    };
    req.onsuccess = () => resolve({ db: req.result, readOnly: false });
    req.onerror = (event) => {
      event.preventDefault();
      const err = req.error;
      if (migrationFailed) {
        reject(new StorageError('MIG-FAIL'));
      } else if (err && err.name === 'VersionError') {
        // The stored database is newer than this app: open it as-is, read-only.
        openExisting(name).then((db) => {
          log('warn', 'STO-NEWER-VERSION', 'storage/db', { count: db.version });
          showError('STO-NEWER-VERSION');
          resolve({ db, readOnly: true });
        }, reject);
      } else {
        log('error', 'STO-OPEN-FAIL', 'storage/db');
        reject(new StorageError('STO-OPEN-FAIL'));
      }
    };
  });
}
