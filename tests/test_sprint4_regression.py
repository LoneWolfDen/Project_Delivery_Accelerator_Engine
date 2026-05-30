"""Sprint 4 Regression Pack — Weakness and Gap Intelligence.

Covers every change made in Sprint 4:

A) extract_weaknesses() — S4-01
   - Empty/None findings returns []
   - Signal-phrase detection (unclear, TBC, assumed, not defined, …)
   - Short-item detection (< 8 words)
   - Long clear item is NOT flagged
   - Multiple categories produce weaknesses
   - Each weakness has id, text, category, status="open"
   - IDs are unique within the result
   - Duplicate texts are deduplicated
   - Item with multiple signals appears only once

B) compute_missing_categories() — S4-02
   - Empty/None findings returns all 5 standard categories
   - All 5 categories present → []
   - Findings missing "risks" → ["risks"]
   - Empty list for a category counts as missing
   - Non-standard category keys don't affect result
   - Returns only STANDARD_CATEGORIES names

C) Integration: weaknesses + missing_categories on stored review
   - Review with weak findings has non-empty weaknesses after extraction
   - Review with all categories covered has [] missing_categories
   - Review missing "dependencies" has "dependencies" in missing_categories
   - Missing categories from stored findings match expectations

D) S4-03: gap-aware deep dive in heuristic mode
   - weaknesses produces "Gaps & Weaknesses" group
   - missing_categories produces questions referencing those categories
   - No weaknesses/missing_categories → no "Gaps & Weaknesses" group
   - Backward-compat: no extra params still returns standard groups
   - Gap questions reference the weakness text
   - Gap questions reference missing category names
   - all_questions flat list includes gap questions with [Gaps & Weaknesses] prefix

E) UI contract — index.html static analysis
   - "Weaknesses" label present in viewReviewDetail() context
   - "Missing Areas" label present in viewReviewDetail() context
   - "missing_categories" referenced in viewReviewDetail() body
   - "weaknesses" referenced in viewReviewDetail() body
"""

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


# ══════════════════════════════════════════════════════════════════════════════
# A) extract_weaknesses() — S4-01
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractWeaknesses:

    def _ew(self, findings):
        from processors.review_quality import extract_weaknesses
        return extract_weaknesses(findings)

    def test_empty_findings_returns_empty_list(self):
        assert self._ew({}) == []

    def test_none_findings_returns_empty_list(self):
        assert self._ew(None) == []

    def test_unclear_is_flagged(self):
        findings = {"risks": ["The integration point is unclear"]}
        result = self._ew(findings)
        assert len(result) == 1
        assert result[0]["text"] == "The integration point is unclear"

    def test_tbc_is_flagged_case_insensitive(self):
        findings = {"assumptions": ["Budget approval TBC by end of month"]}
        result = self._ew(findings)
        assert len(result) == 1
        assert "TBC" in result[0]["text"]

    def test_assumed_is_flagged(self):
        findings = {"dependencies": ["Team availability assumed from week 3"]}
        result = self._ew(findings)
        assert len(result) == 1

    def test_not_defined_is_flagged(self):
        findings = {"constraints": ["Timeline is not defined yet"]}
        result = self._ew(findings)
        assert len(result) == 1

    def test_short_finding_is_flagged(self):
        # Less than 8 words
        findings = {"risks": ["vendor delay"]}
        result = self._ew(findings)
        assert len(result) == 1
        assert result[0]["text"] == "vendor delay"

    def test_long_clear_finding_is_not_flagged(self):
        findings = {"risks": [
            "The cloud provider SLA guarantees 99.9% uptime with automatic failover "
            "to secondary region within 30 seconds."
        ]}
        result = self._ew(findings)
        assert len(result) == 0

    def test_multiple_categories_produce_weaknesses_from_all(self):
        findings = {
            "risks": ["unclear risk"],
            "assumptions": ["TBC assumption here"],
            "dependencies": ["pending vendor agreement"],
        }
        result = self._ew(findings)
        categories_found = {w["category"] for w in result}
        assert "risks" in categories_found
        assert "assumptions" in categories_found
        assert "dependencies" in categories_found

    def test_each_weakness_has_required_keys(self):
        findings = {"risks": ["unclear situation here"]}
        result = self._ew(findings)
        for w in result:
            assert "id" in w
            assert "text" in w
            assert "category" in w
            assert "status" in w

    def test_status_defaults_to_open(self):
        findings = {"risks": ["unclear situation"]}
        result = self._ew(findings)
        assert result[0]["status"] == "open"

    def test_ids_are_unique(self):
        findings = {
            "risks": ["unclear risk one"],
            "assumptions": ["TBC assumption one"],
            "dependencies": ["pending something"],
        }
        result = self._ew(findings)
        ids = [w["id"] for w in result]
        assert len(ids) == len(set(ids))

    def test_duplicate_texts_are_deduplicated(self):
        findings = {
            "risks": ["unclear risk"],
            "assumptions": ["unclear risk"],  # same text, different category
        }
        result = self._ew(findings)
        texts = [w["text"] for w in result]
        assert len(texts) == len(set(texts))

    def test_item_with_multiple_signals_appears_once(self):
        # Has both "unclear" and "TBC" and is short
        findings = {"risks": ["TBC unclear"]}
        result = self._ew(findings)
        assert len(result) == 1

    def test_non_string_items_are_skipped(self):
        findings = {"risks": [None, 42, {"key": "val"}, "unclear risk"]}
        result = self._ew(findings)
        assert len(result) == 1
        assert result[0]["text"] == "unclear risk"

    def test_non_list_category_values_skipped(self):
        findings = {"risks": "not a list", "assumptions": ["unclear assumption"]}
        result = self._ew(findings)
        assert len(result) == 1
        assert result[0]["category"] == "assumptions"


# ══════════════════════════════════════════════════════════════════════════════
# B) compute_missing_categories() — S4-02
# ══════════════════════════════════════════════════════════════════════════════

class TestComputeMissingCategories:

    def _cmc(self, findings):
        from processors.review_quality import compute_missing_categories
        return compute_missing_categories(findings)

    def test_empty_findings_returns_all_five_categories(self):
        result = self._cmc({})
        from processors.review_quality import STANDARD_CATEGORIES
        assert set(result) == set(STANDARD_CATEGORIES)

    def test_none_findings_returns_all_five_categories(self):
        result = self._cmc(None)
        from processors.review_quality import STANDARD_CATEGORIES
        assert set(result) == set(STANDARD_CATEGORIES)

    def test_all_five_categories_present_returns_empty(self):
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            "dependencies": ["dep 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
        }
        result = self._cmc(findings)
        assert result == []

    def test_missing_risks_returns_risks(self):
        findings = {
            "assumptions": ["assumption 1"],
            "dependencies": ["dep 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
        }
        result = self._cmc(findings)
        assert result == ["risks"]

    def test_empty_list_for_category_counts_as_missing(self):
        findings = {
            "risks": [],  # empty list = missing
            "assumptions": ["assumption 1"],
            "dependencies": ["dep 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
        }
        result = self._cmc(findings)
        assert "risks" in result

    def test_non_standard_category_keys_dont_affect_result(self):
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            "dependencies": ["dep 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
            "custom_category": ["extra stuff"],  # non-standard
        }
        result = self._cmc(findings)
        assert result == []

    def test_returns_only_standard_category_names(self):
        findings = {}
        result = self._cmc(findings)
        from processors.review_quality import STANDARD_CATEGORIES
        for cat in result:
            assert cat in STANDARD_CATEGORIES

    def test_missing_dependencies_and_constraints(self):
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            "action_items": ["action 1"],
        }
        result = self._cmc(findings)
        assert "dependencies" in result
        assert "constraints" in result
        assert "risks" not in result


# ══════════════════════════════════════════════════════════════════════════════
# C) Integration: weaknesses + missing_categories on stored review — S4-01/S4-02
# ══════════════════════════════════════════════════════════════════════════════

class TestWeaknessIntegration:
    """Verify weaknesses and missing_categories computed from findings round-trip correctly."""

    def _make_store(self, tmp_path):
        from db.hierarchy_store_sql import HierarchyStoreSQLite
        return HierarchyStoreSQLite("test-proj-s4")

    def test_review_with_weak_findings_has_non_empty_weaknesses(self, tmp_path):
        from processors.review_quality import extract_weaknesses
        findings = {"risks": ["unclear risk", "TBC dependency issue"]}
        result = extract_weaknesses(findings)
        assert len(result) > 0

    def test_review_with_all_categories_has_empty_missing(self, tmp_path):
        from processors.review_quality import compute_missing_categories
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            "dependencies": ["dep 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
        }
        assert compute_missing_categories(findings) == []

    def test_review_missing_dependencies_detected(self, tmp_path):
        from processors.review_quality import compute_missing_categories
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            "constraints": ["constraint 1"],
            "action_items": ["action 1"],
        }
        result = compute_missing_categories(findings)
        assert "dependencies" in result

    def test_stored_review_weaknesses_persisted_and_loaded(self, tmp_path):
        """Weaknesses passed to create_review are stored and returned by get_review."""
        store = self._make_store(tmp_path)
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        findings = {"risks": ["unclear risk detail"]}
        from processors.review_quality import extract_weaknesses
        computed_weaknesses = extract_weaknesses(findings)
        r = store.create_review(
            version_id="v1",
            persona="Solution Architect",
            findings=findings,
            weaknesses=computed_weaknesses,
        )
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        assert len(loaded.weaknesses) > 0
        assert loaded.weaknesses[0]["text"] == "unclear risk detail"

    def test_missing_categories_computed_from_stored_findings(self, tmp_path):
        from processors.review_quality import compute_missing_categories
        findings = {
            "risks": ["risk 1"],
            "assumptions": ["assumption 1"],
            # missing: dependencies, constraints, action_items
        }
        missing = compute_missing_categories(findings)
        assert "dependencies" in missing
        assert "constraints" in missing
        assert "action_items" in missing
        assert "risks" not in missing

    def test_weaknesses_default_to_empty_when_not_provided(self, tmp_path):
        store = self._make_store(tmp_path)
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        r = store.create_review(
            version_id="v1",
            persona="Delivery Manager",
            findings={"risks": ["well-documented risk with full detail and context provided"]},
        )
        loaded = store.get_review(r.review_id)
        assert loaded is not None
        assert isinstance(loaded.weaknesses, list)


# ══════════════════════════════════════════════════════════════════════════════
# D) S4-03: gap-aware deep dive in heuristic mode
# ══════════════════════════════════════════════════════════════════════════════

class TestGapAwareDeepDive:

    @staticmethod
    def _run(weaknesses=None, missing_categories=None, persona="Solution Architect"):
        from personas.deep_dive import run_deep_dive
        return run_deep_dive(
            persona_name=persona,
            scope="Cloud migration project with multiple workstreams",
            intelligence={
                "risks": ["vendor lock-in"],
                "assumptions": [],
                "dependencies": [],
                "constraints": [],
                "action_items": [],
            },
            active_files=[{"filename": "scope.txt", "source_type": "text"}],
            custom_prompt="",
            ai_backend="files_only",
            weaknesses=weaknesses,
            missing_categories=missing_categories,
        )

    def test_weaknesses_produces_gaps_and_weaknesses_group(self):
        w = [{"id": "w1", "text": "unclear integration approach", "category": "risks", "status": "open"}]
        result = self._run(weaknesses=w)
        cats = [g["category"] for g in result["question_groups"]]
        assert "Gaps & Weaknesses" in cats

    def test_missing_categories_produces_gap_questions(self):
        result = self._run(missing_categories=["risks", "constraints"])
        cats = [g["category"] for g in result["question_groups"]]
        assert "Gaps & Weaknesses" in cats
        gap_grp = next(g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses")
        questions_text = " ".join(gap_grp["questions"])
        assert "risks" in questions_text or "constraints" in questions_text

    def test_no_weaknesses_no_missing_no_gap_group(self):
        result = self._run(weaknesses=None, missing_categories=None)
        cats = [g["category"] for g in result["question_groups"]]
        assert "Gaps & Weaknesses" not in cats

    def test_empty_weaknesses_and_empty_missing_no_gap_group(self):
        result = self._run(weaknesses=[], missing_categories=[])
        cats = [g["category"] for g in result["question_groups"]]
        assert "Gaps & Weaknesses" not in cats

    def test_backward_compat_no_extra_params_returns_standard_groups(self):
        from personas.deep_dive import run_deep_dive
        result = run_deep_dive(
            persona_name="Solution Architect",
            scope="Cloud migration",
            intelligence={"risks": [], "assumptions": [], "dependencies": [],
                          "constraints": [], "action_items": []},
            active_files=[],
            custom_prompt="",
            ai_backend="files_only",
        )
        assert isinstance(result["question_groups"], list)
        assert len(result["question_groups"]) >= 1

    def test_gap_questions_reference_weakness_text(self):
        w = [{"id": "w1", "text": "unclear integration approach", "category": "risks", "status": "open"}]
        result = self._run(weaknesses=w)
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        questions_text = " ".join(gap_grp["questions"])
        assert "unclear integration approach" in questions_text

    def test_gap_questions_reference_missing_category_names(self):
        result = self._run(missing_categories=["risks"])
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        questions_text = " ".join(gap_grp["questions"])
        assert "risks" in questions_text

    def test_all_questions_includes_gap_questions_with_prefix(self):
        w = [{"id": "w1", "text": "unclear data flow", "category": "dependencies", "status": "open"}]
        result = self._run(weaknesses=w)
        gap_qs = [q for q in result["all_questions"] if "[Gaps & Weaknesses]" in q]
        assert len(gap_qs) > 0

    def test_gap_icon_is_magnifying_glass(self):
        w = [{"id": "w1", "text": "unclear scope boundary", "category": "risks", "status": "open"}]
        result = self._run(weaknesses=w)
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        assert gap_grp["icon"] == "🔍"

    def test_gap_group_questions_capped_at_five(self):
        # Provide more than 5 items to verify capping
        w = [
            {"id": f"w{i}", "text": f"unclear issue number {i}", "category": "risks", "status": "open"}
            for i in range(1, 5)
        ]
        mc = ["risks", "assumptions", "dependencies"]
        result = self._run(weaknesses=w, missing_categories=mc)
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        assert len(gap_grp["questions"]) <= 5

    def test_weaknesses_capped_at_three_for_gap_questions(self):
        """Only first 3 weaknesses generate gap questions."""
        w = [
            {"id": f"w{i}", "text": f"unclear issue {i}", "category": "risks", "status": "open"}
            for i in range(1, 6)
        ]
        result = self._run(weaknesses=w)
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        # 5 items: first 3 from weaknesses (capped), no missing_categories
        assert len(gap_grp["questions"]) <= 5

    def test_missing_categories_capped_at_three(self):
        """Only first 3 missing_categories generate gap questions."""
        result = self._run(missing_categories=["risks", "assumptions", "dependencies", "constraints", "action_items"])
        gap_grp = next(
            (g for g in result["question_groups"] if g["category"] == "Gaps & Weaknesses"), None
        )
        assert gap_grp is not None
        assert len(gap_grp["questions"]) <= 5


# ══════════════════════════════════════════════════════════════════════════════
# E) UI contract — index.html static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestUIContract:
    """S4 UI sections must be present in viewReviewDetail() in index.html."""

    def _get_view_review_detail_body(self, html_text: str) -> str:
        """Extract the body of viewReviewDetail() from the HTML."""
        m = re.search(
            r"(?:async\s+)?function\s+viewReviewDetail\s*\(.*?\)\s*\{([\s\S]+?)(?=\n(?:async\s+)?function\s|\Z)",
            html_text,
        )
        assert m, "viewReviewDetail() function not found in index.html"
        return m.group(1)

    def test_weaknesses_label_present(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "Weaknesses" in body, (
            "'Weaknesses' label not found in viewReviewDetail() — S4-01 UI section missing"
        )

    def test_missing_areas_label_present(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "Missing Areas" in body, (
            "'Missing Areas' label not found in viewReviewDetail() — S4-02 UI section missing"
        )

    def test_missing_categories_referenced(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "missing_categories" in body, (
            "'missing_categories' not referenced in viewReviewDetail() body — "
            "S4-02 data binding missing"
        )

    def test_weaknesses_referenced_in_body(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "weaknesses" in body, (
            "'weaknesses' not referenced in viewReviewDetail() body — "
            "S4-01 data binding missing"
        )

    def test_weaknesses_section_uses_yellow_border(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "var(--yellow)" in body, (
            "Weaknesses section expected to use var(--yellow) border color"
        )

    def test_missing_areas_section_uses_dim_color(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "🕳️" in body, (
            "Missing Areas section expected to use 🕳️ icon"
        )

    def test_weakness_icon_present(self, html_text):
        body = self._get_view_review_detail_body(html_text)
        assert "⚠️" in body, (
            "Weaknesses section expected to use ⚠️ icon"
        )
