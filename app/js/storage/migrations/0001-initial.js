// Migration 0 → 1 (DAT-01): create every store and index of schema v1 and the install meta record.
import { STORES } from '../schema.js';
import { APP_VERSION } from '../../../version.js';

function randomId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return `ins_${[...bytes].map((b) => b.toString(16).padStart(2, '0')).join('')}`;
}

export default {
  from: 0,
  to: 1,
  up(db, tx) {
    for (const s of STORES) {
      const store = db.createObjectStore(s.name, { keyPath: s.keyPath, autoIncrement: Boolean(s.autoIncrement) });
      for (const ix of s.indexes) store.createIndex(ix.name, ix.keyPath, { unique: Boolean(ix.unique) });
    }
    // installId is random, local only, never transmitted (DATA_AND_STORAGE_ARCHITECTURE.md §3).
    const now = new Date().toISOString();
    tx.objectStore('meta').put({
      key: 'install',
      schema: 1,
      schemaVersion: 1,
      createdAt: now,
      updatedAt: now,
      createdByAppVersion: APP_VERSION,
      lastOpenedAppVersion: APP_VERSION,
      installId: randomId(),
    });
  },
};
