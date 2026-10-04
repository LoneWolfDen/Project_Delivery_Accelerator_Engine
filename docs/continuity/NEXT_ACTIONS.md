# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | SEC-01 | Add `tools/check-forbidden-apis.mjs` with unit tests | TST-01 |
| 2 | CHT-01 | Add statement/label/citation domain modules with unit tests | TST-01 |
| 3 | BAS-03 | Generate legacy golden outputs with `tools/legacy-golden.py` | BAS-01, BAS-02 |
| 4 | BAS-04 | Convert persona YAML to JSON with `tools/personas-to-json.py` | BAS-01 |
| 5 | CLN-01 | Remove `Dockerfile`, `docker-compose.yml`, `.dockerignore` | DOC-01 |
| 6 | BLD-01 | Create the `app/` shell with CSP and smoke e2e | TST-01, SEC-01 |
| 7 | SEC-02 | Enforce Trusted Types with the `pdae-script-url` policy | BLD-01 |
| 8 | UI-01 | Add the safe DOM builder `app/js/ui/dom.js` | BLD-01 |
| 9 | UI-02 | Add store, hash router, header, live region, skip link | UI-01 |
| 10 | DGN-01 | Add diagnostics log, error catalogue and banner | UI-01 |
| 11 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 12 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 13 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
| 14 | DAT-04 | Add cross-tab write lock, change broadcast and version-change handling | DAT-02 |
| 15 | DAT-05 | Add persistent storage request, usage display and quota error handling | DAT-02, UI-02 |
