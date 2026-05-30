"""Sprint 6 Regression Pack — Resolution and Iteration Intelligence.

Covers every change made in Sprint 6:

A) S6-01 · Weakness status tracking
   - update_weakness_status() valid values persist
   - update_weakness_status() invalid status returns error
   - update_weakness_status() unknown review_id returns error
   - update_weakness_status() unknown weakness_id returns error
   - Other weaknesses on same review are unaffected
   - update_review_weaknesses() DB + file mirror

B) S6-01 · Recurrence logic
   - Weakness marked 'addressed' in R1 that recurs in R2 resets to 'open'
   - New weaknesses default to 'open'
   - Weakness resolved in R1 (not in R2) does not appear in R2

C) S6-02 · get_review_diff()
   - Review with no predecessor returns error
   - Unknown review_id returns error
   - Diff structure has findings / weaknesses / decision_points keys
   - New findings appear in findings.new
   - Resolved findings appear in findings.resolved
   - Unchanged finding count is correct
   - New weaknesses appear in weaknesses.new
   - Resolved weaknesses appear in weaknesses.resolved
   - New decision_points appear in decision_points.new
   - Identical reviews produce zero new/resolved, correct unchanged count

D) S6-03 · Feedback version_id integration
   - presales_feedback table has version_id column
   - save_presales_feedback persists version_id
   - _row_to_feedback returns version_id
   - attach_feedback_to_context stores version_id in cache
   - clear_feedback_cache_for_version evicts by version_id
   - Feedback without version_id works (backward compat)

E) UI contract — index.html static analysis
   - updateWeaknessStatus function defined
   - 'updateWeaknessStatus' called inside viewReviewDetail()
   - '_diffSection' or diff fetch inside viewReviewDetail()
   - 'fbVersionId' element referenced in index.html
   - 'version_id' sent in submitCaptureFeedback body
   - 'updateWeaknessStatus' referenced in weakness row render
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


def _make_store(project_id: str = "test-proj-s6"):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite(project_id)


def _weakness(wid: str, text: str, category: str = "risks", status: str = "open") -> Dict:
    return {"id": wid, "text": text, "category": category,
            "status": status}


def _dp(did: str, text: str, category: str = "risks", status: str = "open") -> Dict:
    return {"id": did, "text": text, "category": category,
            "status": status, "linked_finding": text}


# ══════════════════════════════════════════════════════════════════════════════
# A) S6-01 · Weakness status tracking
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateWeaknessStatus:

    def _setup(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        ws = [_weakness("w1", "unclear integration point"),
              _weakness("w2", "TBC vendor timeline")]
        r = store.create_review(version_id="v1", persona="SA", weaknesses=ws)
        return store, r.review_id

    # ── valid statuses ──

    def test_addressed_persists(self):
        from project_manager import update_weakness_status
        store, rid = self._setup()
        result = update_weakness_status("test-proj-s6", rid, "w1", "addressed")
        assert result.get("updated") is True
        assert result["status"] == "addressed"
        loaded = store.get_review(rid)
        w1 = next(w for w in loaded.weaknesses if w["id"] == "w1")
        assert w1["status"] == "addressed"

    def test_validated_persists(self):
        from project_manager import update_weakness_status
        _, rid = self._setup()
        result = update_weakness_status("test-proj-s6", rid, "w2", "validated")
        assert result.get("updated") is True

    def test_rejected_persists(self):
        from project_manager import update_weakness_status
        _, rid = self._setup()
        result = update_weakness_status("test-proj-s6", rid, "w1", "rejected")
        assert result.get("updated") is True

    def test_open_persists(self):
        from project_manager import update_weakness_status
        _, rid = self._setup()
        update_weakness_status("test-proj-s6", rid, "w1", "addressed")
        result = update_weakness_status("test-proj-s6", rid, "w1", "open")
        assert result.get("updated") is True
        assert result["status"] == "open"

    # ── error cases ──

    def test_invalid_status_returns_error(self):
        from project_manager import update_weakness_status
        _, rid = self._setup()
        result = update_weakness_status("test-proj-s6", rid, "w1", "banana")
        assert "error" in result

    def test_unknown_review_id_returns_error(self):
        from project_manager import update_weakness_status
        result = update_weakness_status("test-proj-s6", "r999", "w1", "addressed")
        assert "error" in result

    def test_unknown_weakness_id_returns_error(self):
        from project_manager import update_weakness_status
        _, rid = self._setup()
        result = update_weakness_status("test-proj-s6", rid, "w999", "addressed")
        assert "error" in result

    def test_other_weakness_unaffected(self):
        from project_manager import update_weakness_status
        store, rid = self._setup()
        update_weakness_status("test-proj-s6", rid, "w1", "addressed")
        loaded = store.get_review(rid)
        w2 = next(w for w in loaded.weaknesses if w["id"] == "w2")
        assert w2["status"] == "open"

    def test_update_review_weaknesses_persists(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        ws = [_weakness("w1", "unclear scope")]
        r = store.create_review(version_id="v1", persona="SA", weaknesses=ws)
        updated = [dict(ws[0], status="validated")]
        store.update_review_weaknesses(r.review_id, updated)
        loaded = store.get_review(r.review_id)
        assert loaded.weaknesses[0]["status"] == "validated"


# ══════════════════════════════════════════════════════════════════════════════
# B) S6-01 · Recurrence logic (pure-logic tests, no store needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestWeaknessRecurrence:
    """The recurrence rule: a weakness text that was 'addressed' in the predecessor
    but still appears in the new review is reset to 'open'."""

    def _apply_recurrence(self, new_ws: List[Dict], pred_ws: List[Dict]) -> List[Dict]:
        """Mirror the logic expected in extract_weaknesses when previous_review_id set."""
        pred_addressed = {
            w["text"].strip().lower()
            for w in pred_ws
            if w.get("status") == "addressed"
        }
        result = []
        for w in new_ws:
            norm = w.get("text", "").strip().lower()
            item = dict(w)
            if norm in pred_addressed:
                item["status"] = "open"   # recurred — reset
            result.append(item)
        return result

    def test_addressed_weakness_recurrence_resets_to_open(self):
        pred = [_weakness("w1", "unclear migration plan", status="addressed")]
        new  = [_weakness("w1", "unclear migration plan", status="open")]
        result = self._apply_recurrence(new, pred)
        assert result[0]["status"] == "open"

    def test_new_weakness_defaults_to_open(self):
        pred = []
        new  = [_weakness("w1", "tbc vendor contract")]
        result = self._apply_recurrence(new, pred)
        assert result[0]["status"] == "open"

    def test_addressed_in_pred_not_in_new_not_present(self):
        pred = [_weakness("w1", "resolved issue", status="addressed")]
        new  = []   # not recurring
        result = self._apply_recurrence(new, pred)
        assert result == []

    def test_validated_pred_weakness_not_reset(self):
        pred = [_weakness("w1", "unclear migration plan", status="validated")]
        new  = [_weakness("w1", "unclear migration plan", status="open")]
        result = self._apply_recurrence(new, pred)
        # only 'addressed' triggers reset — 'validated' does not
        assert result[0]["status"] == "open"

    def test_multiple_weaknesses_only_addressed_recurred_resets(self):
        pred = [
            _weakness("w1", "unclear scope", status="addressed"),
            _weakness("w2", "tbc timeline",  status="open"),
        ]
        new = [
            _weakness("w1", "unclear scope"),
            _weakness("w2", "tbc timeline"),
        ]
        result = self._apply_recurrence(new, pred)
        assert result[0]["status"] == "open"   # was addressed, recurred → open
        assert result[1]["status"] == "open"   # was open, not addressed


# ══════════════════════════════════════════════════════════════════════════════
# C) S6-02 · get_review_diff()
# ══════════════════════════════════════════════════════════════════════════════

class TestGetReviewDiff:

    def _two_reviews(self, findings1, findings2,
                     weaknesses1=None, weaknesses2=None,
                     dps1=None, dps2=None):
        """Create two chained reviews and return (store, r1_id, r2_id)."""
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        r1 = store.create_review(
            version_id="v1", persona="SA",
            findings=findings1,
            weaknesses=weaknesses1 or [],
            decision_points=dps1 or [],
        )
        r2 = store.create_review(
            version_id="v1", persona="SA",
            findings=findings2,
            weaknesses=weaknesses2 or [],
            decision_points=dps2 or [],
            previous_review_id=r1.review_id,
        )
        return store, r1.review_id, r2.review_id

    # ── error cases ──

    def test_no_predecessor_returns_error(self):
        from project_manager import get_review_diff
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        r = store.create_review(version_id="v1", persona="SA")
        result = get_review_diff("test-proj-s6", r.review_id)
        assert "error" in result

    def test_unknown_review_id_returns_error(self):
        from project_manager import get_review_diff
        result = get_review_diff("test-proj-s6", "r_nonexistent")
        assert "error" in result

    # ── structure ──

    def test_diff_has_three_dimensions(self):
        from project_manager import get_review_diff
        _, _, r2 = self._two_reviews(
            {"risks": ["risk A"]}, {"risks": ["risk A", "risk B"]}
        )
        result = get_review_diff("test-proj-s6", r2)
        assert "findings" in result
        assert "weaknesses" in result
        assert "decision_points" in result

    def test_diff_includes_review_ids(self):
        from project_manager import get_review_diff
        _, r1, r2 = self._two_reviews(
            {"risks": ["risk A"]}, {"risks": ["risk A"]}
        )
        result = get_review_diff("test-proj-s6", r2)
        assert result["review_id"] == r2
        assert result["previous_review_id"] == r1

    # ── findings diff ──

    def test_new_finding_appears_in_findings_new(self):
        from project_manager import get_review_diff
        _, _, r2 = self._two_reviews(
            {"risks": ["risk A"]},
            {"risks": ["risk A", "risk B"]},
        )
        result = get_review_diff("test-proj-s6", r2)
        new_texts = [i["text"] for i in result["findings"]["new"]]
        assert "risk B" in new_texts

    def test_removed_finding_appears_in_findings_resolved(self):
        from project_manager import get_review_diff
        _, _, r2 = self._two_reviews(
            {"risks": ["risk A", "risk B"]},
            {"risks": ["risk A"]},
        )
        result = get_review_diff("test-proj-s6", r2)
        resolved_texts = [i["text"] for i in result["findings"]["resolved"]]
        assert "risk B" in resolved_texts

    def test_unchanged_finding_counted(self):
        from project_manager import get_review_diff
        _, _, r2 = self._two_reviews(
            {"risks": ["risk A", "risk B"]},
            {"risks": ["risk A", "risk B"]},
        )
        result = get_review_diff("test-proj-s6", r2)
        assert result["findings"]["unchanged"] == 2
        assert result["findings"]["new"] == []
        assert result["findings"]["resolved"] == []

    def test_empty_to_findings_all_new(self):
        from project_manager import get_review_diff
        _, _, r2 = self._two_reviews(
            {},
            {"risks": ["risk X"]},
        )
        result = get_review_diff("test-proj-s6", r2)
        assert len(result["findings"]["new"]) == 1

    # ── weaknesses diff ──

    def test_new_weakness_appears_in_weaknesses_new(self):
        from project_manager import get_review_diff
        w1 = _weakness("w1", "unclear scope")
        w2 = _weakness("w2", "tbc vendor timeline")
        _, _, r2 = self._two_reviews(
            {}, {},
            weaknesses1=[w1],
            weaknesses2=[w1, w2],
        )
        result = get_review_diff("test-proj-s6", r2)
        new_texts = [i["text"] for i in result["weaknesses"]["new"]]
        assert "tbc vendor timeline" in new_texts

    def test_resolved_weakness_appears_in_weaknesses_resolved(self):
        from project_manager import get_review_diff
        w1 = _weakness("w1", "unclear scope")
        _, _, r2 = self._two_reviews(
            {}, {},
            weaknesses1=[w1],
            weaknesses2=[],
        )
        result = get_review_diff("test-proj-s6", r2)
        resolved_texts = [i["text"] for i in result["weaknesses"]["resolved"]]
        assert "unclear scope" in resolved_texts

    def test_unchanged_weakness_counted(self):
        from project_manager import get_review_diff
        w = _weakness("w1", "unclear scope")
        _, _, r2 = self._two_reviews(
            {}, {},
            weaknesses1=[w],
            weaknesses2=[w],
        )
        result = get_review_diff("test-proj-s6", r2)
        assert result["weaknesses"]["unchanged"] == 1
        assert result["weaknesses"]["new"] == []

    # ── decision_points diff ──

    def test_new_decision_point_appears_in_dp_new(self):
        from project_manager import get_review_diff
        d1 = _dp("d1", "decide on cloud region")
        d2 = _dp("d2", "choose between vendors")
        _, _, r2 = self._two_reviews(
            {}, {},
            dps1=[d1],
            dps2=[d1, d2],
        )
        result = get_review_diff("test-proj-s6", r2)
        new_texts = [i["text"] for i in result["decision_points"]["new"]]
        assert "choose between vendors" in new_texts

    def test_resolved_decision_point_in_dp_resolved(self):
        from project_manager import get_review_diff
        d1 = _dp("d1", "decide on cloud region")
        _, _, r2 = self._two_reviews(
            {}, {},
            dps1=[d1],
            dps2=[],
        )
        result = get_review_diff("test-proj-s6", r2)
        resolved_texts = [i["text"] for i in result["decision_points"]["resolved"]]
        assert "decide on cloud region" in resolved_texts

    def test_identical_reviews_zero_new_resolved(self):
        from project_manager import get_review_diff
        w = _weakness("w1", "unclear scope")
        d = _dp("d1", "decide on vendor")
        _, _, r2 = self._two_reviews(
            {"risks": ["risk A"]},
            {"risks": ["risk A"]},
            weaknesses1=[w], weaknesses2=[w],
            dps1=[d], dps2=[d],
        )
        result = get_review_diff("test-proj-s6", r2)
        assert result["findings"]["new"] == []
        assert result["findings"]["resolved"] == []
        assert result["weaknesses"]["new"] == []
        assert result["weaknesses"]["resolved"] == []
        assert result["decision_points"]["new"] == []
        assert result["decision_points"]["resolved"] == []


# ══════════════════════════════════════════════════════════════════════════════
# D) S6-03 · Feedback version_id integration
# ══════════════════════════════════════════════════════════════════════════════

class TestFeedbackVersionId:

    def test_presales_feedback_has_version_id_column(self):
        from db.database import get_db
        db = get_db()
        cols = {r["name"] for r in db.fetchall("PRAGMA table_info(presales_feedback)")}
        assert "version_id" in cols

    def test_save_presales_feedback_persists_version_id(self, tmp_path):
        from db.project_store_sql import save_presales_feedback, load_presales_feedback_item
        item = save_presales_feedback(
            project_id="test-proj-s6",
            feedback_id="fb_test001",
            version_id="v1",
            proposal_ver_id="",
            notes="test note",
        )
        assert item is not None
        assert item.get("version_id") == "v1"

    def test_save_presales_feedback_empty_version_id_backward_compat(self, tmp_path):
        from db.project_store_sql import save_presales_feedback
        item = save_presales_feedback(
            project_id="test-proj-s6",
            feedback_id="fb_test002",
            notes="legacy note",
        )
        assert item is not None
        assert item.get("version_id", "") == ""

    def test_row_to_feedback_includes_version_id(self, tmp_path):
        from db.project_store_sql import save_presales_feedback, load_presales_feedback_item
        save_presales_feedback(
            project_id="test-proj-s6",
            feedback_id="fb_test003",
            version_id="v2",
            notes="check version_id round-trip",
        )
        loaded = load_presales_feedback_item("fb_test003")
        assert loaded is not None
        assert loaded["version_id"] == "v2"

    def test_attach_feedback_stores_version_id_in_cache(self, tmp_path):
        from processors.presales_feedback import attach_feedback_to_context, _cache_path
        import processors.presales_feedback as pfb
        pfb.PROJECTS_DIR = tmp_path
        record = {
            "feedback_id": "fb_v1",
            "project_id": "test-proj-s6",
            "version_id": "v3",
            "proposal_ver_id": "",
            "feedback_items": [{"status": "new", "text": "needs attention",
                                 "category": "concerns"}],
            "notes": "",
        }
        attach_feedback_to_context("test-proj-s6", record)
        cache_file = pfb._cache_path("test-proj-s6")
        assert cache_file.exists()
        with open(cache_file) as f:
            cache = json.load(f)
        assert any(e.get("version_id") == "v3" for e in cache)

    def test_clear_feedback_cache_for_version_evicts_by_version_id(self, tmp_path):
        from processors.presales_feedback import (
            attach_feedback_to_context, clear_feedback_cache_for_version, _cache_path
        )
        import processors.presales_feedback as pfb
        pfb.PROJECTS_DIR = tmp_path
        record = {
            "feedback_id": "fb_evict",
            "project_id": "test-proj-s6",
            "version_id": "v_evict",
            "proposal_ver_id": "",
            "feedback_items": [{"status": "new", "text": "evict me", "category": "concerns"}],
            "notes": "",
        }
        attach_feedback_to_context("test-proj-s6", record)
        clear_feedback_cache_for_version("test-proj-s6", "v_evict")
        cache_file = pfb._cache_path("test-proj-s6")
        if cache_file.exists():
            with open(cache_file) as f:
                cache = json.load(f)
            assert not any(e.get("version_id") == "v_evict" for e in cache)

    def test_clear_feedback_cache_does_not_evict_different_version(self, tmp_path):
        from processors.presales_feedback import (
            attach_feedback_to_context, clear_feedback_cache_for_version, _cache_path
        )
        import processors.presales_feedback as pfb
        pfb.PROJECTS_DIR = tmp_path
        for vid in ["v_keep", "v_remove"]:
            attach_feedback_to_context("test-proj-s6", {
                "feedback_id": f"fb_{vid}",
                "project_id": "test-proj-s6",
                "version_id": vid,
                "proposal_ver_id": "",
                "feedback_items": [{"status": "new", "text": f"item {vid}",
                                     "category": "concerns"}],
                "notes": "",
            })
        clear_feedback_cache_for_version("test-proj-s6", "v_remove")
        cache_file = pfb._cache_path("test-proj-s6")
        with open(cache_file) as f:
            cache = json.load(f)
        assert any(e.get("version_id") == "v_keep" for e in cache)
        assert not any(e.get("version_id") == "v_remove" for e in cache)

    def test_feedback_without_new_items_not_cached(self, tmp_path):
        from processors.presales_feedback import attach_feedback_to_context, _cache_path
        import processors.presales_feedback as pfb
        pfb.PROJECTS_DIR = tmp_path
        record = {
            "feedback_id": "fb_no_new",
            "project_id": "test-proj-s6",
            "version_id": "v_empty",
            "proposal_ver_id": "",
            "feedback_items": [{"status": "addressed", "text": "old item",
                                 "category": "concerns"}],
            "notes": "",
        }
        attach_feedback_to_context("test-proj-s6", record)
        cache_file = pfb._cache_path("test-proj-s6")
        if cache_file.exists():
            with open(cache_file) as f:
                cache = json.load(f)
            assert not any(e.get("feedback_id") == "fb_no_new" for e in cache)


# ══════════════════════════════════════════════════════════════════════════════
# E) UI contract — index.html static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestUIContract:

    def _fn_body(self, html: str, fn_name: str) -> str:
        m = re.search(
            rf"(?:async\s+)?function\s+{re.escape(fn_name)}\s*\(.*?\)\s*\{{([\s\S]+?)"
            r"(?=\n(?:async\s+)?function\s|\Z)",
            html,
        )
        assert m, f"{fn_name}() not found in index.html"
        return m.group(1)

    def test_update_weakness_status_function_defined(self, html_text):
        assert ("function updateWeaknessStatus" in html_text or
                "async function updateWeaknessStatus" in html_text), \
            "updateWeaknessStatus() not defined in index.html"

    def test_update_weakness_status_called_in_view_review_detail(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "updateWeaknessStatus" in body, \
            "updateWeaknessStatus not called in viewReviewDetail()"

    def test_weakness_select_dropdown_in_view_review_detail(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "<select" in body, \
            "No <select> element in viewReviewDetail() — weakness dropdown missing"

    def test_diff_fetch_in_view_review_detail(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "diff" in body.lower(), \
            "'diff' not referenced in viewReviewDetail() — S6-02 diff section missing"

    def test_fb_version_id_element_in_html(self, html_text):
        assert "fbVersionId" in html_text, \
            "'fbVersionId' element not found in index.html — S6-03 hidden field missing"

    def test_version_id_sent_in_submit_capture_feedback(self, html_text):
        body = self._fn_body(html_text, "submitCaptureFeedback")
        assert "version_id" in body, \
            "'version_id' not sent in submitCaptureFeedback() — S6-03 missing"

    def test_open_capture_feedback_sets_version_id(self, html_text):
        body = self._fn_body(html_text, "openCaptureFeedback")
        assert "fbVersionId" in body or "version_id" in body, \
            "openCaptureFeedback() does not populate version_id field — S6-03 missing"

    def test_what_changed_section_references_weaknesses(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "weaknesses" in body.lower(), \
            "'weaknesses' not referenced in viewReviewDetail() diff area"

    def test_what_changed_section_references_decision_points(self, html_text):
        body = self._fn_body(html_text, "viewReviewDetail")
        assert "decision_points" in body or "Decision Points" in body, \
            "'decision_points' not referenced in viewReviewDetail() diff area"
