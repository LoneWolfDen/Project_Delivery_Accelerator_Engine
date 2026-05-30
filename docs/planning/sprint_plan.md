# Sprint Implementation Plan
### Review Workbench Transformation — S1 to S7

**Backlog source:** `review_workbench_transformation_backlog.json` (v1.1)
**Ambiguity resolutions:** AR-01 to AR-05 applied throughout

---

## How to Use This Plan

- Execute **one sprint at a time**. Validate before moving to the next.
- Each story lists the exact files to change, the field or function to add/modify,
  and the acceptance signal to verify.
- No story crosses sprint boundaries. Dependencies are strict and linear.
- Stories within a sprint may be parallelised unless noted as sequential.

---

## Codebase Reference

| Layer | Key Files |
|---|---|
| HTTP routing | `server.py` — `AcceleratorHandler.do_GET / do_POST` |
| Orchestration | `project_manager.py` |
| Review engine | `personas/engine.py` |
| Hierarchy model | `models/hierarchy.py`, `db/hierarchy_store_sql.py` |
| Review quality | `processors/review_quality.py` |
| Feedback loop | `processors/presales_feedback.py` |
| Proposal gen | `processors/proposal_generator.py` |
| Database schema | `db/database.py` — `_SCHEMA_SQL` + `_apply_migrations()` |
| Frontend SPA | `static/index.html` — inline JS, `viewReviews()`, `viewVersions()` |



---

## S1 — Foundation and Review Chain Stability

**Goal:** Make reviews version-scoped, explicitly chained, and visible as iterations.
**Priority:** High | **Depends on:** Nothing

---

### S1-01 · Version-scoped review list

**What:** Reviews tab shows only reviews that belong to the currently selected version.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` | Read `state._dashVersion`. If set, filter `versionsWithReviews` to only the matching version before rendering the review history list. |
| `static/index.html` — `viewReviews()` | Update the review count badge to reflect version-scoped count, not global count. |

**No backend change needed.** `GET /api/projects/{id}/hierarchy/reviews?version_id=…` already exists in `server.py` and `models/hierarchy.py → list_reviews(version_id=…)`.

**Acceptance:**
- Select version `v2` in Dashboard scope selector → Reviews tab shows only `v2` reviews.
- No `v1` reviews bleed into the list.
- Count badge reflects the filtered set.

---

### S1-02 · Explicit review chaining

**What:** Add `previous_review_id` field to the `reviews` table and `Review` dataclass so iterations are traceable.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE reviews ADD COLUMN previous_review_id TEXT DEFAULT ''` if column not in `_existing_cols("reviews")`. |
| `models/hierarchy.py` — `Review` dataclass | Add field: `previous_review_id: str = ""` |
| `models/hierarchy.py` — `HierarchyStore.create_review()` | Accept optional `previous_review_id: str = ""` parameter and store it. |
| `db/hierarchy_store_sql.py` — `create_review()` | Accept and persist `previous_review_id` in the `INSERT INTO reviews` statement. |
| `project_manager.py` — `run_persona_review()` | Accept optional `previous_review_id` from the POST body; pass it through to `store.create_review()`. |
| `server.py` — `_handle_review()` | Read `body.get("previous_review_id", "")` and pass to `project_manager.run_persona_review()`. |

**Backward compatibility:** `DEFAULT ''` in migration — existing reviews unaffected.

**Acceptance:**
- POST `/api/review` with `previous_review_id: "r1"` → new review `r2` stores `previous_review_id = "r1"`.
- GET `/api/projects/{id}/hierarchy/reviews/r2` returns `previous_review_id: "r1"`.
- Existing reviews return `previous_review_id: ""`.



---

### S1-03 · Iteration visibility

**What:** Show `R1`, `R2`, `R3` labels on every review card in both Reviews and Versions tabs.

**Where to change:**

| File | Change |
|---|---|
| `db/hierarchy_store_sql.py` — `list_reviews()` | Add `iteration_number` to each returned row: use `ROW_NUMBER() OVER (PARTITION BY version_id ORDER BY created_at ASC)` or a Python counter post-query, whichever is simpler. |
| `models/hierarchy.py` — `Review.to_summary()` | Add `"iteration_number": self.iteration_number` (default `0` when unknown). |
| `static/index.html` — `viewReviews()` review row HTML | Prefix review ID with iteration label: `R${rev.iteration_number || '?'}` as a small badge. |
| `static/index.html` — `viewVersions()` review row HTML | Same badge in version tree review items. |
| `static/index.html` — `viewReviewDetail()` | Show `previous_review_id` link ("Follows: R1") when present. |

**Acceptance:**
- Three reviews on `v1` show `R1`, `R2`, `R3` in both Versions and Reviews tabs.
- Review detail for `R2` shows "Follows: R1" when `previous_review_id` is set.
- New reviews automatically get the next iteration number.

---

### S1-04 · Move Ask SME before next review

**What:** Reposition the Ask SME (Deep Dive) trigger so it is available *before* starting a new review iteration, not only after completion.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` run card | Move the "Ask SME Questions" button to appear **before** the "Run Review" button, not after results are shown. Adjust the workflow guidance text accordingly. |
| `static/index.html` — `runDeepDive()` | Remove any logic that gates deep dive on a completed review existing. Deep dive should work on the current project intelligence regardless of review state. |
| `static/index.html` — review result HTML | Remove any auto-trigger of deep dive at the end of `runReview()`. The two actions are now independent. |

**No backend change.** `POST /api/projects/{id}/deep-dive` already accepts a standalone call.

**Acceptance:**
- User can click "Ask SME Questions" without having run a review first.
- Running a review does not auto-trigger or auto-display SME questions.
- Current review output is not modified by Ask SME.

---

### S1-05 · Demote completeness score (UI-only)

**What:** Move the completeness score badge from its current prominent position to a secondary, smaller element. No logic changes.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` review row HTML | The progress bar + percentage score block is rendered inside each review card. Reduce it: replace the full-width progress bar with a small inline badge (`60%`). Remove the bar element entirely. |
| `static/index.html` — `viewReviewDetail()` | Score badge moves to the metadata row (alongside persona, backend, date) rather than having its own section. |

**No scoring logic change.** `completeness_score` field, `compute_completeness_score()`, and `complete_review()` are untouched.
Score does **not** block Draft or Final actions — confirmed by AR-05.

**Acceptance:**
- Score appears as a small inline badge next to persona/backend info.
- No progress bar dominating the review card.
- "Mark as Draft" and "Mark as Final" buttons remain fully functional.

---

### S1 Exit Gate

Before moving to S2:
- [ ] All reviews display version-scoped in the Reviews tab
- [ ] `previous_review_id` stored and returned by API
- [ ] Iteration labels `R1 / R2 / R3` visible in both tabs
- [ ] Ask SME is accessible before running a review
- [ ] Score is a small badge, not a dominant element



---

## S2 — Prompt Builder Foundation

**Goal:** Replace blank custom prompting with structured prompt assembly.
**Priority:** High | **Depends on:** S1 complete

---

### S2-01 · Prompt builder sections

**What:** Replace the single `<textarea id="customPrompt">` with a structured three-section prompt builder: (1) baseline persona prompt (read-only preview), (2) injected suggested questions (populated by Ask SME), (3) user-added custom notes (free text).

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` run card HTML | Replace `<textarea id="customPrompt">` with a three-section builder component: a collapsed read-only "Baseline Prompt" `<details>`, a list of injected question chips with remove buttons (`<div id="injectedQuestions">`), and a free-text notes field (`<textarea id="userNotes">`). |
| `static/index.html` — `addSelectedToPrompt()` | Instead of appending to `customPrompt` textarea, push selected questions into `state._injectedQuestions[]` array and re-render the injected questions section. |
| `static/index.html` — `runReview()` | Before calling the API, assemble the final prompt: `[injected questions joined by newline] + "\n" + userNotes`. Send as `custom_prompt`. |
| `static/index.html` — new `_getBaselinePrompt(persona)` helper | Call `GET /api/personas` and find the matching persona's `purpose` + `group_name` to populate the baseline preview. |

**No backend change.** The assembled prompt is sent as `custom_prompt` — server already handles it.

**Acceptance:**
- Prompt builder shows three visible sections.
- Selecting SME questions populates the injected questions section, not raw textarea.
- Final assembled prompt sent to API is `[questions]\n[user notes]`.
- Baseline persona prompt is visible (read-only).

---

### S2-02 · Persist prompt builder state

**What:** Store the prompt builder state on each review record so users can inspect what prompt was used.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE reviews ADD COLUMN prompt_builder_state TEXT DEFAULT NULL`. |
| `models/hierarchy.py` — `Review` dataclass | Add field: `prompt_builder_state: Optional[dict] = None` |
| `db/hierarchy_store_sql.py` — `create_review()` | Accept and persist `prompt_builder_state` (JSON) in the INSERT. |
| `project_manager.py` — `run_persona_review()` | Accept `prompt_builder_state: Optional[dict] = None`; pass to `store.create_review()`. |
| `server.py` — `_handle_review()` | Read `body.get("prompt_builder_state")` and pass to `project_manager.run_persona_review()`. |
| `static/index.html` — `runReview()` | Build and send `prompt_builder_state: { injected_questions: [...], user_notes: "..." }` alongside `custom_prompt`. |

**Acceptance:**
- GET `/api/projects/{id}/hierarchy/reviews/{review_id}` returns `prompt_builder_state`.
- Re-opening a review detail shows which questions were injected.
- Old reviews return `prompt_builder_state: null` without error.



---

### S2-03 · Baseline vs customised indicator

**What:** Show a visible label on each review indicating whether it used the baseline prompt only or a customised (tightened) prompt.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` review row HTML | After rendering `prompt_builder_state`, add a badge: if `prompt_builder_state` has any `injected_questions` or non-empty `user_notes` → show `<span class="tag tag-purple">Customised</span>`; else → show `<span class="tag">Baseline</span>`. |
| `static/index.html` — `viewReviewDetail()` | Same badge in the metadata row of review detail view. |

**No backend change.**

**Acceptance:**
- Reviews with injected questions or user notes show "Customised" badge.
- Reviews with empty prompt builder state show "Baseline" badge.
- Badge visible in both review list and review detail.

---

### S2 Exit Gate

Before moving to S3:
- [ ] Prompt builder renders three sections in Reviews tab
- [ ] Ask SME questions populate the injected section, not the textarea
- [ ] `prompt_builder_state` stored and returned by API
- [ ] Baseline / Customised badge visible in list and detail views

---

## S3 — Guided Tightening Loop

**Goal:** Turn Ask SME into a structured mechanism for tightening the next review.
**Priority:** High | **Depends on:** S2 complete

---

### S3-01 · SME question generator

**What:** Change the deep dive output format to return targeted clarification questions tied to specific weaknesses and gaps — not generic advice.

**Where to change:**

| File | Change |
|---|---|
| `personas/deep_dive.py` — `run_deep_dive()` | Update the `files_only` heuristic path to generate questions framed as clarifications ("What is the DR strategy?" not "You should add DR"). Each question must reference the gap or risk it addresses. |
| `personas/deep_dive.py` — AI prompt template | Update the LLM prompt to instruct: "Generate targeted clarification questions only. Each question must be tied to a specific gap, weak assumption, or unresolved area in the findings. Do not give generic advice." |
| `static/index.html` — `runDeepDive()` / `ddGroup()` | Rename the section header from "Deep Dive" to "SME Clarification Questions" in the UI. |

**Acceptance:**
- Ask SME returns questions, not recommendations.
- Each question references its source area (e.g., `[architecture]`, `[risk]`).
- Generic advice phrases ("You should consider...") do not appear.

---

### S3-02 · Question selection flow

**What:** Selected questions flow into the prompt builder's injected questions section (already built in S2-01), not appended to a raw textarea.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `addSelectedToPrompt()` | Update: push selected question texts into `state._injectedQuestions[]` and re-render the prompt builder's injected section. Do **not** modify `userNotes` textarea. |
| `static/index.html` — `_getSelectedDDItems()` | Strip role prefix tags (e.g., `[Solution Architect] `) before storing in `state._injectedQuestions`. |

**No backend change.**

**Acceptance:**
- Selected questions appear as removable chips in the "Injected Questions" section of the prompt builder.
- Deselected questions do not appear.
- `userNotes` textarea is not modified.



---

### S3-03 · Run tightened review

**What:** When running a review after selecting SME questions, the assembled prompt (questions + notes) is sent correctly and the new review is chained to the previous one via `previous_review_id`.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `viewReviews()` run card | Add a hidden input `<input type="hidden" id="previousReviewId">`. When a user selects SME questions after viewing a review, auto-populate this field with that review's ID. |
| `static/index.html` — `runReview()` | Include `previous_review_id: document.getElementById("previousReviewId")?.value || ""` in the POST body. |
| `static/index.html` — review detail "Run tightened review" button | Add a button in `viewReviewDetail()`: "Tighten with SME Questions" — sets `previousReviewId` state and switches to Reviews tab with Ask SME pre-expanded. |

**Backend already handles `previous_review_id`** (implemented in S1-02).

**Acceptance:**
- Running a review after selecting SME questions sends both `custom_prompt` (assembled) and `previous_review_id`.
- New review is chained to the previous one in the hierarchy.
- Prompt builder state is persisted on the new review.

---

### S3-04 · What changed summary

**What:** Show a concise diff between the current review and its predecessor on the review detail page.

**Where to change:**

| File | Change |
|---|---|
| `project_manager.py` — new function `get_review_diff(project_id, review_id)` | Load review by `review_id` and its `previous_review_id`. Compare `findings` dicts: for each category, classify items as `new`, `resolved` (in previous but not current), or `unchanged`. Return structured diff. |
| `server.py` — `do_GET` | Add route: `GET /api/projects/{id}/hierarchy/reviews/{review_id}/diff` → calls `project_manager.get_review_diff()`. Returns `{"new": {...}, "resolved": {...}, "unchanged": {...}}`. |
| `static/index.html` — `viewReviewDetail()` | When `previous_review_id` is set, fetch `/diff` and render a "What Changed" section: green items = new findings, red strikethrough = resolved, grey = unchanged. |

**Acceptance:**
- Review detail for `R2` (which follows `R1`) shows a "What Changed" section.
- Section shows new findings, resolved findings, and unchanged count.
- Reviews without a predecessor do not show the section.
- Diff is tied to `previous_review_id`, not assumed by timestamp proximity.

---

### S3 Exit Gate

Before moving to S4:
- [ ] Ask SME returns questions only, not generic advice
- [ ] Selected questions appear as chips in prompt builder (not textarea)
- [ ] Running a tightened review sends `previous_review_id`
- [ ] Review detail shows "What Changed" diff when predecessor exists



---

## S4 — Weakness and Gap Intelligence

**Goal:** Identify where the current review is weak, unclear, or incomplete.
**Priority:** High | **Depends on:** S3 complete

---

### S4-01 · Weakness extraction

**What:** Add a structured `weaknesses` section to each review, extracted from the findings.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE reviews ADD COLUMN weaknesses TEXT DEFAULT '[]'`. |
| `models/hierarchy.py` — `Review` dataclass | Add field: `weaknesses: List[dict] = field(default_factory=list)`. Each item: `{id, text, category, status}` where status defaults to `"open"`. |
| `processors/review_quality.py` — new function `extract_weaknesses(findings)` | Scan findings for markers of weakness: short items (<15 words), items containing "unclear", "assumed", "TBC", "not defined", "low confidence", "unknown". Return list of `{id, text, category, status: "open"}`. |
| `project_manager.py` — `run_persona_review()` | After review is created, call `extract_weaknesses(review["findings"])` and store result via `store.update_review_weaknesses(review_id, weaknesses)`. |
| `db/hierarchy_store_sql.py` | Add `update_review_weaknesses(review_id, weaknesses)` — UPDATE reviews SET weaknesses=? WHERE review_id=?. |
| `static/index.html` — `viewReviewDetail()` | Add a "Weaknesses" section below findings: render each weakness with its category and an `open` badge. |

**Acceptance:**
- Every new review has a `weaknesses` array in its API response.
- Weakness items reference the category they came from.
- Section is visible in review detail.

---

### S4-02 · Missing category visibility

**What:** Make missing content areas (categories with zero findings) explicitly visible in the review detail.

**Where to change:**

| File | Change |
|---|---|
| `processors/review_quality.py` — `compute_completeness_score()` | Already returns `missing: [str]`. Expose this in the review detail API response. |
| `db/hierarchy_store_sql.py` — `get_review()` | Ensure `missing_categories` is populated: call `compute_completeness_score(findings).get("missing", [])` when loading a review for detail view. |
| `static/index.html` — `viewReviewDetail()` | Below the Coverage Assessment block, add a "Missing Categories" section. Render each missing category as a `<span class="tag">` with a distinct style. Include a note: "These areas had no findings — consider addressing them in the next review." |

**No new DB column needed.** Missing categories are computed on-read from existing `findings`.

**Acceptance:**
- Review with no `risks` findings shows "risks" in the Missing Categories section.
- Missing categories are visually distinct from covered categories.
- Section is absent when all standard categories have at least one finding.

---

### S4-03 · Gap-aware SME

**What:** Pass the current review's weaknesses and missing categories into the deep dive prompt so generated questions are more targeted.

**Where to change:**

| File | Change |
|---|---|
| `server.py` — `_handle_deep_dive()` | Read optional `review_id` from POST body. If provided, load that review and extract `weaknesses` and `missing_categories`. Pass both to `project_manager.run_deep_dive_analysis()`. |
| `project_manager.py` — `run_deep_dive_analysis()` | Accept `weaknesses: list = None, missing_categories: list = None`. Pass to `personas/deep_dive.py → run_deep_dive()`. |
| `personas/deep_dive.py` — `run_deep_dive()` | Accept `weaknesses` and `missing_categories`. Prepend to the deep dive prompt: "Known weaknesses: [...]. Missing categories: [...]. Generate questions that specifically address these." |
| `static/index.html` — `runDeepDive()` | Include `review_id: state._lastViewedReviewId` in the POST body when available. |

**Acceptance:**
- POST `/deep-dive` with `review_id` set → questions are noticeably more targeted to the specific gaps of that review vs baseline.
- POST without `review_id` → baseline behaviour unchanged.

---

### S4 Exit Gate

Before moving to S5:
- [ ] Every new review has a `weaknesses` array
- [ ] Missing categories shown explicitly in review detail
- [ ] Deep dive uses review weaknesses and missing categories when `review_id` is supplied



---

## S5 — Decision Intelligence

**Goal:** Move from finding issues to identifying the decisions that must be made next.
**Priority:** High | **Depends on:** S4 complete

---

### S5-01 · Decision point extraction

**What:** Add a structured `decision_points` section to each review.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE reviews ADD COLUMN decision_points TEXT DEFAULT '[]'`. |
| `models/hierarchy.py` — `Review` dataclass | Add field: `decision_points: List[dict] = field(default_factory=list)`. Each item: `{id, text, category, status, linked_finding}` where status defaults to `"open"`. |
| `processors/review_quality.py` — new function `extract_decision_points(findings)` | Scan findings for items containing decision-signal phrases: "choose between", "decide", "which approach", "platform choice", "DR vs", "phasing", "cost trade-off", "in scope or out". Return structured list. |
| `project_manager.py` — `run_persona_review()` | After weaknesses extraction (S4-01), call `extract_decision_points(review["findings"])` and store via `store.update_review_decision_points()`. |
| `db/hierarchy_store_sql.py` | Add `update_review_decision_points(review_id, decision_points)`. |
| `static/index.html` — `viewReviewDetail()` | Add a "Decision Points" section below Weaknesses. Each item shows text, category, and status badge (`open` / `addressed` / `validated` / `rejected`). |

**Acceptance:**
- Reviews with decision-signal language return a non-empty `decision_points` array.
- Each decision point has an `id`, `text`, `category`, and `status`.
- Section visible in review detail.

---

### S5-02 · Decision-question mapping

**What:** Each SME question can reference a decision point, so users understand why the question matters.

**Where to change:**

| File | Change |
|---|---|
| `personas/deep_dive.py` — `run_deep_dive()` | When `decision_points` are passed (from S4-03 extension), annotate each generated question with the decision point ID it targets: `{question, decision_point_id, decision_point_text}`. |
| `project_manager.py` — `run_deep_dive_analysis()` | Accept and forward `decision_points` list to deep dive. |
| `server.py` — `_handle_deep_dive()` | Load `decision_points` from review when `review_id` is provided (alongside weaknesses from S4-03). Pass to `run_deep_dive_analysis()`. |
| `static/index.html` — `ddGroup()` | When a question has `decision_point_text`, render it as a secondary line under the question: `"→ Decision: [text]"`. |
| `static/index.html` — prompt builder state | When a question with a `decision_point_id` is injected, store the mapping in `prompt_builder_state.decision_mappings`. |

**Acceptance:**
- Questions generated when `decision_points` exist show which decision they target.
- Prompt builder state retains `decision_mappings` for traceability.
- Questions without a matching decision point render normally (no error).

---

### S5-03 · Decision status tracking

**What:** Decision point status (`open` / `addressed` / `validated` / `rejected`) can be updated across review iterations.

**Where to change:**

| File | Change |
|---|---|
| `server.py` — `do_POST` | Add route: `POST /api/projects/{id}/hierarchy/reviews/{review_id}/decision/{decision_id}/status` — reads `{status}` from body, updates the specific decision point in `reviews.decision_points` JSON. |
| `project_manager.py` — new function `update_decision_status(project_id, review_id, decision_id, status)` | Load review, find decision point by `id`, update `status`, persist. |
| `db/hierarchy_store_sql.py` | Implement the update: deserialise `decision_points` JSON, mutate, re-serialise, UPDATE. |
| `static/index.html` — `viewReviewDetail()` decision point row | Add a status `<select>` dropdown per decision point with options `open / addressed / validated / rejected`. On change, call the new status endpoint. |
| `processors/review_quality.py` — `extract_decision_points()` | When creating a new review with `previous_review_id` set, carry over unresolved decision points from the predecessor with their current status. |

**Acceptance:**
- Changing a decision status via UI persists correctly.
- A new review that chains from a previous one inherits `open` decision points from the predecessor.
- Status values are constrained to the four valid options.

---

### S5 Exit Gate

Before moving to S6:
- [ ] Every new review has a `decision_points` array
- [ ] SME questions reference decision points when available
- [ ] Decision status can be updated per-review via API and UI
- [ ] Chained reviews inherit predecessor's unresolved decision points



---

## S6 — Resolution and Iteration Intelligence

**Goal:** Track whether weaknesses and decisions are actually being resolved review by review.
**Priority:** Medium | **Depends on:** S5 complete

---

### S6-01 · Weakness resolution tracking

**What:** Each weakness can transition through `open → addressed → validated → rejected`. Status persists and is visible.

**Where to change:**

| File | Change |
|---|---|
| `server.py` — `do_POST` | Add route: `POST /api/projects/{id}/hierarchy/reviews/{review_id}/weakness/{weakness_id}/status` — reads `{status}` from body, updates the specific weakness in `reviews.weaknesses` JSON. |
| `project_manager.py` — new function `update_weakness_status(project_id, review_id, weakness_id, status)` | Load review, find weakness by `id`, update `status`, persist. |
| `db/hierarchy_store_sql.py` | Implement via deserialise → mutate → re-serialise → UPDATE. |
| `static/index.html` — `viewReviewDetail()` weakness row | Add a status `<select>` per weakness: `open / addressed / validated / rejected`. On change, call the status endpoint. |
| `processors/review_quality.py` — `extract_weaknesses()` | When `previous_review_id` is set, cross-reference: weaknesses that still appear in the new review and were `addressed` in the predecessor are downgraded back to `open` (they recurred). New weaknesses default to `open`. |

**Acceptance:**
- Weakness status updates persist and survive page reload.
- A weakness marked `addressed` in `R1` that still appears in `R2` is flagged as `open` again in `R2`.
- All four status values work.

---

### S6-02 · Iteration diff engine

**What:** Extend the diff introduced in S3-04 to include `decision_points` and `weaknesses`, not only findings.

**Where to change:**

| File | Change |
|---|---|
| `project_manager.py` — `get_review_diff()` | Extend to also diff `weaknesses` (by `text` key) and `decision_points` (by `text` key). Return structure: `{findings: {...}, weaknesses: {...}, decision_points: {...}}` each with `new / resolved / unchanged` sub-keys. |
| `static/index.html` — `viewReviewDetail()` "What Changed" section | Render three tabs or expandable sections: Findings diff, Weaknesses diff, Decisions diff. Count totals per section. |

**Acceptance:**
- "What Changed" now covers findings, weaknesses, and decision points.
- Resolved weaknesses (gone from new review) appear in the `resolved` bucket.
- New decision points appear in the `new` bucket.

---

### S6-03 · Feedback integration into tightening loop

**What:** Unresolved client feedback artifacts (linked to the current `version_id` or `proposal_version_id`) are injected into the next review's tightening cycle. Only `new` (unresolved) feedback items are used. Resolved feedback is excluded.

**Where to change:**

| File | Change |
|---|---|
| `processors/presales_feedback.py` — `get_feedback_prompt_injection()` | Already filters to `status == "new"` items only (per AR-02). No change needed to filtering logic. |
| `processors/presales_feedback.py` — `attach_feedback_to_context()` | Ensure feedback linked to either `version_id` OR `proposal_version_id` is captured (per AR-02 resolution). Add a `version_id` parameter to the cache record alongside the existing `proposal_ver_id`. |
| `server.py` — `_handle_create_presales_feedback()` | Pass `version_id` from body alongside `proposal_ver_id` when calling `save_presales_feedback`. |
| `db/database.py` — `_apply_migrations()` | Add migration: `ALTER TABLE presales_feedback ADD COLUMN version_id TEXT DEFAULT ''`. |
| `static/index.html` — `openCaptureFeedback()` / feedback form | Add a hidden `version_id` field alongside `proposal_ver_id`; populate from `state._dashVersion`. |

**No change to `get_feedback_prompt_injection()`** filter logic — the S4 and S5 work already ensures prompts are tightened with both feedback and weakness/decision context.

**Acceptance:**
- Feedback captured against a `version_id` (no proposal yet) is injected into the next review.
- Feedback with `status == "actioned"` or `"closed"` is not injected.
- Old resolved feedback does not appear in new review prompts.

---

### S6 Exit Gate

Before moving to S7:
- [ ] Weakness status (`open / addressed / validated / rejected`) persists and is editable in UI
- [ ] Recurred weaknesses reset to `open` in the new review
- [ ] "What Changed" section covers findings, weaknesses, and decision points
- [ ] Feedback from `version_id` (no proposal) is captured and injected into next review



---

## S7 — Convergence and Learning Foundation

**Goal:** Measure proposal readiness and prepare the ground for future self-learning.
**Priority:** Medium | **Depends on:** S6 complete

---

### S7-01 · Convergence indicator (Decision Readiness)

**What:** Compute and display a "Decision Readiness" indicator — `Low / Medium / High` — for the active review chain of a version.

**Resolution AR-03 applied:** No numeric formula. Rules:
- `Low` — one or more unresolved (`open`) decision points exist
- `Medium` — no unresolved decision points, but unresolved weaknesses exist
- `High` — no unresolved decision points AND no unresolved weaknesses

**Where to change:**

| File | Change |
|---|---|
| `processors/review_quality.py` — new function `compute_decision_readiness(review_dict)` | Count `open` items in `decision_points` and `weaknesses`. Apply the three-level rule. Return `{level: "Low|Medium|High", open_decisions: int, open_weaknesses: int}`. |
| `project_manager.py` — new function `get_version_readiness(project_id, version_id)` | Load the active review for the version. Call `compute_decision_readiness()`. Return readiness dict. |
| `server.py` — `do_GET` | Add route: `GET /api/projects/{id}/hierarchy/versions/{version_id}/readiness` → calls `project_manager.get_version_readiness()`. |
| `static/index.html` — `viewVersions()` version summary row | After loading, fetch `readiness` and render: `🟢 High`, `🟡 Medium`, or `🔴 Low` as a small badge next to version ID. |
| `static/index.html` — `viewReviewDetail()` | Show readiness indicator in the metadata row. Label it "Decision Readiness" (not "Score"). |

**Indicator is informational only. Does not block any action** (per AR-03).

**Acceptance:**
- Version with no open decisions or weaknesses shows `High` (green).
- Version with open weaknesses but no open decisions shows `Medium` (yellow).
- Version with open decisions shows `Low` (red).
- Readiness badge visible in version list and review detail.

---

### S7-02 · Proposal readiness gate

**What:** Proposal generation shows a readiness summary and warns when critical unresolved decision points exist. Per AR-01: user selects the Active Review — system does not auto-select.

**Where to change:**

| File | Change |
|---|---|
| `static/index.html` — `showCreateProposal()` | After version and review are selected, fetch `GET /readiness` for that version. Display the readiness indicator in the create proposal form. |
| `static/index.html` — `submitCreateProposal()` | If readiness is `Low`, show a **non-blocking** confirmation: "This version has unresolved decision points. Proceed anyway?" with Confirm / Cancel. Does not prevent submission on confirm. |
| `processors/proposal_generator.py` — `generate_proposal_document()` | Add `readiness` to the returned document metadata (call `compute_decision_readiness` and include in the response). No blocking gate added — warning only, per the product direction of system-guides-not-enforces. |

**Acceptance:**
- Creating a proposal with a `Low` readiness version shows a warning before submission.
- User can confirm and proceed — action is not blocked.
- Validation message explains what is unresolved (open decision count + open weakness count).
- Readiness is shown in the generated proposal document metadata.



---

### S7-03 · Prompt logging foundation

**What:** Capture the full prompt state and outcome links on every review so the system can learn from them later.

**Where to change:**

| File | Change |
|---|---|
| `db/database.py` — new table | Add table `prompt_log` to `_SCHEMA_SQL`: `(log_id, project_id, review_id, persona_name, scenario_type, baseline_prompt, injected_questions, user_notes, final_prompt, outcome_review_id, outcome_proposal_ver_id, created_at)`. All text columns, `DEFAULT ''`. |
| `db/database.py` — `_apply_migrations()` | Run `CREATE TABLE IF NOT EXISTS prompt_log (...)` in the migrations block. |
| `processors/` — new file `prompt_logger.py` | `log_prompt(project_id, review_id, prompt_builder_state, final_prompt, persona_name, scenario_type)` → INSERT into `prompt_log`. `link_outcome(review_id, outcome_type, outcome_id)` → UPDATE `prompt_log` to set `outcome_review_id` or `outcome_proposal_ver_id`. |
| `project_manager.py` — `run_persona_review()` | After review is created, call `prompt_logger.log_prompt(...)` using the review's `prompt_builder_state` and `persona`. |
| `project_manager.py` — `create_proposal()` | After proposal version is created, call `prompt_logger.link_outcome(active_review_id, "proposal_version", proposal_ver_id)`. |

**`persona_name` and `scenario_type` come from `prompt_builder_state`** (AR-04 fields) when present, otherwise default to empty string.

**Acceptance:**
- Every new review creates a `prompt_log` row.
- `final_prompt` stores the assembled prompt sent to the LLM.
- Creating a proposal updates the corresponding prompt log row with `outcome_proposal_ver_id`.
- Existing reviews are unaffected (no backfill required).

---

### S7-04 · Learning-ready retrieval

**What:** Provide a simple API endpoint to query past prompts by `persona_name` and/or `scenario_type`. No autonomous learning or retraining.

**Where to change:**

| File | Change |
|---|---|
| `processors/prompt_logger.py` — new function `query_prompts(project_id, persona_name=None, scenario_type=None, limit=20)` | SELECT from `prompt_log` with optional WHERE filters. Return list of dicts. |
| `project_manager.py` — new function `get_prompt_history(project_id, persona_name=None, scenario_type=None)` | Thin wrapper around `prompt_logger.query_prompts()`. |
| `server.py` — `do_GET` | Add route: `GET /api/projects/{id}/prompt-history?persona_name=…&scenario_type=…` → calls `project_manager.get_prompt_history()`. Returns `{prompts: [...], count: int}`. |

**No UI surface required in this sprint.** The endpoint is for future use.

**Acceptance:**
- `GET /prompt-history` with no filters returns all prompt log entries for the project.
- `?persona_name=Solution+Architect` returns only entries with that persona.
- `?scenario_type=pre-sales` returns only pre-sales scenario entries.
- No retraining, recommendation engine, or autonomous behaviour is implemented.

---

### S7 Exit Gate

Before declaring transformation complete:
- [ ] Decision Readiness (`Low / Medium / High`) visible on version list and review detail
- [ ] Proposal creation shows readiness warning for `Low` versions (non-blocking)
- [ ] Every new review creates a `prompt_log` row with full prompt state
- [ ] `GET /prompt-history` endpoint returns filterable prompt log entries



---

## Cross-Cutting Rules (All Sprints)

These rules apply to every story in every sprint.

| Rule | Detail |
|---|---|
| **No architecture redesign** | All changes are additive. Existing routes, models, and DB tables are extended, not replaced. |
| **Backward compatibility** | All new DB columns use `DEFAULT ''` or `DEFAULT '[]'` so existing records load without error. |
| **No auto-enforcement** | The system shows Decision Readiness and warnings. It does not block user actions unless explicitly stated in a story. User remains the final authority (AR-01, AR-03). |
| **Score is secondary** | `completeness_score` and `compute_completeness_score()` are never removed. The score is available but demoted visually in S1-05. |
| **Single-container constraint** | No new services, no external message queues, no scheduled jobs. All features run inside the existing `http.server` process. |
| **Offline-first** | All new features work with `ai_backend = "files_only"`. AI backends enhance but are never required. |
| **Non-technical users** | UI additions must use existing design tokens and patterns from `static/index.html`. No new build toolchain. |
| **Stop after each sprint** | Do not implement stories from Sprint N+1 until Sprint N exit gate is confirmed. |

---

## Schema Change Summary (All Sprints)

| Sprint | Table | New Column / Table |
|---|---|---|
| S1 | `reviews` | `previous_review_id TEXT DEFAULT ''` |
| S2 | `reviews` | `prompt_builder_state TEXT DEFAULT NULL` |
| S4 | `reviews` | `weaknesses TEXT DEFAULT '[]'` |
| S5 | `reviews` | `decision_points TEXT DEFAULT '[]'` |
| S6 | `presales_feedback` | `version_id TEXT DEFAULT ''` |
| S7 | new table | `prompt_log` (full schema in S7-03) |

All applied via `db/database.py → _apply_migrations()` using the existing idempotent `ALTER TABLE IF NOT EXISTS col` pattern.

---

## New API Endpoints Summary (All Sprints)

| Sprint | Method | Route | Purpose |
|---|---|---|---|
| S3 | GET | `/api/projects/{id}/hierarchy/reviews/{rid}/diff` | Review diff vs predecessor |
| S5 | POST | `/api/projects/{id}/hierarchy/reviews/{rid}/decision/{did}/status` | Update decision point status |
| S6 | POST | `/api/projects/{id}/hierarchy/reviews/{rid}/weakness/{wid}/status` | Update weakness status |
| S7 | GET | `/api/projects/{id}/hierarchy/versions/{vid}/readiness` | Decision Readiness indicator |
| S7 | GET | `/api/projects/{id}/prompt-history` | Query prompt log |

All existing routes remain unchanged.
