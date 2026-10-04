# Repository Cleanup Candidates

| Field | Value |
|---|---|
| Assessment date | 2026-10-01 |
| Commit | `1ca4319` |
| Status | **Candidates only.** Nothing here has been deleted, moved or archived. Each item needs verification and an approved change before action (charter §13). |

Dispositions: **KEEP**, **ARCHIVE** (move out of the active tree or into `_archive/`), **REMOVE AFTER VERIFICATION**, **CONSOLIDATE** (merge duplicates into one source of truth), **FIX** (keep, but it's wrong), **DECIDE** (needs an owner decision first).

---

## 1. Orphaned or unused application code

| # | Path | Size | Evidence it's unused | Verification needed before action | Disposition |
|---|---|---|---|---|---|
| C-1 | `static/v2/js/api.js` | 16.8 KB | Not referenced by any served HTML since `f89c4b2` (2026-06-02). Contains `MOCK_DATA` (`:22`) that becomes active if re-linked without `V2_USE_MOCK=false`. | Decide V2's future; confirm that no route or test besides string checks depends on it | DECIDE → REMOVE AFTER VERIFICATION, or re-link deliberately with mock removed |
| C-2 | `static/v2/js/state.js`, `dashboard.js`, `accordion.js`, `search.js`, `summary.js` | 6.6 + 24.7 + 12.5 + 14.5 + 11.6 KB | Same as C-1 | Same | DECIDE → REMOVE AFTER VERIFICATION |
| C-3 | `static/v2/css/theme.css`, `layout.css`, `components.css` | 7.7 + 9.2 + 20.1 KB | No `<link>` in any served page; V2 styles are inline | Same | DECIDE → REMOVE AFTER VERIFICATION |
| C-4 | `ui/v2/components/Cards.js`, `DetailPanel.js`, `Header.js`, `Sidebar.js`; `ui/v2/layout/MainLayout.js`; `ui/v2/utils/helpers.js` | ~57 KB | Outside `static/`, so the server can't serve them (`server.py:146-151`) | Confirm that no external tool consumes them | REMOVE AFTER VERIFICATION |
| C-5 | `ui/v2/components/ReconciliationPanel.js` ↔ `static/v2/js/reconciliation_panel.js` | 16.8 KB each | Byte-identical; manual sync enforced by a test | Keep the served copy only | CONSOLIDATE |
| C-6 | `contracts/` (`bus.py`, `protocols.py`, `types.py`, `__init__.py`) | ~13.6 KB | Imported only by itself | Confirm there's no dynamic import; `grep` showed none | REMOVE AFTER VERIFICATION |
| C-7 | `project_manager.py` (compat shim) | 5.5 KB | Still used by `server.py`, `cli.py` and tests | Replace imports first | KEEP for now; future CONSOLIDATE |
| C-8 | One of the two UIs (`static/index.html` V1 vs `static/v2/dashboard_v2.html` V2) | 292 KB / 108 KB | Both are complete, independently maintained SPAs with duplicated helpers (`api()`, `escHtml`) and diverging features | Owner decision on the single target UI | DECIDE |

## 2. Archived or legacy material

| # | Path | Size | Evidence | Disposition |
|---|---|---|---|---|
| C-9 | `_archive/migration_demo/**` | ~600 KB, ~70 files | Unrelated earlier "migration dashboard" demo; excluded from packaging and Docker; own `localStorage` persistence | ARCHIVE outside the main branch (e.g. a tag or separate branch), then REMOVE AFTER VERIFICATION |
| C-10 | `_archive/migration_demo/migration_dashboard_pkg/**` | ~250 KB | Near-duplicate of the parent folder (`gates_data.py`, `stories_data.py`, diagrams, CSVs identical; `server.py` differs slightly) | REMOVE AFTER VERIFICATION |
| C-11 | `_archive/migration_demo/sample_data/sample_data/*` | ~20 KB | Duplicates `sample_data/` (`scope.txt` identical) | REMOVE AFTER VERIFICATION |
| C-12 | `_archive/migration_demo/tests/tests/*` | ~12 KB | Tests for the archived demo; not in `testpaths` scope (nested) | ARCHIVE with C-9 |

## 3. Tests that validate dead code or nothing

| # | Path | Evidence | Disposition |
|---|---|---|---|
| C-13 | Test cases using fixtures `api_js`, `detail_js`, `dashboard_js`, `accordion_js`, `recon_js` (~90) in `tests/test_v2_phase1_and_phase2.py`, `tests/test_v2_phase3_and_phase4.py` | Assert on unserved files | FIX: repoint to served code or replace with browser-level tests; remove alongside C-1 to C-4 |
| C-14 | `tests/test_server.py` | Only checks method attributes exist | FIX: replace with HTTP routing tests |
| C-15 | `tests/test_persona_engine.py` | Imports removed symbol `AVAILABLE_PERSONAS`; breaks the whole suite | FIX (highest priority among tests) |

## 4. Documentation that contradicts the implementation

| # | Path | Problem | Disposition |
|---|---|---|---|
| C-16 | `README.md` | "No database"; Docker "single container" works; MIT licence; "180+ tests"; CI badge; compose example differs from the real file | FIX after the target architecture is decided |
| C-17 | `docs/architecture/system_overview.md`, `docs/architecture/application_flow.md` | Describe the unloaded V2 modular architecture as live | FIX or mark superseded |
| C-18 | `docs/architecture/review_proposal_workbench_end_to_end.md` | Phase 3/4 marked "✅ Done" while unreachable or broken in served UI | FIX status |
| C-19 | `docs/architecture.md`, `docs/architecture/*.md`, `docs/architecture_diagram.drawio`, `docs/planning/*.md/json` (≈ 300 KB of planning/architecture prose) | Many overlapping plans (`MASTER_SPRINT_PLAN.md`, `sprint_plan.md`, `V2_DELIVERY_PLAN.md`, transformation backlog, refactor plan); several described as "single source of truth" | CONSOLIDATE into one current-state document plus an archived history folder |
| C-20 | `docs/test-plans/*` (10 files) | Manual plans with no execution record | KEEP; link to executed evidence once it exists |
| C-21 | `.kiro/specs/multi_review_synthesis.md`, `.kiro/steering/project-context.md` | Agent steering for a previous tool; "pyyaml only", "no build/framework" constraints are still largely accurate | DECIDE: keep as history or move under `docs/` |
| C-22 | Missing `LICENSE` | README and Docker label claim MIT | DECIDE (owner/legal), then add |

## 5. Build and configuration hygiene

| # | Path | Problem | Disposition |
|---|---|---|---|
| C-23 | `Dockerfile` | Missing source directories (D-1); `|| true` installs | FIX or remove the Docker path if out of scope for the PWA target |
| C-24 | `docker-compose.yml` | `ollama:latest`; `0.0.0.0` exposure | FIX or remove with C-23 |
| C-25 | `pyproject.toml` | Package list incomplete; unused extras `ollama`, `google-genai`, `strands-agents*` | FIX |
| C-26 | `.github/workflows/ci.yml` | Permanently red; no JS or browser checks | FIX |
| C-27 | `outputs/.gitkeep`, `docs/.gitkeep` | `outputs/` is a runtime folder; `docs/.gitkeep` is redundant now that `docs/` has content | REMOVE AFTER VERIFICATION (`docs/.gitkeep`); KEEP `outputs/.gitkeep` until runtime path decided |

## 6. Git hygiene

| # | Item | Evidence | Disposition |
|---|---|---|---|
| C-28 | ~120 remote branches | Feature, fix, revert and sprint branches, many merged (PRs #101–#118) | DECIDE: prune merged branches after confirming they're merged; keep `revert/*` and `base/pre-sprint1` as historical tags if needed |
| C-29 | Untracked `.claude/prompts/` and `docs/architecture/PWA_ARCHITECTURE_CHARTER.md` | Governing documents aren't under version control | DECIDE: commit the charter (it's described as mandatory) |
| C-30 | Commit authorship `Project Delivery Accelerator <dev@projectdelivery.ai>` (7 commits) | Third identity alongside the owner and `Kiro Agent` | Informational; no action |

## 7. Explicitly *not* cleanup candidates

- `sample_data/`: used by tests (`tests/conftest.py`) and seeding; synthetic.
- `scripts/seed_sqlite.py`, `scripts/seed_demo.py`, `scripts/migrate_decision_system.py`: generators for demo data and schema migration; keep.
- `personas/definitions/*.yaml`: runtime configuration.
- `static/v2/js/compare.js`, `static/v2/js/reconciliation_panel.js`: loaded by served V2 (the latter is non-functional, see C-5 and implementation U4).
