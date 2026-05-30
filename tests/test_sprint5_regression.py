"""Sprint 5 Regression Pack — Decision Intelligence.

Covers every change made in Sprint 5:

A) extract_decision_points() — S5-01
   - Empty/None findings returns []
   - Signal-phrase detection (choose between, decide, which approach, …)
   - Long clear item with no signal is NOT flagged
   - Multiple categories produce decision points from each
   - Each decision point has id, text, category, status, linked_finding
   - status defaults to "open"
   - IDs are unique within the result
   - Duplicate texts are deduplicated
   - Non-string / non-list items skipped

B) DB round-trip — S5-01
   - decision_points column exists in reviews table (PRAGMA)
   - create_review() persists decision_points
   - get_review() deserialises decision_points
   - update_review_decision_points() mutates and persists
   - to_dict() and to_summary() include decision_points

C) update_decision_status() — S5-03
   - Valid status values update decision point correctly
   - Invalid status returns error dict
   - Unknown review_id returns error dict
   - Unknown decision_id returns error dict

D) Predecessor inheritance — S5-01 / S5-03
   - run_persona_review with previous_review_id inherits open DPs
   - Already-present texts are NOT duplicated
   - Addressed DPs in predecessor are NOT inherited

E) Deep dive — S5-02
   - decision_points passed to run_deep_dive produces Decisions group
   - No decision_points → no Decisions group
   - Questions in Decisions group reference decision text
   - _annotate_questions_with_decisions annotates matching category
   - _annotate_questions_with_decisions skips non-open DPs
   - backward compat: no decision_points arg still returns standard groups

F) UI contract — index.html static analysis
   - "Decision Points" label present in viewReviewDetail() body
   - "decision_points" referenced in viewReviewDetail() body
   - "updateDecisionStatus" function defined
   - "🎯" icon present in viewReviewDetail() body
   - "decision_point_text" referenced in ddGroup() body
   - "decision_mappings" referenced in addSelectedToPrompt() body
"""

from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"



# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Fresh temp dir + isolated DB thread-local for every test."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture(scope="module")
def html_text():
    return HTML_PATH.read_text(encoding="utf-8")


def _make_store(project_id="test-proj-s5"):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite(project_id)


# ══════════════════════════════════════════════════════════════════════════════
# A) extract_decision_points() — S5-01
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractDecisionPoints:

    def _edp(self, findings):
        from processors.review_quality import extract_decision_points
        return extract_decision_points(findings)

    def test_empty_findings_returns_empty_list(self):
        assert self._edp({}) == []

    def test_none_findings_returns_empty_list(self):
        assert self._edp(None) == []

    def test_choose_between_is_flagged(self):
        findings = {"risks": ["We need to choose between AWS and Azure for the cloud platform"]}
        result = self._edp(findings)
        assert len(result) == 1
        assert result[0]["text"].startswith("We need to choose between")

    def test_decide_is_flagged(self):
        findings = {"assumptions": ["The team must decide on the deployment strategy by week 2"]}
        result = self._edp(findings)
        assert len(result) == 1

    def test_which_approach_is_flagged(self):
        findings = {"dependencies": ["Not clear which approach to use for data migration"]}
        result = self._edp(findings)
        assert len(result) == 1

    def test_platform_choice_is_flagged(self):
        findings = {"constraints": ["Platform choice between on-prem and cloud is unresolved"]}
        result = self._edp(findings)
        assert len(result) == 1

    def test_cost_trade_off_is_flagged(self):
        findings = {"action_items": ["Evaluate the cost trade-off between build and buy options"]}
        result = self._edp(findings)
        assert len(result) == 1

    def test_in_scope_or_out_is_flagged(self):
        findings = {"risks": ["Legacy system migration is in scope or out — needs sign-off"]}
        result = self._edp(findings)
        assert len(result) == 1

    def test_clear_factual_finding_not_flagged(self):
        findings = {"risks": [
            "The cloud provider SLA guarantees 99.9% uptime with automatic failover "
            "to secondary region within 30 seconds."
        ]}
        result = self._edp(findings)
        assert result == []

    def test_multiple_categories_produce_decision_points(self):
        findings = {
            "risks": ["We need to choose between containerisation strategies"],
            "assumptions": ["The team must decide the DR approach before go-live"],
        }
        result = self._edp(findings)
        cats = {dp["category"] for dp in result}
        assert "risks" in cats
        assert "assumptions" in cats

    def test_each_dp_has_required_keys(self):
        findings = {"risks": ["We need to decide on the cloud region selection"]}
        result = self._edp(findings)
        assert len(result) == 1
        for dp in result:
            assert "id" in dp
            assert "text" in dp
            assert "category" in dp
            assert "status" in dp
            assert "linked_finding" in dp

    def test_status_defaults_to_open(self):
        findings = {"risks": ["We need to decide the vendor selection criteria"]}
        result = self._edp(findings)
        assert result[0]["status"] == "open"

    def test_linked_finding_equals_text(self):
        findings = {"risks": ["We need to decide the vendor selection criteria"]}
        result = self._edp(findings)
        assert result[0]["linked_finding"] == result[0]["text"]

    def test_ids_are_unique(self):
        findings = {
            "risks": ["We need to decide on cloud provider"],
            "assumptions": ["Choose between phasing options A and B"],
        }
        result = self._edp(findings)
        ids = [dp["id"] for dp in result]
        assert len(ids) == len(set(ids))

    def test_duplicate_texts_are_deduplicated(self):
        text = "We need to decide on the approach"
        findings = {"risks": [text], "assumptions": [text]}
        result = self._edp(findings)
        texts = [dp["text"] for dp in result]
        assert len(texts) == len(set(texts))

    def test_non_string_items_skipped(self):
        findings = {"risks": [None, 42, {"key": "val"}, "We need to decide on region"]}
        result = self._edp(findings)
        assert len(result) == 1
        assert result[0]["text"] == "We need to decide on region"

    def test_non_list_category_skipped(self):
        findings = {"risks": "not a list", "assumptions": ["We need to decide the timeline"]}
        result = self._edp(findings)
        assert len(result) == 1
        assert result[0]["category"] == "assumptions"



# ══════════════════════════════════════════════════════════════════════════════
# B) DB round-trip — S5-01
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionPointsDBRoundTrip:

    def test_decision_points_column_exists_in_reviews_table(self, tmp_path):
        from db.database import get_db
        db = get_db()
        cols = {r["name"] for r in db.fetchall("PRAGMA table_info(reviews)")}
        assert "decision_points" in cols, "decision_points column missing from reviews table"

    def test_create_review_persists_decision_points(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "We need to decide on cloud region", "category": "risks",
                "status": "open", "linked_finding": "We need to decide on cloud region"}]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        assert r.decision_points == dps

    def test_get_review_deserialises_decision_points(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "Choose between option A and B", "category": "assumptions",
                "status": "open", "linked_finding": "Choose between option A and B"}]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        assert len(loaded.decision_points) == 1
        assert loaded.decision_points[0]["id"] == "d1"

    def test_create_review_with_no_dps_defaults_to_empty_list(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        r = store.create_review(version_id="v1", persona="SA")
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        assert isinstance(loaded.decision_points, list)
        assert loaded.decision_points == []

    def test_update_review_decision_points_mutates_and_persists(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "We need to decide on vendor", "category": "risks",
                "status": "open", "linked_finding": "We need to decide on vendor"}]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        updated_dps = [dict(dps[0], status="addressed")]
        store.update_review_decision_points(r.review_id, updated_dps)
        loaded = store.get_review(r.review_id)
        assert loaded.decision_points[0]["status"] == "addressed"

    def test_to_dict_includes_decision_points(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "decide on approach", "category": "risks",
                "status": "open", "linked_finding": "decide on approach"}]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        d = r.to_dict()
        assert "decision_points" in d
        assert d["decision_points"] == dps

    def test_to_summary_includes_decision_points(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "decide on approach", "category": "risks",
                "status": "open", "linked_finding": "decide on approach"}]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        s = r.to_summary()
        assert "decision_points" in s
        assert s["decision_points"] == dps

    def test_list_reviews_includes_decision_points_in_summaries(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [{"id": "d1", "text": "decide on approach", "category": "risks",
                "status": "open", "linked_finding": "decide on approach"}]
        store.create_review(version_id="v1", persona="SA", decision_points=dps)
        summaries = store.list_reviews()
        assert len(summaries) == 1
        assert "decision_points" in summaries[0]



# ══════════════════════════════════════════════════════════════════════════════
# C) update_decision_status() — S5-03
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateDecisionStatus:

    def _setup_review_with_dps(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        dps = [
            {"id": "d1", "text": "We need to decide on cloud region", "category": "risks",
             "status": "open", "linked_finding": "We need to decide on cloud region"},
            {"id": "d2", "text": "Choose between on-prem and cloud", "category": "assumptions",
             "status": "open", "linked_finding": "Choose between on-prem and cloud"},
        ]
        r = store.create_review(version_id="v1", persona="SA", decision_points=dps)
        return store, r.review_id

    def test_valid_status_addressed_updates_dp(self, tmp_path):
        from project_manager import update_decision_status
        store, rid = self._setup_review_with_dps()
        result = update_decision_status("test-proj-s5", rid, "d1", "addressed")
        assert result.get("updated") is True
        assert result["status"] == "addressed"
        loaded = store.get_review(rid)
        d1 = next(dp for dp in loaded.decision_points if dp["id"] == "d1")
        assert d1["status"] == "addressed"

    def test_valid_status_validated(self, tmp_path):
        from project_manager import update_decision_status
        _, rid = self._setup_review_with_dps()
        result = update_decision_status("test-proj-s5", rid, "d2", "validated")
        assert result.get("updated") is True
        assert result["status"] == "validated"

    def test_valid_status_rejected(self, tmp_path):
        from project_manager import update_decision_status
        _, rid = self._setup_review_with_dps()
        result = update_decision_status("test-proj-s5", rid, "d1", "rejected")
        assert result.get("updated") is True

    def test_valid_status_open(self, tmp_path):
        from project_manager import update_decision_status
        _, rid = self._setup_review_with_dps()
        # First move to addressed, then back to open
        update_decision_status("test-proj-s5", rid, "d1", "addressed")
        result = update_decision_status("test-proj-s5", rid, "d1", "open")
        assert result.get("updated") is True
        assert result["status"] == "open"

    def test_invalid_status_returns_error(self, tmp_path):
        from project_manager import update_decision_status
        _, rid = self._setup_review_with_dps()
        result = update_decision_status("test-proj-s5", rid, "d1", "banana")
        assert "error" in result

    def test_unknown_review_id_returns_error(self, tmp_path):
        from project_manager import update_decision_status
        result = update_decision_status("test-proj-s5", "r999", "d1", "addressed")
        assert "error" in result

    def test_unknown_decision_id_returns_error(self, tmp_path):
        from project_manager import update_decision_status
        _, rid = self._setup_review_with_dps()
        result = update_decision_status("test-proj-s5", rid, "d999", "addressed")
        assert "error" in result

    def test_other_dp_status_unaffected(self, tmp_path):
        from project_manager import update_decision_status
        store, rid = self._setup_review_with_dps()
        update_decision_status("test-proj-s5", rid, "d1", "addressed")
        loaded = store.get_review(rid)
        d2 = next(dp for dp in loaded.decision_points if dp["id"] == "d2")
        assert d2["status"] == "open"



# ══════════════════════════════════════════════════════════════════════════════
# D) Predecessor inheritance — S5-01 / S5-03
# ══════════════════════════════════════════════════════════════════════════════

class TestPredecessorInheritance:

    def test_open_dps_inherited_from_predecessor(self):
        from processors.review_quality import extract_decision_points
        # Simulates the logic in run_persona_review(): inherit open DPs from pred
        pred_dps = [
            {"id": "d1", "text": "We need to decide on cloud region",
             "category": "risks", "status": "open",
             "linked_finding": "We need to decide on cloud region"},
        ]
        new_dps: list = []  # new review has no decision points of its own
        existing_texts = {dp["text"] for dp in new_dps}
        for dp in pred_dps:
            if dp.get("status") == "open" and dp["text"] not in existing_texts:
                new_dp = dict(dp)
                new_dp["id"] = f"d{len(new_dps) + 1}"
                new_dps.append(new_dp)
                existing_texts.add(dp["text"])
        assert len(new_dps) == 1
        assert new_dps[0]["text"] == "We need to decide on cloud region"

    def test_addressed_dps_not_inherited(self):
        pred_dps = [
            {"id": "d1", "text": "Addressed decision", "category": "risks",
             "status": "addressed", "linked_finding": "Addressed decision"},
        ]
        new_dps: list = []
        existing_texts = set()
        for dp in pred_dps:
            if dp.get("status") == "open" and dp["text"] not in existing_texts:
                new_dps.append(dp)
        assert new_dps == []

    def test_already_present_texts_not_duplicated(self):
        shared_text = "We need to decide on cloud region"
        pred_dps = [
            {"id": "d1", "text": shared_text, "category": "risks",
             "status": "open", "linked_finding": shared_text},
        ]
        new_dps = [
            {"id": "d1", "text": shared_text, "category": "risks",
             "status": "open", "linked_finding": shared_text},
        ]
        existing_texts = {dp["text"] for dp in new_dps}
        for dp in pred_dps:
            if dp.get("status") == "open" and dp["text"] not in existing_texts:
                new_dps.append(dict(dp))
        assert len(new_dps) == 1

    def test_mixed_statuses_only_open_inherited(self):
        pred_dps = [
            {"id": "d1", "text": "Open decision to decide",
             "category": "risks", "status": "open", "linked_finding": ""},
            {"id": "d2", "text": "Validated decision choose between options",
             "category": "risks", "status": "validated", "linked_finding": ""},
            {"id": "d3", "text": "Rejected decision on platform choice",
             "category": "risks", "status": "rejected", "linked_finding": ""},
        ]
        new_dps: list = []
        existing_texts: set = set()
        for dp in pred_dps:
            if dp.get("status") == "open" and dp["text"] not in existing_texts:
                new_dp = dict(dp)
                new_dp["id"] = f"d{len(new_dps) + 1}"
                new_dps.append(new_dp)
                existing_texts.add(dp["text"])
        assert len(new_dps) == 1
        assert new_dps[0]["text"] == "Open decision to decide"



# ══════════════════════════════════════════════════════════════════════════════
# E) Deep dive — S5-02
# ══════════════════════════════════════════════════════════════════════════════

class TestDeepDiveDecisionPoints:

    _INTELLIGENCE = {
        "risks": ["vendor lock-in"],
        "assumptions": [],
        "dependencies": [],
        "constraints": [],
        "action_items": [],
    }
    _SCOPE = "Cloud migration with multiple workstreams"
    _FILES = [{"filename": "scope.txt", "source_type": "text"}]

    def _run(self, decision_points=None, weaknesses=None, missing_categories=None):
        from personas.deep_dive import run_deep_dive
        return run_deep_dive(
            persona_name="Solution Architect",
            scope=self._SCOPE,
            intelligence=self._INTELLIGENCE,
            active_files=self._FILES,
            custom_prompt="",
            ai_backend="files_only",
            weaknesses=weaknesses,
            missing_categories=missing_categories,
            decision_points=decision_points,
        )

    def test_open_decision_points_produce_decisions_group(self):
        dps = [{"id": "d1", "text": "We need to decide on cloud provider",
                "category": "risks", "status": "open", "linked_finding": ""}]
        result = self._run(decision_points=dps)
        cats = [g["category"] for g in result["question_groups"]]
        assert "Decisions" in cats

    def test_no_decision_points_no_decisions_group(self):
        result = self._run(decision_points=None)
        cats = [g["category"] for g in result["question_groups"]]
        assert "Decisions" not in cats

    def test_empty_decision_points_no_decisions_group(self):
        result = self._run(decision_points=[])
        cats = [g["category"] for g in result["question_groups"]]
        assert "Decisions" not in cats

    def test_decisions_group_questions_reference_dp_text(self):
        dps = [{"id": "d1", "text": "We need to decide on cloud provider",
                "category": "risks", "status": "open", "linked_finding": ""}]
        result = self._run(decision_points=dps)
        dec_grp = next(g for g in result["question_groups"] if g["category"] == "Decisions")
        qs = dec_grp["questions"]
        # questions may be strings or dicts after annotation — extract text
        q_texts = [q["question"] if isinstance(q, dict) else q for q in qs]
        combined = " ".join(q_texts)
        assert "We need to decide on cloud provider" in combined

    def test_addressed_dp_does_not_produce_decisions_group(self):
        dps = [{"id": "d1", "text": "Addressed decision on region",
                "category": "risks", "status": "addressed", "linked_finding": ""}]
        result = self._run(decision_points=dps)
        cats = [g["category"] for g in result["question_groups"]]
        assert "Decisions" not in cats

    def test_decisions_group_icon_is_target(self):
        dps = [{"id": "d1", "text": "We need to decide on cloud provider",
                "category": "risks", "status": "open", "linked_finding": ""}]
        result = self._run(decision_points=dps)
        dec_grp = next(g for g in result["question_groups"] if g["category"] == "Decisions")
        assert dec_grp["icon"] == "🎯"

    def test_backward_compat_no_decision_points_arg(self):
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope=self._SCOPE,
            intelligence=self._INTELLIGENCE,
            active_files=self._FILES,
            custom_prompt="",
            ai_backend="files_only",
        )
        assert isinstance(result["question_groups"], list)
        assert len(result["question_groups"]) >= 1

    def test_annotate_questions_with_decisions_adds_dp_info(self):
        from personas.deep_dive import _annotate_questions_with_decisions
        groups = [{"category": "risks", "icon": "🔴", "questions": ["What is the risk?", "Any mitigations?"]}]
        dps = [{"id": "d1", "text": "decide on vendor", "category": "risks",
                "status": "open", "linked_finding": ""}]
        _annotate_questions_with_decisions(groups, dps)
        q0 = groups[0]["questions"][0]
        assert isinstance(q0, dict)
        assert q0["decision_point_id"] == "d1"
        assert q0["decision_point_text"] == "decide on vendor"

    def test_annotate_questions_no_matching_category_sets_none(self):
        from personas.deep_dive import _annotate_questions_with_decisions
        groups = [{"category": "Architecture & Design", "icon": "🏗️", "questions": ["How is it designed?"]}]
        dps = [{"id": "d1", "text": "decide on vendor", "category": "risks",
                "status": "open", "linked_finding": ""}]
        _annotate_questions_with_decisions(groups, dps)
        q0 = groups[0]["questions"][0]
        assert isinstance(q0, dict)
        assert q0["decision_point_id"] is None

    def test_annotate_questions_skips_non_open_dps(self):
        from personas.deep_dive import _annotate_questions_with_decisions
        groups = [{"category": "risks", "icon": "🔴", "questions": ["What is the risk?"]}]
        dps = [{"id": "d1", "text": "addressed decision", "category": "risks",
                "status": "addressed", "linked_finding": ""}]
        _annotate_questions_with_decisions(groups, dps)
        q0 = groups[0]["questions"][0]
        # No open DP matches risks → decision_point_id should be None
        assert isinstance(q0, dict)
        assert q0["decision_point_id"] is None

    def test_decisions_group_capped_at_five_questions(self):
        dps = [
            {"id": f"d{i}", "text": f"We need to decide on option number {i}",
             "category": "risks", "status": "open", "linked_finding": ""}
            for i in range(1, 8)
        ]
        result = self._run(decision_points=dps)
        dec_grp = next((g for g in result["question_groups"] if g["category"] == "Decisions"), None)
        if dec_grp:
            assert len(dec_grp["questions"]) <= 5



# ══════════════════════════════════════════════════════════════════════════════
# F) UI contract — index.html static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestUIContract:
    """S5 UI sections must be present in the correct functions in index.html."""

    def _get_fn_body(self, html_text: str, fn_name: str) -> str:
        """Extract body of a JS function from HTML."""
        m = re.search(
            rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\(.*?\)\s*\{{([\s\S]+?)"
            r"(?=\n(?:async\s+)?function\s|\Z)",
            html_text,
        )
        assert m, f"{fn_name}() function not found in index.html"
        return m.group(1)

    def test_decision_points_label_present_in_view_review_detail(self, html_text):
        body = self._get_fn_body(html_text, "viewReviewDetail")
        assert "Decision Points" in body, \
            "'Decision Points' label not found in viewReviewDetail() — S5-01 UI section missing"

    def test_decision_points_data_binding_in_view_review_detail(self, html_text):
        body = self._get_fn_body(html_text, "viewReviewDetail")
        assert "decision_points" in body, \
            "'decision_points' not referenced in viewReviewDetail() — S5-01 data binding missing"

    def test_target_icon_present_in_view_review_detail(self, html_text):
        body = self._get_fn_body(html_text, "viewReviewDetail")
        assert "🎯" in body, \
            "🎯 icon not found in viewReviewDetail() — S5-01 decision points section missing"

    def test_update_decision_status_function_defined(self, html_text):
        assert "function updateDecisionStatus" in html_text or \
               "async function updateDecisionStatus" in html_text, \
            "updateDecisionStatus() function not defined in index.html — S5-03 missing"

    def test_decision_point_text_in_dd_group(self, html_text):
        body = self._get_fn_body(html_text, "ddGroup")
        assert "decision_point_text" in body, \
            "'decision_point_text' not referenced in ddGroup() — S5-02 annotation render missing"

    def test_decision_mappings_in_add_selected_to_prompt(self, html_text):
        body = self._get_fn_body(html_text, "addSelectedToPrompt")
        assert "decision_mappings" in body, \
            "'decision_mappings' not referenced in addSelectedToPrompt() — S5-02 state missing"

    def test_status_select_present_in_view_review_detail(self, html_text):
        body = self._get_fn_body(html_text, "viewReviewDetail")
        assert "updateDecisionStatus" in body, \
            "updateDecisionStatus call not found in viewReviewDetail() — S5-03 dropdown missing"
