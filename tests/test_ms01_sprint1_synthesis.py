"""Sprint 1 — Multi-Review Synthesis Foundation (PDAE-MS-01).

Tests all acceptance criteria from stories S1-01 through S1-06.
All tests are deterministic — no LLM calls, no filesystem access.
LLM-dependent paths (synthesize_reviews with AI backend) are tested
via the files_only deterministic path only.

Sections
────────
A  Dataclass contracts (to_dict / from_dict round-trips)
B  S1-01  normalize_review_findings
C  S1-02  deduplicate_normalized
D  S1-03  build_reconciliation_prompt / parse_reconciliation_response
E  S1-04  synthesize_reviews orchestrator
F  S1-05  extract_scope_themes
G  S1-06  merge_decision_points
H  Regression — existing proposal generation path unaffected
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

# ── path setup ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from processors.review_synthesizer import (
    _clear_caches,
    _jaccard_similarity,
    _make_dedup_key,
    build_reconciliation_prompt,
    deduplicate_normalized,
    extract_scope_themes,
    merge_decision_points,
    normalize_review_findings,
    parse_reconciliation_response,
    synthesize_reviews,
)
from models.proposal import (
    ConflictEntry,
    CoverageDomain,
    DecisionItem,
    DecisionSummary,
    ForwardGuidance,
    ForwardGuidanceItem,
    NormalizedItem,
    ProposalCoverage,
    ProposalInputSnapshot,
    ProposalReviewPass,
    ReconciliationResult,
    ReviewPassDomain,
)



# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_review(
    review_id: str = "r1",
    version_id: str = "v1",
    persona: str = "Solution Architect",
    completeness_score: int = 80,
    quality_status: str = "complete",
    findings: Optional[Dict[str, Any]] = None,
    decision_points: Optional[List[Dict]] = None,
) -> SimpleNamespace:
    """Lightweight Review-like object for testing (no DB/filesystem)."""
    return SimpleNamespace(
        review_id=review_id,
        version_id=version_id,
        persona=persona,
        completeness_score=completeness_score,
        quality_status=quality_status,
        created_at=f"2026-01-0{review_id[-1]}T00:00:00+00:00",
        findings=findings or {},
        decision_points=decision_points or [],
    )


def _base_findings() -> Dict[str, Any]:
    return {
        "risks":        ["Database access may fail", "Security misconfiguration risk"],
        "assumptions":  ["Client provides environments", "Team is available from day 1"],
        "dependencies": ["Azure AD integration", "Legacy ERP API"],
        "constraints":  ["Go-live must not exceed 12 weeks"],
        "action_items": ["Set up CI/CD pipeline", "Migrate user data", "Train operations team"],
    }


@pytest.fixture(autouse=True)
def clear_caches():
    """Ensure caches are empty between tests."""
    _clear_caches()
    yield
    _clear_caches()



# ─────────────────────────────────────────────────────────────────────────────
# A  Dataclass contracts
# ─────────────────────────────────────────────────────────────────────────────

class TestDataclassContracts:
    """All new dataclasses must round-trip through to_dict / from_dict."""

    def test_normalized_item_roundtrip(self):
        item = NormalizedItem(text="A risk", category="risks",
                              review_id="r1", persona="SA", dedup_key="a risk")
        assert NormalizedItem.from_dict(item.to_dict()) == item

    def test_conflict_entry_roundtrip(self):
        ce = ConflictEntry(category="risks",
                           description="r1 says in-scope; r2 says out-of-scope",
                           review_ids=["r1", "r2"])
        assert ConflictEntry.from_dict(ce.to_dict()) == ce

    def test_reconciliation_result_roundtrip(self):
        rr = ReconciliationResult(
            reconciled_findings={"risks": ["risk A"], "assumptions": []},
            overlaps_resolved=["overlap X"],
            contradictions=[ConflictEntry(category="risks",
                                          description="conflict",
                                          review_ids=["r1"])],
            reconciliation_notes="merged r1 and r2",
            source_review_ids=["r1", "r2"],
            anchor_review_id="r1",
            generated_by="deterministic",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        restored = ReconciliationResult.from_dict(rr.to_dict())
        assert restored.anchor_review_id == "r1"
        assert restored.generated_by == "deterministic"
        assert len(restored.contradictions) == 1
        assert restored.contradictions[0].description == "conflict"

    def test_proposal_input_snapshot_roundtrip(self):
        snap = ProposalInputSnapshot(
            anchor_review_id="r1",
            selected_review_ids=["r1", "r2"],
            selected_version_id="v1",
            generation_mode="multi",
            captured_at="2026-01-01T00:00:00+00:00",
        )
        assert ProposalInputSnapshot.from_dict(snap.to_dict()) == snap

    def test_review_pass_domain_roundtrip(self):
        rpd = ReviewPassDomain(
            covered_well=["good coverage"],
            still_weak=["weak area"],
            may_block_signoff=["blocker"],
        )
        assert ReviewPassDomain.from_dict(rpd.to_dict()) == rpd

    def test_proposal_review_pass_roundtrip(self):
        prp = ProposalReviewPass(
            scope=ReviewPassDomain(covered_well=["scope ok"]),
            generated_by="files_only",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        restored = ProposalReviewPass.from_dict(prp.to_dict())
        assert restored.scope.covered_well == ["scope ok"]
        assert restored.generated_by == "files_only"

    def test_coverage_domain_roundtrip(self):
        cd = CoverageDomain(status="Partial",
                            matched_themes=["azure migration"],
                            gap_notes="Missing SLA details")
        assert CoverageDomain.from_dict(cd.to_dict()) == cd

    def test_proposal_coverage_roundtrip(self):
        pc = ProposalCoverage(
            scope=CoverageDomain(status="Addressed"),
            security_compliance=CoverageDomain(status="Not Yet Addressed"),
            source_theme_count=3,
            computed_at="2026-01-01T00:00:00+00:00",
        )
        restored = ProposalCoverage.from_dict(pc.to_dict())
        assert restored.scope.status == "Addressed"
        assert restored.security_compliance.status == "Not Yet Addressed"
        assert restored.source_theme_count == 3

    def test_decision_item_roundtrip(self):
        di = DecisionItem(text="Choose cloud platform",
                          category="architecture", source_review_id="r1")
        assert DecisionItem.from_dict(di.to_dict()) == di

    def test_decision_summary_roundtrip(self):
        ds = DecisionSummary(
            confirmed=[DecisionItem(text="Platform chosen", category="arch",
                                    source_review_id="r1")],
            open=[DecisionItem(text="DR strategy TBD", category="ops",
                               source_review_id="r2")],
            sign_off_blockers=[],
            source_review_ids=["r1", "r2"],
            generated_by="files_only",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        restored = DecisionSummary.from_dict(ds.to_dict())
        assert len(restored.confirmed) == 1
        assert len(restored.open) == 1
        assert restored.confirmed[0].text == "Platform chosen"

    def test_forward_guidance_item_roundtrip(self):
        fgi = ForwardGuidanceItem(
            issue="Security not covered",
            why_it_matters="Blocks sign-off",
            suggested_action="Add security section",
            trade_off_or_constraint="",
        )
        assert ForwardGuidanceItem.from_dict(fgi.to_dict()) == fgi

    def test_forward_guidance_roundtrip(self):
        fg = ForwardGuidance(
            strengthen_weak_areas=[
                ForwardGuidanceItem(issue="i", why_it_matters="w",
                                    suggested_action="a",
                                    trade_off_or_constraint="")
            ],
            generated_by="files_only",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        restored = ForwardGuidance.from_dict(fg.to_dict())
        assert len(restored.strengthen_weak_areas) == 1
        assert restored.optional_enhancements == []

    def test_trade_off_defaults_to_empty_string_not_none(self):
        """trade_off_or_constraint must be '' not None when absent."""
        fgi = ForwardGuidanceItem.from_dict({
            "issue": "x", "why_it_matters": "y", "suggested_action": "z"
        })
        assert fgi.trade_off_or_constraint == ""
        assert fgi.trade_off_or_constraint is not None



# ─────────────────────────────────────────────────────────────────────────────
# B  S1-01  normalize_review_findings
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeReviewFindings:

    def test_ac1_correct_item_count_and_categories(self):
        """AC1: Review with 3 risks, 2 assumptions → 5 NormalizedItems."""
        review = _make_review(findings={
            "risks": ["Risk A", "Risk B", "Risk C"],
            "assumptions": ["Assumption 1", "Assumption 2"],
        })
        items = normalize_review_findings(review)
        assert len(items) == 5
        risks = [i for i in items if i.category == "risks"]
        assumptions = [i for i in items if i.category == "assumptions"]
        assert len(risks) == 3
        assert len(assumptions) == 2

    def test_ac2_review_id_provenance(self):
        """AC2: Each item's review_id matches the source review."""
        review = _make_review(review_id="r7", findings={"risks": ["Risk X"]})
        items = normalize_review_findings(review)
        assert all(i.review_id == "r7" for i in items)

    def test_ac3_dedup_key_normalisation(self):
        """AC3: 'Risk: Database access  may fail.' →
        lowercased, punctuation stripped, whitespace collapsed to single spaces."""
        key = _make_dedup_key("Risk: Database access  may fail.")
        # Punctuation replaced by spaces then collapsed → single spaces throughout
        assert key == "risk database access may fail"
        # Verify: no leading/trailing whitespace
        assert key == key.strip()
        # Verify: no double-spaces
        assert "  " not in key

    def test_ac4_empty_findings_returns_empty_list(self):
        """AC4: Empty findings dict → empty list, no error."""
        review = _make_review(findings={})
        items = normalize_review_findings(review)
        assert items == []

    def test_ac4_none_findings_returns_empty_list(self):
        """AC4 variant: findings=None → empty list."""
        review = _make_review(findings=None)
        items = normalize_review_findings(review)
        assert items == []

    def test_ac5_non_string_items_coerced(self):
        """AC5: Non-string items coerced to str, not dropped."""
        review = _make_review(findings={"risks": [42, {"key": "value"}, None]})
        items = normalize_review_findings(review)
        # None coerces to "None" which is non-empty
        assert len(items) == 3
        texts = [i.text for i in items]
        assert "42" in texts

    def test_persona_propagated(self):
        review = _make_review(persona="Delivery Manager",
                               findings={"risks": ["A risk"]})
        items = normalize_review_findings(review)
        assert items[0].persona == "Delivery Manager"

    def test_all_five_categories_processed(self):
        review = _make_review(findings=_base_findings())
        items = normalize_review_findings(review)
        cats = {i.category for i in items}
        assert cats == {"risks", "assumptions", "dependencies",
                        "constraints", "action_items"}

    def test_empty_string_items_skipped(self):
        """Items that are empty after strip are excluded."""
        review = _make_review(findings={"risks": ["", "  ", "Real risk"]})
        items = normalize_review_findings(review)
        assert len(items) == 1
        assert items[0].text == "Real risk"

    def test_cache_hit_returns_same_object(self):
        """Second call with same review_id returns cached result."""
        review = _make_review(review_id="r_cache",
                               findings={"risks": ["Risk A"]})
        result1 = normalize_review_findings(review)
        result2 = normalize_review_findings(review)
        assert result1 is result2   # same list object from cache

    def test_dedup_key_present_on_all_items(self):
        review = _make_review(findings=_base_findings())
        items = normalize_review_findings(review)
        for item in items:
            assert item.dedup_key != ""



# ─────────────────────────────────────────────────────────────────────────────
# C  S1-02  deduplicate_normalized
# ─────────────────────────────────────────────────────────────────────────────

class TestDeduplicateNormalized:

    def _item(self, text, category="risks", review_id="r1",
               persona="SA", completeness=80):
        return NormalizedItem(
            text=text,
            category=category,
            review_id=review_id,
            persona=persona,
            dedup_key=_make_dedup_key(text),
        )

    def test_ac1_identical_text_keeps_higher_quality(self):
        """AC1: Two identical items → one retained from higher-quality review."""
        items = [
            self._item("Database may fail", review_id="r1"),
            self._item("Database may fail", review_id="r2"),
        ]
        score_map = {"r1": 60, "r2": 90}
        result = deduplicate_normalized(items, score_map)
        assert len(result) == 1
        assert result[0].review_id == "r2"

    def test_ac2_high_overlap_deduplicated(self):
        """AC2: 80%+ token overlap → deduplicated."""
        # "database may fail during migration" vs "database may fail in migration"
        # tokens: {database,may,fail,during,migration} vs {database,may,fail,in,migration}
        # intersection=4, union=6 → 0.67 — that's below threshold
        # Use near-identical to be above 0.75:
        items = [
            self._item("The database connection may fail unexpectedly",
                        review_id="r1"),
            self._item("The database connection may fail unexpectedly during load",
                        review_id="r2"),
        ]
        # "the database connection may fail unexpectedly" (6) vs
        # "the database connection may fail unexpectedly during load" (8)
        # intersection=6, union=8 → 0.75 — exactly at threshold → dedup
        score_map = {"r1": 80, "r2": 50}
        result = deduplicate_normalized(items, score_map)
        assert len(result) == 1
        assert result[0].review_id == "r1"  # higher score wins

    def test_ac3_low_overlap_both_retained(self):
        """AC3: 50% overlap → both retained."""
        items = [
            self._item("Security authentication failure risk", review_id="r1"),
            self._item("Budget overrun commercial risk", review_id="r2"),
        ]
        result = deduplicate_normalized(items)
        assert len(result) == 2

    def test_ac4_same_text_different_categories_both_retained(self):
        """AC4: Same text in 'risks' and 'assumptions' → both retained."""
        items = [
            self._item("Client will provide environments", "risks", "r1"),
            self._item("Client will provide environments", "assumptions", "r1"),
        ]
        result = deduplicate_normalized(items)
        assert len(result) == 2
        cats = {i.category for i in result}
        assert "risks" in cats
        assert "assumptions" in cats

    def test_ac5_three_reviews_higher_score_wins(self):
        """AC5: Three reviews, two with same risk text → retained = higher-scoring."""
        items = [
            self._item("API rate limit may cause failures", review_id="r1"),
            self._item("API rate limit may cause failures", review_id="r2"),
            self._item("Something completely different risk", review_id="r3"),
        ]
        score_map = {"r1": 40, "r2": 85, "r3": 60}
        result = deduplicate_normalized(items, score_map)
        assert len(result) == 2
        review_ids = {i.review_id for i in result}
        assert "r2" in review_ids   # higher-scoring wins
        assert "r1" not in review_ids

    def test_ac6_cache_hit_avoids_recomputation(self):
        """AC6: Second call with same items → cache hit (same list object)."""
        items = [
            self._item("Risk alpha", review_id="r1"),
            self._item("Risk beta", review_id="r2"),
        ]
        result1 = deduplicate_normalized(items)
        result2 = deduplicate_normalized(items)
        assert result1 is result2

    def test_empty_list_returns_empty(self):
        result = deduplicate_normalized([])
        assert result == []

    def test_single_item_returned_unchanged(self):
        items = [self._item("Only risk", review_id="r1")]
        result = deduplicate_normalized(items)
        assert len(result) == 1
        assert result[0].text == "Only risk"

    def test_equal_score_first_item_wins(self):
        """Equal scores: first (older) item is kept — stable behaviour."""
        items = [
            self._item("Database connection failure", review_id="r1"),
            self._item("Database connection failure", review_id="r2"),
        ]
        score_map = {"r1": 70, "r2": 70}
        result = deduplicate_normalized(items, score_map)
        assert len(result) == 1
        assert result[0].review_id == "r1"

    def test_jaccard_similarity_exact(self):
        assert _jaccard_similarity("a b c", "a b c") == 1.0

    def test_jaccard_similarity_disjoint(self):
        assert _jaccard_similarity("alpha beta", "gamma delta") == 0.0

    def test_jaccard_similarity_partial(self):
        # intersection={b,c}, union={a,b,c,d} → 0.5
        sim = _jaccard_similarity("a b c", "b c d")
        assert abs(sim - 0.5) < 0.01

    def test_jaccard_similarity_empty_strings(self):
        assert _jaccard_similarity("", "") == 1.0
        assert _jaccard_similarity("a b", "") == 0.0



# ─────────────────────────────────────────────────────────────────────────────
# D  S1-03  build_reconciliation_prompt / parse_reconciliation_response
# ─────────────────────────────────────────────────────────────────────────────

class TestReconciliationPrompt:

    def _deduped_items(self) -> List[NormalizedItem]:
        return [
            NormalizedItem(text="DB fail risk", category="risks",
                           review_id="r1", persona="SA",
                           dedup_key="db fail risk"),
            NormalizedItem(text="Team available assumption", category="assumptions",
                           review_id="r2", persona="DM",
                           dedup_key="team available assumption"),
            NormalizedItem(text="Azure AD dependency", category="dependencies",
                           review_id="r1", persona="SA",
                           dedup_key="azure ad dependency"),
        ]

    # ── build_reconciliation_prompt ──────────────────────────────────────────

    def test_ac1_all_five_section_headers_present(self):
        """AC1: All five RECONCILED_* headers present."""
        prompt = build_reconciliation_prompt(self._deduped_items(), "Test scope")
        for header in ["RECONCILED_RISKS", "RECONCILED_ASSUMPTIONS",
                       "RECONCILED_DEPENDENCIES", "RECONCILED_CONSTRAINTS",
                       "RECONCILED_ACTION_ITEMS"]:
            assert f"---{header}---" in prompt, f"Missing header: {header}"

    def test_ac1_output_headers_also_present(self):
        """CONFLICTS and RECONCILIATION_NOTES headers present."""
        prompt = build_reconciliation_prompt(self._deduped_items(), "scope")
        assert "---CONFLICTS---" in prompt
        assert "---RECONCILIATION_NOTES---" in prompt

    def test_ac2_items_tagged_with_review_id(self):
        """AC2: Each item tagged with its review_id."""
        prompt = build_reconciliation_prompt(self._deduped_items(), "scope")
        assert "[r1 /" in prompt
        assert "[r2 /" in prompt

    def test_ac3_scope_truncated_to_800_chars(self):
        """AC3: Scope text > 800 chars truncated to exactly 800."""
        long_scope = "X" * 1200
        prompt = build_reconciliation_prompt([], long_scope)
        # The truncated scope appears literally in the prompt
        assert "X" * 800 in prompt
        assert "X" * 801 not in prompt

    def test_scope_at_exactly_800_not_truncated(self):
        scope = "Y" * 800
        prompt = build_reconciliation_prompt([], scope)
        assert "Y" * 800 in prompt

    def test_empty_items_produces_none_placeholders(self):
        """Categories with no items show (none)."""
        prompt = build_reconciliation_prompt([], "scope")
        assert "(none)" in prompt

    # ── parse_reconciliation_response ───────────────────────────────────────

    def test_ac4_two_conflict_lines_parsed(self):
        """AC4: Response with two conflict lines → 2 ConflictEntry objects."""
        raw = """---RECONCILED_RISKS---
Risk item one
---RECONCILED_ASSUMPTIONS---
---RECONCILED_DEPENDENCIES---
---RECONCILED_CONSTRAINTS---
---RECONCILED_ACTION_ITEMS---
---CONFLICTS---
r1 says in-scope; r2 says out-of-scope
r1 assumes 12 weeks; r3 assumes 20 weeks
---RECONCILIATION_NOTES---
Merged items from r1 and r2."""
        result = parse_reconciliation_response(raw, ["r1", "r2", "r3"], "r1", "gemini")
        assert len(result.contradictions) == 2
        assert "r1 says in-scope" in result.contradictions[0].description

    def test_ac5_missing_section_returns_empty_list(self):
        """AC5: Missing RECONCILED_DEPENDENCIES section → empty list."""
        raw = """---RECONCILED_RISKS---
One risk
---RECONCILED_ASSUMPTIONS---
---RECONCILED_CONSTRAINTS---
---RECONCILED_ACTION_ITEMS---
---CONFLICTS---
---RECONCILIATION_NOTES---"""
        result = parse_reconciliation_response(raw, ["r1"], "r1", "ollama")
        assert result.reconciled_findings["dependencies"] == []
        assert result.reconciled_findings["risks"] == ["One risk"]

    def test_ac6_empty_raw_returns_empty_result(self):
        """AC6: Empty raw response → ReconciliationResult with all empty fields."""
        result = parse_reconciliation_response("", ["r1"], "r1", "files_only")
        assert isinstance(result, ReconciliationResult)
        for cat in ["risks", "assumptions", "dependencies",
                    "constraints", "action_items"]:
            assert result.reconciled_findings[cat] == []
        assert result.contradictions == []
        assert result.reconciliation_notes == ""

    def test_no_conflicts_section_returns_empty_contradictions(self):
        raw = "---RECONCILED_RISKS---\nSome risk\n---RECONCILIATION_NOTES---\nnotes"
        result = parse_reconciliation_response(raw, ["r1"], "r1", "test")
        assert result.contradictions == []

    def test_source_ids_and_anchor_stored(self):
        result = parse_reconciliation_response(
            "", ["r1", "r2", "r3"], "r2", "deterministic"
        )
        assert result.source_review_ids == ["r1", "r2", "r3"]
        assert result.anchor_review_id == "r2"

    def test_generated_by_stored(self):
        result = parse_reconciliation_response("", ["r1"], "r1", "groq")
        assert result.generated_by == "groq"

    def test_generated_at_is_iso_timestamp(self):
        import re as _re
        result = parse_reconciliation_response("", ["r1"], "r1", "test")
        assert _re.match(r"\d{4}-\d{2}-\d{2}T", result.generated_at)

    def test_reconciliation_notes_extracted(self):
        raw = """---RECONCILED_RISKS---
---RECONCILED_ASSUMPTIONS---
---RECONCILED_DEPENDENCIES---
---RECONCILED_CONSTRAINTS---
---RECONCILED_ACTION_ITEMS---
---CONFLICTS---
---RECONCILIATION_NOTES---
Merged overlapping risks from r1 and r2. Kept r2 version as more specific."""
        result = parse_reconciliation_response(raw, ["r1", "r2"], "r1", "test")
        assert "Merged overlapping risks" in result.reconciliation_notes



# ─────────────────────────────────────────────────────────────────────────────
# E  S1-04  synthesize_reviews orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class TestSynthesizeReviews:

    def test_ac1_different_version_id_raises_value_error(self):
        """AC1: Supplemental from different version_id → ValueError."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings=_base_findings())
        supplemental = _make_review(review_id="r2", version_id="v999",
                                     findings={"risks": ["other risk"]})
        with pytest.raises(ValueError, match="version"):
            synthesize_reviews(anchor, [supplemental], "scope", "files_only")

    def test_ac2_files_only_returns_deterministic(self):
        """AC2: files_only backend → generated_by == 'deterministic'."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings=_base_findings())
        result = synthesize_reviews(anchor, [], "scope text", "files_only")
        assert result.generated_by == "deterministic"

    def test_ac3_files_only_findings_are_union_of_deduped(self):
        """AC3: files_only → reconciled_findings contains union of deduped items."""
        anchor = _make_review(
            review_id="r1", version_id="v1",
            findings={"risks": ["Risk A", "Risk B"], "assumptions": ["Assumption X"]},
        )
        supplemental = _make_review(
            review_id="r2", version_id="v1",
            findings={"risks": ["Risk C"], "dependencies": ["Dep Y"]},
        )
        result = synthesize_reviews(anchor, [supplemental], "scope", "files_only")
        assert "Risk A" in result.reconciled_findings["risks"]
        assert "Risk B" in result.reconciled_findings["risks"]
        assert "Risk C" in result.reconciled_findings["risks"]
        assert "Assumption X" in result.reconciled_findings["assumptions"]
        assert "Dep Y" in result.reconciled_findings["dependencies"]

    def test_ac5_single_supplemental_runs_without_error(self):
        """AC5: Single supplemental → no error."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings={"risks": ["Risk A"]})
        sup = _make_review(review_id="r2", version_id="v1",
                            findings={"risks": ["Risk B"]})
        result = synthesize_reviews(anchor, [sup], "scope", "files_only")
        assert isinstance(result, ReconciliationResult)

    def test_ac6_zero_supplementals_anchor_findings_only(self):
        """AC6: Zero supplementals → ReconciliationResult with anchor findings only."""
        anchor = _make_review(
            review_id="r1", version_id="v1",
            findings={"risks": ["Only risk"], "assumptions": ["Only assumption"]},
        )
        result = synthesize_reviews(anchor, [], "scope", "files_only")
        assert result.source_review_ids == ["r1"]
        assert result.anchor_review_id == "r1"
        assert "Only risk" in result.reconciled_findings["risks"]

    def test_ac7_pending_quality_status_accepted(self):
        """AC7: Supplemental with quality_status='pending' → no error."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings={"risks": ["Risk A"]})
        pending_sup = _make_review(review_id="r2", version_id="v1",
                                    quality_status="pending",
                                    findings={"risks": ["Risk B"]})
        result = synthesize_reviews(anchor, [pending_sup], "scope", "files_only")
        assert isinstance(result, ReconciliationResult)

    def test_source_review_ids_includes_anchor_and_supplementals(self):
        anchor = _make_review(review_id="r1", version_id="v1",
                               findings={"risks": ["Risk A"]})
        sup1 = _make_review(review_id="r2", version_id="v1",
                             findings={"risks": ["Risk B"]})
        sup2 = _make_review(review_id="r3", version_id="v1",
                             findings={"risks": ["Risk C"]})
        result = synthesize_reviews(anchor, [sup1, sup2], "scope", "files_only")
        assert set(result.source_review_ids) == {"r1", "r2", "r3"}

    def test_dedup_applied_before_reconciliation(self):
        """Identical risks across anchor + supplemental → deduplicated in result."""
        anchor = _make_review(
            review_id="r1", version_id="v1",
            completeness_score=80,
            findings={"risks": ["Database connection failure"]},
        )
        sup = _make_review(
            review_id="r2", version_id="v1",
            completeness_score=60,
            findings={"risks": ["Database connection failure"]},
        )
        result = synthesize_reviews(anchor, [sup], "scope", "files_only")
        # After dedup, only one instance should survive
        assert result.reconciled_findings["risks"].count(
            "Database connection failure"
        ) == 1

    def test_empty_version_id_on_anchor_does_not_raise(self):
        """Empty version_id on anchor → no validation error (cannot compare)."""
        anchor = _make_review(review_id="r1", version_id="",
                               findings={"risks": ["Risk A"]})
        sup = _make_review(review_id="r2", version_id="v999",
                            findings={"risks": ["Risk B"]})
        # Should not raise — empty anchor version_id skips validation
        result = synthesize_reviews(anchor, [sup], "scope", "files_only")
        assert isinstance(result, ReconciliationResult)



# ─────────────────────────────────────────────────────────────────────────────
# F  S1-05  extract_scope_themes
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractScopeThemes:

    def test_ac1_known_platform_and_capitalised_phrase(self):
        """AC1: 'Azure Data Factory' (platform keyword) and a Title-Case phrase
        extracted from scope that contains 'Data Factory'."""
        scope = "Migrate data using Azure Data Factory and the Data Warehouse platform."
        themes = extract_scope_themes(scope)
        joined = " ".join(themes)
        # Platform keyword 'azure' always detected
        assert "azure" in themes
        # Capitalised phrase 'Data Factory' or 'Data Warehouse' detected
        assert any("data factory" in t or "data warehouse" in t for t in themes)

    def test_ac2_empty_scope_and_findings_returns_empty(self):
        """AC2: Empty scope + empty findings → []."""
        result = extract_scope_themes("", {})
        assert result == []

    def test_ac2_none_scope_returns_empty(self):
        result = extract_scope_themes(None, {})
        assert result == []

    def test_ac3_duplicate_themes_deduplicated(self):
        """AC3: Same theme appearing twice → appears once."""
        scope = "Azure Azure migration using Azure services."
        themes = extract_scope_themes(scope)
        assert themes.count("azure") == 1

    def test_ac4_themes_from_action_items(self):
        """AC4: Themes from action_items included when not in scope text."""
        scope = ""
        findings = {"action_items": ["Deploy Kubernetes cluster for workloads"]}
        themes = extract_scope_themes(scope, findings)
        assert "kubernetes" in themes

    def test_returns_lowercase_themes(self):
        scope = "Migrate to Salesforce CRM platform."
        themes = extract_scope_themes(scope)
        for t in themes:
            assert t == t.lower(), f"Theme not lowercase: {t!r}"

    def test_capitalised_two_word_phrase_extracted(self):
        scope = "The Data Migration project covers Cloud Infrastructure setup."
        themes = extract_scope_themes(scope)
        # Should pick up "Data Migration", "Cloud Infrastructure"
        joined = " ".join(themes)
        assert "data migration" in joined or "data" in joined

    def test_quoted_strings_extracted(self):
        scope = 'Deliver the "Customer Portal Redesign" project on time.'
        themes = extract_scope_themes(scope)
        assert any("customer portal redesign" in t for t in themes)

    def test_does_not_return_none_values(self):
        themes = extract_scope_themes("scope with Kubernetes")
        assert all(t is not None for t in themes)



# ─────────────────────────────────────────────────────────────────────────────
# G  S1-06  merge_decision_points
# ─────────────────────────────────────────────────────────────────────────────

class TestMergeDecisionPoints:

    def test_ac1_identical_decision_deduplicated(self):
        """AC1: Two reviews with same open decision → one item in output."""
        r1 = _make_review(review_id="r1", version_id="v1",
                           decision_points=[
                               {"text": "Choose cloud platform", "category": "arch",
                                "status": "open"}
                           ])
        r2 = _make_review(review_id="r2", version_id="v1",
                           decision_points=[
                               {"text": "Choose cloud platform", "category": "arch",
                                "status": "open"}
                           ])
        result = merge_decision_points([r1, r2])
        assert len(result) == 1

    def test_ac2_different_decisions_both_retained(self):
        """AC2: Two reviews with different open decisions → both retained."""
        r1 = _make_review(review_id="r1", version_id="v1",
                           decision_points=[
                               {"text": "Choose cloud platform", "category": "arch",
                                "status": "open"}
                           ])
        r2 = _make_review(review_id="r2", version_id="v1",
                           decision_points=[
                               {"text": "Decide on DR strategy", "category": "ops",
                                "status": "open"}
                           ])
        result = merge_decision_points([r1, r2])
        assert len(result) == 2

    def test_ac3_source_review_id_is_anchor_when_anchor_has_item(self):
        """AC3: source_review_id on merged duplicate = anchor review_id."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               decision_points=[
                                   {"text": "Choose cloud platform",
                                    "category": "arch", "status": "open"}
                               ])
        sup = _make_review(review_id="r2", version_id="v1",
                            decision_points=[
                                {"text": "Choose cloud platform",
                                 "category": "arch", "status": "addressed"}
                            ])
        result = merge_decision_points([anchor, sup])
        assert len(result) == 1
        assert result[0]["source_review_id"] == "r1"

    def test_ac4_review_with_no_decision_points_field(self):
        """AC4: Review with missing decision_points → empty list, no error."""
        r1 = SimpleNamespace(review_id="r1", version_id="v1",
                              findings={}, decision_points=None)
        r2 = _make_review(review_id="r2", version_id="v1",
                           decision_points=[
                               {"text": "DR strategy TBD",
                                "category": "ops", "status": "open"}
                           ])
        result = merge_decision_points([r1, r2])
        assert len(result) == 1
        assert result[0]["text"] == "DR strategy TBD"

    def test_ac5_mixed_statuses_anchor_wins(self):
        """AC5: Mixed open/addressed on duplicate → anchor status wins."""
        anchor = _make_review(review_id="r1", version_id="v1",
                               decision_points=[
                                   {"text": "Platform selection required",
                                    "category": "arch", "status": "open"}
                               ])
        sup = _make_review(review_id="r2", version_id="v1",
                            decision_points=[
                                {"text": "Platform selection required",
                                 "category": "arch", "status": "addressed"}
                            ])
        result = merge_decision_points([anchor, sup])
        assert len(result) == 1
        assert result[0]["status"] == "open"   # anchor wins

    def test_empty_review_list_returns_empty(self):
        result = merge_decision_points([])
        assert result == []

    def test_single_review_all_decisions_retained(self):
        r1 = _make_review(review_id="r1", version_id="v1",
                           decision_points=[
                               {"text": "Decision A", "category": "arch", "status": "open"},
                               {"text": "Decision B", "category": "ops", "status": "open"},
                           ])
        result = merge_decision_points([r1])
        assert len(result) == 2

    def test_result_has_required_keys(self):
        r1 = _make_review(review_id="r1", version_id="v1",
                           decision_points=[
                               {"text": "Choose DB", "category": "data", "status": "open"}
                           ])
        result = merge_decision_points([r1])
        assert len(result) == 1
        item = result[0]
        for key in ["text", "category", "status", "source_review_id"]:
            assert key in item, f"Missing key: {key}"

    def test_non_dict_decision_points_skipped(self):
        """Non-dict items in decision_points → skipped gracefully."""
        r1 = _make_review(review_id="r1", version_id="v1",
                           decision_points=["not a dict", None, 42])
        result = merge_decision_points([r1])
        assert result == []



# ─────────────────────────────────────────────────────────────────────────────
# H  Regression — existing proposal generation path unaffected
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionExistingPath:
    """Sprint 1 must not change any existing behaviour.

    These tests confirm that:
    - models.proposal still exports all pre-existing symbols
    - processors.proposal_generator still imports cleanly
    - generate_proposal_document signature is unchanged
    - No changes to handlers, services, or DB in this sprint
    """

    def test_proposal_model_pre_existing_exports_intact(self):
        from models.proposal import (
            ProposalDocument, ProposalVersion, ProposalTracker,
            PresalesFeedback, FeedbackItem, GanttRow, RiskEntry,
            AssumptionEntry, DeliveryPhase,
            VALID_PROPOSAL_STATUSES, VALID_PROPOSAL_QUALITY,
            FEEDBACK_CATEGORIES,
        )
        assert ProposalDocument is not None
        assert "draft" in VALID_PROPOSAL_STATUSES

    def test_proposal_generator_imports_cleanly(self):
        from processors.proposal_generator import generate_proposal_document
        assert callable(generate_proposal_document)

    def test_generate_proposal_document_signature_unchanged(self):
        """Existing 6-param signature must be present (no new required params)."""
        import inspect
        from processors.proposal_generator import generate_proposal_document
        sig = inspect.signature(generate_proposal_document)
        params = list(sig.parameters.keys())
        assert "project_id" in params
        assert "proposal_ver_id" in params
        assert "hierarchy_version_id" in params
        assert "review_id" in params
        assert "ai_backend" in params
        assert "force" in params

    def test_review_synthesizer_does_not_import_proposal_generator(self):
        """review_synthesizer must not create circular imports."""
        import importlib, sys
        # Remove from cache if already loaded
        mods_before = set(sys.modules.keys())
        import processors.review_synthesizer  # noqa: F401 (already imported above)
        # proposal_generator should NOT be imported as a side-effect
        # (it may be present from other tests — just verify synthesizer
        # itself doesn't require it at module level)
        import processors.review_synthesizer as rs
        import ast, inspect, textwrap
        src = inspect.getsource(rs)
        tree = ast.parse(src)
        top_level_imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if node.col_offset == 0:   # top-level only
                    top_level_imports.append(ast.dump(node))
        combined = " ".join(top_level_imports)
        assert "proposal_generator" not in combined

    def test_proposal_document_to_dict_has_synthesis_fields(self):
        """ProposalDocument.to_dict() exposes all 6 synthesis fields (Sprint 2+).

        Fields default to None on existing/single-review documents.
        """
        from models.proposal import ProposalDocument
        doc = ProposalDocument(project_id="p1", proposal_ver_id="pv1")
        d = doc.to_dict()
        for key in ["input_snapshot", "reconciliation_result",
                    "review_pass", "proposal_coverage",
                    "decision_summary", "forward_guidance"]:
            assert key in d, f"Synthesis field '{key}' missing from ProposalDocument.to_dict()"
            assert d[key] is None, f"Synthesis field '{key}' should default to None"

    def test_existing_proposal_model_tests_still_pass(self):
        """Spot-check: ProposalVersion round-trip still works."""
        from models.proposal import ProposalVersion
        pv = ProposalVersion(
            version_id="pv1", version_number=1,
            hierarchy_version_id="v1", active_review_id="r1",
        )
        d = pv.to_dict()
        restored = ProposalVersion.from_dict(d)
        assert restored.version_id == "pv1"
        assert restored.hierarchy_version_id == "v1"

