"""Sprint 5 Tests — PDAE-MS-01: Frontend Display & Selection.

All tests are HTML static analysis — no backend imports, no DB.
Reads static/index.html once and asserts structural and content contracts
for all seven Sprint 5 stories.

Sections
────────
A  S5-01  Supplemental review selection — form elements + JS wiring
B  S5-02  Conflict warning banner — _renderConflictBanner
C  S5-03  Proposal Review Pass display — _renderProposalReviewPass
D  S5-04  Proposal Coverage table — _renderProposalCoverage
E  S5-05  Decision Summary display — _renderDecisionSummary
F  S5-06  Forward Guidance display — _renderForwardGuidance
G  S5-07  Proposal iteration readiness — _computeProposalReadiness + _renderProposalReadinessBadge
H  Structural integrity — no script-tag nesting, function definitions present
I  Sprint 4 regression — docCard still calls all Sprint 4 artifact renderers
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"


@pytest.fixture(scope="module")
def html():
    return HTML_PATH.read_text(encoding="utf-8")


# ─── helpers ─────────────────────────────────────────────────────────────────

def _fn_body(html: str, name: str) -> str:
    """Extract the source of a JS function by name (greedy until next top-level function)."""
    m = re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{([\s\S]+?)"
        rf"(?=\n(?:async\s+)?function\s|\Z)",
        html,
    )
    assert m, f"function {name}() not found in index.html"
    return m.group(1)


def _fn_exists(html: str, name: str) -> bool:
    return bool(re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(", html
    ))


# ═════════════════════════════════════════════════════════════════════════════
# A  S5-01 — Supplemental review selection
# ═════════════════════════════════════════════════════════════════════════════

class TestS501SupplementalReviewSelection:

    def test_supplemental_row_element_exists(self, html):
        """propSupplementalRow div is present in the form HTML."""
        assert 'id="propSupplementalRow"' in html or "id='propSupplementalRow'" in html

    def test_supplemental_checkboxes_container_exists(self, html):
        """propSupplementalCheckboxes container is present."""
        assert "propSupplementalCheckboxes" in html

    def test_anchor_review_pin_element_exists(self, html):
        """propAnchorReviewPin element is present (shows pinned anchor)."""
        assert "propAnchorReviewPin" in html

    def test_supplemental_row_hidden_by_default(self, html):
        """propSupplementalRow starts hidden (display:none)."""
        m = re.search(r'id=["\']propSupplementalRow["\'][^>]*style=["\'][^"\']*display:none', html)
        assert m, "propSupplementalRow should have display:none by default"

    def test_render_supplemental_reviews_function_defined(self, html):
        """_renderSupplementalReviews() function is defined."""
        assert _fn_exists(html, "_renderSupplementalReviews")

    def test_render_supplemental_reviews_shows_others_not_anchor(self, html):
        """_renderSupplementalReviews filters out anchor from checkboxes."""
        body = _fn_body(html, "_renderSupplementalReviews")
        assert "anchorId" in body
        assert "filter" in body

    def test_render_supplemental_shows_checkbox_inputs(self, html):
        """_renderSupplementalReviews renders checkbox inputs."""
        body = _fn_body(html, "_renderSupplementalReviews")
        assert 'type="checkbox"' in body or "type='checkbox'" in body

    def test_render_supplemental_label_has_persona_and_status(self, html):
        """Checkbox label includes persona, quality_status, and completeness_score."""
        body = _fn_body(html, "_renderSupplementalReviews")
        assert "persona" in body
        assert "quality_status" in body
        assert "completeness_score" in body

    def test_submit_create_proposal_collects_supplemental_ids(self, html):
        """submitCreateProposal collects checked supplemental IDs."""
        body = _fn_body(html, "submitCreateProposal")
        assert "supplemental_review_ids" in body
        assert "propSupplementalCheckboxes" in body

    def test_submit_sends_supplemental_ids_in_generate_body(self, html):
        """submitCreateProposal passes supplemental_review_ids to generate API call."""
        body = _fn_body(html, "submitCreateProposal")
        assert "supplemental_review_ids" in body
        assert "proposal/generate" in body

    def test_supplemental_ids_never_include_anchor(self, html):
        """Anchor review ID is filtered out of supplemental_review_ids."""
        body = _fn_body(html, "submitCreateProposal")
        # Must filter: anchor (active_review_id) excluded from supp array
        assert "active_review_id" in body
        assert "filter" in body or "!==active_review_id" in body or "!=active_review_id" in body

    def test_on_prop_version_change_calls_render_supplemental(self, html):
        """onPropVersionChange calls _renderSupplementalReviews."""
        body = _fn_body(html, "onPropVersionChange")
        assert "_renderSupplementalReviews" in body

    def test_supplemental_row_hidden_when_one_review(self, html):
        """_renderSupplementalReviews hides row when others.length === 0."""
        body = _fn_body(html, "_renderSupplementalReviews")
        assert "display='none'" in body or 'display="none"' in body or "style.display='none'" in body or "style.display=\"none\"" in body

    def test_zero_supplementals_post_body_has_empty_array(self, html):
        """When no checkboxes checked, supplemental_review_ids is an empty array."""
        body = _fn_body(html, "submitCreateProposal")
        # Array.from on empty NodeList produces []
        assert "Array.from" in body or "querySelectorAll" in body


# ═════════════════════════════════════════════════════════════════════════════
# B  S5-02 — Conflict warning banner
# ═════════════════════════════════════════════════════════════════════════════

class TestS502ConflictBanner:

    def test_render_conflict_banner_function_defined(self, html):
        assert _fn_exists(html, "_renderConflictBanner")

    def test_banner_hidden_when_reconciliation_null(self, html):
        """Returns empty string when reconciliation_result is null."""
        body = _fn_body(html, "_renderConflictBanner")
        assert "if(!rr)return" in body.replace(" ", "") or "if(!rr)" in body

    def test_banner_hidden_when_zero_contradictions(self, html):
        """Returns empty string when contradictions array is empty."""
        body = _fn_body(html, "_renderConflictBanner")
        assert "contradictions" in body
        assert "if(!n)return" in body.replace(" ", "") or "if(!n)" in body

    def test_banner_shows_conflict_count(self, html):
        """Banner text includes the conflict count (n)."""
        body = _fn_body(html, "_renderConflictBanner")
        assert "${n}" in body or "'+n+'" in body or "n +" in body

    def test_banner_text_mentions_conflict_and_decision_summary(self, html):
        """Banner text says 'conflict' and mentions Decision Summary."""
        body = _fn_body(html, "_renderConflictBanner")
        assert "conflict" in body.lower()
        assert "Decision Summary" in body or "decision summary" in body.lower()

    def test_banner_uses_yellow_colour(self, html):
        """Conflict banner uses var(--yellow) for colour (warning style)."""
        body = _fn_body(html, "_renderConflictBanner")
        assert "var(--yellow)" in body

    def test_doccard_calls_render_conflict_banner(self, html):
        """docCard rendering code calls _renderConflictBanner(doc)."""
        assert "_renderConflictBanner(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# C  S5-03 — Proposal Review Pass display
# ═════════════════════════════════════════════════════════════════════════════

class TestS503ProposalReviewPass:

    def test_render_proposal_review_pass_function_defined(self, html):
        assert _fn_exists(html, "_renderProposalReviewPass")

    def test_hidden_when_review_pass_null(self, html):
        """Returns empty string when review_pass is null."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "if(!rp)return" in body.replace(" ", "") or "if(!rp)" in body

    def test_all_six_domains_rendered(self, html):
        """All six domain keys are referenced."""
        body = _fn_body(html, "_renderProposalReviewPass")
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in body, f"Domain '{domain}' missing from _renderProposalReviewPass"

    def test_covered_well_sublabel_present(self, html):
        """'Covered Well' sub-label is present."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "Covered Well" in body or "covered_well" in body

    def test_still_weak_sublabel_present(self, html):
        """'Still Weak' sub-label is present."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "Still Weak" in body or "still_weak" in body

    def test_may_block_signoff_sublabel_present(self, html):
        """'May Block Sign-off' sub-label is present."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "Block" in body or "may_block_signoff" in body

    def test_may_block_items_styled_red(self, html):
        """May block sign-off items use red colour."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "var(--red)" in body

    def test_empty_list_shows_none_placeholder(self, html):
        """Empty sub-list renders '(none)' placeholder, not blank."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "(none)" in body

    def test_collapsible_details_element_used(self, html):
        """Uses <details> collapsible pattern."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "<details>" in body or "<details " in body

    def test_section_title_proposal_review_pass(self, html):
        """Section title is 'Proposal Review Pass'."""
        body = _fn_body(html, "_renderProposalReviewPass")
        assert "Proposal Review Pass" in body

    def test_doccard_calls_render_review_pass(self, html):
        assert "_renderProposalReviewPass(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# D  S5-04 — Proposal Coverage table
# ═════════════════════════════════════════════════════════════════════════════

class TestS504ProposalCoverage:

    def test_render_proposal_coverage_function_defined(self, html):
        assert _fn_exists(html, "_renderProposalCoverage")

    def test_hidden_when_coverage_null(self, html):
        body = _fn_body(html, "_renderProposalCoverage")
        assert "if(!cov)return" in body.replace(" ", "") or "if(!cov)" in body

    def test_all_six_domain_keys_referenced(self, html):
        body = _fn_body(html, "_renderProposalCoverage")
        for domain in ["scope", "architecture", "delivery",
                       "security_compliance", "operations", "commercials"]:
            assert domain in body

    def test_addressed_badge_uses_green(self, html):
        """'Addressed' status badge is styled green."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "Addressed" in body
        assert "tag-green" in body

    def test_partial_badge_uses_yellow(self, html):
        """'Partial' status badge is styled yellow/amber."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "Partial" in body
        assert "tag-yellow" in body

    def test_not_yet_addressed_badge_uses_red(self, html):
        """'Not Yet Addressed' status badge is styled red."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "Not Yet Addressed" in body
        assert "tag-red" in body

    def test_none_detected_placeholder_for_empty_themes(self, html):
        """Empty matched_themes shows '(none detected)'."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "none detected" in body

    def test_gap_notes_rendered(self, html):
        """gap_notes field is referenced in the table."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "gap_notes" in body

    def test_matched_themes_rendered(self, html):
        """matched_themes field is referenced."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "matched_themes" in body

    def test_table_element_used(self, html):
        """Uses a <table> element for the six-row layout."""
        body = _fn_body(html, "_renderProposalCoverage")
        assert "<table" in body

    def test_section_title_proposal_coverage(self, html):
        body = _fn_body(html, "_renderProposalCoverage")
        assert "Proposal Coverage" in body

    def test_doccard_calls_render_coverage(self, html):
        assert "_renderProposalCoverage(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# E  S5-05 — Decision Summary display
# ═════════════════════════════════════════════════════════════════════════════

class TestS505DecisionSummary:

    def test_render_decision_summary_function_defined(self, html):
        assert _fn_exists(html, "_renderDecisionSummary")

    def test_hidden_when_decision_summary_null(self, html):
        body = _fn_body(html, "_renderDecisionSummary")
        assert "if(!ds)return" in body.replace(" ", "") or "if(!ds)" in body

    def test_confirmed_decisions_section_present(self, html):
        body = _fn_body(html, "_renderDecisionSummary")
        assert "Confirmed" in body
        assert "confirmed" in body

    def test_open_decisions_section_present(self, html):
        body = _fn_body(html, "_renderDecisionSummary")
        assert "Open" in body
        assert "ds.open" in body or ".open" in body

    def test_sign_off_blockers_section_present(self, html):
        body = _fn_body(html, "_renderDecisionSummary")
        assert "sign_off_blockers" in body or "Sign-off" in body

    def test_empty_list_renders_none_placeholder(self, html):
        """Empty decision lists render 'None' placeholder."""
        body = _fn_body(html, "_renderDecisionSummary")
        assert "None" in body

    def test_blockers_styled_red(self, html):
        """Sign-off Blockers section has red styling."""
        body = _fn_body(html, "_renderDecisionSummary")
        assert "var(--red)" in body

    def test_source_review_id_tag_shown(self, html):
        """Each item shows source_review_id as a tag for traceability."""
        body = _fn_body(html, "_renderDecisionSummary")
        assert "source_review_id" in body

    def test_section_title_decision_summary(self, html):
        body = _fn_body(html, "_renderDecisionSummary")
        assert "Decision Summary" in body

    def test_doccard_calls_render_decision_summary(self, html):
        assert "_renderDecisionSummary(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# F  S5-06 — Forward Guidance display
# ═════════════════════════════════════════════════════════════════════════════

class TestS506ForwardGuidance:

    def test_render_forward_guidance_function_defined(self, html):
        assert _fn_exists(html, "_renderForwardGuidance")

    def test_hidden_when_forward_guidance_null(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        assert "if(!fg)return" in body.replace(" ", "") or "if(!fg)" in body

    def test_hidden_when_total_zero(self, html):
        """Returns empty when all sections are empty (total === 0)."""
        body = _fn_body(html, "_renderForwardGuidance")
        assert "total" in body
        assert "if(!total)" in body.replace(" ", "") or "if(!total)" in body

    def test_all_five_guidance_sections_referenced(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        for key in ["strengthen_weak_areas", "resolve_key_decisions",
                    "improve_credibility", "accelerate_client_alignment",
                    "optional_enhancements"]:
            assert key in body, f"Guidance section '{key}' missing"

    def test_item_renders_issue_field(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        assert "issue" in body

    def test_item_renders_why_it_matters(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        assert "why_it_matters" in body

    def test_item_renders_suggested_action(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        assert "suggested_action" in body

    def test_trade_off_only_shown_when_non_empty(self, html):
        """trade_off_or_constraint is conditional — only shown when non-empty."""
        body = _fn_body(html, "_renderForwardGuidance")
        assert "trade_off_or_constraint" in body
        # Must be conditional (not always rendered)
        assert "if(" in body or "?" in body

    def test_optional_enhancements_conditional(self, html):
        """optional_enhancements section only shown when non-empty (AC2)."""
        body = _fn_body(html, "_renderForwardGuidance")
        assert "optional_enhancements" in body
        # Must be wrapped in a length check
        assert ".length" in body

    def test_section_title_forward_guidance(self, html):
        body = _fn_body(html, "_renderForwardGuidance")
        assert "Forward Guidance" in body

    def test_doccard_calls_render_forward_guidance(self, html):
        assert "_renderForwardGuidance(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# G  S5-07 — Proposal iteration readiness indicator
# ═════════════════════════════════════════════════════════════════════════════

class TestS507ProposalReadiness:

    def test_compute_proposal_readiness_function_defined(self, html):
        assert _fn_exists(html, "_computeProposalReadiness")

    def test_render_proposal_readiness_badge_function_defined(self, html):
        assert _fn_exists(html, "_renderProposalReadinessBadge")

    def test_returns_not_assessed_when_no_coverage_or_ds(self, html):
        """Returns not_assessed when proposal_coverage or decision_summary is null."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "not_assessed" in body or "Not assessed" in body

    def test_not_ready_when_sign_off_blockers(self, html):
        """🔴 Not Ready triggered by sign_off_blockers or Not Yet Addressed domain."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "not_ready" in body or "Not Ready" in body
        assert "sign_off_blockers" in body or "blockers" in body

    def test_not_ready_when_not_yet_addressed_domain(self, html):
        """🔴 Not Ready also triggered by any 'Not Yet Addressed' domain."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "Not Yet Addressed" in body

    def test_needs_work_when_open_decisions_or_partial(self, html):
        """🟡 Needs Work triggered by open decisions or Partial domain."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "needs_work" in body or "Needs Work" in body
        assert "Partial" in body or "open" in body

    def test_ready_to_submit_label(self, html):
        """🟢 Ready to Submit label exists."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "Ready to Submit" in body or "ready" in body

    def test_readiness_no_extra_api_call(self, html):
        """_computeProposalReadiness does not make any API calls (no fetch/api call)."""
        body = _fn_body(html, "_computeProposalReadiness")
        assert "api(" not in body
        assert "fetch(" not in body

    def test_render_readiness_badge_shows_not_assessed(self, html):
        """Badge renders 'Not assessed' when level is not_assessed."""
        body = _fn_body(html, "_renderProposalReadinessBadge")
        assert "Not assessed" in body or "not_assessed" in body

    def test_render_readiness_badge_uses_green_for_ready(self, html):
        """Ready state uses green colour."""
        body = _fn_body(html, "_renderProposalReadinessBadge")
        assert "var(--green)" in body

    def test_render_readiness_badge_uses_yellow_for_needs_work(self, html):
        """Needs Work state uses yellow colour."""
        body = _fn_body(html, "_renderProposalReadinessBadge")
        assert "var(--yellow)" in body

    def test_render_readiness_badge_uses_red_for_not_ready(self, html):
        """Not Ready state uses red colour."""
        body = _fn_body(html, "_renderProposalReadinessBadge")
        assert "var(--red)" in body

    def test_doccard_calls_render_readiness_badge(self, html):
        assert "_renderProposalReadinessBadge(doc)" in html


# ═════════════════════════════════════════════════════════════════════════════
# H  Structural integrity
# ═════════════════════════════════════════════════════════════════════════════

class TestStructuralIntegrity:

    def test_file_utf8_decodable(self):
        HTML_PATH.read_text(encoding="utf-8")

    def test_no_script_tag_inside_template_literal(self, html):
        """No raw </script> inside a template literal string (regression guard)."""
        # Extract all template literal content
        tl_content = re.findall(r"`[^`]*`", html, re.DOTALL)
        for chunk in tl_content:
            assert "</script>" not in chunk.lower(), (
                "Found </script> inside a template literal — this breaks the HTML parser"
            )

    def test_all_sprint5_functions_defined(self, html):
        expected = [
            "_renderConflictBanner",
            "_renderProposalReviewPass",
            "_renderProposalCoverage",
            "_renderDecisionSummary",
            "_renderForwardGuidance",
            "_computeProposalReadiness",
            "_renderProposalReadinessBadge",
            "_renderSupplementalReviews",
        ]
        for fn in expected:
            assert _fn_exists(html, fn), f"function {fn}() not defined in index.html"

    def test_doccard_calls_all_six_new_renderers(self, html):
        for fn in [
            "_renderConflictBanner(doc)",
            "_renderProposalReadinessBadge(doc)",
            "_renderProposalReviewPass(doc)",
            "_renderProposalCoverage(doc)",
            "_renderDecisionSummary(doc)",
            "_renderForwardGuidance(doc)",
        ]:
            assert fn in html, f"docCard does not call {fn}"

    def test_supplemental_ids_key_in_generate_call(self, html):
        """The generate API call body contains supplemental_review_ids key."""
        assert "supplemental_review_ids" in html

    def test_no_undefined_references_to_sprint5_ids(self, html):
        """All new element IDs used in JS also appear in HTML template strings."""
        ids = ["propSupplementalRow", "propSupplementalCheckboxes", "propAnchorReviewPin"]
        for eid in ids:
            assert eid in html, f"Element id '{eid}' missing from index.html"


# ═════════════════════════════════════════════════════════════════════════════
# I  Sprint 4 regression — existing docCard renderers untouched
# ═════════════════════════════════════════════════════════════════════════════

class TestSprint4Regression:

    def test_exec_summary_section_still_in_doc_card(self, html):
        assert "exec_summary" in html
        assert "Executive Summary" in html

    def test_delivery_phases_section_still_present(self, html):
        assert "delivery_phases" in html
        assert "Delivery Phases" in html

    def test_risks_section_still_present(self, html):
        assert "doc.risks" in html or "risks.length" in html

    def test_assumptions_section_still_present(self, html):
        assert "doc.assumptions" in html or "assumptions.length" in html

    def test_acceptance_criteria_still_present(self, html):
        assert "acceptance_criteria" in html

    def test_raci_client_responsibilities_still_present(self, html):
        assert "client_responsibilities" in html

    def test_submit_create_proposal_still_calls_create_api(self, html):
        body = _fn_body(html, "submitCreateProposal")
        assert "/proposal'" in body or "/proposal`" in body or "proposal," in body

    def test_on_prop_version_change_still_loads_reviews(self, html):
        body = _fn_body(html, "onPropVersionChange")
        assert "hierarchy/versions" in body
        assert "reviews" in body

    def test_existing_sprint1_functions_still_present(self, html):
        for fn in ["viewDashboard", "viewReviews", "viewVersions",
                   "viewIntelligence", "viewPresales"]:
            assert _fn_exists(html, fn), f"{fn}() disappeared"

    def test_proposal_form_metadata_fields_still_present(self, html):
        for eid in ["propName", "propClient", "propBackend", "propNotes",
                    "propVersionSelect", "propReviewSelect"]:
            assert eid in html, f"Form element id='{eid}' missing"
