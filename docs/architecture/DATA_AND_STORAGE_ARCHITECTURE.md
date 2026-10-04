# Data and Storage Architecture

| Field | Value |
|---|---|
| Status | Proposed |
| Date | 2026-10-04 |
| Parent | `TARGET_ARCHITECTURE.md` §6–10 |
| Replaces (at cutover) | Legacy SQLite `accelerator.db` plus JSON dual-write (`db/`, `services/project.py`), which has no backup, silent fallbacks, silent eviction and silent overwrite (security H-6, M-4–M-7) |

---

## 1. Storage tiers (charter §5)

| Tier | Charter category | Target | Release |
|---|---|---|---|
| 1 | Runtime browser storage | IndexedDB database `pdae` in the user's browser profile; `localStorage` for UI preferences only | V1 |
| 2 | User-controlled backup and restore | `.pdae-backup.json` file, downloaded by the user, saved wherever they choose | V1 |
| 3 | User-selected OneDrive/SharePoint content | Files the user picks from a locally synced folder (input), or saves into one (output) | V1 (files), V2 (folder handle) |
| 4 | Approved live Microsoft Graph storage | Not implemented; interface reserved (`connectors/`) | V3, after approvals |
| 5 | Application-managed enterprise storage | **None.** No server, no cloud database. | Not planned |

**Data boundary:** with tiers 1 and 2 only, user content never leaves the device unless the user (a) downloads a file and puts it somewhere, (b) sends a consented OpenRouter request, or (c) copies a Copilot package.

## 2. Entities

```
Project ─┬─< Source ─< Chunk
         │      └── provenance (TARGET_ARCHITECTURE.md §10)
         ├─< Item            (extracted: risk | assumption | dependency | constraint | action | scope; cites Chunk spans)
         ├─< Snapshot        (named version: which Sources were included, Item ids, created time, note)
         │      └─< Review   (persona, mode, findings[] each labelled and cited)
         ├─< Answer          (Ask results: question, scope, evidence[], labelled statements, origin)
         ├─< Draft           (external text: Copilot paste-back or OpenRouter output; never Fact)
         └─< ExportRecord    (what was exported, when, manifest hash, destination type; no content)
Settings (singleton) · Diagnostics (ring buffer) · Quarantine · Trash · Meta (singleton)
```

Labels (charter §9) apply to every statement in `Review.findings`, `Answer.statements` and imported `Draft` fragments:
`FACT` (quoted from a stored source, with citation), `INFERENCE` (derived; cites its basis), `RECOMMENDATION`, `NOT_FOUND` (searched and absent, with scope), `NEEDS_CONFIRMATION`.
Each also carries `origin`: `deterministic | openrouter | copilot-pasted | user`.

## 3. IndexedDB layout

Database name `pdae`. IndexedDB `version` = `SCHEMA_VERSION` (integer, starts at 1).

| Store | keyPath | Indexes | Notes |
|---|---|---|---|
| `meta` | `key` | — | `schemaVersion`, `createdAt`, `createdByAppVersion`, `lastOpenedAppVersion`, `installId` (random, never transmitted) |
| `projects` | `id` | `status`, `updatedAt` | `status: active \| trashed` |
| `sources` | `id` | `projectId`, `[projectId+sha256]` (unique) | Holds the original file `Blob` plus provenance; the unique index prevents silent duplicates |
| `chunks` | `id` | `sourceId`, `projectId` | Text plus locator; the search index is rebuilt from these |
| `items` | `id` | `projectId`, `[projectId+kind]`, `sourceId` | Extraction output with citations; carries `extractorVersion` |
| `snapshots` | `id` | `projectId` | Immutable once created |
| `reviews` | `id` | `projectId`, `snapshotId` | Immutable once created (a re-run creates a new review linked by `previousReviewId`) |
| `answers` | `id` | `projectId`, `createdAt` | Optional history; user can clear |
| `drafts` | `id` | `projectId`, `origin` | External text; editable; acceptance recorded as `{acceptedAs, by, at}` |
| `exports` | `id` | `projectId`, `createdAt` | Metadata only |
| `settings` | `key` | — | No secrets |
| `diagnostics` | `seq` (auto) | `time` | Ring buffer, max 500, content-free |
| `quarantine` | `id` | `store`, `time` | `{store, originalKey, raw, error, appVersion, schemaVersion}`; never auto-deleted |
| `trash` | `id` | `deletedAt`, `projectId` | Soft-deleted records with all children, restorable |

Every record carries `schema: <int>` and `updatedAt`. Every record type has a validator in `domain/`. Reads go through `repos/*`, which validate (§9).

## 4. Writes and integrity

- Every logical operation (e.g. "keep imported file" = 1 Source + N Chunks + M Items) is **one IndexedDB transaction**, so it fully commits or fully aborts.
- Writes are serialised across tabs with `navigator.locks.request("pdae-write")`. Other tabs are notified through `BroadcastChannel("pdae")` and reload their view.
- `onversionchange` in any tab closes its connection and shows "The app was updated in another tab. Reload to continue." This avoids a blocked upgrade.
- **No silent overwrite:** updates use optimistic concurrency (`updatedAt` must match what was read). A mismatch produces a visible conflict message, never a last-write-wins.
- **Quota errors** (`QuotaExceededError`) abort the transaction and show banner `STO-QUOTA` with the current usage and options: Export backup, Empty Trash, Remove originals (keep text).

## 5. Persistence and usage

- On first data write: call `navigator.storage.persist()` and record the result. Settings and Diagnostics show "Storage protected from automatic clean-up: Yes / No".
- When it's **No**, or on Safari, which can evict script-written storage after a period without use unless the app is added to the Dock: show a backup reminder after every import session, and when the last backup is older than 7 days.
- Usage display from `navigator.storage.estimate()`, plus a per-project breakdown computed from `Blob.size` sums.
- Header indicator "Last backup: 3 days ago". Its warning state triggers at more than 7 days or never.

## 6. Delete, trash and reset (no silent loss)

| Action | Behaviour |
|---|---|
| Delete a source, item, review, draft or project | Moved to `trash` with children, in one transaction. Toast with **Undo**. Restorable from the Trash view. |
| Empty Trash / permanent delete | Lists what will be removed. User types `DELETE`. Offers **Download backup first**. |
| Trash retention | Default 30 days (setting). Expiry **never** runs silently: on start, expired entries are listed with "Remove now / Keep 30 more days". |
| Reset app | Settings → Danger zone. User types `RESET`. Mandatory "Download backup first" step that can be skipped only by an explicit second click. Deletes the `pdae` database; service worker and caches untouched. |
| Limits | No maximum-project eviction. The legacy `MAX_ARCHIVED = 5` behaviour (security M-5) is not carried over. |
| Residual content | Deleting a project removes **all** its records, including answers, drafts, exports metadata and diagnostics refs. There's no equivalent of the legacy `prompt_log` residue (security M-4). |

## 7. Schema versioning and migration

- `SCHEMA_VERSION` lives in `app/version.js`. Migrations are files `storage/migrations/NNNN-<name>.js`, each exporting `{from: N-1, to: N, up(tx, log)}`.
- Migrations run inside IndexedDB's `upgradeneeded` (versionchange) transaction. **If any step throws, the whole upgrade aborts and the database stays at the old version, unchanged.** The app then shows `MIG-NNNN-FAIL` with: "Your data is untouched. Download a backup and send the diagnostic report", plus a button to export a backup **using the old schema reader** (each release keeps readers for the previous schema).
- **Before an upgrade:** the service-worker update prompt says "This update changes how data is stored (schema 3 → 4). Download a backup first (recommended)". This is the only reliable pre-migration backup, because a browser download requires a user gesture.
- **Downgrade guard:** if the database version is newer than the running app knows (e.g. the user rolled back the app), the app opens **read-only**, explains why, and offers backup export only. It never writes.
- Records that fail validation during migration are copied to `quarantine` and skipped, not dropped. The count is shown after the upgrade.
- **Tests:** for every migration, a fixture database at version N-1 (built by a Playwright test using the previous migration set) is upgraded and asserted on (`TARGET_ARCHITECTURE.md` §24).

## 8. Backup and restore

### Backup file format `.pdae-backup.json`

```json
{
  "format": "pdae-backup",
  "formatVersion": 1,
  "appVersion": "1.2.0",
  "schemaVersion": 3,
  "createdAt": "2026-10-04T09:12:00Z",
  "scope": { "type": "all" | "project", "projectIds": ["…"] },
  "includesOriginals": true,
  "counts": { "projects": 2, "sources": 14, "chunks": 950, "items": 210, "snapshots": 4, "reviews": 9, "answers": 30, "drafts": 3 },
  "stores": { "projects": [ … ], "sources": [ { …, "blob": { "type": "application/vnd…", "base64": "…", "sha256": "…" } } ], … },
  "recordHashes": { "<store>/<id>": "sha256…" },
  "checksum": "sha256 of canonical JSON of everything except this field"
}
```

- Excludes `diagnostics`, `quarantine` (exported separately from Diagnostics), and anything secret (there are none stored).
- **Download** uses an `<a download>` Blob URL in V1. In V2 Chromium, `showSaveFilePicker` lets the user choose a location, e.g. a synced OneDrive folder, with an explicit boundary notice (`ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3).
- Option "Text only (smaller)": omits original file blobs and keeps chunks and provenance hashes.

### Restore

1. User selects a backup file (file input or drag-and-drop).
2. Validate: `format`, `formatVersion`, `checksum`, every `recordHashes` entry, and `schemaVersion ≤ app's`. On failure, show which check failed; nothing is written.
3. **Preview:** counts, project names, backup date and app version, and what conflicts with current data (same IDs).
4. The user chooses:
   - **Add as copies.** New IDs for clashing projects; nothing existing is touched.
   - **Replace matching projects.** Requires typed `REPLACE` and offers "Download backup of current data first".
   - **Replace everything.** Requires typed `REPLACE ALL` and the same pre-backup offer.
5. Records from an older `schemaVersion` are passed through the same migration functions in memory, then written in one transaction per project.
6. A result summary is shown, and an `ExportRecord`-style `RestoreRecord` is written to diagnostics.

### Rollback instructions (exact, user-facing; also in-app Help)

1. Download a backup (Settings → Backup → Download backup).
2. If the new version misbehaves: open `<app-url>/reset.html` → "Reset app code" (data kept).
3. To run the previous version: use the previous release zip with the local launcher, or wait for the maintainer to republish the previous version.
4. If the previous version can't read the data (newer schema), it opens read-only: Settings → Backup → Restore, and choose the backup made in step 1. Restoring a backup **made by** an older version is always supported by newer versions.

## 9. Corruption preservation

- Every repo read validates the record. Invalid records are moved (copy, then delete, in one transaction) to `quarantine` with the error, and the UI shows "1 item couldn't be read and was set aside. Nothing was deleted."
- Diagnostics lists quarantined records with **Export quarantine** (JSON) and **Try again** (re-validates after an app update).
- If the database itself fails to open (other than a version mismatch), the app shows `STO-OPEN-FAIL` and offers **Export raw data** (best effort via a cursor over each store). It never auto-deletes or recreates the database.

## 10. Moving between hosted and local origins

IndexedDB is per origin (`https://<host>` ≠ `http://127.0.0.1:8765`). Data doesn't follow the user between them. The supported path is Backup on one, Restore on the other. Both start pages show which origin they're on ("This copy stores data in: this browser, at 127.0.0.1:8765") to avoid "my data disappeared" confusion.

## 11. Legacy data

Proposed (ADR-013): **no automated migration** from the legacy SQLite/JSON store. Rationale: the assessment found only seeded or synthetic demo data paths, the owner can't recall which features work (OD-2), and an importer would need the legacy Python runtime. Users re-import original documents, which also creates correct provenance. If the owner has real legacy data worth keeping, a one-off developer script reading `accelerator.db` and writing `.pdae-backup.json` can be added as a single backlog item.
