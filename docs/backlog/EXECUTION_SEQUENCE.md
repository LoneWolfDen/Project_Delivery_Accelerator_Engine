# Execution Sequence

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Rule | Execute steps in the order listed. A step starts only when every ID in its 'Depends on' column is Done with evidence. Items in the same phase that `DEPENDENCY_MAP.md` §2 lists as parallel-safe may run in separate branches, merged one at a time. |
| Phase gate | A phase is complete only when its exit criteria are met **and** CI is green on the branch that contains all of its items. |

Releases are cut only at the release points named below; a release point never splits the PWA-04 → PWA-02 → PWA-03 chain.

---

## Phase 0 – Baseline, backups of behaviour, source recovery, no outbound leakage, truthful foundations, tests

Goal: a trustworthy starting point. The legacy behaviour is captured, CI gives a real signal, and the rules that prevent leakage, XSS and fabricated answers exist **before** any application code.

| Step | ID | Title | Priority | Depends on |
|---|---|---|---|---|
| 0.1 | BAS-01 | Record the legacy baseline tag and execution log | P0 | — |
| 0.2 | BAS-02 | Copy synthetic sample documents into test fixtures | P0 | — |
| 0.3 | BAS-03 | Capture legacy extraction and persona outputs as golden files | P0 | BAS-01, BAS-02 |
| 0.4 | BAS-04 | Convert persona YAML definitions to JSON for the new app | P0 | BAS-01 |
| 0.5 | TST-01 | Add dev-only Node test tooling and static dev server | P0 | — |
| 0.6 | TST-02 | Replace permanently failing CI with the new checks | P0 | TST-01 |
| 0.7 | SEC-01 | Forbidden-API and fabrication guard checker | P0 | TST-01 |
| 0.8 | CHT-01 | Statement, label and citation domain model | P0 | TST-01 |
| 0.9 | DOC-01 | Add MIT LICENSE and a truthful README status banner | P1 | — |
| 0.10 | CLN-01 | Remove Docker and Compose files | P1 | DOC-01 |

Exit criteria:
1. Tag `legacy-baseline` exists; `docs/backlog/EXECUTION_LOG.md` started.
2. Golden files and persona JSON committed; the golden generator re-runs with no diff.
3. CI (new workflow) green; `npm run check` enforces forbidden APIs and fabrication phrases.
4. `LICENSE` present; README states the rebuild status truthfully; Docker files gone.

"Backups" in this phase means preserving the legacy *behaviour* and code (tag plus goldens). There is no user data to back up: the owner confirmed the legacy app holds no real data (ADR-013).

## Phase 1 – Maintainable application shell, reliable storage, file import, provenance

Goal: a modular, CSP-protected browser app that stores projects and imported documents locally with provenance, and can back up and restore them. No service worker yet.

| Step | ID | Title | Priority | Depends on |
|---|---|---|---|---|
| 1.1 | BLD-01 | Application shell skeleton with CSP and file:// guard | P0 | TST-01, SEC-01 |
| 1.2 | SEC-02 | Enforce Trusted Types with a single script-URL policy | P0 | BLD-01 |
| 1.3 | UI-01 | Safe DOM builder | P0 | BLD-01 |
| 1.4 | UI-02 | App frame: store, hash router, header, live region, skip link | P1 | UI-01 |
| 1.5 | DGN-01 | Diagnostics log, error codes and visible error banner | P0 | UI-02 |
| 1.6 | DAT-01 | IndexedDB open, schema v1, migration runner and downgrade guard | P0 | DGN-01 |
| 1.7 | DAT-02 | Record validators and generic repositories with optimistic concurrency | P0 | DAT-01 |
| 1.8 | DAT-03 | Quarantine for unreadable records and diagnostics persistence | P0 | DAT-02 |
| 1.9 | DAT-04 | Cross-tab write lock, change broadcast and version-change handling | P1 | DAT-02 |
| 1.10 | DAT-05 | Persistent storage request, usage display and quota error handling | P1 | DAT-02, UI-02 |
| 1.11 | UI-03 | Projects list and create/rename project | P1 | DAT-02, UI-02 |
| 1.12 | DAT-06 | Trash, undo, typed-confirmation permanent delete and reset | P0 | UI-03, DAT-03 |
| 1.13 | BAK-01 | Backup export (format v1) with checksums | P0 | DAT-06 |
| 1.14 | BAK-02 | Restore: validate, preview and add as copies | P0 | BAK-01 |
| 1.15 | BAK-03 | Restore replace modes and older-schema restores | P1 | BAK-02 |
| 1.16 | IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | P0 | DAT-02, BAS-02 |
| 1.17 | IMP-02 | Import UI: choose or drop files, preview, keep or discard, duplicate detection | P0 | IMP-01, UI-03 |
| 1.18 | IMP-03 | Markdown, CSV and JSON parsers with locators | P1 | IMP-02 |
| 1.19 | IMP-04 | Email (.eml) parser | P1 | IMP-02 |
| 1.20 | IMP-05 | Hostile-input and size-limit protections for import | P0 | IMP-03 |

Exit criteria:
1. Backup → reset → restore round trip proven by e2e (BAK-02) in Chromium and WebKit.
2. Nothing is deleted without Trash or typed confirmation (DAT-06); quarantine works (DAT-03).
3. `.txt .md .csv .json .eml` import with preview-before-keep, duplicate detection and complete provenance.
4. Zero CSP violations and zero forbidden-API findings.

**Release point R0.1 (internal preview):** tag `v0.1.0` after Phase 1 for owner testing via `npm run serve` or the static files. There's no service worker, so there's no caching risk.

## Phase 2 – PWA and daily use, OneDrive/SharePoint V1, grounded chatbot, Copilot package V1

Goal: an installable, offline-capable app for daily use, with grounded Ask, honest persona reviews, exports, a Copilot package with paste-back, and launchers. Ends with retirement of the legacy app.

| Step | ID | Title | Priority | Depends on |
|---|---|---|---|---|
| 2.1 | PWA-01 | Web app manifest and icons | P1 | BLD-01 |
| 2.2 | PWA-04 | Recovery page (reset.html) and remote kill-switch file, before any service worker | P1 | PWA-01 |
| 2.3 | PWA-02 | Service worker with precache manifest generator and offline start | P1 | PWA-04, SEC-02 |
| 2.4 | PWA-03 | Update prompt with backup-first and schema-change notice | P1 | PWA-02, BAK-01 |
| 2.5 | IMP-06 | DOCX import without third-party libraries | P1 | IMP-05 |
| 2.6 | MIG-01 | Port deterministic extraction with citations and parity tests | P0 | IMP-03, IMP-04, BAS-03, CHT-01 |
| 2.7 | UI-04 | Source viewer and citation component | P1 | IMP-02, CHT-01 |
| 2.8 | UI-05 | Extracted items view | P1 | MIG-01, UI-04 |
| 2.9 | CHT-02 | Deterministic search index and query (BM25) | P1 | IMP-01 |
| 2.10 | CHT-03 | Ask view: evidence answers with scope, Not found and history | P1 | CHT-02, UI-04, CHT-01 |
| 2.11 | DAT-07 | Snapshots (named, immutable versions of included sources) | P1 | MIG-01 |
| 2.12 | MIG-02 | Port persona reviews as deterministic, honestly labelled reviews | P0 | MIG-01, DAT-07, BAS-04 |
| 2.13 | UI-06 | Reviews view with labelled findings | P1 | MIG-02, UI-04 |
| 2.14 | ODI-01 | OneDrive/SharePoint V1 input: synced-folder guidance and provenance | P1 | IMP-02 |
| 2.15 | EXP-01 | Exports V1: report (HTML), Markdown and JSON with manifest and boundary notice | P1 | UI-06, BAK-01 |
| 2.16 | EXP-02 | Stored ZIP writer for multi-file exports | P2 | EXP-01, IMP-06 |
| 2.17 | CPL-01 | Copilot package V1: prompt, context, sources manifest; clipboard and ZIP | P2 | EXP-02, CHT-03, UI-06 |
| 2.18 | CPL-02 | Copilot paste-back stored as Draft with citation-ID checks | P2 | CPL-01 |
| 2.19 | BLD-02 | Local launchers for Windows and macOS (double-click start) | P1 | BLD-01 |
| 2.20 | UI-07 | Accessibility verification pass on main journeys | P1 | UI-06, CHT-03, EXP-01, BAK-02 |
| 2.21 | DOC-02 | In-app help: start, backup, restore, rollback, data boundary, Copilot how-to | P1 | PWA-04, BAK-03, CPL-01, BLD-02 |
| 2.22 | REL-01 | Release process: versioning, release zip, optional static deploy | P1 | TST-02, PWA-03, BLD-02 |
| 2.23 | CLN-02 | Retire the legacy application (tag legacy-final, remove legacy code) | P1 | MIG-01, MIG-02, BAS-03, BAS-04, IMP-04, DOC-01 |
| 2.24 | DOC-03 | Rewrite README for the new app | P1 | CLN-02, REL-01, DOC-02 |

Exit criteria:
1. Offline start, update prompt and both kill-switch routes proven by e2e (PWA-04, PWA-02, PWA-03).
2. Extraction and review parity with legacy goldens, with every difference listed and accepted by the owner.
3. Every displayed FACT has a resolvable citation; Ask returns Not found with scope when no evidence exists.
4. Exports and Copilot package carry manifests; the boundary notice appears before the first export.
5. Owner has run the manual checks recorded as UNVERIFIED (corporate laptop: launcher, install, synced-folder import, Copilot paste trial).
6. `legacy-final` tag exists and legacy code is removed (CLN-02); README rewritten (DOC-03).

**Release point R0.2:** only after PWA-04, PWA-02 **and** PWA-03 are all Done (first service-worker release).
**Release point R1.0:** after all Phase 2 items. Use REL-01 (release zip; optional static deploy).

## Phase 3 – Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2, optional AI

Goal: convenience and reach without new approvals: PDF, linked-folder refresh, save-to-folder, Copilot-ready folders and Agent Builder kit (ADR-025), optional OpenRouter behind consent (ADR-006), diagnostics, presentation mode, publication readiness.

| Step | ID | Title | Priority | Depends on |
|---|---|---|---|---|
| 3.1 | AI-01 | AI provider interface, consent token and egress preview (no network) | P2 | CHT-03, UI-06 |
| 3.2 | AI-02 | OpenRouter adapter behind consent (with browser CORS spike) | P2 | AI-01 |
| 3.3 | AI-03 | AI-assisted Ask with response validation | P2 | AI-02 |
| 3.4 | AI-04 | AI-assisted review (optional) per persona section | P2 | AI-03, MIG-02 |
| 3.5 | IMP-07 | PDF import via vendored pdf.js | P2 | IMP-06, PWA-02 |
| 3.6 | ODI-02 | V2 linked folder with user-triggered refresh and changed-file preview | P2 | IMP-06, PWA-03, BAK-03 |
| 3.7 | EXP-03 | V2 save picker export to a user-chosen folder | P2 | EXP-01, CPL-01 |
| 3.8 | CPL-03 | Copilot grounding V2: Copilot-ready export layout and governance notice | P2 | CPL-02, EXP-03 |
| 3.9 | CPL-04 | Agent Builder kit export (user configures the agent manually) | P2 | CPL-03 |
| 3.10 | UI-08 | Presentation (screen-share) mode | P2 | UI-07 |
| 3.11 | DGN-02 | Diagnostics view and content-free diagnostic report | P2 | DAT-03, PWA-03 |
| 3.12 | CLN-03 | Archive superseded docs and remove _archive and sample_data duplicates | P2 | CLN-02 |
| 3.13 | REL-02 | Pre-publication checklist before making the repository public | P2 | CLN-02, DOC-03 |

Exit criteria:
1. First schema migration (ODI-02, 1 → 2) passes the migration e2e, and backup from v1 restores into v2.
2. AI requests are impossible without the egress dialog (interception test), and AI FACTs are always verified.
3. Owner trials recorded: Copilot grounding on a saved folder, Agent Builder kit, linked-folder refresh on the corporate laptop.
4. If publication is wanted: REL-02 checklist completed by the owner.

**Release point R1.1** after ODI-02 (schema change: release notes must say so and the update prompt must show the schema notice).

## Phase 4 – Approved Graph, Copilot APIs or agent path (only after governance decisions)

| Step | ID | Title | Priority | Depends on |
|---|---|---|---|---|
| 4.1 | GRA-01 | Record Microsoft 365 V3 prerequisites P1–P8 | P3 | — |
| 4.2 | GRA-02 | MSAL.js sign-in (auth code + PKCE, delegated) | P3 | GRA-01 |
| 4.3 | GRA-03 | Microsoft File Picker source connector (V3 input) | P3 | GRA-02 |
| 4.4 | GRA-04 | Graph destination connector with conflict handling (V3 output) | P3 | GRA-02 |
| 4.5 | CPL-05 | Copilot API, connector or programmatic agent integration | P3 | GRA-01 |

Entry criterion: GRA-01 accepted with evidence for P1–P8 (`ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5). Until then every Phase 4 item stays BLOCKED, and none may be started or partly implemented.
