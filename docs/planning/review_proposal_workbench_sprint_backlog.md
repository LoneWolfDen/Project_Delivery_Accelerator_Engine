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

## Sprint 2 — Review Iteration (PLANNED)

**Goal:** Create a new review from one selected previous review.

**Status:** Not started

**Module:** Review lineage + controlled iteration

**Stories:**
- Add/select `previous_review_id` on review creation
- Create new review from selected prior review as contextual input
- Persona can be changed between iterations
- Lineage visible in Review Full Details

**Acceptance criteria:**
- No overwrite of prior review
- New review clearly linked to predecessor
- Prior review ID shown in Full Details drawer

---

## Sprint 3 — Reconciliation (PLANNED)

**Goal:** Reconcile selected reviews into one proposal-ready decision pack.

**Status:** Not started

**Module:** Review selection + reconciliation

---

## Sprint 4 — Coverage + Proposal Data Pack (PLANNED)

**Goal:** Turn reconciled intelligence into proposal-ready structure.

**Status:** Not started

---

## Sprint 5 — Forward Guidance (PLANNED)

**Goal:** Tell users what to do next, grounded in unresolved items.

**Status:** Not started
