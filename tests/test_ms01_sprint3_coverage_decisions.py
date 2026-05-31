"""Sprint 3 Tests — PDAE-MS-01: Proposal Coverage + Decision Summary.

Covers all acceptance criteria from stories S3-01 and S3-02, plus
full regression for all prior sprints.

Sections
────────
A  compute_proposal_coverage — S3-01 unit tests (deterministic, no DB)
B  _run_decision_summary — S3-02 unit tests (deterministic path only)
C  Generator integration — coverage + decision_summary wired end-to-end
D  DB persistence — proposal_coverage + decision_summary round-trip
E  Sprint 1 + 2 regression — no prior behaviour broken
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Imports under test ────────────────────────────────────────────────────────
from processors.review_synthesizer import (
    compute_proposal_coverage,
    _run_decision_summary,
    _COVERAGE_SIGNALS,
    _DS_BLOCKER_KEYWORDS,
    merge_decision_points,
    extract_scope_themes,
    _clear_caches,
)
from models.proposal import (
    ProposalCoverage, CoverageDomain,
    DecisionSummary, DecisionItem,
    ProposalReviewPass, ReviewPassDomain,
    ReconciliationResult, ConflictEntry,
)


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_synth_caches():
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    import db.database as _dbmod
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(_dbmod, "_DATA_DIR_OVERRIDE", str(tmp_path))
    monkeypatch.setattr(_dbmod, "_BASE_DIR", tmp_path)
    monkeypatch.setattr(_dbmod, "_thread_local", threading.local())
    from db.database import get_db
    db = get_db()
    yield db
    if hasattr(_dbmod._thread_local, "db") and _dbmod._thread_local.db:
        try:
            _dbmod._thread_local.db.close()
        except Exception:
            pass


def _make_review(
    review_id="r1", version_id="v1", persona="SA",
    quality_status="complete", completeness_score=80,
    project_id="proj1", findings=None, decision_points=None,
):
    return SimpleNamespace(
        review_id=review_id, version_id=version_id,
        persona=persona, quality_status=quality_status,
        completeness_score=completeness_score,
        project_id=project_id,
        created_at="2026-01-01T00:00:00+00:00",
        findings=findings or {
            "risks":        ["Security authentication failure risk"],
            "assumptions":  ["Client provides environments"],
            "dependencies": ["Azure AD integration"],
            "constraints":  ["Go-live must not exceed 12 weeks"],
            "action_items": ["Set up CI/CD pipeline", "Monitor SLA metrics"],
        },
        decision_points=decision_points or [],
        weaknesses=[], deep_dive=None, feedback=None,
        summary="", questions=[], output={},
    )


def _make_version(version_id="v1", label="v1", scope="Migrate legacy ERP to Azure.",
                  active_review_id="r1"):
    return SimpleNamespace(
        version_id=version_id, label=label, scope=scope,
        active_review_id=active_review_id,
        included_artifacts=[], stats={},
    )


def _recon_dict(findings: Dict[str, List[str]]) -> Dict[str, Any]:
    """Build minimal reconciliation_result dict for coverage tests."""
    return {
        "reconciled_findings": findings,
        "contradictions": [], "overlaps_resolved": [],
        "reconciliation_notes": "",
        "source_review_ids": ["r1"], "anchor_review_id": "r1",
        "generated_by": "deterministic", "generated_at": "2026-01-01T00:00:00+00:00",
    }


def _make_review_pass(domain_weak: Dict[str, List[str]] = None,
                      domain_blockers: Dict[str, List[str]] = None) -> ProposalReviewPass:
    """Build a minimal ProposalReviewPass for coverage tests."""
    def _dom(domain: str) -> ReviewPassDomain:
        return ReviewPassDomain(
            covered_well=[],
            still_weak=(domain_weak or {}).get(domain, []),
            may_block_signoff=(domain_blockers or {}).get(domain, []),
        )
    return ProposalReviewPass(
        scope=_dom("scope"), architecture=_dom("architecture"),
        delivery=_dom("delivery"), security_compliance=_dom("security_compliance"),
        operations=_dom("operations"), commercials=_dom("commercials"),
        generated_by="files_only", generated_at="2026-01-01T00:00:00+00:00",
    )



# ═════════════════════════════════════════════════════════════════════════════
# A  compute_proposal_coverage — S3-01
# ═════════════════════════════════════════════════════════════════════════════

class TestComputeProposalCoverage:
    """All acceptance criteria from S3-01."""

    # ── AC1: zero security-signal risks → Not Yet Addressed ──────────────────

    def test_ac1_zero_security_risks_not_yet_addressed(self):
        """AC1: Zero security-signal risks → security_compliance == 'Not Yet Addressed'."""
        recon = _recon_dict({
            "risks":       ["Timeline slippage risk", "Resource availability risk"],
            "action_items": ["Deploy infrastructure"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, None, [])
        assert result.security_compliance.status == "Not Yet Addressed"

    def test_ac1_gap_notes_non_empty_when_not_addressed(self):
        """AC1 corollary: gap_notes is non-empty when status is Not Yet Addressed."""
        recon = _recon_dict({"risks": [], "action_items": [], "assumptions": [],
                              "dependencies": [], "constraints": []})
        result = compute_proposal_coverage(recon, None, [])
        assert result.security_compliance.gap_notes != ""

    # ── AC2: three security risks, no blocker → Addressed ────────────────────

    def test_ac2_three_security_risks_no_blocker_addressed(self):
        """AC2: Three security risks, no blocker in review_pass → 'Addressed'."""
        recon = _recon_dict({
            "risks": [
                "Security misconfiguration in IAM roles",
                "Compliance gap in GDPR data handling",
                "Authentication tokens not rotated regularly",
            ],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        rp = _make_review_pass()  # no blockers, no weak
        result = compute_proposal_coverage(recon, rp, [])
        assert result.security_compliance.status == "Addressed"

    def test_ac2_gap_notes_empty_when_addressed(self):
        """AC2 corollary: gap_notes is empty when status is 'Addressed'."""
        recon = _recon_dict({
            "risks": [
                "Security auth failure risk",
                "GDPR compliance gap risk",
            ],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        assert result.security_compliance.gap_notes == ""

    # ── AC3: one security risk + still_weak → Partial ────────────────────────

    def test_ac3_one_security_risk_domain_weak_partial(self):
        """AC3: One security risk + domain flagged in still_weak → 'Partial'."""
        recon = _recon_dict({
            "risks":       ["Security authentication failure risk"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        rp = _make_review_pass(
            domain_weak={"security_compliance": ["Security section lacks detail"]}
        )
        result = compute_proposal_coverage(recon, rp, [])
        assert result.security_compliance.status == "Partial"

    def test_ac3_one_security_risk_no_weak_also_partial(self):
        """One security item only (count=1) → Partial even without still_weak."""
        recon = _recon_dict({
            "risks":       ["Auth token not rotated"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        assert result.security_compliance.status == "Partial"

    # ── AC4: matched_themes populated ────────────────────────────────────────

    def test_ac4_matched_themes_populated(self):
        """AC4: matched_themes lists themes that triggered the domain match."""
        recon = _recon_dict({
            "risks": ["Azure integration failure risk"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        themes = ["azure migration", "data pipeline"]
        result = compute_proposal_coverage(recon, _make_review_pass(), themes)
        # "azure migration" should map to architecture domain (platform name)
        assert isinstance(result.architecture.matched_themes, list)

    def test_ac4_matched_themes_is_list_for_all_domains(self):
        """AC4: matched_themes is a list (not None) for every domain."""
        result = compute_proposal_coverage(_recon_dict({}), None, [])
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert isinstance(getattr(result, domain).matched_themes, list)

    # ── AC5: gap_notes non-empty when Partial or Not Yet Addressed ────────────

    def test_ac5_gap_notes_non_empty_for_partial(self):
        """AC5: gap_notes non-empty when status == 'Partial'."""
        recon = _recon_dict({
            "risks": ["Auth token risk"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        partial_domains = [
            getattr(result, d)
            for d in ["scope", "architecture", "delivery",
                      "security_compliance", "operations", "commercials"]
            if getattr(result, d).status == "Partial"
        ]
        for dom in partial_domains:
            assert dom.gap_notes != "", f"gap_notes empty for Partial domain"

    def test_ac5_gap_notes_non_empty_for_not_yet_addressed(self):
        """AC5: gap_notes non-empty when status == 'Not Yet Addressed'."""
        recon = _recon_dict({})
        result = compute_proposal_coverage(recon, None, [])
        not_addressed = [
            getattr(result, d)
            for d in ["scope", "architecture", "delivery",
                      "security_compliance", "operations", "commercials"]
            if getattr(result, d).status == "Not Yet Addressed"
        ]
        for dom in not_addressed:
            assert dom.gap_notes != ""

    # ── AC6: deterministic ───────────────────────────────────────────────────

    def test_ac6_same_inputs_same_output(self):
        """AC6: Same inputs always produce same output (status, themes, gap_notes).
        computed_at is excluded — it is a wall-clock timestamp, not a deterministic value.
        """
        recon = _recon_dict({
            "risks":       ["Security auth risk", "GDPR compliance risk"],
            "action_items": ["Deploy monitoring SLA dashboard"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        r1 = compute_proposal_coverage(recon, _make_review_pass(), ["azure"])
        r2 = compute_proposal_coverage(recon, _make_review_pass(), ["azure"])

        def _strip_timestamp(d: dict) -> dict:
            return {k: v for k, v in d.items() if k != "computed_at"}

        assert _strip_timestamp(r1.to_dict()) == _strip_timestamp(r2.to_dict())

    # ── AC7: computed_at is ISO 8601 UTC timestamp ────────────────────────────

    def test_ac7_computed_at_is_iso_timestamp(self):
        """AC7: computed_at is a valid ISO 8601 UTC timestamp."""
        import re
        result = compute_proposal_coverage(_recon_dict({}), None, [])
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.computed_at)

    # ── Additional status boundary tests ─────────────────────────────────────

    def test_operations_addressed_with_sla_and_monitoring_items(self):
        """Two or more ops-signal items → operations == 'Addressed'."""
        recon = _recon_dict({
            "risks":       ["SLA breach risk under peak load"],
            "action_items": ["Set up monitoring alerting pipeline"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        assert result.operations.status == "Addressed"

    def test_commercials_not_addressed_without_budget_items(self):
        """No commercial-signal items → commercials == 'Not Yet Addressed'."""
        recon = _recon_dict({
            "risks":       ["Technical architecture risk"],
            "action_items": ["Deploy infrastructure"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, None, [])
        assert result.commercials.status == "Not Yet Addressed"

    def test_scope_addressed_with_multiple_scope_items(self):
        """Multiple scope-signal items → scope == 'Addressed'."""
        recon = _recon_dict({
            "risks":       ["Out of scope items may be added mid-delivery"],
            "action_items": [
                "Deliver in-scope API integration",
                "Validate delivery objectives with stakeholders",
            ],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        assert result.scope.status == "Addressed"

    def test_blocker_in_review_pass_downgrades_addressed_to_partial(self):
        """Addressed domain but review_pass has blocker → downgraded to Partial."""
        recon = _recon_dict({
            "risks": [
                "Budget overrun commercial risk",
                "Contract terms not yet finalised",
            ],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        rp = _make_review_pass(
            domain_blockers={"commercials": ["Contract sign-off pending"]}
        )
        result = compute_proposal_coverage(recon, rp, [])
        assert result.commercials.status == "Partial"

    def test_source_theme_count_matches_themes_list_length(self):
        """source_theme_count == len(scope_themes) passed in."""
        themes = ["azure migration", "data warehouse", "kubernetes"]
        result = compute_proposal_coverage(_recon_dict({}), None, themes)
        assert result.source_theme_count == 3

    def test_none_reconciliation_uses_empty_findings(self):
        """None reconciliation → graceful empty findings, no error."""
        result = compute_proposal_coverage(None, None, [])
        assert isinstance(result, ProposalCoverage)
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert getattr(result, domain).status == "Not Yet Addressed"

    def test_all_six_domains_present_in_result(self):
        """ProposalCoverage always has all six domain attributes."""
        result = compute_proposal_coverage(_recon_dict({}), None, [])
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert hasattr(result, domain)
            assert isinstance(getattr(result, domain), CoverageDomain)

    def test_review_pass_as_dict_also_accepted(self):
        """review_pass passed as plain dict (from DB deserialization) works."""
        rp_dict = {
            "scope":               {"covered_well": [], "still_weak": ["weak"], "may_block_signoff": []},
            "architecture":        {"covered_well": [], "still_weak": [], "may_block_signoff": []},
            "delivery":            {"covered_well": [], "still_weak": [], "may_block_signoff": []},
            "security_compliance": {"covered_well": [], "still_weak": [], "may_block_signoff": []},
            "operations":          {"covered_well": [], "still_weak": [], "may_block_signoff": []},
            "commercials":         {"covered_well": [], "still_weak": [], "may_block_signoff": []},
            "generated_by": "files_only", "generated_at": "2026-01-01T00:00:00+00:00",
        }
        recon = _recon_dict({
            "risks":       ["Scope creep risk", "delivery delay risk"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        result = compute_proposal_coverage(recon, rp_dict, [])
        # scope domain: 2 scope-signal items but still_weak → Partial
        assert result.scope.status == "Partial"

    def test_reconciliation_as_object_with_attribute_accepted(self):
        """ReconciliationResult dataclass accepted (not just dict)."""
        recon_obj = ReconciliationResult(
            reconciled_findings={
                "risks": ["Security auth failure", "GDPR compliance gap"],
                "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
            },
        )
        result = compute_proposal_coverage(recon_obj, _make_review_pass(), [])
        assert result.security_compliance.status == "Addressed"



# ═════════════════════════════════════════════════════════════════════════════
# B  _run_decision_summary — S3-02
# ═════════════════════════════════════════════════════════════════════════════

class TestRunDecisionSummary:
    """All acceptance criteria from S3-02 — deterministic path only."""

    def _run(self, decisions, notes="", review_ids=None):
        return _run_decision_summary(
            merged_decisions=decisions,
            reconciliation_notes=notes,
            selected_review_ids=review_ids or ["r1"],
            ai_backend="files_only",
        )

    # ── AC2: files_only classification by status field ───────────────────────

    def test_ac2_addressed_status_goes_to_confirmed(self):
        """AC2: decision_points with status='addressed' → confirmed list."""
        decisions = [
            {"text": "Platform selected: Azure", "category": "arch",
             "status": "addressed", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.confirmed) == 1
        assert result.confirmed[0].text == "Platform selected: Azure"
        assert len(result.open) == 0

    def test_ac2_open_status_goes_to_open(self):
        """AC2: decision_points with status='open' → open list."""
        decisions = [
            {"text": "DR strategy not yet decided", "category": "ops",
             "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.open) == 1
        assert result.confirmed == []

    def test_ac2_validated_status_goes_to_confirmed(self):
        """AC2 extension: status='validated' also maps to confirmed."""
        decisions = [
            {"text": "Architecture pattern validated", "category": "arch",
             "status": "validated", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.confirmed) == 1

    def test_ac2_mixed_statuses_split_correctly(self):
        """AC2: mixed addressed/open → each in correct bucket."""
        decisions = [
            {"text": "Cloud vendor chosen", "category": "arch",
             "status": "addressed", "source_review_id": "r1"},
            {"text": "Security model TBD", "category": "sec",
             "status": "open", "source_review_id": "r1"},
            {"text": "Go-live date agreed", "category": "delivery",
             "status": "addressed", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.confirmed) == 2
        assert len(result.open) == 1

    # ── AC3: blocker keyword detection ───────────────────────────────────────

    def test_ac3_must_keyword_triggers_blocker(self):
        """AC3: item with 'must' → appears in sign_off_blockers."""
        decisions = [
            {"text": "Security audit must be completed before go-live",
             "category": "sec", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert any("must" in b.text.lower() for b in result.sign_off_blockers)

    def test_ac3_required_keyword_triggers_blocker(self):
        """AC3: item with 'required' → sign_off_blockers."""
        decisions = [
            {"text": "Board approval required before contract signature",
             "category": "commercial", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.sign_off_blockers) == 1

    def test_ac3_block_keyword_triggers_blocker(self):
        """AC3: item containing 'block' → sign_off_blockers."""
        decisions = [
            {"text": "Unresolved dependency blocks delivery kick-off",
             "category": "delivery", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.sign_off_blockers) >= 1

    def test_ac3_prevent_keyword_triggers_blocker(self):
        """AC3: item containing 'prevent' → sign_off_blockers."""
        decisions = [
            {"text": "Licensing gap may prevent deployment in EU region",
             "category": "compliance", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.sign_off_blockers) >= 1

    def test_ac3_no_blocker_keyword_no_blocker_entry(self):
        """AC3 boundary: open item without blocker keywords → not in sign_off_blockers."""
        decisions = [
            {"text": "DR strategy still under review",
             "category": "ops", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert result.sign_off_blockers == []

    # ── AC4: sign_off_blockers is strict subset of open ──────────────────────

    def test_ac4_blockers_are_subset_of_open(self):
        """AC4: sign_off_blockers is always a subset of open (never in confirmed)."""
        decisions = [
            {"text": "Platform selection must be finalised",
             "category": "arch", "status": "open", "source_review_id": "r1"},
            {"text": "Cloud vendor chosen",
             "category": "arch", "status": "addressed", "source_review_id": "r1"},
            {"text": "DR strategy blocks sign-off",
             "category": "ops", "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        open_texts = {i.text for i in result.open}
        confirmed_texts = {i.text for i in result.confirmed}
        for blocker in result.sign_off_blockers:
            assert blocker.text in open_texts, "Blocker not in open list"
            assert blocker.text not in confirmed_texts, "Blocker also in confirmed"

    # ── AC5: empty decision points → all three lists empty ───────────────────

    def test_ac5_no_decision_points_all_empty(self):
        """AC5: No decision points → all three lists empty, no error."""
        result = self._run([])
        assert result.confirmed == []
        assert result.open == []
        assert result.sign_off_blockers == []

    def test_ac5_none_decision_points_no_error(self):
        """AC5: Empty list from review with no decision_points → no error."""
        reviews = [_make_review(decision_points=[])]
        merged = merge_decision_points(reviews)
        result = self._run(merged)
        assert isinstance(result, DecisionSummary)

    # ── AC6: source_review_ids matches selected review set ───────────────────

    def test_ac6_source_review_ids_matches_selected(self):
        """AC6: source_review_ids matches the full selected review set."""
        result = self._run([], review_ids=["r1", "r2", "r3"])
        assert result.source_review_ids == ["r1", "r2", "r3"]

    # ── Additional quality checks ─────────────────────────────────────────────

    def test_generated_by_is_files_only_for_deterministic(self):
        result = self._run([])
        assert result.generated_by == "files_only"

    def test_generated_at_is_iso_timestamp(self):
        import re
        result = self._run([])
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.generated_at)

    def test_decision_item_fields_populated(self):
        """Each DecisionItem has text, category, source_review_id."""
        decisions = [
            {"text": "Choose DB platform", "category": "data",
             "status": "open", "source_review_id": "r2"},
        ]
        result = self._run(decisions)
        item = result.open[0]
        assert item.text == "Choose DB platform"
        assert item.category == "data"
        assert item.source_review_id == "r2"

    def test_unknown_status_defaults_to_open(self):
        """Unrecognised status treated as open (defensive)."""
        decisions = [
            {"text": "Some decision", "category": "general",
             "status": "unknown_status", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.open) == 1
        assert len(result.confirmed) == 0

    def test_multiple_blockers_all_appear(self):
        """Multiple open items with blocker keywords → all in sign_off_blockers."""
        decisions = [
            {"text": "Contract approval required", "category": "commercial",
             "status": "open", "source_review_id": "r1"},
            {"text": "Pen test must pass before go-live", "category": "security",
             "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        assert len(result.sign_off_blockers) == 2

    def test_to_dict_round_trip(self):
        """DecisionSummary.to_dict() / from_dict() round-trips correctly."""
        decisions = [
            {"text": "Platform chosen", "category": "arch",
             "status": "addressed", "source_review_id": "r1"},
            {"text": "DR strategy must be confirmed", "category": "ops",
             "status": "open", "source_review_id": "r1"},
        ]
        result = self._run(decisions)
        d = result.to_dict()
        restored = DecisionSummary.from_dict(d)
        assert len(restored.confirmed) == len(result.confirmed)
        assert len(restored.open) == len(result.open)
        assert len(restored.sign_off_blockers) == len(result.sign_off_blockers)



# ═════════════════════════════════════════════════════════════════════════════
# C  Generator integration — coverage + decision_summary wired end-to-end
# ═════════════════════════════════════════════════════════════════════════════

class TestGeneratorIntegration:
    """End-to-end: generate_proposal_document() populates both new fields."""

    def _generate(self, isolated_db, findings=None, decision_points=None,
                  scope="Deliver Azure migration with security audit.", supp_ids=None,
                  extra_reviews=()):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version(scope=scope)
        r = _make_review(
            findings=findings or {
                "risks":       ["Security misconfiguration risk", "Budget overrun risk"],
                "assumptions": ["Client provides environments"],
                "dependencies":["Azure AD integration"],
                "constraints": ["Contract must be signed before kick-off"],
                "action_items":["Set up CI/CD", "Monitor SLA"],
            },
            decision_points=decision_points or [],
        )
        store = MagicMock()
        store.get_version.return_value = v
        rev_map = {r.review_id: r}
        for er in extra_reviews:
            rev_map[er.review_id] = er
        store.get_review.side_effect = lambda rid: rev_map.get(rid)

        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness",
                   return_value={"level": "High", "open_decisions": 0, "open_weaknesses": 0}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            return generate_proposal_document(
                "proj1", "pv1", "v1", "r1",
                ai_backend="files_only",
                supplemental_review_ids=supp_ids,
            )

    def test_proposal_coverage_populated_on_single_review(self, isolated_db):
        """proposal_coverage is not None on single-review path."""
        result = self._generate(isolated_db)
        assert result.get("proposal_coverage") is not None

    def test_decision_summary_populated_on_single_review(self, isolated_db):
        """decision_summary is not None on single-review path."""
        result = self._generate(isolated_db)
        assert result.get("decision_summary") is not None

    def test_security_domain_addressed_when_two_security_risks(self, isolated_db):
        """Two security risks → security_compliance == 'Addressed' or 'Partial'
        (Partial is also valid if review_pass flagged weak)."""
        result = self._generate(isolated_db, findings={
            "risks": [
                "Security IAM misconfiguration risk",
                "GDPR compliance audit required",
            ],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        })
        sec_status = result["proposal_coverage"]["security_compliance"]["status"]
        assert sec_status in ("Addressed", "Partial"), f"Unexpected: {sec_status}"

    def test_security_not_addressed_without_security_risks(self, isolated_db):
        """No security-signal content → security_compliance == 'Not Yet Addressed'."""
        result = self._generate(isolated_db, findings={
            "risks":       ["Timeline risk", "Budget pressure"],
            "action_items":["Deploy infrastructure"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        assert result["proposal_coverage"]["security_compliance"]["status"] == "Not Yet Addressed"

    def test_blocker_keyword_in_dp_creates_sign_off_blocker(self, isolated_db):
        """Decision point with 'must' keyword → sign_off_blockers non-empty."""
        dps = [{"text": "Security audit must pass before sign-off",
                "category": "security", "status": "open"}]
        result = self._generate(isolated_db, decision_points=dps)
        blockers = result["decision_summary"]["sign_off_blockers"]
        assert len(blockers) >= 1

    def test_addressed_dp_goes_to_confirmed(self, isolated_db):
        """Decision point with status=addressed → confirmed list."""
        dps = [{"text": "Azure selected as cloud platform",
                "category": "arch", "status": "addressed"}]
        result = self._generate(isolated_db, decision_points=dps)
        confirmed = result["decision_summary"]["confirmed"]
        assert len(confirmed) >= 1

    def test_no_decision_points_all_buckets_empty(self, isolated_db):
        """No decision_points → all three DS buckets are empty lists."""
        result = self._generate(isolated_db, decision_points=[])
        ds = result["decision_summary"]
        assert ds["confirmed"] == []
        assert ds["open"] == []
        assert ds["sign_off_blockers"] == []

    def test_coverage_deterministic_across_identical_calls(self, isolated_db):
        """Two identical calls produce identical proposal_coverage domain statuses.
        computed_at is excluded — it is a wall-clock timestamp, not deterministic.
        """
        r1 = self._generate(isolated_db)
        r2 = self._generate(isolated_db)

        def _strip(cov: dict) -> dict:
            return {k: (v if k != "computed_at" else None)
                    for k, v in cov.items()}

        assert _strip(r1["proposal_coverage"]) == _strip(r2["proposal_coverage"])

    def test_all_six_coverage_domains_present(self, isolated_db):
        """proposal_coverage always contains all six domain keys."""
        result = self._generate(isolated_db)
        cov = result["proposal_coverage"]
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in cov, f"Missing domain: {domain}"

    def test_decision_summary_has_required_keys(self, isolated_db):
        """decision_summary dict always has confirmed, open, sign_off_blockers."""
        result = self._generate(isolated_db)
        ds = result["decision_summary"]
        for key in ["confirmed", "open", "sign_off_blockers",
                    "source_review_ids", "generated_by", "generated_at"]:
            assert key in ds, f"Missing key: {key}"

    def test_existing_fields_unaffected_by_sprint3(self, isolated_db):
        """Sprint 3 wiring must not break existing proposal fields."""
        result = self._generate(isolated_db)
        assert result.get("exec_summary", "") != ""
        assert isinstance(result.get("delivery_phases"), list)
        assert len(result["delivery_phases"]) > 0
        assert result.get("doc_id", "").startswith("doc_")

    def test_review_pass_still_populated(self, isolated_db):
        """Sprint 2 review_pass still populated alongside Sprint 3 fields."""
        result = self._generate(isolated_db)
        assert result.get("review_pass") is not None
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in result["review_pass"]

    def test_reconciliation_result_none_on_single_review(self, isolated_db):
        """Single-review path: reconciliation_result still None (Sprint 2 contract)."""
        result = self._generate(isolated_db)
        assert result.get("reconciliation_result") is None

    def test_generation_mode_single_on_no_supplementals(self, isolated_db):
        """Single-review path: generation_mode == 'single'."""
        result = self._generate(isolated_db)
        assert result["input_snapshot"]["generation_mode"] == "single"


# ═════════════════════════════════════════════════════════════════════════════
# D  DB persistence — proposal_coverage + decision_summary
# ═════════════════════════════════════════════════════════════════════════════

class TestDBPersistence:
    """proposal_coverage and decision_summary round-trip through DB correctly."""

    def test_proposal_coverage_persisted_and_retrieved(self, isolated_db):
        """proposal_coverage written to DB and read back intact."""
        import uuid
        from db.decision_log import save_proposal_document, get_latest_proposal_document

        coverage = ProposalCoverage(
            scope=CoverageDomain(status="Addressed", matched_themes=["erp migration"], gap_notes=""),
            architecture=CoverageDomain(status="Partial", matched_themes=[], gap_notes="Missing cloud detail"),
            delivery=CoverageDomain(status="Addressed", matched_themes=[], gap_notes=""),
            security_compliance=CoverageDomain(status="Not Yet Addressed", matched_themes=[], gap_notes="No security content"),
            operations=CoverageDomain(status="Partial", matched_themes=[], gap_notes="Limited ops coverage"),
            commercials=CoverageDomain(status="Not Yet Addressed", matched_themes=[], gap_notes="No commercial items"),
            source_theme_count=1, computed_at="2026-01-01T00:00:00+00:00",
        )
        ds = DecisionSummary(
            confirmed=[DecisionItem(text="Azure chosen", category="arch", source_review_id="r1")],
            open=[DecisionItem(text="DR strategy must be confirmed", category="ops", source_review_id="r1")],
            sign_off_blockers=[DecisionItem(text="DR strategy must be confirmed", category="ops", source_review_id="r1")],
            source_review_ids=["r1"],
            generated_by="files_only", generated_at="2026-01-01T00:00:00+00:00",
        )

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc = {
            "doc_id": doc_id, "project_id": "p1", "proposal_ver_id": "pv_s3",
            "generated_at": "2026-01-01T00:00:00+00:00", "ai_backend": "files_only",
            "exec_summary": "test", "scope": "scope",
            "delivery_phases": [], "gantt_data": [], "risks": [], "assumptions": [],
            "exclusions": [], "responsibilities": {}, "acceptance_criteria": [],
            "version_label": "", "review_persona": "", "hierarchy_version_id": "v1",
            "active_review_id": "r1", "word_count": 0,
            "input_snapshot": {"anchor_review_id": "r1", "selected_review_ids": ["r1"],
                               "selected_version_id": "v1", "generation_mode": "single",
                               "captured_at": "2026-01-01T00:00:00+00:00"},
            "reconciliation_result": None,
            "review_pass": None,
            "proposal_coverage": coverage.to_dict(),
            "decision_summary": ds.to_dict(),
            "forward_guidance": None,
        }
        save_proposal_document(doc)
        retrieved = get_latest_proposal_document("p1", "pv_s3")

        assert retrieved is not None

        # Coverage round-trip
        cov_rt = retrieved["proposal_coverage"]
        assert cov_rt["scope"]["status"] == "Addressed"
        assert cov_rt["architecture"]["status"] == "Partial"
        assert cov_rt["security_compliance"]["status"] == "Not Yet Addressed"
        assert cov_rt["source_theme_count"] == 1

        # Decision summary round-trip
        ds_rt = retrieved["decision_summary"]
        assert len(ds_rt["confirmed"]) == 1
        assert ds_rt["confirmed"][0]["text"] == "Azure chosen"
        assert len(ds_rt["open"]) == 1
        assert len(ds_rt["sign_off_blockers"]) == 1
        assert ds_rt["sign_off_blockers"][0]["text"] == "DR strategy must be confirmed"

    def test_null_coverage_and_ds_reads_back_as_none(self, isolated_db):
        """Rows without coverage/ds (legacy) read back as None."""
        import uuid
        from db.decision_log import _row_to_doc

        row = {
            "doc_id": f"doc_{uuid.uuid4().hex[:8]}",
            "project_id": "p1", "proposal_ver_id": "pv_legacy",
            "generated_at": "2026-01-01T00:00:00+00:00", "ai_backend": "files_only",
            "exec_summary": "", "scope": "", "delivery_phases": None, "gantt_data": None,
            "risks": None, "assumptions": None, "exclusions": None,
            "responsibilities": None, "acceptance_criteria": None,
            "version_label": "", "review_persona": "", "hierarchy_version_id": "",
            "active_review_id": "", "word_count": 0,
            # deliberately omit proposal_coverage and decision_summary
        }
        result = _row_to_doc(row)
        assert result["proposal_coverage"] is None
        assert result["decision_summary"] is None

    def test_generator_writes_both_fields_to_db(self, isolated_db):
        """End-to-end: generator call writes proposal_coverage + decision_summary to DB."""
        from processors.proposal_generator import generate_proposal_document

        v = _make_version()
        r = _make_review(findings={
            "risks": ["Security audit required", "Budget overrun"],
            "action_items": ["Deploy monitoring SLA"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })

        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")

        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT proposal_coverage, decision_summary FROM proposal_documents WHERE doc_id=?",
            (doc_id,),
        )
        assert row is not None
        assert row["proposal_coverage"] is not None, "proposal_coverage not persisted"
        assert row["decision_summary"] is not None, "decision_summary not persisted"

        import json
        cov = json.loads(row["proposal_coverage"])
        ds  = json.loads(row["decision_summary"])
        # Basic structure checks
        assert "security_compliance" in cov
        assert "confirmed" in ds
        assert "open" in ds
        assert "sign_off_blockers" in ds



# ═════════════════════════════════════════════════════════════════════════════
# E  Sprint 1 + 2 regression — no prior behaviour broken
# ═════════════════════════════════════════════════════════════════════════════

class TestSprint12Regression:
    """Guard all prior sprint contracts against Sprint 3 changes."""

    # ── Sprint 1 ─────────────────────────────────────────────────────────────

    def test_s1_synthesize_reviews_unaffected(self):
        from processors.review_synthesizer import synthesize_reviews
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings={"risks": ["Risk A"], "assumptions": [],
                                         "dependencies": [], "constraints": [], "action_items": []})
        sup = _make_review(review_id="r2", version_id="v1",
                            findings={"risks": ["Risk B"], "assumptions": [],
                                      "dependencies": [], "constraints": [], "action_items": []})
        result = synthesize_reviews(anchor, [sup], "scope", "files_only")
        assert result.generated_by == "deterministic"
        assert "Risk A" in result.reconciled_findings["risks"]
        assert "Risk B" in result.reconciled_findings["risks"]

    def test_s1_normalize_unaffected(self):
        from processors.review_synthesizer import normalize_review_findings
        r = _make_review(findings={"risks": ["A risk"], "assumptions": ["An assumption"],
                                    "dependencies": [], "constraints": [], "action_items": []})
        items = normalize_review_findings(r)
        assert len(items) == 2

    def test_s1_all_new_dataclasses_importable(self):
        from models.proposal import (
            NormalizedItem, ConflictEntry, ReconciliationResult,
            ProposalInputSnapshot, ReviewPassDomain, ProposalReviewPass,
            CoverageDomain, ProposalCoverage, DecisionItem, DecisionSummary,
            ForwardGuidanceItem, ForwardGuidance,
        )

    # ── Sprint 2 ─────────────────────────────────────────────────────────────

    def test_s2_generate_signature_unchanged(self):
        import inspect
        from processors.proposal_generator import generate_proposal_document
        params = list(inspect.signature(generate_proposal_document).parameters.keys())
        for p in ["project_id", "proposal_ver_id", "hierarchy_version_id",
                  "review_id", "ai_backend", "force", "supplemental_review_ids"]:
            assert p in params

    def test_s2_review_pass_still_always_populated(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        assert result.get("review_pass") is not None

    def test_s2_input_snapshot_still_populated(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        snap = result.get("input_snapshot")
        assert snap is not None
        assert snap["generation_mode"] == "single"

    def test_s2_reconciliation_result_none_on_single_review(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        assert result.get("reconciliation_result") is None

    def test_s2_old_6param_call_still_works(self, isolated_db):
        """Old call sites with no supplemental_review_ids arg must still work."""
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document(
                "proj1", "pv1", "v1", "r1", "files_only", False
            )
        assert "error" not in result
        assert result.get("doc_id", "").startswith("doc_")

    def test_s2_db_columns_all_present(self, isolated_db):
        cols = {r[1] for r in isolated_db.conn.execute(
            "PRAGMA table_info(proposal_documents)"
        ).fetchall()}
        for col in ["input_snapshot", "reconciliation_result", "review_pass",
                    "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert col in cols

    def test_s2_handler_still_validates_supplemental_as_list(self):
        from handlers.proposal import handle_generate_proposal_doc
        responses, statuses = [], []

        def respond(payload, status=200):
            responses.append(payload)
            statuses.append(status)

        with patch("services.proposal.generate_proposal_doc") as mock_svc:
            mock_svc.return_value = {"doc_id": "x"}
            handle_generate_proposal_doc("proj1", {
                "proposal_ver_id": "pv1", "hierarchy_version_id": "v1",
                "review_id": "r1", "supplemental_review_ids": "r2",
            }, respond)
        assert statuses[0] == 422

    # ── Existing baseline model exports ──────────────────────────────────────

    def test_existing_model_exports_intact(self):
        from models.proposal import (
            ProposalDocument, ProposalVersion, ProposalTracker,
            PresalesFeedback, FeedbackItem, GanttRow, RiskEntry,
            AssumptionEntry, DeliveryPhase,
            VALID_PROPOSAL_STATUSES, VALID_PROPOSAL_QUALITY,
        )
        assert "draft" in VALID_PROPOSAL_STATUSES
        assert "complete" in VALID_PROPOSAL_QUALITY

    def test_proposal_document_six_synthesis_fields_default_none(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument()
        for f in ["input_snapshot", "reconciliation_result", "review_pass",
                  "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert getattr(doc, f) is None
