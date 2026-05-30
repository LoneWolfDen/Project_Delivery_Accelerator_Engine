# Sprint 3 Regression Test Plan

**Sprint:** S3 — Guided Tightening Loop  
**Depends on:** S1 (foundation + review chain) and S2 (prompt builder) both passing  
**Scope:** S3-01 SME question generator · S3-02 question selection flow · S3-03 tightened review · S3-04 What Changed diff  
**Test files:**
- `tests/test_sprint1_regression.py` — S1 core regression (do not modify)
- `tests/test_sprint2_regression.py` — S2 core regression (do not modify)
- `tests/test_sprint3_regression.py` — S3 core regression (extended this sprint)
- `tests/test_e2e_user_journey.py` — end-to-end user journeys (new this sprint)
- `tests/test_html_static_analysis.py` — HTML structural safety (always-run)

---

## 1. Coverage Summary

| Story | What it changes | Test section | Priority |
|-------|-----------------|--------------|----------|
| S1-02 | `previous_review_id` column + dataclass + store | `test_sprint1_regression.py · TestReviewChaining` | P0 — always run |
| S1-03 | Iteration labels R1/R2/R3 from `list_reviews()` | `test_sprint1_regression.py · TestIterationNumbers` | P0 — always run |
| S2-02 | `prompt_builder_state` column + persistence + API | `test_sprint2_regression.py · TestPromptBuilderState*` | P0 — always run |
| S2-03 | Baseline/Customised badge logic | `test_sprint2_regression.py · TestBaselineCustomisedBadgeLogic` | P0 — always run |
| S3-01 | Deep dive heuristic output contract | `test_sprint3_regression.py · TestDeepDiveHeuristicOutputContract` | P0 — always run |
| S3-02 | `addSelectedToPrompt` uses chip array not textarea | `test_sprint3_regression.py · TestQuestionSelectionFlowHTML` | P0 — always run |
| S3-03 | Chained review stores `previous_review_id` + `pbs` | `test_sprint3_regression.py · TestTightenedReviewBackend` | P0 — always run |
| S3-03 | HTML contract: `previousReviewId` input + `runReview` body | `test_sprint3_regression.py · TestTightenedReviewHTML` | P0 — always run |
| S3-04 | Diff logic: new / resolved / unchanged | `test_sprint3_regression.py · TestGetReviewDiff` | P0 — always run |
| S3-04 | `viewReviewDetail` references `previous_review_id` | `test_sprint3_regression.py · TestWhatChangedHTML` | P0 — always run |
| S3 tasks 1–6 | clear-after-run, YAML prompts, AdminConfig, engine overrides, admin UI | `test_sprint3_regression.py · sections A–E` | P0 — always run |
| HTML safety | No `<script>` in template literals, balanced blocks, function definitions | `test_html_static_analysis.py` | P0 — always run |
| E2E journeys | Full vertical slices — tightening loop, diff, state consistency | `test_e2e_user_journey.py` | P1 — run on every PR |


---

## 2. Test Cases by Module

### 2.1 Core Regression — S1 (must not regress)

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S1-R01 | `test_first_review_has_empty_previous` | Happy path | `previous_review_id == ""` for standalone review |
| S1-R02 | `test_chained_review_stores_previous_review_id` | Happy path | `r2.previous_review_id == r1.review_id` after create |
| S1-R03 | `test_previous_review_id_survives_round_trip` | State consistency | `get_review(r2).previous_review_id == r1.review_id` |
| S1-R04 | `test_previous_review_id_in_to_dict` | API surface | `to_dict()` exposes `previous_review_id` |
| S1-R05 | `test_previous_review_id_in_to_summary` | API surface | `to_summary()` exposes `previous_review_id` |
| S1-R06 | `test_previous_review_id_in_list_reviews` | API surface | `list_reviews()` summaries carry `previous_review_id` |
| S1-R07 | `test_chain_across_three_reviews` | Happy path | R1→R2→R3 each links only to direct predecessor |
| S1-R08 | `test_existing_reviews_unaffected_by_migration` | Backward compat | Reviews without field default to `""` |
| S1-R09 | `test_schema_column_exists` | Schema | `reviews` table has `previous_review_id` column |
| S1-R10 | `test_first_review_is_r1` | Happy path | `iteration_number == 1` for first review |
| S1-R11 | `test_three_reviews_labelled_r1_r2_r3` | Happy path | Three reviews on same version get 1, 2, 3 |
| S1-R12 | `test_iteration_numbers_are_version_scoped` | State consistency | Reviews on different versions each start at 1 |
| S1-R13 | `test_delete_review_does_not_corrupt_remaining_iteration` | Negative | After delete, survivors keep correct labels |

### 2.2 Core Regression — S2 (must not regress)

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S2-R01 | `test_column_exists_in_schema` | Schema | `prompt_builder_state` column in `reviews` table |
| S2-R02 | `test_column_default_is_null` | Schema | Reviews without pbs store `NULL` |
| S2-R03 | `test_dataclass_field_exists` | Model | `Review` dataclass has `prompt_builder_state` field |
| S2-R04 | `test_create_review_with_injected_questions` | Happy path | pbs with injected questions survives round-trip |
| S2-R05 | `test_create_review_with_user_notes` | Happy path | pbs with user notes survives round-trip |
| S2-R06 | `test_pbs_questions_order_preserved` | State consistency | Question order is preserved in round-trip |
| S2-R07 | `test_pbs_in_to_dict` | API surface | `to_dict()` exposes `prompt_builder_state` |
| S2-R08 | `test_pbs_in_to_summary` | API surface | `to_summary()` exposes `prompt_builder_state` |
| S2-R09 | `test_pbs_in_list_reviews` | API surface | `list_reviews()` summaries carry pbs |
| S2-R10 | `test_mixed_reviews_pbs_and_null` | State consistency | List with baseline and customised reviews returns correct pbs per review |
| S2-R11 | `test_none_pbs_is_baseline` | Badge logic | `None` pbs → Baseline badge |
| S2-R12 | `test_whitespace_only_notes_is_baseline` | Badge logic | Whitespace-only notes → Baseline |
| S2-R13 | `test_one_injected_question_is_customised` | Badge logic | One injected question → Customised badge |
| S2-R14 | `test_non_empty_notes_is_customised` | Badge logic | Non-empty user_notes → Customised badge |


### 2.3 Sprint-Specific Regression — S3

#### S3-01: SME Question Generator (deep_dive heuristic)

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S3-01-H01 | `test_returns_dict_with_required_top_level_keys` | Happy path | All required keys present in result |
| S3-01-H02 | `test_ai_mode_is_false_for_files_only` | Happy path | `ai_mode == False` in files_only mode |
| S3-01-H03 | `test_question_groups_is_non_empty_list` | Happy path | At least one question group returned |
| S3-01-H04 | `test_each_group_has_required_keys` | Happy path | Every group has `category`, `icon`, `questions` |
| S3-01-H05 | `test_all_questions_carry_category_prefix` | Happy path | Every flat question starts with `[Category]` prefix |
| S3-01-H06 | `test_scope_completeness_is_integer_0_to_100` | Happy path | `scope_completeness` is `int` in `[0, 100]` |
| S3-01-H07 | `test_question_min_length` | Happy path | No question shorter than 20 characters |
| S3-01-H08 | `test_solution_architect_returns_architecture_category` | Happy path | SA persona produces Architecture/Design/NFR group |
| S3-01-H09 | `test_delivery_manager_returns_delivery_category` | Happy path | DM persona produces Delivery/Risk/Scope group |
| S3-01-N01 | `test_empty_scope_still_returns_questions` | Negative | Empty scope does not crash, returns ≥1 group |
| S3-01-N02 | `test_empty_intelligence_still_returns_questions` | Negative | Empty intelligence does not crash |
| S3-01-N03 | `test_unknown_persona_falls_back_gracefully` | Negative | Unknown persona falls back, no exception |
| S3-01-N04 | `test_groups_capped_at_six` | Boundary | At most 6 groups returned |
| S3-01-N05 | `test_scope_completeness_zero_for_empty_everything` | Boundary | Empty scope + intelligence → completeness == 0 |
| S3-01-N06 | `test_rich_scope_scores_higher_than_empty` | Boundary | Rich scope completeness > empty completeness |

#### S3-02: Question Selection Flow (HTML contract)

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S3-02-H01 | `test_addSelectedToPrompt_function_defined` | UI behaviour | Function present in index.html |
| S3-02-H02 | `test_addSelectedToPrompt_pushes_to_injectedQuestions_not_textarea` | UI behaviour | Body references `_injectedQuestions`, not `customPrompt` |
| S3-02-H03 | `test_removeInjectedQuestion_function_defined` | UI behaviour | `_removeInjectedQuestion` present |
| S3-02-H04 | `test_renderInjectedQuestions_function_defined` | UI behaviour | `_renderInjectedQuestions` present |
| S3-02-H05 | `test_injectedQuestions_state_initialised_before_use` | State consistency | `_injectedQuestions` initialised to `[]` |
| S3-02-H06 | `test_customPrompt_textarea_absent` | UI behaviour | `id="customPrompt"` removed (S2-01 replaced it) |
| S3-02-H07 | `test_injectedQuestions_container_present` | UI behaviour | `id="injectedQuestions"` container in DOM |
| S3-02-H08 | `test_userNotes_textarea_present` | UI behaviour | `id="userNotes"` textarea present |

#### S3-03: Run Tightened Review

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S3-03-H01 | `test_chained_review_stores_previous_review_id` | Happy path | `previous_review_id` persists after create |
| S3-03-H02 | `test_chained_review_also_stores_prompt_builder_state` | Happy path | Both chain + pbs persist together |
| S3-03-H03 | `test_chained_review_iteration_number_increments` | Happy path | R1=1, R2=2 for chained pair |
| S3-03-H04 | `test_unchained_review_has_empty_previous_id` | Happy path | Standalone review has `""` previous_review_id |
| S3-03-H05 | `test_three_level_chain_integrity` | Happy path | R1→R2→R3 each links only to direct predecessor |
| S3-03-H06 | `test_previous_review_id_visible_in_to_summary` | API surface | `to_summary()` exposes chain link |
| S3-03-H07 | `test_previous_review_id_visible_in_list_reviews` | API surface | `list_reviews()` summaries carry chain link |
| S3-03-H08 | `test_chained_review_with_findings_persists_findings_too` | State consistency | Chaining does not corrupt findings field |
| S3-03-UI01 | `test_previousReviewId_input_exists_in_html` | UI behaviour | `id="previousReviewId"` input present in index.html |
| S3-03-UI02 | `test_runReview_sends_previous_review_id` | UI behaviour | `runReview()` POST body includes `previous_review_id` |
| S3-03-UI03 | `test_runReview_sends_prompt_builder_state` | UI behaviour | `runReview()` POST body includes `prompt_builder_state` |
| S3-03-UI04 | `test_viewReviewDetail_has_tighten_mechanism` | UI behaviour | `viewReviewDetail()` references `previousReviewId` or tighten trigger |

#### S3-04: What Changed Summary

| ID | Test name | Type | Pass condition |
|----|-----------|------|----------------|
| S3-04-H01 | `test_new_finding_classified_as_new` | Happy path | Added finding appears in `new` bucket |
| S3-04-H02 | `test_removed_finding_classified_as_resolved` | Happy path | Removed finding appears in `resolved` bucket |
| S3-04-H03 | `test_retained_finding_classified_as_unchanged` | Happy path | Retained finding appears in `unchanged` bucket |
| S3-04-H04 | `test_entirely_new_category_all_items_are_new` | Happy path | New category: all items in `new`, none in `resolved` |
| S3-04-H05 | `test_entirely_removed_category_all_items_are_resolved` | Happy path | Dropped category: all items in `resolved` |
| S3-04-H06 | `test_no_overlap_all_findings_are_new_and_resolved` | Happy path | Fully replaced findings: all in `new`/`resolved` |
| S3-04-H07 | `test_identical_findings_all_unchanged` | Happy path | No changes: all in `unchanged`, `new` and `resolved` empty |
| S3-04-H08 | `test_multi_category_diff_is_per_category` | Happy path | Diff is independently computed per category |
| S3-04-N01 | `test_review_without_predecessor_has_no_diff_context` | Negative | Standalone review has `previous_review_id == ""` |
| S3-04-N02 | `test_chained_review_has_predecessor_for_diff` | State consistency | Chained review has accessible predecessor with correct findings |
| S3-04-N03 | `test_diff_uses_previous_review_id_not_timestamp` | State consistency | Predecessor is the explicitly stored ID, not nearest by time |
| S3-04-N04 | `test_empty_both_returns_empty_diff` | Boundary | Empty prev + empty curr → empty diff |
| S3-04-N05 | `test_empty_previous_all_current_are_new` | Boundary | No predecessor findings → all current in `new` |
| S3-04-N06 | `test_empty_current_all_previous_are_resolved` | Boundary | No current findings → all previous in `resolved` |
| S3-04-UI01 | `test_viewReviewDetail_defined` | UI behaviour | `viewReviewDetail()` function present |
| S3-04-UI02 | `test_viewReviewDetail_references_previous_review_id` | UI behaviour | Function body checks `previous_review_id` |
| S3-04-UI03 | `test_what_changed_label_in_html` | UI behaviour | "What Changed" label present in index.html |


### 2.4 End-to-End User Journey Tests

| Journey | Class | Description | Covers |
|---------|-------|-------------|--------|
| J1 | `TestJourney1_S1Foundation` | Version created → baseline review → R1 label | S1-01, S1-02, S1-03 |
| J2 | `TestJourney2_S2PromptBuilder` | Baseline review → customised review → badge | S2-02, S2-03 |
| J3 | `TestJourney3_S3TighteningLoop` | Baseline → Ask SME → select questions → tightened review → chain | S3-01, S3-02, S3-03 |
| J4 | `TestJourney4_S3ReviewDiff` | Two chained reviews → diff new/resolved/unchanged | S3-04 |
| J5 | `TestJourney5_MultiVersionStateConsistency` | Multiple versions with independent chains | S1-03, S3-03 (cross-version) |
| J6 | `TestJourney6_NegativeAndGuardrails` | Edge cases: null pbs, empty findings, empty scope, unknown persona | All sprints |

---

## 3. Test Priorities

### P0 — Always run (gate on every commit and PR)

These tests catch regressions in stable, merged features. A failure here means something broken in production-critical logic.

```
tests/test_sprint1_regression.py
tests/test_sprint2_regression.py
tests/test_sprint3_regression.py
tests/test_html_static_analysis.py
```

Run command:
```bash
pytest tests/test_sprint1_regression.py \
       tests/test_sprint2_regression.py \
       tests/test_sprint3_regression.py \
       tests/test_html_static_analysis.py \
       -v --tb=short
```

### P1 — Run on every PR (pre-merge gate)

Full regression including end-to-end journeys. Slower but complete.

```
tests/test_sprint1_regression.py
tests/test_sprint2_regression.py
tests/test_sprint3_regression.py
tests/test_html_static_analysis.py
tests/test_e2e_user_journey.py
```

Run command:
```bash
pytest tests/test_sprint1_regression.py \
       tests/test_sprint2_regression.py \
       tests/test_sprint3_regression.py \
       tests/test_html_static_analysis.py \
       tests/test_e2e_user_journey.py \
       -v --tb=short
```

### P2 — Run periodically / on refactor

Full test suite including unit and integration tests.

```bash
pytest tests/ -v --tb=short
```

---

## 4. Test Suite Structure

```
tests/
├── conftest.py                      # shared fixtures (sample_data_dir)
│
├── ── Core regression (P0 — always run) ──────────────────────
├── test_sprint1_regression.py       # S1: review chaining, iteration labels
├── test_sprint2_regression.py       # S2: prompt_builder_state, badge logic
├── test_sprint3_regression.py       # S3: A-E (tasks 1-6) + F-I (S3-01 to S3-04)
├── test_html_static_analysis.py     # HTML structural safety (script-in-template, balanced blocks)
│
├── ── End-to-end journeys (P1 — run on every PR) ──────────────
├── test_e2e_user_journey.py         # J1-J6: full tightening loop vertical slices
│
└── ── Unit + integration (P2 — run periodically) ──────────────
    ├── test_context_builder.py
    ├── test_extraction_quality.py
    ├── test_history.py
    ├── test_ingestion.py
    ├── test_models.py
    ├── test_persona_engine.py
    ├── test_personas.py
    ├── test_proposals_phases.py
    ├── test_sample_data.py
    └── test_server.py
```

---

## 5. Test Separation Rationale

| Layer | File | Why separate |
|-------|------|--------------|
| Core regression | `test_sprint{N}_regression.py` | One file per sprint. Sprint N tests are never modified when implementing sprint N+1. Provides a stable, predictable gate. |
| HTML static analysis | `test_html_static_analysis.py` | Guards against the PR-62 class of bug (script-in-template-literal) independently of any sprint. Always relevant. |
| E2E journeys | `test_e2e_user_journey.py` | Exercises full vertical slices. Slower (real SQLite I/O). Separate to allow P0 gates to stay fast. |
| Unit / integration | existing `test_*.py` files | Existing suite; not modified by S3 work. |

---

## 6. Design Constraints Applied

All tests in this plan respect the project-wide constraints:

| Constraint | How enforced |
|------------|--------------|
| Single-container / no external services | No HTTP server started; backend logic called directly |
| Offline-first | `ai_backend="files_only"` throughout all new tests |
| No mocks | Real SQLite via `HierarchyStoreSQLite`, real YAML loading, real `run_deep_dive()` |
| Deterministic | `files_only` heuristic path produces consistent output; no LLM calls |
| Isolated | Every test gets a fresh `tmp_path` + reset `threading.local()` DB connection |
| Non-technical users | No complex setup required — `pytest tests/` from repo root is the only command |

---

## 7. What Is NOT Covered (Intentionally)

| Item | Reason |
|------|--------|
| S4–S7 stories | Not yet implemented. No speculative tests. |
| LLM-backed deep dive | Non-deterministic; requires API keys. Covered separately if AI integration tests are added. |
| Browser/JS execution | JS chip selection and rendering logic tested via static source analysis only. Full browser tests require a separate toolchain (e.g., Playwright). |
| Server HTTP layer | `_handle_review()` and `_handle_deep_dive()` are covered by `test_server.py`; not duplicated here. |
| `get_review_diff` API endpoint | S3-04 specifies a `GET /diff` route; the endpoint is not yet implemented. Tests cover the diff logic contract and UI contract; the route is tested in `test_server.py` when implemented. |

---

## 8. Recommended Next Steps After S3 Regression Is in Place

1. **Confirm S3 exit gate** — Run P0 + P1 suite. All must pass before beginning S4.
2. **Add S4 regression file** — Create `tests/test_sprint4_regression.py` following the same pattern. Do not add S4 tests to any S1–S3 file.
3. **Implement `GET /diff` route** — Add a route test to `test_server.py` once the endpoint is live.
4. **Extend E2E journeys incrementally** — Add Journey 7 (S4: weakness extraction) to `test_e2e_user_journey.py` after S4 is merged.
5. **Do not modify `test_sprint1_regression.py` or `test_sprint2_regression.py`** — These are stable gates. Changes break the sprint-boundary contract.
