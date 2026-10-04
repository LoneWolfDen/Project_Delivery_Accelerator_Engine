# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | UI-02 | Add store, hash router, header, live region, skip link | UI-01 |
| 2 | DGN-01 | Add diagnostics log, error catalogue and banner | UI-01 |
| 3 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 4 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 5 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
| 6 | DAT-04 | Add cross-tab write lock, change broadcast and version-change handling | DAT-02 |
| 7 | DAT-05 | Add persistent storage request, usage display and quota error handling | DAT-02, UI-02 |
| 8 | UI-03 | Projects list and create/rename project | DAT-02, UI-02 |
| 9 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | UI-03, DAT-03 |
| 10 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | DAT-06A, DAT-05 |
| 11 | BAK-01 | Backup export (format v1) with checksums | DAT-06B |
| 12 | BAK-02 | Restore: validate, preview and add as copies | BAK-01 |
| 13 | BAK-03 | Restore replace modes and older-schema restores | BAK-02 |
| 14 | IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | DAT-02, BAS-02 |
| 15 | IMP-02A | Keep imported files: source/chunk repositories, single transaction, duplicate detection | IMP-01 |
