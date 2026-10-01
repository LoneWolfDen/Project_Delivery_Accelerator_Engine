# Minified and Generated Code Register

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Commit | `1ca4319` |
| Scope | All 249 tracked files, plus runtime-generated artefacts the application writes outside Git |

---

## 1. Summary

**There are no minified JavaScript or CSS files and no source maps in this repository**, tracked or untracked.

Evidence:

- `git ls-files | grep -E '\.min\.|\.map$'`: no results.
- Line-length profile of every tracked `.js`, `.css` and `.html` file: maximum line 410 characters (`static/v2/dashboard_v2.html`), averages 22–61 characters, 0 lines over 500 characters. Minified bundles typically have lines of thousands to millions of characters.
- No `package.json`, bundler config (`webpack`, `vite`, `rollup`, `esbuild`), `tsconfig`, or compiled-CSS toolchain (Sass, PostCSS, Tailwind) exists.
- No vendor directory and no third-party browser library is shipped. The served UI uses only browser built-ins.
- Variable and function names in served code are descriptive (`escHtml`, `renderReviewDetail`, `toggleFileActive`), and comments are present throughout. Readable source *is* what the browser runs.

So charter concerns 3–9 (minified application code, source-map exposure, patched minified bundles, misleading beautification) **do not apply to the current state**. Charter §2 rules about generated code still apply to the small set of derived and generated files below.

## 2. Answers to the specific charter questions

| Question | Answer | Evidence |
|---|---|---|
| Is the app React, Vue, another framework, or static/generated HTML? | **None of these.** Hand-written static HTML with large inline vanilla-JS blocks, served by a Python server. Not generated. | `static/index.html` (16 inline blocks), `static/v2/dashboard_v2.html` (9 inline blocks plus 2 external scripts) |
| Does readable source exist for what the browser executes? | **Yes, the served files are the source.** | Same files |
| Do minified files have readable counterparts? | N/A: none exist | §1 |
| Can generated files be reproduced? | Only one tracked application file is derived (`reconciliation_panel.js`), and it's a **manual byte copy** with no generator. Runtime artefacts are reproducible from their generator modules. | §3, §4 |
| Do source maps expose source? | No source maps exist | §1 |
| Has minified code been patched by override layers? | No. There is, however, an *analogous* problem: unused modular V2 files sit beside an inline monolith, and later features were added to the unused files. | `CURRENT_IMPLEMENTATION_ASSESSMENT.md` U1–U5 |
| Would unminification be misleading? | N/A: names and component structure are intact | — |
| Safest migration to maintainable source | No source recovery is required. Recommended: **controlled extraction** of inline `<script>` blocks into ES-module files, unchanged in behaviour, guarded by browser-level compatibility tests, and removal of the orphaned modular set after verification. See `CURRENT_IMPLEMENTATION_ASSESSMENT.md` §13. | — |

## 3. Register: tracked derived and generated files

Fields: path · file type · size · likely origin · application or vendor · readable source exists · source map exists · generator exists · runtime usage · licence · vulnerability implications · disposition.

### G-1 `static/v2/js/reconciliation_panel.js`

| Field | Value |
|---|---|
| File type | JavaScript (plain, readable) |
| Size | 16,845 bytes, 379 lines |
| Likely origin | Manual copy of `ui/v2/components/ReconciliationPanel.js` (byte-identical, `diff -q`), because `server.py` can only serve files under `static/`. Header comments in `docs/architecture/review_proposal_workbench_end_to_end.md:774` call it "(source) + (served)". |
| Application or vendor | Application |
| Readable source exists | Yes (both copies are readable and identical) |
| Source map exists | No |
| Generator exists | **No.** Sync is manual; `tests/test_v2_phase3_and_phase4.py:455-459` only asserts the two match. |
| Runtime usage | Loaded by `static/v2/dashboard_v2.html:1849`. **Non-functional at runtime**: depends on `window.API` (`:246`), which nothing loaded defines. |
| Licence | Repository licence (none present; README claims MIT) |
| Vulnerability implications | Renders via `innerHTML` with `esc()` helpers (27 escapes / 12 sinks); no specific defect found |
| Recommended disposition | **REMOVE AFTER VERIFICATION** (one of the pair). Keep a single source of truth under the served tree; drop the copy under `ui/v2/` once the served-UI decision is made. |

### G-2 `docs/architecture_diagram.drawio`

| Field | Value |
|---|---|
| File type | draw.io XML (`<mxfile host="app.diagrams.net" … agent="Kiro">`) |
| Size | 43,083 bytes |
| Likely origin | Generated or edited by the Kiro AI agent through draw.io format (2026-05-28) |
| Application or vendor | Documentation (not application runtime) |
| Readable source exists | It *is* the source (XML), editable in draw.io |
| Source map exists | N/A |
| Generator exists | No checked-in generator |
| Runtime usage | None |
| Licence | Repository licence |
| Vulnerability implications | None |
| Recommended disposition | **KEEP**, but treat as **unverified** because it predates major restructuring. Validate it against the implementation before reuse. |

### G-3 to G-8 `_archive/migration_demo/diagrams/*.drawio` and `_archive/migration_demo/migration_dashboard_pkg/diagrams/*.drawio`

| Path | Size |
|---|---|
| `_archive/migration_demo/diagrams/data_flow_diagram.drawio` | 37,760 |
| `_archive/migration_demo/diagrams/migration_dependency_diagram.drawio` | 17,642 |
| `_archive/migration_demo/diagrams/operational_dependency_diagram.drawio` | 19,680 |
| `_archive/migration_demo/migration_dashboard_pkg/diagrams/data_flow_diagram.drawio` | 37,760 (duplicate) |
| `_archive/migration_demo/migration_dashboard_pkg/diagrams/migration_dependency_diagram.drawio` | 17,642 (duplicate) |
| `_archive/migration_demo/migration_dashboard_pkg/diagrams/operational_dependency_diagram.drawio` | 19,680 (duplicate) |

| Field | Value |
|---|---|
| File type | draw.io XML (`agent="draw.io" version="21.0.0"`) |
| Likely origin | Exported from draw.io for an earlier, unrelated "migration dashboard" demo (2026-05) |
| Application or vendor | Archived demo |
| Readable source exists | Yes (XML) |
| Source map / generator | No / No |
| Runtime usage | None (`_archive/` excluded from package and Docker image) |
| Licence | Repository licence |
| Vulnerability implications | None |
| Recommended disposition | **ARCHIVE** (already in `_archive/`). The `migration_dashboard_pkg/` duplicates: **REMOVE AFTER VERIFICATION**. |

### G-9 / G-10 `docs/planning/review_workbench_transformation_backlog.json` and `.md`

| Field | Value |
|---|---|
| File type | JSON (18,953 B) and Markdown (7,321 B) |
| Likely origin | Planning artefact; JSON shape (`backlog_name`, `version`, `goal`) suggests machine-generated or agent-authored. The Markdown may be rendered from the JSON. **UNKNOWN**: no generator present. |
| Application or vendor | Documentation |
| Readable source exists | Yes |
| Source map / generator | No / No |
| Runtime usage | None |
| Licence | Repository licence |
| Vulnerability implications | None |
| Recommended disposition | **KEEP** as historical planning; mark superseded once the new backlog exists. |

## 4. Register: runtime-generated artefacts (not in Git)

These are produced by the application on the server's disk under `PROJECTS_DATA_DIR` (default `./projects_data`) and are git-ignored (`.gitignore`: `projects_data/`, `projects.json`, `uploads/`, `outputs/*`). None are present in the working tree at assessment time.

| ID | Path pattern | Type | Generator (readable) | Reproducible? | Notes / disposition |
|---|---|---|---|---|---|
| R-1 | `projects_data/accelerator.db` (+ `-wal`, `-shm`) | SQLite | `db/database.py` `_SCHEMA_SQL`, `_apply_migrations`; demo content from `scripts/seed_sqlite.py`, `scripts/seed_demo.py` | Schema yes; **user data no** (no backup) | User data store. KEEP; needs backup/restore (charter §5). Readable via path traversal (security B-1). |
| R-2 | `projects_data/projects.json` | JSON | `services/project.py:save_projects`; `db/project_store_sql.py:_rebuild_projects_file` | Mirror of SQLite | Dual-write mirror; divergence risk (security M-7) |
| R-3 | `projects_data/admin_config.json` (cwd-relative) | JSON | `admin/config.py:save_config` | Yes | Contains plaintext PIN and API keys (security H-5) |
| R-4 | `projects_data/<pid>/context/*.json` | JSON | `services/ingest.py` | From original inputs only | Keyed by filename stem; silent overwrite (M-6) |
| R-5 | `projects_data/<pid>/raw/<artifact_id>_<name>` | Original uploads | `processors/artifact_store.py`, `db/artifact_store_sql.py` | No (user content) | Primary user data |
| R-6 | `projects_data/<pid>/intelligence/`, `run_history/`, `proposals/tracker.json` | JSON | `processors/history.py`, `db/project_store_sql.py` | Partly | Derived; re-buildable from context |
| R-7 | Diagram `.drawio` downloads | XML (in-memory, streamed) | `processors/diagram_generator.py` | Yes | GENERATED on request; not stored in Git |

## 5. Vendor files

None. No third-party browser code is shipped, so charter §2's vendor-manifest requirement (name, version, licence, source, hash) has nothing to record. Any future vendor library must go under a dedicated vendor directory with that manifest.
