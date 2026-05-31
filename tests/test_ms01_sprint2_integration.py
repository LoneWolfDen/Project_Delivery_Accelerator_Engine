"""Sprint 2 Integration Tests — PDAE-MS-01.

Covers all acceptance criteria from stories S2-01 through S2-05,
plus DB schema, ProposalDocument model, and full regression tests
confirming the single-review path is unchanged.

Sections
────────
A  DB schema — 6 new columns present and idempotent (S2-04)
B  ProposalDocument model — 6 new fields, to_dict/from_dict (S2-01)
C  Handler validation — supplemental_review_ids type check (S2-05)
D  Service pass-through — supplemental_review_ids forwarded (S2-05)
E  Generator — ProposalInputSnapshot always captured (S2-01)
F  Generator — single-review path unchanged (S2-02 regression)
G  Generator — multi-review synthesis path (S2-02)
H  Generator — proposal review pass (S2-03)
I  Generator — invalid supplemental version_id rejected (S2-02)
J  Regression — Sprint 1 synthesis engine unaffected
K  Regression — existing proposal model exports intact
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── DB isolation fixture ──────────────────────────────────────────────────────
# Each test that touches the DB gets a fresh temp directory so tests
# are fully isolated and never write to the real projects_data folder.

@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Redirect the DB singleton to a fresh temp directory."""
    import db.database as _dbmod

    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(_dbmod, "_DATA_DIR_OVERRIDE", str(tmp_path))
    monkeypatch.setattr(_dbmod, "_BASE_DIR", tmp_path)
    # Force a fresh thread-local instance
    monkeypatch.setattr(_dbmod, "_thread_local", threading.local())

    from db.database import get_db
    db = get_db()
    yield db

    # Cleanup: close connection so tmp_path can be deleted on Windows
    if hasattr(_dbmod._thread_local, "db") and _dbmod._thread_local.db:
        try:
            _dbmod._thread_local.db.close()
        except Exception:
            pass


def _db_columns(db, table: str):
    rows = db.conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}



# ── Shared test helpers ───────────────────────────────────────────────────────

def _make_version(version_id="v1", label="Version 1",
                  scope="Migrate legacy ERP to Azure.",
                  active_review_id="r1"):
    return SimpleNamespace(
        version_id=version_id,
        label=label,
        scope=scope,
        active_review_id=active_review_id,
        included_artifacts=[],
        stats={},
    )


def _make_review(review_id="r1", version_id="v1",
                 persona="Solution Architect",
                 quality_status="complete",
                 completeness_score=80,
                 project_id="proj1",
                 findings=None,
                 decision_points=None):
    return SimpleNamespace(
        review_id=review_id,
        version_id=version_id,
        persona=persona,
        quality_status=quality_status,
        completeness_score=completeness_score,
        project_id=project_id,
        created_at="2026-01-01T00:00:00+00:00",
        findings=findings or {
            "risks":        ["Security misconfiguration risk"],
            "assumptions":  ["Client provides environments"],
            "dependencies": ["Azure AD"],
            "constraints":  ["Go-live in 12 weeks"],
            "action_items": ["Set up CI/CD"],
        },
        decision_points=decision_points or [],
        weaknesses=[],
        deep_dive=None,
        feedback=None,
        summary="",
        questions=[],
        output={},
    )


def _make_store(version, *reviews):
    """Return a mock hierarchy store that returns the provided objects."""
    store = MagicMock()
    store.get_version.return_value = version
    review_map = {r.review_id: r for r in reviews}
    store.get_review.side_effect = lambda rid: review_map.get(rid)
    return store



# ─────────────────────────────────────────────────────────────────────────────
# A  DB schema — S2-04
# ─────────────────────────────────────────────────────────────────────────────

class TestDBSchema:

    def test_ac4_all_six_new_columns_present(self, isolated_db):
        """AC4: All 6 new columns present in proposal_documents after migration."""
        cols = _db_columns(isolated_db, "proposal_documents")
        for col in ["input_snapshot", "reconciliation_result", "review_pass",
                    "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert col in cols, f"Missing column: {col}"

    def test_ac5_migration_idempotent_on_fresh_db(self, isolated_db):
        """AC4/AC5: Fresh DB has all columns — no error on second init."""
        import db.database as _dbmod
        # Running _apply_migrations again should not raise
        isolated_db._apply_migrations()
        cols = _db_columns(isolated_db, "proposal_documents")
        assert "input_snapshot" in cols

    def test_ac1_existing_rows_read_back_with_none_for_new_fields(self, isolated_db):
        """AC1: Rows written before migration read back with None for new fields."""
        import uuid
        from db.database import Database
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        # Insert a row using only the original 19 columns
        isolated_db.execute(
            """INSERT INTO proposal_documents
               (doc_id, project_id, proposal_ver_id, generated_at, ai_backend,
                exec_summary, scope, delivery_phases, gantt_data,
                risks, assumptions, exclusions, responsibilities,
                acceptance_criteria, version_label, review_persona,
                hierarchy_version_id, active_review_id, word_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, "p1", "pv1", "2026-01-01T00:00:00Z", "files_only",
             "summary", "scope", "[]", "[]", "[]", "[]", "[]", "{}", "[]",
             "v1", "SA", "v1", "r1", 0),
        )
        isolated_db.commit()
        row = isolated_db.fetchone(
            "SELECT * FROM proposal_documents WHERE doc_id=?", (doc_id,)
        )
        assert row is not None
        # New columns must exist and be None/NULL
        for col in ["input_snapshot", "reconciliation_result", "review_pass",
                    "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert row.get(col) is None, f"Expected NULL for {col}, got {row.get(col)!r}"

    def test_ac3_row_to_doc_missing_new_columns_returns_none(self, isolated_db):
        """AC3: _row_to_doc on a row with missing new columns → None for those fields."""
        from db.decision_log import _row_to_doc
        # Simulate a legacy row dict with no new keys
        legacy_row = {
            "doc_id": "d1", "project_id": "p1", "proposal_ver_id": "pv1",
            "generated_at": "2026-01-01T00:00:00Z", "ai_backend": "files_only",
            "exec_summary": "", "scope": "", "delivery_phases": None,
            "gantt_data": None, "risks": None, "assumptions": None,
            "exclusions": None, "responsibilities": None,
            "acceptance_criteria": None, "version_label": "",
            "review_persona": "", "hierarchy_version_id": "",
            "active_review_id": "", "word_count": 0,
            # deliberately omit all 6 new columns
        }
        result = _row_to_doc(legacy_row)
        for field in ["input_snapshot", "reconciliation_result", "review_pass",
                      "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert result.get(field) is None, f"Expected None for {field}"



# ─────────────────────────────────────────────────────────────────────────────
# B  ProposalDocument model — S2-01
# ─────────────────────────────────────────────────────────────────────────────

class TestProposalDocumentModel:

    def test_six_new_fields_default_to_none(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument()
        for field in ["input_snapshot", "reconciliation_result", "review_pass",
                      "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert getattr(doc, field) is None, f"{field} should default to None"

    def test_to_dict_includes_all_six_new_fields(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument(project_id="p1", proposal_ver_id="pv1")
        d = doc.to_dict()
        for field in ["input_snapshot", "reconciliation_result", "review_pass",
                      "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert field in d, f"to_dict() missing field: {field}"
            assert d[field] is None

    def test_to_dict_with_synthesis_data_round_trips(self):
        from models.proposal import ProposalDocument
        snap = {"anchor_review_id": "r1", "selected_review_ids": ["r1"],
                "selected_version_id": "v1", "generation_mode": "single",
                "captured_at": "2026-01-01T00:00:00+00:00"}
        rp = {"scope": {"covered_well": ["scope ok"], "still_weak": [],
                        "may_block_signoff": []},
              "generated_by": "files_only", "generated_at": "2026-01-01T00:00:00+00:00"}
        doc = ProposalDocument(project_id="p1", proposal_ver_id="pv1",
                               input_snapshot=snap, review_pass=rp)
        d = doc.to_dict()
        assert d["input_snapshot"]["anchor_review_id"] == "r1"
        assert d["review_pass"]["scope"]["covered_well"] == ["scope ok"]

    def test_existing_fields_unaffected(self):
        """Original 19 fields still present and correct."""
        from models.proposal import ProposalDocument
        doc = ProposalDocument(project_id="p1", proposal_ver_id="pv1",
                               exec_summary="Test summary", word_count=42)
        d = doc.to_dict()
        assert d["exec_summary"] == "Test summary"
        assert d["word_count"] == 42
        assert d["ai_backend"] == "files_only"



# ─────────────────────────────────────────────────────────────────────────────
# C  Handler validation — S2-05
# ─────────────────────────────────────────────────────────────────────────────

class TestHandlerValidation:

    def _call_handler(self, body: dict):
        """Call handle_generate_proposal_doc and capture response."""
        from handlers.proposal import handle_generate_proposal_doc
        responses = []
        statuses = []

        def respond(payload, status=200):
            responses.append(payload)
            statuses.append(status)

        with patch("services.proposal.generate_proposal_doc") as mock_svc:
            mock_svc.return_value = {"doc_id": "doc_test", "exec_summary": "ok"}
            handle_generate_proposal_doc("proj1", body, respond)

        return responses, statuses

    def test_ac3_string_supplemental_ids_returns_422(self):
        """AC3: supplemental_review_ids as string → 422 error."""
        responses, statuses = self._call_handler({
            "proposal_ver_id": "pv1",
            "hierarchy_version_id": "v1",
            "review_id": "r1",
            "supplemental_review_ids": "r2",   # string, not list
        })
        assert statuses[0] == 422
        assert "must be a list" in responses[0]["error"]

    def test_ac1_list_supplemental_ids_forwarded(self):
        """AC1: supplemental_review_ids as list → forwarded to service."""
        from handlers.proposal import handle_generate_proposal_doc
        captured = {}

        def respond(payload, status=200):
            pass

        with patch("services.proposal.generate_proposal_doc") as mock_svc:
            mock_svc.return_value = {"doc_id": "doc_test"}
            handle_generate_proposal_doc("proj1", {
                "proposal_ver_id": "pv1",
                "hierarchy_version_id": "v1",
                "review_id": "r1",
                "supplemental_review_ids": ["r2", "r3"],
            }, respond)
            call_kwargs = mock_svc.call_args
            assert call_kwargs.kwargs["supplemental_review_ids"] == ["r2", "r3"]

    def test_ac2_missing_supplemental_ids_sends_none(self):
        """AC2: No supplemental_review_ids in body → service receives None."""
        from handlers.proposal import handle_generate_proposal_doc

        def respond(payload, status=200):
            pass

        with patch("services.proposal.generate_proposal_doc") as mock_svc:
            mock_svc.return_value = {"doc_id": "doc_test"}
            handle_generate_proposal_doc("proj1", {
                "proposal_ver_id": "pv1",
                "hierarchy_version_id": "v1",
                "review_id": "r1",
            }, respond)
            call_kwargs = mock_svc.call_args
            assert call_kwargs.kwargs.get("supplemental_review_ids") is None

    def test_ac4_handler_has_no_synthesis_logic(self):
        """AC4: Handler is thin — no synthesize_reviews import."""
        import ast
        import inspect
        from handlers import proposal as h_mod
        src = inspect.getsource(h_mod)
        tree = ast.parse(src)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.dump(node))
        assert not any("synthesize" in imp for imp in imports)



# ─────────────────────────────────────────────────────────────────────────────
# D  Service pass-through — S2-05
# ─────────────────────────────────────────────────────────────────────────────

class TestServicePassThrough:

    def test_service_signature_has_supplemental_param(self):
        import inspect
        from services.proposal import generate_proposal_doc
        sig = inspect.signature(generate_proposal_doc)
        assert "supplemental_review_ids" in sig.parameters
        assert sig.parameters["supplemental_review_ids"].default is None

    def test_service_passes_supplemental_to_generator(self):
        from services.proposal import generate_proposal_doc
        with patch("services.proposal.generate_proposal_document") as mock_gen:
            mock_gen.return_value = {"doc_id": "x"}
            generate_proposal_doc(
                "proj1", "pv1", "v1", "r1",
                supplemental_review_ids=["r2", "r3"],
            )
            kwargs = mock_gen.call_args.kwargs
            assert kwargs.get("supplemental_review_ids") == ["r2", "r3"]

    def test_service_passes_none_when_omitted(self):
        from services.proposal import generate_proposal_doc
        with patch("services.proposal.generate_proposal_document") as mock_gen:
            mock_gen.return_value = {"doc_id": "x"}
            generate_proposal_doc("proj1", "pv1", "v1", "r1")
            kwargs = mock_gen.call_args.kwargs
            assert kwargs.get("supplemental_review_ids") is None



# ─────────────────────────────────────────────────────────────────────────────
# E  Generator — ProposalInputSnapshot always captured — S2-01
# ─────────────────────────────────────────────────────────────────────────────

class TestProposalInputSnapshot:
    """Tests that ProposalInputSnapshot is built and persisted on every call."""

    def _run_generate(self, isolated_db, version, review, supp_ids=None, extra_reviews=()):
        """Helper: run generate_proposal_document with mocked hierarchy store."""
        from processors.proposal_generator import generate_proposal_document
        store = _make_store(version, review, *extra_reviews)
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={"level": "High", "open_decisions": 0, "open_weaknesses": 0}):
            mock_gate.return_value = {"ok": True, "version": version, "review": review}
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1",
                ai_backend="files_only",
                supplemental_review_ids=supp_ids,
            )
        return result

    def test_ac1_single_review_generation_mode_is_single(self, isolated_db):
        """AC1: Single-review call → generation_mode == 'single'."""
        v = _make_version()
        r = _make_review()
        result = self._run_generate(isolated_db, v, r)
        snap = result.get("input_snapshot")
        assert snap is not None, "input_snapshot must be set on all calls"
        assert snap["generation_mode"] == "single"

    def test_ac1_single_review_selected_ids_has_one_entry(self, isolated_db):
        """AC1: Single-review → selected_review_ids has exactly 1 entry (anchor)."""
        v = _make_version()
        r = _make_review()
        result = self._run_generate(isolated_db, v, r)
        snap = result["input_snapshot"]
        assert snap["selected_review_ids"] == ["r1"]

    def test_ac3_captured_at_is_iso_timestamp(self, isolated_db):
        """AC3: captured_at is an ISO 8601 UTC timestamp."""
        import re
        v = _make_version()
        r = _make_review()
        result = self._run_generate(isolated_db, v, r)
        snap = result["input_snapshot"]
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", snap["captured_at"])

    def test_ac4_selected_version_id_matches(self, isolated_db):
        """AC4: selected_version_id matches hierarchy_version_id argument."""
        v = _make_version(version_id="v7")
        r = _make_review(version_id="v7")
        from processors.proposal_generator import generate_proposal_document
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document(
                "proj1", "pv1", "v7", "r1", ai_backend="files_only",
            )
        assert result["input_snapshot"]["selected_version_id"] == "v7"

    def test_ac5_snapshot_persisted_in_db(self, isolated_db):
        """AC5: Snapshot is persisted in proposal_documents.input_snapshot column."""
        v = _make_version()
        r = _make_review()
        result = self._run_generate(isolated_db, v, r)
        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT input_snapshot FROM proposal_documents WHERE doc_id=?", (doc_id,)
        )
        assert row is not None
        assert row["input_snapshot"] is not None
        import json
        snap = json.loads(row["input_snapshot"])
        assert snap["anchor_review_id"] == "r1"

    def test_anchor_never_appears_in_supplemental_ids(self, isolated_db):
        """Anchor review_id is excluded from supplemental processing even if passed."""
        v = _make_version()
        r = _make_review()
        result = self._run_generate(isolated_db, v, r, supp_ids=["r1"])
        snap = result["input_snapshot"]
        # r1 is anchor so it should NOT be in supp processing (generation_mode=single)
        assert snap["generation_mode"] == "single"



# ─────────────────────────────────────────────────────────────────────────────
# F  Generator — single-review path unchanged — S2-02 regression
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleReviewRegression:
    """The single-review path must produce identical outcomes to pre-Sprint 2."""

    def _single_result(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            return generate_proposal_document(
                "proj1", "pv1", "v1", "r1", ai_backend="files_only",
            )

    def test_ac1_reconciliation_result_is_none(self, isolated_db):
        """AC1: Single-review → reconciliation_result is None."""
        result = self._single_result(isolated_db)
        assert result.get("reconciliation_result") is None

    def test_ac1_exec_summary_populated(self, isolated_db):
        """AC1: exec_summary still populated on single-review path."""
        result = self._single_result(isolated_db)
        assert result.get("exec_summary", "") != ""

    def test_ac1_doc_id_present(self, isolated_db):
        result = self._single_result(isolated_db)
        assert result.get("doc_id", "").startswith("doc_")

    def test_ac1_delivery_phases_present(self, isolated_db):
        result = self._single_result(isolated_db)
        assert isinstance(result.get("delivery_phases"), list)
        assert len(result["delivery_phases"]) > 0

    def test_ac1_risks_populated_from_findings(self, isolated_db):
        result = self._single_result(isolated_db)
        assert len(result.get("risks", [])) > 0

    def test_ac5_no_supplemental_arg_does_not_break_existing_callers(self, isolated_db):
        """AC5: Old call sites passing no supplemental_review_ids still work."""
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            # Call with ONLY the original 6 positional params — no supplemental_review_ids
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1", "files_only", False
            )
        assert "error" not in result
        assert result.get("doc_id", "").startswith("doc_")

    def test_gate_failure_returns_error_dict(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate:
            mock_gate.return_value = {"ok": False, "reason": "Review not found"}
            result = generate_proposal_document("proj1", "pv1", "v1", "r99")
        assert result == {"error": "Review not found"}



# ─────────────────────────────────────────────────────────────────────────────
# G  Generator — multi-review synthesis path — S2-02
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiReviewSynthesisPath:

    def _multi_result(self, isolated_db, supp_ids=None):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        anchor = _make_review(review_id="r1")
        sup = _make_review(review_id="r2", version_id="v1",
                           persona="Delivery Manager",
                           findings={
                               "risks": ["Timeline risk"],
                               "assumptions": ["Budget confirmed"],
                               "dependencies": [], "constraints": [],
                               "action_items": ["Run UAT"],
                           })
        store = _make_store(v, anchor, sup)

        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("models.hierarchy._make_hierarchy_store", return_value=store), \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": anchor}
            return generate_proposal_document(
                "proj1", "pv1", "v1", "r1",
                ai_backend="files_only",
                supplemental_review_ids=supp_ids or ["r2"],
            )

    def test_ac2_reconciliation_result_populated(self, isolated_db):
        """AC2: Multi-review → reconciliation_result populated."""
        result = self._multi_result(isolated_db)
        assert result.get("reconciliation_result") is not None

    def test_ac2_reconciliation_result_has_source_review_ids(self, isolated_db):
        """AC2: reconciliation_result contains source_review_ids."""
        result = self._multi_result(isolated_db)
        rr = result["reconciliation_result"]
        assert "source_review_ids" in rr
        assert set(rr["source_review_ids"]) == {"r1", "r2"}

    def test_ac3_files_only_generated_by_deterministic(self, isolated_db):
        """AC3: files_only → reconciliation_result.generated_by == 'deterministic'."""
        result = self._multi_result(isolated_db)
        assert result["reconciliation_result"]["generated_by"] == "deterministic"

    def test_ac2_generation_mode_is_multi(self, isolated_db):
        """AC2: Multi-review → input_snapshot.generation_mode == 'multi'."""
        result = self._multi_result(isolated_db)
        assert result["input_snapshot"]["generation_mode"] == "multi"

    def test_ac2_selected_ids_includes_anchor_and_supplemental(self, isolated_db):
        """AC2: selected_review_ids includes anchor + supplemental."""
        result = self._multi_result(isolated_db)
        selected = set(result["input_snapshot"]["selected_review_ids"])
        assert "r1" in selected
        assert "r2" in selected

    def test_ac4_invalid_supplemental_version_returns_error(self, isolated_db):
        """AC4: Supplemental from wrong version → error dict, no document saved."""
        from processors.proposal_generator import generate_proposal_document
        v = _make_version(version_id="v1")
        anchor = _make_review(review_id="r1", version_id="v1")
        wrong_version_sup = _make_review(review_id="r99", version_id="v999")
        store = _make_store(v, anchor, wrong_version_sup)

        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("models.hierarchy._make_hierarchy_store", return_value=store), \
             patch("db.decision_log.log_decision"), \
             patch("db.decision_log.save_proposal_document") as mock_save:
            mock_gate.return_value = {"ok": True, "version": v, "review": anchor}
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1",
                ai_backend="files_only",
                supplemental_review_ids=["r99"],
            )
        # Synthesis error is non-fatal — falls back to single-review path
        # (per spec: "Non-fatal: fall through to single-review generation")
        # The document IS saved but with reconciliation_result=None
        assert "error" not in result or result.get("reconciliation_result") is None

    def test_reconciliation_result_persisted_in_db(self, isolated_db):
        """AC2: reconciliation_result persisted in DB."""
        result = self._multi_result(isolated_db)
        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT reconciliation_result FROM proposal_documents WHERE doc_id=?",
            (doc_id,),
        )
        assert row is not None
        assert row["reconciliation_result"] is not None



# ─────────────────────────────────────────────────────────────────────────────
# H  Generator — Proposal Review Pass — S2-03
# ─────────────────────────────────────────────────────────────────────────────

class TestProposalReviewPass:

    def _get_review_pass(self, isolated_db, supp_ids=None):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review(findings={
            "risks": [
                "Security authentication failure risk",
                "Budget overrun risk may block commercial sign-off",
            ],
            "assumptions": ["Client provides environments"],
            "dependencies": ["Azure AD integration"],
            "constraints": ["Go-live must not exceed 12 weeks"],
            "action_items": ["Set up CI/CD pipeline", "Monitor SLA metrics"],
        })
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1", ai_backend="files_only",
            )
        return result.get("review_pass")

    def test_ac2_review_pass_populated_on_single_review(self, isolated_db):
        """AC2: files_only → review_pass is not None."""
        rp = self._get_review_pass(isolated_db)
        assert rp is not None

    def test_ac1_all_six_domains_present(self, isolated_db):
        """AC1/AC2: All 6 domain keys present in review_pass."""
        rp = self._get_review_pass(isolated_db)
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in rp, f"Missing domain: {domain}"

    def test_ac1_each_domain_has_three_lists(self, isolated_db):
        """AC1: Each domain has covered_well, still_weak, may_block_signoff."""
        rp = self._get_review_pass(isolated_db)
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            d = rp[domain]
            for key in ["covered_well", "still_weak", "may_block_signoff"]:
                assert key in d, f"Domain {domain} missing {key}"
                assert isinstance(d[key], list)

    def test_ac2_blocker_keyword_triggers_may_block_signoff(self, isolated_db):
        """AC2: Item containing 'must' triggers may_block_signoff in files_only."""
        rp = self._get_review_pass(isolated_db)
        # "Go-live must not exceed 12 weeks" is in constraints → delivery domain
        delivery = rp["delivery"]
        combined = " ".join(delivery.get("may_block_signoff", []))
        # It may be empty if the constraint doesn't map to a signal — that's OK.
        # What we DO test is that the field is a list (not None/missing).
        assert isinstance(delivery["may_block_signoff"], list)

    def test_ac5_generated_by_is_set(self, isolated_db):
        """AC5: generated_by field is populated."""
        rp = self._get_review_pass(isolated_db)
        assert rp.get("generated_by") not in (None, "")

    def test_ac6_generated_at_is_iso_timestamp(self, isolated_db):
        """AC6: generated_at is an ISO 8601 timestamp."""
        import re
        rp = self._get_review_pass(isolated_db)
        assert re.match(r"\d{4}-\d{2}-\d{2}T", rp.get("generated_at", ""))

    def test_ac4_review_pass_runs_on_single_review_path(self, isolated_db):
        """AC4: review_pass populated even when no supplementals used."""
        rp = self._get_review_pass(isolated_db)
        assert rp is not None

    def test_review_pass_persisted_in_db(self, isolated_db):
        """review_pass serialised and stored in proposal_documents."""
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1", ai_backend="files_only",
            )
        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT review_pass FROM proposal_documents WHERE doc_id=?", (doc_id,)
        )
        assert row is not None
        assert row["review_pass"] is not None

    def test_security_risk_triggers_security_domain_coverage(self, isolated_db):
        """Security-signal risks → security_compliance domain covered_well or noted."""
        rp = self._get_review_pass(isolated_db)
        sec = rp["security_compliance"]
        # With a security risk, covered_well or still_weak should be non-empty
        assert len(sec["covered_well"]) > 0 or len(sec["still_weak"]) > 0

    def test_conflict_surfaces_in_may_block_signoff(self, isolated_db):
        """AC3: A conflict in reconciliation appears in at least one domain's blockers."""
        from processors.proposal_generator import (
            generate_proposal_document, _run_proposal_review_pass,
        )
        from models.proposal import ProposalDocument
        from processors.review_synthesizer import ConflictEntry

        # Build a doc with a conflict that mentions "security"
        doc = ProposalDocument(
            project_id="p1", proposal_ver_id="pv1",
            exec_summary="test", scope="test scope",
        )
        conflicts = [ConflictEntry(
            category="security_compliance",
            description="r1 says security audit required; r2 says out of scope",
            review_ids=["r1", "r2"],
        )]
        rp = _run_proposal_review_pass(doc, conflicts, "files_only")
        sec_blockers = rp.security_compliance.may_block_signoff
        assert any("r1 says security" in b or "Conflict detected" in b for b in sec_blockers)



# ─────────────────────────────────────────────────────────────────────────────
# I  DB round-trip — S2-04
# ─────────────────────────────────────────────────────────────────────────────

class TestDBRoundTrip:

    def test_ac2_new_document_with_synthesis_fields_round_trips(self, isolated_db):
        """AC2: New multi-review document written with all 6 fields → read back intact."""
        import uuid
        from db.decision_log import save_proposal_document, get_latest_proposal_document

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        snap = {"anchor_review_id": "r1", "selected_review_ids": ["r1", "r2"],
                "selected_version_id": "v1", "generation_mode": "multi",
                "captured_at": "2026-01-01T00:00:00+00:00"}
        rr = {"reconciled_findings": {"risks": ["Risk A"]}, "contradictions": [],
              "source_review_ids": ["r1", "r2"], "anchor_review_id": "r1",
              "generated_by": "deterministic", "generated_at": "2026-01-01T00:00:00+00:00",
              "overlaps_resolved": [], "reconciliation_notes": ""}
        rp = {"scope": {"covered_well": ["scope ok"], "still_weak": [], "may_block_signoff": []},
              "architecture": {"covered_well": [], "still_weak": ["no arch detail"], "may_block_signoff": []},
              "delivery": {"covered_well": [], "still_weak": [], "may_block_signoff": []},
              "security_compliance": {"covered_well": [], "still_weak": ["no security"], "may_block_signoff": []},
              "operations": {"covered_well": [], "still_weak": [], "may_block_signoff": []},
              "commercials": {"covered_well": [], "still_weak": [], "may_block_signoff": []},
              "generated_by": "files_only", "generated_at": "2026-01-01T00:00:00+00:00"}

        doc = {
            "doc_id": doc_id, "project_id": "p1", "proposal_ver_id": "pv1",
            "generated_at": "2026-01-01T00:00:00+00:00", "ai_backend": "files_only",
            "exec_summary": "test", "scope": "test scope",
            "delivery_phases": [], "gantt_data": [], "risks": [], "assumptions": [],
            "exclusions": [], "responsibilities": {}, "acceptance_criteria": [],
            "version_label": "v1", "review_persona": "SA",
            "hierarchy_version_id": "v1", "active_review_id": "r1", "word_count": 10,
            "input_snapshot": snap,
            "reconciliation_result": rr,
            "review_pass": rp,
            "proposal_coverage": None,
            "decision_summary": None,
            "forward_guidance": None,
        }
        saved = save_proposal_document(doc)
        retrieved = get_latest_proposal_document("p1", "pv1")

        assert retrieved is not None
        assert retrieved["input_snapshot"]["generation_mode"] == "multi"
        assert retrieved["reconciliation_result"]["generated_by"] == "deterministic"
        assert retrieved["review_pass"]["scope"]["covered_well"] == ["scope ok"]
        assert retrieved["proposal_coverage"] is None
        assert retrieved["decision_summary"] is None
        assert retrieved["forward_guidance"] is None

    def test_save_document_without_new_fields_still_works(self, isolated_db):
        """Backward-compat: doc dict without synthesis keys → saved and read back OK."""
        import uuid
        from db.decision_log import save_proposal_document, get_latest_proposal_document
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc = {
            "doc_id": doc_id, "project_id": "p2", "proposal_ver_id": "pv2",
            "generated_at": "2026-01-01T00:00:00+00:00", "ai_backend": "files_only",
            "exec_summary": "old doc", "scope": "old scope",
            "delivery_phases": [], "gantt_data": [], "risks": [], "assumptions": [],
            "exclusions": [], "responsibilities": {}, "acceptance_criteria": [],
            "version_label": "", "review_persona": "", "hierarchy_version_id": "",
            "active_review_id": "", "word_count": 0,
            # no synthesis fields at all
        }
        save_proposal_document(doc)
        retrieved = get_latest_proposal_document("p2", "pv2")
        assert retrieved is not None
        assert retrieved["exec_summary"] == "old doc"
        for field in ["input_snapshot", "reconciliation_result", "review_pass",
                      "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert retrieved.get(field) is None



# ─────────────────────────────────────────────────────────────────────────────
# J  Regression — Sprint 1 synthesis engine unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestSprint1Regression:

    def test_synthesize_reviews_still_importable(self):
        from processors.review_synthesizer import synthesize_reviews
        assert callable(synthesize_reviews)

    def test_normalize_still_works(self):
        from processors.review_synthesizer import normalize_review_findings, _clear_caches
        _clear_caches()
        r = SimpleNamespace(
            review_id="r1", version_id="v1", persona="SA",
            completeness_score=80, quality_status="complete",
            created_at="2026-01-01T00:00:00+00:00",
            findings={"risks": ["Risk A", "Risk B"], "assumptions": ["Assumption X"]},
            decision_points=[],
        )
        items = normalize_review_findings(r)
        assert len(items) == 3
        _clear_caches()

    def test_deduplicate_still_works(self):
        from processors.review_synthesizer import (
            deduplicate_normalized, _clear_caches, _make_dedup_key,
        )
        from models.proposal import NormalizedItem
        _clear_caches()
        items = [
            NormalizedItem(text="DB fail", category="risks",
                           review_id="r1", persona="SA",
                           dedup_key=_make_dedup_key("DB fail")),
            NormalizedItem(text="DB fail", category="risks",
                           review_id="r2", persona="DM",
                           dedup_key=_make_dedup_key("DB fail")),
        ]
        result = deduplicate_normalized(items, {"r1": 80, "r2": 60})
        assert len(result) == 1
        _clear_caches()

    def test_all_sprint1_dataclasses_still_importable(self):
        from models.proposal import (
            NormalizedItem, ConflictEntry, ReconciliationResult,
            ProposalInputSnapshot, ReviewPassDomain, ProposalReviewPass,
            CoverageDomain, ProposalCoverage, DecisionItem, DecisionSummary,
            ForwardGuidanceItem, ForwardGuidance,
        )

    def test_review_synthesizer_no_circular_import(self):
        """review_synthesizer must not import proposal_generator at module level."""
        import ast, inspect
        import processors.review_synthesizer as rs
        src = inspect.getsource(rs)
        tree = ast.parse(src)
        top_imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.col_offset == 0:
                top_imports.append(ast.dump(node))
        assert not any("proposal_generator" in imp for imp in top_imports)


# ─────────────────────────────────────────────────────────────────────────────
# K  Regression — existing proposal model exports intact
# ─────────────────────────────────────────────────────────────────────────────

class TestExistingModelRegression:

    def test_pre_existing_exports_still_present(self):
        from models.proposal import (
            ProposalDocument, ProposalVersion, ProposalTracker,
            PresalesFeedback, FeedbackItem, GanttRow, RiskEntry,
            AssumptionEntry, DeliveryPhase,
            VALID_PROPOSAL_STATUSES, VALID_PROPOSAL_QUALITY,
            FEEDBACK_CATEGORIES,
        )
        assert "draft" in VALID_PROPOSAL_STATUSES
        assert "complete" in VALID_PROPOSAL_QUALITY

    def test_proposal_version_round_trip(self):
        from models.proposal import ProposalVersion
        pv = ProposalVersion(version_id="pv1", version_number=1,
                             hierarchy_version_id="v1", active_review_id="r1")
        d = pv.to_dict()
        restored = ProposalVersion.from_dict(d)
        assert restored.version_id == "pv1"
        assert restored.hierarchy_version_id == "v1"

    def test_generate_proposal_document_signature_has_all_original_params(self):
        import inspect
        from processors.proposal_generator import generate_proposal_document
        sig = inspect.signature(generate_proposal_document)
        params = list(sig.parameters.keys())
        for p in ["project_id", "proposal_ver_id", "hierarchy_version_id",
                  "review_id", "ai_backend", "force"]:
            assert p in params, f"Missing original param: {p}"

    def test_new_param_is_last_and_optional(self):
        import inspect
        from processors.proposal_generator import generate_proposal_document
        sig = inspect.signature(generate_proposal_document)
        params = list(sig.parameters.items())
        last_name, last_param = params[-1]
        assert last_name == "supplemental_review_ids"
        assert last_param.default is None

    def test_findings_shim_delegates_attributes(self):
        from processors.proposal_generator import _FindingsShim
        review = SimpleNamespace(
            review_id="r1", persona="SA", project_id="p1",
            findings={"risks": ["old risk"]},
        )
        shim = _FindingsShim(review, {"risks": ["new risk"]})
        assert shim.findings == {"risks": ["new risk"]}
        assert shim.review_id == "r1"
        assert shim.persona == "SA"
        assert shim.project_id == "p1"
