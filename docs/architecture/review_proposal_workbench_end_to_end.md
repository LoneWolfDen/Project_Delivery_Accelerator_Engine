# Review & Proposal Workbench — End-to-End Architecture and Specification

## 1. Purpose

This document defines the target end-to-end design for the Review & Proposal Workbench.

The goal is to move from isolated review outputs to a **traceable, iterative, decision-support system** that:
- preserves Version → Review context
- supports human + AI refinement
- reconciles selected reviews into proposal-ready intelligence
- shows why a risk, weakness, or recommendation exists
- remains lightweight and production-friendly

This document is the **source of truth** for future implementation planning and code review.

---

## 2. Scope

This architecture applies to:
- **v2 UI and v2 workflows**
- backend and data contracts needed to support v2 behaviour
- review, iteration, reconciliation, coverage, proposal, and guidance workflows

This architecture does **not** require:
- a full redesign of v1
- heavy new platform services
- client-specific proposal formatting
- microservices or a separate orchestration runtime

v1 remains a fallback / baseline unless explicitly changed.

---

## 3. Product Goal

The product should help users answer:

- What is missing?
- What is weak?
- What is unresolved?
- What should be decided next?
- Is this strong enough to move toward proposal / sign-off?

This is **not** a one-shot LLM wrapper.

This is a **decision and review workbench** built around:
- persistent context
- review evolution
- explicit provenance
- proposal synthesis from selected reviews

---

## 4. Design Principles

### 4.1 Traceability first
Every important output should be explainable:
- why is it being said?
- which artifact or prior review supports it?
- which persona and prompt produced it?

### 4.2 Review is evolving knowledge
A review is not disposable output.
A review can be:
- created
- refined
- compared
- referenced
- used as input to later reasoning

### 4.3 Proposal is synthesis
Proposal creation should reconcile **selected reviews** into a proposal-ready intelligence pack.
It should not behave like a free-form standalone generator.

### 4.4 Human input improves intelligence
User notes on weaknesses are part of the intelligence system.
They should influence future review iterations and later synthesis.

### 4.5 Keep it lightweight
- additive changes
- backward-compatible where possible
- module boundaries clear
- no unnecessary new entities
- no heavy new runtime

---

## 5. Core Conceptual Model

```mermaid
flowchart LR
    P[Project] --> V[Version]
    V --> R[Review]
    R --> RI[Review Iteration]
    R --> RS[Review Selection]
    RI --> RS
    RS --> RC[Reconciliation]
    RC --> CV[Coverage]
    CV --> PP[Proposal Data Pack]
    PP --> PR[Proposal Review]
    PR --> FG[Forward Guidance]



6. User Value by Stage
6.1 Ingest and Version
User value:

knows what artifacts are included
trusts the context behind later reviews

6.2 Review
User value:

sees persona, prompt, and top risks immediately
understands what the review is based on

6.3 Review Iteration
User value:

can build on one selected prior review
can refine a line of thinking deliberately

6.4 Reconciliation
User value:

can combine multiple selected perspectives without losing clarity
sees where reviews agree, disagree, or leave decisions open

6.5 Proposal Output
User value:

gets a reusable proposal intelligence pack
sees what is covered, what is weak, and what to do next

This matches the review style expected by the existing system: reviews should evaluate architecture, scope, delivery, resourcing, and financial concerns, and the output structure already expects discovered artefacts to be part of the result set.

7. End-to-End Workflow

<img width="4032" height="555" alt="image" src="https://github.com/user-attachments/assets/145105b9-7fb9-4bcc-822a-5316c1207069" />

8. Agent / Module Responsibilities
The implementation should be modular. These do not require separate services; they can be implemented as internal processors / modules.
8.1 Version Context Builder
Purpose: build trusted context for a selected Version
Input

project
version
selected artifacts
artifact metadata

Output

version ID
artifact inventory
normalized context summary
provenance-ready artifact refs


8.2 Review Analyzer
Purpose: run persona-specific review against version context
Output

risks
assumptions
dependencies
constraints
action items
weaknesses
decision points

Each item should preserve provenance if available.

8.3 Weakness + Note Handler
Purpose: attach user judgment to AI findings
Each weakness supports:

text
status
optional free-text user note
provenance


8.4 Review Iteration Handler
Purpose: create a new review from one user-selected prior review
Rules

prior review is explicit, never automatic
new review is created, old review is not overwritten
prior review becomes part of contextual input
persona may be changed


8.5 Reconciliation Engine
Purpose: reconcile explicitly selected reviews into one proposal-grade intelligence pack
Output

consensus points
divergent / conflicting points
confirmed decisions
open decisions
unresolved weaknesses
merged findings
provenance summary


8.6 Coverage Mapper
Purpose: show what proposal intelligence covers
Domains

Scope
Architecture
Delivery
Security / Compliance
Operations
Commercials

Statuses

Addressed
Partial
Not Yet Addressed


8.7 Proposal Builder
Purpose: create a Proposal Data Pack (not client-formatted document yet)
Output sections

Executive Position
Client Need / Problem Framing
Recommended Solution Approach
What This Proposal Covers
Key Assumptions
Confirmed Decisions
Open Decisions / Clarifications Needed
Key Risks and Mitigations
Delivery Approach and Phasing
Operations / MSP Considerations
Commercial Sensitivities
Why This Proposal Is Credible
Next Best Actions


8.8 Proposal Review Agent
Purpose: critique the proposal data pack
Output

Covered Well
Still Weak
May Block Sign-off

Across the same domains as coverage.

8.9 Forward Guidance Agent
Purpose: suggest practical next actions
Must be grounded only in:

unresolved weaknesses
open decisions
conflicts
coverage gaps


9. Provenance Model
Goal
Provenance must be human-meaningful, not generic.
9.1 Artifact-type-aware provenance
Documents / Word / PDF

artifact name
section / heading
page number
optional short excerpt

Slides / PowerPoint

artifact name
slide number
optional slide title

Email

subject
date
optional sender

Meeting notes / transcript

meeting name
date
timestamp or section
optional speaker if available

Spreadsheet

workbook name
sheet
row range / label if available

9.2 Provenance payload shape
{
  "artifact_id": "a123",
  "artifact_name": "RFP.pdf",
  "artifact_type": "document",
  "section_reference": "Delivery Model",
  "page_reference": "3",
  "excerpt": "Optional short snippet"
}

9.3 UI pattern
Use lightweight chips or short reference lines.
Do not flood the UI with full citations.

10. UI Contract
10.1 Review Full Details
Must be visible immediately

Review ID
Version ID
Persona used
Prompt used
Top 3 risks
Status
Created / updated date

Expandable / scrollable sections

Included Artifacts
Findings
Weaknesses
Decision Points
User Notes
Raw output / extra detail

Weakness interaction
For each weakness:

text
status
optional free-text note
provenance chip

Interaction rule

clicking a review opens Full Details
compare is a secondary action
review remains the primary interaction

This is consistent with the repo intent that each review must expose Version context, included files/categories, persona, prompt, and output.

10.2 Proposal UI
Proposal should be a contextual workflow, not a detached standalone experience.
Primary path

select Version
select anchor review
optionally select supplemental reviews
reconcile
generate proposal data pack

Proposal output should show

summary
coverage
decisions
risks
blockers
next actions
lightweight provenance


11. Business Logic Rules
11.1 Version
A Version is a snapshot of:

selected artifacts
metadata
available context

11.2 Review
A Review is:

an execution on a Version
tied to a persona and prompt
expected to expose Version context + output + provenance

11.3 Review Iteration
A new review can be created from one user-selected prior review.
That base review becomes contextual input.
The new review must:

link back via previous_review_id
retain its own persona and prompt

11.4 Reconciliation
Reconciliation combines:

one anchor review
optional supplemental reviews
current version context

Rules:

no auto “latest N” selection
user explicit selection
preserve provenance
keep consensus, divergence, open decisions, unresolved weaknesses explicit

11.5 Proposal
Proposal uses reconciled output to build a reusable intelligence pack.
Formatting into client templates is a separate concern and not in scope here.

12. Data Relationships

<img width="1107" height="2268" alt="image" src="https://github.com/user-attachments/assets/0de33265-d2f7-42d3-9b26-0d198573940c" />


13. Minimal Data Contract Expectations
Review
Ensure support for:

version_id
artifact_refs[]
persona_used
prompt_used
prompt_builder_state
weaknesses[]
decision_points[]
previous_review_id
user_note per weakness

Proposal
Ensure support for:

version_id
anchor_review_id
selected_review_ids[]
reconciliation_result
proposal_review_pass
proposal_coverage
forward_guidance

No heavy new standalone business entity is required for this stage.

14. Traceability Flow

<img width="1038" height="2268" alt="image" src="https://github.com/user-attachments/assets/6cf6a5ee-d1c3-4529-a189-dbe2bc4290d7" />

15. Module Independence
Implementation should be modular so Kiro can:

compare current code vs target behaviour
plan module-by-module changes
implement incrementally without broad regressions

Recommended independent modules:

Review Full Details + traceability
Review iteration
Reconciliation
Coverage
Proposal data pack
Proposal review
Forward guidance


16. Production-readiness Guidelines

additive changes only
backward-compatible where feasible
explicit contracts over hidden state
lightweight persistence
deterministic logic where possible before downstream LLM usage
provenance carried through all downstream steps
tests and affected diagrams updated with each module change



---

## 17. Implementation Plan — Current State and Remaining Work

*Last updated: 2026-06-02. Based on a full cross-check of v2 code against this document and `sequence_flows.md`.*

---

### 17.1 Cross-Check Summary

| Layer | Status |
|-------|--------|
| Core data model (Phase → Version → Review) | ✅ Complete |
| Backend processors (synthesis, quality, proposal) | ✅ Complete |
| Backend services and handlers (CRUD, metrics, diff, gate) | ✅ Complete |
| Server routes (hierarchy, review, proposal, presales) | ⚠️ Partial — missing 7 routes |
| V2 frontend shell (state, API layer, layout, accordion) | ✅ Complete |
| V2 frontend — live data connection (mock flag off) | ✅ **Phase 1 — Done** |
| V2 DetailPanel — weakness notes + decision status | ✅ **Phase 2 — Done** |
| V2 DetailPanel — provenance line on findings | ✅ **Phase 2.3 — Done** |
| Review Iteration workflow (UI + route) | ❌ Not done — Phase 3 |
| Reconciliation workflow (UI + route) | ❌ Not done — Phase 4 |
| Proposal Data Pack workflow (UI + route) | ❌ Not done — Phase 6 |
| Proposal Review Pass (UI + route) | ❌ Not done — Phase 7 |
| Coverage Map (UI + route) | ❌ Not done — Phase 5 |
| Forward Guidance (UI + route) | ❌ Not done — Phase 7 |
| Provenance endpoint + full chips | ❌ Not done — Phase 8 |

---

### 17.2 What Is Already Implemented

#### 17.2.1 Backend — complete

**`models/hierarchy.py`**
- `Phase`, `Version`, `Review` dataclasses with all required fields
- `HierarchyStore` (file-based) and `_make_hierarchy_store()` factory (routes to SQLite-backed store when enabled)
- `Review` carries: `previous_review_id`, `iteration_number`, `weaknesses`, `decision_points`, `prompt_builder_state`, `quality_status`, `completeness_score`, `decided_by`

**`processors/review_quality.py`**
- `extract_weaknesses()` — derives weaknesses from findings with signal-phrase detection
- `extract_decision_points()` — derives decision points from findings
- `compute_decision_readiness()` — Low / Medium / High indicator
- `compute_completeness_score()` — 5-category gate (0–100)
- `check_review_gate()`, `complete_review()`, `set_active_review_with_gate()` — full quality gate chain

**`processors/review_synthesizer.py`**
- `normalize_review_findings()` — flattens findings to `NormalizedItem` list with provenance
- `deduplicate_normalized()` — Jaccard-based dedup across categories
- `build_reconciliation_prompt()` / `parse_reconciliation_response()` — LLM reconciliation
- `synthesize_reviews()` — full orchestrator: normalise → dedup → LLM or deterministic fallback
- `compute_proposal_coverage()` — six-domain coverage map (S3-01)
- `_run_decision_summary()` — decision classification into confirmed / open / blockers (S3-02)
- `extract_scope_themes()` — platform/keyword theme extraction
- `merge_decision_points()` — dedup decision points across selected reviews

**`processors/proposal_generator.py`**
- `_generate_files_only()` — deterministic proposal from review findings
- `_generate_ai()` — LLM-enriched proposal generation with graceful fallback
- `_run_proposal_review_pass()` — six-domain critique (AI + deterministic)
- `_run_forward_guidance()` — grounded next-action recommendations (AI + deterministic)
- `_check_generation_gate()` — validates active review status before generation

**`services/review.py`**
- `run_persona_review()` — full review run with version linking, weakness/decision extraction, iteration chaining via `previous_review_id`
- `update_weakness_status()` / `update_decision_status()` — status + user_note persistence
- `get_review_diff()` — finding-level diff against predecessor review
- `get_version_readiness()` — decision readiness for a version's active review
- `get_prompt_history()` — prompt log query

**`services/hierarchy.py`**
- Full hierarchy CRUD: phases, versions, reviews, active review, metrics, delete
- `compare_project_reviews()` — fixed to use hierarchy store (not flat-file path)

**`server.py` routes — confirmed present**
- `GET /api/projects/{pid}/hierarchy` — full tree
- `GET /api/projects/{pid}/hierarchy/metrics` — scoped metrics
- `GET /api/projects/{pid}/hierarchy/versions` / `/{vid}` / `/{vid}/readiness`
- `GET /api/projects/{pid}/hierarchy/reviews` / `/{rid}` / `/{rid}/quality` / `/{rid}/diff`
- `POST /api/projects/{pid}/hierarchy/reviews/{rid}/complete`
- `POST /api/projects/{pid}/hierarchy/reviews/{rid}/delete`
- `POST /api/projects/{pid}/hierarchy/versions/{vid}/set-active-review`
- `POST /api/projects/{pid}/hierarchy/versions/{vid}/set-active-review-gated`
- `POST /api/projects/{pid}/hierarchy/reviews/{rid}/weakness/{wid}/status`
- `POST /api/projects/{pid}/hierarchy/reviews/{rid}/decision/{did}/status`
- `POST /api/projects/{pid}/compare-reviews`
- `POST /api/review` — run review (supports `previous_review_id`)
- `GET/POST /api/projects/{pid}/proposal` and `/proposal/generate`
- `GET /api/projects/{pid}/prompt-history`

#### 17.2.2 Frontend V2 — shell complete

- `AppState` (`state.js`) — observable store, full selection cascade, drawer state
- `API` (`api.js`) — all fetch functions stubbed; mock data mirrors live shape exactly; `V2_USE_MOCK` flag controls switch
- `Dashboard` (`dashboard.js`) — init, loadAll, renderAll, selection handlers, drawer sync
- `VersionAccordion` (`accordion.js`) — render, expand/collapse, review click → drawer
- `DetailPanel` (`ui/v2/components/DetailPanel.js`) — renderVersion, renderReview (summary + findings + weaknesses skeleton)
- `Cards` / `Header` / `Sidebar` / `MainLayout` — implemented
- Sequences 1–6 from `sequence_flows.md` are fully implemented

---

### 17.3 Gap Analysis — What Is Missing

#### GAP-1: `api.js` mock flag not switched to live
- `window.V2_USE_MOCK` defaults to `true` in `api.js`
- Every API function returns mock data; real backend is never called in v2
- **Fix required:** set `V2_USE_MOCK = false` in `dashboard_v2.html` script block, or remove the flag entirely now that backend routes are stable

#### GAP-2: Missing backend routes (7 routes)

| Missing Route | Processor/Service Already Ready | Purpose |
|---------------|--------------------------------|---------|
| `POST /api/projects/{pid}/hierarchy/reviews/{rid}/iterate` | `services/review.run_persona_review()` (accepts `previous_review_id`) | Review Iteration Handler — create new review from selected prior |
| `POST /api/projects/{pid}/hierarchy/reconcile` | `processors/review_synthesizer.synthesize_reviews()` | Reconciliation Engine — reconcile selected reviews |
| `GET  /api/projects/{pid}/hierarchy/reviews/{rid}/provenance` | `models/hierarchy.Review` (carries `included_files`, `categories`, `prompt_used`, `persona`) | Provenance payload for a review |
| `POST /api/projects/{pid}/proposal/coverage` | `processors/review_synthesizer.compute_proposal_coverage()` | Coverage map — six-domain status |
| `POST /api/projects/{pid}/proposal/review-pass` | `processors/proposal_generator._run_proposal_review_pass()` | Proposal review — domain critique |
| `POST /api/projects/{pid}/proposal/forward-guidance` | `processors/proposal_generator._run_forward_guidance()` | Forward guidance — grounded next actions |
| `POST /api/projects/{pid}/proposal/proposal-data-pack` | All sub-processors ready; needs orchestration in `services/proposal.py` | Full proposal data pack endpoint |

All processors are implemented. These routes require thin handler + service wiring only.

#### GAP-3: V2 DetailPanel — weakness notes and decision status not wired

- `sequence_flows.md` §7 (Weakness User Note Update) is fully implemented in the backend and in `static/index.html` (v1)
- `ui/v2/components/DetailPanel.js` renders open weaknesses as read-only chips (`⚠ text`) — no status dropdown, no user_note textarea
- Decision points are not rendered at all in `DetailPanel.renderReview()`
- **Fix required:** add weakness interaction (status `<select>` + note `<textarea>` + blur handler calling `POST .../weakness/{wid}/status`) and decision point section (status `<select>`) to `DetailPanel.renderReview()`

#### GAP-4: Review Iteration UI — not present in v2

- No UI flow for: "select a prior review → create iteration from it"
- `accordion.js` and `dashboard.js` have action stubs but no iteration panel or modal
- Backend is ready: `POST /api/review` with `previous_review_id` already works
- **Fix required:** iteration trigger in DetailPanel or accordion action area; new route `POST .../iterate` as a semantic alias (or use existing `/api/review` with `previous_review_id` param)

#### GAP-5: Reconciliation workflow UI — not present in v2

- No UI for: select anchor review + optional supplementals → reconcile → view result
- `processors/review_synthesizer.synthesize_reviews()` is complete
- **Fix required:** reconciliation panel (modal or dedicated tab area), new route, result display showing consensus, conflicts, reconciliation notes

#### GAP-6: Proposal Data Pack workflow UI — not present in v2

- No UI for: version → anchor review → supplementals → reconcile → generate pack → view sections
- `processors/proposal_generator` is complete for single-review path; multi-review path needs orchestration
- **Fix required:** proposal workflow panel, new `proposal-data-pack` route, output display showing executive position, coverage, decisions, risks, blockers, next actions

#### GAP-7: Proposal Review Pass and Forward Guidance display — not present in v2

- `_run_proposal_review_pass()` and `_run_forward_guidance()` exist in `proposal_generator.py` but are only invoked internally during proposal generation
- No standalone routes and no v2 UI panels to surface these outputs independently
- **Fix required:** standalone routes + v2 display components for domain critique and grounded next actions

#### GAP-8: Coverage Map display — not present in v2

- `compute_proposal_coverage()` in `review_synthesizer.py` is complete
- No v2 UI component renders the six-domain (Scope / Architecture / Delivery / Security / Operations / Commercials) Addressed / Partial / Not Yet Addressed grid
- **Fix required:** `CoverageMap.js` component + route + integration into proposal or review detail view

#### GAP-9: Provenance chips — not present in v2

- Architecture doc §9 requires artifact-type-aware provenance chips on findings and weaknesses
- `Review` dataclass carries `included_files`, `categories`, `prompt_used`, `persona` — sufficient for lightweight provenance
- `DetailPanel.renderReview()` shows findings as plain text with no source reference
- **Fix required:** provenance chip rendering in `DetailPanel` + provenance endpoint

---

### 17.4 Remaining Implementation Work — Ordered Plan

Work is sequenced so each item builds on the previous. Items within a phase are independent and can be done in parallel.

---

#### Phase 1 — Connect V2 Frontend to Live Backend ✅ COMPLETE
*Completed: 2026-06-02*

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 1.1 | Disable mock flag | `static/v2/dashboard_v2.html` | ✅ Done — `window.V2_USE_MOCK = false` added in dedicated script tag before `compare.js` |
| 1.2 | Verify all 6 sequences work live | Manual smoke test | ✅ Sequences 1–6 functional; live path taken for all API calls |

**What was implemented:**
- Single `<script>window.V2_USE_MOCK = false;</script>` tag inserted before `compare.js` in `dashboard_v2.html`
- `_useMock()` guard in `api.js` reads `window.V2_USE_MOCK !== false` — explicit `false` disables mock for every call
- Mock data retained in `api.js` for offline/dev use; re-enable by setting `window.V2_USE_MOCK = true`

---

#### Phase 2 — Complete Review Detail in V2 ✅ COMPLETE
*Completed: 2026-06-02*

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 2.1 | Weakness status + user_note in DetailPanel | `ui/v2/components/DetailPanel.js`, `static/v2/js/api.js` | ✅ Done |
| 2.2 | Decision points section in DetailPanel | `ui/v2/components/DetailPanel.js`, `static/v2/js/api.js` | ✅ Done |
| 2.3 | Provenance line on findings | `ui/v2/components/DetailPanel.js` | ✅ Done |

**What was implemented:**

`static/v2/js/api.js`:
- `updateWeaknessStatus(projectId, reviewId, weaknessId, status, userNote)` — POST to `/hierarchy/reviews/{rid}/weakness/{wid}/status`; omits `user_note` key when `userNote` is `null` so existing notes are preserved server-side
- `updateDecisionStatus(projectId, reviewId, decisionId, status)` — POST to `/hierarchy/reviews/{rid}/decision/{did}/status`
- Both functions exposed on `window.API`

`ui/v2/components/DetailPanel.js` (full rewrite):
- `_renderWeaknessRow(w, reviewId, projectId)` — renders each weakness with: status `<select>` (open/addressed/validated/rejected), note `<textarea>` with `onblur`, data attributes for event routing
- `_onWeaknessStatusChange(sel)` — reads `data-pid/rid/wid`; POSTs status-only (null note); no re-render
- `_onWeaknessNoteBlur(ta)` — reads sibling `<select>` for current status; POSTs status + note text
- `_renderDecisionRow(dp, reviewId, projectId)` — renders each decision point with status `<select>`
- `_onDecisionStatusChange(sel)` — reads `data-pid/rid/did`; POSTs status; no re-render
- `_renderProvenanceLine(r)` — lightweight provenance from `r.persona`, `r.included_files.length`, `r.categories[]`; no extra API call; returns `''` when no data available
- `renderReview()` — now renders **all** weaknesses (not just open, so any can be updated), all decision points, and provenance above finding blocks
- Three event handlers exported from IIFE so inline `onclick`/`onblur` in injected HTML can reach them via `DetailPanel.*`

**Test coverage added** (`tests/test_v2_phase1_and_phase2.py`):
- 50 tests covering Phase 1 (6), Phase 2.1 API (7), Phase 2.1 DetailPanel weakness (11), Phase 2.2 decision (7), Phase 2.3 provenance (6), regression (13)
- All 50 pass; 314 static-analysis tests pass with no regressions

**Sequence flows added** (`docs/architecture/sequence_flows.md`):
- Sequence 10: Phase 1 — V2 connects to live backend
- Sequence 11: Phase 2 — weakness status + note update from drawer
- Sequence 12: Phase 2 — decision point status update from drawer
- Sequence 13: Phase 2 — provenance line render (no extra API call)

---

#### Phase 3 — Review Iteration Route + UI
*Closes GAP-2 (partial) and GAP-4.*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 3.1 | Add `POST .../iterate` route | `server.py`, `handlers/review.py` | New route: validates `previous_review_id` present; delegates to `svc.run_persona_review()` with `previous_review_id`; identical to `/api/review` but semantically explicit |
| 3.2 | Add `iterateReview()` to API layer | `static/v2/js/api.js` | `POST /api/projects/{pid}/hierarchy/reviews/{rid}/iterate` |
| 3.3 | Iteration trigger in DetailPanel | `ui/v2/components/DetailPanel.js` | "Iterate from this review" button in review detail; opens modal with persona selector + optional custom prompt; calls `API.iterateReview()`; on success refreshes hierarchy |

---

#### Phase 4 — Reconciliation Route + UI
*Closes GAP-2 (partial) and GAP-5.*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 4.1 | Add `POST .../reconcile` route | `server.py`, `handlers/hierarchy.py`, `services/hierarchy.py` | Body: `{ anchor_review_id, supplemental_review_ids[], ai_backend }`. Load reviews from store, call `synthesize_reviews()`, return `ReconciliationResult` |
| 4.2 | Add `reconcileReviews()` to API layer | `static/v2/js/api.js` | `POST /api/projects/{pid}/hierarchy/reconcile` |
| 4.3 | Reconciliation panel component | `ui/v2/components/ReconciliationPanel.js` | Multi-select of reviews (anchor + supplementals) from current version; trigger button; result view showing: reconciled findings by category, conflicts, reconciliation notes; provenance attribution per item |
| 4.4 | Wire panel into dashboard | `static/v2/js/dashboard.js`, `static/v2/dashboard_v2.html` | Add "Reconcile" action to version detail; render `ReconciliationPanel` in drawer or modal |

---

#### Phase 5 — Coverage Map Route + UI
*Closes GAP-2 (partial) and GAP-8. Depends on Phase 4 (uses ReconciliationResult).*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 5.1 | Add `POST .../proposal/coverage` route | `server.py`, `handlers/proposal.py`, `services/proposal.py` | Body: `{ reconciliation_result, scope_themes[] }`. Calls `compute_proposal_coverage()`. Returns `ProposalCoverage` |
| 5.2 | Add `fetchProposalCoverage()` to API layer | `static/v2/js/api.js` | `POST /api/projects/{pid}/proposal/coverage` |
| 5.3 | CoverageMap component | `ui/v2/components/CoverageMap.js` | Six-domain grid: domain label, status badge (Addressed / Partial / Not Yet Addressed), gap_notes; matched_themes as chips |

---

#### Phase 6 — Proposal Data Pack Route + UI
*Closes GAP-2 (partial) and GAP-6. Depends on Phases 4–5.*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 6.1 | Add `POST .../proposal/proposal-data-pack` route | `server.py`, `handlers/proposal.py`, `services/proposal.py` | Body: `{ version_id, anchor_review_id, supplemental_review_ids[], ai_backend, force }`. Orchestrates: load reviews → synthesize → coverage → generate doc → review pass → forward guidance. Returns assembled pack |
| 6.2 | Add `generateProposalDataPack()` to API layer | `static/v2/js/api.js` | `POST /api/projects/{pid}/proposal/proposal-data-pack` |
| 6.3 | ProposalWorkbench component | `ui/v2/components/ProposalWorkbench.js` | Step flow: (1) version + review selection, (2) reconcile, (3) generate pack; output sections: executive position, coverage map, decisions, risks, blockers, next actions; all with lightweight provenance |
| 6.4 | Wire into dashboard | `static/v2/js/dashboard.js`, `static/v2/dashboard_v2.html` | "Build Proposal Pack" CTA on version detail; renders `ProposalWorkbench` in a full-panel mode |

---

#### Phase 7 — Proposal Review Pass + Forward Guidance Routes + Display
*Closes GAP-2 (partial), GAP-7. Can be incorporated into Phase 6 output or surfaced standalone.*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 7.1 | Add `POST .../proposal/review-pass` route | `server.py`, `handlers/proposal.py`, `services/proposal.py` | Body: `{ proposal_doc_id or inline doc }`. Calls `_run_proposal_review_pass()`. Returns `ProposalReviewPass` |
| 7.2 | Add `POST .../proposal/forward-guidance` route | `server.py`, `handlers/proposal.py`, `services/proposal.py` | Body: `{ review_pass, decision_summary, conflicts, coverage, scope }`. Calls `_run_forward_guidance()`. Returns `ForwardGuidance` |
| 7.3 | ForwardGuidance display | `ui/v2/components/ProposalWorkbench.js` or `DetailPanel.js` | Render grounded next actions list; each item shows: action text, priority, domain, source (open decision / coverage gap / conflict) |

---

#### Phase 8 — Provenance Endpoint + Full Provenance Chips
*Closes GAP-2 (partial) and GAP-9. Builds on Phase 2.3 which adds lightweight inline provenance.*

| # | Item | File(s) | Work |
|---|------|---------|------|
| 8.1 | Add `GET .../hierarchy/reviews/{rid}/provenance` route | `server.py`, `handlers/hierarchy.py`, `services/hierarchy.py` | Returns: `{ review_id, persona, included_files[], categories[], prompt_used, artifact_refs[] }` assembled from `Review` fields |
| 8.2 | Add `fetchReviewProvenance()` to API layer | `static/v2/js/api.js` | `GET /api/projects/{pid}/hierarchy/reviews/{rid}/provenance` |
| 8.3 | Provenance chips in DetailPanel | `ui/v2/components/DetailPanel.js` | Per-finding chip showing artifact name / category; loaded async on drawer open; follows spec §9.3 pattern (lightweight chips, not full citations) |

---

### 17.5 Files Affected Per Phase

| Phase | New Files | Modified Files |
|-------|-----------|----------------|
| 1 ✅ | — | `static/v2/dashboard_v2.html` |
| 2 ✅ | `tests/test_v2_phase1_and_phase2.py` | `ui/v2/components/DetailPanel.js`, `static/v2/js/api.js`, `docs/architecture/sequence_flows.md`, `docs/architecture/review_proposal_workbench_end_to_end.md` |
| 3 | — | `server.py`, `handlers/review.py`, `static/v2/js/api.js`, `ui/v2/components/DetailPanel.js` |
| 4 | `ui/v2/components/ReconciliationPanel.js` | `server.py`, `handlers/hierarchy.py`, `services/hierarchy.py`, `static/v2/js/api.js`, `static/v2/js/dashboard.js`, `static/v2/dashboard_v2.html` |
| 5 | `ui/v2/components/CoverageMap.js` | `server.py`, `handlers/proposal.py`, `services/proposal.py`, `static/v2/js/api.js` |
| 6 | `ui/v2/components/ProposalWorkbench.js` | `server.py`, `handlers/proposal.py`, `services/proposal.py`, `static/v2/js/api.js`, `static/v2/js/dashboard.js`, `static/v2/dashboard_v2.html` |
| 7 | — | `server.py`, `handlers/proposal.py`, `services/proposal.py`, `static/v2/js/api.js`, `ui/v2/components/ProposalWorkbench.js` |
| 8 | — | `server.py`, `handlers/hierarchy.py`, `services/hierarchy.py`, `static/v2/js/api.js`, `ui/v2/components/DetailPanel.js` |

---

### 17.6 Constraints (Unchanged)

- v1 code (`static/index.html`, v1 services) must not be modified
- All new backend work adds routes and handlers only — no changes to existing data models or service signatures
- Single-container Docker deployment: no new services, no new runtime dependencies
- Offline-first: `files_only` path must remain fully functional for every new feature; AI path is an enhancement, not a dependency
- Processors (`review_synthesizer.py`, `proposal_generator.py`) are complete — new work wires them to routes and UI, it does not rewrite them

---

### 17.7 Definition of Done — Per Phase

| Phase | Done When |
|-------|-----------|
| 1 ✅ | v2 loads real project list; version/review selection fetches live metrics; drawer shows real review data |
| 2 ✅ | Weakness status and note can be saved from v2 drawer; decision points render with status control; provenance line shown above findings |
| 3 | "Iterate" button creates a new review linked to prior review; new review appears in accordion; `previous_review_id` is set |
| 4 | Reconciliation panel renders reconciled findings + conflicts for two or more selected reviews from the same version |
| 5 | Coverage map renders six-domain grid with correct Addressed / Partial / Not Yet Addressed status after reconciliation |
| 6 | Proposal data pack generates end-to-end from version selection through to displayed output sections |
| 7 | Review pass domain critique and forward guidance items display in proposal output panel |
| 8 | Per-finding provenance chips appear in DetailPanel showing artifact name and category |
