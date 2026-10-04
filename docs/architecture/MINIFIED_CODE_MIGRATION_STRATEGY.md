# Minified Code Migration Strategy

| Field | Value |
|---|---|
| Status | Proposed |
| Date | 2026-10-04 |
| Parent | `TARGET_ARCHITECTURE.md` §30 |
| Key fact | **The repository contains no minified application code and no source maps** (`MINIFIED_AND_GENERATED_CODE_REGISTER.md` §1). This document therefore covers the actual migration problem: moving from a Python server with two monolithic inline-script UIs to a modular browser-only PWA, safely and in slices. |

---

## 1. Recovery assessment

| Question | Answer | Evidence |
|---|---|---|
| Is any served code minified or obfuscated? | No | Max line 410 chars; descriptive names; comments present |
| Is anything to be recovered from source maps or history? | No. The readable source is the served source. | No `.map`, no bundler |
| Is beautification needed? | No | — |
| Are any generated application files without a generator? | One manual copy: `static/v2/js/reconciliation_panel.js` = `ui/v2/components/ReconciliationPanel.js` | Register G-1. Not carried forward. |

Charter recovery options, mapped to this repository:

| Charter option | Applies? | Where |
|---|---|---|
| Recover source from history | No (nothing lost) | — |
| Recover from source maps | No (none exist) | — |
| Reconstruct component by component | **Yes, for domain logic**: Python → JavaScript port of extraction, persona reviews and parsers | §3 |
| Controlled rewrite behind compatibility tests | **Yes, for the UI**: the owner doesn't value either UI (OD-2), so a new UI is written, guarded by behaviour tests, in vertical slices | §4 |

## 2. What is kept, reconstructed or dropped

| Legacy component | Legacy path | Disposition | Reason |
|---|---|---|---|
| Extraction patterns and extractor | `processors/extractors/patterns.py` (410 lines), `intelligence_extractor.py` (296), parts of `processors/context_builder.py` | **Reconstruct** in `app/js/extract/` with characterization tests | Core value; deterministic; small |
| Parsers: txt, md, csv, eml, transcript | `processors/parsers/*.py` | **Reconstruct** in `app/js/import/parsers/` | Needed for browser-only import |
| DOCX parser | `processors/parsers/docx_parser.py` (python-docx) | **Rewrite** with ZIP plus `DOMParser` (no library) | Library not available in browser |
| PDF parser | `processors/parsers/pdf_parser.py` (pypdf) | **Replace** with vendored `pdf.js` (later slice) | Library not available in browser |
| Persona definitions | `personas/definitions/*.yaml` (10 files) | **Convert** to JSON (one-off script, output reviewed and committed) | Content is the value |
| Persona heuristics and deep-dive questions | `personas/engine.py` `_heuristic_findings`, `personas/deep_dive.py` `_heuristic_questions` | **Reconstruct with relabelling** (`COPILOT_AND_CHAT_ARCHITECTURE.md` §3) | Behaviour kept, honesty added |
| Phase → Version → Review hierarchy | `models/hierarchy.py`, `db/hierarchy_store_sql.py` | **Simplify** to Snapshot → Review (`DATA_AND_STORAGE_ARCHITECTURE.md` §2) | Phases, gates and reconciliation are deferred (ADR-012) |
| Proposal generator, presales feedback, decision log, reconciliation, synthesis, diagram generator | `processors/proposal_generator.py`, `presales_*`, `db/decision_log.py`, `review_synthesizer.py`, `diagram_generator.py` | **Defer** (not in first scope; candidates for later slices) | Large, partly unreachable in UI, unverified (OD-2) |
| AI backends | `ai_backends/*` | **Drop** all except an OpenRouter equivalent, rewritten in `app/js/ai/openrouter.js` | OD-6 |
| HTTP server, routing, handlers, services, admin, guardrails | `server.py`, `handlers/`, `services/`, `admin/`, `project_manager.py`, `cli.py` | **Drop** at cutover | No server in target |
| V1 UI | `static/index.html` | **Reference only**; dropped at cutover | OD-2 |
| V2 UI and orphans | `static/v2/**`, `ui/v2/**` | **Reference only**; dropped at cutover | OD-2; unloaded (U1–U3) |
| Docker | `Dockerfile`, `docker-compose.yml`, `.dockerignore` | **Drop** (may be removed early) | OD-4 |
| Feedback page | `static/feedback.html` | **Drop** | OD-3 |
| Tests | `tests/*.py` | **Keep running against legacy until cutover**, then archive with legacy | Only meaningful for legacy |
| Sample data | `sample_data/*` | **Keep**; move to `tests/fixtures/synthetic/` and the in-app sample project | Synthetic, needed for golden tests |

## 3. Characterization tests (preserving working behaviour)

Behaviour worth preserving is defined by **outputs on synthetic inputs**, not by the legacy code's structure.

1. **Golden generation (developer-run, once per change of fixture set):** `tools/legacy-golden.py` imports the legacy extractor and persona heuristics directly (no server). It runs them over every file in `tests/fixtures/synthetic/`, and writes `tests/fixtures/legacy-golden/<fixture>.json` (items by kind; persona sections; deep-dive questions). The legacy commit hash is recorded in each file.
2. **Parity test (CI):** `tests/unit/extract.parity.test.mjs` runs the JS extractor over the same fixtures and compares with the golden files using set comparison per kind (order-insensitive, whitespace-normalised).
3. **Accepted differences:** listed in `tests/fixtures/legacy-golden/ACCEPTED_DIFFERENCES.md` with a reason each (e.g. "legacy split on '|' table rows incorrectly"). The test fails on any difference not listed. Improvements are allowed, but made visible.
4. **Label tests:** the relabelled heuristics (§2) have their own expectations. Each legacy generic sentence maps to `NOT_FOUND`, `RECOMMENDATION` or `NEEDS_CONFIRMATION`, never `FACT`.
5. **Golden files are generated output:** the generator is checked in, and the files carry a header comment saying "GENERATED by tools/legacy-golden.py – do not edit" (charter §2).

The legacy Python runtime is needed only for step 1, by a developer. Users never need it.

## 4. Vertical slices

Each slice is independently shippable: its own branch, tests, release-notes entry and rollback. It's built in `app/` alongside the untouched legacy app.

| Slice | Delivers (user-visible) | Depends on | Acceptance gate (summary) |
|---|---|---|---|
| S0 Foundations | `LICENSE`; new CI (static checks, `node --test`, Playwright smoke); `app/` skeleton with no inline script; CSP; diagnostics; dev static server | — | CI green; CSP-violation test passes; forbidden-API check active |
| S1 Shell and lifecycle | Installable shell, manifest, icons, service worker with update prompt and `reset.html` kill-switch, offline start | S0 | Offline-start, update-prompt and kill-switch e2e tests |
| S2 Storage core | IndexedDB schema v1, repos, quarantine, Trash, storage usage and persistence, **backup and restore** | S0 | Backup → reset → restore round-trip e2e; corrupt-record quarantine test; quota error banner |
| S3 Import V1 | File input and drop, preview-before-keep, txt/md/csv/eml/json parsers, provenance, duplicate detection | S2 | Provenance fields asserted; hostile filename (XSS) fixture; duplicate test |
| S4 DOCX | ZIP reader plus DOCX parser | S3 | Fixture DOCX parity with legacy golden text |
| S5 Extraction | Ported extractor with citations; Items view | S3 | Parity test with accepted differences |
| S6 Ask (deterministic) | Chunk index, BM25 query, evidence view with scope and Not found | S3 | Citation resolution test; Not-found test |
| S7 Snapshots and reviews (deterministic) | Snapshot creation; persona reviews with honest labels | S5, S6 | Label tests; no `FACT` without citation |
| S8 Exports V1 | HTML / Markdown / JSON plus manifest; boundary notice | S7 | Manifest checksum test |
| S9 Copilot V1 | Package, clipboard split, ZIP download, paste-back as Draft | S8 | Package content test; paste-back never yields `FACT` |
| S10 OpenRouter (optional) | Settings toggle, session key, egress preview, consent token, validation | S6, S7 | No-request-without-consent test (network interception); validation tests |
| S11 PDF | Vendored `pdf.js` with manifest and hash check | S3 | Vendor-verify; text-PDF fixture; scanned-PDF warning |
| S12 Folder link V2 | Linked folder, refresh, changed-file preview; save-picker export | S3, S8 | Chromium e2e; fallback hidden in WebKit |
| S13 Hosting and release | GitHub Pages publish (when the repo is public), release zip, launchers, rollback doc | S1, S2 | Release checklist executed once end-to-end |
| S14 Cutover | Owner acceptance; tag `legacy-final`; remove legacy app, tests, Docker, `ui/`, `_archive/`; update README | All in agreed scope | Owner sign-off on the acceptance checklist; repo cleanup per `REPOSITORY_CLEANUP_CANDIDATES.md` |

The **Never replace the entire UI in one untested change** rule is met as follows:

- The new UI grows one slice at a time, each behind its own tests.
- The legacy UI stays runnable and unchanged until S14.
- S14 is a separate, reviewed change that removes code only after every in-scope slice has passed acceptance.

## 5. Rollback routes

| Stage | Rollback |
|---|---|
| During S0–S13 | The legacy app is untouched and runs as before (`python server.py`, localhost only). New-app slices revert by reverting their branch or commit. |
| After a new-app release | Previous release zip (local) or republish the previous tag (hosted); `reset.html` kill-switch; data safety via backup and the downgrade guard (`DATA_AND_STORAGE_ARCHITECTURE.md` §7–8) |
| After cutover (S14) | `git checkout legacy-final` restores the full legacy application; documented in `README` under "Previous version" |

## 6. Interim legacy safety (decision for the backlog step)

While the legacy app is still used, its security BLOCKERs remain (`SECURITY_PRIVACY_ASSESSMENT.md` B-1, B-2; H-1–H-3). There are two options for the backlog:

- **(a) Minimal legacy patches**, contained, with tests: contain static paths under `static/`; drop `admin_pin` from `to_safe_dict`; require the current PIN to change it; restrict CORS to the same origin; reject absolute paths in `/api/ingest`.
- **(b) No patches, plus a usage restriction:** run only on localhost, no Docker, don't browse other sites while it's running.

Recommendation: (a) for B-1, H-1 and H-2 only (small, contained, high value), because the repo is intended to go public (OD-5). Everything else is (b).

## 7. Vendor policy for new code

- First choice: browser built-ins.
- If a library is unavoidable (only `pdf.js` is foreseen), it goes under `app/vendor/<name>/<version>/`, unmodified, with `VENDOR_MANIFEST.json` recording name, version, licence (Apache-2.0 for pdf.js), source URL and SHA-256 per file. `tools/vendor-verify.mjs` checks the hashes in CI.
- Vendor files may be minified (charter §2 allows minified **vendor** code under a vendor directory). Application code may not.
- No patches or override layers on vendor code. Upgrades replace the directory and update the manifest in one change.
