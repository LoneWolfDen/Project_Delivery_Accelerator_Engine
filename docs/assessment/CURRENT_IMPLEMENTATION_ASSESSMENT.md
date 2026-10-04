# Current Implementation Assessment

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Branch | `assessment/pwa-readiness-2026-10` |
| Commit assessed | `1ca4319` (same as `main` and tag `pwa-assessment-baseline-2026-10-01`) |
| Governing guidance | `docs/architecture/PWA_ARCHITECTURE_CHARTER.md` (untracked in Git at assessment time) |
| Method | Read-only inspection: Git metadata, file reads, `grep`, Python `ast.parse` and `node --check` on copies of extracted inline scripts written to a scratch directory outside the repository, read-only `gh run list/view` for CI history. No server was started, no tests were run (pytest not installed and installation prohibited), and no repository file other than the six assessment documents was written. |

Classifications used: WORKING, PARTIAL, PLACEHOLDER, MOCKED, DOCUMENTED ONLY, BROKEN, UNUSED, GENERATED, UNKNOWN.
"Runtime" in the tables means runtime validation is still required before the conclusion is treated as fact.

---

## 1. Headline findings

1. **The application is not a PWA and not a browser-first application.** It is a Python 3.9+ standard-library HTTP server (`server.py`, `http.server.HTTPServer`) with SQLite and JSON file persistence on the server's disk, plus two hand-written vanilla-JavaScript single-page UIs embedded in HTML files. There is no web app manifest, no service worker, no icons, no offline shell and no client-side persistence of user data.
2. **There is no framework and no build.** No React, Vue or other framework. No `package.json`, bundler, transpiler or lockfile. The browser executes exactly the readable source in the repository.
3. **There is no minified or obfuscated code anywhere in the repository**, and there are no source maps. The charter's minified-code concerns don't apply to this repository's current state (details in `MINIFIED_AND_GENERATED_CODE_REGISTER.md`).
4. **There are two competing UIs.** V1 (`static/index.html`, 292 KB, 5,311 lines, 16 inline `<script>` blocks) is the default. V2 (`static/v2/dashboard_v2.html`, 108 KB, 9 inline blocks) is served with `?ui=v2` or `--ui v2`. The modular V2 JavaScript described in the architecture documents (`static/v2/js/api.js`, `state.js`, `dashboard.js`, `accordion.js`, `search.js`, `summary.js`, all of `ui/v2/**`, all of `static/v2/css/**`) is **not loaded by any served page**.
5. **Features documented as "Done" are not reachable in the served UI.** Review iteration (Phase 3) and reconciliation (Phase 4) were implemented in the unloaded `api.js`/`DetailPanel.js`. The served V2 page loads `reconciliation_panel.js`, which needs `window.API`. That is never defined, so the panel can only show "⚠ API not available."
6. **CI has never been green in the last 200 runs** (`gh run list`: 200 of 200 `failure`). Lint reports 1,810 errors. The test job stops at collection (`ImportError: cannot import name 'AVAILABLE_PERSONAS' from 'personas.engine'`), so none of the ~1,422 test functions has executed in CI.
7. **The Docker image as defined can't start.** The `Dockerfile` doesn't copy `core/`, `db/`, `services/`, `handlers/`, `contracts/` or `version.py`, all of which `server.py` imports at module load.
8. **There is no chatbot.** There is no conversational or question-answering feature. The AI usage is batch "persona reviews", deep-dive question generation, proposal generation and synthesis. These send full project content to the selected third-party provider when one is chosen.
9. **No Microsoft 365, OneDrive, SharePoint, Graph, MSAL, Entra or Copilot code exists.** The only reference is a README roadmap line ("v5 Vision … copilot assistant").
10. **Serious security defects exist on the local server.** They include a static-file path traversal, unauthenticated admin configuration (including replacing the PIN), the admin PIN returned in plaintext by `GET /api/admin/config`, wildcard CORS, and an arbitrary server-side file read via `/api/ingest`. Details are in `SECURITY_PRIVACY_ASSESSMENT.md`.

---

## 2. What the application genuinely is

| # | Conclusion | Class | Path / symbol | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| A1 | Server is Python stdlib `HTTPServer` (single-threaded), routing by string matching | WORKING (by static read) | `server.py:28`, `server.py:638` `HTTPServer((HOST, PORT), AcceleratorHandler)` | Imports `http.server`; long `if/elif` chains in `do_GET`/`do_POST` | Long AI calls block all other requests; no thread pool | High | Yes |
| A2 | Front end is vanilla JS inline in HTML; no framework | WORKING | `static/index.html`, `static/v2/dashboard_v2.html` | No `import`, no framework globals; only `<script>` inline blocks plus two `src` scripts in V2 | Very large single files are hard to maintain | High | No |
| A3 | Browser runs readable source; nothing generated or minified | WORKING | all `*.html`, `*.js`, `*.css` | Max line length 410 chars; average 22–61 chars; no `.min.`, no `.map` | None | High | No |
| A4 | Inline scripts are syntactically valid JS | WORKING | V1 16 blocks, V2 9 blocks, feedback 1 block | Each block extracted to scratch and passed `node --check` (Node 24) | Doesn't prove runtime correctness | High | Yes |
| A5 | All 146 tracked Python files parse | WORKING | repo-wide | `ast.parse` over `git ls-files '*.py'`: 0 errors; all first-party imports resolve to files | Import-time side effects unverified | High | Yes |
| A6 | Default UI is V1; V2 is opt-in | WORKING | `server.py:66-79`, `server.py:126-137` | `--ui` default `v1` (env `UI_VERSION`); `?ui=v2` overrides per request | Two UIs to maintain; behaviour diverges | High | No |
| A7 | Application requires a local Python runtime and a long-running server | — | `README.md` Quick Start; `server.py:main` | `pip install -e .`, `python server.py`, `http://localhost:8080` | Conflicts with the charter target "no installer / no admin rights" on a managed laptop if Python is not permitted | High | Needs a corporate-device policy check |

## 3. PWA capability (charter §10)

| Item | Class | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|
| Web app manifest | DOCUMENTED ONLY (charter) / absent | No `manifest.json` / `.webmanifest`; no `<link rel="manifest">` | Not installable | High | No |
| Service worker | Absent | No `serviceWorker.register`, no `sw.js`, no `caches.` usage | No offline shell; but also **no stale-SW pinning risk today** | High | No |
| Icons / favicon | Absent | `server.py` returns `204` for `/favicon.ico` | None functional | High | No |
| Offline mode | PARTIAL | Works "offline" only in the sense that the local server needs no internet in `files_only` mode. If the server isn't running, the UI doesn't load | README "Fully offline-capable" overstates this | High | Yes |
| Cache control | PARTIAL | `server.py` `_serve_static`: HTML `no-cache, no-store`; JS/CSS `max-age=3600` | Up to 1 h stale `compare.js`/`reconciliation_panel.js` after an update, while the HTML is fresh (version skew) | Medium | Yes |
| CSP, `X-Content-Type-Options`, `Referrer-Policy` | Absent | No such headers in `server.py` | See security assessment | High | No |
| Runtime CDN dependencies | None (WORKING) | Only external URL in served UI is a plain hyperlink `https://app.diagrams.net` (`static/index.html:3010`) | Low | High | No |
| Fonts | WORKING | System font stacks only; no web fonts | None | High | No |
| `prefers-reduced-motion` / dark-light media queries | Absent | 0 `@media (prefers-…)` in either UI | Accessibility gap | High | No |
| Keyboard / contrast / screen-share mode | UNKNOWN | ~70 `onclick` handlers on non-button elements (e.g. `div.file-header`) | Likely keyboard-inaccessible | Medium | Yes |

## 4. Storage model (charter §5)

| # | Store | Class | Path / symbol | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| S1 | Browser storage | WORKING (UI preferences only) | `static/index.html:547,706,4585`; `static/v2/dashboard_v2.html:1105` | Only `localStorage` keys `pdae_active_tab`, `pdae_flow_mode`, `pdae_current_project_id`, all wrapped in `try/catch` | Negligible; no user content in browser storage | High | No |
| S2 | SQLite on server disk | WORKING (static read) | `db/database.py` `_SCHEMA_SQL`, `get_db()`; file `PROJECTS_DATA_DIR/accelerator.db` | WAL mode, FK on, `CREATE TABLE IF NOT EXISTS`, ad-hoc `ALTER TABLE` migrations in `_apply_migrations` | No schema version number; migrations are column-presence checks | High | Yes |
| S3 | JSON files mirrored alongside SQLite ("dual-write") | PARTIAL | `services/project.py` `load_projects`/`save_projects`; `db/project_store_sql.py:123` `save_all_projects_sql` | SQL write, then JSON rebuild; every failure is swallowed with `except Exception: pass` and falls back to JSON-only write | **Silent divergence** between SQLite and JSON; reads prefer SQL, so a JSON-only fallback write is invisible on the next read | High | Yes |
| S4 | Admin config file | BROKEN in containers / cwd-dependent | `admin/config.py:16` `CONFIG_DIR = Path("projects_data")` | Ignores `PROJECTS_DATA_DIR`; relative to the process working directory | Config (PIN, API keys) written somewhere other than the data volume; in Docker `/app/projects_data` isn't writable by user `contexta` | High | Yes |
| S5 | Uploaded raw files, context JSON, run history, outputs | WORKING (static read) | `PROJECTS_DATA_DIR/<project_id>/{uploads,outputs,context,intelligence,run_history}` | `services/project.py:create_project` | See S6–S9 | High | Yes |
| S6 | Backup / restore | Absent | No export, backup or import of project data anywhere in the UI or API | Only "Restore" means un-archive. `README` "Reset demo data" is `rm -rf projects_data` | **No recovery path** | High | No |
| S7 | Silent overwrite on ingest | BROKEN | `services/ingest.py:39` `context_dir / f"{path.stem}.json"` | Two inputs with the same stem (e.g. `notes.txt`, `notes.md`) overwrite each other without warning | Data loss | High | Yes |
| S8 | Silent eviction on archive | Data-loss behaviour | `services/project.py:33` `MAX_ARCHIVED = 5`; `:184` `oldest["status"] = "deleted"` | Archiving a 6th project silently marks the oldest archived project as deleted | User data hidden without confirmation | High | Yes |
| S9 | Permanent delete | WORKING but unsafe | `services/project.py:205-243` | `shutil.rmtree(project_dir)` plus `DELETE FROM` 10 tables, with errors swallowed; `prompt_log` **not** purged | Irreversible; no backup; residual content stays in `prompt_log` | High | Yes |
| S10 | Storage usage / quota display, corruption preservation | Absent | — | No disk-usage reporting; JSON read errors raise or fall back silently | Charter §5 minimums unmet | High | No |

## 5. Input: OneDrive / SharePoint readiness (charter §6)

| Level | Class | Evidence |
|---|---|---|
| V1 user-selected local / synced files | PARTIAL | V1 UI uploads through `POST /api/v1/projects/{id}/artifacts/upload` (multipart; `static/index.html:1250`). A user *can* pick a file from a locally synced OneDrive folder. There's no preview-before-retention step, no content hash, and no provenance record matching charter §6 (source system, hash, as-of date, parser version). Supported types: `.txt .md .csv .eml .pdf .docx` (`processors/ingestion.py:22`); `artifact_store` also lists `.json .yaml .yml .xlsx .pptx` (`processors/artifact_store.py:96`); the two lists disagree. |
| Server-path ingest | Conflicts with charter | `POST /api/ingest` with `file_paths` reads **any server path** (`services/ingest.py:33-36`). That's an unrestricted disk read, which the charter forbids (§6 V2 "no unrestricted disk scan"). |
| V2 folder refresh | Absent | No File System Access API usage. |
| V3 Microsoft picker / Graph | Absent | No MSAL, Graph or Entra code. |

## 6. Output: OneDrive / SharePoint readiness (charter §7)

| Level | Class | Evidence |
|---|---|---|
| V1 download and user-save | PARTIAL | Only draw.io diagram download (`GET /api/projects/{pid}/diagrams/{type}`, `Content-Disposition: attachment`). No export of reviews, proposals or project data. No boundary-change warning. |
| V2 browser save workflow | Absent | — |
| V3 Graph write | Absent | — |

## 7. Microsoft 365 Copilot feasibility (charter §8)

| Pattern | Current state | Feasibility notes (no code exists) |
|---|---|---|
| A: manual package workflow | Absent | Most feasible first step: export a grounded package (Markdown/DOCX plus manifest) and the user uploads it to M365. Requires the export capability that is currently missing (§6 above). Copilot output must come back labelled Draft/Recommendation; no data model for that label exists today. |
| B: Microsoft-native grounding | Absent | Depends on Pattern A outputs being saved to OneDrive/SharePoint by the user. No code needed in the app beyond export. |
| C: agent / API integration | Absent | Requires licensing, Entra registration, consent, hosting and data-boundary decisions; none are recorded. The current architecture (local Python server) has no identity layer at all. Not feasible without external approvals. |

An interactive Copilot licence is **not** a JavaScript API (charter §8). Nothing in the repository assumes otherwise.

## 8. AI / assistant behaviour (charter §9)

| # | Conclusion | Class | Path / symbol | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| C1 | No chatbot exists | — (DOCUMENTED ONLY as roadmap) | `README.md:374` | `grep` for chat/assistant/ask finds only provider endpoint names (`/chat/completions`) | Charter §9 requirements have no implementation to assess | High | No |
| C2 | Provider abstraction exists | WORKING | `ai_backends/base.py` `AIBackend`; `ai_backends/registry.py` | Six backends: `files_only`, `ollama`, `bedrock`, `gemini`, `groq`, `openrouter` | Meets the "behind an interface" requirement | High | No |
| C3 | Default provider is deterministic | PARTIAL | `admin/config.py` default `default_ai_backend`; `services/project.py:117` fallback `"ollama"` if config load fails | Contradiction: README says Files Only is the default, but code falls back to `ollama` on config error | A project created during a config failure defaults to an AI backend | Medium | Yes |
| C4 | External transmission of project content | WORKING (and a boundary) | `personas/engine.py:276`, `personas/deep_dive.py:301`, `processors/proposal_generator.py:193,588,825`, `processors/review_synthesizer.py:477,887`, `processors/extractors/ai_extractor.py:100` | Full built context is sent to Groq, OpenRouter, Gemini or Bedrock when selected; per-run user choice in the UI | Device-to-third-party boundary; no explicit per-send warning | High | Yes |
| C5 | Hard-coded generic findings presented as review output | MOCKED-like (heuristic) | `personas/engine.py:527-625` `_heuristic_findings`; `personas/deep_dive.py:362` `_heuristic_questions` | Fixed strings such as "No ROI statements found", "Define acceptance criteria for each deliverable", "Conduct security threat model" are emitted when keywords are absent, and appear in the same `findings` structure as evidence-derived items | Generic text can read as document-grounded findings; no Fact/Inference/Not-found distinction; no citations | High | Yes (UI labelling) |
| C6 | Silent AI-to-heuristic fallback | PARTIAL | `personas/engine.py:284-289`; `processors/proposal_generator.py:208-210`; `processors/review_synthesizer.py:440` | On provider error the result is replaced with heuristic output and `ai_backend` set to `"<name>_fallback"` | User may not notice the review isn't AI-generated | High | Yes (UI display) |
| C7 | Citations / evidence linking | Absent | — | Findings are strings; no source document/section reference model in `_parse_ai_output` | Charter §9 unmet | High | No |
| C8 | Admin-panel API keys aren't used by backends | BROKEN | `admin/config.py` `api_keys`; backends read env only (`ai_backends/groq_backend.py:40`, etc.); `admin/guardrails.py:166` uses config keys for the availability check | A key saved via Admin makes guardrails report "configured" while the backend has no key, so the run silently falls back to heuristics | Misleading UI | High | Yes |
| C9 | Bedrock default model is a dated identifier | UNKNOWN | `ai_backends/bedrock_backend.py:20` `anthropic.claude-3-haiku-20240307-v1:0` | Model availability not verified | Likely failure to heuristic fallback | Low | Yes |

## 9. UI implementation reality vs. documentation

| # | Conclusion | Class | Path / symbol | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|---|
| U1 | V2 modular JS is not loaded | UNUSED | `static/v2/js/{api,state,dashboard,accordion,search,summary}.js` | Commit `f89c4b2` (2026-06-02) removed the `<script src>` tags; served HTML now loads only `compare.js` and `reconciliation_panel.js` (`static/v2/dashboard_v2.html:385,1849`) | Docs, tests and later feature commits target dead files | High | No |
| U2 | `ui/v2/**` cannot even be served | UNUSED | `ui/v2/components/*.js`, `ui/v2/layout/MainLayout.js`, `ui/v2/utils/helpers.js` | `server.py:146-151` maps every `.js` request into `static/`; `ui/` is outside it | Dead code that looks like the architecture | High | No |
| U3 | V2 CSS files are not linked | UNUSED | `static/v2/css/{theme,layout,components}.css` | No `<link>` in `dashboard_v2.html`; styles are inline `<style>` blocks | Duplicate styling | High | No |
| U4 | Reconciliation panel in served V2 | BROKEN | `static/v2/js/reconciliation_panel.js:246` `const api = window.API;` | `window.API` is defined only in the unloaded `api.js` | Feature visible, can't run | High | Yes (click-through) |
| U5 | Review iteration UI | DOCUMENTED ONLY (backend WORKING by static read) | Endpoint `POST …/reviews/{rid}/iterate` (`server.py`); callers only in `static/v2/js/api.js` | `grep` finds `/iterate` in neither served HTML | Docs claim ✅ Done (`docs/architecture/review_proposal_workbench_end_to_end.md:716-717`) | High | No |
| U6 | V2 Admin "Save" | MOCKED (false success) | `static/v2/dashboard_v2.html:1500` | Posts `max_projects` / `max_reviews_per_project`; `admin/config.py:update_config` recognises neither key, returns 200, and UI shows "✓ Saved" | User believes settings changed | High | Yes |
| U7 | V2 `MOCK_DATA` | UNUSED (not loaded) | `static/v2/js/api.js:22`, `:217` `_useMock()` | Default is mock **unless** `window.V2_USE_MOCK === false`; served page sets false but doesn't load `api.js` | If `api.js` is ever re-linked without the flag, the UI silently shows fabricated projects | High | No |
| U8 | `ui/v2/components/ReconciliationPanel.js` and `static/v2/js/reconciliation_panel.js` | Duplicate (byte-identical) | both paths | `diff -q` identical; a test enforces sync (`tests/test_v2_phase3_and_phase4.py:455-459`) | Manual copy instead of a build step | High | No |
| U9 | `contracts/` package | UNUSED | `contracts/bus.py`, `protocols.py`, `types.py` | Imported only by itself | Dead architecture layer | High | No |
| U10 | `project_manager.py` | WORKING (compat shim) | `project_manager.py` | Re-exports `services.*`; mutated by `server.py:82-90` | Two path globals (`services.project`, `core.paths`, `db.database._BASE_DIR`, `admin.config.CONFIG_DIR`) can disagree | Medium | Yes |
| U11 | Feedback page for external reviewers | WORKING (static read) | `static/feedback.html`; `db/project_store_sql.py:442-483` | Token via `secrets.token_urlsafe(24)`, single-use, `expires_days` | Requires exposing the server to the external reviewer, which conflicts with local-only use | Medium | Yes |
| U13 | V1 hierarchy phase change | BROKEN | `static/index.html:3194` → `server.py:446` (shadows `:449`) | `endswith("/phase")` matches `/hierarchy/phase` first; `handle_phase_transition` requires `new_phase`, but the UI sends `phase_id`, so the response is 400 "new_phase required" | Visible feature can't succeed | High | Yes |
| U12 | Diagram generation | WORKING (static read) | `processors/diagram_generator.py` | Generates draw.io XML from intelligence; download endpoint | None | Medium | Yes |

## 10. Build, packaging and deployment model

| # | Conclusion | Class | Evidence | Risk | Conf. | Runtime |
|---|---|---|---|---|---|---|
| B1 | One coherent build model? | PARTIAL | Python: `pyproject.toml` (setuptools). Front end: no build (charter model A, de facto). But the modular V2 sources sit beside an inline monolith, plus a hand-synced duplicate, so the repo **mixes** "source files never used" with the served artefacts | Charter §3 violation | High | No |
| B2 | `pip install .` (non-editable) | BROKEN | `pyproject.toml:35` packages include only `models*, processors*, personas*, ai_backends*, admin*`; `server.py` imports `core`, `db`, `services`, `handlers`, `version` (`version` is in `py-modules`, the others are not packaged) | Wheel install can't start the server | High | Yes |
| B3 | Docker image | BROKEN | `Dockerfile:40-50` copies `admin ai_backends models personas processors static sample_data server.py project_manager.py cli.py`, missing `core db services handlers contracts version.py` | Container exits on import | High | Yes |
| B4 | Docker binds `0.0.0.0` | Risk amplifier | `Dockerfile` `ENV HOST=0.0.0.0`; `docker-compose.yml` same; Ollama `11434` published | Exposes every unauthenticated endpoint to the network | High | Yes |
| B5 | Python dependency pinning | PARTIAL | Lower bounds only; no lockfile; `pip install -e ".[ai]" || true` hides failures | Non-reproducible builds | High | No |
| B6 | CI | BROKEN | `.github/workflows/ci.yml`; 200/200 recent runs fail; lint 1,810 errors; test collection error | No regression signal at all | High | No (observed via `gh`) |
| B7 | Licence | DOCUMENTED ONLY | README badge "License: MIT", Docker label `licenses="MIT"`; **no `LICENSE` file** | Unclear legal status | High | No |

## 11. Architecture claims that don't match the implementation

| Claim (location) | Reality | Class |
|---|---|---|
| "No database" (`README.md` "What it does") | SQLite `accelerator.db` plus JSON dual-write | DOCUMENTED ONLY (false) |
| "Everything runs in a single Docker container" (`README.md`) | Dockerfile omits required packages (B3) | BROKEN |
| "Fully offline-capable" (`README.md`) | True only for the local server in `files_only` mode; no PWA offline | PARTIAL |
| "180+ tests (pytest)" / CI badge (`README.md`) | ~1,422 test functions exist, but CI hasn't passed in 200 runs; suite aborts at collection | BROKEN |
| V2 modular architecture (`docs/architecture/system_overview.md:15-23`, `application_flow.md:16-24`) | Those modules aren't loaded (U1–U3) | DOCUMENTED ONLY |
| Phase 3/4 "✅ Done" (`docs/architecture/review_proposal_workbench_end_to_end.md:677-753`) | Not reachable / broken in served UI (U4, U5) | DOCUMENTED ONLY / BROKEN |
| `ADMIN_PIN` protects destructive operations (`.env.example`, README) | PIN can be read and replaced without a PIN (security H-2/H-3); review and artefact deletes need no PIN | BROKEN |
| "Python 3.9+ (pyyaml only dep)" (`.kiro/steering/project-context.md`) | Core is pyyaml-only; PDF/DOCX need extras; AI SDK extras listed but only `boto3` is actually used (others use `urllib`) | PARTIAL |
| MIT licence | No licence file | DOCUMENTED ONLY |

## 12. Repository facts

| Item | Value |
|---|---|
| Tracked files | 249 |
| Working tree size | 5.7 MB; `.git` 1.9 MB (1 pack, 1.66 MiB) |
| Largest tracked files | `static/index.html` 292 KB; `_archive/migration_demo/server.py` 120 KB; `_archive/.../migration_dashboard_pkg/server.py` 116 KB; `static/v2/dashboard_v2.html` 108 KB |
| Binary / large files | None (largest non-text: none; `.drawio` files are XML) |
| Commits | 275 on HEAD, 295 across all refs |
| Branches | `main`, current branch, ~120 remote feature/fix/revert branches |
| Tags | `pwa-assessment-baseline-2026-10-01` → `1ca4319` |
| Authors | `Kiro Agent` 150 commits, `LoneWolfDen` 138, `Project Delivery Accelerator <dev@projectdelivery.ai>` 7 |
| History notes | Revert to PR #88 state (`df63c08`, `revert/to-pr88-may31*` branches), plus repeated "fix page-load / SyntaxError" commits (`#114`–`#118`), point to an unstable UI with no automated browser check |
| Untracked | `.claude/`, `docs/architecture/PWA_ARCHITECTURE_CHARTER.md` |
| Runtime folders | `projects_data/`, `uploads/`, `outputs/*` git-ignored; none present in working tree |

## 13. Safest migration direction (for the target-architecture step; not a backlog)

- No minified-code recovery is needed. The source of truth is already readable.
- The real maintainability problem is **two monolithic inline-script HTML files plus a set of orphaned modular files that tests and docs treat as live**. The safe path is to pick **one** UI, delete or archive the orphan set only after verification, and extract inline scripts into ES modules (charter model A, no-build). Compatibility tests should drive real HTTP endpoints and a real browser, not source-string checks.
- Moving to a genuine browser-first PWA (charter §1) would mean relocating storage and processing from the Python server into the browser (IndexedDB/OPFS) or accepting the local server as a documented constraint. That decision belongs to the target-architecture step and depends on whether Python may run on the managed laptop (see unresolved questions).

---

## 14. Owner decisions recorded after the assessment (2026-10-02)

These are the repository owner's answers to the open questions from the assessment. They are inputs for the target-architecture step (`.claude/prompts/02-target-architecture.md`).

| ID | Question | Owner answer | Consequence for the target architecture |
|---|---|---|---|
| OD-1 | May Python run on the managed laptop? | Yes, **but users are mostly non-technical**: start-up and every operation must happen through UI interaction, not a terminal. | Terminal steps (`pip install`, `export`, `python server.py`, `seed_sqlite.py`) aren't acceptable for users. The target must either run entirely in the browser or have a one-click start that needs no command line. Prefer the option with the fewest user steps. |
| OD-2 | Which UI survives, V1 or V2? | **Neither is valued.** Both were scaffolding produced while experimenting with a coding agent; the owner doesn't remember which features work. | Treat both UIs as disposable reference material, not as code to preserve. Use the assessment to identify the *behaviours* worth keeping. Don't spend effort extracting or refactoring the inline scripts. The back-end domain logic (extraction, personas, review/proposal model) is the main asset to evaluate. |
| OD-3 | Is the external-reviewer feedback link (`/feedback?token=`) needed? | Not now. Ignore. | Out of scope for the first target. Don't design network exposure for it. |
| OD-4 | Are Docker and Compose in scope? | **No.** | `Dockerfile`, `docker-compose.yml`, `.dockerignore` become removal candidates; no container start-up path in the target. |
| OD-5 | Licence | **MIT**, as stated in the README. The repo is intended to become public, but is still in development. | Add a `LICENSE` file. Before making the repository public: fix security BLOCKER/HIGH items, keep demo data synthetic, and note that commit author names and e-mail addresses in Git history become public. |
| OD-6 | Approved AI providers | **OpenRouter** as the single generic API provider. Ideally the app works with **Microsoft 365 Copilot licences without any API**. | Keep exactly one external AI provider slot (OpenRouter), off by default, with a visible notice before data leaves the device. Other provider adapters (Groq, Gemini, Bedrock, Ollama) are removal candidates. Copilot support means charter §8 **Pattern A**: the app produces a copy-ready package, the user pastes or uploads it into Copilot themselves, and the reply is brought back labelled Draft. No Copilot API or browser automation. |
| OD-7 | Commit the charter and `.claude/prompts/`? | Yes. | Done on branch `assessment/pwa-readiness-2026-10`. |
| OD-8 | Do browser protections block the cross-site attack (security H-3)? | Owner can't assess. | Treat it as **not mitigated**. The target must not rely on browser protections; remove the cause (no unauthenticated local API, or strict origin checks). |
| OD-9 | Real test pass rate | Unknown. | Measure it only if existing tests are kept; given OD-2, prefer new tests written against the target behaviours. |

**Context from the owner:** the current code is an early experiment in using a coding agent to bring an idea to life. The owner is a project manager with an interest in technology, not a software engineer. Target-architecture choices should favour the fewest moving parts, plain-language operation, and steps a non-specialist can verify.
