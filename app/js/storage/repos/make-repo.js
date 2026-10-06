// Generic repository with validation and optimistic concurrency (DAT-02;
// DATA_AND_STORAGE_ARCHITECTURE.md §4). Only code under app/js/storage/ opens transactions.
// Every method takes the open database first. put() never silently overwrites: when a record
// exists, the caller must pass the updatedAt it read (expectUpdatedAt), or the write fails
// with STO-CONFLICT and nothing is written.
import { StorageError } from '../db.js';
import { nowIso } from '../../core/time.js';

function codeFor(err) {
  if (err instanceof StorageError) return err.code;
  if (err && err.name === 'QuotaExceededError') return 'STO-QUOTA';
  return 'STO-WRITE-FAIL';
}

function request(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Run fn(tx) inside one transaction; resolves with fn's result when the transaction commits.
// If fn throws or rejects, the transaction is aborted and nothing is written.
export function withTx(db, storeNames, mode, fn) {
  return new Promise((resolve, reject) => {
    let tx;
    try {
      tx = db.transaction(storeNames, mode);
    } catch (err) {
      reject(new StorageError(codeFor(err)));
      return;
    }
    let value;
    let failure = null;
    tx.oncomplete = () => resolve(value);
    tx.onabort = () => reject(failure ?? new StorageError(codeFor(tx.error)));
    Promise.resolve()
      .then(() => fn(tx, request))
      .then(
        (v) => {
          value = v;
        },
        (err) => {
          failure = err instanceof StorageError ? err : new StorageError(codeFor(err));
          try {
            tx.abort();
          } catch {
            reject(failure);
          }
        },
      );
  });
}

function laterThan(previous) {
  const now = nowIso();
  if (!previous || now > previous) return now;
  return new Date(Date.parse(previous) + 1).toISOString();
}

export function makeRepo(storeName, validate) {
  return {
    storeName,

    // Returns the validated record (defaults applied) or undefined. Invalid stored records
    // reject with STO-INVALID (DAT-03 moves them to quarantine).
    get(db, key) {
      return withTx(db, [storeName], 'readonly', async (tx) => {
        const raw = await request(tx.objectStore(storeName).get(key));
        if (raw === undefined) return undefined;
        const v = validate(raw);
        if (!v.ok) throw new StorageError('STO-INVALID');
        return v.value;
      });
    },

    // All records, or those whose index `indexName` equals `key`. Invalid records are skipped
    // here and counted on the result's `invalid` property (DAT-03 quarantines them).
    list(db, indexName, key) {
      return withTx(db, [storeName], 'readonly', async (tx) => {
        const store = tx.objectStore(storeName);
        const source = indexName ? store.index(indexName) : store;
        const raws = await request(key === undefined ? source.getAll() : source.getAll(key));
        const out = [];
        let invalid = 0;
        for (const raw of raws) {
          const v = validate(raw);
          if (v.ok) out.push(v.value);
          else invalid += 1;
        }
        Object.defineProperty(out, 'invalid', { value: invalid });
        return out;
      });
    },

    // Insert or update. Sets updatedAt (strictly later than the stored one). Resolves with the
    // stored record. Rejects with STO-INVALID (nothing written) or STO-CONFLICT (stale read).
    put(db, record, { expectUpdatedAt } = {}) {
      return withTx(db, [storeName], 'readwrite', async (tx) => {
        const store = tx.objectStore(storeName);
        const key = record?.[store.keyPath];
        const existing = key === undefined ? undefined : await request(store.get(key));
        if (existing !== undefined && existing.updatedAt !== expectUpdatedAt) throw new StorageError('STO-CONFLICT');
        if (existing === undefined && expectUpdatedAt !== undefined) throw new StorageError('STO-CONFLICT');
        const next = { ...record, updatedAt: laterThan(existing?.updatedAt) };
        const v = validate(next);
        if (!v.ok) {
          const err = new StorageError('STO-INVALID');
          err.errors = v.errors;
          throw err;
        }
        await request(store.put(next));
        return next;
      });
    },
  };
}
