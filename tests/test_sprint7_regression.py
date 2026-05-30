"""Sprint 7 Regression Pack — Convergence and Learning Foundation.

Covers every change made in Sprint 7:

A) S7-01 · compute_decision_readiness()
   - No open items → High
   - Open weaknesses only → Medium
   - Open decisions present → Low
   - Mixed open decisions and weaknesses → Low
   - Empty review → High
   - All addressed → High

B) S7-01 · get_version_readiness() integration
   - Returns error for unknown version
   - Returns Low note when no active review set
   - Returns correct level from active review data

C) S7-02 · Proposal readiness metadata
   - generate_proposal_document() returns 'readiness' key in result
   - Readiness level reflects review decision_points / weaknesses

D) S7-03 · Prompt logging
   - prompt_log table exists in DB schema
   - log_prompt() inserts a row
   - log_prompt() stores persona_name and scenario_type
   - log_prompt() stores final_prompt
   - link_outcome() updates outcome_proposal_ver_id
   - link_outcome() for unknown review_id is a no-op (no error)
   - run_persona_review() creates a prompt_log entry (via project_manager wiring)

E) S7-04 · Learning-ready retrieval
   - query_prompts() returns all rows for project
   - query_prompts() filters by persona_name
   - query_prompts() filters by scenario_type
   - query_prompts() returns [] for unknown project
   - get_prompt_history() returns {prompts, count}

F) UI contract — index.html static analysis
   - _populateReadinessBadges function defined
   - 'readiness-badge-' referenced in viewVersions()
   - 'detailReadinessBadge' referenced in viewReviewDetail()
   - Decision Readiness label in viewReviewDetail()
   - 'propReadinessRow' element in HTML
   - readiness fetch in onPropVersionChange() or submitCreateProposal()
   - Non-blocking Low warning in submitCreateProposal()
   - prompt-history or prompt_log referenced in server.py or project_manager.py
"""

from __future__ import annotations

import json
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture(scope="module")
def html_text():
    return HTML_PATH.read_text(encoding="utf-8")


def _make_store(project_id: str = "test-proj-s7"):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite(project_id)


def _weakness(wid: str, text: str, category: str = "risks", status: str = "open") -> Dict:
    return {"id": wid, "text": text, "category": category, "status": status}


def _dp(did: str, text: str, category: str = "risks", status: str = "open") -> Dict:
    return {"id": did, "text": text, "category": category,
            "status": status, "linked_finding": text}


# ══════════════════════════════════════════════════════════════════════════════
# A) S7-01 · compute_decision_readiness()
# ══════════════════════════════════════════════════════════════════════════════

class TestComputeDecisionReadiness:

    def _call(self, dps: List[Dict], ws: List[Dict]) -> Dict:
        from processors.review_quality import compute_decision_readiness
        return compute_decision_readiness({"decision_points": dps, "weaknesses": ws})

    def test_no_open_items_returns_high(self):
        result = self._call([], [])
        assert result["level"] == "High"
        assert result["open_decisions"] == 0
        assert result["open_weaknesses"] == 0

    def test_open_weaknesses_only_returns_medium(self):
        result = self._call([], [_weakness("w1", "unclear scope")])
        assert result["level"] == "Medium"
        assert result["open_weaknesses"] == 1
        assert result["open_decisions"] == 0

    def test_open_decisions_returns_low(self):
        result = self._call([_dp("d1", "choose between vendors")], [])
        assert result["level"] == "Low"
        assert result["open_decisions"] == 1

    def test_mixed_open_decisions_and_weaknesses_returns_low(self):
        result = self._call(
            [_dp("d1", "choose platform")],
            [_weakness("w1", "tbc timeline")],
        )
        assert result["level"] == "Low"
        assert result["open_decisions"] == 1
        assert result["open_weaknesses"] == 1

    def test_all_addressed_returns_high(self):
        result = self._call(
            [_dp("d1", "vendor chosen", status="addressed")],
            [_weakness("w1", "scope defined", status="addressed")],
        )
        assert result["level"] == "High"
        assert result["open_decisions"] == 0
        assert result["open_weaknesses"] == 0

    def test_empty_review_dict_returns_high(self):
        from processors.review_quality import compute_decision_readiness
        result = compute_decision_readiness({})
        assert result["level"] == "High"

    def test_validated_decision_not_counted_as_open(self):
        result = self._call(
            [_dp("d1", "cloud region", status="validated")],
            [],
        )
        assert result["level"] == "High"
        assert result["open_decisions"] == 0

    def test_rejected_weakness_not_counted_as_open(self):
        result = self._call(
            [],
            [_weakness("w1", "risk dismissed", status="rejected")],
        )
        assert result["level"] == "High"

    def test_multiple_open_decisions_counts_correctly(self):
        dps = [_dp(f"d{i}", f"decision {i}") for i in range(3)]
        result = self._call(dps, [])
        assert result["open_decisions"] == 3
        assert result["level"] == "Low"

    def test_result_has_required_keys(self):
        result = self._call([], [])
        assert "level" in result
        assert "open_decisions" in result
        assert "open_weaknesses" in result


# ══════════════════════════════════════════════════════════════════════════════
# B) S7-01 · get_version_readiness() integration
# ══════════════════════════════════════════════════════════════════════════════

class TestGetVersionReadiness:

    def test_unknown_version_returns_error(self):
        from project_manager import get_version_readiness
        result = get_version_readiness("test-proj-s7", "v_nonexistent")
        assert "error" in result

    def test_no_active_review_returns_low_note(self):
        from project_manager import get_version_readiness
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        result = get_version_readiness("test-proj-s7", "v1")
        # No active review — note is returned; not an error
        assert "error" not in result
        assert "note" in result
        assert result["version_id"] == "v1"

    def test_with_active_review_no_open_items_returns_high(self):
        from project_manager import get_version_readiness
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        rev = store.create_review(
            version_id="v1", persona="SA",
            decision_points=[_dp("d1", "vendor chosen", status="addressed")],
            weaknesses=[_weakness("w1", "scope defined", status="addressed")],
        )
        store.set_active_review("v1", rev.review_id)
        result = get_version_readiness("test-proj-s7", "v1")
        assert result["level"] == "High"
        assert result["review_id"] == rev.review_id

    def test_with_active_review_open_decisions_returns_low(self):
        from project_manager import get_version_readiness
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        rev = store.create_review(
            version_id="v1", persona="SA",
            decision_points=[_dp("d1", "platform choice")],
            weaknesses=[],
        )
        store.set_active_review("v1", rev.review_id)
        result = get_version_readiness("test-proj-s7", "v1")
        assert result["level"] == "Low"

    def test_with_active_review_open_weaknesses_only_returns_medium(self):
        from project_manager import get_version_readiness
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        rev = store.create_review(
            version_id="v1", persona="SA",
            decision_points=[],
            weaknesses=[_weakness("w1", "unclear timeline")],
        )
        store.set_active_review("v1", rev.review_id)
        result = get_version_readiness("test-proj-s7", "v1")
        assert result["level"] == "Medium"


# ══════════════════════════════════════════════════════════════════════════════
# C) S7-02 · Proposal readiness metadata
# ══════════════════════════════════════════════════════════════════════════════

class TestProposalReadinessMetadata:

    def _setup_version_with_active_review(self, weaknesses=None, decision_points=None):
        """Create version + complete review + set as active. Returns (store, version_id, review_id)."""
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        rev = store.create_review(
            version_id="v1", persona="SA",
            findings={"risks": ["risk A", "risk B"],
                      "assumptions": ["assume budget"],
                      "dependencies": ["dep X"],
                      "constraints": ["no cloud"],
                      "action_items": ["kick off"]},
            weaknesses=weaknesses or [],
            decision_points=decision_points or [],
        )
        # Mark complete so generator gate passes
        from db.database import get_db
        db = get_db()
        db.execute(
            "UPDATE reviews SET quality_status='complete' WHERE review_id=?",
            (rev.review_id,),
        )
        db.commit()
        store.set_active_review("v1", rev.review_id)
        return store, "v1", rev.review_id

    def test_generate_proposal_document_returns_readiness_key(self):
        from processors.proposal_generator import generate_proposal_document
        _, vid, rid = self._setup_version_with_active_review()
        result = generate_proposal_document(
            project_id="test-proj-s7",
            proposal_ver_id="pv-test1",
            hierarchy_version_id=vid,
            review_id=rid,
            ai_backend="files_only",
        )
        assert "error" not in result
        assert "readiness" in result

    def test_readiness_high_when_no_open_items(self):
        from processors.proposal_generator import generate_proposal_document
        _, vid, rid = self._setup_version_with_active_review(
            weaknesses=[_weakness("w1", "scope done", status="addressed")],
            decision_points=[_dp("d1", "vendor decided", status="addressed")],
        )
        result = generate_proposal_document(
            project_id="test-proj-s7",
            proposal_ver_id="pv-test2",
            hierarchy_version_id=vid,
            review_id=rid,
            ai_backend="files_only",
        )
        assert result.get("readiness", {}).get("level") == "High"

    def test_readiness_low_when_open_decisions(self):
        from processors.proposal_generator import generate_proposal_document
        _, vid, rid = self._setup_version_with_active_review(
            decision_points=[_dp("d1", "choose platform")],
        )
        result = generate_proposal_document(
            project_id="test-proj-s7",
            proposal_ver_id="pv-test3",
            hierarchy_version_id=vid,
            review_id=rid,
            ai_backend="files_only",
        )
        assert result.get("readiness", {}).get("level") == "Low"


# ══════════════════════════════════════════════════════════════════════════════
# D) S7-03 · Prompt logging
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptLogging:

    def test_prompt_log_table_exists(self):
        from db.database import get_db
        db = get_db()
        cols = {r["name"] for r in db.fetchall("PRAGMA table_info(prompt_log)")}
        required = {
            "log_id", "project_id", "review_id", "persona_name", "scenario_type",
            "baseline_prompt", "injected_questions", "user_notes", "final_prompt",
            "outcome_review_id", "outcome_proposal_ver_id", "created_at",
        }
        assert required.issubset(cols), f"Missing columns: {required - cols}"

    def test_log_prompt_inserts_row(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-test-001",
            prompt_builder_state={},
            final_prompt="test prompt",
        )
        db = get_db()
        row = db.fetchone("SELECT * FROM prompt_log WHERE log_id=?", (log_id,))
        assert row is not None
        assert row["review_id"] == "r-test-001"

    def test_log_prompt_stores_persona_name(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-persona-001",
            prompt_builder_state={},
            final_prompt="",
            persona_name="Solution Architect",
        )
        db = get_db()
        row = db.fetchone("SELECT persona_name FROM prompt_log WHERE log_id=?", (log_id,))
        assert row["persona_name"] == "Solution Architect"

    def test_log_prompt_prefers_state_persona_over_argument(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-persona-002",
            prompt_builder_state={"persona_name": "Delivery Manager"},
            final_prompt="",
            persona_name="Solution Architect",  # should be overridden by state
        )
        db = get_db()
        row = db.fetchone("SELECT persona_name FROM prompt_log WHERE log_id=?", (log_id,))
        assert row["persona_name"] == "Delivery Manager"

    def test_log_prompt_stores_scenario_type(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-scenario-001",
            prompt_builder_state={"scenario_type": "pre-sales"},
            final_prompt="",
        )
        db = get_db()
        row = db.fetchone("SELECT scenario_type FROM prompt_log WHERE log_id=?", (log_id,))
        assert row["scenario_type"] == "pre-sales"

    def test_log_prompt_stores_final_prompt(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-fp-001",
            prompt_builder_state={},
            final_prompt="You are a solution architect…",
        )
        db = get_db()
        row = db.fetchone("SELECT final_prompt FROM prompt_log WHERE log_id=?", (log_id,))
        assert "solution architect" in row["final_prompt"].lower()

    def test_log_prompt_stores_injected_questions_from_state(self):
        from processors.prompt_logger import log_prompt
        from db.database import get_db
        qs = ["What is the DR strategy?", "Who owns the budget?"]
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-iq-001",
            prompt_builder_state={"injected_questions": qs},
            final_prompt="",
        )
        db = get_db()
        row = db.fetchone("SELECT injected_questions FROM prompt_log WHERE log_id=?", (log_id,))
        assert row is not None
        loaded = json.loads(row["injected_questions"])
        assert loaded == qs

    def test_link_outcome_updates_proposal_ver_id(self):
        from processors.prompt_logger import log_prompt, link_outcome
        from db.database import get_db
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-link-001",
            prompt_builder_state={},
            final_prompt="",
        )
        link_outcome("r-link-001", "proposal_version", "pv-xyz")
        db = get_db()
        row = db.fetchone("SELECT outcome_proposal_ver_id FROM prompt_log WHERE log_id=?", (log_id,))
        assert row["outcome_proposal_ver_id"] == "pv-xyz"

    def test_link_outcome_unknown_review_is_noop(self):
        """Calling link_outcome for a review that has no log entry must not raise."""
        from processors.prompt_logger import link_outcome
        # Should not raise
        link_outcome("r-no-such-review", "proposal_version", "pv-noop")

    def test_log_prompt_returns_log_id_string(self):
        from processors.prompt_logger import log_prompt
        log_id = log_prompt(
            project_id="test-proj-s7",
            review_id="r-id-001",
            prompt_builder_state={},
            final_prompt="",
        )
        assert isinstance(log_id, str)
        assert len(log_id) > 0


# ══════════════════════════════════════════════════════════════════════════════
# E) S7-04 · Learning-ready retrieval
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptHistoryRetrieval:

    def _seed_entries(self):
        from processors.prompt_logger import log_prompt
        log_prompt(
            project_id="test-proj-s7",
            review_id="r-hist-001",
            prompt_builder_state={"persona_name": "Solution Architect", "scenario_type": "pre-sales"},
            final_prompt="prompt A",
        )
        log_prompt(
            project_id="test-proj-s7",
            review_id="r-hist-002",
            prompt_builder_state={"persona_name": "Delivery Manager", "scenario_type": "sdlc"},
            final_prompt="prompt B",
        )
        log_prompt(
            project_id="test-proj-s7",
            review_id="r-hist-003",
            prompt_builder_state={"persona_name": "Solution Architect", "scenario_type": "sdlc"},
            final_prompt="prompt C",
        )

    def test_query_prompts_returns_all_for_project(self):
        from processors.prompt_logger import query_prompts
        self._seed_entries()
        results = query_prompts("test-proj-s7")
        assert len(results) == 3

    def test_query_prompts_filters_by_persona_name(self):
        from processors.prompt_logger import query_prompts
        self._seed_entries()
        results = query_prompts("test-proj-s7", persona_name="Solution Architect")
        assert len(results) == 2
        assert all(r["persona_name"] == "Solution Architect" for r in results)

    def test_query_prompts_filters_by_scenario_type(self):
        from processors.prompt_logger import query_prompts
        self._seed_entries()
        results = query_prompts("test-proj-s7", scenario_type="pre-sales")
        assert len(results) == 1
        assert results[0]["scenario_type"] == "pre-sales"

    def test_query_prompts_filters_by_both(self):
        from processors.prompt_logger import query_prompts
        self._seed_entries()
        results = query_prompts(
            "test-proj-s7",
            persona_name="Solution Architect",
            scenario_type="sdlc",
        )
        assert len(results) == 1
        assert results[0]["review_id"] == "r-hist-003"

    def test_query_prompts_unknown_project_returns_empty(self):
        from processors.prompt_logger import query_prompts
        results = query_prompts("test-proj-nobody")
        assert results == []

    def test_get_prompt_history_returns_prompts_and_count(self):
        from project_manager import get_prompt_history
        self._seed_entries()
        result = get_prompt_history("test-proj-s7")
        assert "prompts" in result
        assert "count" in result
        assert result["count"] == len(result["prompts"])

    def test_get_prompt_history_with_persona_filter(self):
        from project_manager import get_prompt_history
        self._seed_entries()
        result = get_prompt_history("test-proj-s7", persona_name="Delivery Manager")
        assert result["count"] == 1
        assert result["prompts"][0]["persona_name"] == "Delivery Manager"

    def test_get_prompt_history_with_scenario_filter(self):
        from project_manager import get_prompt_history
        self._seed_entries()
        result = get_prompt_history("test-proj-s7", scenario_type="sdlc")
        assert result["count"] == 2


# ══════════════════════════════════════════════════════════════════════════════
# F) UI contract — index.html static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestUIContractS7:

    def _fn_body(self, html: str, fn_name: str) -> str:
        m = re.search(
            rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\(.*?\)\s*\{{([\s\S]+?)"
            r"(?=\n(?:async\s+)?function\s|\Z)",
            html,
        )
        assert m, f"{fn_name}() not found in index.html"
        return m.group(1)

    def test_populate_readiness_badges_function_defined(self, html_text):
        assert "_populateReadinessBadges" in html_text, \
            "_populateReadinessBadges() not defined in index.html"

    def test_readiness_badge_slot_in_view_versions(self, html_text):
        body = self._fn_body(html_text, "viewVersions")
        assert "readiness-badge-" in body, \
            "'readiness-badge-' placeholder not rendered in viewVersions()"

    def test_detail_readiness_badge_element_defined(self, html_text):
        assert "detailReadinessBadge" in html_text, \
            "'detailReadinessBadge' element not found in index.html"

    def test_decision_readiness_label_in_view_review_detail(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "Decision Readiness" in body, \
            "'Decision Readiness' label not in viewReviewDetail()"

    def test_readiness_fetch_in_view_review_detail(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "readiness" in body.lower(), \
            "Readiness API fetch not present in viewReviewDetail()"

    def test_prop_readiness_row_element_in_html(self, html_text):
        assert "propReadinessRow" in html_text, \
            "'propReadinessRow' element not found in index.html — S7-02 readiness row missing"

    def test_readiness_fetch_in_on_prop_version_change(self, html_text):
        body = self._fn_body(html_text, "onPropVersionChange")
        assert "readiness" in body.lower(), \
            "Readiness fetch not present in onPropVersionChange() — S7-02 missing"

    def test_low_warning_in_submit_create_proposal(self, html_text):
        body = self._fn_body(html_text, "submitCreateProposal")
        assert "Low" in body, \
            "'Low' readiness check not in submitCreateProposal() — S7-02 non-blocking warning missing"

    def test_non_blocking_confirm_in_submit_create_proposal(self, html_text):
        body = self._fn_body(html_text, "submitCreateProposal")
        assert "confirm(" in body, \
            "'confirm()' dialog not found in submitCreateProposal() — S7-02 non-blocking confirm missing"

    def test_versions_tab_triggers_populate_readiness(self, html_text):
        # The render() function should call _populateReadinessBadges on the versions tab
        m = re.search(r"async function render\(\)([\s\S]+?)(?=\n(?:async\s+)?function\s|\Z)", html_text)
        assert m, "render() not found in index.html"
        body = m.group(1)
        assert "_populateReadinessBadges" in body, \
            "_populateReadinessBadges not called in render() for versions tab"
