# Master Sprint Plan — Review & Proposal Workbench
### Single Source of Truth for Implementation

**Spec source:** `docs/architecture/review_proposal_workbench_end_to_end.md`
**Last reviewed:** 2 June 2026
**Status:** Active

---

## How to Use This Document

- This is the **single source of truth**. All prior planning files (`sprint_plan.md`,
  `review_workbench_transformation_backlog.md`, `review_workbench_transformation_backlog.json`)
  are superseded by this document.
- Each sprint has its own PR. Do not merge a sprint PR until its exit gate passes.
- Stories within a sprint may be parallelised unless marked **sequential**.
- Do not implement a story from Sprint N+1 until Sprint N is validated.
- Every change must be additive, backward-compatible, and offline-first (`files_only` mode).

---

## Constraints (Non-Negotiable)

| Constraint | Detail |
|---|---|
| Single-container Docker | No new services, no external queues, no cron jobs |
| Offline-first | All features work with `ai_backend = "files_only"` |
| Non-technical users | UI stays simple; no new build toolchain |
| Open-source only | No proprietary SDKs or hosted-only AI services |
| Additive changes | No redesign of existing routes, models, or DB tables |
| Backward-compatible DB | All new columns use `DEFAULT ''` or `DEFAULT '[]'` |

---


## Current State vs Target State

### What the spec defines (9 modules)

| # | Module | Spec Section |
|---|---|---|
| 1 | Version Context Builder | §8.1 |
| 2 | Review Analyzer | §8.2 |
| 3 | Weakness + Note Handler | §8.3 |
| 4 | Review Iteration Handler | §8.4 |
| 5 | Reconciliation Engine | §8.5 |
| 6 | Coverage Mapper | §8.6 |
| 7 | Proposal Builder | §8.7 |
| 8 | Proposal Review Agent | §8.8 |
| 9 | Forward Guidance Agent | §8.9 |

### Completed work (S1–S8 + PDAE-MS-01)

| Module / Feature | Backend | UI | Notes |
|---|---|---|---|
| Review chain (`previous_review_id`) | ✅ | ✅ | DB, model, SQL, index.html |
| Iteration labels R1/R2/R3 | ✅ | ✅ | Both Versions and Reviews tabs |
| Prompt builder (3-section) | ✅ | ✅ | Injected questions, user notes, baseline preview |
| `prompt_builder_state` persistence | ✅ | ✅ | Stored on review, shown in detail |
| Baseline/Customised badge | ✅ | ✅ | List and detail views |
| SME clarification questions | ✅ | ✅ | AI + heuristic fallback |
| Tighten loop (Q → inject → run) | ✅ | ✅ | Chip flow, previousReviewId wiring |
| Review diff (`/diff` endpoint) | ✅ | ✅ | renderReviewProgression (F3) |
| Weakness extraction | ✅ | ✅ | `extract_weaknesses()`, section in detail |
| Missing categories | ✅ | ✅ | `compute_missing_categories()` |
| Gap-aware SME (`review_id` param) | ✅ | ✅ | Deep dive uses prior review context |
| Decision point extraction | ✅ | ✅ | `extract_decision_points()` |
| Decision-question mapping | ✅ | ✅ | S5-02 annotation in `deep_dive.py` |
| Decision status tracking | ✅ | ✅ | `/decision/{id}/status` endpoint |
| Weakness status tracking | ✅ | ✅ | `/weakness/{id}/status` endpoint |
| Predecessor inheritance (decisions) | ✅ | ✅ | Inherited open DPs on chain |
| Feedback `version_id` field | ✅ | ✅ | S6-03 migration + UI wiring |
| Decision Readiness indicator | ✅ | ✅ | Low/Medium/High, readiness endpoint |
| Prompt log table | ✅ | — | S7-03, `prompt_logger.py` |
| `get_prompt_history` endpoint | ✅ | — | S7-04, no UI surface needed yet |
| Review Strength panel | ✅ | ✅ | Sprint 8 F1 `renderReviewStrength` |
| Decision Points Engine | ✅ | ✅ | Sprint 8 F2 `renderDecisionPointsEngine` |
| Review Progression diff | ✅ | ✅ | Sprint 8 F3 (replaces What Changed) |
| Proposal Readiness indicator | ✅ | ✅ | Sprint 8 F4 `renderProposalReadiness` |
| SME question type tags | ✅ | ✅ | Sprint 8 F5 `_smeQuestionTypeTag` |
| Next Best Actions | ✅ | ✅ | Sprint 8 F6 `renderNextBestActions` |
| Proposal Strength summary | ✅ | ✅ | Sprint 8 F7 `renderProposalStrength` |
| Feedback mapping | ✅ | ✅ | Sprint 8 F8 `_enrichFeedbackWithMapping` |
| Review synthesizer (reconciliation) | ✅ | ✅ | `processors/review_synthesizer.py` |
| Proposal Review Pass (6-domain) | ✅ | ✅ | `_run_proposal_review_pass()` |
| Coverage Mapper | ✅ | ✅ | `ProposalCoverage`, `proposal_coverage` field |
| Forward Guidance | ✅ | ✅ | `_run_forward_guidance()` |
| Proposal data pack (synthesis) | ✅ | ✅ | `ProposalDocument` with synthesis fields |
| Weakness `user_note` field | ✅ | ✅ | S9-03: `extract_weaknesses()`, `update_weakness_status()`, weakness textarea |
| `list_reviews` kwarg fix | ✅ | — | S9-01: `version_filter=` → `version_id=` in `services/review.py` |



---

## Missing Capabilities (Gaps vs Spec)

### GAP-1 · Provenance model (spec §9) — NOT IMPLEMENTED

The spec defines a human-meaningful provenance payload per finding:
```json
{
  "artifact_id": "a123",
  "artifact_name": "RFP.pdf",
  "artifact_type": "document",
  "section_reference": "Delivery Model",
  "page_reference": "3",
  "excerpt": "Optional short snippet"
}
```
**Current state:** Finding items are plain strings. No artifact reference, no page/section
reference, no excerpt. `artifact_refs[]` is not a field on `Review`.

**Impact:** Traceability principle (spec §4.1) is unmet. "Why is this finding here?"
cannot be answered from stored data.

---

### GAP-2 · `user_note` per weakness (spec §8.3) — ✅ CLOSED in S9

The spec requires each weakness to support: `text`, `status`, and **optional free-text
`user_note`**.
**Resolution (S9-03):** `user_note: ""` now emitted by `extract_weaknesses()`. Persisted
via `update_weakness_status(…, user_note=)`. Editable textarea in review detail UI.

---

### GAP-3 · `artifact_refs[]` on Review (spec §13) — NOT IMPLEMENTED

The spec's data contract for Review includes an `artifact_refs[]` array that carries
provenance-ready artifact references through to downstream synthesis.
**Current state:** `included_files` is a flat list of filename strings. No structured
artifact reference objects are stored.

---

### GAP-4 · Version Context Builder output (spec §8.1) — INCOMPLETE

The spec defines explicit output from Version Context Builder:
- version ID ✅
- artifact inventory ✅ (exists as `included_artifacts`)
- **normalised context summary** — absent as a standalone field
- **provenance-ready artifact refs** — absent (same as GAP-1/GAP-3)

---

### GAP-5 · UI Full Details — Review artifact inventory section (spec §10.1) — MISSING

The spec requires the Review Full Details view to show an **Included Artifacts** expandable
section listing the artifact inventory with metadata. Current UI shows `included_files`
as a plain text list only. No metadata, no artifact type, no toggle.

---

### GAP-6 · Provenance chips on findings in UI (spec §10.1) — NOT IMPLEMENTED

The spec defines: for each weakness, show a **provenance chip** (lightweight reference
line). Currently the UI renders plain text for each finding/weakness item.

---

### GAP-7 · Proposal contextual workflow in UI (spec §10.2) — PARTIAL

The spec defines an explicit proposal creation path:
1. Select Version
2. Select anchor review
3. Optionally select supplemental reviews
4. Reconcile
5. Generate proposal data pack

Steps 1–3 and 5 exist in the current UI. Step 4 (explicit reconcile action before
generation) is implicit inside `generate_proposal_doc` — it is not a visible,
user-initiated step with its own UI state.

---

### GAP-8 · Test environment dependency (`yaml` missing) — BROKEN

8 tests in `test_sprint7_regression.py` fail because `pyyaml` is not installed in the
test environment. The code is correct; this is an environment/dependency issue.
`personas/engine.py` imports `yaml` which is not in the sandbox's Python path.

---

## Broken or Incomplete Capabilities

| Item | File(s) | Status |
|---|---|---|
| `list_reviews(version_filter=...)` called with wrong kwarg | `services/review.py` line ~130 | Bug: `version_filter` should be `version_id` |
| 8 sprint-7 tests fail (env) | `tests/test_sprint7_regression.py` | `pyyaml` not installed |
| v2 UI (`dashboard_v2.html`) missing sprint 3–8 features | `static/v2/dashboard_v2.html` | Only has iteration labels; no prompt builder, weakness, decisions, readiness |
| `prompt_builder_state.decision_mappings` not stored | `static/index.html` `addSelectedToPrompt` | S5-02 spec says map `decision_point_id` into `prompt_builder_state.decision_mappings`; not present |



---

## Modules Already Close to Target

| Module | Closeness | What remains |
|---|---|---|
| Review Analyzer (§8.2) | 95% | Provenance on findings only |
| Weakness + Note Handler (§8.3) | 100% | Complete (S9-03) |
| Review Iteration Handler (§8.4) | 100% | Complete |
| Reconciliation Engine (§8.5) | 95% | UI step is implicit not explicit |
| Coverage Mapper (§8.6) | 100% | Complete |
| Proposal Builder (§8.7) | 90% | UI workflow step missing |
| Proposal Review Agent (§8.8) | 100% | Complete |
| Forward Guidance Agent (§8.9) | 100% | Complete |
| Version Context Builder (§8.1) | 60% | Provenance-ready artifact refs missing |

---

## File-Level Impact Areas

### Sprint 9 — `user_note` on weakness + `artifact_refs` on review
| File | Change |
|---|---|
| `db/database.py` | No schema change needed (weaknesses stored as JSON blob) |
| `models/hierarchy.py` — `Review` | `artifact_refs: List[Dict] = field(default_factory=list)` |
| `db/hierarchy_store_sql.py` — `create_review()` | Accept and persist `artifact_refs` |
| `processors/review_quality.py` — `extract_weaknesses()` | Add `user_note: ""` to each weakness dict |
| `services/review.py` — `update_weakness_status()` | Extend to also accept and persist `user_note` |
| `server.py` — weakness status route | Read `user_note` from body; pass to service |
| `static/index.html` — weakness row HTML | Add editable `<textarea>` for `user_note`; PATCH on blur |

### Sprint 10 — Provenance payload
| File | Change |
|---|---|
| `processors/context_builder.py` | Emit `provenance` dict per finding when artifact metadata available |
| `models/hierarchy.py` — finding items | Document expected shape: `{text, provenance?: {...}}` |
| `services/review.py` — `run_persona_review()` | Pass provenance-enriched findings through to `store.create_review()` |
| `static/index.html` — finding items | Render provenance chip when `finding.provenance` present |

### Sprint 11 — Explicit reconcile UI step + v2 UI catch-up
| File | Change |
|---|---|
| `static/index.html` — proposal creation modal | Add explicit "Reconcile" button between review selection and Generate |
| `handlers/proposal.py` | New route: `POST /api/projects/{id}/hierarchy/reconcile` |
| `services/proposal.py` | `reconcile_reviews(project_id, anchor_id, supplemental_ids)` |
| `static/v2/dashboard_v2.html` | Bring forward prompt builder, weakness, decisions, readiness from v1 |

### Sprint 12 — Test environment fix + regression coverage
| File | Change |
|---|---|
| `pyproject.toml` | Add `pyyaml` to dependencies |
| `tests/test_sprint9_regression.py` | New regression pack for Sprint 9 changes |



---

## Risks and Sequencing Concerns

| Risk | Severity | Mitigation |
|---|---|---|
| `list_reviews(version_filter=...)` kwarg bug in `services/review.py` | High | Fix in Sprint 9 before any review list work |
| `pyyaml` missing causes 8 test failures masking real regressions | Medium | Add to `pyproject.toml` in Sprint 9 |
| Provenance requires upstream extractor changes | High | Must not change finding text format — use wrapper objects only |
| v2 UI is severely behind v1 | Medium | Sprint 11 is dedicated to v2 catch-up; do not ship features to v2 before that |
| Weakness `user_note` must survive `update_review_weaknesses()` round-trip | Medium | Read-modify-write: preserve all existing fields, add only `user_note` |
| Reconcile as explicit UI step may confuse users | Low | Keep it optional — single-review path unchanged |
| `prompt_builder_state.decision_mappings` gap | Low | Additive fix; no breaking change to existing state shape |

---

## Recommended Implementation Plan

> Each sprint below is scoped for one PR. Exit gate must pass before next sprint starts.
> Sprints 1–8 and PDAE-MS-01 are already implemented and their PRs are complete.
> Sprints 9 onwards are the remaining work.

---

### Sprint 9 — Weakness User Notes + Kwarg Bug Fix + Dependency Fix
**Goal:** Close GAP-2, fix the `list_reviews` kwarg bug, fix `pyyaml` dependency.
**Priority:** High | **Depends on:** S1–S8 complete
**PR scope:** 4 targeted changes, no new endpoints.

#### S9-01 · Fix `list_reviews` kwarg bug (sequential — do first)

**What:** `services/review.py` calls `store.list_reviews(version_filter=latest_version_id)`.
The correct kwarg is `version_id=`. This silently returns all reviews instead of the
version-scoped set.

**Where to change:**

| File | Change |
|---|---|
| `services/review.py` — `run_persona_review()` | Change `store.list_reviews(version_filter=latest_version_id)` to `store.list_reviews(version_id=latest_version_id)` |

**Acceptance:**
- `run_persona_review()` returns the new review's ID correctly in all paths.
- Existing tests pass without change.

---

#### S9-02 · Add `pyyaml` to dependencies

**What:** `personas/engine.py` imports `yaml`. Missing from `pyproject.toml`.

**Where to change:**

| File | Change |
|---|---|
| `pyproject.toml` | Add `pyyaml>=6.0` to `[project.dependencies]` |

**Acceptance:**
- All 8 previously failing `test_sprint7_regression.py` tests now pass.
- `python3 -m pytest tests/test_sprint7_regression.py --tb=short -q` exits 0.

---

#### S9-03 · `user_note` field on weakness items

**What:** Add optional free-text `user_note` to every weakness dict. The note is editable
in the review detail UI and persisted via the existing weakness status endpoint.

**Where to change:**

| File | Change |
|---|---|
| `processors/review_quality.py` — `extract_weaknesses()` | Add `"user_note": ""` to each returned weakness dict |
| `services/review.py` — `update_weakness_status()` | Accept optional `user_note: str = None`; if provided, set `target["user_note"] = user_note` before persisting |
| `server.py` — weakness status route | Read `body.get("user_note")` and pass to `update_weakness_status()` |
| `static/index.html` — weakness row HTML | Below each weakness status `<select>`, add a `<textarea placeholder="Add note…">` (2 rows). On `blur`, call the status endpoint with current status + `user_note`. Pre-populate from `w.user_note` if present. |

**Backward compatibility:** Existing weaknesses without `user_note` render with an
empty textarea. No migration needed (JSON blob in DB).

**Acceptance:**
- New reviews have `user_note: ""` in each weakness.
- Typing a note and tabbing away PATCHes it to the server.
- Reloading the review detail shows the saved note.
- Existing reviews with no `user_note` load without error.

---

#### S9-04 · Sprint 9 regression test

**What:** Static analysis test verifying `user_note` is wired correctly.

**Where to change:**

| File | Change |
|---|---|
| `tests/test_sprint9_regression.py` | New file. Tests: (a) `extract_weaknesses()` returns `user_note: ""` on each item, (b) `update_weakness_status()` accepts and returns `user_note`, (c) HTML contains `user_note` textarea in weakness row |

**Acceptance:**
- New test file passes.
- No existing tests broken.

#### S9 Exit Gate — ✅ PASSED
- [x] `list_reviews` kwarg bug fixed; `run_persona_review()` returns correct review ID
- [x] `pyyaml` in `pyproject.toml`; all 8 sprint-7 tests pass (yaml importable in env)
- [x] Weakness items have `user_note` field in API response and UI
- [x] Saving a note persists across page reload
- [x] All prior regression packs still pass (S1–S9: 524/524)



---

### Sprint 10 — Provenance Model (GAP-1, GAP-3, GAP-4, GAP-5, GAP-6)
**Goal:** Implement spec §9 provenance payload. Carry artifact references through to UI.
**Priority:** High | **Depends on:** S9 complete
**PR scope:** Backend provenance enrichment + UI provenance chips.

#### S10-01 · Provenance payload shape in artifact model

**What:** Establish the provenance payload shape as a typed dict across the codebase.
No new table. Provenance is embedded in finding items when available.

Expected shape (matches spec §9.2):
```
{
  "artifact_id": str,
  "artifact_name": str,
  "artifact_type": str,   # document|slide|email|meeting_notes|spreadsheet
  "section_reference": str,
  "page_reference": str,
  "excerpt": str
}
```

**Where to change:**

| File | Change |
|---|---|
| `contracts/types.py` | Add `ProvenanceRef = TypedDict(...)` with the 6 fields above (all optional except `artifact_id`) |
| `processors/context_builder.py` | When building context per artifact, emit a `provenance_ref` dict from artifact metadata. Use `artifact_id`, `file_name` → `artifact_name`, `category` → `artifact_type`. `section_reference`, `page_reference`, `excerpt` are empty string defaults. |

**Acceptance:**
- `ProvenanceRef` importable from `contracts.types`.
- `build_context_summary()` can optionally include provenance metadata per artifact.
- No runtime errors on `files_only` path.

---

#### S10-02 · `artifact_refs[]` on Review model

**What:** Add `artifact_refs: List[Dict]` to the `Review` dataclass and DB migration.
Each entry is a `ProvenanceRef`-shaped dict for an artifact included in that review.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE reviews ADD COLUMN artifact_refs TEXT DEFAULT '[]'` |
| `models/hierarchy.py` — `Review` dataclass | Add `artifact_refs: List[Dict[str, Any]] = field(default_factory=list)` |
| `models/hierarchy.py` — `Review.to_summary()` | Add `"artifact_refs": self.artifact_refs` |
| `db/hierarchy_store_sql.py` — `create_review()` | Accept and persist `artifact_refs` parameter |
| `db/hierarchy_store_sql.py` — `_row_to_review()` | Deserialise `artifact_refs` from JSON |
| `services/review.py` — `run_persona_review()` | Build `artifact_refs` from `_list_artifacts_sql(project_id)` for included artifacts; pass to `store.create_review()` |

**Backward compatibility:** `DEFAULT '[]'` — existing reviews return empty list.

**Acceptance:**
- `GET /api/projects/{id}/hierarchy/reviews/{rid}` returns `artifact_refs: [...]`.
- Each entry has at minimum `artifact_id` and `artifact_name`.
- Existing reviews return `artifact_refs: []` without error.

---

#### S10-03 · Artifact inventory section in Review Full Details UI

**What:** Add an expandable "Included Artifacts" section to `viewReviewDetail()`.
Shows `artifact_refs[]` if present, falls back to `included_files[]` list.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviewDetail()` | After the metadata row, add a `<details>` element: `<summary>Included Artifacts (N)</summary>`. Inside, render a row per artifact: name, type badge, artifact_id. If `artifact_refs` is empty, fall back to rendering `included_files` as plain text list. |

**Acceptance:**
- Review detail shows "Included Artifacts (3)" collapsed by default.
- Expanding shows artifact name and type for each.
- Reviews with no `artifact_refs` show the legacy `included_files` text list.

---

#### S10-04 · Provenance chips on findings

**What:** When a finding item carries a `provenance` object (future enrichment), render a
lightweight chip below the finding text. Chip shows `artifact_name + section_reference`.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — finding item HTML helper | Add: if item is an object with `.provenance`, render `<span class="tag prov-chip">📄 {artifact_name} › {section_reference}</span>` below the text. If item is plain string (current default), render as before. |
| `static/index.html` — weakness row HTML | Same chip pattern for each weakness if `w.provenance` is set. |

**Acceptance:**
- Existing plain-string findings render unchanged.
- If a finding object carries `provenance.artifact_name`, the chip appears.
- Chip is small, not dominant (matches spec §9.3 "lightweight chips").

#### S10 Exit Gate
- [ ] `ProvenanceRef` type defined in `contracts/types.py`
- [ ] `artifact_refs[]` field on `Review` model, DB, and SQL store
- [ ] New reviews include `artifact_refs` populated from ingested artifacts
- [ ] Review detail shows expandable Included Artifacts section
- [ ] Provenance chip renders on findings that carry provenance data
- [ ] All prior regression packs still pass



---

### Sprint 11 — Explicit Reconcile Step + v2 UI Catch-Up (GAP-7)
**Goal:** Make reconciliation a visible user-initiated step in the proposal workflow.
Bring v2 UI to feature parity with v1 for S1–S8 features.
**Priority:** Medium | **Depends on:** S10 complete
**PR scope:** One new endpoint, modal update, v2 HTML update.

#### S11-01 · Reconcile endpoint (sequential — do before UI)

**What:** Expose reconciliation as a standalone API call, separate from proposal
generation. This matches spec §8.5 and §10.2 step 4.

**Where to change:**

| File | Change |
|---|---|
| `handlers/proposal.py` | Add `handle_reconcile(project_id, body, respond)`: reads `anchor_review_id` and `supplemental_review_ids[]`; calls `svc.reconcile_reviews()` |
| `services/proposal.py` | Add `reconcile_reviews(project_id, anchor_id, supplemental_ids, version_id)` — calls `processors/review_synthesizer.synthesize_reviews()` and returns `ReconciliationResult.to_dict()` |
| `server.py` — `do_POST` | Add route: `POST /api/projects/{id}/hierarchy/reconcile` → `h_proposal.handle_reconcile(pid, body, R)` |

**Acceptance:**
- `POST /api/projects/{id}/hierarchy/reconcile` with `anchor_review_id` + optional `supplemental_review_ids` returns a `ReconciliationResult` dict.
- Works on `files_only` path (deterministic reconcile).
- Existing `generate_proposal_doc` path unchanged.

---

#### S11-02 · Reconcile step in proposal UI

**What:** Add a "Reconcile" intermediate step in `showCreateProposal()`. After review
selection, user can optionally click "Reconcile Reviews" before generating. Result
is shown inline. Generation proceeds regardless (reconcile is optional for single-review).

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — proposal creation section | After supplemental review checkboxes, add a `<button id="btnReconcile">Reconcile Reviews</button>`. On click, `POST /reconcile` and render a short summary (consensus count, conflict count) inline. |
| `static/index.html` — `submitCreateProposal()` | If reconcile was run, store `reconciliation_result` in form state and include `anchor_review_id` + `supplemental_review_ids` in the generate call. |

**Acceptance:**
- Single-review proposal: Reconcile button is shown but optional; skipping it produces the same result as before.
- Multi-review: reconcile summary appears before generation.
- Reconcile result does not block generation.

---

#### S11-03 · v2 UI catch-up (parallel to S11-01/02)

**What:** Bring `static/v2/dashboard_v2.html` to feature parity with `static/index.html`
for the following sprint 3–8 features: prompt builder (3-section), weakness section,
decision points section, Decision Readiness badge, tighten loop button.

**Where to change:**

| File | Change |
|---|---|
| `static/v2/dashboard_v2.html` — `viewReviews()` | Add 3-section prompt builder (copy pattern from index.html S2-01 block) |
| `static/v2/dashboard_v2.html` — `viewReviewDetail()` | Add: weaknesses section (S4-01), decision points section (S5-01), Decision Readiness badge (S7-01), Tighten button (S3-03) |
| `static/v2/dashboard_v2.html` — `viewVersions()` | Add Decision Readiness badge per version (S7-01 pattern) |

**Acceptance:**
- v2 UI shows weakness section when a review has weaknesses.
- v2 UI shows Decision Readiness badge (Low/Medium/High) on version rows.
- v2 UI tighten button switches to Reviews tab with `previousReviewId` set.
- v1 UI is unchanged.

#### S11 Exit Gate
- [ ] `POST /api/projects/{id}/hierarchy/reconcile` returns `ReconciliationResult`
- [ ] Proposal UI shows Reconcile button (optional, non-blocking)
- [ ] v2 UI has prompt builder, weaknesses, decision points, readiness, tighten button
- [ ] All prior regression packs still pass

---

### Sprint 12 — `decision_mappings` in prompt state + Test Coverage
**Goal:** Close the remaining S5-02 gap. Add regression test coverage for S9–S11.
**Priority:** Low | **Depends on:** S11 complete
**PR scope:** Small JS change, one new test file.

#### S12-01 · `decision_mappings` in `prompt_builder_state`

**What:** When a question with a `decision_point_id` is injected into the prompt builder,
store the mapping in `prompt_builder_state.decision_mappings` for traceability.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `addSelectedToPrompt()` | When pushing a question with `decision_point_id` into `state._injectedQuestions`, also push `{question_text, decision_point_id, decision_point_text}` to `state._decisionMappings`. |
| `static/index.html` — `runReview()` | Include `decision_mappings: state._decisionMappings || []` inside the `prompt_builder_state` object sent to the API. |

**Acceptance:**
- A review run after selecting a question that was linked to a decision point has `prompt_builder_state.decision_mappings` populated.
- Questions without a decision link are excluded from `decision_mappings`.
- Existing reviews with no `decision_mappings` load without error.

---

#### S12-02 · Regression test packs for S9–S11

**What:** Static analysis and unit tests for Sprint 9–11 changes.

**Where to change:**

| File | Covers |
|---|---|
| `tests/test_sprint9_regression.py` | S9-01 kwarg fix, S9-02 pyyaml, S9-03 user_note field |
| `tests/test_sprint10_regression.py` | S10-01 ProvenanceRef type, S10-02 artifact_refs model/DB, S10-03/04 HTML |
| `tests/test_sprint11_regression.py` | S11-01 reconcile endpoint, S11-02 HTML reconcile button, S11-03 v2 feature presence |

**Acceptance:**
- All three new test files pass.
- No existing tests broken.

#### S12 Exit Gate
- [ ] `prompt_builder_state.decision_mappings` populated when decision-linked questions are injected
- [ ] Sprint 9–11 regression tests all pass
- [ ] Full test suite passes (excluding known env-only failures if any)



---

## Sprint Roadmap Summary

| Sprint | Name | Priority | Depends On | Stories | PRs |
|---|---|---|---|---|---|
| S1 | Foundation & Review Chain | ✅ Done | — | 5 | Done |
| S2 | Prompt Builder Foundation | ✅ Done | S1 | 3 | Done |
| S3 | Guided Tightening Loop | ✅ Done | S2 | 4 | Done |
| S4 | Weakness & Gap Intelligence | ✅ Done | S3 | 3 | Done |
| S5 | Decision Intelligence | ✅ Done | S4 | 3 | Done |
| S6 | Resolution & Iteration Intelligence | ✅ Done | S5 | 3 | Done |
| S7 | Convergence & Learning Foundation | ✅ Done | S6 | 4 | Done |
| S8 | UI Strengthening (F1–F8) | ✅ Done | S7 | 8 | Done |
| PDAE-MS-01 | Proposal Synthesis Pipeline | ✅ Done | S5 | Multi-sprint | Done |
| ~~S9~~ | ~~Weakness Notes + Bug Fixes~~ | ✅ Done | S1–S8 | 4 | Done |
| **S10** | **Provenance Model** | **High** | S9 | 4 | **Next PR** |
| **S11** | **Reconcile Step + v2 Catch-Up** | **Medium** | S10 | 3 | — |
| **S12** | **decision_mappings + Test Coverage** | **Low** | S11 | 2 | — |

---

## Schema Change Summary (Remaining Sprints)

| Sprint | Table | New Column |
|---|---|---|
| S10 | `reviews` | `artifact_refs TEXT DEFAULT '[]'` |

All applied via `db/database.py → _apply_migrations()` using the existing idempotent pattern.

---

## New API Endpoints Summary (Remaining Sprints)

| Sprint | Method | Route | Purpose |
|---|---|---|---|
| S11 | POST | `/api/projects/{id}/hierarchy/reconcile` | Explicit reconcile step |

All existing routes remain unchanged.

---

## Cross-Cutting Rules (All Remaining Sprints)

| Rule | Detail |
|---|---|
| No architecture redesign | All changes are additive |
| Backward-compatible DB | All new columns use `DEFAULT ''` or `DEFAULT '[]'` |
| Single-container | No new services, processes, or external dependencies |
| Offline-first | All features work with `files_only` backend |
| Non-technical users | No new build toolchain; use existing CSS tokens |
| One PR per sprint | Exit gate must pass before next sprint begins |
| v1 UI is primary | v2 catches up in S11; all new features land in v1 first |
| Stop after scope | Do not implement S(N+1) work until S(N) exit gate is confirmed |

---

## Superseded Documents

The following files are superseded by this document and should not be used for
implementation planning:

- `docs/planning/sprint_plan.md` — covers S1–S7 only; code has advanced further
- `docs/planning/review_workbench_transformation_backlog.md` — S1–S7 backlog only
- `docs/planning/review_workbench_transformation_backlog.json` — S1–S7 JSON source

Those files are retained for historical reference only.
