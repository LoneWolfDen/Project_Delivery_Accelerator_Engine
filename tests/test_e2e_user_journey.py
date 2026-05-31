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



# ══════════════════════════════════════════════════════════════════════════════
# Journey 7 — S4 Weakness Intelligence: baseline → weaknesses → SME → improved review
# ══════════════════════════════════════════════════════════════════════════════

class TestJourney7_S4WeaknessIntelligence:
    """Full S4 vertical slice.

    Scenario:
      Step 1. Run baseline review — findings contain weak/unclear items.
      Step 2. Weakness extraction identifies weak findings automatically.
      Step 3. Missing category detection flags absent standard categories.
      Step 4. Gap-aware SME generates questions that reference weaknesses and
              missing categories.
      Step 5. User selects SME questions → prompt_builder_state assembled.
      Step 6. Run second (improved) review chained to baseline —
              carries pbs with selected questions.
      Step 7. Verify: second review is improved (weaknesses reduced) OR
              clarified (missing categories addressed).

    Invariants asserted throughout:
    - previous_review_id chain intact (S1).
    - prompt_builder_state persisted (S2).
    - Gap questions reference specific weakness/category text (S3/S4).
    - No duplicate questions (S4).
    - Second review has fewer or zero weaknesses than first (improvement signal).
    """

    def test_step1_baseline_review_with_weak_findings(self, store, version):
        """Step 1 — baseline review created with findings that include weak items."""
        r1 = store.create_review(
            version_id=version.version_id,
            persona="Solution Architect",
            findings={
                "risks": [
                    "unclear integration approach between legacy and new system",
                    "TBC — vendor contract not finalised",
                ],
                "assumptions": ["team available from week 1"],
                # dependencies, constraints, action_items intentionally absent
            },
        )
        assert r1.previous_review_id == ""
        assert r1.prompt_builder_state is None
        # Baseline weaknesses field is empty by default (computed later)
        assert r1.weaknesses == []

    def test_step2_weakness_extraction_identifies_weak_findings(self, store, version):
        """Step 2 — extract_weaknesses() detects signal phrases and short items."""
        from processors.review_quality import extract_weaknesses
        findings = {
            "risks": [
                "unclear integration approach between legacy and new system",
                "TBC — vendor contract not finalised",
            ],
            "assumptions": ["team available from week 1"],
        }
        weaknesses = extract_weaknesses(findings)
        assert len(weaknesses) >= 1
        texts = [w["text"] for w in weaknesses]
        # 'unclear' and 'TBC' must be detected
        assert any("unclear" in t.lower() for t in texts), (
            "Weakness with 'unclear' signal not detected"
        )
        assert any("tbc" in t.lower() for t in texts), (
            "Weakness with 'TBC' signal not detected"
        )
        # Each weakness has required keys
        for w in weaknesses:
            assert {"id", "text", "category", "status"} <= w.keys()
            assert w["status"] == "open"

    def test_step3_missing_category_detection(self, store, version):
        """Step 3 — compute_missing_categories() flags absent standard categories."""
        from processors.review_quality import compute_missing_categories, STANDARD_CATEGORIES
        findings = {
            "risks": ["unclear risk"],
            "assumptions": ["team available from week 1"],
            # missing: dependencies, constraints, action_items
        }
        missing = compute_missing_categories(findings)
        assert "dependencies" in missing
        assert "constraints" in missing
        assert "action_items" in missing
        # Present categories not in missing list
        assert "risks" not in missing
        assert "assumptions" not in missing
        # Only standard category names returned
        for cat in missing:
            assert cat in STANDARD_CATEGORIES

    def test_step4_gap_aware_sme_generates_specific_questions(self, store, version):
        """Step 4 — deep dive with weaknesses + missing_categories produces
        a 'Gaps & Weaknesses' group with specific, non-generic questions."""
        from personas.deep_dive import run_deep_dive
        weaknesses = [
            {"id": "w1", "text": "unclear integration approach between legacy and new system",
             "category": "risks", "status": "open"},
            {"id": "w2", "text": "TBC — vendor contract not finalised",
             "category": "risks", "status": "open"},
        ]
        missing_categories = ["dependencies", "constraints", "action_items"]

        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration for healthcare platform. 6-month timeline. AWS target.",
            intelligence={
                "risks": ["unclear integration approach", "TBC vendor contract"],
                "assumptions": ["team available from week 1"],
                "dependencies": [],
                "constraints": [],
                "action_items": [],
            },
            active_files=[{"filename": "scope.txt", "source_type": "text"}],
            ai_backend="files_only",
            weaknesses=weaknesses,
            missing_categories=missing_categories,
        )

        # Gaps & Weaknesses group must be present
        cats = [g["category"] for g in result["question_groups"]]
        assert "Gaps & Weaknesses" in cats, (
            "'Gaps & Weaknesses' group not found — gap-aware SME not triggered"
        )

        gap_grp = next(g for g in result["question_groups"]
                       if g["category"] == "Gaps & Weaknesses")

        # Questions must reference specific weakness or missing category text
        qs_text = " ".join(gap_grp["questions"])
        has_weakness_ref = (
            "unclear integration approach" in qs_text
            or "vendor contract" in qs_text
            or "tbc" in qs_text.lower()
        )
        has_category_ref = any(cat in qs_text for cat in missing_categories)
        assert has_weakness_ref or has_category_ref, (
            "Gap questions do not reference specific weakness text or missing category names — "
            f"questions: {gap_grp['questions']}"
        )

        # No question is generic filler (< 20 chars)
        for q in gap_grp["questions"]:
            assert len(q.strip()) >= 20, f"Question too short (vague): {q!r}"

        # Scope completeness is present and in range
        assert 0 <= result["scope_completeness"] <= 100

    def test_step4_no_duplicate_questions_in_sme_output(self, store, version):
        """Step 4 — no duplicate questions across the entire deep dive output."""
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration",
            intelligence={"risks": ["TBC vendor lock-in"], "assumptions": [],
                          "dependencies": [], "constraints": [], "action_items": []},
            active_files=[],
            ai_backend="files_only",
            weaknesses=[{"id": "w1", "text": "TBC vendor lock-in",
                         "category": "risks", "status": "open"}],
            missing_categories=["dependencies"],
        )
        all_qs = [q.lower().strip() for q in result["all_questions"]]
        duplicates = [q for q in all_qs if all_qs.count(q) > 1]
        assert duplicates == [], (
            f"Duplicate questions found in SME output: {list(set(duplicates))}"
        )

    def test_step5_user_selects_questions_assembles_pbs(self, store, version):
        """Step 5 — user selects gap questions; valid pbs assembled."""
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration for healthcare platform.",
            intelligence={"risks": ["unclear integration approach"], "assumptions": [],
                          "dependencies": [], "constraints": [], "action_items": []},
            active_files=[{"filename": "scope.txt", "source_type": "text"}],
            ai_backend="files_only",
            weaknesses=[{"id": "w1", "text": "unclear integration approach",
                         "category": "risks", "status": "open"}],
            missing_categories=["dependencies"],
        )

        # User picks up to 3 questions from all_questions
        selected = result["all_questions"][:3]
        assert len(selected) >= 1

        # Strip [Category] prefix to get clean question text (as S3-02 specifies)
        clean_selected = [
            q.split("] ", 1)[1] if "] " in q else q
            for q in selected
        ]

        pbs = {
            "injected_questions": clean_selected,
            "user_notes": "Vendor must be confirmed before week 3",
        }

        # Badge logic: customised
        has_q = bool(pbs.get("injected_questions") or [])
        assert has_q is True

        # All selected questions are non-empty
        for q in pbs["injected_questions"]:
            assert q.strip() != ""

    def test_step6_second_review_chained_carries_pbs(self, store, version):
        """Step 6 — second review is chained to R1 and carries pbs with selected questions."""
        from processors.review_quality import extract_weaknesses
        from personas.deep_dive import run_deep_dive

        # R1: baseline
        r1_findings = {
            "risks": [
                "unclear integration approach between legacy and new system",
                "TBC — vendor contract not finalised",
            ],
            "assumptions": ["team available from week 1"],
        }
        weaknesses = extract_weaknesses(r1_findings)
        r1 = store.create_review(
            version_id=version.version_id,
            persona="Solution Architect",
            findings=r1_findings,
            weaknesses=weaknesses,
        )

        # SME
        dd = run_deep_dive(
            persona_name="Solution Architect",
            scope=version.scope,
            intelligence={**r1_findings, "dependencies": [], "constraints": [],
                          "action_items": []},
            active_files=[{"filename": "scope.txt", "source_type": "text"}],
            ai_backend="files_only",
            weaknesses=weaknesses,
            missing_categories=["dependencies", "constraints", "action_items"],
        )

        # Select first gap question
        selected = dd["all_questions"][:2]
        pbs = {"injected_questions": selected, "user_notes": "Vendor confirmed AWS"}

        # R2: improved review chained to R1
        r2_findings = {
            "risks": [
                "integration approach documented — API-first confirmed by vendor",
            ],
            "assumptions": ["team available from week 1"],
            "dependencies": ["vendor API team — owner confirmed"],
            "constraints": ["no downtime allowed during cutover"],
            "action_items": ["schedule integration review by week 2"],
        }
        r2_weaknesses = extract_weaknesses(r2_findings)
        r2 = store.create_review(
            version_id=version.version_id,
            persona="Solution Architect",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
            findings=r2_findings,
            weaknesses=r2_weaknesses,
        )

        # Chain intact
        fetched_r2 = store.get_review(r2.review_id)
        assert fetched_r2.previous_review_id == r1.review_id

        # pbs persisted
        assert fetched_r2.prompt_builder_state["injected_questions"] == selected

        # Iteration labels
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id[r1.review_id] == 1
        assert by_id[r2.review_id] == 2

    def test_step7_second_review_improved_weaknesses_reduced(self, store, version):
        """Step 7 — second review has fewer weaknesses than the baseline.

        Improvement signal: the clarified/resolved findings contain no signal
        phrases AND are long enough (≥ 8 words) to avoid the short-item flag,
        so extract_weaknesses() returns a smaller list than for the baseline.
        """
        from processors.review_quality import extract_weaknesses

        r1_findings = {
            "risks": [
                "unclear integration approach between legacy and new cloud system",
                "TBC — vendor contract has not been finalised yet",
                "pending security review with no timeline confirmed",
            ],
            "assumptions": ["assumed infrastructure will be available before project start"],
        }
        # R2 findings: same categories, all items ≥ 8 words, no signal phrases
        r2_findings = {
            "risks": [
                "Integration approach fully documented and agreed with the vendor team in writing",
                "Vendor contract has been signed and all commercial terms are confirmed",
                "Security review completed successfully and certificate of compliance issued",
            ],
            "assumptions": [
                "Infrastructure has been provisioned and confirmed available from week one onward"
            ],
            "dependencies": [
                "Vendor API team owner identified and committed to delivery timeline"
            ],
            "constraints": [
                "No downtime is permitted during the planned production cutover window"
            ],
            "action_items": [
                "Schedule and run the integration smoke test before the end of week two"
            ],
        }

        w1 = extract_weaknesses(r1_findings)
        w2 = extract_weaknesses(r2_findings)

        assert len(w2) < len(w1), (
            f"Expected second review to have fewer weaknesses than baseline. "
            f"Baseline: {len(w1)}, second: {len(w2)}\n"
            f"  Baseline weaknesses: {[x['text'] for x in w1]}\n"
            f"  Second weaknesses:   {[x['text'] for x in w2]}"
        )

    def test_step7_second_review_clarified_missing_categories_addressed(self, store, version):
        """Step 7 (alt) — second review addresses missing categories from baseline."""
        from processors.review_quality import compute_missing_categories

        r1_findings = {
            "risks": ["unclear risk"],
            "assumptions": ["team available"],
            # missing: dependencies, constraints, action_items
        }
        r2_findings = {
            "risks": ["documented risk — owner assigned"],
            "assumptions": ["team available and confirmed by HR"],
            "dependencies": ["vendor API team"],
            "constraints": ["no downtime during migration"],
            "action_items": ["schedule kickoff by end of week 1"],
        }

        missing_after_r1 = compute_missing_categories(r1_findings)
        missing_after_r2 = compute_missing_categories(r2_findings)

        assert len(missing_after_r2) < len(missing_after_r1), (
            f"Expected second review to have fewer missing categories. "
            f"After R1: {missing_after_r1}, after R2: {missing_after_r2}"
        )
        assert missing_after_r2 == [], (
            f"Second review should have no missing categories, but got: {missing_after_r2}"
        )

    def test_full_s4_journey_state_consistency(self, store, version):
        """Combined integrity check: after the full S4 journey, all stored state
        is consistent — no field bleed, no corruption, no missing keys."""
        from processors.review_quality import extract_weaknesses, compute_missing_categories
        from personas.deep_dive import run_deep_dive

        # R1
        r1_findings = {
            "risks": ["TBC — vendor contract", "unclear NFR targets"],
            "assumptions": ["budget assumed approved"],
        }
        w1 = extract_weaknesses(r1_findings)
        mc1 = compute_missing_categories(r1_findings)
        r1 = store.create_review(
            version_id=version.version_id, persona="Solution Architect",
            findings=r1_findings, weaknesses=w1,
        )

        # SME
        dd = run_deep_dive(
            persona_name="Solution Architect",
            scope=version.scope,
            intelligence={**r1_findings, "dependencies": [], "constraints": [],
                          "action_items": []},
            active_files=[],
            ai_backend="files_only",
            weaknesses=w1,
            missing_categories=mc1,
        )
        pbs = {
            "injected_questions": dd["all_questions"][:2],
            "user_notes": "Vendor confirmed, budget approved",
        }

        # R2: all items ≥ 8 words, no signal phrases — verified improvement
        r2_findings = {
            "risks": [
                "All identified risks have been fully documented with owner and mitigation plan assigned"
            ],
            "assumptions": [
                "Budget has been formally approved by the finance committee and is confirmed"
            ],
            "dependencies": [
                "Vendor has been confirmed and API integration contract is signed by both parties"
            ],
            "constraints": [
                "No production changes are allowed during the scheduled external audit window"
            ],
            "action_items": [
                "Finalise and publish the NFR document with sign-off before the end of sprint two"
            ],
        }
        w2 = extract_weaknesses(r2_findings)
        r2 = store.create_review(
            version_id=version.version_id, persona="Solution Architect",
            previous_review_id=r1.review_id,
            prompt_builder_state=pbs,
            findings=r2_findings,
            weaknesses=w2,
        )

        # Assertions
        fetched_r1 = store.get_review(r1.review_id)
        fetched_r2 = store.get_review(r2.review_id)

        # Chain
        assert fetched_r2.previous_review_id == r1.review_id
        assert fetched_r1.previous_review_id == ""

        # pbs
        assert fetched_r2.prompt_builder_state is not None
        assert fetched_r1.prompt_builder_state is None

        # Weaknesses improved
        assert len(fetched_r2.weaknesses) <= len(fetched_r1.weaknesses)

        # Missing categories improved
        mc_r2 = compute_missing_categories(fetched_r2.findings)
        assert len(mc_r2) < len(mc1)

        # Iteration labels
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id[r1.review_id] == 1
        assert by_id[r2.review_id] == 2

        # to_summary() has all S4 keys
        s1 = fetched_r1.to_summary()
        s2 = fetched_r2.to_summary()
        for key in ("weaknesses", "missing_categories", "prompt_builder_state",
                    "previous_review_id", "iteration_number"):
            assert key in s1, f"Key '{key}' missing from R1 to_summary()"
            assert key in s2, f"Key '{key}' missing from R2 to_summary()"
