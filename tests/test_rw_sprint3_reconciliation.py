"""RW Sprint 3 — Explicit Multi-Review Reconciliation.

Test sections:

A) Explicit review selection
   - anchor stored correctly
   - supplemental reviews stored correctly
   - anchor auto-included when missing from selected_review_ids
   - no auto latest-N behaviour

B) Reconciliation structure
   - consensus points generated when item present in all reviews
   - divergent points generated when item missing from some reviews
   - supplemental-only items captured in divergent
   - confirmed/open decisions split correctly
   - unresolved weaknesses (open only)
   - merged_findings covers all reviews

C) Reconciliation safety
   - duplicate-like items merged (not counted twice)
   - distinct items not collapsed
   - anchor-only mode works (no supplemental)
   - empty supplemental list works

D) Provenance retention
   - each consensus item carries source_reviews list
   - each divergent item carries present_in / absent_from
   - each decision carries source_reviews
   - each weakness carries source_reviews
   - missing artifact_refs do not break reconciliation
   - provenance_summary has one entry per review

E) Output model validation
   - ReconciliationOutput.to_dict() includes all required keys
   - counts match list lengths
   - reconciliation_id is non-empty
   - anchor_review_id preserved in output

F) Service + handler static analysis
   - services/reconciliation.py defines expected public functions
   - handlers/reconciliation.py defines expected handler functions
   - server.py has all four routes
   - project_manager.py re-exports all four functions

G) Frontend static analysis — api.js Sprint 3 additions
   - saveReconciliationSelection defined
   - fetchReconciliationSelection defined
   - runReconciliation defined
   - fetchReconciliation defined
   - all four exported on window.API
   - mock runReconciliation returns expected keys

H) Frontend static analysis — review_detail.js Sprint 3 additions
   - _renderReconciliationPanel defined
   - onToggleReconciliationPanel defined
   - onRunReconciliation defined
   - renderReview includes reconciliation panel call
   - new handlers exported

I) Frontend static analysis — CSS Sprint 3 classes
   - .rc-panel defined
   - .rc-panel-header defined
   - .rc-anchor-badge defined
   - .rc-supp-badge defined
   - .rc-result-card defined
   - .rc-item defined
   - .rc-review-list defined

J) Non-regression — Sprint 1 features still work
   - weakness notes still persist
   - artifact_refs field present on Review
   - Full Details renderReview still present in review_detail.js

K) Non-regression — Sprint 2 features still work
   - previous_review_id stored on iterated reviews
   - create_review_iteration defined in services/review.py
   - lineage banner rendered when previous_review_id present

L) Backward compatibility
   - old reviews without reconciliation fields render safely
   - get_reconciliation returns None when no output stored
   - get_reconciliation_selection returns None when no selection stored
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

BASE = Path(__file__).parent.parent

SERVICES_RECONCILIATION = BASE / "services" / "reconciliation.py"
HANDLERS_RECONCILIATION = BASE / "handlers" / "reconciliation.py"
SERVICES_REVIEW         = BASE / "services" / "review.py"
SERVER_PY               = BASE / "server.py"
PROJECT_MANAGER         = BASE / "project_manager.py"
API_JS                  = BASE / "static" / "v2" / "js" / "api.js"
REVIEW_DETAIL_JS        = BASE / "static" / "v2" / "js" / "review_detail.js"
COMPONENTS_CSS          = BASE / "static" / "v2" / "css" / "components.css"



# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a fresh SQLite database and data directory."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture(scope="module")
def services_reconciliation_py() -> str:
    return SERVICES_RECONCILIATION.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def handlers_reconciliation_py() -> str:
    return HANDLERS_RECONCILIATION.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def services_review_py() -> str:
    return SERVICES_REVIEW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def server_py() -> str:
    return SERVER_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def project_manager_py() -> str:
    return PROJECT_MANAGER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_js() -> str:
    return API_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review_detail_js() -> str:
    return REVIEW_DETAIL_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text(encoding="utf-8")



# ── Store + service helpers ───────────────────────────────────────────────────

def _make_store(project_id: str = "test-rw-s3"):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite(project_id)


def _weakness(wid: str, text: str, status: str = "open", note: str = "") -> Dict:
    return {"id": wid, "text": text, "category": "risks", "status": status, "user_note": note}


def _decision(did: str, text: str, status: str = "open") -> Dict:
    return {"id": did, "text": text, "category": "architecture", "status": status}


def _artifact_ref(name: str, atype: str = "document") -> Dict:
    return {"artifact_id": f"a_{name}", "artifact_name": name,
            "artifact_type": atype, "section_reference": "§1"}


def _setup_two_reviews(project_id: str = "test-rw-s3"):
    """Create one version with two reviews sharing some and diverging on other findings."""
    store = _make_store(project_id)
    store.create_version(included_artifacts=[{"filename": "arch.docx"}], label="V1")
    anchor = store.create_review(
        version_id="v1",
        persona="Solution Architect",
        findings={
            "risks":        ["No DR strategy defined", "Vendor lock-in risk"],
            "assumptions":  ["Client has AWS access"],
            "dependencies": ["Identity provider integration"],
        },
        weaknesses=[
            _weakness("w1", "DR strategy not defined", "open"),
            _weakness("w2", "API security unclear",    "addressed"),
        ],
        decision_points=[
            _decision("d1", "Cloud provider selection", "open"),
            _decision("d2", "Identity provider vendor", "accepted"),
        ],
        artifact_refs=[_artifact_ref("Solution_Architecture_v3.docx")],
    )
    supp = store.create_review(
        version_id="v1",
        persona="Delivery Manager",
        findings={
            "risks":        ["No DR strategy defined", "Team capacity risk"],
            "assumptions":  ["Client has AWS access"],
            "dependencies": ["Data team availability"],
        },
        weaknesses=[
            _weakness("w1", "DR strategy not defined", "open"),
        ],
        decision_points=[
            _decision("d1", "Cloud provider selection", "open"),
        ],
        artifact_refs=[],
    )
    return store, anchor, supp


def _run_reconciliation_direct(project_id: str, anchor_rid: str, selected_rids: List[str],
                               version_id: str = "v1"):
    import services.reconciliation as svc
    return svc.run_reconciliation(project_id, version_id, anchor_rid, selected_rids)



# ══════════════════════════════════════════════════════════════════════════════
# A) Explicit review selection
# ══════════════════════════════════════════════════════════════════════════════

class TestExplicitReviewSelection:

    def test_anchor_review_id_stored_correctly(self):
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        result = svc.save_reconciliation_selection(
            "test-rw-s3", "v1", anchor.review_id, [anchor.review_id, supp.review_id]
        )
        assert result.get("anchor_review_id") == anchor.review_id

    def test_supplemental_reviews_stored_correctly(self):
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        svc.save_reconciliation_selection(
            "test-rw-s3", "v1", anchor.review_id, [anchor.review_id, supp.review_id]
        )
        stored = svc.get_reconciliation_selection("test-rw-s3", "v1")
        assert stored is not None
        assert supp.review_id in stored["selected_review_ids"]

    def test_anchor_auto_prepended_when_missing_from_list(self):
        """anchor_review_id must always be in selected_review_ids."""
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        # Pass only supplemental — anchor should be prepended
        result = svc.save_reconciliation_selection(
            "test-rw-s3", "v1", anchor.review_id, [supp.review_id]
        )
        assert anchor.review_id in result["selected_review_ids"]

    def test_no_auto_latest_n_selection(self):
        """Selecting no reviews must return error, not auto-pick latest."""
        import services.reconciliation as svc
        result = svc.save_reconciliation_selection(
            "test-rw-s3", "v1", "", []
        )
        assert "error" in result, "Empty anchor must produce an error, not auto-select"

    def test_empty_anchor_returns_error(self):
        import services.reconciliation as svc
        result = svc.save_reconciliation_selection("test-rw-s3", "v1", "", ["r1"])
        assert "error" in result

    def test_invalid_review_id_returns_error(self):
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        result = svc.save_reconciliation_selection(
            "test-rw-s3", "v1", "r_nonexistent", ["r_nonexistent"]
        )
        assert "error" in result

    def test_selection_persists_and_is_retrievable(self):
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        svc.save_reconciliation_selection(
            "test-rw-s3", "v1", anchor.review_id, [anchor.review_id, supp.review_id]
        )
        retrieved = svc.get_reconciliation_selection("test-rw-s3", "v1")
        assert retrieved is not None
        assert retrieved["anchor_review_id"] == anchor.review_id
        assert len(retrieved["selected_review_ids"]) == 2

    def test_selected_review_ids_deduplication(self):
        """Duplicate IDs in input must be stored once."""
        store, anchor, supp = _setup_two_reviews()
        import services.reconciliation as svc
        result = svc.save_reconciliation_selection(
            "test-rw-s3", "v1", anchor.review_id,
            [anchor.review_id, supp.review_id, anchor.review_id]
        )
        ids = result["selected_review_ids"]
        assert ids.count(anchor.review_id) == 1, "Duplicate anchor ID must be de-duplicated"



# ══════════════════════════════════════════════════════════════════════════════
# B) Reconciliation structure
# ══════════════════════════════════════════════════════════════════════════════

class TestReconciliationStructure:

    def test_consensus_points_generated(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.consensus_points) > 0, "Expected consensus for shared findings"

    def test_consensus_contains_shared_risk(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [item["text"].lower() for item in out.consensus_points]
        assert any("dr strategy" in t for t in texts), \
            f"'No DR strategy' should be consensus. Got: {texts}"

    def test_divergent_points_generated(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.divergent_points) > 0, "Expected divergent points for unique findings"

    def test_anchor_only_finding_in_divergent(self):
        """'Vendor lock-in risk' is only in anchor — must appear in divergent."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [item["text"].lower() for item in out.divergent_points]
        assert any("vendor lock" in t for t in texts), \
            f"Anchor-only 'Vendor lock-in' must be divergent. Got: {texts}"

    def test_supplemental_only_finding_in_divergent(self):
        """'Team capacity risk' is only in supp — must appear in divergent."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [item["text"].lower() for item in out.divergent_points]
        assert any("team capacity" in t for t in texts), \
            f"Supplemental-only finding must be divergent. Got: {texts}"

    def test_open_decisions_generated(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.open_decisions) > 0, "Cloud provider selection must be open"

    def test_confirmed_decisions_generated(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.confirmed_decisions) > 0, "Identity provider (accepted) must be confirmed"

    def test_unresolved_weaknesses_open_only(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for w in out.unresolved_weaknesses:
            assert w["status"] == "open", \
                f"Non-open weakness must not appear in unresolved. Got status={w['status']}"

    def test_addressed_weakness_not_in_unresolved(self):
        """'API security unclear' is addressed — must NOT appear in unresolved."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [w["text"].lower() for w in out.unresolved_weaknesses]
        assert not any("api security" in t for t in texts), \
            "Addressed weakness must not appear in unresolved_weaknesses"

    def test_merged_findings_covers_all_reviews(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.merged_findings) >= 4, \
            "merged_findings must include all unique items across reviews"



# ══════════════════════════════════════════════════════════════════════════════
# C) Reconciliation safety
# ══════════════════════════════════════════════════════════════════════════════

class TestReconciliationSafety:

    def test_duplicate_like_items_merged_not_counted_twice(self):
        """Near-identical items must not appear twice in merged_findings."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [i["text"].lower() for i in out.merged_findings]
        dr_count = sum(1 for t in texts if "dr strategy" in t)
        assert dr_count == 1, f"'DR strategy' must appear once in merged, not {dr_count}"

    def test_distinct_items_not_collapsed(self):
        """'Vendor lock-in' and 'Team capacity' are different and must both appear."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        texts = [i["text"].lower() for i in out.merged_findings]
        assert any("vendor lock" in t for t in texts),  "Vendor lock-in must be in merged"
        assert any("team capacity" in t for t in texts), "Team capacity must be in merged"

    def test_anchor_only_reconciliation_works(self):
        """No supplemental reviews — reconciliation must still produce output."""
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id])
        assert out.anchor_only is True
        assert len(out.consensus_points) > 0, \
            "Anchor-only: all anchor findings should be consensus"
        assert len(out.divergent_points) == 0, \
            "Anchor-only: no divergent points (nothing to compare)"

    def test_empty_supplemental_list_is_anchor_only(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id])
        assert out.anchor_only is True

    def test_reconciliation_with_three_reviews(self):
        """Three reviews: item in all three = consensus; item in two = divergent."""
        store = _make_store("test-s3-three")
        store.create_version(included_artifacts=[], label="V1")
        shared_risk = "Shared risk across all reviews"
        r1 = store.create_review("v1", "SA", findings={"risks": [shared_risk, "Only in R1"]})
        r2 = store.create_review("v1", "DM", findings={"risks": [shared_risk, "Only in R2"]})
        r3 = store.create_review("v1", "PO", findings={"risks": [shared_risk, "Only in R3"]})

        out = _run_reconciliation_direct("test-s3-three", r1.review_id,
                                         [r1.review_id, r2.review_id, r3.review_id])
        consensus_texts = [i["text"].lower() for i in out.consensus_points]
        assert any("shared risk" in t for t in consensus_texts), \
            "Item in all three reviews must be consensus"
        # Items unique to one review each must be divergent
        div_texts = [i["text"].lower() for i in out.divergent_points]
        assert any("only in r1" in t for t in div_texts)
        assert any("only in r2" in t for t in div_texts)
        assert any("only in r3" in t for t in div_texts)

    def test_review_with_no_findings_still_works(self):
        """A review with empty findings must not crash reconciliation."""
        store = _make_store("test-s3-empty")
        store.create_version(included_artifacts=[], label="V1")
        r1 = store.create_review("v1", "SA", findings={"risks": ["Real risk"]})
        r2 = store.create_review("v1", "DM", findings={})

        out = _run_reconciliation_direct("test-s3-empty", r1.review_id,
                                         [r1.review_id, r2.review_id])
        assert out is not None
        # r2 has no findings so r1's risk won't be consensus (missing from r2)
        assert len(out.divergent_points) > 0



# ══════════════════════════════════════════════════════════════════════════════
# D) Provenance retention
# ══════════════════════════════════════════════════════════════════════════════

class TestProvenanceRetention:

    def test_consensus_items_carry_source_reviews(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for item in out.consensus_points:
            assert len(item["source_reviews"]) > 0, \
                f"Consensus item must have source_reviews. Item: {item['text']}"

    def test_consensus_item_source_reviews_include_anchor(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for item in out.consensus_points:
            review_ids = [p["review_id"] for p in item["source_reviews"]]
            assert anchor.review_id in review_ids, \
                f"Consensus item must cite the anchor. Got: {review_ids}"

    def test_consensus_item_provenance_has_is_anchor_flag(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for item in out.consensus_points:
            anchor_provs = [p for p in item["source_reviews"] if p.get("is_anchor")]
            assert len(anchor_provs) == 1, \
                f"Exactly one anchor provenance entry expected per item. Got: {item['source_reviews']}"

    def test_divergent_item_carries_present_in(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for item in out.divergent_points:
            assert "present_in_reviews" in item, \
                f"Divergent item must have present_in_reviews. Item: {item}"

    def test_divergent_item_carries_absent_from(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for item in out.divergent_points:
            assert "absent_from_reviews" in item, \
                f"Divergent item must have absent_from_reviews. Item: {item}"

    def test_decisions_carry_source_reviews(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        all_dps = out.open_decisions + out.confirmed_decisions
        for dp in all_dps:
            assert len(dp["source_reviews"]) > 0, \
                f"Decision must carry source_reviews. Item: {dp['text']}"

    def test_weaknesses_carry_source_reviews(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        for w in out.unresolved_weaknesses:
            assert len(w["source_reviews"]) > 0, \
                f"Weakness must carry source_reviews. Item: {w['text']}"

    def test_provenance_summary_has_one_entry_per_review(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert len(out.provenance_summary) == 2, \
            f"Expected 2 entries in provenance_summary. Got: {len(out.provenance_summary)}"

    def test_provenance_summary_marks_anchor(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        anchor_entries = [p for p in out.provenance_summary if p.get("is_anchor")]
        assert len(anchor_entries) == 1, "Exactly one anchor in provenance_summary"
        assert anchor_entries[0]["review_id"] == anchor.review_id

    def test_missing_artifact_refs_do_not_break_reconciliation(self):
        """Supplemental review has no artifact_refs — must not crash."""
        store, anchor, supp = _setup_two_reviews()
        # supp was created with empty artifact_refs
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert out is not None
        assert out.reconciliation_id != ""

    def test_provenance_summary_includes_persona(self):
        store, anchor, supp = _setup_two_reviews()
        out = _run_reconciliation_direct("test-rw-s3", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        personas = {p["persona"] for p in out.provenance_summary}
        assert "Solution Architect" in personas
        assert "Delivery Manager"   in personas



# ══════════════════════════════════════════════════════════════════════════════
# E) Output model validation
# ══════════════════════════════════════════════════════════════════════════════

class TestOutputModelValidation:

    REQUIRED_KEYS = {
        "reconciliation_id", "project_id", "version_id",
        "anchor_review_id", "selected_review_ids", "created_at",
        "consensus_points", "divergent_points", "confirmed_decisions",
        "open_decisions", "unresolved_weaknesses", "merged_findings",
        "provenance_summary", "anchor_only",
        "total_consensus", "total_divergent",
        "total_open_decisions", "total_unresolved_weaknesses",
    }

    def test_to_dict_includes_all_required_keys(self):
        store, anchor, supp = _setup_two_reviews("test-s3-model")
        out = _run_reconciliation_direct("test-s3-model", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        d = out.to_dict()
        missing = self.REQUIRED_KEYS - set(d.keys())
        assert not missing, f"Missing keys in ReconciliationOutput.to_dict(): {missing}"

    def test_total_counts_match_list_lengths(self):
        store, anchor, supp = _setup_two_reviews("test-s3-counts")
        out = _run_reconciliation_direct("test-s3-counts", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert out.total_consensus             == len(out.consensus_points)
        assert out.total_divergent             == len(out.divergent_points)
        assert out.total_open_decisions        == len(out.open_decisions)
        assert out.total_unresolved_weaknesses == len(out.unresolved_weaknesses)

    def test_reconciliation_id_is_non_empty(self):
        store, anchor, supp = _setup_two_reviews("test-s3-id")
        out = _run_reconciliation_direct("test-s3-id", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert out.reconciliation_id != ""

    def test_anchor_review_id_preserved_in_output(self):
        store, anchor, supp = _setup_two_reviews("test-s3-anchor-pres")
        out = _run_reconciliation_direct("test-s3-anchor-pres", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert out.anchor_review_id == anchor.review_id

    def test_selected_review_ids_preserved_in_output(self):
        store, anchor, supp = _setup_two_reviews("test-s3-sel-pres")
        out = _run_reconciliation_direct("test-s3-sel-pres", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        assert anchor.review_id in out.selected_review_ids
        assert supp.review_id   in out.selected_review_ids

    def test_from_dict_round_trip(self):
        from models.reconciliation import ReconciliationOutput
        store, anchor, supp = _setup_two_reviews("test-s3-rtrip")
        out = _run_reconciliation_direct("test-s3-rtrip", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        d = out.to_dict()
        restored = ReconciliationOutput.from_dict(d)
        assert restored.reconciliation_id == out.reconciliation_id
        assert restored.anchor_review_id  == out.anchor_review_id
        assert len(restored.consensus_points) == len(out.consensus_points)

    def test_output_persisted_and_retrievable(self):
        import services.reconciliation as svc
        store, anchor, supp = _setup_two_reviews("test-s3-persist")
        out = _run_reconciliation_direct("test-s3-persist", anchor.review_id,
                                         [anchor.review_id, supp.review_id])
        fetched = svc.get_reconciliation("test-s3-persist", "v1")
        assert fetched is not None
        assert fetched.reconciliation_id == out.reconciliation_id

    def test_rerun_overwrites_previous_output(self):
        import services.reconciliation as svc
        store, anchor, supp = _setup_two_reviews("test-s3-overwrite")
        out1 = _run_reconciliation_direct("test-s3-overwrite", anchor.review_id,
                                          [anchor.review_id, supp.review_id])
        out2 = _run_reconciliation_direct("test-s3-overwrite", anchor.review_id,
                                          [anchor.review_id, supp.review_id])
        fetched = svc.get_reconciliation("test-s3-overwrite", "v1")
        assert fetched.reconciliation_id == out2.reconciliation_id, \
            "Latest run must overwrite previous output"



# ══════════════════════════════════════════════════════════════════════════════
# F) Service + handler — static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestServiceHandlerStaticAnalysis:

    def test_save_reconciliation_selection_defined(self, services_reconciliation_py):
        assert "def save_reconciliation_selection(" in services_reconciliation_py

    def test_get_reconciliation_selection_defined(self, services_reconciliation_py):
        assert "def get_reconciliation_selection(" in services_reconciliation_py

    def test_run_reconciliation_defined(self, services_reconciliation_py):
        assert "def run_reconciliation(" in services_reconciliation_py

    def test_get_reconciliation_defined(self, services_reconciliation_py):
        assert "def get_reconciliation(" in services_reconciliation_py

    def test_service_requires_anchor_review_id(self, services_reconciliation_py):
        assert "anchor_review_id" in services_reconciliation_py

    def test_service_requires_selected_review_ids(self, services_reconciliation_py):
        assert "selected_review_ids" in services_reconciliation_py

    def test_service_no_auto_select_latest(self, services_reconciliation_py):
        # No auto-selection code pattern — must NOT contain "latest" auto logic
        assert "auto" not in services_reconciliation_py.lower() or \
               "no auto" in services_reconciliation_py.lower(), \
            "Service must not auto-select reviews"

    def test_handle_save_selection_defined(self, handlers_reconciliation_py):
        assert "def handle_save_selection(" in handlers_reconciliation_py

    def test_handle_get_selection_defined(self, handlers_reconciliation_py):
        assert "def handle_get_selection(" in handlers_reconciliation_py

    def test_handle_run_reconciliation_defined(self, handlers_reconciliation_py):
        assert "def handle_run_reconciliation(" in handlers_reconciliation_py

    def test_handle_get_reconciliation_defined(self, handlers_reconciliation_py):
        assert "def handle_get_reconciliation(" in handlers_reconciliation_py

    def test_handler_delegates_to_service(self, handlers_reconciliation_py):
        assert "svc." in handlers_reconciliation_py, \
            "Handler must delegate to services/reconciliation"

    def test_server_has_reconciliation_select_route(self, server_py):
        assert "reconciliation/select" in server_py

    def test_server_has_reconciliation_run_route(self, server_py):
        assert "reconciliation/run" in server_py

    def test_server_has_reconciliation_selection_get_route(self, server_py):
        assert "reconciliation/selection" in server_py

    def test_server_has_reconciliation_get_route(self, server_py):
        assert "h_reconciliation" in server_py

    def test_server_imports_h_reconciliation(self, server_py):
        assert "import handlers.reconciliation as h_reconciliation" in server_py

    def test_project_manager_exports_save_selection(self, project_manager_py):
        assert "save_reconciliation_selection" in project_manager_py

    def test_project_manager_exports_run_reconciliation(self, project_manager_py):
        assert "run_reconciliation" in project_manager_py

    def test_project_manager_exports_get_reconciliation(self, project_manager_py):
        assert "get_reconciliation" in project_manager_py

    def test_project_manager_exports_get_reconciliation_selection(self, project_manager_py):
        assert "get_reconciliation_selection" in project_manager_py



# ══════════════════════════════════════════════════════════════════════════════
# G) Frontend static analysis — api.js Sprint 3 additions
# ══════════════════════════════════════════════════════════════════════════════

class TestApiJSSprint3:

    def test_save_reconciliation_selection_defined(self, api_js):
        assert "function saveReconciliationSelection(" in api_js

    def test_fetch_reconciliation_selection_defined(self, api_js):
        assert "function fetchReconciliationSelection(" in api_js

    def test_run_reconciliation_defined(self, api_js):
        assert "function runReconciliation(" in api_js

    def test_fetch_reconciliation_defined(self, api_js):
        assert "function fetchReconciliation(" in api_js

    def test_save_reconciliation_selection_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "saveReconciliationSelection" in api_section

    def test_fetch_reconciliation_selection_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "fetchReconciliationSelection" in api_section

    def test_run_reconciliation_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "runReconciliation" in api_section

    def test_fetch_reconciliation_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "fetchReconciliation" in api_section

    def test_mock_run_reconciliation_returns_reconciliation_id(self, api_js):
        assert "reconciliation_id" in api_js

    def test_mock_run_reconciliation_returns_consensus_points(self, api_js):
        assert "consensus_points" in api_js

    def test_mock_run_reconciliation_returns_divergent_points(self, api_js):
        assert "divergent_points" in api_js

    def test_mock_run_reconciliation_returns_open_decisions(self, api_js):
        assert "open_decisions" in api_js

    def test_mock_run_reconciliation_returns_provenance_summary(self, api_js):
        assert "provenance_summary" in api_js

    def test_mock_run_reconciliation_returns_anchor_review_id(self, api_js):
        assert "anchor_review_id" in api_js

    def test_live_path_posts_to_reconciliation_select(self, api_js):
        assert "reconciliation/select" in api_js

    def test_live_path_posts_to_reconciliation_run(self, api_js):
        assert "reconciliation/run" in api_js

    def test_sprint1_and_sprint2_functions_still_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "updateWeaknessNote"      in api_section, "Sprint 1 export missing"
        assert "createReviewIteration"   in api_section, "Sprint 2 export missing"



# ══════════════════════════════════════════════════════════════════════════════
# H) Frontend static analysis — review_detail.js Sprint 3 additions
# ══════════════════════════════════════════════════════════════════════════════

class TestReviewDetailJSSprint3:

    def test_render_reconciliation_panel_defined(self, review_detail_js):
        assert "_renderReconciliationPanel" in review_detail_js

    def test_on_toggle_reconciliation_panel_defined(self, review_detail_js):
        assert "onToggleReconciliationPanel" in review_detail_js

    def test_on_run_reconciliation_defined(self, review_detail_js):
        assert "onRunReconciliation" in review_detail_js

    def test_on_reconciliation_checkbox_change_defined(self, review_detail_js):
        assert "onReconciliationCheckboxChange" in review_detail_js

    def test_render_reconciliation_result_defined(self, review_detail_js):
        assert "_renderReconciliationResult" in review_detail_js

    def test_render_review_includes_reconciliation_panel(self, review_detail_js):
        render_fn = review_detail_js.split("function renderReview(")[1] \
            if "function renderReview(" in review_detail_js else ""
        assert "_renderReconciliationPanel" in render_fn, \
            "renderReview() must call _renderReconciliationPanel"

    def test_reconciliation_panel_has_explicit_toggle_button(self, review_detail_js):
        assert "onToggleReconciliationPanel" in review_detail_js

    def test_reconciliation_panel_body_hidden_by_default(self, review_detail_js):
        # The body must start hidden — explicit user toggle required
        assert "display:none" in review_detail_js or "display: none" in review_detail_js

    def test_anchor_badge_rendered(self, review_detail_js):
        assert "rc-anchor-badge" in review_detail_js

    def test_result_card_shows_consensus_section(self, review_detail_js):
        assert "Consensus Points" in review_detail_js or "consensus_points" in review_detail_js

    def test_result_card_shows_divergent_section(self, review_detail_js):
        assert "Divergent Points" in review_detail_js or "divergent_points" in review_detail_js

    def test_result_card_shows_open_decisions(self, review_detail_js):
        assert "open_decisions" in review_detail_js or "Open Decisions" in review_detail_js

    def test_result_card_shows_unresolved_weaknesses(self, review_detail_js):
        assert "unresolved_weaknesses" in review_detail_js or \
               "Unresolved Weaknesses" in review_detail_js

    def test_on_toggle_exported(self, review_detail_js):
        exports_section = review_detail_js.split("return {")[1] \
            if "return {" in review_detail_js else ""
        assert "onToggleReconciliationPanel" in exports_section

    def test_on_run_reconciliation_exported(self, review_detail_js):
        exports_section = review_detail_js.split("return {")[1] \
            if "return {" in review_detail_js else ""
        assert "onRunReconciliation" in exports_section

    def test_sprint1_render_review_still_present(self, review_detail_js):
        assert "function renderReview(" in review_detail_js

    def test_sprint2_iteration_banner_still_present(self, review_detail_js):
        assert "_renderIterationBanner" in review_detail_js



# ══════════════════════════════════════════════════════════════════════════════
# I) Frontend static analysis — CSS Sprint 3 classes
# ══════════════════════════════════════════════════════════════════════════════

class TestCSSSprint3:

    def test_rc_panel_defined(self, components_css):
        assert ".rc-panel" in components_css

    def test_rc_panel_header_defined(self, components_css):
        assert ".rc-panel-header" in components_css

    def test_rc_anchor_badge_defined(self, components_css):
        assert ".rc-anchor-badge" in components_css

    def test_rc_supp_badge_defined(self, components_css):
        assert ".rc-supp-badge" in components_css

    def test_rc_result_card_defined(self, components_css):
        assert ".rc-result-card" in components_css

    def test_rc_item_defined(self, components_css):
        assert ".rc-item" in components_css

    def test_rc_review_list_defined(self, components_css):
        assert ".rc-review-list" in components_css

    def test_rc_section_header_defined(self, components_css):
        assert ".rc-section-header" in components_css

    def test_rc_result_error_defined(self, components_css):
        assert ".rc-result-error" in components_css

    def test_rc_prov_block_defined(self, components_css):
        assert ".rc-prov-block" in components_css

    def test_rc_result_header_defined(self, components_css):
        assert ".rc-result-header" in components_css

    def test_rc_chip_id_defined(self, components_css):
        assert ".rc-chip-id" in components_css

    def test_sprint1_rd_classes_still_present(self, components_css):
        assert ".rd-header" in components_css or ".rd-" in components_css, \
            "Sprint 1 CSS must not be removed"

    def test_sprint2_ri_classes_still_present(self, components_css):
        assert ".ri-lineage-banner" in components_css, \
            "Sprint 2 CSS must not be removed"



# ══════════════════════════════════════════════════════════════════════════════
# J) Non-regression — Sprint 1 features still work
# ══════════════════════════════════════════════════════════════════════════════

class TestNonRegressionSprint1:

    def test_weakness_note_field_on_review(self):
        """Weakness user_note field must still be present on Review objects."""
        store = _make_store("test-s3-nr-s1a")
        store.create_version(included_artifacts=[], label="V1")
        r = store.create_review(
            "v1", "SA",
            weaknesses=[{"id": "w1", "text": "Test weakness", "status": "open",
                         "user_note": "My annotation", "category": "risks"}]
        )
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        w = loaded.weaknesses[0]
        assert w.get("user_note") == "My annotation", "user_note must persist"

    def test_artifact_refs_field_on_review(self):
        """artifact_refs must still be stored and retrievable."""
        store = _make_store("test-s3-nr-s1b")
        store.create_version(included_artifacts=[], label="V1")
        r = store.create_review(
            "v1", "SA",
            artifact_refs=[{"artifact_id": "a1", "artifact_name": "arch.docx",
                             "artifact_type": "document", "section_reference": "§1"}]
        )
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        assert len(loaded.artifact_refs) == 1
        assert loaded.artifact_refs[0]["artifact_name"] == "arch.docx"

    def test_weakness_status_update_still_works(self):
        """update_weakness_status() store-layer logic still works (Sprint 1 path)."""
        store = _make_store("test-s3-nr-s1c")
        store.create_version(included_artifacts=[], label="V1")
        r = store.create_review(
            "v1", "SA",
            weaknesses=[{"id": "w1", "text": "Test", "status": "open",
                         "user_note": "", "category": "risks"}]
        )
        # Directly update via store (avoids yaml dependency from services.review import)
        weaknesses = list(store.get_review(r.review_id).weaknesses)
        weaknesses[0]["status"] = "addressed"
        store.update_review_weaknesses(r.review_id, weaknesses)
        loaded = store.get_review(r.review_id)
        assert loaded.weaknesses[0]["status"] == "addressed"

    def test_sprint1_render_review_function_present(self, review_detail_js):
        assert "function renderReview(" in review_detail_js

    def test_sprint1_provenance_chips_css_present(self, components_css):
        assert ".rd-prov-chip" in components_css


# ══════════════════════════════════════════════════════════════════════════════
# K) Non-regression — Sprint 2 features still work
# ══════════════════════════════════════════════════════════════════════════════

class TestNonRegressionSprint2:

    def test_previous_review_id_stored_on_iteration(self):
        """previous_review_id must still link iterations (Sprint 2)."""
        store = _make_store("test-s3-nr-s2a")
        store.create_version(included_artifacts=[], label="V1")
        base = store.create_review("v1", "SA", findings={"risks": ["R1"]})
        new = store.create_review("v1", "SA", previous_review_id=base.review_id,
                                  findings={"risks": ["R1 refined"]})
        loaded = store.get_review(new.review_id)
        assert loaded.previous_review_id == base.review_id

    def test_create_review_iteration_still_defined(self, services_review_py):
        assert "def create_review_iteration(" in services_review_py

    def test_sprint2_iteration_banner_css_present(self, components_css):
        assert ".ri-lineage-banner" in components_css

    def test_sprint2_api_create_review_iteration_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "createReviewIteration" in api_section

    def test_original_review_unchanged_after_reconciliation(self):
        """Reconciliation must not modify the original reviews."""
        store, anchor, supp = _setup_two_reviews("test-s3-nr-s2b")
        original_summary   = anchor.summary
        original_findings  = dict(anchor.findings)
        _run_reconciliation_direct("test-s3-nr-s2b", anchor.review_id,
                                    [anchor.review_id, supp.review_id])
        reloaded = store.get_review(anchor.review_id)
        assert reloaded.summary  == original_summary
        assert reloaded.findings == original_findings



# ══════════════════════════════════════════════════════════════════════════════
# L) Backward compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:

    def test_get_reconciliation_returns_none_when_none_stored(self):
        import services.reconciliation as svc
        result = svc.get_reconciliation("no-such-project", "v1")
        assert result is None, "Must return None when no reconciliation stored"

    def test_get_reconciliation_selection_returns_none_when_none_stored(self):
        import services.reconciliation as svc
        result = svc.get_reconciliation_selection("no-such-project", "v1")
        assert result is None, "Must return None when no selection stored"

    def test_old_review_without_reconciliation_fields_renders_safely(self):
        """Reviews created before Sprint 3 (no reconciliation data) must not error."""
        store = _make_store("test-s3-bcompat")
        store.create_version(included_artifacts=[], label="V1")
        # Create review with minimal fields (no decision_points, no weaknesses)
        r = store.create_review("v1", "SA", findings={"risks": ["Legacy risk"]})
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        # Simulate reconciliation on old-style review
        out = _run_reconciliation_direct("test-s3-bcompat", r.review_id, [r.review_id])
        assert out is not None
        assert out.anchor_only is True

    def test_reconciliation_with_review_missing_weaknesses_field(self):
        """Review with empty weaknesses must not crash unresolved_weaknesses computation."""
        store = _make_store("test-s3-bcompat2")
        store.create_version(included_artifacts=[], label="V1")
        r1 = store.create_review("v1", "SA", findings={"risks": ["R1"]}, weaknesses=[])
        r2 = store.create_review("v1", "DM", findings={"risks": ["R1"]}, weaknesses=[])
        out = _run_reconciliation_direct("test-s3-bcompat2", r1.review_id,
                                         [r1.review_id, r2.review_id])
        assert out.unresolved_weaknesses == []

    def test_reconciliation_with_review_missing_decision_points_field(self):
        """Review with empty decision_points must not crash decisions computation."""
        store = _make_store("test-s3-bcompat3")
        store.create_version(included_artifacts=[], label="V1")
        r1 = store.create_review("v1", "SA", findings={"risks": ["R1"]}, decision_points=[])
        r2 = store.create_review("v1", "DM", findings={"risks": ["R1"]}, decision_points=[])
        out = _run_reconciliation_direct("test-s3-bcompat3", r1.review_id,
                                         [r1.review_id, r2.review_id])
        assert out.open_decisions      == []
        assert out.confirmed_decisions == []

    def test_reconciliation_selection_model_round_trip(self):
        from models.reconciliation import ReconciliationSelection
        sel = ReconciliationSelection(
            version_id="v1", project_id="p1",
            anchor_review_id="r1",
            selected_review_ids=["r1", "r2"],
            selected_at="2026-06-01T10:00:00Z",
            selected_by="tester",
        )
        d = sel.to_dict()
        restored = ReconciliationSelection.from_dict(d)
        assert restored.anchor_review_id    == "r1"
        assert restored.selected_review_ids == ["r1", "r2"]
        assert restored.selected_by         == "tester"

    def test_sprint3_routes_do_not_break_existing_iterate_route(self, server_py):
        """Verify both /iterate and /reconciliation routes coexist."""
        assert "/iterate" in server_py,                 "Sprint 2 iterate route missing"
        assert "reconciliation/select" in server_py,    "Sprint 3 select route missing"
        assert "reconciliation/run"    in server_py,    "Sprint 3 run route missing"
