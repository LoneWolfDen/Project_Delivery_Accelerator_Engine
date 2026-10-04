# Master Backlog

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Baseline | Branch `assessment/pwa-readiness-2026-10`, commit `491fc7e` (application code unchanged since `1ca4319`) |
| Sources | `docs/assessment/*`, `docs/architecture/*` (incl. `ADR_REGISTER.md` owner answers 2026-10-04: ADR-023 early legacy retirement, ADR-024 hosting-neutral, ADR-025 Copilot via licensed desktop surfaces, no API) |
| Items | 83 |
| Revision | Corrected by `BACKLOG_VALIDATION.md` (2026-10-04): 9 items split, 1 added (TST-03), 17 corrected. Changed items carry a 'Validation note' row. Execution order: **`FINAL_EXECUTION_SEQUENCE.md`** (supersedes `EXECUTION_SEQUENCE.md` and the tables in `DEPENDENCY_MAP.md` §1–2). |
| How to use | Execute **one ID at a time** following `SMALL_MODEL_EXECUTION_RULES.md` and `.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`. Order and dependencies: `FINAL_EXECUTION_SEQUENCE.md`. Alternatives, high-risk sequences and approval blocks: `DEPENDENCY_MAP.md` §3–6. |

Conventions used in every item:

- Test commands come from TST-01: `npm run check` (syntax, forbidden APIs, precache and vendor checks), `npm run test:unit` (`node --test tests/unit/`), `npm run test:e2e -- <spec>` (Playwright, Chromium and WebKit).
- 'Legacy paths' means the Python application and its UIs, which are frozen until CLN-02 removes them (ADR-023).
- 'UNVERIFIED' marks behaviour that automated tests cannot prove (real corporate browser policy, OneDrive client, Copilot apps); the item's manual verification must record the observed result.
- Classification values are those of the assessment: WORKING, PARTIAL, PLACEHOLDER, MOCKED, DOCUMENTED ONLY, BROKEN, UNUSED, GENERATED, UNKNOWN.

Additional rules from validation (apply to every item, in addition to `SMALL_MODEL_EXECUTION_RULES.md`):

- **Schema evolution (V-13):** new record fields are optional with read-time defaults; validators ignore unknown fields. Making a field required, renaming it or changing its type needs its own migration item with `upRecord`, a backup-first update prompt and a migration e2e test.
- **Rollback after release (V-27):** once an item has shipped in a tagged release, 'git revert' alone doesn't reach users. Rollback = revert + new patch release (REL-01A) + update prompt; if the app is broken, publish `kill-switch.json` or direct users to `./reset.html` (PWA-04).
- **Manual smoke steps (V-10):** every item that adds user-visible behaviour appends its steps to `docs/release/MANUAL_SMOKE_CHECKLIST.md` (once TST-03 exists); add that file to the item's changed files.
- **Shared files (V-28):** `app/js/ui/router.js`, `app/js/domain/validate.js`, `app/js/ui/views/project.js`, `app/js/import/pipeline.js`, `app/js/import/intake.js` are edited by many items: never run two such items in parallel branches.

## Summary

| ID | Title | Group | Priority | Phase | Depends on |
|---|---|---|---|---|---|
| BAS-01 | Record the legacy baseline tag and execution log | BASELINE AND RECOVERY | P0 | 0 | — |
| BAS-02 | Copy synthetic sample documents into test fixtures | BASELINE AND RECOVERY | P0 | 0 | — |
| BAS-03 | Capture legacy extraction and persona outputs as golden files | BASELINE AND RECOVERY | P0 | 0 | BAS-01, BAS-02 |
| BAS-04 | Convert persona YAML definitions to JSON for the new app | MINIFIED CODE MIGRATION | P0 | 0 | BAS-01 |
| TST-01 | Add dev-only Node test tooling and static dev server | TESTING | P0 | 0 | — |
| TST-02 | Replace permanently failing CI with the new checks | TESTING | P0 | 0 | TST-01 |
| SEC-01 | Forbidden-API and fabrication guard checker | SECURITY AND PRIVACY | P0 | 0 | TST-01 |
| CHT-01 | Statement, label and citation domain model | CHAT AND RETRIEVAL | P0 | 0 | TST-01 |
| DOC-01 | Add MIT LICENSE and a truthful README status banner | DOCUMENTATION | P1 | 0 | — |
| CLN-01 | Remove Docker and Compose files | REPOSITORY CLEANUP | P1 | 0 | DOC-01 |
| BLD-01 | Application shell skeleton with CSP and file:// guard | HUMAN-READABLE SOURCE | P0 | 1 | TST-01, SEC-01 |
| SEC-02 | Enforce Trusted Types with a single script-URL policy | SECURITY AND PRIVACY | P0 | 1 | BLD-01 |
| UI-01 | Safe DOM builder | UI AND ACCESSIBILITY | P0 | 1 | BLD-01 |
| UI-02 | App frame: store, hash router, header, live region, skip link | UI AND ACCESSIBILITY | P1 | 1 | UI-01 |
| DGN-01 | Diagnostics log, error codes and visible error banner | DIAGNOSTICS | P0 | 1 | UI-01 |
| DAT-01 | IndexedDB open, schema v1, migration runner and downgrade guard | DATA AND STORAGE | P0 | 1 | DGN-01 |
| DAT-02 | Record validators and generic repositories with optimistic concurrency | DATA AND STORAGE | P0 | 1 | DAT-01 |
| DAT-03 | Quarantine for unreadable records and diagnostics persistence | DATA AND STORAGE | P0 | 1 | DAT-02 |
| DAT-04 | Cross-tab write lock, change broadcast and version-change handling | DATA AND STORAGE | P1 | 1 | DAT-02 |
| DAT-05 | Persistent storage request, usage display and quota error handling | DATA AND STORAGE | P1 | 1 | DAT-02, UI-02 |
| UI-03 | Projects list and create/rename project | UI AND ACCESSIBILITY | P1 | 1 | DAT-02, UI-02 |
| DAT-06A | Trash: move to Trash, Undo, restore from Trash view | DATA AND STORAGE | P0 | 1 | UI-03, DAT-03 |
| DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | DATA AND STORAGE | P0 | 1 | DAT-06A, DAT-05 |
| BAK-01 | Backup export (format v1) with checksums | BACKUP AND RESTORE | P0 | 1 | DAT-06B |
| BAK-02 | Restore: validate, preview and add as copies | BACKUP AND RESTORE | P0 | 1 | BAK-01 |
| BAK-03 | Restore replace modes and older-schema restores | BACKUP AND RESTORE | P1 | 1 | BAK-02 |
| IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | FILE IMPORT | P0 | 1 | DAT-02, BAS-02 |
| IMP-02A | Keep imported files: source/chunk repositories, single transaction, duplicate detection | FILE IMPORT | P0 | 1 | IMP-01 |
| IMP-02B | Import UI: choose or drop files, preview, keep or discard | FILE IMPORT | P0 | 1 | IMP-02A, UI-03 |
| TST-03 | Manual browser smoke checklist for phase gates and releases | TESTING | P1 | 1 | BAK-02, IMP-02B |
| IMP-03 | Markdown, CSV and JSON parsers with locators | FILE IMPORT | P1 | 1 | IMP-02B |
| IMP-04 | Email (.eml) parser | FILE IMPORT | P1 | 1 | IMP-02B |
| IMP-05 | Hostile-input and size-limit protections for import | SECURITY AND PRIVACY | P0 | 1 | IMP-03 |
| PWA-01 | Web app manifest and icons | PWA AND OFFLINE | P1 | 2 | BLD-01 |
| PWA-04 | Recovery page (reset.html) and remote kill-switch file, before any service worker | PWA AND OFFLINE | P1 | 2 | PWA-01 |
| PWA-02A | Precache manifest generator and CI freshness check (no service worker) | PWA AND OFFLINE | P1 | 2 | PWA-04 |
| PWA-02B | Service worker: app-shell cache, offline start, kill-switch integration | PWA AND OFFLINE | P1 | 2 | PWA-02A, SEC-02 |
| PWA-03 | Update prompt with backup-first and schema-change notice | PWA AND OFFLINE | P1 | 2 | PWA-02B, BAK-03 |
| IMP-06 | DOCX import without third-party libraries | FILE IMPORT | P1 | 2 | IMP-05 |
| MIG-01A | Port deterministic extraction (pure) with citations and parity tests | MINIFIED CODE MIGRATION | P0 | 2 | IMP-03, IMP-04, BAS-03, CHT-01 |
| MIG-01B | Store extracted items on keep and support re-run | MINIFIED CODE MIGRATION | P0 | 2 | MIG-01A, IMP-02B, DAT-06A |
| UI-04 | Source viewer and citation component | UI AND ACCESSIBILITY | P1 | 2 | IMP-02B, CHT-01 |
| UI-05 | Extracted items view | UI AND ACCESSIBILITY | P1 | 2 | MIG-01B, UI-04 |
| CHT-02 | Deterministic search index and query (BM25) | CHAT AND RETRIEVAL | P1 | 2 | IMP-01 |
| CHT-03 | Ask view: evidence answers with scope, Not found and history | CHAT AND RETRIEVAL | P1 | 2 | CHT-02, UI-04, CHT-01 |
| DAT-07 | Snapshots (named, immutable versions of included sources) | DATA AND STORAGE | P1 | 2 | MIG-01B, CHT-03 |
| MIG-02A | Port persona review heuristics (pure) with explicit labelling rules and parity tests | MINIFIED CODE MIGRATION | P0 | 2 | MIG-01A, BAS-04 |
| MIG-02B | Persist reviews against snapshots | MINIFIED CODE MIGRATION | P0 | 2 | MIG-02A, DAT-07 |
| UI-06 | Reviews view with labelled findings | UI AND ACCESSIBILITY | P1 | 2 | MIG-02B, UI-04 |
| ODI-01 | OneDrive/SharePoint V1 input: synced-folder guidance and provenance | ONEDRIVE INPUT + SHAREPOINT INPUT | P1 | 2 | IMP-02B |
| EXP-01A | Export builders: manifest, Markdown and JSON (pure) | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT | P1 | 2 | MIG-02B, BAK-01 |
| EXP-01B | Self-contained HTML report export | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT | P1 | 2 | EXP-01A |
| EXP-01C | Exports view, boundary notice and export records | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT | P1 | 2 | EXP-01B, UI-06 |
| EXP-02 | Stored ZIP writer for multi-file exports | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT | P2 | 2 | EXP-01C, IMP-06 |
| CPL-01A | Copilot package builder and clipboard splitter (pure) | MICROSOFT 365 COPILOT | P2 | 2 | EXP-01A, CHT-03, MIG-02B |
| CPL-01B | Prepare-for-Copilot dialog: clipboard copy and ZIP download | MICROSOFT 365 COPILOT | P2 | 2 | CPL-01A, EXP-02, UI-06 |
| CPL-02 | Copilot paste-back stored as Draft with citation-ID checks | MICROSOFT 365 COPILOT | P2 | 2 | CPL-01B |
| BLD-02 | Local launchers for Windows and macOS (double-click start) | BUILD AND STARTUP | P1 | 2 | BLD-01 |
| UI-07 | Accessibility verification pass on main journeys | UI AND ACCESSIBILITY | P1 | 2 | UI-06, CHT-03, EXP-01C, BAK-02 |
| DOC-02 | In-app help: start, backup, restore, rollback, data boundary, Copilot how-to | DOCUMENTATION | P1 | 2 | PWA-04, BAK-03, CPL-01B, BLD-02 |
| REL-01A | Release process: versioning, release checklist and release zip | RELEASE AND OPERATIONS | P1 | 2 | TST-02, PWA-03, BLD-02, TST-03 |
| CLN-02 | Retire the legacy application (tag legacy-final, remove legacy code) | REPOSITORY CLEANUP | P1 | 2 | MIG-01A, MIG-02A, BAS-03, BAS-04, IMP-04, DOC-01 |
| DOC-03 | Rewrite README for the new app | DOCUMENTATION | P1 | 2 | CLN-02, REL-01A, DOC-02 |
| REL-02 | Pre-publication checklist before making the repository public | RELEASE AND OPERATIONS | P2 | 3 | CLN-02, DOC-03 |
| REL-01B | Optional static deployment job (hosting-neutral) | RELEASE AND OPERATIONS | P2 | 3 | REL-01A, REL-02 |
| AI-01 | AI provider interface, consent token and egress preview (no network) | SECURITY AND PRIVACY | P2 | 3 | CHT-03, UI-06 |
| AI-02 | OpenRouter adapter behind consent (with browser CORS spike) | CHAT AND RETRIEVAL | P2 | 3 | AI-01 |
| AI-03 | AI-assisted Ask with response validation | CHAT AND RETRIEVAL | P2 | 3 | AI-02 |
| AI-04 | AI-assisted review (optional) per persona section | CHAT AND RETRIEVAL | P2 | 3 | AI-03, MIG-02B |
| IMP-07 | PDF import via vendored pdf.js | FILE IMPORT | P2 | 3 | IMP-06, PWA-02B |
| ODI-02A | Schema migration 1 → 2: folderLinks store (migration only) | DATA AND STORAGE | P2 | 3 | PWA-03, BAK-03, REL-01A |
| ODI-02B | Linked folder connector with user-triggered refresh and changed-file preview | ONEDRIVE INPUT + SHAREPOINT INPUT | P2 | 3 | ODI-02A, IMP-02B |
| EXP-03 | V2 save picker export to a user-chosen folder | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT | P2 | 3 | EXP-01C, CPL-01B |
| CPL-03 | Copilot grounding V2: Copilot-ready export layout and governance notice | MICROSOFT 365 COPILOT | P2 | 3 | CPL-02, EXP-03 |
| CPL-04 | Agent Builder kit export (user configures the agent manually) | MICROSOFT 365 COPILOT | P2 | 3 | CPL-03 |
| UI-08 | Presentation (screen-share) mode | UI AND ACCESSIBILITY | P2 | 3 | UI-07 |
| DGN-02 | Diagnostics view and content-free diagnostic report | DIAGNOSTICS | P2 | 3 | DAT-03, PWA-03 |
| CLN-03 | Archive superseded docs and remove _archive and sample_data duplicates | REPOSITORY CLEANUP | P2 | 3 | CLN-02 |
| GRA-01 | Record Microsoft 365 V3 prerequisites P1–P8 (BLOCKED) | MICROSOFT GRAPH | P3 | 4 | — |
| GRA-02 | MSAL.js sign-in (auth code + PKCE, delegated) (BLOCKED) | MICROSOFT GRAPH | P3 | 4 | GRA-01 |
| GRA-03 | Microsoft File Picker source connector (V3 input) (BLOCKED) | SHAREPOINT INPUT | P3 | 4 | GRA-02 |
| GRA-04 | Graph destination connector with conflict handling (V3 output) (BLOCKED) | SHAREPOINT OUTPUT | P3 | 4 | GRA-02 |
| CPL-05 | Copilot API, connector or programmatic agent integration (BLOCKED) | MICROSOFT 365 COPILOT | P3 | 4 | GRA-01 |

Counts by priority: P0: 27, P1: 32, P2: 19, P3: 5.
Counts by phase: Phase 0: 10, Phase 1: 23, Phase 2: 30, Phase 3: 15, Phase 4: 5.

## Phase 0 – Baseline, recovery, truthful foundations, tests

### BAS-01 · Record the legacy baseline tag and execution log

| Field | Detail |
|---|---|
| Unique ID | BAS-01 |
| Title | Record the legacy baseline tag and execution log |
| Capability group | BASELINE AND RECOVERY |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | UNKNOWN (no release tags exist except `pwa-assessment-baseline-2026-10-01`) |
| Evidence | `DEPENDENCY_BUILD_REGISTER.md` D-11 (no release process); `ADR_REGISTER.md` ADR-023 (legacy retired via tag). |
| Exact problem | There is no named, durable reference to the last legacy state from which characterization outputs will be captured. |
| Reason this matters | Golden outputs (BAS-03) and the later removal (CLN-02) must point at one immutable commit so the old app stays recoverable. |
| Target behaviour | Annotated tag `legacy-baseline` exists on the commit where BAS-01 runs; `docs/backlog/EXECUTION_LOG.md` exists with a header and the first entry recording the tag and commit hash. |
| Smallest safe change | Create `docs/backlog/EXECUTION_LOG.md` (header: `date \| ID \| status \| tests \| notes`). The **owner** runs `git tag -a legacy-baseline -m "Legacy app before PWA rebuild" <HEAD>`; the model only prints that command. |
| Explicit exclusions | No code change. No push of tags unless the owner runs it. No changes to existing tags. |
| Files expected to change | `docs/backlog/EXECUTION_LOG.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | Git tag `legacy-baseline`. |
| Dependencies | None. |
| Prerequisite decisions | ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | None (documentation). Run `git tag --list legacy-baseline` after the owner creates it. |
| Manual verification | Owner confirms `git show legacy-baseline --stat` shows the expected commit. |
| Acceptance criteria | 1. `docs/backlog/EXECUTION_LOG.md` exists with header and one entry naming the tag and full commit hash. 2. `git tag --list legacy-baseline` prints `legacy-baseline`. |
| Rollback | `git tag -d legacy-baseline` (owner) and revert the log commit. |
| Recommended commit boundary | One commit titled `BAS-01: Record the legacy baseline tag and execution log` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAS-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAS-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | BAS-03, BAS-04 |

### BAS-02 · Copy synthetic sample documents into test fixtures

| Field | Detail |
|---|---|
| Unique ID | BAS-02 |
| Title | Copy synthetic sample documents into test fixtures |
| Capability group | BASELINE AND RECOVERY |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | WORKING (sample data exists in `sample_data/`, used by legacy tests) |
| Evidence | `sample_data/` (10 synthetic files); `TARGET_ARCHITECTURE.md` §24; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §2 (sample data kept as fixtures). |
| Exact problem | The new test suite needs fixture documents that survive removal of legacy folders (CLN-02). |
| Reason this matters | Characterization (BAS-03) and all import/extraction tests need stable, synthetic, non-confidential inputs. |
| Target behaviour | `tests/fixtures/synthetic/` contains byte-identical copies of the 10 files in `sample_data/` plus `README.md` stating they are synthetic and must never be replaced by real project data. |
| Smallest safe change | Copy the 10 files (`cp`, not move). Add `tests/fixtures/synthetic/README.md` listing each file with its SHA-256. |
| Explicit exclusions | Do not move or edit `sample_data/`. Do not add new or real documents. |
| Files expected to change | `tests/fixtures/synthetic/*` (10 copies), `tests/fixtures/synthetic/README.md`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | None. |
| Prerequisite decisions | ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Positive: guarantees test data is synthetic (charter §4). |
| Automated tests | `shasum -a 256 sample_data/* tests/fixtures/synthetic/*` — hashes of each pair match. |
| Manual verification | Open README and confirm it says SYNTHETIC in the first line. |
| Acceptance criteria | 1. Ten fixture files exist and hash-match their `sample_data/` originals. 2. README lists the ten hashes. 3. `git diff --stat` shows only additions under `tests/fixtures/synthetic/`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BAS-02: Copy synthetic sample documents into test fixtures` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAS-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAS-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | BAS-03, IMP-01 |

### BAS-03 · Capture legacy extraction and persona outputs as golden files

| Field | Detail |
|---|---|
| Unique ID | BAS-03 |
| Title | Capture legacy extraction and persona outputs as golden files |
| Capability group | BASELINE AND RECOVERY |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | WORKING (legacy deterministic extraction, by static read) — behaviour to preserve |
| Evidence | `processors/ingestion.py:25` `ingest_file`; `processors/extractors/intelligence_extractor.py:42` `extract_intelligence`; `processors/context_builder.py:27` `build_context`; `personas/engine.py:121` `run_review` (files_only); `personas/deep_dive.py:28` `run_deep_dive`; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §3. |
| Exact problem | The only definition of 'working' extraction behaviour is the legacy Python code, which will be removed (ADR-023). |
| Reason this matters | Ports (MIG-01A, MIG-02A) need an objective parity target; without it, behaviour silently changes. |
| Target behaviour | `tools/legacy-golden.py` (checked-in generator) writes `tests/fixtures/legacy-golden/<fixture-name>.json` for every file in `tests/fixtures/synthetic/`, each containing: legacy commit hash, `ingest_file` sections summary, `extract_intelligence` output per kind, `run_review` (files_only) output for every persona group, `run_deep_dive` (files_only) questions for each persona. Files start with key `"_generated": "GENERATED by tools/legacy-golden.py – do not edit"`. |
| Smallest safe change | Write `tools/legacy-golden.py` that adds the repo root to `sys.path`, sets `PROJECTS_DATA_DIR` to a temp dir, imports the legacy functions directly (no server), runs them with `ai_backend="files_only"`, normalises timestamps/IDs to fixed placeholders, sorts lists, and writes JSON with `indent=2, sort_keys=True`. Run once in a virtualenv with `pip install pyyaml` only, **with the current working directory set to a fresh temporary directory** (legacy `admin/config.py:16` uses a cwd-relative `projects_data`). Normalisation: replace values of keys named `timestamp`, `created_at`, `updated_at`, `generated_at`, and any key ending in `_id` or equal to `id`, with `"<normalised>"`. Call mapping (document it in the script header after reading the legacy signatures): `ingest_file(path).to_dict()` → `build_context([doc_dict])` → for each persona from `list_personas()` call `run_review(<id>, context, ai_backend='files_only')`, and `run_deep_dive(<name>, scope=context.get('scope',''), intelligence=context, active_files=[])` — if a signature or key differs from this, follow the code and record the difference in the header. Add `tests/fixtures/legacy-golden/ACCEPTED_DIFFERENCES.md` (empty table: fixture \| kind \| legacy \| new \| reason). |
| Explicit exclusions | Do not modify any legacy module. Do not call AI backends. Do not start `server.py`. `.pdf`/`.docx` fixtures are out of scope here (none exist). |
| Files expected to change | `tools/legacy-golden.py` (new), `tests/fixtures/legacy-golden/*.json` (new, generated), `tests/fixtures/legacy-golden/ACCEPTED_DIFFERENCES.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | Legacy (read-only): `ingest_file`, `extract_intelligence`, `build_context`, `run_review`, `run_deep_dive`, `list_personas`. |
| Dependencies | BAS-01, BAS-02. |
| Prerequisite decisions | ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes only to a temporary directory during generation; nothing under `projects_data/`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Run `python3 tools/legacy-golden.py` twice; `git diff --exit-code tests/fixtures/legacy-golden/` after the second run proves determinism. |
| Manual verification | Spot-check one golden file: risks listed match sentences visible in the fixture text. |
| Acceptance criteria | 1. One golden JSON per synthetic fixture. 2. Second run produces no diff. 3. No legacy file changed (`git diff --stat` shows only the three new paths). 4. Each JSON records the legacy commit hash. |
| Rollback | Delete the new files via `git revert`. |
| Recommended commit boundary | One commit titled `BAS-03: Capture legacy extraction and persona outputs as golden files` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAS-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAS-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-14 (cwd side effect; explicit normalisation and call mapping). |
| Required by | CLN-02, MIG-01A |

### BAS-04 · Convert persona YAML definitions to JSON for the new app

| Field | Detail |
|---|---|
| Unique ID | BAS-04 |
| Title | Convert persona YAML definitions to JSON for the new app |
| Capability group | MINIFIED CODE MIGRATION |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | WORKING (10 persona YAML files loaded by legacy engine) |
| Evidence | `personas/definitions/*.yaml` (10 files); `MINIFIED_CODE_MIGRATION_STRATEGY.md` §2 (convert to JSON). |
| Exact problem | Persona content is in YAML, which the browser can't read without a parser; the YAML files will be removed at CLN-02. |
| Reason this matters | The persona definitions (focus areas, questions, sections) are core product content. |
| Target behaviour | `app/js/review/personas/<id>.json` per YAML file with identical fields, plus `app/js/review/personas/index.json` listing ids in a stable order. After conversion the JSON files are the hand-maintained source of truth. |
| Smallest safe change | Write `tools/personas-to-json.py` (one-off converter, kept for traceability; header comment states it is not re-run after CLN-02). Run it, review output. |
| Explicit exclusions | No content edits to personas. No review engine code. |
| Files expected to change | `tools/personas-to-json.py` (new), `app/js/review/personas/*.json` (new, 11 files). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | BAS-01. |
| Prerequisite decisions | ADR-012, ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `python3 tools/personas-to-json.py --verify` re-reads YAML and JSON and asserts deep equality (implement the flag). |
| Manual verification | Open two JSON files; confirm `prompt_template` multi-line text is intact. |
| Acceptance criteria | 1. 10 persona JSON files + index.json. 2. `--verify` exits 0. 3. No YAML file changed. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BAS-04: Convert persona YAML definitions to JSON for the new app` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAS-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAS-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CLN-02, MIG-02A |

### TST-01 · Add dev-only Node test tooling and static dev server

| Field | Detail |
|---|---|
| Unique ID | TST-01 |
| Title | Add dev-only Node test tooling and static dev server |
| Capability group | TESTING |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | BROKEN (current test suite cannot run: `TEST_AND_RELEASE_READINESS.md` T-1) |
| Evidence | `TEST_AND_RELEASE_READINESS.md` §2–3; `TARGET_ARCHITECTURE.md` §1 (dev tooling is not a build), §24; ADR-018. |
| Exact problem | There is no working test harness for browser code and no way to serve `app/` locally on a fixed origin. |
| Reason this matters | Every later item depends on runnable unit and browser tests; CI is the owner's only health signal. |
| Target behaviour | `package.json` (`private: true`, `type: module`, `engines: {node: '>=22'}`, devDependency `@playwright/test` pinned to an exact version, scripts `check`, `test:unit`, `test:e2e`, `test`, `serve`), committed `package-lock.json`, `playwright.config.mjs` (projects `chromium` and `webkit`, `webServer` = `node tools/serve-dev.mjs`, baseURL `http://127.0.0.1:8765`), `tools/serve-dev.mjs` (static server of `app/` bound to 127.0.0.1:8765, correct MIME types incl. `.mjs`, `.webmanifest`, refuses paths outside `app/`), `tools/check-syntax.mjs` (runs `node --check` on every `app/**/*.js`, `tools/**/*.mjs`), `tests/unit/serve-dev.test.mjs`. |
| Smallest safe change | Create the files above. `npm run check` = `node tools/check-syntax.mjs`. `test:unit` = `node --test tests/unit/`. `test:e2e` = `playwright test`. Add `node_modules/`, `test-results/`, `playwright-report/` to `.gitignore`. Add `.nvmrc` with `22`. CI uses Node 22 LTS or later. |
| Explicit exclusions | No runtime dependency. No bundler, transpiler, linter framework or TypeScript. Do not touch the Python test setup. |
| Files expected to change | `package.json`, `package-lock.json`, `playwright.config.mjs`, `tools/serve-dev.mjs`, `tools/check-syntax.mjs`, `tests/unit/serve-dev.test.mjs`, `.gitignore`, `.nvmrc`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `serveDev({root, host, port})`, `resolveSafe(root, urlPath)`. |
| Dependencies | None. |
| Prerequisite decisions | ADR-002, ADR-018, ADR-022. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | `serve-dev` must reject `..` traversal (unit test with `/../package.json` and `%2e%2e/`) — the legacy B-1 defect must not be repeated. |
| Automated tests | `npm run test:unit` (`serve-dev.test.mjs`: MIME types, traversal rejected with 404, binds 127.0.0.1 only); `npm run check`. |
| Manual verification | `npm run serve`, open http://127.0.0.1:8765/ — 404 page is fine while `app/` is empty. |
| Acceptance criteria | 1. `npm ci && npm run check && npm run test:unit` pass on a clean clone. 2. Traversal requests return 404. 3. `package.json` has no `dependencies` key (devDependencies only). 4. Lockfile committed. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `TST-01: Add dev-only Node test tooling and static dev server` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `TST-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| TST-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-23 (Node ≥ 22 required for `DecompressionStream('deflate-raw')` used by IMP-06; verified on v24.18.0, not available in older lines). |
| Required by | BLD-01, CHT-01, SEC-01, TST-02 |

### TST-02 · Replace permanently failing CI with the new checks

| Field | Detail |
|---|---|
| Unique ID | TST-02 |
| Title | Replace permanently failing CI with the new checks |
| Capability group | TESTING |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | BROKEN (200/200 recent CI runs failed) |
| Evidence | `DEPENDENCY_BUILD_REGISTER.md` D-7, D-8, D-9; `TEST_AND_RELEASE_READINESS.md` §1. |
| Exact problem | CI is always red (legacy ruff 1,810 findings; pytest collection error), so it gives no signal. |
| Reason this matters | A trustworthy green/red signal is required before any rebuild work (charter §12). |
| Target behaviour | `.github/workflows/ci.yml` runs on push and pull_request to `main` and the working branches: job `check` (`npm ci`, `npm run check`), job `unit` (`npm run test:unit`), job `e2e` (`npx playwright install --with-deps chromium webkit`, `npm run test:e2e`), Node LTS pinned (`actions/setup-node` with explicit major). Legacy lint/pytest jobs removed (legacy is being retired, ADR-023). |
| Smallest safe change | Rewrite `ci.yml` as above; upload Playwright report as artifact on failure. |
| Explicit exclusions | Do not fix legacy lint or tests. No deployment job (REL-01A). |
| Files expected to change | `.github/workflows/ci.yml`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | Workflow jobs `check`, `unit`, `e2e`. |
| Dependencies | TST-01. |
| Prerequisite decisions | ADR-018, ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Push branch; CI run is green (e2e job passes with zero specs or the smoke spec once BLD-01 exists — configure Playwright `--pass-with-no-tests`). |
| Manual verification | Owner opens the Actions tab and sees a green run for the branch. |
| Acceptance criteria | 1. CI run on the branch completes green. 2. No job references `pytest` or `ruff`. 3. Failure of any npm script fails the workflow (verified by a deliberately broken local run of the same commands). |
| Rollback | `git revert` restores the old (red) workflow. |
| Recommended commit boundary | One commit titled `TST-02: Replace permanently failing CI with the new checks` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `TST-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| TST-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | REL-01A |

### SEC-01 · Forbidden-API and fabrication guard checker

| Field | Detail |
|---|---|
| Unique ID | SEC-01 |
| Title | Forbidden-API and fabrication guard checker |
| Capability group | SECURITY AND PRIVACY |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | DOCUMENTED ONLY (rules in `TARGET_ARCHITECTURE.md` §4, §23; none enforced) |
| Evidence | Legacy XSS M-1 (`static/index.html:1112`), heuristic placeholder text C5, external transmission C4; `TARGET_ARCHITECTURE.md` §4 module table, §23. |
| Exact problem | Nothing prevents new code from using HTML sinks, sending data externally, or shipping canned answer text. |
| Reason this matters | Prevents external leakage, XSS and fabricated answers by construction (P0 classes). |
| Target behaviour | `tools/check-forbidden-apis.mjs` scans `app/**/*.{js,html,css}` and fails (exit 1, file:line, rule id) on: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `new Function(`, string `setTimeout/setInterval`, inline `on[a-z]+=` attributes or `<script>` without `src`/`style=` in HTML; `fetch(`, `XMLHttpRequest`, `WebSocket`, `EventSource`, `navigator.sendBeacon` outside allow-list (`app/sw.js`, `app/js/ai/openrouter.js`); any `http(s)://` literal outside allow-list (`https://openrouter.ai` in `app/index.html` CSP and `app/js/ai/openrouter.js`; XML namespace URIs `http://www.w3.org/2000/svg`, `http://www.w3.org/1999/xhtml` and those starting `http://schemas.openxmlformats.org/` anywhere in `app/js` as string constants, never passed to network APIs); `localStorage`/`sessionStorage` outside `app/js/ui/prefs.js`; fabrication phrases (case-insensitive list in the script: `lorem ipsum`, `demo answer`, `sample response`, `as an ai`, `mock data`, `MOCK_DATA`, `placeholder answer`). `app/vendor/**` is skipped (verified by hash instead). |
| Smallest safe change | Implement the script with a rules array `{id, pattern, appliesTo, allow}`; add to `npm run check`; unit tests feed small strings per rule. |
| Explicit exclusions | No AST parser dependency (regex per line is acceptable; document known limits in the script header). Does not scan legacy paths. |
| Files expected to change | `tools/check-forbidden-apis.mjs` (new), `tests/unit/check-forbidden-apis.test.mjs` (new), `package.json` (script `check`). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `RULES`, `scanFile(path, text) → Violation[]`. |
| Dependencies | TST-01. |
| Prerequisite decisions | ADR-008, ADR-010. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Core preventive control for M-1–M-3, M-8 classes. |
| Automated tests | `npm run test:unit` — one passing and one failing sample per rule; `npm run check` passes on the current (empty or skeleton) `app/`. |
| Manual verification | Temporarily add `el.innerHTML = x` to a scratch file under `app/`, run `npm run check`, see failure; remove it. |
| Acceptance criteria | 1. Every listed rule has a failing-sample unit test. 2. `npm run check` exits 1 with file:line on a violation. 3. Allow-listed files pass for allowed uses only. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `SEC-01: Forbidden-API and fabrication guard checker` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `SEC-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| SEC-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-20 (namespace URIs needed by DOCX parsing and SVG would otherwise fail the check). |
| Required by | BLD-01 |

### CHT-01 · Statement, label and citation domain model

| Field | Detail |
|---|---|
| Unique ID | CHT-01 |
| Title | Statement, label and citation domain model |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P0 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | DOCUMENTED ONLY (labels defined in `DATA_AND_STORAGE_ARCHITECTURE.md` §2; legacy has none — C5–C7) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §1, §5; `CURRENT_IMPLEMENTATION_ASSESSMENT.md` C5–C7. |
| Exact problem | There is no shared representation that forces every statement to carry a label, origin and verifiable citations. |
| Reason this matters | Prevents fabricated answers: a `FACT` without a resolvable quote must be impossible to construct. |
| Target behaviour | `app/js/core/labels.js` exports frozen `LABELS` (FACT, INFERENCE, RECOMMENDATION, NOT_FOUND, NEEDS_CONFIRMATION) and `ORIGINS` (deterministic, openrouter, copilot-pasted, user). `app/js/domain/statement.js` exports `makeStatement({text, label, origin, citations, scope})` (throws on unknown label/origin, on FACT with zero citations, on NOT_FOUND without `scope`), `normaliseWhitespace(s)`, `verifyCitation(chunkText, quote) → boolean` (exact match after whitespace normalisation), `downgradeUnverified(statement, chunksById) → statement` (drops citations whose quote is not in the chunk; FACT with no remaining citation → NEEDS_CONFIRMATION). |
| Smallest safe change | Pure ES modules, no DOM, no storage. |
| Explicit exclusions | No UI. No AI code. |
| Files expected to change | `app/js/core/labels.js`, `app/js/domain/statement.js`, `tests/unit/statement.test.mjs` (all new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `LABELS`, `ORIGINS`, `makeStatement`, `verifyCitation`, `downgradeUnverified`, `normaliseWhitespace`. |
| Dependencies | TST-01. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — FACT without citation throws; FACT with citation whose quote isn't in chunk → downgraded; whitespace variants verify; NOT_FOUND requires scope. |
| Manual verification | None (pure module). |
| Acceptance criteria | 1. All listed behaviours covered by passing unit tests. 2. Modules import nothing outside `app/js/core` and `app/js/domain`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CHT-01: Statement, label and citation domain model` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CHT-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CHT-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CHT-03, MIG-01A, UI-04 |

### DOC-01 · Add MIT LICENSE and a truthful README status banner

| Field | Detail |
|---|---|
| Unique ID | DOC-01 |
| Title | Add MIT LICENSE and a truthful README status banner |
| Capability group | DOCUMENTATION |
| Priority | P1 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | DOCUMENTED ONLY (README claims MIT; no LICENSE file) and BROKEN claims (README 'No database', Docker works, CI badge) |
| Evidence | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §11, B7; ADR-016. |
| Exact problem | Licence missing; README describes capabilities that don't work. |
| Reason this matters | Truthful baseline for anyone reading the repo; prerequisite for publication (OD-5). |
| Target behaviour | `LICENSE` with standard MIT text, year 2026, copyright holder as the owner specifies. README starts with a status section: 'Being rebuilt as a browser-only app. The Python app in this repository is legacy, unsupported and not safe to expose on a network. See docs/architecture/TARGET_ARCHITECTURE.md.' Remove the Docker sections and the CI badge; leave other legacy sections under a heading 'Legacy app (being retired)'. |
| Smallest safe change | Add LICENSE; edit README top and remove Docker/compose sections. |
| Explicit exclusions | No full README rewrite (DOC-03). No code. |
| Files expected to change | `LICENSE` (new), `README.md`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | None. |
| Prerequisite decisions | ADR-016, ADR-015, ADR-023. **Owner must state the copyright holder name.** |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | None automated; `grep -n 'docker' README.md` returns nothing. |
| Manual verification | Owner reads the new README top section. |
| Acceptance criteria | 1. LICENSE is the unmodified MIT template with year and holder. 2. README status section present as first section. 3. No Docker instructions or CI badge remain. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DOC-01: Add MIT LICENSE and a truthful README status banner` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DOC-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DOC-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CLN-01, CLN-02 |

### CLN-01 · Remove Docker and Compose files

| Field | Detail |
|---|---|
| Unique ID | CLN-01 |
| Title | Remove Docker and Compose files |
| Capability group | REPOSITORY CLEANUP |
| Priority | P1 |
| Phase | 0 (Baseline, recovery, truthful foundations, tests) |
| Current classification | BROKEN (`Dockerfile` omits required packages; D-1) and out of scope (OD-4) |
| Evidence | `DEPENDENCY_BUILD_REGISTER.md` D-1, D-3, D-6; ADR-015; security B-2 (binds 0.0.0.0). |
| Exact problem | Broken container path that exposes the legacy server on the network if anyone fixes it. |
| Reason this matters | Removes a documented-but-broken start-up path and a network-exposure route. |
| Target behaviour | `Dockerfile`, `docker-compose.yml`, `.dockerignore` deleted. |
| Smallest safe change | `git rm` the three files. |
| Explicit exclusions | No other cleanup. |
| Files expected to change | `Dockerfile`, `docker-compose.yml`, `.dockerignore` (deleted). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | DOC-01 (README no longer references Docker). |
| Prerequisite decisions | ADR-015. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Positive: removes 0.0.0.0 exposure path (B-2). |
| Automated tests | `git ls-files \| grep -i docker` returns nothing. |
| Manual verification | None. |
| Acceptance criteria | 1. The three files are gone. 2. No remaining reference to `docker` in README or workflows. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CLN-01: Remove Docker and Compose files` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CLN-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CLN-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

## Phase 1 – Maintainable shell, reliable storage, import, provenance

### BLD-01 · Application shell skeleton with CSP and file:// guard

| Field | Detail |
|---|---|
| Unique ID | BLD-01 |
| Title | Application shell skeleton with CSP and file:// guard |
| Capability group | HUMAN-READABLE SOURCE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`TARGET_ARCHITECTURE.md` §2–3) |
| Evidence | Legacy UIs are 292 KB / 108 KB inline-script monoliths (`CURRENT_IMPLEMENTATION_ASSESSMENT.md` A2, U1–U3); OD-2. |
| Exact problem | No maintainable application source exists for the target. |
| Reason this matters | Restores maintainable source: every later UI item builds on this shell. |
| Target behaviour | `app/index.html` (no inline script/style; `<meta http-equiv="Content-Security-Policy">` exactly as `TARGET_ARCHITECTURE.md` §23 **without** the Trusted Types directives (added in SEC-02); `<div id="boot-msg">` visible by default saying 'Starting… If this message stays, open the app through its web address or the start file — opening the file directly is not supported.'; `<main id="app">`; `<script type="module" src="./js/main.js">`), `app/version.js` (`APP_VERSION = "0.1.0"`, `SCHEMA_VERSION = 1`), `app/js/main.js` (hides `#boot-msg`, renders app title and version), `app/css/tokens.css`, `app/css/base.css`, `app/css/components.css` (system font stack, light/dark via `prefers-color-scheme`, `prefers-reduced-motion`). All paths relative (ADR-024). `tests/e2e/helpers.mjs` exporting `openApp(page)` that fails the test on any `securitypolicyviolation` or console error. `tests/e2e/smoke.spec.mjs`. |
| Smallest safe change | Create the files; keep `main.js` under 40 lines. |
| Explicit exclusions | No storage, routing, views, service worker or manifest. |
| Files expected to change | `app/index.html`, `app/version.js`, `app/js/main.js`, `app/css/tokens.css`, `app/css/base.css`, `app/css/components.css`, `tests/e2e/helpers.mjs`, `tests/e2e/smoke.spec.mjs` (all new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `APP_VERSION`, `SCHEMA_VERSION`, `openApp`. |
| Dependencies | TST-01, SEC-01. |
| Prerequisite decisions | ADR-002, ADR-010, ADR-024. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | CSP active from the first page. |
| Automated tests | `npm run check`; `npm run test:e2e -- tests/e2e/smoke.spec.mjs` — title and version visible, `#boot-msg` hidden, zero CSP violations, zero console errors (chromium + webkit). |
| Manual verification | `npm run serve`, open http://127.0.0.1:8765/ in Edge: version shows. Open `app/index.html` via file:// — the boot message stays visible. |
| Acceptance criteria | 1. Smoke e2e passes in both projects. 2. `npm run check` passes (no inline script/style). 3. No absolute URL other than the CSP's `https://openrouter.ai`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BLD-01: Application shell skeleton with CSP and file:// guard` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BLD-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BLD-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | BLD-02, PWA-01, SEC-02, UI-01 |

### SEC-02 · Enforce Trusted Types with a single script-URL policy

| Field | Detail |
|---|---|
| Unique ID | SEC-02 |
| Title | Enforce Trusted Types with a single script-URL policy |
| Capability group | SECURITY AND PRIVACY |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`TARGET_ARCHITECTURE.md` §23) |
| Evidence | Legacy M-1/M-3; `TARGET_ARCHITECTURE.md` §23 (policy `pdae-script-url`). |
| Exact problem | Without Trusted Types, an accidental HTML sink would execute injected markup in Chromium. |
| Reason this matters | Defence in depth against XSS from imported document content. |
| Target behaviour | CSP gains `require-trusted-types-for 'script'; trusted-types pdae-script-url`. `app/js/core/trusted-types.js` exports `scriptURL(path)` that returns a `TrustedScriptURL` (or the plain string where `window.trustedTypes` is undefined) only for paths in a frozen allow-list `['./sw.js']`, throwing otherwise. Imported first by `main.js`. |
| Smallest safe change | Edit CSP meta in `app/index.html`; add module; import in `main.js`. |
| Explicit exclusions | No HTML policy. No changes to view code. |
| Files expected to change | `app/index.html`, `app/js/core/trusted-types.js` (new), `app/js/main.js`, `tests/e2e/trusted-types.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `scriptURL`, policy name `pdae-script-url`. |
| Dependencies | BLD-01. |
| Prerequisite decisions | ADR-010. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/trusted-types.spec.mjs` — chromium: `document.body.innerHTML = '<b>x</b>'` via `page.evaluate` throws TypeError; `scriptURL('./evil.js')` throws; webkit: test skipped with reason 'Trusted Types not supported'. |
| Manual verification | In Edge devtools console: `document.body.innerHTML='x'` throws a Trusted Types error. |
| Acceptance criteria | 1. Chromium e2e passes. 2. Smoke test still passes with no CSP violation. 3. Allow-list contains only `./sw.js`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `SEC-02: Enforce Trusted Types with a single script-URL policy` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `SEC-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| SEC-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | PWA-02B |

### UI-01 · Safe DOM builder

| Field | Detail |
|---|---|
| Unique ID | UI-01 |
| Title | Safe DOM builder |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (string templates into `innerHTML`, escaping incomplete — M-1); DOCUMENTED ONLY in target |
| Evidence | `static/index.html:423-426` `escHtml` misses `'`; `static/index.html:1112`; `TARGET_ARCHITECTURE.md` §23. |
| Exact problem | UI code needs a way to build DOM from untrusted strings without HTML parsing. |
| Reason this matters | All views use it; it is the structural XSS fix. |
| Target behaviour | `app/js/ui/dom.js` exports `h(tag, props, ...children)` (props: `class`, `id`, `attrs` object via `setAttribute` with an allow-list that rejects `on*`, `style`, `srcdoc`, and `href`/`src` values not starting with `./`, `#`, `blob:` or `https://openrouter.ai`; `on` object of event listeners via `addEventListener`; children: strings become text nodes, arrays flattened, null skipped), `clear(el)`, `replace(el, ...children)`. |
| Smallest safe change | Implement the module; e2e spec loads it in the page and asserts behaviour. |
| Explicit exclusions | No templating language, no virtual DOM. |
| Files expected to change | `app/js/ui/dom.js` (new), `tests/e2e/dom.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `h`, `clear`, `replace`. |
| Dependencies | BLD-01. |
| Prerequisite decisions | ADR-010. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/dom.spec.mjs` — string `<img src=x onerror=alert(1)>` renders as literal text; `attrs:{onclick:'x'}` throws; `href:'javascript:alert(1)'` throws; listeners fire. |
| Manual verification | None. |
| Acceptance criteria | 1. All listed cases pass in chromium and webkit. 2. `npm run check` passes. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-01: Safe DOM builder` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DGN-01, UI-02 |

### UI-02 · App frame: store, hash router, header, live region, skip link

| Field | Detail |
|---|---|
| Unique ID | UI-02 |
| Title | App frame: store, hash router, header, live region, skip link |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`TARGET_ARCHITECTURE.md` §5, §28) |
| Evidence | Legacy has ~70 clickable non-button elements (`CURRENT_IMPLEMENTATION_ASSESSMENT.md` §3). |
| Exact problem | No navigation or state container exists for views. |
| Reason this matters | Reliable daily use requires predictable navigation and keyboard access. |
| Target behaviour | `app/js/ui/store.js` (`getState()`, `update(patch)`, `subscribe(fn) → unsubscribe`), `app/js/ui/router.js` (hash routes `#/projects`, `#/project/:id/:tab`, `#/settings`, `#/trash`, `#/help`; unknown → `#/projects`), `app/js/ui/a11y.js` (`announce(text)` writing to `aria-live=polite` region; focus management helper `focusHeading(view)`), header with nav `<button>`s and a skip link; each route renders a view module from `app/js/ui/views/`; views not yet built render 'This part isn't built yet.' (no fake data). |
| Smallest safe change | Create modules; `main.js` mounts frame and router. |
| Explicit exclusions | No storage access, no real views. |
| Files expected to change | `app/js/ui/store.js`, `app/js/ui/router.js`, `app/js/ui/a11y.js`, `app/js/ui/views/not-built.js` (new); `app/js/main.js`; `app/css/components.css`; `tests/unit/store.test.mjs`, `tests/e2e/navigation.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `getState`, `update`, `subscribe`, `route`, `announce`, `focusHeading`. |
| Dependencies | UI-01. |
| Prerequisite decisions | ADR-002. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` (store); `npm run test:e2e -- tests/e2e/navigation.spec.mjs` — keyboard-only: Tab to skip link, Enter moves focus to main; nav buttons change hash and focus the view `<h1>`. |
| Manual verification | Navigate the app with keyboard only in Edge. |
| Acceptance criteria | 1. Unit and e2e pass. 2. Every interactive element is a `<button>` or `<a>`. 3. Placeholder views contain no sample data. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-02: App frame: store, hash router, header, live region, skip link` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DAT-05, UI-03 |

### DGN-01 · Diagnostics log, error codes and visible error banner

| Field | Detail |
|---|---|
| Unique ID | DGN-01 |
| Title | Diagnostics log, error codes and visible error banner |
| Capability group | DIAGNOSTICS |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (pervasive `except Exception: pass`; M-7) |
| Evidence | `services/project.py:41,52,71,89,113,188,199,222`; `TARGET_ARCHITECTURE.md` §22. |
| Exact problem | Failures must be visible and diagnosable without logging user content. |
| Reason this matters | Charter §5 'visible storage failures', §1 'observable failures'. |
| Target behaviour | `app/js/diagnostics/errors.js` (frozen catalogue `{code, title, help}` incl. `STO-OPEN-FAIL`, `STO-QUOTA`, `STO-WRITE-FAIL`, `MIG-FAIL`, `IMP-READ-FAIL`, `IMP-PARSE-FAIL`, `BAK-INVALID`, `AI-NET`, `AI-HTTP`), `app/js/diagnostics/log.js` (`log(level, code, module, refs)` — **no free-text message parameter**; the human-readable text comes from the `ERRORS` catalogue by `code`; ring buffer 500 in memory; **rejects** any `refs` key not in allow-list `projectId, sourceId, itemId, reviewId, count, bytes, status` and any `refs` value that is not a number or an ID matching `^[a-z]+_[0-9a-f-]+$`; `getEvents()`; `onEvent(fn)` hook for DAT-03 mirroring), `app/js/ui/components/banner.js` (`showError(code, detail?)` rendering title + help + 'Copy diagnostic code' button; `role=alert`). |
| Smallest safe change | Implement modules; wire `window.onerror`/`unhandledrejection` in `main.js` to `log` + `showError('APP-UNEXPECTED')`. |
| Explicit exclusions | No persistence (DAT-03), no diagnostics view (DGN-02). |
| Files expected to change | `app/js/diagnostics/errors.js`, `app/js/diagnostics/log.js`, `app/js/ui/components/banner.js`, `tests/unit/log.test.mjs`, `tests/e2e/error-banner.spec.mjs` (new); `app/js/main.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `ERRORS`, `log`, `getEvents`, `onEvent`, `showError`. |
| Dependencies | UI-01. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Positive: content-free logging by construction (charter §4). |
| Automated tests | `npm run test:unit` — refs key `text` rejected; refs value 'free text' rejected; buffer capped at 500. `npm run test:e2e -- tests/e2e/error-banner.spec.mjs` — thrown error in a test hook shows banner with code. |
| Manual verification | Trigger the test hook in devtools; read banner text. |
| Acceptance criteria | 1. Tests pass. 2. `log` signature has no free-text parameter, so document text can't be logged by construction. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DGN-01: Diagnostics log, error codes and visible error banner` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DGN-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DGN-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-11 (testable no-content logging), V-12 (dependency on UI-01 only). |
| Required by | DAT-01 |

### DAT-01 · IndexedDB open, schema v1, migration runner and downgrade guard

| Field | Detail |
|---|---|
| Unique ID | DAT-01 |
| Title | IndexedDB open, schema v1, migration runner and downgrade guard |
| Capability group | DATA AND STORAGE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`DATA_AND_STORAGE_ARCHITECTURE.md` §3, §7) |
| Evidence | Legacy has no schema version (`CURRENT_IMPLEMENTATION_ASSESSMENT.md` S2); charter §5. |
| Exact problem | No local store exists; future schema changes need safe, atomic upgrades. |
| Reason this matters | Prevents data loss on upgrade; restores recoverable storage. |
| Target behaviour | `app/js/storage/schema.js` (store/index definitions exactly per `DATA_AND_STORAGE_ARCHITECTURE.md` §3 table), `app/js/storage/migrations/index.js` (ordered list), `app/js/storage/migrations/0001-initial.js` (`{from:0,to:1,up(db, tx, log)}` creating all stores/indexes and `meta` record), `app/js/storage/db.js` (`openDb({name='pdae', version=SCHEMA_VERSION})` running migrations inside `upgradeneeded`; any thrown error aborts the upgrade and rejects with `MIG-FAIL`; if existing DB version > app version → resolve `{db, readOnly:true}` and show banner 'Data was saved by a newer version… read-only'; `onblocked` → banner). Test-only hook `window.__pdaeTest` gated by `?test=1` query param exposing `openDb` for e2e. |
| Smallest safe change | Implement modules; open DB at start in `main.js`; on failure `showError`. |
| Explicit exclusions | No repos or UI beyond banners. |
| Files expected to change | `app/js/storage/schema.js`, `app/js/storage/db.js`, `app/js/storage/migrations/index.js`, `app/js/storage/migrations/0001-initial.js`, `tests/e2e/storage-open.spec.mjs` (new); `app/js/main.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `openDb`, `MIGRATIONS`, `STORES`. |
| Dependencies | DGN-01. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Creates database `pdae` version 1 in the user's browser profile. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/storage-open.spec.mjs` — fresh profile creates all stores; a test migration that throws leaves version unchanged and shows `MIG-FAIL`; pre-creating `pdae` at version 99 opens read-only with banner. |
| Manual verification | Edge devtools → Application → IndexedDB shows `pdae` with the listed stores. |
| Acceptance criteria | 1. Store and index names match the architecture table exactly. 2. Failing migration is atomic (version unchanged). 3. Newer-version DB opens read-only. |
| Rollback | `git revert`; testers delete the `pdae` database in devtools (no real user data exists yet). |
| Recommended commit boundary | One commit titled `DAT-01: IndexedDB open, schema v1, migration runner and downgrade guard` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DAT-02 |

### DAT-02 · Record validators and generic repositories with optimistic concurrency

| Field | Detail |
|---|---|
| Unique ID | DAT-02 |
| Title | Record validators and generic repositories with optimistic concurrency |
| Capability group | DATA AND STORAGE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §3–4; legacy silent last-write-wins (M-7). |
| Exact problem | Views need safe read/write access with validation and no silent overwrite. |
| Reason this matters | Prevents silent overwrite and corrupt writes. |
| Target behaviour | `app/js/domain/validate.js` (validators for `project`, `settings`, `meta`; each returns `{ok, errors[]}`; every record requires `id`, `schema`, `updatedAt`), `app/js/storage/repos/make-repo.js` (`makeRepo(storeName, validate)` → `get`, `list(indexName?, key?)`, `put(record, {expectUpdatedAt})` failing with `STO-CONFLICT` if stored `updatedAt` differs, `withTx(storeNames, mode, fn)` single-transaction helper), `app/js/storage/repos/projects.js`, `settings.js`, `app/js/core/ids.js` (`newId(prefix)` using `crypto.randomUUID`), `app/js/core/time.js` (`nowIso()`). **Schema-evolution rule:** validators must accept records missing any field added after schema v1 (new fields optional with defaults applied on read) and must ignore unknown fields; making a field required, renaming or changing its type requires a new migration item with `upRecord`. |
| Smallest safe change | Implement; add `STO-CONFLICT` to error catalogue. |
| Explicit exclusions | Validators for sources/chunks/items etc. are added by their own items. |
| Files expected to change | `app/js/domain/validate.js`, `app/js/storage/repos/make-repo.js`, `app/js/storage/repos/projects.js`, `app/js/storage/repos/settings.js`, `app/js/core/ids.js`, `app/js/core/time.js`, `tests/unit/validate.test.mjs`, `tests/e2e/repo.spec.mjs` (new); `app/js/diagnostics/errors.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `makeRepo`, `withTx`, `validateProject`, `newId`, `nowIso`. |
| Dependencies | DAT-01. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Defines write semantics; no schema change. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` validators; `npm run test:e2e -- tests/e2e/repo.spec.mjs` — stale `expectUpdatedAt` rejects with `STO-CONFLICT`; invalid record rejected, nothing written. |
| Manual verification | None. |
| Acceptance criteria | 1. Tests pass. 2. No code outside `app/js/storage/` opens IndexedDB transactions (grep `transaction(`). 3. Unit test: a v1 record lacking every later optional field validates; a record with an extra unknown field validates. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-02: Record validators and generic repositories with optimistic concurrency` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-13 (prevents quarantine floods after updates). |
| Required by | DAT-03, DAT-04, DAT-05, IMP-01, UI-03 |

### DAT-03 · Quarantine for unreadable records and diagnostics persistence

| Field | Detail |
|---|---|
| Unique ID | DAT-03 |
| Title | Quarantine for unreadable records and diagnostics persistence |
| Capability group | DATA AND STORAGE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`DATA_AND_STORAGE_ARCHITECTURE.md` §9) |
| Evidence | Charter §5 'corruption preservation'; legacy swallows errors (M-7). |
| Exact problem | Corrupt or invalid stored records must never be silently dropped or crash the app. |
| Reason this matters | Prevents data loss. |
| Target behaviour | `make-repo.js` read paths validate each record; invalid → `app/js/storage/quarantine.js` `quarantine(storeName, record, errors)` copies to `quarantine` store and deletes from origin store in one transaction, logs `STO-QUARANTINED` (count only) and shows banner 'N item(s) couldn't be read and were set aside. Nothing was deleted.' `log.js` `onEvent` mirrors events to `diagnostics` store (ring buffer trimmed to 500 by `seq`). |
| Smallest safe change | Implement; add error code. |
| Explicit exclusions | No quarantine UI list (DGN-02). |
| Files expected to change | `app/js/storage/quarantine.js` (new), `app/js/storage/repos/make-repo.js`, `app/js/diagnostics/log.js`, `app/js/diagnostics/errors.js`, `tests/e2e/quarantine.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `quarantine`, `listQuarantine`, diagnostics mirror. |
| Dependencies | DAT-02. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Uses existing `quarantine` and `diagnostics` stores. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/quarantine.spec.mjs` — inject an invalid `projects` record via raw IndexedDB; listing projects moves it to quarantine, banner shown, original raw object preserved byte-for-byte. |
| Manual verification | None. |
| Acceptance criteria | 1. Test passes. 2. Diagnostics store never exceeds 500 records (test inserts 600 events). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-03: Quarantine for unreadable records and diagnostics persistence` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DAT-06A, DGN-02 |

### DAT-04 · Cross-tab write lock, change broadcast and version-change handling

| Field | Detail |
|---|---|
| Unique ID | DAT-04 |
| Title | Cross-tab write lock, change broadcast and version-change handling |
| Capability group | DATA AND STORAGE |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`TARGET_ARCHITECTURE.md` §3; `DATA_AND_STORAGE_ARCHITECTURE.md` §4) |
| Evidence | Two open tabs could interleave writes; an upgrade could be blocked by an old tab. |
| Exact problem | Concurrent tabs can corrupt multi-step writes or block upgrades. |
| Reason this matters | Reliable daily use; prevents data loss. |
| Target behaviour | `withTx(..., 'readwrite', fn)` wraps in `navigator.locks.request('pdae-write', …)`; after commit posts `{type:'changed', stores}` on `BroadcastChannel('pdae')`; `app/js/storage/db.js` sets `db.onversionchange = () => { db.close(); showError('STO-VERSIONCHANGE') }` ('The app was updated in another tab. Reload to continue.' with Reload button); store subscribers re-query on broadcast. |
| Smallest safe change | Implement in storage layer; add error code. |
| Explicit exclusions | No UI beyond the banner. |
| Files expected to change | `app/js/storage/repos/make-repo.js`, `app/js/storage/db.js`, `app/js/diagnostics/errors.js`, `tests/e2e/multitab.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `withTx`, channel `pdae`, lock `pdae-write`. |
| Dependencies | DAT-02. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/multitab.spec.mjs` — two pages in one context: write in A triggers refresh in B; opening a higher test version in A shows the banner in B. |
| Manual verification | Open two Edge tabs; create a project in one; it appears in the other. |
| Acceptance criteria | 1. Test passes in chromium and webkit. 2. No write path bypasses `withTx`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-04: Cross-tab write lock, change broadcast and version-change handling` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### DAT-05 · Persistent storage request, usage display and quota error handling

| Field | Detail |
|---|---|
| Unique ID | DAT-05 |
| Title | Persistent storage request, usage display and quota error handling |
| Capability group | DATA AND STORAGE |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (`DATA_AND_STORAGE_ARCHITECTURE.md` §4–5) |
| Evidence | Charter §5 'storage usage'; Safari eviction risk (`TARGET_ARCHITECTURE.md` §27). |
| Exact problem | Users can't see whether storage is protected or how full it is; quota errors would be silent. |
| Reason this matters | Prevents data loss from eviction/quota. |
| Target behaviour | `app/js/storage/usage.js` (`requestPersistence()` on first data write, stored in `meta.persisted`; `getUsage()` via `navigator.storage.estimate()`); minimal `app/js/ui/views/settings.js` section 'Storage' showing used/available, 'Protected from automatic clean-up: Yes/No' with plain explanation; any `QuotaExceededError` in `withTx` → `STO-QUOTA` banner listing options (Download backup, Empty trash). |
| Smallest safe change | Implement; route `#/settings` to the view. |
| Explicit exclusions | Backup button behaviour is BAK-01 (show disabled 'Coming soon' is not allowed — omit the button until BAK-01). |
| Files expected to change | `app/js/storage/usage.js` (new), `app/js/ui/views/settings.js` (new), `app/js/storage/repos/make-repo.js`, `app/js/ui/router.js`, `tests/e2e/storage-usage.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `requestPersistence`, `getUsage`, `renderSettings`. |
| Dependencies | DAT-02, UI-02. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/storage-usage.spec.mjs` — settings shows numeric usage; mocked `QuotaExceededError` (test hook) shows `STO-QUOTA`. |
| Manual verification | Edge: Settings shows persistence Yes after creating a project (Edge grants for installed/engaged sites; record actual value). |
| Acceptance criteria | 1. Test passes. 2. Persistence result recorded in `meta`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-05: Persistent storage request, usage display and quota error handling` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-05` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-05 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DAT-06B |

### UI-03 · Projects list and create/rename project

| Field | Detail |
|---|---|
| Unique ID | UI-03 |
| Title | Projects list and create/rename project |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (target); legacy equivalent PARTIAL with max-project limits (`services/project.py:97-105`) |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §2; ADR-012. |
| Exact problem | Users need to create and choose projects; nothing else works without one. |
| Reason this matters | Reliable daily use. |
| Target behaviour | `app/js/ui/views/projects.js`: list active projects (name, updated date, source count once sources exist), 'New project' dialog (`<dialog>`, name required, 1–120 chars), rename; `#/project/:id/overview` shows name and empty-state guidance 'Add documents to start'. No project limit. |
| Smallest safe change | Implement view + `app/js/ui/components/dialog.js` helper (`openDialog({title, body, actions})` with focus return). |
| Explicit exclusions | No delete (DAT-06A, DAT-06B). No sample data. |
| Files expected to change | `app/js/ui/views/projects.js`, `app/js/ui/views/project.js`, `app/js/ui/components/dialog.js` (new); `app/js/ui/router.js`; `tests/e2e/projects.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderProjects`, `renderProject`, `openDialog`. |
| Dependencies | DAT-02, UI-02. |
| Prerequisite decisions | ADR-012. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes `projects` records. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/projects.spec.mjs` — create, rename, persists across reload, keyboard-only flow, name with `<script>` shows literally. |
| Manual verification | Create two projects in Edge, reload, both present. |
| Acceptance criteria | 1. Test passes in chromium and webkit. 2. Reload preserves projects. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-03: Projects list and create/rename project` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DAT-06A, IMP-02B |

### DAT-06A · Trash: move to Trash, Undo, restore from Trash view

| Field | Detail |
|---|---|
| Unique ID | DAT-06A |
| Title | Trash: move to Trash, Undo, restore from Trash view |
| Capability group | DATA AND STORAGE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (irreversible `shutil.rmtree`, silent archive eviction — H-6, M-5) |
| Evidence | `services/project.py:184`, `:205-243`; `DATA_AND_STORAGE_ARCHITECTURE.md` §6. |
| Exact problem | Deletion must be reversible by default and never silent. |
| Reason this matters | Prevents data loss. |
| Target behaviour | `app/js/storage/trash.js`: `trashProject(id)` moves the project and all its child records from exactly these stores: `sources`, `chunks`, `items`, `snapshots`, `reviews`, `answers`, `drafts`, `exports` (and `folderLinks` once ODI-02A exists) into one `trash` entry in one transaction; `trashRecord(store, id)` for single records; `restoreFromTrash(trashId)`. Undo toast (`app/js/ui/components/toast.js`). `app/js/ui/views/trash.js` lists entries with Restore. |
| Smallest safe change | Implement. |
| Explicit exclusions | No permanent delete, expiry or reset (DAT-06B). |
| Files expected to change | `app/js/storage/trash.js`, `app/js/ui/components/toast.js`, `app/js/ui/views/trash.js`, `tests/e2e/trash.spec.mjs` (new); `app/js/ui/views/projects.js`, `app/js/ui/router.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `trashProject`, `trashRecord`, `restoreFromTrash`. |
| Dependencies | UI-03, DAT-03. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Uses `trash` store; no schema change. |
| Security and privacy impact | Positive: no silent deletion paths. |
| Automated tests | `npm run test:e2e -- tests/e2e/trash.spec.mjs` — trash + undo and trash + restore both reproduce identical records in every listed store. |
| Manual verification | Delete and undo a project in Edge. |
| Acceptance criteria | 1. Round trip identical. 2. No record deleted outright. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-06A: Trash: move to Trash, Undo, restore from Trash view` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-06A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-06A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from DAT-06 by validation V-07. |
| Required by | DAT-06B, MIG-01B |

### DAT-06B · Permanent delete with typed confirmation, expiry prompt and app reset

| Field | Detail |
|---|---|
| Unique ID | DAT-06B |
| Title | Permanent delete with typed confirmation, expiry prompt and app reset |
| Capability group | DATA AND STORAGE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (irreversible `shutil.rmtree`, silent archive eviction — H-6, M-5) |
| Evidence | `services/project.py:184`, `:205-243`; `DATA_AND_STORAGE_ARCHITECTURE.md` §6. |
| Exact problem | Deletion must be reversible by default and never silent. |
| Reason this matters | Prevents data loss. |
| Target behaviour | `app/js/ui/components/confirm-typed.js`; Trash view 'Delete permanently' (typed `DELETE`) calling `emptyTrash(ids)`; start-up check listing entries older than `settings.trashRetentionDays` (30) with 'Remove now / Keep 30 more days' (never automatic); Settings → Danger zone 'Reset app' (typed `RESET`; deletes `pdae` DB only). Until BAK-01 exists the dialogs state 'There is no backup feature yet; this cannot be undone'. |
| Smallest safe change | Implement. |
| Explicit exclusions | Backup buttons (BAK-01). |
| Files expected to change | `app/js/ui/components/confirm-typed.js`, `tests/e2e/trash-permanent.spec.mjs` (new); `app/js/storage/trash.js`, `app/js/ui/views/trash.js`, `app/js/ui/views/settings.js`, `app/js/main.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `emptyTrash`, `expiredEntries`, `confirmTyped`, `resetApp`. |
| Dependencies | DAT-06A, DAT-05. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Uses `trash` store; no schema change. |
| Security and privacy impact | Positive: no silent deletion paths. |
| Automated tests | `npm run test:e2e -- tests/e2e/trash-permanent.spec.mjs` — wrong word keeps data; expired entries prompt and nothing auto-deleted; reset only after `RESET`. |
| Manual verification | Delete and undo a project in Edge. |
| Acceptance criteria | 1. Only `emptyTrash` and reset delete user records (grep `.delete(` / `deleteDatabase` in `app/js`). 2. Tests pass. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-06B: Permanent delete with typed confirmation, expiry prompt and app reset` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-06B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-06B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from DAT-06 by validation V-07. |
| Required by | BAK-01 |

### BAK-01 · Backup export (format v1) with checksums

| Field | Detail |
|---|---|
| Unique ID | BAK-01 |
| Title | Backup export (format v1) with checksums |
| Capability group | BACKUP AND RESTORE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (legacy has no backup — H-6) |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §8; charter §5. |
| Exact problem | Users have no way to keep a copy of their data outside the browser. |
| Reason this matters | Prevents data loss; required before any migration or update. |
| Target behaviour | `app/js/core/hash.js` (`sha256Hex(bytes\|string)` via `crypto.subtle`; `canonicalJson(value)` with sorted keys), `app/js/storage/backup.js` (`buildBackup({scope, projectIds, includeOriginals}) → Blob` exactly per §8 format; blobs base64 with own sha256; `recordHashes`; `checksum`; excludes `diagnostics`, `quarantine`), `app/js/exports/download.js` (`downloadBlob(blob, fileName)` via `<a download>` + revokeObjectURL), Settings → Backup: 'Download backup' (all), 'Text only (smaller)' checkbox; project page 'Download project backup'; `meta.lastBackupAt` updated. File name `pdae-backup-<yyyymmdd-hhmm>.pdae-backup.json`. Danger-zone and permanent-delete dialogs gain 'Download backup first'. |
| Smallest safe change | Implement; replace the DAT-06B interim wording. |
| Explicit exclusions | No restore (BAK-02). No ZIP format. |
| Files expected to change | `app/js/core/hash.js`, `app/js/storage/backup.js`, `app/js/exports/download.js`, `tests/unit/hash.test.mjs`, `tests/e2e/backup.spec.mjs` (new); `app/js/ui/views/settings.js`, `app/js/ui/views/project.js`, `app/js/ui/views/trash.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `sha256Hex`, `canonicalJson`, `buildBackup`, `downloadBlob`. |
| Dependencies | DAT-06B. |
| Prerequisite decisions | ADR-004. |
| External approvals | None. |
| Data-boundary impact | Creates a file on the user's device only on click; the user decides where it goes (a OneDrive folder would change the boundary — notice added in EXP-01C). |
| Storage or migration impact | Reads all stores; writes `meta.lastBackupAt`. |
| Security and privacy impact | Backup must never contain secrets (none are stored — test asserts no key named like `key`, `token`, `secret` appears). |
| Automated tests | `npm run test:unit` canonicalJson/sha256 vectors; `npm run test:e2e -- tests/e2e/backup.spec.mjs` — download captured by Playwright, JSON parses, checksum and every recordHash verify, counts match. |
| Manual verification | Download a backup in Edge; open it in a text editor; first keys are `format`, `formatVersion`. |
| Acceptance criteria | 1. Tests pass. 2. Checksum recomputation matches. 3. `lastBackupAt` shown in Settings. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BAK-01: Backup export (format v1) with checksums` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAK-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAK-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | BAK-02, EXP-01A |

### BAK-02 · Restore: validate, preview and add as copies

| Field | Detail |
|---|---|
| Unique ID | BAK-02 |
| Title | Restore: validate, preview and add as copies |
| Capability group | BACKUP AND RESTORE |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §8 Restore steps 1–4 ('Add as copies'), 6. |
| Exact problem | A backup is useless without a safe way to bring it back. |
| Reason this matters | Prevents data loss; enables moving between hosted and local origins (§10). |
| Target behaviour | `app/js/storage/restore.js` (`readBackup(file) → {ok, errors, summary}` checking format, formatVersion, checksum, recordHashes, schemaVersion ≤ app; `restoreAsCopies(backup)` remapping all IDs for projects that already exist, writing each project in one transaction), `app/js/ui/views/restore.js` (file input + drop; validation result list; preview of counts, project names, backup date/app version, conflicts; button 'Add as copies'; result summary). Invalid backups: nothing written, failing check named (`BAK-INVALID`). |
| Smallest safe change | Implement; Settings → Backup gains 'Restore from backup'. |
| Explicit exclusions | Replace modes and older-schema migration (BAK-03). |
| Files expected to change | `app/js/storage/restore.js`, `app/js/ui/views/restore.js`, `tests/e2e/restore.spec.mjs`, `tests/fixtures/backups/` (valid + tampered samples generated by the test itself) (new); `app/js/ui/views/settings.js`, `app/js/ui/router.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `readBackup`, `restoreAsCopies`. |
| Dependencies | BAK-01. |
| Prerequisite decisions | ADR-004. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes restored records; never modifies existing ones. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/restore.spec.mjs` — round trip backup → reset → restore equals original (deep-equal per store, ignoring nothing); tampered byte → rejected with named check, zero writes; restoring twice yields two copies. |
| Manual verification | Backup in Edge, reset, restore, verify projects. |
| Acceptance criteria | 1. Round-trip deep equality. 2. Tampered file writes nothing. 3. Existing data never modified. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BAK-02: Restore: validate, preview and add as copies` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAK-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAK-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | BAK-03, TST-03, UI-07 |

### BAK-03 · Restore replace modes and older-schema restores

| Field | Detail |
|---|---|
| Unique ID | BAK-03 |
| Title | Restore replace modes and older-schema restores |
| Capability group | BACKUP AND RESTORE |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §8 step 4–5, rollback instructions. |
| Exact problem | Users sometimes need to replace current data with a backup, including backups from older versions. |
| Reason this matters | Supports rollback; prevents silent overwrite. |
| Target behaviour | Restore view adds 'Replace matching projects' (typed `REPLACE`) and 'Replace everything' (typed `REPLACE ALL`), both preceded by a 'Download backup of current data first' step; `restore.js` runs older-`schemaVersion` records through the migration `upRecord` functions in memory before writing (each migration file gains an optional `upRecord(storeName, record)`). |
| Smallest safe change | Implement; add `upRecord` no-op to `0001-initial.js`. |
| Explicit exclusions | No merging at record level. |
| Files expected to change | `app/js/storage/restore.js`, `app/js/ui/views/restore.js`, `app/js/storage/migrations/0001-initial.js`, `tests/e2e/restore-replace.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `restoreReplace`, `upRecord`. |
| Dependencies | BAK-02. |
| Prerequisite decisions | ADR-004. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Replace modes delete and rewrite projects in one transaction per project. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/restore-replace.spec.mjs` — replace requires typed word; pre-backup offered; after replace, data equals backup. |
| Manual verification | Replace everything in Edge with a saved backup. |
| Acceptance criteria | 1. No replace without typed confirmation. 2. Pre-backup step shown every time. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BAK-03: Restore replace modes and older-schema restores` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BAK-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BAK-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | DOC-02, ODI-02A, PWA-03 |

### IMP-01 · Import pipeline: text parser, chunker, provenance and hashing (pure)

| Field | Detail |
|---|---|
| Unique ID | IMP-01 |
| Title | Import pipeline: text parser, chunker, provenance and hashing (pure) |
| Capability group | FILE IMPORT |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (server-path ingest H-4; stem-collision overwrite M-6; no provenance) |
| Evidence | `services/ingest.py:33-39`; `TARGET_ARCHITECTURE.md` §9–10; charter §6 provenance list. |
| Exact problem | There is no browser-side way to turn a chosen file into stored text with provenance. |
| Reason this matters | Every grounded feature depends on correctly attributed text. |
| Target behaviour | `app/js/import/parsers/text.js` (`parseText(text) → {sections:[{heading?, paragraphs:[string]}]}`), `app/js/search/chunker.js` (`chunk(parsed, {sourceId}) → Chunk[]` 80–300 words, never splitting a paragraph unless >300 words, locator `{heading?, paragraph, charStart, charEnd}`), `app/js/domain/provenance.js` (`buildProvenance({file, sha256, parser, appVersion, sourceSystem:'local-file'})` exactly per `TARGET_ARCHITECTURE.md` §10, asOf = `file.lastModified`), `app/js/import/pipeline.js` (`prepareImport(file, {projectId}) → {source, chunks, warnings}` without writing), validators for `source` and `chunk` in `validate.js`. |
| Smallest safe change | Pure modules + unit tests using fixture files read in Node. |
| Explicit exclusions | No UI, no storage writes (IMP-02A), no other formats. |
| Files expected to change | `app/js/import/parsers/text.js`, `app/js/search/chunker.js`, `app/js/domain/provenance.js`, `app/js/import/pipeline.js`, `tests/unit/import-text.test.mjs`, `tests/unit/chunker.test.mjs` (new); `app/js/domain/validate.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `parseText`, `chunk`, `buildProvenance`, `prepareImport`, `validateSource`, `validateChunk`. |
| Dependencies | DAT-02, BAS-02. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — fixtures `scope.txt`, `sample_call_notes.txt`: chunk text concatenation reproduces normalised input; every chunk has locator; provenance fields complete; sha256 equals `shasum`. |
| Manual verification | None. |
| Acceptance criteria | 1. Tests pass. 2. Pipeline has no IndexedDB or DOM imports. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-01: Import pipeline: text parser, chunker, provenance and hashing (pure)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CHT-02, IMP-02A |

### IMP-02A · Keep imported files: source/chunk repositories, single transaction, duplicate detection

| Field | Detail |
|---|---|
| Unique ID | IMP-02A |
| Title | Keep imported files: source/chunk repositories, single transaction, duplicate detection |
| Capability group | FILE IMPORT |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (target) |
| Evidence | `TARGET_ARCHITECTURE.md` §9; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V1. |
| Exact problem | Users need to bring documents in with a preview before anything is retained. |
| Reason this matters | Charter §6 V1: user-chosen files only, preview before retention. |
| Target behaviour | `app/js/storage/repos/sources.js`, `app/js/storage/repos/chunks.js`; `app/js/import/keep.js` exporting `keepPrepared(prepared)` (writes source with original Blob + all chunks in **one** transaction via `withTx`) and `findDuplicate(projectId, sha256)` (uses unique index `[projectId+sha256]`); `keepAsNewVersion(prepared, supersedesSourceId)`. Test hook (`?test=1`) exposes `prepareImport` + `keepPrepared` for e2e. |
| Smallest safe change | Implement storage side only. |
| Explicit exclusions | No UI (IMP-02B). No other formats. |
| Files expected to change | `app/js/storage/repos/sources.js`, `app/js/storage/repos/chunks.js`, `app/js/import/keep.js`, `tests/e2e/import-keep.spec.mjs` (new); `app/js/main.js` (test hook registration only). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `keepPrepared`, `findDuplicate`, `keepAsNewVersion`. |
| Dependencies | IMP-01. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | Reads only user-chosen files; nothing transmitted. |
| Storage or migration impact | Writes `sources` (with Blob) and `chunks`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/import-keep.spec.mjs` — keep writes 1 source + N chunks atomically (forced failure mid-write leaves zero records); duplicate found by hash; new version sets `supersedesSourceId`. |
| Manual verification | None (storage only; UI in IMP-02B). |
| Acceptance criteria | 1. Atomicity proven by forced-failure test. 2. Duplicate never overwrites (unique index rejects). 3. No DOM code in `keep.js`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-02A: Keep imported files: source/chunk repositories, single transaction, duplicate detection` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-02A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-02A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from IMP-02 by validation V-01. |
| Required by | IMP-02B |

### IMP-02B · Import UI: choose or drop files, preview, keep or discard

| Field | Detail |
|---|---|
| Unique ID | IMP-02B |
| Title | Import UI: choose or drop files, preview, keep or discard |
| Capability group | FILE IMPORT |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (target) |
| Evidence | `TARGET_ARCHITECTURE.md` §9; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V1. |
| Exact problem | Users need to bring documents in with a preview before anything is retained. |
| Reason this matters | Charter §6 V1: user-chosen files only, preview before retention. |
| Target behaviour | `app/js/import/intake.js` (`<input type=file multiple accept>` + drop zone; reads only chosen files), `app/js/ui/views/import.js` (preview card per file: name, size, type, as-of date, first 3 chunks as text, warnings; Keep/Discard per file; 'Keep all'; duplicate prompt 'Already imported on <date> (<name>). Skip / Import as new version'), `app/js/ui/views/sources.js` (Sources tab list). Unsupported type → message listing supported types. Only `.txt` registered. |
| Smallest safe change | Implement UI calling IMP-01 `prepareImport` and IMP-02A `keepPrepared`/`findDuplicate`. |
| Explicit exclusions | No extraction (MIG-01B). No folder selection. No storage code (IMP-02A). |
| Files expected to change | `app/js/import/intake.js`, `app/js/ui/views/import.js`, `app/js/ui/views/sources.js`, `tests/e2e/import.spec.mjs` (new); `app/js/ui/router.js`, `app/js/ui/views/project.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `pickFiles`, `onDrop`, `renderImport`, `renderSources`. |
| Dependencies | IMP-02A, UI-03. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | Reads only user-chosen files; nothing transmitted. |
| Storage or migration impact | Writes `sources` (with Blob) and `chunks`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/import.spec.mjs` — `setInputFiles` with fixture `.txt`: preview shows, IndexedDB count 0 before Keep, 1 source after Keep; same file again → duplicate prompt; Discard stores nothing; keyboard-only flow. |
| Manual verification | Drag a `.txt` file from a OneDrive-synced folder in Edge; preview, keep, reload, still present. |
| Acceptance criteria | 1. Nothing persisted before Keep. 2. Duplicate never silently overwrites. 3. Keyboard-operable. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-02B: Import UI: choose or drop files, preview, keep or discard` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-02B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-02B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from IMP-02 by validation V-01. |
| Required by | IMP-03, IMP-04, MIG-01B, ODI-01, ODI-02B, TST-03, UI-04 |

### TST-03 · Manual browser smoke checklist for phase gates and releases

| Field | Detail |
|---|---|
| Unique ID | TST-03 |
| Title | Manual browser smoke checklist for phase gates and releases |
| Capability group | TESTING |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | DOCUMENTED ONLY (manual checks scattered across items) |
| Evidence | Validation V-10: several items rely on real-browser behaviour that automation can't prove (`TEST_AND_RELEASE_READINESS.md` §6). |
| Exact problem | There is no single manual check run in real Edge (and Safari where available) before a phase gate or release. |
| Reason this matters | Catches behaviour that Playwright's bundled browsers don't reproduce (corporate policy, real file dialogs). |
| Target behaviour | `docs/release/MANUAL_SMOKE_CHECKLIST.md`: numbered steps with expected results for the features Done so far (open app, create project, import `.txt`, reload, backup, reset, restore, Trash/undo); a results table (date, browser + version, OS, tester, pass/fail per step, notes). Each later feature item appends its steps when it completes (rule added to the MASTER header). |
| Smallest safe change | Create the document. |
| Explicit exclusions | No automation. |
| Files expected to change | `docs/release/MANUAL_SMOKE_CHECKLIST.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | BAK-02, IMP-02B. |
| Prerequisite decisions | ADR-018. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | None (manual document). |
| Manual verification | Owner runs the checklist once in Edge on the corporate laptop and records results. |
| Acceptance criteria | 1. Checklist covers every user-visible Phase 1 feature. 2. One completed results row exists. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `TST-03: Manual browser smoke checklist for phase gates and releases` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `TST-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| TST-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Added by validation V-10. |
| Required by | REL-01A |

### IMP-03 · Markdown, CSV and JSON parsers with locators

| Field | Detail |
|---|---|
| Unique ID | IMP-03 |
| Title | Markdown, CSV and JSON parsers with locators |
| Capability group | FILE IMPORT |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | WORKING in legacy (`processors/parsers/markdown_parser.py`, `csv_parser.py`); JSON handled ad hoc |
| Evidence | `processors/parsers/*.py`; `processors/ingestion.py:22`. |
| Exact problem | Common project formats can't yet be imported. |
| Reason this matters | Daily use requires the formats PMs actually have. |
| Target behaviour | `parsers/markdown.js` (headings → sections; table rows kept as text rows; locator `heading`), `parsers/csv.js` (RFC 4180 quoting; each row → paragraph `Header: value; …`; locator `row`, header kept in chunk context), `parsers/json.js` (pretty-printed, top-level keys → sections; invalid JSON → `IMP-PARSE-FAIL` warning and treat as text). Registered in `pipeline.js` by extension. |
| Smallest safe change | Port behaviour from legacy parsers; unit tests on fixtures `sample_artefact.md`, `cpg_app.csv`, `health_infra.csv`. |
| Explicit exclusions | No Excel (`.xlsx`). |
| Files expected to change | `app/js/import/parsers/markdown.js`, `csv.js`, `json.js`, `tests/unit/parsers-md-csv-json.test.mjs` (new); `app/js/import/pipeline.js`, `app/js/import/intake.js` (accept list). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `parseMarkdown`, `parseCsv`, `parseJson`. |
| Dependencies | IMP-02B. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — CSV with quoted commas/newlines; markdown heading locators; invalid JSON warning. |
| Manual verification | Import one CSV fixture in Edge; preview shows row-based chunks. |
| Acceptance criteria | 1. Tests pass. 2. Section counts for fixtures equal legacy golden `ingest_file` section counts or a difference is listed in `ACCEPTED_DIFFERENCES.md`. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-03: Markdown, CSV and JSON parsers with locators` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | IMP-05, MIG-01A |

### IMP-04 · Email (.eml) parser

| Field | Detail |
|---|---|
| Unique ID | IMP-04 |
| Title | Email (.eml) parser |
| Capability group | FILE IMPORT |
| Priority | P1 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | WORKING in legacy (`processors/parsers/email_parser.py`) |
| Evidence | `processors/parsers/email_parser.py:27`; fixture `sample_email.txt`. |
| Exact problem | Client correspondence (.eml) can't be imported. |
| Reason this matters | Emails are a primary source of decisions and risks. |
| Target behaviour | `parsers/email.js`: headers (From, To, Date, Subject) captured as metadata (stored on source, shown in preview), body text/plain preferred, quoted-printable and base64 decoding, multipart boundaries, HTML-only bodies converted to text via `DOMParser` (text content only, never inserted into the page), locator `messageId` + paragraph. |
| Smallest safe change | Implement + unit tests; add a synthetic `.eml` fixture `tests/fixtures/synthetic/sample_email.eml` derived from `sample_email.txt` (state in fixture README it's synthetic). |
| Explicit exclusions | No attachments extraction (listed by name only). |
| Files expected to change | `app/js/import/parsers/email.js`, `tests/unit/parser-email.test.mjs`, `tests/fixtures/synthetic/sample_email.eml` (new); `tests/fixtures/synthetic/README.md`; `app/js/import/pipeline.js`, `app/js/import/intake.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `parseEmail`. |
| Dependencies | IMP-02B. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | HTML bodies parsed with `DOMParser` into a detached document; only `textContent` used. |
| Automated tests | `npm run test:unit` — QP decoding, multipart, HTML-only body with `<script>` yields text only. `npm run test:e2e -- tests/e2e/import.spec.mjs` extended: importing an `.eml` whose HTML body contains `<img id="pwned" src=x onerror=alert(1)>` leaves no `#pwned` element in the page and fires no dialog. |
| Manual verification | Import the `.eml` fixture in Edge; preview shows subject and body. |
| Acceptance criteria | 1. Tests pass. 2. The `#pwned` e2e assertion passes in chromium and webkit. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-04: Email (.eml) parser` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-15 (testable acceptance). |
| Required by | CLN-02, MIG-01A |

### IMP-05 · Hostile-input and size-limit protections for import

| Field | Detail |
|---|---|
| Unique ID | IMP-05 |
| Title | Hostile-input and size-limit protections for import |
| Capability group | SECURITY AND PRIVACY |
| Priority | P0 |
| Phase | 1 (Maintainable shell, reliable storage, import, provenance) |
| Current classification | BROKEN in legacy (filename XSS M-1; unbounded body L-2) |
| Evidence | `static/index.html:1112`; `server.py:503,588`; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V1 limits. |
| Exact problem | Malicious or huge files must not execute script or freeze/crash the app. |
| Reason this matters | Prevents XSS and data loss from crashes. |
| Target behaviour | Size warning above `settings.importWarnMB` (default 25) and refusal above 100 MB with plain reason; `tests/fixtures/hostile/`: filenames `x');alert(1);//.txt`, `<img src=x onerror=alert(1)>.md`, a 0-byte file, a binary file renamed `.txt` (detected by >10 % control characters → `IMP-PARSE-FAIL` 'This doesn't look like a text file'), a 5,000-line CSV for responsiveness (import yields to the UI every 200 rows). |
| Smallest safe change | Add checks in `intake.js`/`pipeline.js`; add fixtures and e2e. |
| Explicit exclusions | No antivirus scanning. |
| Files expected to change | `app/js/import/intake.js`, `app/js/import/pipeline.js`, `tests/fixtures/hostile/*` (new), `tests/e2e/import-hostile.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `checkSize`, `looksBinary`. |
| Dependencies | IMP-03. |
| Prerequisite decisions | ADR-010. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Direct XSS regression coverage. |
| Automated tests | `npm run test:e2e -- tests/e2e/import-hostile.spec.mjs` — no dialog/alert fires (Playwright `page.on('dialog')` fails test), names render literally, binary rejected, large CSV completes with UI responsive (a button click during import is handled). |
| Manual verification | None beyond e2e. |
| Acceptance criteria | 1. All hostile fixtures handled as described. 2. Zero CSP violations. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-05: Hostile-input and size-limit protections for import` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-05` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-05 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | IMP-06 |

## Phase 2 – PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1

### PWA-01 · Web app manifest and icons

| Field | Detail |
|---|---|
| Unique ID | PWA-01 |
| Title | Web app manifest and icons |
| Capability group | PWA AND OFFLINE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no manifest/icons exist — assessment §3) |
| Evidence | `TARGET_ARCHITECTURE.md` §19. |
| Exact problem | The app can't be installed. |
| Reason this matters | Installable, dependable use for non-technical users (OD-1). |
| Target behaviour | `app/manifest.webmanifest` exactly per §19 (relative `id`, `start_url`, `scope`); `app/icons/icon.svg` (simple monogram, hand-written SVG), `icon-192.png`, `icon-512.png`, `maskable-512.png` generated once by checked-in `tools/make-icons.mjs` (Playwright renders the SVG, which uses shapes only and no text, to PNG) and committed; `<link rel="manifest">` and `<meta name="theme-color">` in `index.html`. |
| Smallest safe change | Create files; PNGs are GENERATED (header note in tools script; list in register). |
| Explicit exclusions | No service worker (PWA-02B). No `file_handlers`/`share_target`. |
| Files expected to change | `app/manifest.webmanifest`, `app/icons/*`, `tools/make-icons.mjs` (new); `app/index.html`; `tests/e2e/manifest.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | BLD-01. |
| Prerequisite decisions | ADR-011, ADR-024. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/manifest.spec.mjs` — manifest fetch 200, parses, icons 200 with correct sizes. |
| Manual verification | Edge devtools → Application → Manifest shows no errors. |
| Acceptance criteria | 1. Manifest valid, all URLs relative. 2. Icon PNGs have the declared dimensions (byte-identical regeneration is not required — rendering varies by platform). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `PWA-01: Web app manifest and icons` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `PWA-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| PWA-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-17 (untestable byte-identical criterion removed). |
| Required by | PWA-04 |

### PWA-04 · Recovery page (reset.html) and remote kill-switch file, before any service worker

| Field | Detail |
|---|---|
| Unique ID | PWA-04 |
| Title | Recovery page (reset.html) and remote kill-switch file, before any service worker |
| Capability group | PWA AND OFFLINE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY |
| Evidence | Charter §10 ('do not replace a service worker … without tests and a kill-switch'); `TARGET_ARCHITECTURE.md` §18. |
| Exact problem | Once a service worker exists, a broken release could be pinned with no recovery for non-technical users; the recovery route must exist first. |
| Reason this matters | Recoverable PWA; hard prerequisite for PWA-02B. |
| Target behaviour | `app/reset.html` + `app/reset.js` (standalone page that does not import `main.js` or any app module; plain-language explanation; button 'Reset app code (your data is kept)': `navigator.serviceWorker.getRegistrations()` → unregister all; delete caches whose names start with `pdae-shell-`; **never** touches IndexedDB; then navigates to `./`). `app/kill-switch.json` = `{"disable": false, "below": "0.0.0"}`. `app/js/core/kill-switch.js` (`checkKillSwitch(appVersion)`: fetch `./kill-switch.json` with `cache:'no-store'`, 3 s timeout, ignore any failure; returns true when `disable` and `appVersion` < `below` by semver compare). Footer link 'Problems? Reset app code' → `./reset.html`. SEC-01 allow-list: `fetch(` permitted in `app/js/core/kill-switch.js` for the same-origin relative URL only. |
| Smallest safe change | Implement; works (harmlessly) even before a service worker exists. |
| Explicit exclusions | No service worker (PWA-02B consumes `checkKillSwitch` and serves reset files network-first). |
| Files expected to change | `app/reset.html`, `app/reset.js`, `app/kill-switch.json`, `app/js/core/kill-switch.js`, `tests/unit/kill-switch.test.mjs`, `tests/e2e/reset-page.spec.mjs` (new); `app/index.html` (footer link), `tools/check-forbidden-apis.mjs` (allow-list entry). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `resetAppCode`, `checkKillSwitch`, `semverLess`. |
| Dependencies | PWA-01. |
| Prerequisite decisions | ADR-011. |
| External approvals | None. |
| Data-boundary impact | Each app start requests `./kill-switch.json` from the hosting origin (no content; the host sees IP address and time, as for any page load). Document in DOC-02. |
| Storage or migration impact | Explicitly preserves IndexedDB (asserted in test). |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` semver compare and timeout handling. `npm run test:e2e -- tests/e2e/reset-page.spec.mjs` — with a project stored and a dummy cache `pdae-shell-test` created, reset deletes the cache and keeps the project; reset works when `main.js` is served broken (test route returns a syntax error). |
| Manual verification | Edge: open `./reset.html`, click reset, data still present. |
| Acceptance criteria | 1. Data preserved after reset. 2. Reset page works with a broken `main.js`. 3. `checkKillSwitch` never throws. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `PWA-04: Recovery page (reset.html) and remote kill-switch file, before any service worker` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `PWA-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| PWA-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-19 (data-boundary impact made explicit). |
| Required by | DOC-02, PWA-02A |

### PWA-02A · Precache manifest generator and CI freshness check (no service worker)

| Field | Detail |
|---|---|
| Unique ID | PWA-02A |
| Title | Precache manifest generator and CI freshness check (no service worker) |
| Capability group | PWA AND OFFLINE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no service worker exists — no legacy pinning risk) |
| Evidence | `TARGET_ARCHITECTURE.md` §18, §20; ADR-011. |
| Exact problem | The app doesn't start without a network connection to its host. |
| Reason this matters | Dependable PWA use; offline mode. |
| Target behaviour | `tools/precache.mjs` writes `app/precache-manifest.js` (`PRECACHE=[{url, sha256}]`, `MANIFEST_HASH`) for every file under `app/` except `sw.js`, `reset.html`, `reset.js`, `kill-switch.json`; `npm run check` regenerates to a temp file and fails on difference. |
| Smallest safe change | Generator + check only. |
| Explicit exclusions | No `sw.js`, no registration. |
| Files expected to change | `tools/precache.mjs`, `app/precache-manifest.js` (GENERATED), `tests/unit/precache.test.mjs` (new); `package.json`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `PRECACHE`, `MANIFEST_HASH`. |
| Dependencies | PWA-04. |
| Prerequisite decisions | ADR-011. |
| External approvals | None. |
| Data-boundary impact | None. |
| Storage or migration impact | None. |
| Security and privacy impact | SW must not cache `openrouter.ai` responses or any POST. |
| Automated tests | `npm run test:unit`; `npm run check` fails after editing an `app/` file without regenerating. |
| Manual verification | None. |
| Acceptance criteria | 1. Deterministic output. 2. Stale manifest fails the check. |
| Rollback | `git revert`; no user impact (nothing executes it). |
| Recommended commit boundary | One commit titled `PWA-02A: Precache manifest generator and CI freshness check (no service worker)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `PWA-02A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| PWA-02A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from PWA-02 by validation V-06. |
| Required by | PWA-02B |

### PWA-02B · Service worker: app-shell cache, offline start, kill-switch integration

| Field | Detail |
|---|---|
| Unique ID | PWA-02B |
| Title | Service worker: app-shell cache, offline start, kill-switch integration |
| Capability group | PWA AND OFFLINE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no service worker exists — no legacy pinning risk) |
| Evidence | `TARGET_ARCHITECTURE.md` §18, §20; ADR-011. |
| Exact problem | The app doesn't start without a network connection to its host. |
| Reason this matters | Dependable PWA use; offline mode. |
| Target behaviour | Uses `PRECACHE`/`MANIFEST_HASH` from PWA-02A. `app/sw.js`: install → open cache `pdae-shell-<APP_VERSION>-<MANIFEST_HASH>` and add all; fetch → same-origin GET only, cache-first, falling back to network; never handles non-same-origin requests; activate → delete other `pdae-shell-*` caches; **no `skipWaiting` on install**; `reset.html`, `reset.js` and `kill-switch.json` are served network-first (cache fallback for reset files, never cached for the json); on `activate` and at each app start `checkKillSwitch(APP_VERSION)` true → `self.registration.unregister()` and clients reload once. Registration in `main.js` via `navigator.serviceWorker.register(scriptURL('./sw.js'))` only when `location.protocol` is `https:` or host is `127.0.0.1`/`localhost`. |
| Smallest safe change | Implement `sw.js` and registration. |
| Explicit exclusions | No update prompt (PWA-03), no runtime caching of data. **Must not be released (tagged) unless PWA-04 is already in the same or an earlier release.** |
| Files expected to change | `app/sw.js` (new); `app/js/main.js`, `tests/e2e/offline.spec.mjs`, `tests/e2e/kill-switch.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `PRECACHE`, `MANIFEST_HASH`, SW `install`/`fetch`/`activate` handlers. |
| Dependencies | PWA-02A, SEC-02. |
| Prerequisite decisions | ADR-011. |
| External approvals | None. |
| Data-boundary impact | None (SW never touches other origins). |
| Storage or migration impact | None. |
| Security and privacy impact | SW must not cache `openrouter.ai` responses or any POST. |
| Automated tests | `npm run test:e2e -- tests/e2e/offline.spec.mjs` — load, wait for SW `activated`, `context.setOffline(true)`, reload → app renders and existing projects list. `npm run test:e2e -- tests/e2e/kill-switch.spec.mjs` — after SW install, `reset.html` unregisters it and data survives; serving `kill-switch.json` `{disable:true, below:'99.0.0'}` unregisters on next start. |
| Manual verification | Edge: load, go offline (devtools), reload: app works. |
| Acceptance criteria | 1. Offline reload works in chromium (webkit best-effort, record result). 2. Stale precache manifest fails `npm run check`. |
| Rollback | Set `kill-switch.json` to `{"disable": true, "below": "<next version>"}` and publish, or tell users to open `./reset.html`; then revert the commit. |
| Recommended commit boundary | One commit titled `PWA-02B: Service worker: app-shell cache, offline start, kill-switch integration` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `PWA-02B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| PWA-02B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from PWA-02 by validation V-06. |
| Required by | IMP-07, PWA-03 |

### PWA-03 · Update prompt with backup-first and schema-change notice

| Field | Detail |
|---|---|
| Unique ID | PWA-03 |
| Title | Update prompt with backup-first and schema-change notice |
| Capability group | PWA AND OFFLINE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `TARGET_ARCHITECTURE.md` §18; `DATA_AND_STORAGE_ARCHITECTURE.md` §7. |
| Exact problem | Users need control over when a new version activates, and a chance to back up before schema changes. |
| Reason this matters | Prevents data loss during upgrades. |
| Target behaviour | `main.js` detects `registration.waiting` / `updatefound`; shows non-blocking panel 'Update available (vX). Download a backup first (recommended) · Update now · Later'. The new SW exposes its version via `postMessage({type:'VERSION'})` reply including `SCHEMA_VERSION`; if higher than current DB version, panel adds 'This update changes how data is stored (schema A → B).' Update now → `postMessage({type:'SKIP_WAITING'})`; page reloads once on `controllerchange` (guarded against loops). |
| Smallest safe change | Implement in `main.js` + `app/js/ui/components/update-panel.js`; `sw.js` handles the two messages. |
| Explicit exclusions | No automatic activation. |
| Files expected to change | `app/js/ui/components/update-panel.js` (new), `app/js/main.js`, `app/sw.js`, `tests/e2e/update.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `showUpdatePanel`, SW message handlers `VERSION`, `SKIP_WAITING`. |
| Dependencies | PWA-02B, BAK-03. |
| Prerequisite decisions | ADR-011. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/update.spec.mjs` — serve version A, then switch served files to version B (test server flag): panel appears; 'Later' keeps A; 'Update now' reloads into B exactly once; schema notice shown when B has higher schema. |
| Manual verification | Edge: simulate update via two local builds; observe panel. |
| Acceptance criteria | 1. No activation without click. 2. Single reload. 3. Backup button triggers BAK-01 download. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `PWA-03: Update prompt with backup-first and schema-change notice` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `PWA-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| PWA-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-18 (restore must exist before prompting users to back up for an update). |
| Required by | DGN-02, ODI-02A, REL-01A |

### IMP-06 · DOCX import without third-party libraries

| Field | Detail |
|---|---|
| Unique ID | IMP-06 |
| Title | DOCX import without third-party libraries |
| Capability group | FILE IMPORT |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | WORKING in legacy via python-docx (`processors/parsers/docx_parser.py`); not available in browser |
| Evidence | ADR-009; `TARGET_ARCHITECTURE.md` §9. |
| Exact problem | SoWs and proposals are usually `.docx`. |
| Reason this matters | Daily use. |
| Target behaviour | `app/js/import/zip-read.js` (`readZipEntries(arrayBuffer) → Map<name, () => Promise<Uint8Array>>` parsing the central directory; methods stored (0) and deflate (8) via `DecompressionStream('deflate-raw')`; rejects zip64, encrypted entries, entries >50 MB uncompressed, total >200 MB, and names containing `..` — 'zip bomb' guard), `parsers/docx.js` (`word/document.xml` via `DOMParser('application/xml')`: paragraphs `w:p` → text of `w:t`, headings from `w:pStyle` `Heading1..6`, tables row-wise; locator `paragraph`, `heading`). Unsupported browser (no `DecompressionStream`) → 'DOCX isn't supported in this browser'. |
| Smallest safe change | Implement; create synthetic fixture `tests/fixtures/synthetic/sample_scope.docx` generated by checked-in `tools/make-docx-fixture.mjs` from `scope.txt` (stored zip, minimal OOXML). |
| Explicit exclusions | No images, comments, tracked changes, headers/footers. |
| Files expected to change | `app/js/import/zip-read.js`, `app/js/import/parsers/docx.js`, `tools/make-docx-fixture.mjs`, `tests/fixtures/synthetic/sample_scope.docx`, `tests/unit/zip-docx.test.mjs` (new); `app/js/import/pipeline.js`, `app/js/import/intake.js`, `tests/fixtures/synthetic/README.md`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `readZipEntries`, `parseDocx`. |
| Dependencies | IMP-05. |
| Prerequisite decisions | ADR-009. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Zip-bomb and path guards required. |
| Automated tests | `npm run test:unit` (Node ≥ 22, per TST-01 `engines`) — fixture text equals `scope.txt` paragraphs; crafted bomb rejected; `..` entry rejected. `npm run test:e2e -- tests/e2e/import.spec.mjs` extended with docx case. |
| Manual verification | Import a real Word document the owner authored (non-confidential) in Edge; compare preview text with Word. |
| Acceptance criteria | 1. Tests pass. 2. Manual comparison recorded (unverified Word features listed). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-06: DOCX import without third-party libraries` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-06` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-06 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-23 (unit tests need Node ≥ 22). |
| Required by | EXP-02, IMP-07 |

### MIG-01A · Port deterministic extraction (pure) with citations and parity tests

| Field | Detail |
|---|---|
| Unique ID | MIG-01A |
| Title | Port deterministic extraction (pure) with citations and parity tests |
| Capability group | MINIFIED CODE MIGRATION |
| Priority | P0 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | WORKING in legacy (`processors/extractors/patterns.py`, `intelligence_extractor.py`), no citations |
| Evidence | `processors/extractors/patterns.py` (410 lines), `intelligence_extractor.py:42`; BAS-03 goldens; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §3. |
| Exact problem | Extraction logic exists only in Python and produces items without source references. |
| Reason this matters | Restores maintainable source for the core feature; adds evidence for every item (no fabricated findings). |
| Target behaviour | `app/js/extract/patterns.js` (same patterns and thresholds as legacy, comments cite legacy line numbers), `app/js/extract/extractor.js` (`extractItems(chunks) → Item[]`, kinds risk, assumption, dependency, constraint, action, scope, resource; each `{text, kind, citations:[{chunkId, quote}]}` with `quote` = exact matched sentence; `EXTRACTOR_VERSION`), `tests/unit/extract.parity.test.mjs` (per fixture and kind, set equality with legacy goldens after whitespace normalisation, minus `ACCEPTED_DIFFERENCES.md`), `tests/unit/extract.test.mjs`. |
| Smallest safe change | Port function by function; no storage, no UI. |
| Explicit exclusions | No storage (MIG-01B). No AI. No new patterns. |
| Files expected to change | `app/js/extract/patterns.js`, `app/js/extract/extractor.js`, `tests/unit/extract.parity.test.mjs`, `tests/unit/extract.test.mjs` (new); `tests/fixtures/legacy-golden/ACCEPTED_DIFFERENCES.md`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `extractItems`, `PATTERNS`, `isNoiseLine`, `cleanExtraction`, `EXTRACTOR_VERSION`. |
| Dependencies | IMP-03, IMP-04, BAS-03, CHT-01. |
| Prerequisite decisions | ADR-012, ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` parity; every item's quote verifies with `verifyCitation`. |
| Manual verification | None (pure). |
| Acceptance criteria | 1. Parity test passes with every difference listed and accepted by the owner (BD-04). 2. 100 % of items have a verifying citation. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `MIG-01A: Port deterministic extraction (pure) with citations and parity tests` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `MIG-01A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| MIG-01A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from MIG-01 by validation V-02. |
| Required by | CLN-02, MIG-01B, MIG-02A |

### MIG-01B · Store extracted items on keep and support re-run

| Field | Detail |
|---|---|
| Unique ID | MIG-01B |
| Title | Store extracted items on keep and support re-run |
| Capability group | MINIFIED CODE MIGRATION |
| Priority | P0 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | WORKING in legacy (`processors/extractors/patterns.py`, `intelligence_extractor.py`), no citations |
| Evidence | `processors/extractors/patterns.py` (410 lines), `intelligence_extractor.py:42`; BAS-03 goldens; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §3. |
| Exact problem | Extraction logic exists only in Python and produces items without source references. |
| Reason this matters | Restores maintainable source for the core feature; adds evidence for every item (no fabricated findings). |
| Target behaviour | `validateItem` in `validate.js`; `app/js/storage/repos/items.js`; `keep.js` runs `extractItems` on the kept chunks and writes items in the same transaction; project action 'Re-run extraction' replaces items whose `extractorVersion` differs (old items moved to Trash, not deleted). |
| Smallest safe change | Wire MIG-01A into IMP-02A storage. |
| Explicit exclusions | No UI list (UI-05). |
| Files expected to change | `app/js/storage/repos/items.js` (new), `app/js/domain/validate.js`, `app/js/import/keep.js`, `app/js/ui/views/project.js` (Re-run button), `tests/e2e/items-store.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `validateItem`, `rerunExtraction`. |
| Dependencies | MIG-01A, IMP-02B, DAT-06A. |
| Prerequisite decisions | ADR-012, ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes `items`; re-run uses Trash. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/items-store.spec.mjs` — keeping `scope.txt` stores items equal to `extractItems` output; re-run with changed version trashes old items. |
| Manual verification | Import `scope.txt` in Edge; item counts by kind match the golden file. |
| Acceptance criteria | 1. Items stored in the keep transaction. 2. Re-run never deletes (Trash). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `MIG-01B: Store extracted items on keep and support re-run` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `MIG-01B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| MIG-01B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from MIG-01 by validation V-02. |
| Required by | DAT-07, UI-05 |

### UI-04 · Source viewer and citation component

| Field | Detail |
|---|---|
| Unique ID | UI-04 |
| Title | Source viewer and citation component |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §2 (clickable citations), `TARGET_ARCHITECTURE.md` §10. |
| Exact problem | Users must be able to see exactly where a statement comes from. |
| Reason this matters | Grounded answers are only trustworthy if citations open the source text. |
| Target behaviour | `app/js/ui/components/citation.js` (`citationLink({chunkId, quote})` → button text '<source name> · <locator>' ; activates route `#/project/:id/source/:sourceId?chunk=:chunkId`), `app/js/ui/views/source-viewer.js` (shows source provenance and all chunks as text; scrolls to and highlights the cited chunk and quote by wrapping text nodes in `<mark>` built with `h()`), `app/js/ui/components/label-badge.js` (label text + icon, never colour only). |
| Smallest safe change | Implement. |
| Explicit exclusions | No editing of source text. |
| Files expected to change | `app/js/ui/components/citation.js`, `app/js/ui/components/label-badge.js`, `app/js/ui/views/source-viewer.js`, `tests/e2e/source-viewer.spec.mjs` (new); `app/js/ui/router.js`, `app/js/ui/views/sources.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `citationLink`, `labelBadge`, `renderSourceViewer`. |
| Dependencies | IMP-02B, CHT-01. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/source-viewer.spec.mjs` — clicking a citation focuses the highlighted quote; quote containing `<b>` displays literally. |
| Manual verification | Keyboard-only: Tab to a citation, Enter, focus lands on highlight. |
| Acceptance criteria | 1. Test passes. 2. Provenance fields (hash, imported, as-of, parser) visible. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-04: Source viewer and citation component` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CHT-03, UI-05, UI-06 |

### UI-05 · Extracted items view

| Field | Detail |
|---|---|
| Unique ID | UI-05 |
| Title | Extracted items view |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy (intelligence tab, no citations) |
| Evidence | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §8 C7. |
| Exact problem | Extracted items aren't visible with their evidence. |
| Reason this matters | Daily use: the PM's main view of risks, assumptions, dependencies. |
| Target behaviour | `app/js/ui/views/items.js`: tabs by kind with counts; each item shows text, `FACT` badge, citation link(s); filter by source; text search within items; empty kinds show 'None found in N sources' (NOT_FOUND wording with scope). |
| Smallest safe change | Implement. |
| Explicit exclusions | No item editing (user annotations deferred). |
| Files expected to change | `app/js/ui/views/items.js` (new), `app/js/ui/router.js`, `app/js/ui/views/project.js`, `tests/e2e/items.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderItems`. |
| Dependencies | MIG-01B, UI-04. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/items.spec.mjs` — after importing `scope.txt`, risk tab count equals stored count; every item has a citation link. |
| Manual verification | Edge: browse items for the sample fixture. |
| Acceptance criteria | 1. Test passes. 2. Empty states state scope. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-05: Extracted items view` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-05` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-05 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### CHT-02 · Deterministic search index and query (BM25)

| Field | Detail |
|---|---|
| Unique ID | CHT-02 |
| Title | Deterministic search index and query (BM25) |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no retrieval exists — C1) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §2. |
| Exact problem | There is no way to search stored documents. |
| Reason this matters | Required for grounded chat without AI. |
| Target behaviour | `app/js/search/tokenize.js` (lower-case, NFKD, strip diacritics, split on non-letters/digits, English stop-word list, light suffix stemming: -ing, -ed, -es, -s, -ly), `app/js/search/index.js` (`buildIndex(chunks)`; BM25 k1=1.2, b=0.75), `app/js/search/query.js` (`search(index, question, {limit=10}) → [{chunkId, score, matchedTerms}]`, threshold constant for 'weak'), `app/js/search/evidence.js` (`selectEvidence(results, chunksById) → {strong[], weak[], searchedTerms, searchedCount}`). |
| Smallest safe change | Pure modules with unit tests. |
| Explicit exclusions | No UI, no persistence of the index. |
| Files expected to change | `app/js/search/tokenize.js`, `index.js`, `query.js`, `evidence.js`, `tests/unit/search.test.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `tokenize`, `buildIndex`, `search`, `selectEvidence`. |
| Dependencies | IMP-01. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — query 'data residency' on fixtures ranks the chunk containing it first; nonsense query returns empty strong set; performance: 5,000 chunks indexed < 2 s in Node. |
| Manual verification | None. |
| Acceptance criteria | 1. Tests pass. 2. No module generates prose. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CHT-02: Deterministic search index and query (BM25)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CHT-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CHT-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CHT-03 |

### CHT-03 · Ask view: evidence answers with scope, Not found and history

| Field | Detail |
|---|---|
| Unique ID | CHT-03 |
| Title | Ask view: evidence answers with scope, Not found and history |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no chatbot exists — C1) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §2 result screen. |
| Exact problem | Users can't ask questions about their documents. |
| Reason this matters | Grounded chatbot that never invents answers (charter §9). |
| Target behaviour | `app/js/ui/views/ask.js`: question box; scope selector (all sources / chosen sources); result: 'Scope: … · searched N passages'; Evidence list of `FACT` statements quoting chunk text with citation links; 'Possibly related' `NEEDS_CONFIRMATION`; if none: `NOT_FOUND` statement with scope and searched terms; footer 'Nothing here was written by AI.' Answers stored (`answers` store, `validateAnswer`) and listed with Clear history. |
| Smallest safe change | Implement using CHT-01 statements and CHT-02 search. |
| Explicit exclusions | No AI (AI-*). No conversational memory. |
| Files expected to change | `app/js/ui/views/ask.js`, `app/js/storage/repos/answers.js`, `tests/e2e/ask.spec.mjs` (new); `app/js/domain/validate.js`, `app/js/ui/router.js`, `app/js/ui/views/project.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderAsk`, `answerQuestion`. |
| Dependencies | CHT-02, UI-04, CHT-01. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/ask.spec.mjs` — known phrase returns quoted evidence whose text equals stored chunk substring; unknown topic returns Not found with scope; no statement without label. |
| Manual verification | Edge: ask three questions on the sample project; verify quotes by clicking citations. |
| Acceptance criteria | 1. Test passes. 2. Every evidence statement's text is an exact substring of its cited chunk, and every other visible sentence comes from a fixed template list in `ask.js` (unit-checked). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CHT-03: Ask view: evidence answers with scope, Not found and history` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CHT-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CHT-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-16 (testable 'no generated sentences'; snapshot scope moved to DAT-07). |
| Required by | AI-01, CPL-01A, DAT-07, UI-07 |

### DAT-07 · Snapshots (named, immutable versions of included sources)

| Field | Detail |
|---|---|
| Unique ID | DAT-07 |
| Title | Snapshots (named, immutable versions of included sources) |
| Capability group | DATA AND STORAGE |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy (Phase→Version hierarchy; complex) |
| Evidence | `models/hierarchy.py`; ADR-012 (simplified Snapshot → Review). |
| Exact problem | Reviews need a fixed set of sources so they can be compared over time. |
| Reason this matters | Repeatable reviews; traceability. |
| Target behaviour | `app/js/storage/repos/snapshots.js`, `validateSnapshot`; Snapshots tab: 'Create snapshot' (name, note, ticked sources default all current non-superseded) storing `sourceIds`, `itemIds`, `createdAt`; list; snapshots are read-only (no edit/delete except via Trash of whole project). Ask scope selector gains 'Snapshot: <name>'. |
| Smallest safe change | Implement. |
| Explicit exclusions | No phases, gates or proposal versions. |
| Files expected to change | `app/js/storage/repos/snapshots.js`, `app/js/ui/views/snapshots.js`, `tests/e2e/snapshots.spec.mjs` (new); `app/js/domain/validate.js`, `app/js/ui/router.js`, `app/js/ui/views/project.js`, `app/js/ui/views/ask.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `createSnapshot`, `renderSnapshots`. |
| Dependencies | MIG-01B, CHT-03. |
| Prerequisite decisions | ADR-012. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes `snapshots`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/snapshots.spec.mjs` — snapshot records exact source/item ids; adding a new source later doesn't change it. |
| Manual verification | Create a snapshot in Edge. |
| Acceptance criteria | 1. Immutability enforced by repo (put on existing id rejected). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DAT-07: Snapshots (named, immutable versions of included sources)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DAT-07` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DAT-07 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-16 (adds snapshot scope to Ask; depends on CHT-03). |
| Required by | MIG-02B |

### MIG-02A · Port persona review heuristics (pure) with explicit labelling rules and parity tests

| Field | Detail |
|---|---|
| Unique ID | MIG-02A |
| Title | Port persona review heuristics (pure) with explicit labelling rules and parity tests |
| Capability group | MINIFIED CODE MIGRATION |
| Priority | P0 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | MOCKED-like in legacy (generic heuristic text presented as findings — C5, C6) |
| Evidence | `personas/engine.py:527-625` `_heuristic_findings`; `personas/deep_dive.py:362` `_heuristic_questions`; `COPILOT_AND_CHAT_ARCHITECTURE.md` §3 mapping table; BAS-03/BAS-04. |
| Exact problem | Legacy reviews mix document evidence with canned advice without telling the user. |
| Reason this matters | Prevents fabricated findings; keeps the persona value. |
| Target behaviour | `app/js/review/checks.js` (keyword lists per persona group, ported verbatim with legacy line references), `app/js/review/engine.js` (`runReview({personaId, snapshot, items, chunks}) → Review` with `method:'deterministic'`). Mapping rules (deterministic, no interpretation): (1) a legacy finding string that is an extracted item text, or `<prefix>: <item text>` → `FACT` citing that item's citation; (2) a string starting with `No ` or containing `not found`/`found —`/`mentioned` with no item → `NOT_FOUND` with scope `{sources, keywords}` from the check; (3) any other fixed sentence not ending in `?` → `RECOMMENDATION`, origin deterministic, `note:'Checklist guidance, not from your documents'`; (4) any sentence ending in `?` → `NEEDS_CONFIRMATION`, linked to the related NOT_FOUND when its keyword set overlaps. Strings matching none of the rules fail the parity test. Deep-dive questions become the NEEDS_CONFIRMATION set. `tests/unit/review.parity.test.mjs`, `tests/unit/review.labels.test.mjs`. |
| Smallest safe change | Port; no storage. |
| Explicit exclusions | No storage (MIG-02B), no AI, no synthesis. |
| Files expected to change | `app/js/review/checks.js`, `app/js/review/engine.js`, `tests/unit/review.parity.test.mjs`, `tests/unit/review.labels.test.mjs` (new); `tests/fixtures/legacy-golden/ACCEPTED_DIFFERENCES.md`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `runReview`, `CHECKS`, `classifyLegacyString`. |
| Dependencies | MIG-01A, BAS-04. |
| Prerequisite decisions | ADR-008, ADR-012. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` parity (every legacy string classified by the four rules) + label rules (no FACT without verifying citation). |
| Manual verification | None (pure). |
| Acceptance criteria | 1. Every golden string classified; unclassifiable strings listed in ACCEPTED_DIFFERENCES and accepted (BD-04). 2. Label rule test passes for all personas. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `MIG-02A: Port persona review heuristics (pure) with explicit labelling rules and parity tests` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `MIG-02A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| MIG-02A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from MIG-02 by validation V-03. |
| Required by | CLN-02, MIG-02B |

### MIG-02B · Persist reviews against snapshots

| Field | Detail |
|---|---|
| Unique ID | MIG-02B |
| Title | Persist reviews against snapshots |
| Capability group | MINIFIED CODE MIGRATION |
| Priority | P0 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | MOCKED-like in legacy (generic heuristic text presented as findings — C5, C6) |
| Evidence | `personas/engine.py:527-625` `_heuristic_findings`; `personas/deep_dive.py:362` `_heuristic_questions`; `COPILOT_AND_CHAT_ARCHITECTURE.md` §3 mapping table; BAS-03/BAS-04. |
| Exact problem | Legacy reviews mix document evidence with canned advice without telling the user. |
| Reason this matters | Prevents fabricated findings; keeps the persona value. |
| Target behaviour | `validateReview`, `app/js/storage/repos/reviews.js`; `createReview(snapshotId, personaId)` loads snapshot items/chunks, calls `runReview`, stores; reviews immutable; re-run creates new with `previousReviewId`. |
| Smallest safe change | Storage wiring. |
| Explicit exclusions | No UI (UI-06). |
| Files expected to change | `app/js/storage/repos/reviews.js` (new), `app/js/domain/validate.js`, `app/js/review/create.js` (new), `tests/e2e/reviews-store.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `createReview`, `validateReview`. |
| Dependencies | MIG-02A, DAT-07. |
| Prerequisite decisions | ADR-008, ADR-012. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes `reviews`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/reviews-store.spec.mjs` — stored review equals `runReview` output; put on existing id rejected. |
| Manual verification | None (UI-06). |
| Acceptance criteria | 1. Immutability enforced. 2. Snapshot linkage correct. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `MIG-02B: Persist reviews against snapshots` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `MIG-02B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| MIG-02B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from MIG-02 by validation V-03. |
| Required by | AI-04, CPL-01A, EXP-01A, UI-06 |

### UI-06 · Reviews view with labelled findings

| Field | Detail |
|---|---|
| Unique ID | UI-06 |
| Title | Reviews view with labelled findings |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §3. |
| Exact problem | Users can't run or read reviews in the new app. |
| Reason this matters | Core product feature. |
| Target behaviour | `app/js/ui/views/reviews.js`: choose snapshot + persona (from `personas/index.json`), Run review; review page grouped by output section with label badges, citations, the header 'Deterministic review: checklist plus keyword evidence. No AI was used.', and filter by label; list of past reviews per snapshot; 'Run again' creates a new review with `previousReviewId`. |
| Smallest safe change | Implement. |
| Explicit exclusions | No compare/diff of reviews (deferred). |
| Files expected to change | `app/js/ui/views/reviews.js`, `tests/e2e/reviews.spec.mjs` (new); `app/js/ui/router.js`, `app/js/ui/views/project.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderReviews`. |
| Dependencies | MIG-02B, UI-04. |
| Prerequisite decisions | ADR-008. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/reviews.spec.mjs` — run each persona on the sample; header present; every FACT has a citation link; checklist guidance visibly marked. |
| Manual verification | Edge: run two personas; read output. |
| Acceptance criteria | 1. Test passes. 2. No unlabelled statement rendered. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-06: Reviews view with labelled findings` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-06` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-06 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | AI-01, CPL-01B, EXP-01C, UI-07 |

### ODI-01 · OneDrive/SharePoint V1 input: synced-folder guidance and provenance

| Field | Detail |
|---|---|
| Unique ID | ODI-01 |
| Title | OneDrive/SharePoint V1 input: synced-folder guidance and provenance |
| Capability group | ONEDRIVE INPUT + SHAREPOINT INPUT |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no OneDrive/SharePoint code — assessment §5) |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V1. |
| Exact problem | Users with documents in OneDrive or SharePoint need a clear, approval-free way to import them, with provenance noting where they came from. |
| Reason this matters | Manual OneDrive/SharePoint workflow (P1 class). |
| Target behaviour | Import preview gains per-file option 'This file came from OneDrive / SharePoint' with optional 'Web link' field (validated as `https://` URL, stored as text, never fetched) → provenance `sourceSystem:'synced-folder'`, `userDeclaredOrigin:true`, `webUrl`. Read failures (`NotReadableError`) → `IMP-READ-FAIL` banner with Files On-Demand guidance text from §2. |
| Smallest safe change | Implement in import view and provenance builder. |
| Explicit exclusions | No Graph, no folder handles, no automatic detection of sync paths. |
| Files expected to change | `app/js/ui/views/import.js`, `app/js/domain/provenance.js`, `app/js/diagnostics/errors.js`, `tests/e2e/import-onedrive.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildProvenance` (`userDeclaredOrigin`, `webUrl`). |
| Dependencies | IMP-02B. |
| Prerequisite decisions | ADR-019 (V3 deferred). |
| External approvals | None. |
| Data-boundary impact | None: link stored, never requested. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/import-onedrive.spec.mjs` — ticked origin stored in provenance; `javascript:` link rejected; simulated read error shows guidance. |
| Manual verification | Owner imports a file from their synced OneDrive folder in Edge on the corporate laptop; records result. |
| Acceptance criteria | 1. Test passes. 2. Manual corporate-laptop check recorded (OneDrive client behaviour is UNVERIFIED until then). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `ODI-01: OneDrive/SharePoint V1 input: synced-folder guidance and provenance` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `ODI-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| ODI-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-26 (help text belongs to DOC-02 only; removes ambiguous 'new or existing' file). |
| Required by | — |

### EXP-01A · Export builders: manifest, Markdown and JSON (pure)

| Field | Detail |
|---|---|
| Unique ID | EXP-01A |
| Title | Export builders: manifest, Markdown and JSON (pure) |
| Capability group | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy (diagram download only — assessment §6) |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V1. |
| Exact problem | Users can't take results out of the app in shareable formats. |
| Reason this matters | Manual OneDrive/SharePoint output workflow; prerequisite for Copilot packages. |
| Target behaviour | `app/js/exports/manifest.js` (`buildManifest({project, sources, items, reviews, files:[{name, sha256}]})`), `exports/markdown.js` (`toMarkdown`), `exports/json.js` (`toJson`, includes manifest). Pure functions. |
| Smallest safe change | Implement with unit tests. |
| Explicit exclusions | No HTML (EXP-01B), no UI (EXP-01C). |
| Files expected to change | `app/js/exports/manifest.js`, `app/js/exports/markdown.js`, `app/js/exports/json.js`, `tests/unit/exports.test.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildManifest`, `toMarkdown`, `toJson`. |
| Dependencies | MIG-02B, BAK-01. |
| Prerequisite decisions | ADR-024. |
| External approvals | None. |
| Data-boundary impact | None (pure). |
| Storage or migration impact | None. |
| Security and privacy impact | Markdown output escapes `<`, `>` and backticks in user strings (unit test). |
| Automated tests | `npm run test:unit` manifest hashes; hostile names escaped. |
| Manual verification | None. |
| Acceptance criteria | 1. Unit tests pass. 2. Manifest sha256 values recomputable. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `EXP-01A: Export builders: manifest, Markdown and JSON (pure)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `EXP-01A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| EXP-01A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from EXP-01 by validation V-04. |
| Required by | CPL-01A, EXP-01B |

### EXP-01B · Self-contained HTML report export

| Field | Detail |
|---|---|
| Unique ID | EXP-01B |
| Title | Self-contained HTML report export |
| Capability group | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy (diagram download only — assessment §6) |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V1. |
| Exact problem | Users can't take results out of the app in shareable formats. |
| Reason this matters | Manual OneDrive/SharePoint output workflow; prerequisite for Copilot packages. |
| Target behaviour | `exports/html.js` (`toHtml(model)`): builds a detached document via `document.implementation.createHTMLDocument`, fills it with `h()`-equivalent DOM calls, inline `<style>` allowed only inside the exported file, an 'About this export' table showing the manifest, then serialises `documentElement.outerHTML`. SEC-01 allow-list gains exactly one entry: `outerHTML` **read** in `app/js/exports/html.js`. |
| Smallest safe change | Implement + allow-list entry. |
| Explicit exclusions | No UI wiring. |
| Files expected to change | `app/js/exports/html.js`, `tests/e2e/export-html.spec.mjs` (new); `tools/check-forbidden-apis.mjs`, `tests/unit/check-forbidden-apis.test.mjs`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `toHtml`. |
| Dependencies | EXP-01A. |
| Prerequisite decisions | ADR-024. |
| External approvals | None. |
| Data-boundary impact | None (in-memory). |
| Storage or migration impact | None. |
| Security and privacy impact | Exported HTML contains no `<script>` and no `on*` attributes even with hostile fixture names (test parses output). |
| Automated tests | `npm run test:e2e -- tests/e2e/export-html.spec.mjs`; `npm run test:unit` allow-list test (outerHTML assignment still rejected everywhere). |
| Manual verification | Open a generated HTML file in Edge offline; print to PDF. |
| Acceptance criteria | 1. No script/handlers in output. 2. `outerHTML =` assignment still fails the check. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `EXP-01B: Self-contained HTML report export` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `EXP-01B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| EXP-01B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from EXP-01 by validation V-04. |
| Required by | EXP-01C |

### EXP-01C · Exports view, boundary notice and export records

| Field | Detail |
|---|---|
| Unique ID | EXP-01C |
| Title | Exports view, boundary notice and export records |
| Capability group | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | PARTIAL in legacy (diagram download only — assessment §6) |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V1. |
| Exact problem | Users can't take results out of the app in shareable formats. |
| Reason this matters | Manual OneDrive/SharePoint output workflow; prerequisite for Copilot packages. |
| Target behaviour | `app/js/ui/views/exports.js` (choose whole project / one review; formats HTML, Markdown, JSON; file names `<project>-report-v<seq>-<yyyymmdd>.<ext>`), boundary notice dialog before the first export per session (wording `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V1, 'Don't show again this session'), `repos/exports.js` storing ExportRecord metadata only. |
| Smallest safe change | Implement UI and record. |
| Explicit exclusions | No ZIP (EXP-02), no save picker (EXP-03). |
| Files expected to change | `app/js/ui/views/exports.js`, `app/js/storage/repos/exports.js`, `tests/e2e/exports.spec.mjs` (new); `app/js/domain/validate.js`, `app/js/ui/router.js`, `app/js/ui/views/project.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderExports`, `recordExport`. |
| Dependencies | EXP-01B, UI-06. |
| Prerequisite decisions | ADR-024. |
| External approvals | None. |
| Data-boundary impact | User-initiated file creation; notice explains that saving into OneDrive/SharePoint copies content to Microsoft 365. |
| Storage or migration impact | None. |
| Security and privacy impact | Exported HTML must contain no script; test parses export and asserts zero `<script>` and no `on*` attributes even with hostile fixture names. |
| Automated tests | `npm run test:e2e -- tests/e2e/exports.spec.mjs` — notice once per session; three downloads; ExportRecord contains no content. |
| Manual verification | Export to Downloads, then move into a synced OneDrive folder; confirm the notice was understandable. |
| Acceptance criteria | 1. Notice shown before first export. 2. ExportRecord has no content fields. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `EXP-01C: Exports view, boundary notice and export records` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `EXP-01C` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| EXP-01C \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from EXP-01 by validation V-04. |
| Required by | EXP-02, EXP-03, UI-07 |

### EXP-02 · Stored ZIP writer for multi-file exports

| Field | Detail |
|---|---|
| Unique ID | EXP-02 |
| Title | Stored ZIP writer for multi-file exports |
| Capability group | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT |
| Priority | P2 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V1 step 3 (download package). |
| Exact problem | Packages with several files (manifest + content) need a single download. |
| Reason this matters | Prerequisite for the Copilot package. |
| Target behaviour | `app/js/exports/zip-write.js` (`buildZip([{name, bytes}]) → Blob`, method stored (0), CRC-32 table, UTF-8 names flag, rejects names with `..` or leading `/`); exports view 'Download all as ZIP'. |
| Smallest safe change | Implement with unit tests reading the result back via `zip-read.js`. |
| Explicit exclusions | No compression. |
| Files expected to change | `app/js/exports/zip-write.js`, `tests/unit/zip-write.test.mjs` (new); `app/js/ui/views/exports.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildZip`, `crc32`. |
| Dependencies | EXP-01C, IMP-06. |
| Prerequisite decisions | ADR-009. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — round trip with `readZipEntries`; CRC-32 known vectors; macOS `unzip -t` on output in test (skip if unavailable). |
| Manual verification | Open the ZIP in Windows Explorer and macOS Finder. |
| Acceptance criteria | 1. Round trip passes. 2. Opens in both OS file managers (manual). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `EXP-02: Stored ZIP writer for multi-file exports` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `EXP-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| EXP-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CPL-01B |

### CPL-01A · Copilot package builder and clipboard splitter (pure)

| Field | Detail |
|---|---|
| Unique ID | CPL-01A |
| Title | Copilot package builder and clipboard splitter (pure) |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P2 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no Copilot code — assessment §7) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V1; ADR-007, ADR-025 (all users licensed, desktop/Teams/SharePoint surfaces, no API). |
| Exact problem | Users with M365 Copilot have no grounded way to use it on their project material. |
| Reason this matters | Manual Copilot package workflow (OD-6, ADR-025). |
| Target behaviour | `app/js/exports/copilot-package.js`: `buildCopilotPackage({purpose, question, items, evidence, sources}) → {files:{'PROMPT.md','CONTEXT.md','SOURCES.json','context.json'}, packageId, sha256}`; stable IDs `[S<n>-P<m>]` mapped to chunkIds in `context.json`; four templates; `splitForClipboard(text, limit)` → parts ≤ limit, never splitting inside a passage, each prefixed 'Part i of n – reply "continue"'. |
| Smallest safe change | Pure module + unit tests. |
| Explicit exclusions | No UI, no clipboard calls. |
| Files expected to change | `app/js/exports/copilot-package.js`, `tests/unit/copilot-package.test.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildCopilotPackage`, `splitForClipboard`. |
| Dependencies | EXP-01A, CHT-03, MIG-02B. |
| Prerequisite decisions | ADR-007, ADR-025. |
| External approvals | None. |
| Data-boundary impact | None (pure). |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — IDs consistent; split invariants. |
| Manual verification | None. |
| Acceptance criteria | 1. Every ID in CONTEXT.md exists in context.json. 2. Parts ≤ limit. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CPL-01A: Copilot package builder and clipboard splitter (pure)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-01A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-01A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from CPL-01 by validation V-05. |
| Required by | CPL-01B |

### CPL-01B · Prepare-for-Copilot dialog: clipboard copy and ZIP download

| Field | Detail |
|---|---|
| Unique ID | CPL-01B |
| Title | Prepare-for-Copilot dialog: clipboard copy and ZIP download |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P2 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (no Copilot code — assessment §7) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V1; ADR-007, ADR-025 (all users licensed, desktop/Teams/SharePoint surfaces, no API). |
| Exact problem | Users with M365 Copilot have no grounded way to use it on their project material. |
| Reason this matters | Manual Copilot package workflow (OD-6, ADR-025). |
| Target behaviour | `app/js/ui/components/copilot-dialog.js` opened from Ask, Review and Project pages: purpose, question, preview, character count vs `settings.copilotCharLimit` (default 12,000, BD-06), 'Copy to clipboard' (single or parts) via `navigator.clipboard.writeText` on click, 'Download package (ZIP)'; boundary notice adds: 'Copilot processes this under your organisation's Microsoft 365 terms' **and** 'Clipboard contents can be kept by clipboard history or synced by Windows clipboard sync; clear it after pasting.' |
| Smallest safe change | Implement UI. |
| Explicit exclusions | No Microsoft endpoints, no automation, no paste-back. |
| Files expected to change | `app/js/ui/components/copilot-dialog.js`, `tests/e2e/copilot-package.spec.mjs` (new); `app/js/ui/views/ask.js`, `app/js/ui/views/reviews.js`, `app/js/ui/views/project.js`, `app/js/domain/validate.js` (settings). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `openCopilotDialog`. |
| Dependencies | CPL-01A, EXP-02, UI-06. |
| Prerequisite decisions | ADR-007, ADR-025. |
| External approvals | None. |
| Data-boundary impact | User copies/downloads; clipboard is a boundary (history/sync) — stated in the notice. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/copilot-package.spec.mjs` — Chromium only for clipboard read-back (WebKit: download path only); ZIP contains 4 files. |
| Manual verification | Owner pastes a package into Copilot (desktop app and Teams) on a non-confidential sample project; records whether the character limit default is acceptable and whether Copilot cites the IDs. |
| Acceptance criteria | 1. Tests pass. 2. Manual Copilot trial recorded with observed input limit (BD-06; UNVERIFIED until done). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CPL-01B: Prepare-for-Copilot dialog: clipboard copy and ZIP download` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-01B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-01B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from CPL-01 by validation V-05. |
| Required by | CPL-02, DOC-02, EXP-03 |

### CPL-02 · Copilot paste-back stored as Draft with citation-ID checks

| Field | Detail |
|---|---|
| Unique ID | CPL-02 |
| Title | Copilot paste-back stored as Draft with citation-ID checks |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P2 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V1 step 5–6. |
| Exact problem | Copilot output brought back must never be mistaken for document facts. |
| Reason this matters | Prevents fabricated answers entering the record. |
| Target behaviour | 'Add Copilot reply' on a package's record: textarea; on save → `Draft {origin:'copilot-pasted', packageId, packageSha256, createdAt, statements[]}` where paragraphs become statements labelled `NEEDS_CONFIRMATION` (or `RECOMMENDATION`/`INFERENCE` when the paragraph starts with that word), never `FACT`; citation IDs found by regex `\[S\d+-P\d+\]` marked resolves/unknown; per statement actions Accept as Recommendation (records `acceptedBy` = free-text name entered once in Settings, `acceptedAt`), Edit (keeps original + edited), Discard. Drafts list per project. |
| Smallest safe change | Implement `repos/drafts.js`, `validateDraft`, `ui/views/drafts.js`. |
| Explicit exclusions | No automatic merging into items or reviews. |
| Files expected to change | `app/js/storage/repos/drafts.js`, `app/js/ui/views/drafts.js`, `app/js/domain/draft.js`, `tests/unit/draft.test.mjs`, `tests/e2e/drafts.spec.mjs` (new); `app/js/domain/validate.js`, `app/js/ui/router.js`, `app/js/ui/views/project.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `parsePastedReply`, `acceptAsRecommendation`. |
| Dependencies | CPL-01B. |
| Prerequisite decisions | ADR-008, ADR-025. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | Writes `drafts`. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — a paragraph starting 'Fact:' still becomes NEEDS_CONFIRMATION; unknown IDs flagged. `npm run test:e2e -- tests/e2e/drafts.spec.mjs`. |
| Manual verification | Paste a real Copilot reply from the CPL-01B trial. |
| Acceptance criteria | 1. No code path creates FACT from pasted text (unit test + grep). 2. Original pasted text preserved verbatim. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CPL-02: Copilot paste-back stored as Draft with citation-ID checks` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CPL-03 |

### BLD-02 · Local launchers for Windows and macOS (double-click start)

| Field | Detail |
|---|---|
| Unique ID | BLD-02 |
| Title | Local launchers for Windows and macOS (double-click start) |
| Capability group | BUILD AND STARTUP |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | BROKEN in legacy (terminal-only start: `pip install`, `export`, `python server.py`) |
| Evidence | README Quick Start; OD-1; ADR-005, ADR-022, ADR-024; `TARGET_ARCHITECTURE.md` §26. |
| Exact problem | Non-technical users cannot start the app without a terminal. |
| Reason this matters | Predictable start-up; organisation-neutral delivery route (ADR-024). |
| Target behaviour | `launch/start-windows.bat` (finds `py -3` or `python`; if missing shows a plain message and pauses; runs `python -m http.server 8765 --bind 127.0.0.1 --directory "%~dp0app"` and opens `http://127.0.0.1:8765/` via `start`), `launch/start-macos.command` (same with `python3`, `open`), both refusing to start if port 8765 is busy (Windows: `netstat -ano \| findstr ":8765 " \| findstr LISTENING`; macOS: `lsof -nP -iTCP:8765 -sTCP:LISTEN`) with message 'The app may already be running – open http://127.0.0.1:8765/'; `launch/README-START.txt` (plain language, SmartScreen/Gatekeeper notes, 'keep this window open while using the app', 'your data lives in this browser at this address'). |
| Smallest safe change | Create files; release zip layout puts `app/` next to `launch/` files. |
| Explicit exclusions | No installer, no auto-start, no other port. |
| Files expected to change | `launch/start-windows.bat`, `launch/start-macos.command`, `launch/README-START.txt` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | BLD-01. |
| Prerequisite decisions | ADR-005, ADR-022, ADR-024. |
| External approvals | None. |
| Data-boundary impact | Binds loopback only. |
| Storage or migration impact | None. |
| Security and privacy impact | Must bind 127.0.0.1 (never 0.0.0.0); test asserts the command text. |
| Automated tests | `tests/unit/launchers.test.mjs` asserts both scripts contain `--bind 127.0.0.1`, port 8765 and `--directory`. |
| Manual verification | Owner double-clicks the launcher on Windows (corporate laptop) and macOS; records any policy block. |
| Acceptance criteria | 1. Unit test passes. 2. Manual start recorded on at least one OS (other OS UNVERIFIED if unavailable). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `BLD-02: Local launchers for Windows and macOS (double-click start)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `BLD-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| BLD-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-24 (port check method specified). |
| Required by | DOC-02, REL-01A |

### UI-07 · Accessibility verification pass on main journeys

| Field | Detail |
|---|---|
| Unique ID | UI-07 |
| Title | Accessibility verification pass on main journeys |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | UNKNOWN in legacy (likely failing); DOCUMENTED ONLY in target |
| Evidence | `TARGET_ARCHITECTURE.md` §28. |
| Exact problem | Accessibility isn't verified. |
| Reason this matters | Dependable daily use for all users. |
| Target behaviour | `tests/e2e/a11y.spec.mjs`: keyboard-only journeys (create project → import → items → ask → review → export → backup) without mouse; every interactive element reachable and has an accessible name (for each `button, a, input, select, textarea` locator: `await expect(loc).toHaveAccessibleName(/\S/)`; `page.accessibility` is deprecated and must not be used); `tools/check-contrast.mjs` verifies token pairs in `tokens.css` ≥ 4.5:1 (light and dark); 200 % zoom/320 px viewport test has no horizontal scroll on main views; reduced-motion disables transitions. |
| Smallest safe change | Add the tests and the contrast tool. **Do not fix defects in this item**: if tests fail, mark nothing as skipped, stop, and list each defect (view, element, rule) in the report so the reviewer can create one fix item per defect. |
| Explicit exclusions | No redesign. |
| Files expected to change | `tests/e2e/a11y.spec.mjs`, `tools/check-contrast.mjs` (new); `package.json` (check script). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | UI-06, CHT-03, EXP-01C, BAK-02. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/a11y.spec.mjs`; `npm run check`. |
| Manual verification | Owner navigates one journey with keyboard only in Edge; tries Windows High Contrast. |
| Acceptance criteria | 1. Tests pass, or the item stops with a defect list (item not Done until fix items pass). 2. Manual keyboard journey completed. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-07: Accessibility verification pass on main journeys` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-07` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-07 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-22 (open-ended 'fix defects found' removed; deprecated API replaced). |
| Required by | UI-08 |

### DOC-02 · In-app help: start, backup, restore, rollback, data boundary, Copilot how-to

| Field | Detail |
|---|---|
| Unique ID | DOC-02 |
| Title | In-app help: start, backup, restore, rollback, data boundary, Copilot how-to |
| Capability group | DOCUMENTATION |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | DOCUMENTED ONLY (instructions exist only in architecture docs) |
| Evidence | `DATA_AND_STORAGE_ARCHITECTURE.md` §8 rollback; `COPILOT_AND_CHAT_ARCHITECTURE.md` §6; OD-1. |
| Exact problem | Non-technical users need plain-language guidance inside the app. |
| Reason this matters | Documented limitations; recoverability. |
| Target behaviour | `app/js/ui/views/help.js` with sections (plain language, ≤ 150 words each): Starting the app; Where your data lives (this browser, this address); Backing up; Restoring; If the app breaks (reset.html, rollback steps exactly as `DATA_AND_STORAGE_ARCHITECTURE.md` §8); What leaves your device (nothing unless you export, copy for Copilot, or turn on OpenRouter; the app checks a small kill-switch file on its own web address at start-up); Using Copilot (desktop app, Teams, SharePoint; paste-back) — written from the recorded CPL-01B trial (BD-06); if no trial is recorded, the section says 'Not yet tested in your organisation'; Importing from OneDrive/SharePoint. Content is static text in the module (no fetched HTML). |
| Smallest safe change | Implement. |
| Explicit exclusions | No external links other than none (all text in-app). |
| Files expected to change | `app/js/ui/views/help.js` (new or extended), `app/js/ui/router.js`, `tests/e2e/help.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `renderHelp`. |
| Dependencies | PWA-04, BAK-03, CPL-01B, BLD-02. |
| Prerequisite decisions | ADR-024 (no host-specific wording). |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/help.spec.mjs` — all sections present; no `github` string in help text. |
| Manual verification | Owner reads help and confirms it is understandable. |
| Acceptance criteria | 1. Owner sign-off on wording. 2. No hosting-specific assumptions. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DOC-02: In-app help: start, backup, restore, rollback, data boundary, Copilot how-to` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DOC-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DOC-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-25 (no unverified Copilot claims in help; kill-switch request disclosed). |
| Required by | DOC-03 |

### REL-01A · Release process: versioning, release checklist and release zip

| Field | Detail |
|---|---|
| Unique ID | REL-01A |
| Title | Release process: versioning, release checklist and release zip |
| Capability group | RELEASE AND OPERATIONS |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | BROKEN/absent (no releases, D-11) |
| Evidence | `TARGET_ARCHITECTURE.md` §25; ADR-024. |
| Exact problem | There is no controlled way to publish a version or roll back. |
| Reason this matters | Controlled releases (charter definition of production-ready). |
| Target behaviour | `docs/release/RELEASE_CHECKLIST.md` (bump `app/version.js`; regenerate precache; CI green; manual smoke checklist TST-03; tag `vX.Y.Z` by owner), `.github/workflows/release.yml` on tag `v*`: all checks, build `pdae-vX.Y.Z.zip` (`app/` + `launch/` + `RELEASE_NOTES.md` + `SHA256SUMS.txt`), attach to a GitHub release (release assets on a private repo stay private). `RELEASE_NOTES.md` template (changes, schema change yes/no, data-boundary changes, known limitations). |
| Smallest safe change | Create workflow and docs. |
| Explicit exclusions | No static deployment (REL-01B). |
| Files expected to change | `.github/workflows/release.yml`, `docs/release/RELEASE_CHECKLIST.md`, `RELEASE_NOTES.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | Workflow jobs `verify`, `package`. |
| Dependencies | TST-02, PWA-03, BLD-02, TST-03. |
| Prerequisite decisions | ADR-005, ADR-024. |
| External approvals | None. |
| Data-boundary impact | Release assets visible to repository collaborators only while private. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Dry-run tag `v0.0.0-rc1` on a branch; zip contents and checksums verified. |
| Manual verification | Download the zip, run the launcher, app works offline after first load. |
| Acceptance criteria | 1. Zip contents and checksums verified. 2. No deployment step exists. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `REL-01A: Release process: versioning, release checklist and release zip` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `REL-01A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| REL-01A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from REL-01 by validation V-09. |
| Required by | DOC-03, ODI-02A, REL-01B |

### CLN-02 · Retire the legacy application (tag legacy-final, remove legacy code)

| Field | Detail |
|---|---|
| Unique ID | CLN-02 |
| Title | Retire the legacy application (tag legacy-final, remove legacy code) |
| Capability group | REPOSITORY CLEANUP |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | UNUSED by owner (Q-C); BROKEN/insecure (B-1, B-2, H-1–H-6) |
| Evidence | ADR-023; `REPOSITORY_CLEANUP_CANDIDATES.md` C-1–C-15; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §2. |
| Exact problem | Insecure, unused legacy code remains in the repository and must not be published. |
| Reason this matters | Single coherent source tree (charter §3); prerequisite for making the repo public (ADR-023). |
| Target behaviour | Owner creates tag `legacy-final` on the commit before removal. Removed: `server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/` (YAML now in JSON), `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `tests/__init__.py`, `tests/conftest.py`, `outputs/.gitkeep`, `.env.example`, `.kiro/`. Kept: `sample_data/` (until CLN-03 decides), `tools/legacy-golden.py` (marked 'requires legacy-final checkout'), golden files. `.gitignore` Python entries removed. |
| Smallest safe change | `git rm -r` the listed paths in one commit; update `tools/legacy-golden.py` header with `git worktree add ../legacy legacy-final` instructions. |
| Explicit exclusions | Do not touch `app/`, `tests/unit`, `tests/e2e`, `tests/fixtures`, `docs/`, `_archive/` (CLN-03). |
| Files expected to change | Deletions listed above; `.gitignore`; `tools/legacy-golden.py` (header only); `README.md` (remove the 'Legacy app' section, add 'Previous version: `git checkout legacy-final`'). |
| Files that must not change | `app/**`, `tests/unit/**`, `tests/e2e/**`, `tests/fixtures/**`, `tools/*.mjs`, `docs/**`, `_archive/**`, `.github/workflows/*`. |
| Functions, symbols or components likely affected | Tag `legacy-final`. |
| Dependencies | MIG-01A, MIG-02A, BAS-03, BAS-04, IMP-04, DOC-01. |
| Prerequisite decisions | ADR-023. **Owner confirms nobody runs the legacy app.** |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Positive: removes B-1/B-2/H-1–H-6 code from the tree (still in history — publication note in REL-02). |
| Automated tests | `npm run check`; `npm run test:unit`; `npm run test:e2e` (full) all green after removal; `git grep -n 'import .*processors\\|server.py'` in remaining files returns nothing relevant. |
| Manual verification | Owner confirms `git checkout legacy-final` in a separate worktree still shows the old app files. |
| Acceptance criteria | 1. Full test suite green. 2. Tag exists. 3. Only listed paths removed. |
| Rollback | `git revert` of the removal commit restores all files; tag remains. |
| Recommended commit boundary | One commit titled `CLN-02: Retire the legacy application (tag legacy-final, remove legacy code)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CLN-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CLN-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CLN-03, DOC-03, REL-02 |

### DOC-03 · Rewrite README for the new app

| Field | Detail |
|---|---|
| Unique ID | DOC-03 |
| Title | Rewrite README for the new app |
| Capability group | DOCUMENTATION |
| Priority | P1 |
| Phase | 2 (PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1) |
| Current classification | BROKEN (README describes legacy) |
| Evidence | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §11. |
| Exact problem | README doesn't describe the app that exists after cutover. |
| Reason this matters | Documented limitations; public readiness. |
| Target behaviour | README sections: what it is; who it's for; how to use (hosted URL if your organisation provides one, or release zip + launcher); where data lives; what leaves the device; Copilot use; limitations (browser support matrix, Safari eviction, no multi-device sync, no Graph); development (npm scripts); licence; previous version (`legacy-final`). No claims without a test or manual check backing them. |
| Smallest safe change | Rewrite. |
| Explicit exclusions | No marketing claims; no screenshots requirement. |
| Files expected to change | `README.md`. |
| Files that must not change | Everything except README.md, including legacy paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | CLN-02, REL-01A, DOC-02. |
| Prerequisite decisions | ADR-024. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Manual link check; `grep -n 'Docker\\|server.py\\|pip install' README.md` returns nothing. |
| Manual verification | Owner reads and approves. |
| Acceptance criteria | 1. Owner approval. 2. Every capability claim maps to a Done backlog item. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DOC-03: Rewrite README for the new app` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DOC-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DOC-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | REL-02 |

## Phase 3 – Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2

### REL-02 · Pre-publication checklist before making the repository public

| Field | Detail |
|---|---|
| Unique ID | REL-02 |
| Title | Pre-publication checklist before making the repository public |
| Capability group | RELEASE AND OPERATIONS |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY (OD-5 intent) |
| Evidence | ADR-016, ADR-023; `SECURITY_PRIVACY_ASSESSMENT.md` §4 L-5, §6. |
| Exact problem | Publishing could expose legacy vulnerabilities, personal data in history, or unlicensed content. |
| Reason this matters | Prevents external leakage of personal/identifying data. |
| Target behaviour | `docs/release/PUBLICATION_CHECKLIST.md` executed and signed by the owner: LICENSE present; CLN-02 done; secret scan of full history repeated (record command and result); commit author names/emails in history acknowledged as becoming public (list distinct identities via `git shortlog -sne --all`); remote branches reviewed (owner decides which to delete); `.claude/prompts` and docs reviewed for personal or employer-identifying content; fixtures synthetic. |
| Smallest safe change | Create checklist; owner executes; model only prepares commands. |
| Explicit exclusions | Model must not change repository visibility, delete branches or rewrite history. |
| Files expected to change | `docs/release/PUBLICATION_CHECKLIST.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | CLN-02, DOC-03. |
| Prerequisite decisions | ADR-016, ADR-023. |
| External approvals | Owner (and employer policy, if applicable) approves publication. |
| Data-boundary impact | Repository becomes public: code and history leave private scope. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Secret-scan command output recorded in the checklist. |
| Manual verification | Owner completes every checkbox. |
| Acceptance criteria | 1. All checkboxes ticked with dates. 2. Visibility change performed by the owner only. |
| Rollback | Repository can be made private again, but anything already cloned/indexed can't be recalled — hence the checklist. |
| Recommended commit boundary | One commit titled `REL-02: Pre-publication checklist before making the repository public` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `REL-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| REL-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | REL-01B |

### REL-01B · Optional static deployment job (hosting-neutral)

| Field | Detail |
|---|---|
| Unique ID | REL-01B |
| Title | Optional static deployment job (hosting-neutral) |
| Capability group | RELEASE AND OPERATIONS |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | BROKEN/absent (no releases, D-11) |
| Evidence | `TARGET_ARCHITECTURE.md` §25; ADR-024. |
| Exact problem | There is no controlled way to publish a version or roll back. |
| Reason this matters | Controlled releases (charter definition of production-ready). |
| Target behaviour | Job `deploy-static` in `release.yml` publishing `app/` to GitHub Pages only when repository variable `DEPLOY_PAGES == 'true'`; `docs/release/STATIC_HOSTING.md` describing generic deployment of `app/` to any static HTTPS host (GitHub Pages as one example). **GitHub Pages sites are publicly reachable** (except private Pages on Enterprise plans), so this job publishes the application code to the internet. |
| Smallest safe change | Add job and doc. |
| Explicit exclusions | No custom domain; no host-specific code in `app/`. |
| Files expected to change | `.github/workflows/release.yml`, `docs/release/STATIC_HOSTING.md` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | Workflow job `deploy-static`. |
| Dependencies | REL-01A, REL-02. |
| Prerequisite decisions | ADR-005, ADR-024. |
| External approvals | Owner enables Pages (permitted in owner's organisation, Q-D) after REL-02. |
| Data-boundary impact | Publishes application code (never user data) to a public URL. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | Job skipped when variable unset (workflow run log). |
| Manual verification | Owner opens the deployed URL, installs, works offline. |
| Acceptance criteria | 1. Skipped by default. 2. Deployed app passes the TST-03 smoke checklist. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `REL-01B: Optional static deployment job (hosting-neutral)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `REL-01B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| REL-01B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from REL-01 by validation V-09. |
| Required by | — |

### AI-01 · AI provider interface, consent token and egress preview (no network)

| Field | Detail |
|---|---|
| Unique ID | AI-01 |
| Title | AI provider interface, consent token and egress preview (no network) |
| Capability group | SECURITY AND PRIVACY |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY (legacy sends full context without per-send notice — C4, M-8) |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §4; ADR-006. |
| Exact problem | Before any external AI exists, the guard that prevents silent transmission must exist. |
| Reason this matters | Prevents external leakage (charter §4). |
| Target behaviour | `app/js/ai/provider.js` (interface docs + `getProvider()` returning `none` unless Settings AI enabled), `app/js/ai/none.js`, `app/js/ai/consent.js` (`createConsent(bodySha256)` callable only from the egress dialog's Send handler — enforced by passing a private symbol obtained by the dialog module; `consume(token, bodySha256)` single-use), `app/js/ui/components/egress-dialog.js` (destination, model, passage count, characters, source list, collapsible exact JSON, warning text from §4, Send/Cancel); Settings → AI section: off by default, enable toggle with explanation; key field (password input, memory only, 'kept until you close the tab'). |
| Smallest safe change | Implement without any network call. |
| Explicit exclusions | No OpenRouter adapter (AI-02). |
| Files expected to change | `app/js/ai/provider.js`, `app/js/ai/none.js`, `app/js/ai/consent.js`, `app/js/ui/components/egress-dialog.js`, `tests/unit/consent.test.mjs`, `tests/e2e/ai-settings.spec.mjs` (new); `app/js/ui/views/settings.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `getProvider`, `createConsent`, `consume`, `openEgressDialog`. |
| Dependencies | CHT-03, UI-06. |
| Prerequisite decisions | ADR-006. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Key never written to storage, logs, backups, exports (test greps IndexedDB and backup output after entering a dummy key `sk-or-TESTKEY`). |
| Automated tests | `npm run test:unit` — consent reused → rejected; mismatched hash → rejected. `npm run test:e2e -- tests/e2e/ai-settings.spec.mjs` — AI off by default; after entering key and reload, key gone; backup contains no `sk-or-`. |
| Manual verification | None. |
| Acceptance criteria | 1. Tests pass. 2. No `fetch` added (`npm run check`). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `AI-01: AI provider interface, consent token and egress preview (no network)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `AI-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| AI-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | AI-02 |

### AI-02 · OpenRouter adapter behind consent (with browser CORS spike)

| Field | Detail |
|---|---|
| Unique ID | AI-02 |
| Title | OpenRouter adapter behind consent (with browser CORS spike) |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY (legacy Python adapter `ai_backends/openrouter_backend.py`) |
| Evidence | `ai_backends/openrouter_backend.py:24,98-106`; OD-6; ADR-006 (CORS assumption). |
| Exact problem | The approved external AI provider isn't available in the browser app. |
| Reason this matters | OD-6. |
| Target behaviour | Spike first: from the served app with a test key, confirm `POST https://openrouter.ai/api/v1/chat/completions` succeeds cross-origin; record result in `docs/backlog/DECISION_REGISTER.md`. If it fails, STOP and report (do not add a proxy). Then `app/js/ai/openrouter.js` (`complete(request, consentToken)`: verifies token via `consume`, sends only `model`, `messages`, `temperature`, `response_format` where supported; headers `Authorization`, `Content-Type` only; 60 s `AbortController` timeout; maps errors to `AI-NET` / `AI-HTTP-<status>`; returns raw text). Only file allowed to `fetch` an external origin (SEC-01 allow-list already covers it). |
| Smallest safe change | Implement after successful spike. |
| Explicit exclusions | No other providers; no retries; no streaming; no key persistence. |
| Files expected to change | `app/js/ai/openrouter.js` (new), `app/js/ai/provider.js`, `tests/e2e/ai-network.spec.mjs` (new), `docs/backlog/DECISION_REGISTER.md` (append spike result). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `complete`. |
| Dependencies | AI-01. |
| Prerequisite decisions | ADR-006 (spike outcome may supersede). |
| External approvals | Owner confirms their organisation permits sending the chosen content classes to OpenRouter (stated in the egress warning; not technically enforceable). |
| Data-boundary impact | **Changes the data boundary**: device → OpenRouter → model provider, only per consented request. |
| Storage or migration impact | None. |
| Security and privacy impact | Network interception test proves no request without consent. |
| Automated tests | `npm run test:e2e -- tests/e2e/ai-network.spec.mjs` — `page.route('https://openrouter.ai/**')` records requests: zero requests before Send; exactly one after; body equals previewed JSON; no `HTTP-Referer` header. |
| Manual verification | Owner runs one Ask with a non-confidential sample and a real key. |
| Acceptance criteria | 1. Spike result recorded. 2. Interception test passes. 3. Manual call succeeds or failure is reported. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `AI-02: OpenRouter adapter behind consent (with browser CORS spike)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `AI-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| AI-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | AI-03 |

### AI-03 · AI-assisted Ask with response validation

| Field | Detail |
|---|---|
| Unique ID | AI-03 |
| Title | AI-assisted Ask with response validation |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §5. |
| Exact problem | AI output must be checked against evidence before display. |
| Reason this matters | Prevents fabricated answers when AI is enabled. |
| Target behaviour | `app/js/ai/validate.js` (`validateAiResponse(raw, sentChunks) → {statements, problems}` per §5 rules 1–5 using `downgradeUnverified`); Ask view gains 'Ask AI using these passages' (top-k = 8, char cap from settings) → egress dialog → `complete` → validate → display with origin badge 'AI (OpenRouter · model)', label badges, citations, 'Compare with evidence' toggle; stored as `Answer {origin:'openrouter'}`. |
| Smallest safe change | Implement. |
| Explicit exclusions | No whole-project context; no conversation memory. |
| Files expected to change | `app/js/ai/validate.js`, `tests/unit/ai-validate.test.mjs`, `tests/e2e/ai-ask.spec.mjs` (new); `app/js/ui/views/ask.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `validateAiResponse`, `askWithAi`. |
| Dependencies | AI-02. |
| Prerequisite decisions | ADR-006, ADR-008. |
| External approvals | None. |
| Data-boundary impact | As AI-02. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` — invented quote downgraded; malformed JSON → Draft NEEDS_CONFIRMATION; citation to unsent chunk dropped. `npm run test:e2e -- tests/e2e/ai-ask.spec.mjs` with mocked route responses. |
| Manual verification | Owner compares one AI answer with its evidence. |
| Acceptance criteria | 1. No FACT displayed without verified quote (unit + e2e). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `AI-03: AI-assisted Ask with response validation` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `AI-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| AI-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | AI-04 |

### AI-04 · AI-assisted review (optional) per persona section

| Field | Detail |
|---|---|
| Unique ID | AI-04 |
| Title | AI-assisted review (optional) per persona section |
| Capability group | CHAT AND RETRIEVAL |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | PARTIAL in legacy (`personas/engine.py:256-306`, full-context send, silent fallback) |
| Evidence | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` C4, C6. |
| Exact problem | Persona reviews with AI should use minimal evidence and never silently fall back. |
| Reason this matters | OD-6 value with charter §9 safeguards. |
| Target behaviour | Reviews view: 'Ask AI to extend this review' → per persona section send the section's evidence (cited items/chunks, capped) and persona prompt template; validated like AI-03; stored as a separate `Review {method:'openrouter', previousReviewId}`; on failure show `AI-*` error and keep the deterministic review unchanged (no automatic fallback substitution). |
| Smallest safe change | Implement reusing AI-03 validation. |
| Explicit exclusions | No multi-persona synthesis. |
| Files expected to change | `app/js/review/ai-review.js`, `tests/unit/ai-review.test.mjs`, `tests/e2e/ai-review.spec.mjs` (new); `app/js/ui/views/reviews.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `extendReviewWithAi`. |
| Dependencies | AI-03, MIG-02B. |
| Prerequisite decisions | ADR-006, ADR-008. |
| External approvals | None. |
| Data-boundary impact | As AI-02. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` payload contains only section evidence; `npm run test:e2e -- tests/e2e/ai-review.spec.mjs` failure path leaves deterministic review intact. |
| Manual verification | Owner runs one AI-extended review on sample data. |
| Acceptance criteria | 1. Tests pass. 2. Payload size within cap. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `AI-04: AI-assisted review (optional) per persona section` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `AI-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| AI-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### IMP-07 · PDF import via vendored pdf.js

| Field | Detail |
|---|---|
| Unique ID | IMP-07 |
| Title | PDF import via vendored pdf.js |
| Capability group | FILE IMPORT |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | WORKING in legacy via pypdf (`processors/parsers/pdf_parser.py`); not in browser |
| Evidence | ADR-009; `MINIFIED_CODE_MIGRATION_STRATEGY.md` §7. |
| Exact problem | PDF documents can't be imported. |
| Reason this matters | Additional file type (P2). |
| Target behaviour | `app/vendor/pdfjs/<version>/` (unmodified official build files `pdf.min.mjs`, `pdf.worker.min.mjs`, licence), `app/vendor/VENDOR_MANIFEST.json` entry (name, version, Apache-2.0, source URL, SHA-256 per file), `tools/vendor-verify.mjs` (in `npm run check`), Trusted Types allow-list gains the worker path, CSP unchanged (`worker-src 'self'`), `parsers/pdf.js` (page → paragraphs; locator `page`; pages with no text → warning 'This page looks scanned; no text found'). pdf.js is configured with `isEvalSupported: false` (CSP forbids eval); the worker is created by app code as `new Worker(scriptURL('./vendor/pdfjs/<version>/pdf.worker.min.mjs'), {type:'module'})` and passed as `GlobalWorkerOptions.workerPort`, so Trusted Types sees only the allow-listed URL. |
| Smallest safe change | Add vendor files, manifest, verifier and parser. |
| Explicit exclusions | No OCR. No patching vendor files. |
| Files expected to change | `app/vendor/pdfjs/**`, `app/vendor/VENDOR_MANIFEST.json`, `tools/vendor-verify.mjs`, `app/js/import/parsers/pdf.js`, `tests/fixtures/synthetic/sample_scope.pdf` (generated by checked-in `tools/make-pdf-fixture.mjs` via Playwright `page.pdf()` from `scope.txt`), `tests/e2e/import-pdf.spec.mjs` (new); `app/js/core/trusted-types.js`, `app/js/import/pipeline.js`, `app/js/import/intake.js`, `package.json`, `tools/precache.mjs` (include vendor). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `parsePdf`, `verifyVendor`. |
| Dependencies | IMP-06, PWA-02B. |
| Prerequisite decisions | ADR-009. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Hash-pinned vendor code; tampering fails CI. |
| Automated tests | `npm run test:e2e -- tests/e2e/import-pdf.spec.mjs`; `npm run check` (vendor hashes). |
| Manual verification | Import a real text PDF and a scanned PDF in Edge. |
| Acceptance criteria | 1. Vendor verify passes; altering one byte fails. 2. Text matches fixture source. 3. Zero CSP or Trusted Types violations during PDF import (e2e listener). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `IMP-07: PDF import via vendored pdf.js` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `IMP-07` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| IMP-07 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Validation V-21 (security controls would otherwise break pdf.js). |
| Required by | — |

### ODI-02A · Schema migration 1 → 2: folderLinks store (migration only)

| Field | Detail |
|---|---|
| Unique ID | ODI-02A |
| Title | Schema migration 1 → 2: folderLinks store (migration only) |
| Capability group | DATA AND STORAGE |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V2. |
| Exact problem | Users must re-pick files manually each time documents in a synced folder change. |
| Reason this matters | Assisted refresh / folder workflow (P2). |
| Target behaviour | `app/js/storage/migrations/0002-folder-links.js` (`{from:1,to:2}` creating store `folderLinks` keyPath `id`, index `projectId`; `upRecord` no-op); `SCHEMA_VERSION = 2`; `schema.js` updated; trash store list gains `folderLinks`; backup/restore include it. RELEASE_NOTES entry 'Schema change 1 → 2'. |
| Smallest safe change | Migration only; no feature uses the store yet. |
| Explicit exclusions | No connector or UI. |
| Files expected to change | `app/js/storage/migrations/0002-folder-links.js` (new), `app/js/storage/migrations/index.js`, `app/version.js`, `app/js/storage/schema.js`, `app/js/storage/trash.js`, `app/js/storage/backup.js`, `app/js/storage/restore.js`, `RELEASE_NOTES.md`, `tests/e2e/migration-0002.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `MIGRATIONS[1]`. |
| Dependencies | PWA-03, BAK-03, REL-01A. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | Reads only inside the linked folder, only on Refresh. |
| Storage or migration impact | **Schema migration 1 → 2.** Release must use the PWA-03 schema notice. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/migration-0002.spec.mjs` — v1 DB with data upgrades with data intact; forced failure leaves v1; v1 backup restores into v2; v2 DB opened by a v1 build is read-only. |
| Manual verification | Owner updates the installed app via the update prompt and sees the schema notice; data intact. |
| Acceptance criteria | 1. All four migration cases pass. 2. Release notes flag the schema change. |
| Rollback | Revert commit; users on v2 data opening the v1 app get read-only mode (downgrade guard) and must restore a v1-era backup — documented in RELEASE_NOTES. |
| Recommended commit boundary | One commit titled `ODI-02A: Schema migration 1 → 2: folderLinks store (migration only)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `ODI-02A` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| ODI-02A \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from ODI-02 by validation V-08. |
| Required by | ODI-02B |

### ODI-02B · Linked folder connector with user-triggered refresh and changed-file preview

| Field | Detail |
|---|---|
| Unique ID | ODI-02B |
| Title | Linked folder connector with user-triggered refresh and changed-file preview |
| Capability group | ONEDRIVE INPUT + SHAREPOINT INPUT |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V2. |
| Exact problem | Users must re-pick files manually each time documents in a synced folder change. |
| Reason this matters | Assisted refresh / folder workflow (P2). |
| Target behaviour | `app/js/connectors/source-folder.js` (`isAvailable()` = `'showDirectoryPicker' in window`; `link()` stores handle + label; `refresh(link, {includeSubfolders=false})` requests read permission, lists one level (or depth ≤ 3, ≤ 500 files), returns New/Changed (lastModified or size differs, then confirmed by SHA-256)/Missing/Unchanged); preview screen with ticks; Changed → new source version with `supersedesSourceId`; Missing reported only; 'Unlink folder'. Hidden with explanatory note when unavailable. |
| Smallest safe change | Implement connector and UI on top of ODI-02A. |
| Explicit exclusions | No timers, no start-up scan, no deletion of sources. |
| Files expected to change | `app/js/connectors/source-folder.js`, `app/js/ui/views/folder-link.js`, `tests/e2e/folder-link.spec.mjs` (new); `app/js/ui/views/sources.js`, `app/js/domain/provenance.js` (`relativePath`). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `link`, `refresh`, `diffFolder`. |
| Dependencies | ODI-02A, IMP-02B. |
| Prerequisite decisions | ADR-003. |
| External approvals | None. |
| Data-boundary impact | Reads only inside the linked folder, only on Refresh. |
| Storage or migration impact | Uses `folderLinks` (ODI-02A); writes new source versions. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/folder-link.spec.mjs` (chromium; `showDirectoryPicker` stubbed via `page.addInitScript`; real picker UNVERIFIED in automation); WebKit shows fallback note. |
| Manual verification | Owner links a synced SharePoint folder on the corporate laptop, edits a file, refreshes, sees Changed. |
| Acceptance criteria | 1. Refresh only on click; reads only inside the linked folder (stub records calls). 2. Changed files create new versions, never overwrite. 3. Manual corporate check recorded. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `ODI-02B: Linked folder connector with user-triggered refresh and changed-file preview` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `ODI-02B` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| ODI-02B \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Validation note | Split from ODI-02 by validation V-08. |
| Required by | — |

### EXP-03 · V2 save picker export to a user-chosen folder

| Field | Detail |
|---|---|
| Unique ID | EXP-03 |
| Title | V2 save picker export to a user-chosen folder |
| Capability group | ONEDRIVE OUTPUT + SHAREPOINT OUTPUT |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §3 V2. |
| Exact problem | Users can't choose the save location (e.g. a synced library folder) from the app. |
| Reason this matters | Folder-based output workflow (P2). |
| Target behaviour | `app/js/connectors/dest-save-picker.js` (`showSaveFilePicker({suggestedName})`, write once on click; `AbortError` = cancel silently); used by exports, backup and Copilot package when available, falling back to `downloadBlob`; extra app confirmation when chosen name matches a previous export of a different project; ExportRecord `destination:'save-picker'` (no path). |
| Smallest safe change | Implement. |
| Explicit exclusions | No background writes; no folder enumeration. |
| Files expected to change | `app/js/connectors/dest-save-picker.js`, `tests/e2e/save-picker.spec.mjs` (new); `app/js/exports/download.js`, `app/js/ui/views/exports.js`, `app/js/ui/views/settings.js`, `app/js/ui/components/copilot-dialog.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `saveWithPicker`. |
| Dependencies | EXP-01C, CPL-01B. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | Same as EXP-01C (notice shown). |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/save-picker.spec.mjs` with stubbed picker; fallback path in webkit. |
| Manual verification | Owner saves an export into a synced SharePoint folder; confirms it syncs. |
| Acceptance criteria | 1. Tests pass. 2. Manual sync check recorded. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `EXP-03: V2 save picker export to a user-chosen folder` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `EXP-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| EXP-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CPL-03 |

### CPL-03 · Copilot grounding V2: Copilot-ready export layout and governance notice

| Field | Detail |
|---|---|
| Unique ID | CPL-03 |
| Title | Copilot grounding V2: Copilot-ready export layout and governance notice |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V2; ADR-025 (all users licensed). |
| Exact problem | Licensed users could let Copilot ground on saved project files, but exports aren't structured for that. |
| Reason this matters | Copilot grounding V2 without API. |
| Target behaviour | Export option 'Copilot-ready folder (ZIP)': `README-FOR-COPILOT.md` (what the files are, citation ID convention, as-of dates), `ITEMS.md` (all items with IDs and quotes), `REVIEWS.md`, `SOURCES.json`, one `.md` per source (chunk text with `[S<n>-P<m>]` markers); dialog text: save into a OneDrive/SharePoint folder you control; check sharing before asking Copilot; example prompts for Copilot desktop, Teams and SharePoint ('Using the files in <folder>, …'). |
| Smallest safe change | Implement in `exports/copilot-folder.js` reusing CPL-01A ID mapping. |
| Explicit exclusions | No Microsoft API calls; no automatic upload. |
| Files expected to change | `app/js/exports/copilot-folder.js`, `tests/unit/copilot-folder.test.mjs`, `tests/e2e/copilot-folder.spec.mjs` (new); `app/js/ui/views/exports.js`, `app/js/ui/views/help.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildCopilotFolder`. |
| Dependencies | CPL-02, EXP-03. |
| Prerequisite decisions | ADR-025. |
| External approvals | None. |
| Data-boundary impact | User-saved files enter M365 via OneDrive sync; governed by tenant permissions. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` IDs consistent across files; `npm run test:e2e -- tests/e2e/copilot-folder.spec.mjs`. |
| Manual verification | Owner saves the folder to OneDrive, asks Copilot (desktop) a question referencing it, records whether Copilot finds and cites the files. |
| Acceptance criteria | 1. Tests pass. 2. Manual grounding trial recorded (Copilot behaviour UNVERIFIED until then). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CPL-03: Copilot grounding V2: Copilot-ready export layout and governance notice` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CPL-04 |

### CPL-04 · Agent Builder kit export (user configures the agent manually)

| Field | Detail |
|---|---|
| Unique ID | CPL-04 |
| Title | Agent Builder kit export (user configures the agent manually) |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | ADR-025 (Agent Builder in use; no API). |
| Exact problem | Users who build Copilot agents need consistent instructions and knowledge layout for project files. |
| Reason this matters | Reuses licensed capability without any integration code. |
| Target behaviour | Export 'Agent Builder kit': `AGENT_INSTRUCTIONS.md` (instructions text: use only the knowledge files; cite IDs; say Not found; label Fact/Inference/Recommendation; length checked against `settings.agentInstructionLimit`, default 8,000 characters, flagged UNVERIFIED), `AGENT_SETUP.md` (step-by-step: open Agent Builder, create agent, paste instructions, add the Copilot-ready folder from CPL-03 as knowledge, test prompts, sharing caution), plus the CPL-03 folder content. |
| Smallest safe change | Implement `exports/agent-kit.js`. |
| Explicit exclusions | No programmatic agent creation, no manifest/app package, no Copilot Studio, no connectors. |
| Files expected to change | `app/js/exports/agent-kit.js`, `tests/unit/agent-kit.test.mjs` (new); `app/js/ui/views/exports.js`, `app/js/ui/views/help.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildAgentKit`. |
| Dependencies | CPL-03. |
| Prerequisite decisions | ADR-025. |
| External approvals | Tenant policy must allow users to create agents and add SharePoint/OneDrive knowledge (owner verifies in their tenant). |
| Data-boundary impact | As CPL-03. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:unit` instruction length ≤ limit; required rules present. |
| Manual verification | Owner builds one agent from the kit; records instruction limit, knowledge-source options and result quality in DECISION_REGISTER. |
| Acceptance criteria | 1. Unit test passes. 2. Manual agent trial recorded; limit setting adjusted if needed. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CPL-04: Agent Builder kit export (user configures the agent manually)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### UI-08 · Presentation (screen-share) mode

| Field | Detail |
|---|---|
| Unique ID | UI-08 |
| Title | Presentation (screen-share) mode |
| Capability group | UI AND ACCESSIBILITY |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `TARGET_ARCHITECTURE.md` §29; charter §10. |
| Exact problem | Screens are hard to read and may reveal names when shared in meetings. |
| Reason this matters | Usability (P2). |
| Target behaviour | Header toggle 'Presentation mode' (pref via `app/js/ui/prefs.js`, the only `localStorage` user): `screenshare.css` (125 % base font, high contrast, larger targets), hides key field/diagnostic IDs/file paths, toasts ≥ 8 s; sub-toggle 'Hide names' replacing project/source names with 'Project A', 'Source 3' in rendering only. |
| Smallest safe change | Implement. |
| Explicit exclusions | No change to stored data. |
| Files expected to change | `app/css/screenshare.css`, `app/js/ui/prefs.js` (new); `app/index.html`, `app/js/ui/views/*.js` (name rendering via a `displayName()` helper), `tests/e2e/presentation.spec.mjs` (new). |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `displayName`, `getPref`, `setPref`. |
| Dependencies | UI-07. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run test:e2e -- tests/e2e/presentation.spec.mjs` — hidden names never appear in DOM text when enabled. |
| Manual verification | Owner shares screen in Teams with mode on. |
| Acceptance criteria | 1. Test passes. 2. Pref survives reload; localStorage failure doesn't break app. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `UI-08: Presentation (screen-share) mode` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `UI-08` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| UI-08 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### DGN-02 · Diagnostics view and content-free diagnostic report

| Field | Detail |
|---|---|
| Unique ID | DGN-02 |
| Title | Diagnostics view and content-free diagnostic report |
| Capability group | DIAGNOSTICS |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | DOCUMENTED ONLY |
| Evidence | `TARGET_ARCHITECTURE.md` §22; `DATA_AND_STORAGE_ARCHITECTURE.md` §9. |
| Exact problem | Users and the maintainer can't see quarantine, versions or recent errors. |
| Reason this matters | Improved diagnostics (P2). |
| Target behaviour | `app/js/ui/views/diagnostics.js`: app/schema/SW versions, storage usage + persistence, last backup, quarantine list with 'Export quarantine (JSON)' and 'Try again', recent events; 'Download diagnostic report' (JSON with versions, browser UA, counts, events — no content; test asserts no chunk text appears). |
| Smallest safe change | Implement. |
| Explicit exclusions | No remote upload of reports. |
| Files expected to change | `app/js/ui/views/diagnostics.js`, `app/js/diagnostics/report.js`, `tests/e2e/diagnostics.spec.mjs` (new); `app/js/ui/router.js`. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | `buildReport`, `renderDiagnostics`. |
| Dependencies | DAT-03, PWA-03. |
| Prerequisite decisions | — |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | Report must not contain document text, names or keys (test with sentinel strings). |
| Automated tests | `npm run test:e2e -- tests/e2e/diagnostics.spec.mjs`. |
| Manual verification | Download a report; read it. |
| Acceptance criteria | 1. Sentinel strings absent from report. 2. Quarantine export works. |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `DGN-02: Diagnostics view and content-free diagnostic report` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `DGN-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| DGN-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### CLN-03 · Archive superseded docs and remove _archive and sample_data duplicates

| Field | Detail |
|---|---|
| Unique ID | CLN-03 |
| Title | Archive superseded docs and remove _archive and sample_data duplicates |
| Capability group | REPOSITORY CLEANUP |
| Priority | P2 |
| Phase | 3 (Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2) |
| Current classification | UNUSED / superseded |
| Evidence | `REPOSITORY_CLEANUP_CANDIDATES.md` C-9–C-12, C-16–C-21. |
| Exact problem | Old plans and demo code mislead readers. |
| Reason this matters | Single source of truth. |
| Target behaviour | Remove `_archive/`; move `docs/planning/`, `docs/test-plans/`, `docs/architecture/{application_flow,data_model,logic_flow,Product_Source_of_Truth_2Jun2026,refactor-plan,review_proposal_workbench_end_to_end,sequence_flows,system_overview,traceability_map}.md`, `docs/architecture.md`, `docs/architecture_diagram.drawio`, `docs/api-reference.md`, `docs/getting-started.md` to `docs/history/` with `docs/history/README.md` ('superseded on <date>; describes the legacy app at tag legacy-final'); remove `sample_data/` (copies live in `tests/fixtures/synthetic/`), `docs/.gitkeep`. |
| Smallest safe change | `git mv`/`git rm` only. |
| Explicit exclusions | Don't move `docs/assessment`, `docs/architecture/PWA_ARCHITECTURE_CHARTER.md`, new architecture docs, `docs/backlog`, `docs/continuity`, `docs/release`. |
| Files expected to change | Paths listed above. |
| Files that must not change | `docs/assessment/**`, `docs/architecture/{PWA_ARCHITECTURE_CHARTER,TARGET_ARCHITECTURE,DATA_AND_STORAGE_ARCHITECTURE,ONEDRIVE_SHAREPOINT_ARCHITECTURE,COPILOT_AND_CHAT_ARCHITECTURE,MINIFIED_CODE_MIGRATION_STRATEGY,ADR_REGISTER}.md`, `docs/backlog/**`, `docs/continuity/**`, `app/**`, `tests/**`, `tools/**`. |
| Functions, symbols or components likely affected | — |
| Dependencies | CLN-02. |
| Prerequisite decisions | ADR-023. |
| External approvals | None. |
| Data-boundary impact | None. No data leaves the device and no new outbound request is introduced. |
| Storage or migration impact | None. |
| Security and privacy impact | No new risk beyond those named in this item's target; all rules in `SMALL_MODEL_EXECUTION_RULES.md` §4 apply. |
| Automated tests | `npm run check`; `npm run test:unit` (fixtures unaffected). |
| Manual verification | Owner skims `docs/` tree. |
| Acceptance criteria | 1. Tests green. 2. No link in kept docs points to a moved file without updated path (grep). |
| Rollback | `git revert <commit>` of this item's single commit. No stored user data is affected. |
| Recommended commit boundary | One commit titled `CLN-03: Archive superseded docs and remove _archive and sample_data duplicates` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CLN-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CLN-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

## Phase 4 – Approved Graph / Copilot API / agent path (blocked on governance)

### GRA-01 · Record Microsoft 365 V3 prerequisites P1–P8 — **BLOCKED (external approval)**

| Field | Detail |
|---|---|
| Unique ID | GRA-01 |
| Title | Record Microsoft 365 V3 prerequisites P1–P8 |
| Capability group | MICROSOFT GRAPH |
| Priority | P3 |
| Phase | 4 (Approved Graph / Copilot API / agent path (blocked on governance)) |
| Current classification | DOCUMENTED ONLY — BLOCKED |
| Evidence | ADR-019 / ADR-025; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5; owner answer Q-E (no API access). |
| Exact problem | Live Microsoft integration requires tenant approvals that don't exist. |
| Reason this matters | Future enterprise integration path (P3). |
| Target behaviour | `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5 table filled with real values (registration ID, redirect URI, permissions, consent model, CA impact, hosting approval, data classification, support owner) in a new `docs/architecture/V3_PREREQUISITES.md`, each with evidence (ticket/email reference). |
| Smallest safe change | Owner collects answers from the tenant administrator and records them; the model only drafts the document template. |
| Explicit exclusions | Any code before prerequisites are met; application permissions; hard-coded drives/sites; Copilot UI automation. |
| Files expected to change | `docs/architecture/V3_PREREQUISITES.md` (new) |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | None. |
| Prerequisite decisions | ADR-019, ADR-020, ADR-025. |
| External approvals | Entra app registration, admin consent, IT security approval of hosting origin, information-governance approval (P1–P8). |
| Data-boundary impact | None. |
| Storage or migration impact | None. |
| Security and privacy impact | Token handling, consent, least privilege — to be designed at re-planning. |
| Automated tests | None (document). |
| Manual verification | Tenant admin confirms the recorded values. |
| Acceptance criteria | All P1–P8 rows recorded with evidence. |
| Rollback | Not applicable while blocked. |
| Recommended commit boundary | One commit titled `GRA-01: Record Microsoft 365 V3 prerequisites P1–P8` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `GRA-01` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| GRA-01 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | CPL-05, GRA-02 |

### GRA-02 · MSAL.js sign-in (auth code + PKCE, delegated) — **BLOCKED (external approval)**

| Field | Detail |
|---|---|
| Unique ID | GRA-02 |
| Title | MSAL.js sign-in (auth code + PKCE, delegated) |
| Capability group | MICROSOFT GRAPH |
| Priority | P3 |
| Phase | 4 (Approved Graph / Copilot API / agent path (blocked on governance)) |
| Current classification | DOCUMENTED ONLY — BLOCKED |
| Evidence | ADR-019 / ADR-025; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5; owner answer Q-E (no API access). |
| Exact problem | Live Microsoft integration requires tenant approvals that don't exist. |
| Reason this matters | Future enterprise integration path (P3). |
| Target behaviour | Vendored MSAL browser library under `app/vendor/msal/` with manifest; `app/js/connectors/ms-auth.js` sign-in/out, token acquisition for the approved scopes only, 'Disconnect Microsoft account' clearing the MSAL cache; CSP `connect-src` extended only with the approved Microsoft endpoints. |
| Smallest safe change | **Do not start.** First confirm every prerequisite in `V3_PREREQUISITES.md` is recorded as met; then this item must be re-planned into contained sub-items by a human reviewer. |
| Explicit exclusions | Any code before prerequisites are met; application permissions; hard-coded drives/sites; Copilot UI automation. |
| Files expected to change | To be defined at re-planning. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | GRA-01. |
| Prerequisite decisions | ADR-019, ADR-020, ADR-025. |
| External approvals | Entra app registration, admin consent, IT security approval of hosting origin, information-governance approval (P1–P8). |
| Data-boundary impact | Device ↔ Microsoft 365 tenant via Graph (new boundary). |
| Storage or migration impact | None. |
| Security and privacy impact | Token handling, consent, least privilege — to be designed at re-planning. |
| Automated tests | Defined at re-planning. |
| Manual verification | Defined at re-planning. |
| Acceptance criteria | Defined at re-planning; item stays BLOCKED until GRA-01 is accepted. |
| Rollback | Not applicable while blocked. |
| Recommended commit boundary | One commit titled `GRA-02: MSAL.js sign-in (auth code + PKCE, delegated)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `GRA-02` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| GRA-02 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | GRA-03, GRA-04 |

### GRA-03 · Microsoft File Picker source connector (V3 input) — **BLOCKED (external approval)**

| Field | Detail |
|---|---|
| Unique ID | GRA-03 |
| Title | Microsoft File Picker source connector (V3 input) |
| Capability group | SHAREPOINT INPUT |
| Priority | P3 |
| Phase | 4 (Approved Graph / Copilot API / agent path (blocked on governance)) |
| Current classification | DOCUMENTED ONLY — BLOCKED |
| Evidence | ADR-019 / ADR-025; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5; owner answer Q-E (no API access). |
| Exact problem | Live Microsoft integration requires tenant approvals that don't exist. |
| Reason this matters | Future enterprise integration path (P3). |
| Target behaviour | `app/js/connectors/graph-picker-source.js` per `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §2 V3 (picker, item download, provenance with driveId/itemId/eTag, user-triggered refresh by eTag). |
| Smallest safe change | **Do not start.** First confirm every prerequisite in `V3_PREREQUISITES.md` is recorded as met; then this item must be re-planned into contained sub-items by a human reviewer. |
| Explicit exclusions | Any code before prerequisites are met; application permissions; hard-coded drives/sites; Copilot UI automation. |
| Files expected to change | To be defined at re-planning. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | GRA-02. |
| Prerequisite decisions | ADR-019, ADR-020, ADR-025. |
| External approvals | Entra app registration, admin consent, IT security approval of hosting origin, information-governance approval (P1–P8). |
| Data-boundary impact | Device ↔ Microsoft 365 tenant via Graph (new boundary). |
| Storage or migration impact | Provenance fields for Graph sources (driveId, itemId, eTag) — schema migration at re-planning. |
| Security and privacy impact | Token handling, consent, least privilege — to be designed at re-planning. |
| Automated tests | Defined at re-planning. |
| Manual verification | Defined at re-planning. |
| Acceptance criteria | Defined at re-planning; item stays BLOCKED until GRA-01 is accepted. |
| Rollback | Not applicable while blocked. |
| Recommended commit boundary | One commit titled `GRA-03: Microsoft File Picker source connector (V3 input)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `GRA-03` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| GRA-03 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### GRA-04 · Graph destination connector with conflict handling (V3 output) — **BLOCKED (external approval)**

| Field | Detail |
|---|---|
| Unique ID | GRA-04 |
| Title | Graph destination connector with conflict handling (V3 output) |
| Capability group | SHAREPOINT OUTPUT |
| Priority | P3 |
| Phase | 4 (Approved Graph / Copilot API / agent path (blocked on governance)) |
| Current classification | DOCUMENTED ONLY — BLOCKED |
| Evidence | ADR-019 / ADR-025; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5; owner answer Q-E (no API access). |
| Exact problem | Live Microsoft integration requires tenant approvals that don't exist. |
| Reason this matters | Future enterprise integration path (P3). |
| Target behaviour | `app/js/connectors/graph-dest.js` per §3 V3 (folder picker, `conflictBehavior=fail`, typed REPLACE with `If-Match`, confirmation, audit fields in ExportRecord). |
| Smallest safe change | **Do not start.** First confirm every prerequisite in `V3_PREREQUISITES.md` is recorded as met; then this item must be re-planned into contained sub-items by a human reviewer. |
| Explicit exclusions | Any code before prerequisites are met; application permissions; hard-coded drives/sites; Copilot UI automation. |
| Files expected to change | To be defined at re-planning. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | GRA-02. |
| Prerequisite decisions | ADR-019, ADR-020, ADR-025. |
| External approvals | Entra app registration, admin consent, IT security approval of hosting origin, information-governance approval (P1–P8). |
| Data-boundary impact | Device ↔ Microsoft 365 tenant via Graph (new boundary). |
| Storage or migration impact | None. |
| Security and privacy impact | Token handling, consent, least privilege — to be designed at re-planning. |
| Automated tests | Defined at re-planning. |
| Manual verification | Defined at re-planning. |
| Acceptance criteria | Defined at re-planning; item stays BLOCKED until GRA-01 is accepted. |
| Rollback | Not applicable while blocked. |
| Recommended commit boundary | One commit titled `GRA-04: Graph destination connector with conflict handling (V3 output)` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `GRA-04` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| GRA-04 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |

### CPL-05 · Copilot API, connector or programmatic agent integration — **BLOCKED (external approval)**

| Field | Detail |
|---|---|
| Unique ID | CPL-05 |
| Title | Copilot API, connector or programmatic agent integration |
| Capability group | MICROSOFT 365 COPILOT |
| Priority | P3 |
| Phase | 4 (Approved Graph / Copilot API / agent path (blocked on governance)) |
| Current classification | DOCUMENTED ONLY — BLOCKED |
| Evidence | ADR-019 / ADR-025; `ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5; owner answer Q-E (no API access). |
| Exact problem | Live Microsoft integration requires tenant approvals that don't exist. |
| Reason this matters | Future enterprise integration path (P3). |
| Target behaviour | Only after a new ADR records licensing, API availability (currently **none** — Q-E), identity, hosting, data boundary, tenant policy, operations and audit (`COPILOT_AND_CHAT_ARCHITECTURE.md` §6 V3). |
| Smallest safe change | **Do not start.** First confirm every prerequisite in `V3_PREREQUISITES.md` is recorded as met; then this item must be re-planned into contained sub-items by a human reviewer. |
| Explicit exclusions | Any code before prerequisites are met; application permissions; hard-coded drives/sites; Copilot UI automation. |
| Files expected to change | To be defined at re-planning. |
| Files that must not change | Legacy application paths (`server.py`, `cli.py`, `project_manager.py`, `version.py`, `pyproject.toml`, `admin/`, `ai_backends/`, `contracts/`, `core/`, `db/`, `handlers/`, `models/`, `personas/`, `processors/`, `services/`, `static/`, `ui/`, `scripts/`, `tests/*.py`, `sample_data/`, `_archive/`); `docs/assessment/**`; `docs/architecture/**`; any `app/` or `tests/` file not listed under 'Files expected to change'. |
| Functions, symbols or components likely affected | — |
| Dependencies | GRA-01. |
| Prerequisite decisions | ADR-019, ADR-020, ADR-025. |
| External approvals | Entra app registration, admin consent, IT security approval of hosting origin, information-governance approval (P1–P8). |
| Data-boundary impact | Device ↔ Microsoft 365 tenant via Graph (new boundary). |
| Storage or migration impact | None. |
| Security and privacy impact | Token handling, consent, least privilege — to be designed at re-planning. |
| Automated tests | Defined at re-planning. |
| Manual verification | Defined at re-planning. |
| Acceptance criteria | Defined at re-planning; item stays BLOCKED until GRA-01 is accepted. |
| Rollback | Not applicable while blocked. |
| Recommended commit boundary | One commit titled `CPL-05: Copilot API, connector or programmatic agent integration` containing only the files listed under 'Files expected to change'. Do not commit until the owner says so. |
| Completion evidence | Execution report containing: exact test commands and their pass/fail summary; `git diff --stat`; each acceptance criterion with how it was checked; any browser behaviour that was not verified. |
| Continuity update instructions | If `docs/continuity/PROJECT_STATE.md` exists: mark `CPL-05` Done (date, evidence) there and remove it from `docs/continuity/NEXT_ACTIONS.md`. Otherwise append `<date> \| CPL-05 \| Done \| <tests run> \| <notes>` to `docs/backlog/EXECUTION_LOG.md`. Append any decision taken to `docs/backlog/DECISION_REGISTER.md` (never edit earlier entries). |
| Required by | — |
