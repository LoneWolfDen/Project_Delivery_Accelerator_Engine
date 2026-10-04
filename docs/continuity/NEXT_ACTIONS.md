# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | CLN-01 | Remove `Dockerfile`, `docker-compose.yml`, `.dockerignore` | DOC-01 |
| 2 | BLD-01 | Create the `app/` shell with CSP and smoke e2e | TST-01, SEC-01 |
| 3 | SEC-02 | Enforce Trusted Types with the `pdae-script-url` policy | BLD-01 |
| 4 | UI-01 | Add the safe DOM builder `app/js/ui/dom.js` | BLD-01 |
| 5 | UI-02 | Add store, hash router, header, live region, skip link | UI-01 |
| 6 | DGN-01 | Add diagnostics log, error catalogue and banner | UI-01 |
| 7 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 8 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 9 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
| 10 | DAT-04 | Add cross-tab write lock, change broadcast and version-change handling | DAT-02 |
| 11 | DAT-05 | Add persistent storage request, usage display and quota error handling | DAT-02, UI-02 |
| 12 | UI-03 | Projects list and create/rename project | DAT-02, UI-02 |
| 13 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | UI-03, DAT-03 |
| 14 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | DAT-06A, DAT-05 |
| 15 | BAK-01 | Backup export (format v1) with checksums | DAT-06B |
