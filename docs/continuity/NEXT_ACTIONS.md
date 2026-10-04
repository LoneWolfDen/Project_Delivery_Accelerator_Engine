# Next Actions

Ordered. Execute top to bottom, one at a time, with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Remove an entry when it is Done in `PROJECT_STATE.md`, and append the next item from `docs/backlog/FINAL_EXECUTION_SEQUENCE.md` so the list stays at 15 or fewer.

| # | Backlog ID | Action | Prerequisite |
|---|---|---|---|
| 1 | DOC-01 | Add MIT `LICENSE` and README status banner | — (holder: Vamsi Yedlapalli / LoneWolfDen, BD-01a) |
| 2 | TST-02 | Replace the failing CI workflow with check/unit/e2e jobs | TST-01 |
| 3 | SEC-01 | Add `tools/check-forbidden-apis.mjs` with unit tests | TST-01 |
| 4 | CHT-01 | Add statement/label/citation domain modules with unit tests | TST-01 |
| 5 | BAS-03 | Generate legacy golden outputs with `tools/legacy-golden.py` | BAS-01, BAS-02 |
| 6 | BAS-04 | Convert persona YAML to JSON with `tools/personas-to-json.py` | BAS-01 |
| 7 | CLN-01 | Remove `Dockerfile`, `docker-compose.yml`, `.dockerignore` | DOC-01 |
| 8 | BLD-01 | Create the `app/` shell with CSP and smoke e2e | TST-01, SEC-01 |
| 9 | SEC-02 | Enforce Trusted Types with the `pdae-script-url` policy | BLD-01 |
| 10 | UI-01 | Add the safe DOM builder `app/js/ui/dom.js` | BLD-01 |
| 11 | UI-02 | Add store, hash router, header, live region, skip link | UI-01 |
| 12 | DGN-01 | Add diagnostics log, error catalogue and banner | UI-01 |
| 13 | DAT-01 | Add IndexedDB open, schema v1, migration runner and downgrade guard | DGN-01 |
| 14 | DAT-02 | Add record validators and generic repositories with optimistic concurrency | DAT-01 |
| 15 | DAT-03 | Add quarantine for unreadable records and diagnostics persistence | DAT-02 |
