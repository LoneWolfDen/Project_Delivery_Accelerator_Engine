// IndexedDB schema v1 (DAT-01). Exactly the DATA_AND_STORAGE_ARCHITECTURE.md §3 table.
// Compound indexes are named '<a>+<b>' with key path [a, b].

export const DB_NAME = 'pdae';

export const STORES = Object.freeze([
  { name: 'meta', keyPath: 'key', indexes: [] },
  { name: 'projects', keyPath: 'id', indexes: [{ name: 'status', keyPath: 'status' }, { name: 'updatedAt', keyPath: 'updatedAt' }] },
  { name: 'sources', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'projectId+sha256', keyPath: ['projectId', 'sha256'], unique: true }] },
  { name: 'chunks', keyPath: 'id', indexes: [{ name: 'sourceId', keyPath: 'sourceId' }, { name: 'projectId', keyPath: 'projectId' }] },
  { name: 'items', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'projectId+kind', keyPath: ['projectId', 'kind'] }, { name: 'sourceId', keyPath: 'sourceId' }] },
  { name: 'snapshots', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }] },
  { name: 'reviews', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'snapshotId', keyPath: 'snapshotId' }] },
  { name: 'answers', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'createdAt', keyPath: 'createdAt' }] },
  { name: 'drafts', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'origin', keyPath: 'origin' }] },
  { name: 'exports', keyPath: 'id', indexes: [{ name: 'projectId', keyPath: 'projectId' }, { name: 'createdAt', keyPath: 'createdAt' }] },
  { name: 'settings', keyPath: 'key', indexes: [] },
  { name: 'diagnostics', keyPath: 'seq', autoIncrement: true, indexes: [{ name: 'time', keyPath: 'time' }] },
  { name: 'quarantine', keyPath: 'id', indexes: [{ name: 'store', keyPath: 'store' }, { name: 'time', keyPath: 'time' }] },
  { name: 'trash', keyPath: 'id', indexes: [{ name: 'deletedAt', keyPath: 'deletedAt' }, { name: 'projectId', keyPath: 'projectId' }] },
]);
