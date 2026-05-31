"""Sprint 8 Regression Pack — Review → Decision → Proposal Strengthening.

Covers every change made in Sprint 8.  All tests are static-analysis of
index.html (UI-only sprint) except where noted with (unit).

Feature map
-----------
F1  renderReviewStrength      — Missing / Weak / Unresolved / Impact Areas
F2  renderDecisionPointsEngine — enriched decision cards (title/options/SME link)
F3  renderReviewProgression   — replaces "What Changed" diff block
F4  renderProposalReadiness   — Not Ready / Partially Ready / Ready
F5  _smeQuestionTypeTag       — Decision / Gap-fill / Trade-off type tags on SME Qs
F6  renderNextBestActions     — 3-5 executable actions from weaknesses + decisions
F7  renderProposalStrength    — Strong/Weak areas + Risk-to-sign-off in presales
F8  _enrichFeedbackWithMapping / _mapFeedbackToContext — map feedback to context

Section index
─────────────
A  CSS classes present
B  F1 – Review Strength Panel
C  F2 – Decision Points Engine
D  F3 – Review Progression (replaces What Changed)
E  F4 – Proposal Readiness Indicator
F  F5 – SME question type tags
G  F6 – Next Best Actions
H  F7 – Proposal Strength Summary
I  F8 – Feedback mapping
J  Wiring: functions called in the correct view functions
K  Backward-compat: old functionality still present
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

HTML_PATH = Path(__file__).parent.parent / "static" / "index.html"


@pytest.fixture(scope="module")
def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# A  CSS classes
# ─────────────────────────────────────────────────────────────────────────────

class TestCSSClasses:
    def test_rs_grid_defined(self, html):
        assert ".rs-grid" in html

    def test_rs_cell_defined(self, html):
        assert ".rs-cell{" in html or ".rs-cell " in html

    def test_rs_cell_header_defined(self, html):
        assert ".rs-cell-header" in html

    def test_rs_item_defined(self, html):
        assert ".rs-item" in html

    def test_pr_bar_defined(self, html):
        assert ".pr-bar{" in html or ".pr-bar " in html

    def test_pr_bar_states(self, html):
        assert ".pr-bar.not-ready" in html
        assert ".pr-bar.partial" in html
        assert ".pr-bar.ready" in html

    def test_nba_item_defined(self, html):
        assert ".nba-item{" in html or ".nba-item " in html

    def test_dp_card_defined(self, html):
        assert ".dp-card{" in html or ".dp-card " in html

    def test_prog_row_defined(self, html):
        assert ".prog-row{" in html or ".prog-row " in html

    def test_prop_strength_classes(self, html):
        assert ".prop-strength-area" in html
        assert ".prop-strength-strong" in html
        assert ".prop-strength-weak" in html

    def test_fb_map_tag_defined(self, html):
        assert ".fb-map-tag{" in html or ".fb-map-tag " in html


# ─────────────────────────────────────────────────────────────────────────────
# B  F1 – Review Strength Panel
# ─────────────────────────────────────────────────────────────────────────────

class TestF1ReviewStrength:
    def test_function_defined(self, html):
        assert "function renderReviewStrength(r)" in html

    def test_panel_id_emitted(self, html):
        assert "reviewStrengthPanel" in html

    def test_impact_map_defined(self, html):
        assert "const _IMPACT_MAP" in html

    def test_impact_map_has_architecture(self, html):
        assert "'Architecture'" in html or '"Architecture"' in html

    def test_impact_map_has_delivery(self, html):
        assert "'Delivery'" in html or '"Delivery"' in html

    def test_impact_map_has_cost(self, html):
        assert "'Cost'" in html or '"Cost"' in html

    def test_impact_map_has_operations(self, html):
        assert "'Operations'" in html or '"Operations"' in html

    def test_missing_section_label(self, html):
        # The panel emits 'Missing' as a section header
        assert "'Missing'" in html or '"Missing"' in html

    def test_weak_section_label(self, html):
        assert "'Weak'" in html or '"Weak"' in html

    def test_unresolved_section_label(self, html):
        assert "'Unresolved'" in html or '"Unresolved"' in html

    def test_impact_areas_header(self, html):
        assert "Impact Areas" in html

    def test_rs_grid_used_in_function(self, html):
        # rs-grid class must appear inside the renderReviewStrength return value
        # (function body may span > 2000 chars; search up to 3000)
        idx = html.index("function renderReviewStrength")
        assert "rs-grid" in html[idx:idx + 3000]

    def test_function_called_in_view_review_detail(self, html):
        assert "renderReviewStrength(r)" in html

    def test_returns_empty_when_no_data(self, html):
        # Guard clause: if no missing/weak/unresolved items, return ''
        # The guard may appear as  return '';  or  return ''  or  return ``
        idx = html.index("function renderReviewStrength")
        fn_body = html[idx: idx + 1600]
        assert "return ''" in fn_body or "return ``" in fn_body


# ─────────────────────────────────────────────────────────────────────────────
# C  F2 – Decision Points Engine
# ─────────────────────────────────────────────────────────────────────────────

class TestF2DecisionEngine:
    def test_function_defined(self, html):
        assert "function renderDecisionPointsEngine(r)" in html

    def test_panel_id_emitted(self, html):
        assert "decisionEnginePanel" in html

    def test_infer_title_defined(self, html):
        assert "function _inferDecisionTitle" in html

    def test_infer_options_defined(self, html):
        assert "function _inferOptions" in html

    def test_cloud_strategy_title(self, html):
        assert "Cloud Strategy" in html

    def test_options_cloud(self, html):
        # _inferOptions emits AWS / Azure / GCP for cloud
        idx = html.index("function _inferOptions")
        fn_body = html[idx: idx + 500]
        assert "AWS" in fn_body

    def test_dp_card_class_used(self, html):
        assert "dp-card" in html

    def test_dp_title_class_used(self, html):
        assert "dp-title" in html

    def test_dp_desc_class_used(self, html):
        assert "dp-desc" in html

    def test_sme_link_hint_present(self, html):
        assert "Ask SME Questions" in html

    def test_status_badge_open(self, html):
        # Open status must show a red tag
        idx = html.index("function renderDecisionPointsEngine")
        fn_body = html[idx: idx + 1500]
        assert "Open" in fn_body

    def test_status_badge_partial(self, html):
        idx = html.index("function renderDecisionPointsEngine")
        fn_body = html[idx: idx + 1500]
        assert "Partially Clarified" in fn_body

    def test_function_called_in_view_review_detail(self, html):
        assert "renderDecisionPointsEngine(r)" in html


# ─────────────────────────────────────────────────────────────────────────────
# D  F3 – Review Progression (replaces What Changed)
# ─────────────────────────────────────────────────────────────────────────────

class TestF3ReviewProgression:
    def test_function_defined(self, html):
        assert "function renderReviewProgression(diff, prevReviewId)" in html

    def test_panel_id_emitted(self, html):
        assert "reviewProgressionPanel" in html

    def test_resolved_bucket_label(self, html):
        assert "Resolved" in html

    def test_new_findings_bucket_label(self, html):
        assert "New Findings" in html

    def test_still_open_bucket_label(self, html):
        assert "Still Open" in html

    def test_unchanged_bucket_label(self, html):
        assert "Unchanged" in html

    def test_four_counter_cells_emitted(self, html):
        idx = html.index("function renderReviewProgression")
        fn_body = html[idx: idx + 3000]
        # Counter cells for Resolved, New Findings, Still Open, Unchanged
        assert fn_body.count("font-size:18px") >= 4

    def test_what_changed_removed_from_view(self, html):
        # The old "What Changed from" heading must no longer exist in the
        # viewReviewDetail section (it still exists nowhere, or only in comments)
        assert "What Changed from" not in html

    def test_no_diff_diff_section_function_inline(self, html):
        # The old inline _diffSection function is gone
        assert "function _diffSection(" not in html

    def test_function_called_with_diff_data(self, html):
        assert "renderReviewProgression(diff, r.previous_review_id)" in html

    def test_prog_row_resolved_class(self, html):
        assert "prog-resolved" in html

    def test_prog_row_new_class(self, html):
        assert "prog-new" in html

    def test_prog_row_still_class(self, html):
        assert "prog-still" in html


# ─────────────────────────────────────────────────────────────────────────────
# E  F4 – Proposal Readiness Indicator
# ─────────────────────────────────────────────────────────────────────────────

class TestF4ProposalReadiness:
    def test_function_defined(self, html):
        assert "function renderProposalReadiness(r)" in html

    def test_panel_id_emitted(self, html):
        assert "proposalReadinessPanel" in html

    def test_not_ready_status(self, html):
        assert "Not Ready" in html

    def test_partially_ready_status(self, html):
        assert "Partially Ready" in html

    def test_ready_status(self, html):
        assert "'Ready'" in html or '"Ready"' in html or "status = 'Ready'" in html

    def test_pr_bar_class_used(self, html):
        idx = html.index("function renderProposalReadiness")
        fn_body = html[idx: idx + 3500]
        assert "pr-bar" in fn_body

    def test_blockers_section(self, html):
        idx = html.index("function renderProposalReadiness")
        fn_body = html[idx: idx + 3500]
        assert "Why" in fn_body or "blockers" in fn_body

    def test_next_steps_section(self, html):
        idx = html.index("function renderProposalReadiness")
        fn_body = html[idx: idx + 3500]
        assert "Next Steps" in fn_body

    def test_next_steps_max_5(self, html):
        idx = html.index("function renderProposalReadiness")
        fn_body = html[idx: idx + 2500]
        assert "slice(0,5)" in fn_body

    def test_no_numerical_score(self, html):
        idx = html.index("function renderProposalReadiness")
        fn_body = html[idx: idx + 2500]
        # Must not reference scoring logic (compute_completeness_score etc.)
        assert "compute_completeness_score" not in fn_body
        assert "completeness_score" not in fn_body

    def test_function_called_in_view_review_detail(self, html):
        assert "renderProposalReadiness(r)" in html


# ─────────────────────────────────────────────────────────────────────────────
# F  F5 – SME question type tags
# ─────────────────────────────────────────────────────────────────────────────

class TestF5SMEQuestionTypes:
    def test_function_defined(self, html):
        assert "function _smeQuestionTypeTag(qText)" in html

    def test_decision_type_tag(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 500]
        assert "Decision" in fn_body

    def test_trade_off_type_tag(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 500]
        assert "Trade-off" in fn_body or "Trade-Off" in fn_body

    def test_gap_fill_type_tag(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 700]
        assert "Gap-fill" in fn_body or "Gap-Fill" in fn_body or "isGapFill" in fn_body

    def test_called_in_dd_group(self, html):
        # originLine in ddGroup() calls _smeQuestionTypeTag
        assert "_smeQuestionTypeTag(qText)" in html

    def test_fb_map_tag_class_used_in_output(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 700]
        assert "fb-map-tag" in fn_body

    def test_returns_empty_string_default(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 700]
        assert "return '';" in fn_body or "return ''" in fn_body or "return ``" in fn_body

    def test_emoji_icons_present(self, html):
        idx = html.index("function _smeQuestionTypeTag")
        fn_body = html[idx: idx + 700]
        # Decision = 🎯
        assert "🎯" in fn_body


# ─────────────────────────────────────────────────────────────────────────────
# G  F6 – Next Best Actions
# ─────────────────────────────────────────────────────────────────────────────

class TestF6NextBestActions:
    def test_function_defined(self, html):
        assert "function renderNextBestActions(r)" in html

    def test_panel_id_emitted(self, html):
        assert "nextBestActionsPanel" in html

    def test_max_5_actions(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "slice(0,5)" in fn_body

    def test_actions_from_decisions(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "openD" in fn_body or "openDecisions" in fn_body or "decision" in fn_body.lower()

    def test_actions_from_weaknesses(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "openW" in fn_body or "openWeaknesses" in fn_body or "weakness" in fn_body.lower()

    def test_from_label_per_action(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "From:" in fn_body

    def test_nba_item_class_used(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "nba-item" in fn_body

    def test_nba_num_class_used(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "nba-num" in fn_body

    def test_returns_empty_when_no_actions(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "return '';" in fn_body or "return ``" in fn_body

    def test_function_called_in_view_review_detail(self, html):
        assert "renderNextBestActions(r)" in html

    def test_missing_category_actions(self, html):
        idx = html.index("function renderNextBestActions")
        fn_body = html[idx: idx + 2000]
        assert "miss" in fn_body  # iterates missing categories for actions


# ─────────────────────────────────────────────────────────────────────────────
# H  F7 – Proposal Strength Summary
# ─────────────────────────────────────────────────────────────────────────────

class TestF7ProposalStrength:
    def test_function_defined(self, html):
        assert "function renderProposalStrength(review)" in html

    def test_panel_id_emitted(self, html):
        assert "proposalStrengthPanel" in html

    def test_strong_areas_label(self, html):
        assert "Strong Areas" in html

    def test_weak_areas_label(self, html):
        assert "Weak Areas" in html

    def test_risk_to_signoff_label(self, html):
        assert "Risk to Sign-off" in html or "Risk-to-sign-off" in html or "Risk to sign-off" in html

    def test_three_risk_levels(self, html):
        idx = html.index("function renderProposalStrength")
        fn_body = html[idx: idx + 2000]
        assert "'High'" in fn_body or '"High"' in fn_body
        assert "'Medium'" in fn_body or '"Medium"' in fn_body
        assert "'Low'" in fn_body or '"Low"' in fn_body

    def test_prop_strength_strong_class(self, html):
        idx = html.index("function renderProposalStrength")
        fn_body = html[idx: idx + 2000]
        assert "prop-strength-strong" in fn_body

    def test_prop_strength_weak_class(self, html):
        idx = html.index("function renderProposalStrength")
        fn_body = html[idx: idx + 2000]
        assert "prop-strength-weak" in fn_body

    def test_returns_empty_for_no_categories(self, html):
        idx = html.index("function renderProposalStrength")
        fn_body = html[idx: idx + 2000]
        assert "return '';" in fn_body or "return ``" in fn_body

    def test_called_in_view_presales(self, html):
        assert "renderProposalStrength(activeReview)" in html

    def test_proposal_strength_card_in_presales_return(self, html):
        assert "proposalStrengthCard" in html

    def test_card_included_in_presales_html_return(self, html):
        # The final return statement in viewPresales must include proposalStrengthCard
        idx = html.rindex("proposalStrengthCard")   # last occurrence = return line
        assert "return " in html[max(0, idx-50): idx+200] or "+" in html[idx: idx+50]


# ─────────────────────────────────────────────────────────────────────────────
# I  F8 – Feedback mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestF8FeedbackMapping:
    def test_map_function_defined(self, html):
        assert "function _mapFeedbackToContext(feedbackItem, review)" in html

    def test_enrich_function_defined(self, html):
        assert "function _enrichFeedbackWithMapping(feedbackList, review)" in html

    def test_map_tries_weakness_match(self, html):
        idx = html.index("function _mapFeedbackToContext")
        fn_body = html[idx: idx + 800]
        assert "weaknesses" in fn_body

    def test_map_tries_decision_match(self, html):
        idx = html.index("function _mapFeedbackToContext")
        fn_body = html[idx: idx + 800]
        assert "decision" in fn_body.lower()

    def test_map_returns_type_and_text(self, html):
        idx = html.index("function _mapFeedbackToContext")
        fn_body = html[idx: idx + 800]
        assert "{type:" in fn_body or "type:" in fn_body

    def test_enrich_sets_mapped_context_key(self, html):
        idx = html.index("function _enrichFeedbackWithMapping")
        fn_body = html[idx: idx + 400]
        assert "_mappedContext" in fn_body

    def test_enrich_called_before_feedback_render(self, html):
        assert "const enrichedFeedback = _enrichFeedbackWithMapping(feedbackList, activeReview)" in html

    def test_fb_map_tag_rendered_when_mapped(self, html):
        # The feedback row renders fb-map-tag when _mappedContext is truthy
        assert "fb-map-tag" in html
        assert "_mappedContext" in html

    def test_no_duplicate_entry_creation(self, html):
        # _enrichFeedbackWithMapping must NOT push new items into weaknesses/decisions
        idx = html.index("function _enrichFeedbackWithMapping")
        fn_body = html[idx: idx + 400]
        assert "push(" not in fn_body  # no mutation of existing arrays

    def test_map_returns_null_on_no_match(self, html):
        idx = html.index("function _mapFeedbackToContext")
        fn_body = html[idx: idx + 800]
        assert "return null" in fn_body


# ─────────────────────────────────────────────────────────────────────────────
# J  Wiring: functions called in the correct view functions
# ─────────────────────────────────────────────────────────────────────────────

class TestWiring:
    def test_review_strength_called_after_decision_points(self, html):
        # Both calls must exist in viewReviewDetail; renderDecisionPointsEngine
        # is called before renderReviewStrength
        idx_dp  = html.index("renderDecisionPointsEngine(r)")
        idx_rs  = html.index("renderReviewStrength(r)")
        assert idx_dp < idx_rs

    def test_proposal_readiness_called_after_strength(self, html):
        idx_rs = html.index("renderReviewStrength(r)")
        idx_pr = html.index("renderProposalReadiness(r)")
        assert idx_rs < idx_pr

    def test_next_best_actions_called_after_readiness(self, html):
        idx_pr  = html.index("renderProposalReadiness(r)")
        idx_nba = html.index("renderNextBestActions(r)")
        assert idx_pr < idx_nba

    def test_review_progression_called_with_diff_and_prev(self, html):
        assert "renderReviewProgression(diff, r.previous_review_id)" in html

    def test_progression_inside_previous_review_block(self, html):
        # Must be guarded by r.previous_review_id check
        prev_block = re.search(
            r'if\(r\.previous_review_id\).*?renderReviewProgression',
            html, re.DOTALL
        )
        assert prev_block is not None

    def test_proposal_strength_called_with_active_review(self, html):
        assert "renderProposalStrength(activeReview)" in html

    def test_sme_type_tag_called_in_dd_group(self, html):
        # Must appear inside the ddGroup function, wired into originLine
        idx_dd = html.index("function ddGroup(grp)")
        fn_body = html[idx_dd: idx_dd + 3000]
        assert "_smeQuestionTypeTag(qText)" in fn_body

    def test_enrich_feedback_uses_active_review(self, html):
        assert "activeReview" in html[
            html.index("_enrichFeedbackWithMapping"):
            html.index("_enrichFeedbackWithMapping") + 100
        ]


# ─────────────────────────────────────────────────────────────────────────────
# K  Backward-compat: old functionality still present
# ─────────────────────────────────────────────────────────────────────────────

class TestBackwardCompat:
    def test_weaknesses_section_still_present(self, html):
        assert "renderWeaknesses" in html or "S4-01: Weaknesses" in html or \
               "Weaknesses" in html and "weakness" in html

    def test_weakness_status_update_still_works(self, html):
        assert "updateWeaknessStatus" in html

    def test_decision_status_update_still_works(self, html):
        assert "updateDecisionStatus" in html

    def test_coverage_assessment_still_rendered(self, html):
        assert "renderCoverageAssessment" in html

    def test_tighten_sme_button_still_present(self, html):
        assert "Tighten with SME Questions" in html

    def test_diff_css_classes_still_defined(self, html):
        # diff-added / diff-removed used in renderReviewProgression
        assert ".diff-added" in html
        assert ".diff-removed" in html

    def test_missing_areas_section_still_present(self, html):
        assert "Missing Areas" in html

    def test_run_review_button_still_present(self, html):
        assert "runReview()" in html

    def test_sme_questions_workflow_still_present(self, html):
        assert "runDeepDive()" in html

    def test_presales_view_still_has_proposal_versions(self, html):
        assert "versionsCard" in html

    def test_feedback_log_card_still_rendered(self, html):
        assert "fbCard" in html or "Feedback Log" in html

    def test_sprint8_css_before_loading_bar(self, html):
        # New CSS must come before .loading-bar in source order
        assert html.index(".rs-grid") < html.index(".loading-bar")
