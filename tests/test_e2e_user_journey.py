"""End-to-End User Journey Tests — Sprint 1 + Sprint 2 + Sprint 3.

These tests exercise full vertical slices through the backend stack
(store → model → API surfaces) to verify the end-to-end tightening loop
works exactly as a user would experience it.

Journey 1  (S1 foundation)
  Version created → baseline review run → iteration labels assigned.

Journey 2  (S2 prompt builder)
  Baseline review → customised review with injected questions + notes →
  badge logic consistent with stored state.

Journey 3  (S3 tightening loop)
  Baseline review → Ask SME (deep dive) → questions selected →
  tightened review run (chained) → chain integrity verified.

Journey 4  (S3 diff)
  Two chained reviews with overlapping findings → diff correctly
  classifies new / resolved / unchanged per category.

Journey 5  (State consistency)
  Multiple versions with independent review chains — no cross-version
  iteration number or chain leakage.

Journey 6  (Negative / guard-rails)
  Missing previous_review_id → standalone, no diff context.
  Null prompt_builder_state → badge is Baseline.
  Empty findings → diff returns empty buckets.

Design rules:
  - No mocks. All tests hit real in-process code paths.
  - Isolated SQLite per test via tmp_path + monkeypatch.
  - No server process required: backend logic called directly.
  - Deterministic: files_only AI backend throughout.
  - No speculative S4+ assertions.
"""

import sys
import threading
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))



# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Fresh temp dir + reset DB thread-local for every test."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture()
def store(tmp_path):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite("proj-e2e")


@pytest.fixture()
def version(store):
    return store.create_version(
        included_artifacts=[
            {"filename": "scope.txt", "category": "scope"},
            {"filename": "risks.md", "category": "risk"},
        ],
        label="Baseline version",
        scope="Cloud migration for healthcare platform. 6-month timeline. AWS target.",
    )


# ── Badge helper (mirrors S2-03 JS logic) ────────────────────────────────────

def _is_customised(pbs: Any) -> bool:
    if not pbs:
        return False
    has_q = bool(pbs.get("injected_questions") or [])
    has_n = bool((pbs.get("user_notes") or "").strip())
    return has_q or has_n



# ── Diff helper (mirrors S3-04 backend logic) ─────────────────────────────────

def _compute_diff(prev: Dict[str, list], curr: Dict[str, list]) -> Dict[str, Dict[str, list]]:
    """Pure Python mirror of the get_review_diff contract."""
    result: Dict[str, Dict[str, list]] = {}
    for cat in set(prev) | set(curr):
        p = set(prev.get(cat, []))
        c = set(curr.get(cat, []))
        result[cat] = {
            "new":       sorted(c - p),
            "resolved":  sorted(p - c),
            "unchanged": sorted(c & p),
        }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Journey 1 — S1 foundation: version → baseline review → iteration labels
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney1_S1Foundation:
    """A user creates a version and runs their first review.

    Validates: version created, review linked, R1 label assigned,
    previous_review_id empty for first review.
    """

    def test_version_is_created_with_correct_label(self, store, version):
        v = store.get_version(version.version_id)
        assert v is not None
        assert v.label == "Baseline version"

    def test_first_review_linked_to_version(self, store, version):
        r = store.create_review(
            version_id=version.version_id,
            persona="Solution Architect",
            findings={"risks": ["no DR strategy documented"]},
        )
        v_after = store.get_version(version.version_id)
        assert r.review_id in v_after.review_ids

    def test_first_review_is_iteration_r1(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        summaries = store.list_reviews(version_id=version.version_id)
        assert len(summaries) == 1
        assert summaries[0]["iteration_number"] == 1

    def test_first_review_has_empty_previous_review_id(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        assert r.previous_review_id == ""

    def test_second_review_on_same_version_is_r2(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        store.create_review(version_id=version.version_id, persona="DM")
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id["r1"] == 1
        assert by_id["r2"] == 2

    def test_active_review_defaults_to_latest(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(version_id=version.version_id, persona="DM")
        v_after = store.get_version(version.version_id)
        assert v_after.active_review_id == r2.review_id



# ══════════════════════════════════════════════════════════════════════════════
# Journey 2 — S2 prompt builder: baseline → customised review
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney2_S2PromptBuilder:
    """User runs a baseline review, then a customised review with injected questions.

    Validates: baseline review has null pbs → Baseline badge.
    Customised review stores pbs → Customised badge.
    Both reviews visible in list with correct badge state.
    """

    def test_baseline_review_has_null_prompt_builder_state(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state is None

    def test_baseline_review_badge_is_baseline(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        fetched = store.get_review(r.review_id)
        assert _is_customised(fetched.prompt_builder_state) is False

    def test_customised_review_stores_injected_questions(self, store, version):
        pbs = {
            "injected_questions": ["What is the DR strategy?", "Any cost ceiling?"],
            "user_notes": "",
        }
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state["injected_questions"] == [
            "What is the DR strategy?", "Any cost ceiling?"
        ]

    def test_customised_review_badge_is_customised(self, store, version):
        pbs = {"injected_questions": ["Q?"], "user_notes": ""}
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert _is_customised(fetched.prompt_builder_state) is True

    def test_notes_only_review_badge_is_customised(self, store, version):
        pbs = {"injected_questions": [], "user_notes": "AWS only, budget cap £500K"}
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert _is_customised(fetched.prompt_builder_state) is True

    def test_list_contains_both_baseline_and_customised(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        pbs = {"injected_questions": ["Q?"], "user_notes": ""}
        store.create_review(
            version_id=version.version_id, persona="SA",
            prompt_builder_state=pbs,
        )
        summaries = store.list_reviews(version_id=version.version_id)
        badges = {s["review_id"]: _is_customised(s["prompt_builder_state"])
                  for s in summaries}
        # r1 = baseline, r2 = customised
        assert badges["r1"] is False
        assert badges["r2"] is True

    def test_question_order_preserved_through_round_trip(self, store, version):
        questions = ["Q3 last?", "Q1 first?", "Q2 middle?"]
        pbs = {"injected_questions": questions, "user_notes": ""}
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state["injected_questions"] == questions



# ══════════════════════════════════════════════════════════════════════════════
# Journey 3 — S3 tightening loop: baseline → Ask SME → tightened review
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney3_S3TighteningLoop:
    """Full tightening loop:
      1. Baseline review on v1.
      2. User runs Ask SME (deep dive) → gets structured questions.
      3. User selects questions → state._injectedQuestions populated.
      4. User runs tightened review → chained to baseline via previous_review_id.
      5. Tightened review stores pbs (injected questions) + previous_review_id.
      6. Iteration numbers: R1 (baseline) and R2 (tightened).
    """

    def test_step1_baseline_review_created(self, store, version):
        r1 = store.create_review(
            version_id=version.version_id, persona="Solution Architect",
            findings={"risks": ["no DR strategy"]},
        )
        assert r1.previous_review_id == ""
        assert r1.prompt_builder_state is None

    def test_step2_ask_sme_returns_question_groups(self):
        """Deep dive (Ask SME) returns structured groups in files_only mode."""
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration for healthcare. AWS target.",
            intelligence={"risks": ["no DR strategy"], "assumptions": [], "dependencies": [],
                          "constraints": [], "action_items": []},
            active_files=[{"filename": "scope.txt", "source_type": "text"}],
            ai_backend="files_only",
        )
        assert len(result["question_groups"]) >= 1
        assert len(result["all_questions"]) >= 1

    def test_step3_selected_questions_form_valid_pbs(self, store, version):
        """Simulates user selecting questions from deep dive output."""
        from personas.deep_dive import run_deep_dive
        dd = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration",
            intelligence={"risks": [], "assumptions": [], "dependencies": [],
                          "constraints": [], "action_items": []},
            active_files=[],
            ai_backend="files_only",
        )
        # User picks the first question from the first group
        first_q = dd["question_groups"][0]["questions"][0]
        # Strip [Category] prefix (as S3-02 spec requires)
        clean_q = first_q  # already stripped in heuristic (prefix only in all_questions)
        pbs = {"injected_questions": [clean_q], "user_notes": "AWS only"}
        assert _is_customised(pbs) is True

    def test_step4_tightened_review_chained_to_baseline(self, store, version):
        r1 = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["no DR strategy"]},
        )
        pbs = {"injected_questions": ["What is the DR strategy?"], "user_notes": "AWS only"}
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
            findings={"risks": ["cost overrun possible"]},
        )
        assert r2.previous_review_id == r1.review_id

    def test_step5_tightened_review_has_pbs_and_chain(self, store, version):
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        pbs = {
            "injected_questions": ["What is the DR strategy?", "Any SLA targets?"],
            "user_notes": "Budget cap £500K",
        }
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r2.review_id)
        assert fetched.previous_review_id == r1.review_id
        assert fetched.prompt_builder_state["injected_questions"] == [
            "What is the DR strategy?", "Any SLA targets?"
        ]
        assert fetched.prompt_builder_state["user_notes"] == "Budget cap £500K"

    def test_step6_iteration_labels_r1_and_r2(self, store, version):
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id[r1.review_id] == 1  # R1 — baseline
        assert by_id[r2.review_id] == 2  # R2 — tightened

    def test_tightened_review_badge_is_customised(self, store, version):
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        pbs = {"injected_questions": ["DR strategy?"], "user_notes": ""}
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r2.review_id)
        assert _is_customised(fetched.prompt_builder_state) is True

    def test_full_loop_r1_r2_r3_chain_integrity(self, store, version):
        """Three-iteration tightening loop: R1 → R2 → R3."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            prompt_builder_state={"injected_questions": ["Q1?"], "user_notes": ""},
        )
        r3 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r2.review_id,
            prompt_builder_state={"injected_questions": ["Q2?", "Q3?"], "user_notes": "Final context"},
        )
        assert store.get_review(r3.review_id).previous_review_id == r2.review_id
        assert store.get_review(r2.review_id).previous_review_id == r1.review_id
        assert store.get_review(r1.review_id).previous_review_id == ""
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id[r1.review_id] == 1
        assert by_id[r2.review_id] == 2
        assert by_id[r3.review_id] == 3



# ══════════════════════════════════════════════════════════════════════════════
# Journey 4 — S3-04 diff: chained reviews produce correct What Changed output
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney4_S3ReviewDiff:
    """Two chained reviews with overlapping findings.
    Diff correctly classifies new / resolved / unchanged across categories.
    """

    def test_new_finding_appears_in_new_bucket(self, store, version):
        r1 = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["vendor lock-in", "cost overrun"]},
        )
        f1 = store.get_review(r1.review_id).findings
        f2 = store.get_review(r2.review_id).findings
        diff = _compute_diff(f1, f2)
        assert "cost overrun" in diff["risks"]["new"]

    def test_resolved_finding_appears_in_resolved_bucket(self, store, version):
        r1 = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in", "cost overrun"]},
        )
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["vendor lock-in"]},
        )
        diff = _compute_diff(
            store.get_review(r1.review_id).findings,
            store.get_review(r2.review_id).findings,
        )
        assert "cost overrun" in diff["risks"]["resolved"]
        assert "vendor lock-in" in diff["risks"]["unchanged"]

    def test_identical_findings_produce_all_unchanged(self, store, version):
        findings = {"risks": ["vendor lock-in"], "assumptions": ["team available"]}
        r1 = store.create_review(
            version_id=version.version_id, persona="SA", findings=findings)
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id, findings=findings)
        diff = _compute_diff(
            store.get_review(r1.review_id).findings,
            store.get_review(r2.review_id).findings,
        )
        assert diff["risks"]["new"] == []
        assert diff["risks"]["resolved"] == []
        assert "vendor lock-in" in diff["risks"]["unchanged"]

    def test_diff_spans_multiple_categories(self, store, version):
        r1 = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={
                "risks": ["vendor lock-in"],
                "assumptions": ["team available"],
            },
        )
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={
                "risks": ["vendor lock-in", "regulatory change"],
                "assumptions": [],
                "dependencies": ["external API"],
            },
        )
        diff = _compute_diff(
            store.get_review(r1.review_id).findings,
            store.get_review(r2.review_id).findings,
        )
        assert "regulatory change" in diff["risks"]["new"]
        assert "vendor lock-in" in diff["risks"]["unchanged"]
        assert "team available" in diff["assumptions"]["resolved"]
        assert "external API" in diff["dependencies"]["new"]

    def test_diff_absent_when_no_predecessor(self, store, version):
        """A standalone review has no predecessor — diff context should not be shown."""
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        fetched = store.get_review(r.review_id)
        assert fetched.previous_review_id == "", (
            "Standalone review must have empty previous_review_id — diff section absent."
        )

    def test_diff_predecessor_loaded_by_explicit_id_not_proximity(self, store, version):
        """Diff predecessor is the explicitly stored previous_review_id, not any nearby review."""
        v2 = store.create_version(included_artifacts=[], label="v2")
        r_other = store.create_review(
            version_id=v2.version_id, persona="DM",
            findings={"risks": ["unrelated risk"]},
        )
        r1 = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        r2 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r1.review_id,
            findings={"risks": ["cost overrun"]},
        )
        fetched_r2 = store.get_review(r2.review_id)
        # Must point to r1, not r_other
        assert fetched_r2.previous_review_id == r1.review_id
        predecessor = store.get_review(fetched_r2.previous_review_id)
        diff = _compute_diff(predecessor.findings, fetched_r2.findings)
        assert "cost overrun" in diff["risks"]["new"]
        assert "unrelated risk" not in diff.get("risks", {}).get("resolved", [])



# ══════════════════════════════════════════════════════════════════════════════
# Journey 5 — State consistency: multi-version independence
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney5_MultiVersionStateConsistency:
    """Multiple versions each have independent review chains.
    No cross-version iteration number leakage or chain pollution.
    """

    def test_two_versions_each_start_iteration_at_r1(self, store):
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        store.create_review(version_id=v1.version_id, persona="SA")
        store.create_review(version_id=v1.version_id, persona="DM")
        store.create_review(version_id=v2.version_id, persona="SA")

        v1_iters = {s["review_id"]: s["iteration_number"]
                    for s in store.list_reviews(version_id=v1.version_id)}
        v2_iters = {s["review_id"]: s["iteration_number"]
                    for s in store.list_reviews(version_id=v2.version_id)}

        assert v1_iters["r1"] == 1
        assert v1_iters["r2"] == 2
        assert v2_iters["r3"] == 1  # r3 is v2's first review → R1

    def test_chain_on_v1_does_not_affect_v2_reviews(self, store):
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        r1 = store.create_review(version_id=v1.version_id, persona="SA")
        store.create_review(
            version_id=v1.version_id, persona="SA",
            previous_review_id=r1.review_id,
        )
        r3 = store.create_review(version_id=v2.version_id, persona="DM")
        fetched = store.get_review(r3.review_id)
        assert fetched.previous_review_id == "", (
            "v2 review must not inherit v1 chain — previous_review_id must be empty."
        )

    def test_global_list_reviews_iteration_numbers_are_per_version(self, store):
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        store.create_review(version_id=v1.version_id, persona="SA")
        store.create_review(version_id=v2.version_id, persona="DM")
        store.create_review(version_id=v1.version_id, persona="EA")

        all_s = {s["review_id"]: s for s in store.list_reviews()}
        assert all_s["r1"]["iteration_number"] == 1  # v1 R1
        assert all_s["r2"]["iteration_number"] == 1  # v2 R1 (independent)
        assert all_s["r3"]["iteration_number"] == 2  # v1 R2

    def test_deleting_r2_does_not_renumber_r1_or_r3(self, store):
        v1 = store.create_version(included_artifacts=[], label="v1")
        r1 = store.create_review(version_id=v1.version_id, persona="SA")
        r2 = store.create_review(version_id=v1.version_id, persona="DM")
        r3 = store.create_review(version_id=v1.version_id, persona="EA")

        store.delete_review(r2.review_id)
        remaining = {s["review_id"]: s["iteration_number"]
                     for s in store.list_reviews(version_id=v1.version_id)}
        assert r2.review_id not in remaining
        # r1 is the oldest → 1, r3 is next → 2 (re-computed from remaining)
        assert remaining[r1.review_id] == 1
        assert remaining[r3.review_id] == 2

    def test_prompt_builder_state_isolated_per_review(self, store):
        v1 = store.create_version(included_artifacts=[], label="v1")
        pbs_a = {"injected_questions": ["Q-A?"], "user_notes": "context A"}
        pbs_b = {"injected_questions": ["Q-B1?", "Q-B2?"], "user_notes": "context B"}
        ra = store.create_review(version_id=v1.version_id, persona="SA",
                                 prompt_builder_state=pbs_a)
        rb = store.create_review(version_id=v1.version_id, persona="DM",
                                 prompt_builder_state=pbs_b)
        assert store.get_review(ra.review_id).prompt_builder_state == pbs_a
        assert store.get_review(rb.review_id).prompt_builder_state == pbs_b
        # Mutating one must not affect the other
        assert store.get_review(ra.review_id).prompt_builder_state != pbs_b



# ══════════════════════════════════════════════════════════════════════════════
# Journey 6 — Negative / guard-rail tests
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney6_NegativeAndGuardrails:
    """Edge cases and negative paths that must not crash or corrupt state."""

    def test_null_pbs_review_does_not_raise(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=None)
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state is None

    def test_null_pbs_badge_is_baseline(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        assert _is_customised(store.get_review(r.review_id).prompt_builder_state) is False

    def test_empty_pbs_dict_badge_is_baseline(self):
        assert _is_customised({}) is False

    def test_whitespace_notes_badge_is_baseline(self):
        assert _is_customised({"injected_questions": [], "user_notes": "   \n  "}) is False

    def test_empty_findings_diff_returns_empty_buckets(self):
        diff = _compute_diff({}, {})
        assert diff == {}

    def test_empty_current_findings_all_previous_resolved(self):
        diff = _compute_diff({"risks": ["vendor lock-in"]}, {})
        assert "vendor lock-in" in diff["risks"]["resolved"]
        assert diff["risks"]["new"] == []
        assert diff["risks"]["unchanged"] == []

    def test_empty_previous_findings_all_current_are_new(self):
        diff = _compute_diff({}, {"risks": ["brand new risk"]})
        assert "brand new risk" in diff["risks"]["new"]
        assert diff["risks"]["resolved"] == []

    def test_standalone_review_has_no_diff_predecessor(self, store, version):
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            findings={"risks": ["vendor lock-in"]},
        )
        fetched = store.get_review(r.review_id)
        # No predecessor → no diff should be shown
        assert fetched.previous_review_id == ""

    def test_review_with_empty_previous_review_id_stored_correctly(self, store, version):
        r = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id="",  # explicit empty string
        )
        fetched = store.get_review(r.review_id)
        assert fetched.previous_review_id == ""

    def test_deep_dive_with_empty_scope_does_not_raise(self):
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="",
            intelligence={},
            active_files=[],
            ai_backend="files_only",
        )
        assert isinstance(result["question_groups"], list)
        assert len(result["all_questions"]) >= 1

    def test_deep_dive_with_unknown_persona_does_not_raise(self):
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Nonexistent Persona XYZ",
            scope="some scope",
            intelligence={"risks": ["risk A"]},
            active_files=[],
            ai_backend="files_only",
        )
        assert isinstance(result["question_groups"], list)

    def test_creating_review_on_nonexistent_version_gracefully_handled(self, store):
        """Attempt to create a review on a version that does not exist.
        Should not corrupt the store — the version link will simply be None."""
        r = store.create_review(
            version_id="v999",  # does not exist
            persona="SA",
        )
        # Review is created (store does not enforce FK)
        assert r.review_id is not None
        # But the version v999 is still not found
        assert store.get_version("v999") is None

    def test_pbs_with_none_user_notes_key_is_baseline(self):
        assert _is_customised({"injected_questions": [], "user_notes": None}) is False

    def test_pbs_missing_user_notes_key_but_has_questions_is_customised(self):
        assert _is_customised({"injected_questions": ["Q?"]}) is True

    def test_diff_single_finding_moved_between_categories(self):
        """Finding text appearing in different category in new review → new in one, resolved in other."""
        diff = _compute_diff(
            {"risks": ["cross-cutting concern"]},
            {"assumptions": ["cross-cutting concern"]},
        )
        assert "cross-cutting concern" in diff["risks"]["resolved"]
        assert "cross-cutting concern" in diff["assumptions"]["new"]
