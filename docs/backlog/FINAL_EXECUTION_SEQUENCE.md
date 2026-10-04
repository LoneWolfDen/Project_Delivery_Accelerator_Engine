# Final Execution Sequence

| Field | Value |
|---|---|
| Date | 2026-10-04 |
| Status | **Authoritative.** Supersedes `EXECUTION_SEQUENCE.md` and `DEPENDENCY_MAP.md` §1–2 (their tables predate the validation splits). `DEPENDENCY_MAP.md` §3–6 (alternatives, high-risk sequences, approval blocks, missing source) remain valid, with split IDs read as their parts. |
| Basis | `MASTER_BACKLOG.md` after the corrections in `BACKLOG_VALIDATION.md`; owner acceptance of all architecture decisions (BD-15) |
| Items | 83 (Phase 0: 10, Phase 1: 23, Phase 2: 30, Phase 3: 15, Phase 4: 5) |
| Checks performed | No dependency cycles; no item depends on an item in a later phase; every dependency ID exists; all 28 required fields present in every item |
| **Next item** | **BAS-01** (then TST-01, BAS-02, DOC-01 in any order; see parallel-safe sets) |

## Execution rules for this sequence

1. Execute steps in order. A step may start only when everything in its 'Depends on' column is **Done with evidence** (`docs/continuity/PROJECT_STATE.md`, or `docs/backlog/EXECUTION_LOG.md` until continuity docs exist).
2. Items listed in the same parallel-safe set may run in separate branches, but must be merged one at a time with the full test suite re-run after each merge. Never parallelise two items that edit a shared file (`MASTER_BACKLOG.md` header, rule V-28).
3. One item = one implementation cycle = one commit when the owner instructs (`.claude/prompts/IMPLEMENT_ONE_ITEM_TEMPLATE.md`).
4. A phase is complete only when its gate criteria are met, CI is green, and the manual smoke checklist (TST-03, from Phase 1 on) has a passing row for real Edge.
5. **BLOCKED** items are never started.

---

## Phase 0 – Baseline, behaviour capture, no outbound leakage, truthful foundations, tests

| Step | ID | Title | Priority | Depends on | Required by |
|---|---|---|---|---|---|
| 0.1 | BAS-01 | Record the legacy baseline tag and execution log | P0 | — | BAS-03, BAS-04 |
| 0.2 | BAS-02 | Copy synthetic sample documents into test fixtures | P0 | — | BAS-03, IMP-01 |
| 0.3 | BAS-03 | Capture legacy extraction and persona outputs as golden files | P0 | BAS-01, BAS-02 | CLN-02, MIG-01A |
| 0.4 | BAS-04 | Convert persona YAML definitions to JSON for the new app | P0 | BAS-01 | CLN-02, MIG-02A |
| 0.5 | TST-01 | Add dev-only Node test tooling and static dev server | P0 | — | BLD-01, CHT-01, SEC-01, TST-02 |
| 0.6 | TST-02 | Replace permanently failing CI with the new checks | P0 | TST-01 | REL-01A |
| 0.7 | SEC-01 | Forbidden-API and fabrication guard checker | P0 | TST-01 | BLD-01 |
| 0.8 | CHT-01 | Statement, label and citation domain model | P0 | TST-01 | CHT-03, MIG-01A, UI-04 |
| 0.9 | DOC-01 | Add MIT LICENSE and a truthful README status banner | P1 | — | CLN-01, CLN-02 |
| 0.10 | CLN-01 | Remove Docker and Compose files | P1 | DOC-01 | — |

Parallel-safe sets:
- depth 1: BAS-01, BAS-02, DOC-01, TST-01
- depth 2: BAS-03, BAS-04, CHT-01, CLN-01, SEC-01, TST-02

**Gate 0:** tag `legacy-baseline` recorded; goldens and persona JSON committed and reproducible; new CI green; forbidden-API and fabrication checks active; `LICENSE` added and README truthful; Docker removed.

## Phase 1 – Maintainable shell, reliable storage, import, provenance

| Step | ID | Title | Priority | Depends on | Required by |
|---|---|---|---|---|---|
| 1.1 | BLD-01 | Application shell skeleton with CSP and file:// guard | P0 | TST-01, SEC-01 | BLD-02, PWA-01, SEC-02, UI-01 |
| 1.2 | SEC-02 | Enforce Trusted Types with a single script-URL policy | P0 | BLD-01 | PWA-02B |
| 1.3 | UI-01 | Safe DOM builder | P0 | BLD-01 | DGN-01, UI-02 |
| 1.4 | UI-02 | App frame: store, hash router, header, live region, skip link | P1 | UI-01 | DAT-05, UI-03 |
| 1.5 | DGN-01 | Diagnostics log, error codes and visible error banner | P0 | UI-01 | DAT-01 |
| 1.6 | DAT-01 | IndexedDB open, schema v1, migration runner and downgrade guard | P0 | DGN-01 | DAT-02 |
| 1.7 | DAT-02 | Record validators and generic repositories with optimistic concurrency | P0 | DAT-01 | DAT-03, DAT-04, DAT-05, IMP-01, UI-03 |
| 1.8 | DAT-03 | Quarantine for unreadable records and diagnostics persistence | P0 | DAT-02 | DAT-06A, DGN-02 |
| 1.9 | DAT-04 | Cross-tab write lock, change broadcast and version-change handling | P1 | DAT-02 | — |
| 1.10 | DAT-05 | Persistent storage request, usage display and quota error handling | P1 | DAT-02, UI-02 | DAT-06B |
| 1.11 | UI-03 | Projects list and create/rename project | P1 | DAT-02, UI-02 | DAT-06A, IMP-02B |
| 1.12 | DAT-06A | Trash: move to Trash, Undo, restore from Trash view | P0 | UI-03, DAT-03 | DAT-06B, MIG-01B |
| 1.13 | DAT-06B | Permanent delete with typed confirmation, expiry prompt and app reset | P0 | DAT-06A, DAT-05 | BAK-01 |
| 1.14 | BAK-01 | Backup export (format v1) with checksums | P0 | DAT-06B | BAK-02, EXP-01A |
| 1.15 | BAK-02 | Restore: validate, preview and add as copies | P0 | BAK-01 | BAK-03, TST-03, UI-07 |
| 1.16 | BAK-03 | Restore replace modes and older-schema restores | P1 | BAK-02 | DOC-02, ODI-02A, PWA-03 |
| 1.17 | IMP-01 | Import pipeline: text parser, chunker, provenance and hashing (pure) | P0 | DAT-02, BAS-02 | CHT-02, IMP-02A |
| 1.18 | IMP-02A | Keep imported files: source/chunk repositories, single transaction, duplicate detection | P0 | IMP-01 | IMP-02B |
| 1.19 | IMP-02B | Import UI: choose or drop files, preview, keep or discard | P0 | IMP-02A, UI-03 | IMP-03, IMP-04, MIG-01B, ODI-01, ODI-02B, TST-03, UI-04 |
| 1.20 | TST-03 | Manual browser smoke checklist for phase gates and releases | P1 | BAK-02, IMP-02B | REL-01A |
| 1.21 | IMP-03 | Markdown, CSV and JSON parsers with locators | P1 | IMP-02B | IMP-05, MIG-01A |
| 1.22 | IMP-04 | Email (.eml) parser | P1 | IMP-02B | CLN-02, MIG-01A |
| 1.23 | IMP-05 | Hostile-input and size-limit protections for import | P0 | IMP-03 | IMP-06 |

Parallel-safe sets:
- depth 4: SEC-02, UI-01
- depth 5: DGN-01, UI-02
- depth 8: DAT-03, DAT-04, DAT-05, IMP-01, UI-03
- depth 9: DAT-06A, IMP-02A
- depth 10: DAT-06B, IMP-02B
- depth 11: BAK-01, IMP-03, IMP-04
- depth 12: BAK-02, IMP-05
- depth 13: BAK-03, TST-03

**Gate 1:** backup → reset → restore round trip proven (Chromium + WebKit); deletion only through Trash/typed confirmation; quarantine works; `.txt .md .csv .json .eml` import with preview-before-keep and provenance; zero CSP violations; TST-03 checklist run once in real Edge.
**Preview point P1 (no tag):** owner may try the app via `npm run serve`. No service worker exists, so there's no caching risk. Use non-confidential documents only.

## Phase 2 – PWA and daily use, OneDrive/SharePoint V1, grounded chat, Copilot package V1, legacy retirement

| Step | ID | Title | Priority | Depends on | Required by |
|---|---|---|---|---|---|
| 2.1 | PWA-01 | Web app manifest and icons | P1 | BLD-01 | PWA-04 |
| 2.2 | PWA-04 | Recovery page (reset.html) and remote kill-switch file, before any service worker | P1 | PWA-01 | DOC-02, PWA-02A |
| 2.3 | PWA-02A | Precache manifest generator and CI freshness check (no service worker) | P1 | PWA-04 | PWA-02B |
| 2.4 | PWA-02B | Service worker: app-shell cache, offline start, kill-switch integration | P1 | PWA-02A, SEC-02 | IMP-07, PWA-03 |
| 2.5 | PWA-03 | Update prompt with backup-first and schema-change notice | P1 | PWA-02B, BAK-03 | DGN-02, ODI-02A, REL-01A |
| 2.6 | IMP-06 | DOCX import without third-party libraries | P1 | IMP-05 | EXP-02, IMP-07 |
| 2.7 | MIG-01A | Port deterministic extraction (pure) with citations and parity tests | P0 | IMP-03, IMP-04, BAS-03, CHT-01 | CLN-02, MIG-01B, MIG-02A |
| 2.8 | MIG-01B | Store extracted items on keep and support re-run | P0 | MIG-01A, IMP-02B, DAT-06A | DAT-07, UI-05 |
| 2.9 | UI-04 | Source viewer and citation component | P1 | IMP-02B, CHT-01 | CHT-03, UI-05, UI-06 |
| 2.10 | UI-05 | Extracted items view | P1 | MIG-01B, UI-04 | — |
| 2.11 | CHT-02 | Deterministic search index and query (BM25) | P1 | IMP-01 | CHT-03 |
| 2.12 | CHT-03 | Ask view: evidence answers with scope, Not found and history | P1 | CHT-02, UI-04, CHT-01 | AI-01, CPL-01A, DAT-07, UI-07 |
| 2.13 | DAT-07 | Snapshots (named, immutable versions of included sources) | P1 | MIG-01B, CHT-03 | MIG-02B |
| 2.14 | MIG-02A | Port persona review heuristics (pure) with explicit labelling rules and parity tests | P0 | MIG-01A, BAS-04 | CLN-02, MIG-02B |
| 2.15 | MIG-02B | Persist reviews against snapshots | P0 | MIG-02A, DAT-07 | AI-04, CPL-01A, EXP-01A, UI-06 |
| 2.16 | UI-06 | Reviews view with labelled findings | P1 | MIG-02B, UI-04 | AI-01, CPL-01B, EXP-01C, UI-07 |
| 2.17 | ODI-01 | OneDrive/SharePoint V1 input: synced-folder guidance and provenance | P1 | IMP-02B | — |
| 2.18 | EXP-01A | Export builders: manifest, Markdown and JSON (pure) | P1 | MIG-02B, BAK-01 | CPL-01A, EXP-01B |
| 2.19 | EXP-01B | Self-contained HTML report export | P1 | EXP-01A | EXP-01C |
| 2.20 | EXP-01C | Exports view, boundary notice and export records | P1 | EXP-01B, UI-06 | EXP-02, EXP-03, UI-07 |
| 2.21 | EXP-02 | Stored ZIP writer for multi-file exports | P2 | EXP-01C, IMP-06 | CPL-01B |
| 2.22 | CPL-01A | Copilot package builder and clipboard splitter (pure) | P2 | EXP-01A, CHT-03, MIG-02B | CPL-01B |
| 2.23 | CPL-01B | Prepare-for-Copilot dialog: clipboard copy and ZIP download | P2 | CPL-01A, EXP-02, UI-06 | CPL-02, DOC-02, EXP-03 |
| 2.24 | CPL-02 | Copilot paste-back stored as Draft with citation-ID checks | P2 | CPL-01B | CPL-03 |
| 2.25 | BLD-02 | Local launchers for Windows and macOS (double-click start) | P1 | BLD-01 | DOC-02, REL-01A |
| 2.26 | UI-07 | Accessibility verification pass on main journeys | P1 | UI-06, CHT-03, EXP-01C, BAK-02 | UI-08 |
| 2.27 | DOC-02 | In-app help: start, backup, restore, rollback, data boundary, Copilot how-to | P1 | PWA-04, BAK-03, CPL-01B, BLD-02 | DOC-03 |
| 2.28 | REL-01A | Release process: versioning, release checklist and release zip | P1 | TST-02, PWA-03, BLD-02, TST-03 | DOC-03, ODI-02A, REL-01B |
| 2.29 | CLN-02 | Retire the legacy application (tag legacy-final, remove legacy code) | P1 | MIG-01A, MIG-02A, BAS-03, BAS-04, IMP-04, DOC-01 | CLN-03, DOC-03, REL-02 |
| 2.30 | DOC-03 | Rewrite README for the new app | P1 | CLN-02, REL-01A, DOC-02 | REL-02 |

Parallel-safe sets:
- depth 4: BLD-02, PWA-01
- depth 11: ODI-01, UI-04
- depth 12: CHT-03, MIG-01A
- depth 13: IMP-06, MIG-01B, MIG-02A
- depth 14: CLN-02, DAT-07, PWA-03, UI-05
- depth 15: MIG-02B, REL-01A
- depth 16: EXP-01A, UI-06
- depth 17: CPL-01A, EXP-01B
- depth 19: EXP-02, UI-07
- depth 21: CPL-02, DOC-02

**Gate 2:** offline start, update prompt and both kill-switch routes proven; extraction and review parity accepted by the owner; every displayed FACT has a resolvable citation and Ask reports Not found with scope; exports and the Copilot package carry manifests and boundary notices; owner's corporate-laptop checks recorded (launcher, install, synced-folder import, Copilot paste trial); `legacy-final` tagged and legacy removed; README rewritten.
**Release R0.2:** the first tag that contains PWA-02B; allowed only when PWA-04, PWA-02A, PWA-02B and PWA-03 are all Done.
**Release R1.0:** after Gate 2, via REL-01A (release zip; private distribution).

## Phase 3 – Assisted folder workflows, expanded formats, OneDrive/SharePoint V2, Copilot grounding V2, optional AI

| Step | ID | Title | Priority | Depends on | Required by |
|---|---|---|---|---|---|
| 3.1 | REL-02 | Pre-publication checklist before making the repository public | P2 | CLN-02, DOC-03 | REL-01B |
| 3.2 | REL-01B | Optional static deployment job (hosting-neutral) | P2 | REL-01A, REL-02 | — |
| 3.3 | AI-01 | AI provider interface, consent token and egress preview (no network) | P2 | CHT-03, UI-06 | AI-02 |
| 3.4 | AI-02 | OpenRouter adapter behind consent (with browser CORS spike) | P2 | AI-01 | AI-03 |
| 3.5 | AI-03 | AI-assisted Ask with response validation | P2 | AI-02 | AI-04 |
| 3.6 | AI-04 | AI-assisted review (optional) per persona section | P2 | AI-03, MIG-02B | — |
| 3.7 | IMP-07 | PDF import via vendored pdf.js | P2 | IMP-06, PWA-02B | — |
| 3.8 | ODI-02A | Schema migration 1 → 2: folderLinks store (migration only) | P2 | PWA-03, BAK-03, REL-01A | ODI-02B |
| 3.9 | ODI-02B | Linked folder connector with user-triggered refresh and changed-file preview | P2 | ODI-02A, IMP-02B | — |
| 3.10 | EXP-03 | V2 save picker export to a user-chosen folder | P2 | EXP-01C, CPL-01B | CPL-03 |
| 3.11 | CPL-03 | Copilot grounding V2: Copilot-ready export layout and governance notice | P2 | CPL-02, EXP-03 | CPL-04 |
| 3.12 | CPL-04 | Agent Builder kit export (user configures the agent manually) | P2 | CPL-03 | — |
| 3.13 | UI-08 | Presentation (screen-share) mode | P2 | UI-07 | — |
| 3.14 | DGN-02 | Diagnostics view and content-free diagnostic report | P2 | DAT-03, PWA-03 | — |
| 3.15 | CLN-03 | Archive superseded docs and remove _archive and sample_data duplicates | P2 | CLN-02 | — |

Parallel-safe sets:
- depth 15: CLN-03, DGN-02
- depth 17: AI-01, ODI-02B
- depth 20: AI-04, UI-08
- depth 23: CPL-04, REL-02

**Gate 3:** schema migration 1 → 2 passes all four migration cases; no AI request without the egress dialog (interception test); AI FACTs always verified; owner trials recorded for Copilot grounding, the Agent Builder kit and linked-folder refresh; if publication is wanted, REL-02 completed **before** REL-01B.
**Release R1.1:** the first tag containing ODI-02A; release notes flag the schema change and the update prompt shows the schema notice.

## Phase 4 – Approved Graph / Copilot API / agent path

| Step | ID | Title | Priority | Depends on | Required by |
|---|---|---|---|---|---|
| 4.1 | GRA-01 | Record Microsoft 365 V3 prerequisites P1–P8 **(BLOCKED)** | P3 | — | CPL-05, GRA-02 |
| 4.2 | GRA-02 | MSAL.js sign-in (auth code + PKCE, delegated) **(BLOCKED)** | P3 | GRA-01 | GRA-03, GRA-04 |
| 4.3 | GRA-03 | Microsoft File Picker source connector (V3 input) **(BLOCKED)** | P3 | GRA-02 | — |
| 4.4 | GRA-04 | Graph destination connector with conflict handling (V3 output) **(BLOCKED)** | P3 | GRA-02 | — |
| 4.5 | CPL-05 | Copilot API, connector or programmatic agent integration **(BLOCKED)** | P3 | GRA-01 | — |

**Entry criterion:** GRA-01 accepted with evidence for prerequisites P1–P8 (`ONEDRIVE_SHAREPOINT_ARCHITECTURE.md` §5) and, for CPL-05, a Copilot API that is available and approved (none today). Until then, nothing in this phase may be started or prototyped.

## Critical path

Computed from the dependency data (longest prerequisite chain):

- **To Gate 2 (R1.0), 22 sequential items:** TST-01 → SEC-01 → BLD-01 → UI-01 → DGN-01 → DAT-01 → DAT-02 → IMP-01 → IMP-02A → IMP-02B → IMP-03 → MIG-01A → MIG-01B → DAT-07 → MIG-02B → EXP-01A → EXP-01B → EXP-01C → EXP-02 → CPL-01B → DOC-02 → DOC-03
- **To Gate 3, 24 sequential items:** TST-01 → SEC-01 → BLD-01 → UI-01 → DGN-01 → DAT-01 → DAT-02 → IMP-01 → IMP-02A → IMP-02B → IMP-03 → MIG-01A → MIG-01B → DAT-07 → MIG-02B → EXP-01A → EXP-01B → EXP-01C → EXP-02 → CPL-01B → DOC-02 → DOC-03 → REL-02 → REL-01B

Everything not on these chains can run alongside them, subject to the parallel-safety rules above.
