# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | SEC-02 | Enforce Trusted Types with the `pdae-script-url` policy | BLD-01 |
| 2 | UI-01 | Add the safe DOM builder `app/js/ui/dom.js` | BLD-01 |
| 3 | UI-02 | Add store, hash router, header, live region, skip link | UI-01 |
| 4 | DGN-01 | Add diagnostics log, error catalogue and banner | UI-01 |
| 5 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 6 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 7 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
| 8 | DAT-04 | Add cross-tab write lock, change broadcast and version-change handling | DAT-02 |
| 9 | DAT-05 | Add persistent storage request, usage display and quota error handling | DAT-02, UI-02 |
| 10 | UI-03 | Projects list and create/rename project | DAT-02, UI-02 |
| 11 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | UI-03, DAT-03 |
| 12 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | DAT-06A, DAT-05 |
| 13 | BAK-01 | Backup export (format v1) with checksums | DAT-06B |
| 14 | BAK-02 | Restore: validate, preview and add as copies | BAK-01 |
| 15 | BAK-03 | Restore replace modes and older-schema restores | BAK-02 |
