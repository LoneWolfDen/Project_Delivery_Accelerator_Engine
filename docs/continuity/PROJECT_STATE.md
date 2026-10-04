# Project State

| Field | Value |
|---|---|
| Last updated | 2026-10-04 |
| Repository | `LoneWolfDen/Project_Delivery_Accelerator_Engine` (private; local path on owner's Mac: `~/Developer/Project_Delivery_Accelerator_Engine`) |
| Branch | `assessment/pwa-readiness-2026-10` (created from `main` at `1ca4319`) |
| Commit | Planning work sits on top of `491fc7e` (charter and prompts). After the owner commits the planning documents, run `git log -1 --oneline` for the current hash. **Application code is unchanged since `1ca4319`.** |
| Tags | `pwa-assessment-baseline-2026-10-01` → `1ca4319`; `legacy-baseline` (annotated) → `fffe2e7` (BAS-01, pushed). Planned: `legacy-final` (CLN-02) |
| Phase | Planning complete. Implementation Phase 0 not started |

## Current implementation state

The repository still contains only the **legacy application**: a Python standard-library HTTP server with SQLite/JSON storage and two hand-written inline-script UIs (`static/index.html` V1 default, `static/v2/dashboard_v2.html` V2). Key facts (`docs/assessment/`):

- Not a PWA (no manifest, no service worker); no framework; **no minified code**.
- CI has failed on the last 200 runs. The Docker image and non-editable install can't start.
- Security BLOCKERs: static path traversal (B-1), unauthenticated network exposure in Docker (B-2). HIGH: admin PIN readable and replaceable, wildcard CORS, arbitrary file ingest, plaintext secrets, irreversible delete.
- No chatbot; heuristic text presented as findings; no Microsoft 365 integration.
- The owner doesn't use the legacy app and it holds no real data (Q-B, Q-C).

## Target

A **browser-only, no-build PWA** (`docs/architecture/TARGET_ARCHITECTURE.md`):

- plain ES modules in `app/`
- IndexedDB storage with Trash, quarantine, schema migrations and a backup/restore file
- import with provenance
- deterministic, cited "Ask" and persona reviews
- exports
- Microsoft 365 Copilot via copy-ready packages, paste-back as Draft, a Copilot-ready folder and an Agent Builder kit (no API)
- optional OpenRouter behind per-request consent
- hosting-neutral: any static HTTPS host, or a double-click local launcher on `127.0.0.1:8765`

The legacy app is retired after the extraction and review ports pass parity (ADR-023).

## Top risks

See `docs/backlog/RISK_REGISTER.md`.

| Risk | Mitigation status |
|---|---|
| R-01 browser storage loss | Backup/restore planned (BAK-01–03); not built |
| R-02 service worker pins a broken release | Reset page before worker (PWA-04 → PWA-02A/B); not built |
| R-04 / R-15 corporate policy differs from tests | Owner manual checks (TST-03) |
| R-06 OpenRouter blocked from browser | AI-02 spike |
| R-12 publishing legacy vulnerabilities | REL-02 depends on CLN-02 |

## Blockers

| Blocker | Affects | Needed from |
|---|---|---|
| Copyright holder name for `LICENSE` (BD-01) | DOC-01 | Owner |
| Tenant prerequisites P1–P8 | GRA-01–04, CPL-05 (Phase 4 only) | Tenant administrator |
| A Copilot API (none available, Q-E) | CPL-05 | Microsoft / organisation |

Nothing blocks Phase 0 except BD-01 for DOC-01.

## Next task

**TST-01** (dev-only test tooling) or **BAS-02** (synthetic fixtures): both have no prerequisites. Run one at a time with `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. See `NEXT_ACTIONS.md`.

## Backlog item status

Status values: Not started · In progress · Done · Stopped (reason in Evidence) · BLOCKED. When an item is Done, set Date and Evidence (test commands passed, commit hash if committed) and remove it from `NEXT_ACTIONS.md`. Order = `docs/backlog/FINAL_EXECUTION_SEQUENCE.md`.

| Phase | ID | Title | Priority | Status | Date | Evidence |
|---|---|---|---|---|---|---|
| 0 | BAS-01 | Record the legacy baseline tag and execution log | P0 | Done | 2026-10-04 | `git tag --list legacy-baseline` → `legacy-baseline`; tag object → commit `fffe2e70d6e25b7db4d1baf0762140024f80d957`; on origin; log commit `b61df6f` |
| 0 | BAS-02 | Copy synthetic sample documents into test fixtures | P0 | Not started | — | — |
| 0 | BAS-03 | Capture legacy extraction and persona outputs as golden files | P0 | Not started | — | — |
| 0 | BAS-04 | Convert persona YAML definitions to JSON for the new app | P0 | Not started | — | — |
| 0 | TST-01 | Add dev-only Node test tooling and static dev server | P0 | Not started | — | — |
| 0 | TST-02 | Replace permanently failing CI with the new checks | P0 | Not started | — | — |
| 0 | SEC-01 | Forbidden-API and fabrication guard checker | P0 | Not started | — | — |
| 0 | CHT-01 | Statement, label and citation domain model | P0 | Not started | — | — |
| 0 | DOC-01 | Add MIT LICENSE and a truthful README status banner | P1 | Not started | — | — |
| 0 | CLN-01 | Remove Docker and Compose files | P1 | Not started | — | — |
| 1 | BLD-01 | Application shell skeleton with CSP and file:// guard | P0 | Not started | — | — |
| 1 | SEC-02 | Enforce Trusted Types with a single script-URL policy | P0 | Not started | — | — |
| 1 | UI-01 | Safe DOM builder | P0 | Not started | — | — |
| 1 | UI-02 | App frame: store, hash router, header, live region, skip link | P1 | Not started | — | — |
| 1 | DGN-01 | Diagnostics log, error codes and visible error banner | P0 | Not started | — | — |
| 1 | DAT-01 | IndexedDB open, schema v1, migration runner and downgrade guard | P0 | Not started | — | — |
| 1 | DAT-02 | Record validators and generic repositories with optimistic concurrency | P0 | Not started | — | — |
| 1 | DAT-03 | Quarantine for unreadable records and diagnostics persistence | P0 | Not started | — | — |
| 1 | DAT-04 | Cross-tab write lock, change broadcast and version-change handling | P1 | Not started | — | — |
| 1 | DAT-05 | Persistent storage request, usage display and quota error handling | P1 | Not started | — | — |
| 1 | UI-03 | Projects list and create/rename project | P1 | Not started | — | — |
| 1 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | P0 | Not started | — | — |
| 1 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | P0 | Not started | — | — |
| 1 | BAK-01 | Backup export (format v1) with checksums | P0 | Not started | — | — |
| 1 | BAK-02 | Restore: validate, preview and add as copies | P0 | Not started | — | — |
| 1 | BAK-03 | Restore replace modes and older-schema restores | P1 | Not started | — | — |
| 1 | IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | P0 | Not started | — | — |
| 1 | IMP-02A | Keep imported files: source/chunk repositories, single transaction, duplicate detection | P0 | Not started | — | — |
| 1 | IMP-02B | Import UI: choose or drop files, preview, keep or discard | P0 | Not started | — | — |
| 1 | TST-03 | Manual browser smoke checklist for phase gates and releases | P1 | Not started | — | — |
| 1 | IMP-03 | Markdown, CSV and JSON parsers with locators | P1 | Not started | — | — |
| 1 | IMP-04 | Email (.eml) parser | P1 | Not started | — | — |
| 1 | IMP-05 | Hostile-input and size-limit protections for import | P0 | Not started | — | — |
| 2 | PWA-01 | Web app manifest and icons | P1 | Not started | — | — |
| 2 | PWA-04 | Recovery page (reset.html) and remote kill-switch file, before any service worker | P1 | Not started | — | — |
| 2 | PWA-02A | Precache manifest generator and CI freshness check (no service worker) | P1 | Not started | — | — |
| 2 | PWA-02B | Service worker: app-shell cache, offline start, kill-switch integration | P1 | Not started | — | — |
| 2 | PWA-03 | Update prompt with backup-first and schema-change notice | P1 | Not started | — | — |
| 2 | IMP-06 | DOCX import without third-party libraries | P1 | Not started | — | — |
| 2 | MIG-01A | Port deterministic extraction (pure) with citations and parity tests | P0 | Not started | — | — |
| 2 | MIG-01B | Store extracted items on keep and support re-run | P0 | Not started | — | — |
| 2 | UI-04 | Source viewer and citation component | P1 | Not started | — | — |
| 2 | UI-05 | Extracted items view | P1 | Not started | — | — |
| 2 | CHT-02 | Deterministic search index and query (BM25) | P1 | Not started | — | — |
| 2 | CHT-03 | Ask view: evidence answers with scope, Not found and history | P1 | Not started | — | — |
| 2 | DAT-07 | Snapshots (named, immutable versions of included sources) | P1 | Not started | — | — |
| 2 | MIG-02A | Port persona review heuristics (pure) with explicit labelling rules and parity tests | P0 | Not started | — | — |
| 2 | MIG-02B | Persist reviews against snapshots | P0 | Not started | — | — |
| 2 | UI-06 | Reviews view with labelled findings | P1 | Not started | — | — |
| 2 | ODI-01 | OneDrive/SharePoint V1 input: synced-folder guidance and provenance | P1 | Not started | — | — |
| 2 | EXP-01A | Export builders: manifest, Markdown and JSON (pure) | P1 | Not started | — | — |
| 2 | EXP-01B | Self-contained HTML report export | P1 | Not started | — | — |
| 2 | EXP-01C | Exports view, boundary notice and export records | P1 | Not started | — | — |
| 2 | EXP-02 | Stored ZIP writer for multi-file exports | P2 | Not started | — | — |
| 2 | CPL-01A | Copilot package builder and clipboard splitter (pure) | P2 | Not started | — | — |
| 2 | CPL-01B | Prepare-for-Copilot dialog: clipboard copy and ZIP download | P2 | Not started | — | — |
| 2 | CPL-02 | Copilot paste-back stored as Draft with citation-ID checks | P2 | Not started | — | — |
| 2 | BLD-02 | Local launchers for Windows and macOS (double-click start) | P1 | Not started | — | — |
| 2 | UI-07 | Accessibility verification pass on main journeys | P1 | Not started | — | — |
| 2 | DOC-02 | In-app help: start, backup, restore, rollback, data boundary, Copilot how-to | P1 | Not started | — | — |
| 2 | REL-01A | Release process: versioning, release checklist and release zip | P1 | Not started | — | — |
| 2 | CLN-02 | Retire the legacy application (tag legacy-final, remove legacy code) | P1 | Not started | — | — |
| 2 | DOC-03 | Rewrite README for the new app | P1 | Not started | — | — |
| 3 | REL-02 | Pre-publication checklist before making the repository public | P2 | Not started | — | — |
| 3 | REL-01B | Optional static deployment job (hosting-neutral) | P2 | Not started | — | — |
| 3 | AI-01 | AI provider interface, consent token and egress preview (no network) | P2 | Not started | — | — |
| 3 | AI-02 | OpenRouter adapter behind consent (with browser CORS spike) | P2 | Not started | — | — |
| 3 | AI-03 | AI-assisted Ask with response validation | P2 | Not started | — | — |
| 3 | AI-04 | AI-assisted review (optional) per persona section | P2 | Not started | — | — |
| 3 | IMP-07 | PDF import via vendored pdf.js | P2 | Not started | — | — |
| 3 | ODI-02A | Schema migration 1 → 2: folderLinks store (migration only) | P2 | Not started | — | — |
| 3 | ODI-02B | Linked folder connector with user-triggered refresh and changed-file preview | P2 | Not started | — | — |
| 3 | EXP-03 | V2 save picker export to a user-chosen folder | P2 | Not started | — | — |
| 3 | CPL-03 | Copilot grounding V2: Copilot-ready export layout and governance notice | P2 | Not started | — | — |
| 3 | CPL-04 | Agent Builder kit export (user configures the agent manually) | P2 | Not started | — | — |
| 3 | UI-08 | Presentation (screen-share) mode | P2 | Not started | — | — |
| 3 | DGN-02 | Diagnostics view and content-free diagnostic report | P2 | Not started | — | — |
| 3 | CLN-03 | Archive superseded docs and remove _archive and sample_data duplicates | P2 | Not started | — | — |
| 4 | GRA-01 | Record Microsoft 365 V3 prerequisites P1–P8 | P3 | BLOCKED | — | — |
| 4 | GRA-02 | MSAL.js sign-in (auth code + PKCE, delegated) | P3 | BLOCKED | — | — |
| 4 | GRA-03 | Microsoft File Picker source connector (V3 input) | P3 | BLOCKED | — | — |
| 4 | GRA-04 | Graph destination connector with conflict handling (V3 output) | P3 | BLOCKED | — | — |
| 4 | CPL-05 | Copilot API, connector or programmatic agent integration | P3 | BLOCKED | — | — |
