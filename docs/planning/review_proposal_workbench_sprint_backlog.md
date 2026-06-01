# Review & Proposal Workbench — Sprint Backlog

**Source of truth:** `/docs/architecture/review_proposal_workbench_architecture.md`

> This file tracks sprint delivery status. Each sprint maps to one independent module. Completed sprints are marked and their outcomes summarised.

---

## Sprint 1 — Review Traceability + Full Details ✅ COMPLETE

**Goal:** Make reviews self-explanatory, traceable, and trustworthy.

**Branch:** `sprint1/review-full-details-traceability`

### Stories delivered

| # | Story | Status |
|---|-------|--------|
| 1.1 | Show Version ID, Persona, Prompt Used, Top 3 Risks in Review Full Details | ✅ Done |
| 1.2 | Show included artifacts with type-aware provenance chips | ✅ Done |
| 1.3 | Add weakness status + optional free-text user note | ✅ Done |
| 1.4 | Ensure review click opens Full Details, not Compare | ✅ Done |
| 1.5 | Keep Compare as secondary explicit action | ✅ Done |
| 1.6 | Add `artifact_refs[]` field to Review model (backward compatible) | ✅ Done |
| 1.7 | Persist `weakness.user_note` via new API endpoint | ✅ Done |

### Acceptance criteria — verified

- [x] Users can understand a review without hidden context
- [x] Version ID, Persona, Prompt always visible on review open
- [x] Provenance chips visible for documents, slides, emails, meetings, spreadsheets
- [x] Weakness note persists and re-appears on re-open
- [x] Page does not grow uncontrollably (collapse/expand used)
- [x] v1 untouched

### Files changed

**Backend:**
- `models/hierarchy.py` — added `artifact_refs` field to `Review` dataclass; `prompt_used` + `artifact_refs` added to `to_summary()`
- `db/database.py` — `artifact_refs TEXT DEFAULT '[]'` migration added
- `db/hierarchy_store_sql.py` — `artifact_refs` in `create_review()` + `_row_to_review()`
- `services/review.py` — `update_weakness_note()` added
- `handlers/review.py` — `handle_weakness_note()` added
- `server.py` — `POST /weakness/{wid}/note` route added
- `project_manager.py` — `update_weakness_note` re-exported

**Frontend (v2 only):**
- `static/v2/js/review_detail.js` — **NEW** `ReviewDetail` module (F1/F2/F3)
- `static/v2/js/api.js` — `updateWeaknessStatus()`, `updateWeaknessNote()` added; mock reviewDetail enriched
- `static/v2/js/dashboard.js` — `_renderDrawerContent` + `_loadDrawerDetail` prefer `ReviewDetail`
- `static/v2/dashboard_v2.html` — `review_detail.js` script tag added
- `static/v2/css/components.css` — Sprint 1 `.rd-*` CSS classes appended

**Tests:**
- `tests/test_rw_sprint1_review_traceability.py` — **NEW** 90 tests, all passing

**Docs:**
- `docs/architecture/data_model.md` — Review entity updated (artifact_refs, weakness schema)
- `docs/architecture/application_flow.md` — Review drawer flow updated (ReviewDetail)
- `docs/architecture/logic_flow.md` — Section §8 added (weakness note/status logic)
- `docs/architecture/traceability_map.md` — §1.3, §1.7, §2–§6 updated
- `docs/planning/review_proposal_workbench_sprint_backlog.md` — **THIS FILE** created

### New API endpoints (Sprint 1)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/note` | `handle_weakness_note` | Persist user note on weakness |

---

## Sprint 2 — Review Iteration ✅ COMPLETE

**Goal:** Create a new review from one selected previous review.

**Branch:** `sprint2/review-iteration-lineage`

**Status:** Complete

**Module:** Review lineage + controlled iteration

### Stories delivered

| # | Story | Status |
|---|-------|--------|
| 2.1 | Create new review from selected existing review (user-initiated) | ✅ Done |
| 2.2 | Store `previous_review_id` on new review; base review unchanged | ✅ Done |
| 2.3 | Pass base review content as context input to new review execution | ✅ Done |
| 2.4 | Carry forward open decision points from base review | ✅ Done |
| 2.5 | Optional persona change on iteration; `persona_used` stored on new review | ✅ Done |
| 2.6 | Show lineage banner in Full Details drawer when `previous_review_id` present | ✅ Done |
| 2.7 | "Create New Review" form in drawer — explicit toggle, not automatic | ✅ Done |
| 2.8 | Result card confirms new review ID, persona, predecessor, created_at | ✅ Done |
| 2.9 | Legacy reviews without `previous_review_id` render cleanly (no banner) | ✅ Done |

### Acceptance criteria — verified

- [x] No overwrite of prior review — original is immutable
- [x] New review clearly linked to predecessor via `previous_review_id`
- [x] Prior review ID shown in Full Details drawer lineage banner
- [x] Persona selection is optional; defaults to base review persona
- [x] Persona change clearly indicated (`persona_changed` flag + badge)
- [x] Open decision points carried forward from base review
- [x] Sprint 1 features (weakness notes, provenance chips) still working
- [x] v1 untouched

### Files changed

**Backend:**
- `services/review.py` — `create_review_iteration()` added (Sprint 2)
- `handlers/review.py` — `handle_create_review_iteration()` added (Sprint 2)
- `server.py` — `POST /hierarchy/reviews/{rid}/iterate` route added (Sprint 2)
- `project_manager.py` — `create_review_iteration` re-exported

**Frontend (v2 only):**
- `static/v2/js/api.js` — `createReviewIteration()` added + exported; mock updated
- `static/v2/js/review_detail.js` — `_renderIterationBanner()`, `_renderCreateIterationAction()`, `onToggleIterationForm()`, `onCreateIteration()`, `_renderIterationResult()` added; `renderReview()` updated
- `static/v2/css/components.css` — Sprint 2 `.ri-*` CSS classes appended

**Tests:**
- `tests/test_rw_sprint2_review_iteration.py` — **NEW** 109 tests, all passing (sections A–K)

**Docs:**
- `docs/architecture/data_model.md` — Sprint 2 Review additions (previous_review_id schema, iteration lineage schema, key relationship rule)
- `docs/architecture/application_flow.md` — Review Iteration Flow diagram added; Linked Components + State Machine updated
- `docs/architecture/traceability_map.md` — §1.8 (Review Iteration) added; §2, §3, §4, §5, §6 updated
- `docs/planning/review_proposal_workbench_sprint_backlog.md` — Sprint 2 marked complete

### New API endpoints (Sprint 2)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/api/projects/{pid}/hierarchy/reviews/{rid}/iterate` | `handle_create_review_iteration` | Create new review from existing review with lineage |

---

## Sprint 3 — Reconciliation ✅ COMPLETE

**Goal:** Reconcile selected reviews into one proposal-ready decision pack.

**Branch:** `sprint3/multi-review-reconciliation`

**Status:** Complete

**Module:** Explicit review selection + reconciliation engine + output

### Stories delivered

| # | Story | Status |
|---|-------|--------|
| 3.1 | Explicit review selection — anchor + supplemental (no auto-select) | ✅ Done |
| 3.2 | `ReconciliationSelection` model + persistence (`reconciliation_selections` table) | ✅ Done |
| 3.3 | Reconciliation engine — consensus, divergent, decisions, weaknesses, merged findings | ✅ Done |
| 3.4 | `ReconciliationOutput` model with all sections + `provenance_summary` | ✅ Done |
| 3.5 | Provenance retention — every output item carries `source_reviews[]` | ✅ Done |
| 3.6 | Reconciliation output persistence (`reconciliation_outputs` table) | ✅ Done |
| 3.7 | Handler + 4 API routes (POST select, POST run, GET selection, GET output) | ✅ Done |
| 3.8 | Frontend reconciliation panel in review drawer (explicit, not automatic) | ✅ Done |
| 3.9 | Sprint 1 + Sprint 2 non-regression confirmed | ✅ Done |

### Acceptance criteria — verified

- [x] User explicitly selects anchor review and supplemental reviews — no auto-selection
- [x] Active Review pre-populated as anchor in UI — user must confirm
- [x] Reconciliation produces: consensus, divergent, open decisions, confirmed decisions, unresolved weaknesses, merged findings, provenance summary
- [x] Every output item carries `source_reviews` with `is_anchor` flag
- [x] Provenance preserves `review_id`, `persona`, artifact refs where available
- [x] Original reviews unchanged after reconciliation
- [x] Anchor-only mode works (single review)
- [x] Old reviews without reconciliation fields render safely
- [x] Sprint 1 features (weakness notes, provenance chips) still working
- [x] Sprint 2 features (review iteration, lineage banner) still working
- [x] v1 untouched

### Files changed

**New files:**
- `models/reconciliation.py` — `ReconciliationSelection`, `ProvenanceRef`, `ReconciledItem`, `NormalisedReviewInput`, `ReconciliationOutput`
- `services/reconciliation.py` — `save_reconciliation_selection`, `get_reconciliation_selection`, `run_reconciliation`, `get_reconciliation`; full engine
- `handlers/reconciliation.py` — `handle_save_selection`, `handle_get_selection`, `handle_run_reconciliation`, `handle_get_reconciliation`
- `tests/test_rw_sprint3_reconciliation.py` — 129 tests (sections A–L), all passing

**Modified files:**
- `db/database.py` — `reconciliation_selections` + `reconciliation_outputs` tables in schema + migration
- `db/hierarchy_store_sql.py` — `save_reconciliation_selection`, `get_reconciliation_selection`, `save_reconciliation_output`, `get_reconciliation_output`
- `models/hierarchy.py` — file-store reconciliation stubs (4 methods)
- `project_manager.py` — Sprint 3 reconciliation functions re-exported
- `server.py` — `import h_reconciliation`; 2 POST + 2 GET routes registered
- `static/v2/js/api.js` — `saveReconciliationSelection`, `fetchReconciliationSelection`, `runReconciliation`, `fetchReconciliation` + mock data; exported on `window.API`
- `static/v2/js/review_detail.js` — `_renderReconciliationPanel`, `onToggleReconciliationPanel`, `onRunReconciliation`, `_renderReconciliationResult`, handlers exported; `renderReview` updated
- `static/v2/css/components.css` — Sprint 3 `.rc-*` CSS classes appended

**Docs:**
- `docs/architecture/data_model.md` — Sprint 3 entities, ERD, schema examples, relationship rules
- `docs/architecture/application_flow.md` — Reconciliation Flow diagram, state machine updated
- `docs/architecture/logic_flow.md` — §9 Reconciliation Selection + Engine Logic
- `docs/architecture/traceability_map.md` — §1.9, §2–§6 updated
- `docs/planning/review_proposal_workbench_sprint_backlog.md` — Sprint 3 marked complete

### New API endpoints (Sprint 3)

| Method | Path | Handler | Purpose |
|--------|------|---------|---------|
| POST | `/api/projects/{pid}/hierarchy/versions/{vid}/reconciliation/select` | `handle_save_selection` | Save explicit anchor + supplemental selection |
| POST | `/api/projects/{pid}/hierarchy/versions/{vid}/reconciliation/run` | `handle_run_reconciliation` | Run reconciliation, return output |
| GET  | `/api/projects/{pid}/hierarchy/versions/{vid}/reconciliation/selection` | `handle_get_selection` | Fetch stored selection |
| GET  | `/api/projects/{pid}/hierarchy/versions/{vid}/reconciliation` | `handle_get_reconciliation` | Fetch stored output |

---

## Sprint 4 — Coverage + Proposal Data Pack (PLANNED)

**Goal:** Turn reconciled intelligence into proposal-ready structure.

**Status:** Not started

---

## Sprint 5 — Forward Guidance (PLANNED)

**Goal:** Tell users what to do next, grounded in unresolved items.

**Status:** Not started
