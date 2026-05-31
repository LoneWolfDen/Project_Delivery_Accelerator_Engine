"""Sprint 4 Tests — PDAE-MS-01: Forward Guidance & Recommendation Engine.

Covers all acceptance criteria from stories S4-01 and S4-02, plus
full regression for all prior sprints.

Sections
────────
A  parse_forward_guidance_response — unit tests (prompt parsing)
B  build_forward_guidance_prompt — prompt construction tests
C  _run_forward_guidance (files_only) — S4-01 / S4-02 deterministic path
D  Generator integration — forward_guidance wired end-to-end
E  DB persistence — forward_guidance round-trip
F  Sprint 1 + 2 + 3 regression — no prior behaviour broken
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

from processors.review_synthesizer import (
    build_forward_guidance_prompt,
    parse_forward_guidance_response,
    _clear_caches,
)
from models.proposal import (
    ForwardGuidance, ForwardGuidanceItem,
    ProposalCoverage, CoverageDomain,
    DecisionSummary, DecisionItem,
    ProposalReviewPass, ReviewPassDomain,
    ConflictEntry, ReconciliationResult,
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


def _make_review_pass(
    domain_weak: Dict[str, List[str]] = None,
    domain_blockers: Dict[str, List[str]] = None,
) -> ProposalReviewPass:
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


def _make_decision_summary(
    open_items: List[str] = None,
    confirmed: List[str] = None,
    blockers: List[str] = None,
    review_ids: List[str] = None,
) -> DecisionSummary:
    def _items(texts):
        return [DecisionItem(text=t, category="general", source_review_id="r1")
                for t in (texts or [])]
    return DecisionSummary(
        confirmed=_items(confirmed),
        open=_items(open_items),
        sign_off_blockers=_items(blockers),
        source_review_ids=review_ids or ["r1"],
        generated_by="files_only",
        generated_at="2026-01-01T00:00:00+00:00",
    )


def _make_coverage(domain_statuses: Dict[str, str] = None) -> ProposalCoverage:
    defaults = {d: "Addressed" for d in
                ["scope", "architecture", "delivery",
                 "security_compliance", "operations", "commercials"]}
    defaults.update(domain_statuses or {})
    def _dom(d): return CoverageDomain(status=defaults[d], matched_themes=[], gap_notes="")
    return ProposalCoverage(
        scope=_dom("scope"), architecture=_dom("architecture"),
        delivery=_dom("delivery"), security_compliance=_dom("security_compliance"),
        operations=_dom("operations"), commercials=_dom("commercials"),
        source_theme_count=0, computed_at="2026-01-01T00:00:00+00:00",
    )


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


def _make_version(version_id="v1", label="v1",
                  scope="Migrate legacy ERP to Azure.",
                  active_review_id="r1"):
    return SimpleNamespace(
        version_id=version_id, label=label, scope=scope,
        active_review_id=active_review_id,
        included_artifacts=[], stats={},
    )



# ═════════════════════════════════════════════════════════════════════════════
# A  parse_forward_guidance_response — prompt parsing
# ═════════════════════════════════════════════════════════════════════════════

class TestParseForwardGuidanceResponse:
    """Unit tests for parse_forward_guidance_response()."""

    def _parse(self, raw: str, backend: str = "files_only") -> ForwardGuidance:
        return parse_forward_guidance_response(raw, backend)

    def _make_raw(self, sections: Dict[str, str]) -> str:
        headers = [
            "STRENGTHEN_WEAK_AREAS", "RESOLVE_KEY_DECISIONS",
            "IMPROVE_CREDIBILITY", "ACCELERATE_CLIENT_ALIGNMENT",
            "OPTIONAL_ENHANCEMENTS",
        ]
        parts = []
        for h in headers:
            key = h.lower()
            parts.append(f"---{h}---\n{sections.get(key, '')}")
        return "\n".join(parts)

    def test_empty_raw_returns_all_empty_lists(self):
        result = self._parse("")
        assert result.strengthen_weak_areas == []
        assert result.resolve_key_decisions == []
        assert result.improve_credibility == []
        assert result.accelerate_client_alignment == []
        assert result.optional_enhancements == []

    def test_empty_raw_no_exception(self):
        result = self._parse("")
        assert isinstance(result, ForwardGuidance)

    def test_missing_section_returns_empty_list_for_that_section(self):
        raw = "---STRENGTHEN_WEAK_AREAS---\nissue: X\nwhy_it_matters: Y\nsuggested_action: Z\ntrade_off_or_constraint:"
        result = self._parse(raw)
        assert result.resolve_key_decisions == []
        assert result.optional_enhancements == []

    def test_structured_item_parsed_correctly(self):
        raw = (
            "---STRENGTHEN_WEAK_AREAS---\n"
            "issue: Security coverage missing\n"
            "why_it_matters: Client requires compliance\n"
            "suggested_action: Add security section\n"
            "trade_off_or_constraint: May require extra review cycle\n"
        )
        result = self._parse(raw)
        assert len(result.strengthen_weak_areas) == 1
        item = result.strengthen_weak_areas[0]
        assert item.issue == "Security coverage missing"
        assert item.why_it_matters == "Client requires compliance"
        assert item.suggested_action == "Add security section"
        assert item.trade_off_or_constraint == "May require extra review cycle"

    def test_trade_off_empty_string_when_blank(self):
        raw = (
            "---RESOLVE_KEY_DECISIONS---\n"
            "issue: DR strategy unresolved\n"
            "why_it_matters: Blocks sign-off\n"
            "suggested_action: Schedule workshop\n"
            "trade_off_or_constraint:\n"
        )
        result = self._parse(raw)
        assert len(result.resolve_key_decisions) == 1
        assert result.resolve_key_decisions[0].trade_off_or_constraint == ""

    def test_multiple_items_in_one_section(self):
        raw = (
            "---RESOLVE_KEY_DECISIONS---\n"
            "issue: DR strategy unresolved\n"
            "why_it_matters: Blocks sign-off\n"
            "suggested_action: Schedule workshop\n"
            "trade_off_or_constraint:\n"
            "\n"
            "issue: Platform choice pending\n"
            "why_it_matters: Architecture cannot proceed\n"
            "suggested_action: Decision matrix session\n"
            "trade_off_or_constraint: Vendor evaluation needed\n"
        )
        result = self._parse(raw)
        assert len(result.resolve_key_decisions) == 2
        assert result.resolve_key_decisions[0].issue == "DR strategy unresolved"
        assert result.resolve_key_decisions[1].issue == "Platform choice pending"

    def test_all_five_sections_populated(self):
        item_block = (
            "issue: Test issue\n"
            "why_it_matters: Important\n"
            "suggested_action: Do something\n"
            "trade_off_or_constraint:\n"
        )
        raw = "\n".join([
            f"---{h}---\n{item_block}"
            for h in ["STRENGTHEN_WEAK_AREAS", "RESOLVE_KEY_DECISIONS",
                      "IMPROVE_CREDIBILITY", "ACCELERATE_CLIENT_ALIGNMENT",
                      "OPTIONAL_ENHANCEMENTS"]
        ])
        result = self._parse(raw)
        assert len(result.strengthen_weak_areas) == 1
        assert len(result.resolve_key_decisions) == 1
        assert len(result.improve_credibility) == 1
        assert len(result.accelerate_client_alignment) == 1
        assert len(result.optional_enhancements) == 1

    def test_generated_by_set_to_backend_name(self):
        result = self._parse("", backend="ollama")
        assert result.generated_by == "ollama"

    def test_generated_at_is_iso_timestamp(self):
        import re
        result = self._parse("")
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.generated_at)

    def test_plain_text_item_treated_as_issue(self):
        """Non-structured line (no key:) used as issue text."""
        raw = "---IMPROVE_CREDIBILITY---\nAdd case studies to strengthen proposal\n"
        result = self._parse(raw)
        assert len(result.improve_credibility) == 1
        assert "case studies" in result.improve_credibility[0].issue

    def test_to_dict_round_trip(self):
        raw = (
            "---STRENGTHEN_WEAK_AREAS---\n"
            "issue: Security missing\n"
            "why_it_matters: Required\n"
            "suggested_action: Add section\n"
            "trade_off_or_constraint:\n"
        )
        result = self._parse(raw, "files_only")
        d = result.to_dict()
        restored = ForwardGuidance.from_dict(d)
        assert len(restored.strengthen_weak_areas) == 1
        assert restored.strengthen_weak_areas[0].issue == "Security missing"



# ═════════════════════════════════════════════════════════════════════════════
# B  build_forward_guidance_prompt — prompt construction
# ═════════════════════════════════════════════════════════════════════════════

class TestBuildForwardGuidancePrompt:
    """Verify prompt structure and content injection."""

    def _prompt(self, rp=None, ds=None, conflicts=None, scope="Test scope", gaps=None):
        rp_dict = (rp or _make_review_pass()).to_dict()
        ds_dict = (ds or _make_decision_summary()).to_dict()
        return build_forward_guidance_prompt(
            review_pass_dict=rp_dict,
            decision_summary_dict=ds_dict,
            conflicts=conflicts or [],
            version_scope=scope,
            coverage_gaps=gaps,
        )

    def test_all_five_output_headers_present(self):
        prompt = self._prompt()
        for h in ["STRENGTHEN_WEAK_AREAS", "RESOLVE_KEY_DECISIONS",
                  "IMPROVE_CREDIBILITY", "ACCELERATE_CLIENT_ALIGNMENT",
                  "OPTIONAL_ENHANCEMENTS"]:
            assert f"---{h}---" in prompt

    def test_still_weak_items_appear_in_prompt(self):
        rp = _make_review_pass(domain_weak={"scope": ["Scope lacks detail"]})
        prompt = self._prompt(rp=rp)
        assert "Scope lacks detail" in prompt

    def test_open_decisions_appear_in_prompt(self):
        ds = _make_decision_summary(open_items=["DR strategy unresolved"])
        prompt = self._prompt(ds=ds)
        assert "DR strategy unresolved" in prompt

    def test_conflict_descriptions_appear_in_prompt(self):
        conflicts = [ConflictEntry(category="arch", description="Conflicting architecture views",
                                   review_ids=["r1", "r2"])]
        prompt = self._prompt(conflicts=conflicts)
        assert "Conflicting architecture views" in prompt

    def test_scope_truncated_to_600_chars(self):
        long_scope = "X" * 1000
        prompt = self._prompt(scope=long_scope)
        # The truncated scope appears in the prompt
        assert "X" * 600 in prompt
        assert "X" * 601 not in prompt

    def test_coverage_gaps_appear_in_prompt(self):
        prompt = self._prompt(gaps=["Security / Compliance: Not Yet Addressed"])
        assert "Security / Compliance" in prompt

    def test_none_coverage_gaps_omits_gaps_section_content(self):
        prompt = self._prompt(gaps=None)
        assert "COVERAGE GAPS" in prompt  # header still present
        assert "(none)" in prompt          # but shows (none)

    def test_no_still_weak_shows_none_placeholder(self):
        prompt = self._prompt(rp=_make_review_pass())
        assert "(none)" in prompt

    def test_no_open_decisions_shows_none_placeholder(self):
        prompt = self._prompt(ds=_make_decision_summary(open_items=[]))
        assert "(none)" in prompt



# ═════════════════════════════════════════════════════════════════════════════
# C  _run_forward_guidance (files_only) — S4-01 / S4-02
# ═════════════════════════════════════════════════════════════════════════════

class TestRunForwardGuidanceDeterministic:
    """All acceptance criteria from S4-01 and S4-02 — deterministic path."""

    def _run(self, ds=None, coverage=None, rp=None, conflicts=None):
        from processors.proposal_generator import _run_forward_guidance
        return _run_forward_guidance(
            review_pass=rp or _make_review_pass(),
            decision_summary=ds or _make_decision_summary(),
            conflicts=conflicts or [],
            proposal_coverage=coverage or _make_coverage(),
            version_scope="Migrate legacy ERP to Azure cloud.",
            ai_backend="files_only",
        )

    # ── S4-01 AC3: files_only → one item per open decision ───────────────────

    def test_ac3_one_item_per_open_decision(self):
        """AC3: files_only → one item in resolve_key_decisions per open decision."""
        ds = _make_decision_summary(open_items=["DR strategy", "Platform choice"])
        result = self._run(ds=ds)
        assert len(result.resolve_key_decisions) == 2

    def test_ac3_resolve_item_uses_decision_text_as_issue(self):
        ds = _make_decision_summary(open_items=["Choose between AWS and Azure"])
        result = self._run(ds=ds)
        assert result.resolve_key_decisions[0].issue == "Choose between AWS and Azure"

    def test_ac3_resolve_item_has_template_why_and_action(self):
        ds = _make_decision_summary(open_items=["DR strategy unresolved"])
        result = self._run(ds=ds)
        item = result.resolve_key_decisions[0]
        assert item.why_it_matters != ""
        assert item.suggested_action != ""

    def test_ac3_no_open_decisions_resolve_list_empty(self):
        ds = _make_decision_summary(open_items=[])
        result = self._run(ds=ds)
        assert result.resolve_key_decisions == []

    # ── S4-01 AC4: one item per "Not Yet Addressed" domain ───────────────────

    def test_ac4_one_item_per_not_yet_addressed_domain(self):
        """AC4: files_only → one item per 'Not Yet Addressed' coverage domain."""
        coverage = _make_coverage({
            "security_compliance": "Not Yet Addressed",
            "commercials": "Not Yet Addressed",
        })
        result = self._run(coverage=coverage)
        assert len(result.strengthen_weak_areas) == 2

    def test_ac4_strengthen_item_mentions_domain_name(self):
        coverage = _make_coverage({"security_compliance": "Not Yet Addressed"})
        result = self._run(coverage=coverage)
        issues = " ".join(i.issue for i in result.strengthen_weak_areas)
        assert "Security" in issues or "Compliance" in issues

    def test_ac4_partial_domain_does_not_generate_strengthen_item(self):
        """Partial domains are NOT Not Yet Addressed — no strengthen item."""
        coverage = _make_coverage({"delivery": "Partial"})
        result = self._run(coverage=coverage)
        assert result.strengthen_weak_areas == []

    def test_ac4_all_addressed_no_strengthen_items(self):
        coverage = _make_coverage()  # all Addressed
        result = self._run(coverage=coverage)
        assert result.strengthen_weak_areas == []

    # ── S4-01 AC5: each item has non-empty required fields ───────────────────

    def test_ac5_each_item_has_non_empty_issue(self):
        ds = _make_decision_summary(open_items=["DR strategy"])
        coverage = _make_coverage({"security_compliance": "Not Yet Addressed"})
        result = self._run(ds=ds, coverage=coverage)
        all_items = (
            result.strengthen_weak_areas + result.resolve_key_decisions +
            result.improve_credibility + result.accelerate_client_alignment +
            result.optional_enhancements
        )
        for item in all_items:
            assert item.issue != "", f"Empty issue found: {item}"

    def test_ac5_each_item_has_non_empty_why_it_matters(self):
        ds = _make_decision_summary(open_items=["DR strategy"])
        coverage = _make_coverage({"security_compliance": "Not Yet Addressed"})
        result = self._run(ds=ds, coverage=coverage)
        all_items = (
            result.strengthen_weak_areas + result.resolve_key_decisions +
            result.accelerate_client_alignment
        )
        for item in all_items:
            assert item.why_it_matters != "", f"Empty why_it_matters: {item}"

    def test_ac5_each_item_has_non_empty_suggested_action(self):
        ds = _make_decision_summary(open_items=["DR strategy"])
        result = self._run(ds=ds)
        for item in result.resolve_key_decisions:
            assert item.suggested_action != ""

    # ── S4-01 AC6: trade_off_or_constraint is empty string not None ──────────

    def test_ac6_trade_off_is_empty_string_not_none(self):
        """AC6: trade_off_or_constraint is '' (not None) when no constraint applies."""
        ds = _make_decision_summary(open_items=["DR strategy"])
        coverage = _make_coverage({"security_compliance": "Not Yet Addressed"})
        result = self._run(ds=ds, coverage=coverage)
        all_items = (
            result.strengthen_weak_areas + result.resolve_key_decisions +
            result.accelerate_client_alignment
        )
        for item in all_items:
            assert item.trade_off_or_constraint is not None
            assert isinstance(item.trade_off_or_constraint, str)

    # ── S4-01 AC7: generated_by and generated_at populated ───────────────────

    def test_ac7_generated_by_files_only(self):
        result = self._run()
        assert result.generated_by == "files_only"

    def test_ac7_generated_at_is_iso_timestamp(self):
        import re
        result = self._run()
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", result.generated_at)

    # ── S4-02 AC1: 2 open decisions → 2 resolve items ────────────────────────

    def test_s402_ac1_two_open_decisions_two_resolve_items(self):
        """S4-02 AC1: 2 open decisions → 2 items in resolve_key_decisions."""
        ds = _make_decision_summary(open_items=["Decision A", "Decision B"])
        result = self._run(ds=ds)
        assert len(result.resolve_key_decisions) == 2
        texts = [i.issue for i in result.resolve_key_decisions]
        assert "Decision A" in texts
        assert "Decision B" in texts

    # ── S4-02 AC2: Not Yet Addressed domain → strengthen item ────────────────

    def test_s402_ac2_not_yet_addressed_security_creates_strengthen_item(self):
        """S4-02 AC2: 'Security/Compliance: Not Yet Addressed' → strengthen item."""
        coverage = _make_coverage({"security_compliance": "Not Yet Addressed"})
        result = self._run(coverage=coverage)
        assert len(result.strengthen_weak_areas) == 1
        assert "Security" in result.strengthen_weak_areas[0].issue or \
               "Compliance" in result.strengthen_weak_areas[0].issue

    # ── S4-02 AC3: optional_enhancements always empty ────────────────────────

    def test_s402_ac3_optional_enhancements_always_empty_in_files_only(self):
        """S4-02 AC3: optional_enhancements is always [] in files_only mode."""
        ds = _make_decision_summary(open_items=["Decision X"])
        coverage = _make_coverage({"operations": "Not Yet Addressed"})
        result = self._run(ds=ds, coverage=coverage)
        assert result.optional_enhancements == []

    # ── S4-02 AC4: no inputs → all lists empty, no error ─────────────────────

    def test_s402_ac4_no_open_decisions_all_addressed_returns_empty_guidance(self):
        """S4-02 AC4: no open decisions, all domains Addressed → all lists empty."""
        ds = _make_decision_summary(open_items=[], blockers=[])
        coverage = _make_coverage()  # all Addressed
        result = self._run(ds=ds, coverage=coverage)
        assert result.strengthen_weak_areas == []
        assert result.resolve_key_decisions == []
        assert result.improve_credibility == []
        assert result.accelerate_client_alignment == []
        assert result.optional_enhancements == []

    # ── Sign-off blockers → accelerate_client_alignment ──────────────────────

    def test_sign_off_blockers_go_to_accelerate_alignment(self):
        ds = _make_decision_summary(
            open_items=["Security audit must pass"],
            blockers=["Security audit must pass"],
        )
        result = self._run(ds=ds)
        assert len(result.accelerate_client_alignment) >= 1
        texts = " ".join(i.issue for i in result.accelerate_client_alignment)
        assert "Security audit must pass" in texts

    def test_no_blockers_accelerate_list_empty(self):
        ds = _make_decision_summary(open_items=["DR strategy"], blockers=[])
        result = self._run(ds=ds)
        assert result.accelerate_client_alignment == []

    # ── Return type is always ForwardGuidance ────────────────────────────────

    def test_always_returns_forward_guidance_instance(self):
        result = self._run()
        assert isinstance(result, ForwardGuidance)

    def test_to_dict_produces_all_required_keys(self):
        result = self._run()
        d = result.to_dict()
        for key in ["strengthen_weak_areas", "resolve_key_decisions",
                    "improve_credibility", "accelerate_client_alignment",
                    "optional_enhancements", "generated_by", "generated_at"]:
            assert key in d



# ═════════════════════════════════════════════════════════════════════════════
# D  Generator integration — forward_guidance wired end-to-end
# ═════════════════════════════════════════════════════════════════════════════

class TestGeneratorIntegration:
    """End-to-end: generate_proposal_document() populates forward_guidance."""

    def _generate(self, isolated_db, findings=None, decision_points=None,
                  scope="Deliver Azure migration with security and compliance audit.",
                  supp_ids=None, extra_reviews=()):
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

    # ── S4-01 AC8: stored on document and persisted ───────────────────────────

    def test_forward_guidance_populated_on_single_review(self, isolated_db):
        """AC8: forward_guidance is not None on single-review path."""
        result = self._generate(isolated_db)
        assert result.get("forward_guidance") is not None

    def test_forward_guidance_has_all_five_keys(self, isolated_db):
        result = self._generate(isolated_db)
        fg = result["forward_guidance"]
        for key in ["strengthen_weak_areas", "resolve_key_decisions",
                    "improve_credibility", "accelerate_client_alignment",
                    "optional_enhancements"]:
            assert key in fg, f"Missing key: {key}"

    def test_forward_guidance_generated_by_populated(self, isolated_db):
        result = self._generate(isolated_db)
        assert result["forward_guidance"]["generated_by"] != ""

    def test_forward_guidance_generated_at_is_iso_timestamp(self, isolated_db):
        import re
        result = self._generate(isolated_db)
        ts = result["forward_guidance"].get("generated_at", "")
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts)

    def test_no_open_decisions_resolve_list_empty(self, isolated_db):
        """No decision_points → resolve_key_decisions is empty."""
        result = self._generate(isolated_db, decision_points=[])
        fg = result["forward_guidance"]
        assert fg["resolve_key_decisions"] == []

    def test_open_decision_point_creates_resolve_item(self, isolated_db):
        """Open decision_point → appears in resolve_key_decisions."""
        dps = [{"text": "Choose DR approach", "category": "ops", "status": "open"}]
        result = self._generate(isolated_db, decision_points=dps)
        fg = result["forward_guidance"]
        assert len(fg["resolve_key_decisions"]) >= 1
        assert "Choose DR approach" in fg["resolve_key_decisions"][0]["issue"]

    def test_no_security_risks_generates_strengthen_item(self, isolated_db):
        """No security-signal content → security domain Not Yet Addressed →
        strengthen_weak_areas has an item for it."""
        result = self._generate(isolated_db, findings={
            "risks":       ["Timeline risk", "Budget pressure"],
            "action_items":["Deploy infrastructure"],
            "assumptions": [], "dependencies": [], "constraints": [],
        })
        fg = result["forward_guidance"]
        issues = " ".join(i["issue"] for i in fg["strengthen_weak_areas"])
        assert "Security" in issues or "Compliance" in issues

    def test_optional_enhancements_always_empty_in_files_only(self, isolated_db):
        result = self._generate(isolated_db)
        assert result["forward_guidance"]["optional_enhancements"] == []

    def test_existing_sprint3_fields_still_present(self, isolated_db):
        """Sprint 3 fields still populated alongside Sprint 4."""
        result = self._generate(isolated_db)
        assert result.get("proposal_coverage") is not None
        assert result.get("decision_summary") is not None

    def test_existing_sprint2_fields_still_present(self, isolated_db):
        """Sprint 2 fields still populated alongside Sprint 4."""
        result = self._generate(isolated_db)
        assert result.get("review_pass") is not None
        assert result.get("input_snapshot") is not None

    def test_existing_core_fields_unaffected(self, isolated_db):
        """Sprint 4 must not break core proposal document fields."""
        result = self._generate(isolated_db)
        assert result.get("exec_summary", "") != ""
        assert isinstance(result.get("delivery_phases"), list)
        assert len(result["delivery_phases"]) > 0
        assert result.get("doc_id", "").startswith("doc_")

    def test_forward_guidance_persisted_to_db(self, isolated_db):
        """AC8: forward_guidance written to proposal_documents DB column."""
        result = self._generate(isolated_db)
        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT forward_guidance FROM proposal_documents WHERE doc_id=?",
            (doc_id,),
        )
        assert row is not None
        assert row["forward_guidance"] is not None, "forward_guidance not persisted to DB"

    def test_forward_guidance_db_column_parseable_json(self, isolated_db):
        import json
        result = self._generate(isolated_db)
        doc_id = result.get("doc_id")
        row = isolated_db.fetchone(
            "SELECT forward_guidance FROM proposal_documents WHERE doc_id=?",
            (doc_id,),
        )
        fg = json.loads(row["forward_guidance"])
        assert "strengthen_weak_areas" in fg
        assert "resolve_key_decisions" in fg



# ═════════════════════════════════════════════════════════════════════════════
# E  DB persistence — forward_guidance round-trip
# ═════════════════════════════════════════════════════════════════════════════

class TestDBPersistence:
    """forward_guidance round-trips through the DB correctly."""

    def test_forward_guidance_written_and_read_back_intact(self, isolated_db):
        import uuid
        from db.decision_log import save_proposal_document, get_latest_proposal_document

        fg = ForwardGuidance(
            strengthen_weak_areas=[
                ForwardGuidanceItem(
                    issue="Security coverage missing",
                    why_it_matters="Client requires ISO 27001",
                    suggested_action="Add security section",
                    trade_off_or_constraint="Extra review cycle needed",
                )
            ],
            resolve_key_decisions=[
                ForwardGuidanceItem(
                    issue="DR strategy unresolved",
                    why_it_matters="Blocks sign-off",
                    suggested_action="Schedule workshop",
                    trade_off_or_constraint="",
                )
            ],
            improve_credibility=[],
            accelerate_client_alignment=[],
            optional_enhancements=[],
            generated_by="files_only",
            generated_at="2026-01-01T00:00:00+00:00",
        )

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc = {
            "doc_id": doc_id, "project_id": "p1", "proposal_ver_id": "pv_s4",
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
            "proposal_coverage": None,
            "decision_summary": None,
            "forward_guidance": fg.to_dict(),
        }
        save_proposal_document(doc)
        retrieved = get_latest_proposal_document("p1", "pv_s4")

        assert retrieved is not None
        fg_rt = retrieved["forward_guidance"]
        assert fg_rt is not None

        assert len(fg_rt["strengthen_weak_areas"]) == 1
        assert fg_rt["strengthen_weak_areas"][0]["issue"] == "Security coverage missing"
        assert fg_rt["strengthen_weak_areas"][0]["trade_off_or_constraint"] == "Extra review cycle needed"

        assert len(fg_rt["resolve_key_decisions"]) == 1
        assert fg_rt["resolve_key_decisions"][0]["issue"] == "DR strategy unresolved"
        assert fg_rt["resolve_key_decisions"][0]["trade_off_or_constraint"] == ""

        assert fg_rt["optional_enhancements"] == []
        assert fg_rt["generated_by"] == "files_only"

    def test_null_forward_guidance_reads_back_as_none(self, isolated_db):
        """Legacy rows with no forward_guidance read back as None."""
        from db.decision_log import _row_to_doc
        import uuid

        row = {
            "doc_id": f"doc_{uuid.uuid4().hex[:8]}",
            "project_id": "p1", "proposal_ver_id": "pv_legacy",
            "generated_at": "2026-01-01T00:00:00+00:00", "ai_backend": "files_only",
            "exec_summary": "", "scope": "", "delivery_phases": None, "gantt_data": None,
            "risks": None, "assumptions": None, "exclusions": None,
            "responsibilities": None, "acceptance_criteria": None,
            "version_label": "", "review_persona": "", "hierarchy_version_id": "",
            "active_review_id": "", "word_count": 0,
        }
        result = _row_to_doc(row)
        assert result["forward_guidance"] is None

    def test_forward_guidance_column_exists_in_schema(self, isolated_db):
        """forward_guidance column must exist in proposal_documents table."""
        cols = {r[1] for r in isolated_db.conn.execute(
            "PRAGMA table_info(proposal_documents)"
        ).fetchall()}
        assert "forward_guidance" in cols, (
            "'forward_guidance' column missing from proposal_documents table"
        )

    def test_all_six_synthesis_columns_present(self, isolated_db):
        """All six PDAE-MS-01 columns present (sprint 2 + 3 + 4)."""
        cols = {r[1] for r in isolated_db.conn.execute(
            "PRAGMA table_info(proposal_documents)"
        ).fetchall()}
        for col in ["input_snapshot", "reconciliation_result", "review_pass",
                    "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert col in cols, f"Missing column: {col}"

    def test_forward_guidance_from_dict_round_trip(self):
        fg = ForwardGuidance(
            strengthen_weak_areas=[ForwardGuidanceItem(
                issue="i", why_it_matters="w", suggested_action="a",
                trade_off_or_constraint="",
            )],
            resolve_key_decisions=[],
            improve_credibility=[],
            accelerate_client_alignment=[],
            optional_enhancements=[],
            generated_by="files_only",
            generated_at="2026-01-01T00:00:00+00:00",
        )
        restored = ForwardGuidance.from_dict(fg.to_dict())
        assert len(restored.strengthen_weak_areas) == 1
        assert restored.strengthen_weak_areas[0].issue == "i"
        assert restored.generated_by == "files_only"



# ═════════════════════════════════════════════════════════════════════════════
# F  Sprint 1 + 2 + 3 regression — no prior behaviour broken
# ═════════════════════════════════════════════════════════════════════════════

class TestPriorSprintRegression:
    """Guard all prior sprint contracts against Sprint 4 changes."""

    # ── Sprint 1 dataclasses still importable ────────────────────────────────

    def test_s1_all_sprint1_dataclasses_importable(self):
        from models.proposal import (
            NormalizedItem, ConflictEntry, ReconciliationResult,
        )

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

    # ── Sprint 2 contracts ───────────────────────────────────────────────────

    def test_s2_generate_signature_has_supplemental_param(self):
        import inspect
        from processors.proposal_generator import generate_proposal_document
        params = list(inspect.signature(generate_proposal_document).parameters.keys())
        assert "supplemental_review_ids" in params

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

    def test_s2_input_snapshot_still_single_mode_on_no_supplementals(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        assert result["input_snapshot"]["generation_mode"] == "single"

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

    def test_s2_handler_rejects_non_list_supplemental_ids(self):
        from handlers.proposal import handle_generate_proposal_doc
        statuses = []

        def respond(payload, status=200):
            statuses.append(status)

        with patch("services.proposal.generate_proposal_doc") as mock_svc:
            mock_svc.return_value = {"doc_id": "x"}
            handle_generate_proposal_doc("proj1", {
                "proposal_ver_id": "pv1", "hierarchy_version_id": "v1",
                "review_id": "r1", "supplemental_review_ids": "r2",
            }, respond)
        assert statuses[0] == 422

    # ── Sprint 3 contracts ───────────────────────────────────────────────────

    def test_s3_proposal_coverage_still_populated(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        assert result.get("proposal_coverage") is not None
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in result["proposal_coverage"]

    def test_s3_decision_summary_still_populated(self, isolated_db):
        from processors.proposal_generator import generate_proposal_document
        v = _make_version()
        r = _make_review()
        with patch("processors.proposal_generator._check_generation_gate") as mock_gate, \
             patch("db.decision_log.log_decision"), \
             patch("processors.review_quality.compute_decision_readiness", return_value={}):
            mock_gate.return_value = {"ok": True, "version": v, "review": r}
            result = generate_proposal_document("proj1", "pv1", "v1", "r1")
        ds = result.get("decision_summary")
        assert ds is not None
        for key in ["confirmed", "open", "sign_off_blockers"]:
            assert key in ds

    def test_s3_compute_proposal_coverage_unaffected(self):
        from processors.review_synthesizer import compute_proposal_coverage
        recon = {"reconciled_findings": {
            "risks": ["Security auth failure", "GDPR compliance gap"],
            "action_items": [], "assumptions": [], "dependencies": [], "constraints": [],
        }}
        result = compute_proposal_coverage(recon, _make_review_pass(), [])
        assert result.security_compliance.status == "Addressed"

    # ── ProposalDocument default fields ──────────────────────────────────────

    def test_proposal_document_forward_guidance_defaults_to_none(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument()
        assert doc.forward_guidance is None

    def test_proposal_document_all_six_synthesis_fields_default_none(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument()
        for f in ["input_snapshot", "reconciliation_result", "review_pass",
                  "proposal_coverage", "decision_summary", "forward_guidance"]:
            assert getattr(doc, f) is None

    def test_proposal_document_to_dict_includes_forward_guidance(self):
        from models.proposal import ProposalDocument
        doc = ProposalDocument()
        d = doc.to_dict()
        assert "forward_guidance" in d
        assert d["forward_guidance"] is None

    # ── Existing model constants untouched ───────────────────────────────────

    def test_existing_model_constants_intact(self):
        from models.proposal import (
            VALID_PROPOSAL_STATUSES, VALID_PROPOSAL_QUALITY,
            FEEDBACK_CATEGORIES, FEEDBACK_ITEM_STATUS,
        )
        assert "draft" in VALID_PROPOSAL_STATUSES
        assert "complete" in VALID_PROPOSAL_QUALITY
        assert "accepted" in FEEDBACK_CATEGORIES
        assert "new" in FEEDBACK_ITEM_STATUS

    # ── Sprint 4 dataclasses importable and complete ──────────────────────────

    def test_s4_forward_guidance_item_importable(self):
        from models.proposal import ForwardGuidanceItem
        item = ForwardGuidanceItem(
            issue="test", why_it_matters="important",
            suggested_action="do it", trade_off_or_constraint="",
        )
        d = item.to_dict()
        assert d["issue"] == "test"
        assert d["trade_off_or_constraint"] == ""

    def test_s4_forward_guidance_importable(self):
        from models.proposal import ForwardGuidance, ForwardGuidanceItem
        fg = ForwardGuidance()
        d = fg.to_dict()
        for k in ["strengthen_weak_areas", "resolve_key_decisions", "improve_credibility",
                  "accelerate_client_alignment", "optional_enhancements",
                  "generated_by", "generated_at"]:
            assert k in d

    def test_s4_forward_guidance_from_dict_handles_missing_keys(self):
        """ForwardGuidance.from_dict() is safe with empty dict (backward compat)."""
        fg = ForwardGuidance.from_dict({})
        assert fg.strengthen_weak_areas == []
        assert fg.optional_enhancements == []
        assert fg.generated_by == ""
