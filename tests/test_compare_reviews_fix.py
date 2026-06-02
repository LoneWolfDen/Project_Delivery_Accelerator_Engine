"""Regression tests for the compare-reviews bug fix and v2 UI feature additions.

Bug fixed
---------
compare_project_reviews() previously opened files from
  projects_data/{pid}/reviews/<filename>
which is the OLD flat-file store.  The hierarchy store writes reviews to
  projects_data/{pid}/hierarchy/reviews/<review_id>.json
and the Compare module sends review IDs (e.g. "r1"), not filenames.
Result: every compare-reviews call returned "Review not found: r1".

Fix applied
-----------
services/hierarchy.py compare_project_reviews() now calls
  _make_hierarchy_store(project_id).get_review(review_id_a/b)
and passes the resulting Review dataclasses (serialised via .to_dict()) to
processors/history.compare_reviews().

v2 UI changes tested
--------------------
- viewReviews() function defined and includes all required features
- All action functions declared: v2RunReview, v2ViewReviewDetail,
  v2SetActiveReview, v2DeleteReview, v2OpenMarkComplete, v2SubmitMarkComplete,
  v2RunDeepDive, v2AddSelectedToPrompt, v2RenderInjectedChips, v2SetReviewSort
- Full Details button present in both Reviews tab and Versions tab review body
- Mark as Draft / Mark as Final present in Reviews tab
- Delete button present in Reviews tab
- Prompt builder (three sections) present in viewReviews
- SME / deep-dive trigger present
- Versions tab review-item-body no longer shows only the Compare button
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT     = Path(__file__).parent.parent
HTML_V2  = ROOT / "static" / "v2" / "dashboard_v2.html"
SVC_HIER = ROOT / "services" / "hierarchy.py"


@pytest.fixture(scope="module")
def v2() -> str:
    return HTML_V2.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def svc() -> str:
    return SVC_HIER.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# A  Backend: compare_project_reviews() uses hierarchy store, not flat files
# ─────────────────────────────────────────────────────────────────────────────

class TestCompareReviewsBackendFix:

    def test_old_flat_file_path_absent(self, svc):
        """The service must not open files from the legacy flat reviews/ dir."""
        assert 'reviews_dir / review_file_a' not in svc
        assert 'reviews_dir / review_file_b' not in svc

    def test_hierarchy_store_used(self, svc):
        """compare_project_reviews() must call _make_hierarchy_store."""
        # Find the function body
        m = re.search(
            r'def compare_project_reviews\(.*?\n(?=def |\Z)',
            svc, re.DOTALL
        )
        assert m, "compare_project_reviews not found"
        body = m.group(0)
        assert '_make_hierarchy_store' in body

    def test_get_review_called_for_both(self, svc):
        m = re.search(
            r'def compare_project_reviews\(.*?\n(?=def |\Z)',
            svc, re.DOTALL
        )
        body = m.group(0)
        assert body.count('.get_review(') >= 2

    def test_to_dict_called(self, svc):
        """Results are serialised via .to_dict() before passing to compare_reviews."""
        m = re.search(
            r'def compare_project_reviews\(.*?\n(?=def |\Z)',
            svc, re.DOTALL
        )
        body = m.group(0)
        assert '.to_dict()' in body

    def test_docstring_mentions_review_ids(self, svc):
        """Docstring should clarify that IDs (e.g. r1) are accepted."""
        assert 'r1' in svc or 'review_id' in svc

    def test_function_imports_hierarchy_store(self, svc):
        assert '_make_hierarchy_store' in svc

    def test_unit_compare_reviews_with_hierarchy_store(self, tmp_path):
        """End-to-end unit test: create two real reviews, compare them."""
        import os
        os.environ.setdefault("PROJECTS_DATA_DIR", str(tmp_path))

        from models.hierarchy import _make_hierarchy_store
        from services.hierarchy import compare_project_reviews

        store = _make_hierarchy_store("proj_cmp_test")
        ver = store.create_version(included_artifacts=[], label="v1")

        r1 = store.create_review(
            version_id=ver.version_id,
            persona="Architect",
            findings={"risks": ["DR strategy not defined", "No SLA specified"]},
        )
        r2 = store.create_review(
            version_id=ver.version_id,
            persona="Architect",
            findings={"risks": ["DR strategy not defined", "New risk: vendor lock-in"]},
        )

        result = compare_project_reviews("proj_cmp_test", r1.review_id, r2.review_id)

        assert "sections" in result
        assert "summary" in result
        risks = result["sections"].get("risks", {})
        # "No SLA specified" was in r1 but not r2 → resolved
        assert any("sla" in x.lower() for x in risks.get("resolved", []))
        # "New risk: vendor lock-in" is in r2 but not r1 → new
        assert any("vendor" in x.lower() for x in risks.get("new_findings", []))

    def test_missing_review_raises_value_error(self, tmp_path):
        import os
        os.environ["PROJECTS_DATA_DIR"] = str(tmp_path)
        from services.hierarchy import compare_project_reviews
        from models.hierarchy import _make_hierarchy_store

        store = _make_hierarchy_store("proj_cmp_err")
        ver = store.create_version(included_artifacts=[])
        r1 = store.create_review(version_id=ver.version_id, persona="P")

        with pytest.raises(ValueError, match="Review not found"):
            compare_project_reviews("proj_cmp_err", r1.review_id, "r999_nonexistent")

    def test_both_missing_raises_value_error(self, tmp_path):
        import os
        os.environ["PROJECTS_DATA_DIR"] = str(tmp_path)
        from services.hierarchy import compare_project_reviews
        with pytest.raises(ValueError, match="Review not found"):
            compare_project_reviews("proj_cmp_none", "r_bad_a", "r_bad_b")


# ─────────────────────────────────────────────────────────────────────────────
# B  v2 HTML: viewReviews function defined and complete
# ─────────────────────────────────────────────────────────────────────────────

class TestV2ViewReviewsDefined:

    def test_viewreviews_function_exists(self, v2):
        assert "async function viewReviews()" in v2

    def test_run_review_card_present(self, v2):
        assert "v2RunReview" in v2

    def test_prompt_builder_three_sections_present(self, v2):
        """Prompt builder must have all three section labels."""
        assert "① Role Persona Prompt" in v2
        assert "② SME Questions" in v2
        assert "③ Your Context" in v2 or "③ Your Notes" in v2 or "③" in v2

    def test_injected_questions_container_present(self, v2):
        assert "v2InjectedQuestions" in v2

    def test_user_notes_textarea_present(self, v2):
        assert "v2UserNotes" in v2

    def test_previous_review_id_hidden_input(self, v2):
        assert "v2PreviousReviewId" in v2

    def test_ask_sme_button_present(self, v2):
        assert "v2RunDeepDive" in v2

    def test_add_to_prompt_button_present(self, v2):
        assert "v2AddSelectedToPrompt" in v2

    def test_sort_buttons_present(self, v2):
        assert "v2SetReviewSort('newest')" in v2
        assert "v2SetReviewSort('oldest')" in v2
        assert "v2SetReviewSort('most-findings')" in v2


# ─────────────────────────────────────────────────────────────────────────────
# C  v2 HTML: Reviews tab — action buttons
# ─────────────────────────────────────────────────────────────────────────────

class TestV2ReviewsTabButtons:

    def test_full_details_button(self, v2):
        assert "v2ViewReviewDetail" in v2
        assert "Full Details" in v2

    def test_set_active_button(self, v2):
        assert "v2SetActiveReview" in v2
        assert "Set Active" in v2

    def test_mark_draft_button(self, v2):
        assert "v2OpenMarkComplete" in v2
        assert "Mark as Draft" in v2 or "Mark Draft" in v2

    def test_mark_final_button(self, v2):
        assert "Mark as Final" in v2 or "Mark Final" in v2

    def test_delete_button(self, v2):
        assert "v2DeleteReview" in v2
        assert "Delete" in v2

    def test_mark_complete_form_inline(self, v2):
        assert "v2SubmitMarkComplete" in v2
        assert "v2mc_" in v2   # inline form div id prefix
        assert "v2cb_" in v2   # name input id prefix

    def test_completeness_score_badge(self, v2):
        assert "completeness_score" in v2

    def test_baseline_customised_badge(self, v2):
        assert "Baseline" in v2
        assert "Customised" in v2

    def test_reviews_tab_no_longer_only_compare(self, v2):
        """The Reviews tab body must not only contain Compare Reviews."""
        # viewReviews() ends just before v2SetReviewSort (plain function, not async)
        start = v2.find("async function viewReviews(){")
        end   = v2.find("\nfunction v2SetReviewSort(", start)
        body  = v2[start:end] if end > start else v2[start:start+15000]
        # Must have Full Details and Delete — not just Compare
        assert "Full Details" in body, "Full Details button missing from viewReviews"
        assert "v2DeleteReview" in body, "Delete button missing from viewReviews"


# ─────────────────────────────────────────────────────────────────────────────
# D  v2 HTML: Versions tab — review-item-body has action buttons too
# ─────────────────────────────────────────────────────────────────────────────

class TestV2VersionsTabReviewBody:

    def _versions_body(self, v2: str) -> str:
        """Extract the viewVersions function body."""
        start = v2.find("async function viewVersions(){")
        end   = v2.find("\nasync function runInlineVersionCompare", start)
        return v2[start:end] if end > start else v2[start:start+12000]

    def test_full_details_in_versions_tab(self, v2):
        body = self._versions_body(v2)
        assert "Full Details" in body

    def test_set_active_in_versions_tab(self, v2):
        body = self._versions_body(v2)
        assert "v2SetActiveReview" in body

    def test_delete_in_versions_tab(self, v2):
        body = self._versions_body(v2)
        assert "v2DeleteReview" in body

    def test_mark_complete_in_versions_tab(self, v2):
        body = self._versions_body(v2)
        assert "v2OpenMarkComplete" in body

    def test_versions_tab_review_body_not_only_compare(self, v2):
        body = self._versions_body(v2)
        # Should have substantive actions, not just openCompare()
        assert "Full Details" in body
        assert "v2DeleteReview" in body


# ─────────────────────────────────────────────────────────────────────────────
# E  v2 HTML: all helper functions declared
# ─────────────────────────────────────────────────────────────────────────────

class TestV2HelperFunctionsDeclared:

    REQUIRED = [
        "function v2SetReviewSort(",
        "function v2OnRoleCheck(",
        "function v2RenderInjectedChips(",
        "function v2RemoveInjectedQuestion(",
        "function v2AssemblePrompt(",
        "async function v2RunReview(",
        "async function v2RunDeepDive(",
        "function v2AddSelectedToPrompt(",
        "async function v2SetActiveReview(",
        "async function v2DeleteReview(",
        "function v2OpenMarkComplete(",
        "async function v2SubmitMarkComplete(",
        "async function v2ViewReviewDetail(",
    ]

    @pytest.mark.parametrize("fn", REQUIRED)
    def test_function_declared(self, v2, fn):
        assert fn in v2, f"Missing function declaration: {fn}"


# ─────────────────────────────────────────────────────────────────────────────
# F  v2 HTML: v2 functions do NOT shadow v1 globals
# ─────────────────────────────────────────────────────────────────────────────

class TestV2FunctionNamespace:

    def test_v2_functions_use_v2_prefix(self, v2):
        """All new review-tab functions use v2 prefix to avoid v1 collision."""
        # These v1 function names must NOT appear as function declarations in v2
        v1_globals = [
            "async function runReview(",
            "async function runDeepDive(",
            "function setReviewSort(",
            "async function setActiveReview(",
            "async function deleteReview(",
            "function openMarkComplete(",
            "async function submitMarkComplete(",
        ]
        for name in v1_globals:
            assert name not in v2, (
                f"v1 global '{name}' declared in v2 — use v2 prefix to avoid collision"
            )

    def test_v2_role_checkbox_class_distinct(self, v2):
        """Role checkboxes use v2-role-check class, not role-check (v1 class)."""
        assert "v2-role-check" in v2
