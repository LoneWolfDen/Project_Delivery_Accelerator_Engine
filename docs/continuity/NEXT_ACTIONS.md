# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 2 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 3 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
| 4 | DAT-04 | Add cross-tab write lock, change broadcast and version-change handling | DAT-02 |
| 5 | DAT-05 | Add persistent storage request, usage display and quota error handling | DAT-02, UI-02 |
| 6 | UI-03 | Projects list and create/rename project | DAT-02, UI-02 |
| 7 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | UI-03, DAT-03 |
| 8 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | DAT-06A, DAT-05 |
| 9 | BAK-01 | Backup export (format v1) with checksums | DAT-06B |
| 10 | BAK-02 | Restore: validate, preview and add as copies | BAK-01 |
| 11 | BAK-03 | Restore replace modes and older-schema restores | BAK-02 |
| 12 | IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | DAT-02, BAS-02 |
| 13 | IMP-02A | Keep imported files: source/chunk repositories, single transaction, duplicate detection | IMP-01 |
| 14 | IMP-02B | Import UI: choose or drop files, preview, keep or discard | IMP-02A, UI-03 |
| 15 | TST-03 | Manual browser smoke checklist for phase gates and releases | BAK-02, IMP-02B |
