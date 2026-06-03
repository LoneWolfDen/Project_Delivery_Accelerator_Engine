"""Static analysis tests for static/v2/dashboard_v2.html.

Covers all fixes introduced in the V2 bug-fix PR:
  - Review Tab: error display, SME questions UI, multi-persona preview,
    Full Details page, Review History sections
  - Dashboard Tab: tile navigation, Proposal & Outcomes section
  - New tabs: Ingest, Settings, Admin
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

V2_HTML_PATH = Path(__file__).parent.parent / "static" / "v2" / "dashboard_v2.html"


@pytest.fixture(scope="module")
def html():
    return V2_HTML_PATH.read_text(encoding="utf-8")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fn_exists(html: str, name: str) -> bool:
    return bool(re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(", html
    ))


def _fn_body(html: str, name: str) -> str:
    m = re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{([\s\S]+?)"
        rf"(?=\n(?:async\s+)?function\s|\Z)",
        html,
    )
    assert m, f"function {name}() not found in dashboard_v2.html"
    return m.group(1)


# ── Basic file health ─────────────────────────────────────────────────────────

class TestFileHealth:

    def test_utf8_decodable(self):
        V2_HTML_PATH.read_text(encoding="utf-8")

    def test_no_script_tag_inside_template_literal(self, html):
        parts = re.split(r"(?<!\\)`", html)
        for i, part in enumerate(parts):
            if i % 2 == 1:
                assert not re.search(r"<script[\s>]", part, re.IGNORECASE), (
                    "<script> tag found inside a template literal in dashboard_v2.html"
                )

    def test_no_close_script_in_template_literal(self, html):
        parts = re.split(r"(?<!\\)`", html)
        for i, part in enumerate(parts):
            if i % 2 == 1:
                assert "</script>" not in part.lower(), (
                    "</script> found inside a template literal in dashboard_v2.html"
                )

    def test_script_tags_balanced(self, html):
        opens = len(re.findall(r"<script[>\s]", html, re.IGNORECASE))
        closes = len(re.findall(r"</script\s*>", html, re.IGNORECASE))
        assert opens == closes, f"Unbalanced <script> tags: {opens} opens, {closes} closes"


# ── Tab navigation ────────────────────────────────────────────────────────────

class TestTabNavigation:

    def test_tabs_array_contains_all_six_tabs(self, html):
        m = re.search(r"const\s+TABS\s*=\s*\[([^\]]+)\]", html)
        assert m, "TABS array not found"
        tabs_src = m.group(1)
        for tab in ["dashboard", "versions", "reviews", "ingest", "settings", "admin"]:
            assert tab in tabs_src, f"Tab '{tab}' missing from TABS array"

    def test_views_dispatch_has_all_tabs(self, html):
        m = re.search(r"const\s+views\s*=\s*\{([^}]+)\}", html)
        assert m, "views dispatch object not found"
        table = m.group(1)
        for tab in ["dashboard", "versions", "reviews", "ingest", "settings", "admin"]:
            assert tab in table, f"Tab '{tab}' missing from views dispatch"

    def test_view_functions_all_defined(self, html):
        for fn in ["viewDashboard", "viewVersions", "viewReviews",
                   "viewIngest", "viewSettings", "viewAdmin"]:
            assert _fn_exists(html, fn), f"{fn}() not defined in dashboard_v2.html"


# ── Dashboard: tile navigation ────────────────────────────────────────────────

class TestDashboardTileNavigation:

    def test_versions_tile_navigates_to_versions(self, html):
        assert "switchTab('versions')" in html

    def test_reviews_tile_navigates_to_reviews(self, html):
        assert "switchTab('reviews')" in html

    def test_ingest_tile_navigates_to_ingest(self, html):
        assert "switchTab('ingest')" in html

    def test_stat_tiles_have_onclick(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "onclick=\"switchTab('versions')\"" in body or "onclick=\"switchTab('reviews')\"" in body

    def test_insight_tiles_navigate_to_reviews(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "switchTab('reviews')" in body


# ── Dashboard: Proposal & Outcomes section ────────────────────────────────────

class TestDashboardProposalOutcomes:

    def test_proposal_outcomes_section_exists(self, html):
        assert "Proposal" in html and "Outcomes" in html

    def test_proposal_section_heading_in_dashboard(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "Proposal" in body

    def test_v2_load_proposal_summary_function_defined(self, html):
        assert _fn_exists(html, "v2LoadProposalSummary")

    def test_proposal_summary_loaded_after_render(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "v2LoadProposalSummary" in body

    def test_proposal_view_reviews_button(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "View Reviews" in body

    def test_proposal_manage_artefacts_button(self, html):
        body = _fn_body(html, "viewDashboard")
        assert "Manage Artefacts" in body or "Artefacts" in body


# ── Review Tab: Run Persona Review error messages ─────────────────────────────

class TestReviewRunErrorDisplay:

    def test_run_button_has_id(self, html):
        assert 'id="v2RunReviewBtn"' in html

    def test_error_shown_without_render(self, html):
        body = _fn_body(html, "v2RunReview")
        # On error, must show error in el without calling render()
        # There should be only one render() call (on success path, after if(r.error) block)
        assert "r.error" in body
        # Error path must NOT call render() — check that render() only appears after the error return
        lines = body.split("\n")
        error_line = next((i for i, l in enumerate(lines) if "r.error" in l), -1)
        render_lines = [i for i, l in enumerate(lines) if "render()" in l]
        # All render() calls must be after the error block
        assert all(r > error_line for r in render_lines), \
            "render() appears to be called inside or before the error block"

    def test_error_display_uses_error_styling(self, html):
        body = _fn_body(html, "v2RunReview")
        assert "var(--red)" in body or "color:var(--red)" in body

    def test_run_button_referenced_by_id(self, html):
        body = _fn_body(html, "v2RunReview")
        assert "getElementById('v2RunReviewBtn')" in body or 'getElementById("v2RunReviewBtn")' in body


# ── Review Tab: SME Questions UI ──────────────────────────────────────────────

class TestSMEQuestionsUI:

    def test_select_all_button_present(self, html):
        assert "Select All" in html

    def test_unselect_all_button_present(self, html):
        assert "Unselect All" in html

    def test_expand_all_button_present(self, html):
        assert "Expand All" in html

    def test_collapse_all_button_present(self, html):
        assert "Collapse All" in html

    def test_v2_dd_select_all_function_defined(self, html):
        assert _fn_exists(html, "v2DdSelectAll")

    def test_v2_dd_expand_all_function_defined(self, html):
        assert _fn_exists(html, "v2DdExpandAll")

    def test_select_all_sets_checked_true(self, html):
        body = _fn_body(html, "v2DdSelectAll")
        assert "checked" in body

    def test_expand_all_sets_open(self, html):
        body = _fn_body(html, "v2DdExpandAll")
        assert "open" in body

    def test_deep_dive_result_buttons_call_helpers(self, html):
        body = _fn_body(html, "v2RunDeepDive")
        assert "v2DdSelectAll" in body
        assert "v2DdExpandAll" in body


# ── Review Tab: Role Persona Prompt (all selected personas) ──────────────────

class TestRolePersonaPrompt:

    def test_update_all_baselines_function_defined(self, html):
        assert _fn_exists(html, "v2UpdateAllBaselinePreviews")

    def test_role_check_calls_all_previews(self, html):
        body = _fn_body(html, "v2OnRoleCheck")
        assert "v2UpdateAllBaselinePreviews" in body

    def test_all_previews_shows_multiple_roles(self, html):
        body = _fn_body(html, "v2UpdateAllBaselinePreviews")
        # Must iterate over all checked roles, not just first
        assert "checked" in body
        assert "map" in body or "forEach" in body or "for" in body

    def test_previews_joined_with_separator(self, html):
        body = _fn_body(html, "v2UpdateAllBaselinePreviews")
        # Must join multiple previews
        assert "join" in body or "---" in body or "+=" in body


# ── Review Tab: Full Details page ─────────────────────────────────────────────

class TestReviewFullDetails:

    def test_v2_render_review_detail_page_defined(self, html):
        assert _fn_exists(html, "v2RenderReviewDetailPage")

    def test_view_reviews_checks_detail_state(self, html):
        body = _fn_body(html, "viewReviews")
        assert "_v2ReviewDetail" in body
        assert "v2RenderReviewDetailPage" in body

    def test_detail_page_has_back_button(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Back" in body
        assert "_v2ReviewDetail=null" in body

    def test_detail_page_fetches_review(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "hierarchy/reviews" in body

    def test_detail_page_shows_metadata_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        # Metadata is shown inline in the header card (version, phase, persona, ai_backend)
        assert "version_id" in body or "phase_id" in body or "ai_backend" in body

    def test_detail_page_shows_summary_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Summary" in body

    def test_detail_page_shows_findings_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Findings" in body

    def test_detail_page_shows_empty_sections(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        # Empty included_files shows a clear message
        assert "No file information recorded" in body or "No artefacts recorded" in body

    def test_full_details_button_calls_view_detail(self, html):
        assert "v2ViewReviewDetail" in html

    def test_view_review_detail_sets_state(self, html):
        body = _fn_body(html, "v2ViewReviewDetail")
        assert "_v2ReviewDetail" in body
        assert "render()" in body


# ── Ingest Tab ────────────────────────────────────────────────────────────────

class TestIngestTab:

    def test_view_ingest_defined(self, html):
        assert _fn_exists(html, "viewIngest")

    def test_artifact_categories_defined(self, html):
        assert "ARTIFACT_CATEGORIES" in html

    def test_category_meta_schema_defined(self, html):
        assert "CATEGORY_META_SCHEMA" in html

    def test_upload_artifact_function_defined(self, html):
        assert _fn_exists(html, "doUploadArtifact")

    def test_paste_artifact_function_defined(self, html):
        assert _fn_exists(html, "doPasteArtifact")

    def test_build_intelligence_function_defined(self, html):
        assert _fn_exists(html, "buildContext")

    def test_ingest_shows_artifact_registry(self, html):
        body = _fn_body(html, "viewIngest")
        assert "Artefact Registry" in body or "Registry" in body

    def test_ingest_shows_add_artefact_card(self, html):
        body = _fn_body(html, "viewIngest")
        assert "Add Artefact" in body or "upload" in body.lower()

    def test_toggle_artifact_function_defined(self, html):
        assert _fn_exists(html, "toggleArtifact")

    def test_process_artifact_function_defined(self, html):
        assert _fn_exists(html, "processArtifact")


# ── Settings Tab ──────────────────────────────────────────────────────────────

class TestSettingsTab:

    def test_view_settings_defined(self, html):
        assert _fn_exists(html, "viewSettings")

    def test_settings_has_create_project_card(self, html):
        body = _fn_body(html, "viewSettings")
        assert "Create New Project" in body or "newName" in body

    def test_settings_has_all_projects_list(self, html):
        body = _fn_body(html, "viewSettings")
        assert "All Projects" in body or "allProjects" in body

    def test_settings_has_ai_backends_card(self, html):
        body = _fn_body(html, "viewSettings")
        assert "AI Backend" in body or "backends" in body

    def test_archive_project_function_defined(self, html):
        assert _fn_exists(html, "archiveProject")

    def test_delete_project_function_defined(self, html):
        assert _fn_exists(html, "deleteProject")


# ── Admin Tab ─────────────────────────────────────────────────────────────────

class TestAdminTab:

    def test_view_admin_defined(self, html):
        assert _fn_exists(html, "viewAdmin")

    def test_admin_has_system_health_card(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "System Health" in body

    def test_admin_has_config_card(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "Configuration" in body or "cfgMaxP" in body

    def test_admin_has_persona_prompts_card(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "Persona" in body and "Prompt" in body

    def test_save_admin_config_function_defined(self, html):
        assert _fn_exists(html, "saveAdminConfig")

    def test_save_persona_prompts_function_defined(self, html):
        assert _fn_exists(html, "savePersonaPrompts")

    def test_reset_persona_prompt_function_defined(self, html):
        assert _fn_exists(html, "resetPersonaPrompt")

    def test_admin_has_lifecycle_card(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "Lifecycle" in body or "lifecycle" in body

    def test_admin_fetches_config(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "/api/admin/config" in body

    def test_admin_fetches_health(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "/api/admin/health" in body

    def test_admin_persona_prompts_show_all_groups(self, html):
        body = _fn_body(html, "viewAdmin")
        assert "group_id" in body or "seenGroups" in body



# ── Admin Tab: Persona Base Prompts fix ───────────────────────────────────────

class TestAdminPersonaBasePrompts:
    """Issue fix: Persona Base Prompts not populating in Admin tab.

    Root cause: nested template literals + silent catch swallowed the card.
    Fix: string concatenation build, &#10; encoding of newlines, visible error on failure.
    """

    def test_persona_prompts_built_with_string_concat(self, html):
        """viewAdmin uses += string concat for groupRows, not template literal map."""
        body = _fn_body(html, "viewAdmin")
        # String concat pattern (groupRows += '...') rather than .map(...).join('')
        assert "groupRows+=" in body or "groupRows +=" in body

    def test_persona_prompts_encodes_newlines_in_attribute(self, html):
        """data-yaml-default encodes newlines as &#10; to survive HTML attribute parsing."""
        body = _fn_body(html, "viewAdmin")
        assert "&#10;" in body

    def test_persona_prompts_catch_logs_to_console(self, html):
        """catch block logs to console.error instead of silently discarding."""
        body = _fn_body(html, "viewAdmin")
        assert "console.error" in body

    def test_persona_prompts_catch_shows_error_card(self, html):
        """catch block renders a visible error card rather than empty string."""
        body = _fn_body(html, "viewAdmin")
        # Error card has red text — not just personaPromptsCard=''
        assert "var(--red)" in body or "color:var(--red)" in body

    def test_persona_prompts_validates_roles_returned(self, html):
        """viewAdmin checks that allRoles is non-empty before building the card."""
        body = _fn_body(html, "viewAdmin")
        assert "allRoles.length" in body or "!allRoles.length" in body

    def test_save_persona_prompts_decodes_attribute(self, html):
        """savePersonaPrompts decodes &#10; back to newlines before comparing."""
        body = _fn_body(html, "savePersonaPrompts")
        assert "&#10;" in body
        assert "replace" in body

    def test_reset_persona_prompt_decodes_attribute(self, html):
        """resetPersonaPrompt decodes &#10; back to newlines when restoring."""
        body = _fn_body(html, "resetPersonaPrompt")
        assert "&#10;" in body
        assert "replace" in body

    def test_persona_prompts_uses_escHtml_for_group_name(self, html):
        """Group name is HTML-escaped before insertion."""
        body = _fn_body(html, "viewAdmin")
        assert "escHtml(g.group_name)" in body

    def test_persona_prompts_uses_escHtml_for_prompt_template(self, html):
        """prompt_template is HTML-escaped (safeDefault / safeVal)."""
        body = _fn_body(html, "viewAdmin")
        assert "safeDefault" in body or "escHtml(g.prompt_template)" in body


# ── Review Full Details: V1 feature parity ────────────────────────────────────

class TestReviewFullDetailsV1Parity:
    """Verify full V1 viewReviewDetail feature parity in v2RenderReviewDetailPage."""

    def test_coverage_assessment_function_defined(self, html):
        assert _fn_exists(html, "renderCoverageAssessment")

    def test_review_strength_function_defined(self, html):
        assert _fn_exists(html, "renderReviewStrength")

    def test_decision_points_engine_function_defined(self, html):
        assert _fn_exists(html, "renderDecisionPointsEngine")

    def test_review_progression_function_defined(self, html):
        assert _fn_exists(html, "renderReviewProgression")

    def test_proposal_readiness_function_defined(self, html):
        assert _fn_exists(html, "renderProposalReadiness")

    def test_next_best_actions_function_defined(self, html):
        assert _fn_exists(html, "renderNextBestActions")

    def test_coverage_baseline_constant_defined(self, html):
        assert "COVERAGE_BASELINE" in html

    def test_coverage_persona_constant_defined(self, html):
        assert "COVERAGE_PERSONA" in html

    def test_impact_map_constant_defined(self, html):
        assert "_IMPACT_MAP" in html

    def test_infer_decision_title_helper_defined(self, html):
        assert _fn_exists(html, "_inferDecisionTitle")

    def test_infer_options_helper_defined(self, html):
        assert _fn_exists(html, "_inferOptions")

    def test_update_weakness_status_defined(self, html):
        assert _fn_exists(html, "updateWeaknessStatus")

    def test_update_decision_status_defined(self, html):
        assert _fn_exists(html, "updateDecisionStatus")

    def test_detail_calls_coverage_assessment(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderCoverageAssessment(r)" in body

    def test_detail_calls_review_strength(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderReviewStrength(r)" in body

    def test_detail_calls_decision_engine(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderDecisionPointsEngine(r)" in body

    def test_detail_calls_proposal_readiness(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderProposalReadiness(r)" in body

    def test_detail_calls_next_best_actions(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderNextBestActions(r)" in body

    def test_detail_calls_review_progression(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "renderReviewProgression" in body

    def test_detail_shows_decision_readiness_badge(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "v2detailReadinessBadge" in body

    def test_detail_loads_readiness_async(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "/readiness" in body

    def test_detail_shows_files_included(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "included_files" in body

    def test_detail_shows_weaknesses_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "weaknesses" in body
        assert "Weaknesses" in body

    def test_detail_weakness_has_status_dropdown(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "updateWeaknessStatus" in body
        assert "open" in body and "addressed" in body and "validated" in body and "rejected" in body

    def test_detail_weakness_has_note_textarea(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "user_note" in body

    def test_detail_shows_missing_areas(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "missing_categories" in body

    def test_detail_shows_decision_points_raw(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "decision_points" in body
        assert "updateDecisionStatus" in body

    def test_detail_shows_prompt_used_collapsible(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "prompt_used" in body

    def test_detail_shows_custom_prompt_collapsible(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "custom_prompt" in body

    def test_detail_shows_prompt_composition(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "prompt_builder_state" in body
        assert "injected_questions" in body

    def test_detail_shows_ai_metadata(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "ai_metadata" in body
        assert "tokens_used" in body

    def test_detail_has_tighten_button(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Tighten" in body

    def test_detail_has_back_button_top_and_bottom(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert body.count("← Back") >= 2

    def test_detail_fetches_review_diff_for_progression(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "previous_review_id" in body
        assert "/diff" in body

    def test_detail_shows_customised_baseline_badge(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Customised" in body and "Baseline" in body

    def test_coverage_assessment_uses_coverage_baseline(self, html):
        body = _fn_body(html, "renderCoverageAssessment")
        assert "COVERAGE_BASELINE" in body

    def test_coverage_assessment_uses_persona_dims(self, html):
        body = _fn_body(html, "renderCoverageAssessment")
        assert "COVERAGE_PERSONA" in body

    def test_coverage_assessment_renders_bar(self, html):
        body = _fn_body(html, "renderCoverageAssessment")
        assert "coverage-bar-outer" in body

    def test_coverage_assessment_renders_pills(self, html):
        body = _fn_body(html, "renderCoverageAssessment")
        assert "coverage-pill" in body

    def test_review_strength_uses_impact_map(self, html):
        body = _fn_body(html, "renderReviewStrength")
        assert "_IMPACT_MAP" in body

    def test_review_strength_shows_missing_weak_unresolved(self, html):
        body = _fn_body(html, "renderReviewStrength")
        assert "Missing" in body
        assert "Weak" in body
        assert "Unresolved" in body

    def test_proposal_readiness_has_three_levels(self, html):
        body = _fn_body(html, "renderProposalReadiness")
        assert "Not Ready" in body
        assert "Partially Ready" in body
        assert "Ready" in body

    def test_review_progression_shows_four_tiles(self, html):
        body = _fn_body(html, "renderReviewProgression")
        assert "Resolved" in body
        assert "New Findings" in body
        assert "Still Open" in body
        assert "Unchanged" in body

    def test_decision_engine_infers_title(self, html):
        body = _fn_body(html, "renderDecisionPointsEngine")
        assert "_inferDecisionTitle" in body

    def test_decision_engine_infers_options(self, html):
        body = _fn_body(html, "renderDecisionPointsEngine")
        assert "_inferOptions" in body

    # CSS classes added for full-detail panels
    def test_css_coverage_bar_defined(self, html):
        assert ".coverage-bar-outer" in html

    def test_css_coverage_pills_defined(self, html):
        assert ".coverage-pill" in html

    def test_css_rs_grid_defined(self, html):
        assert ".rs-grid" in html

    def test_css_pr_bar_defined(self, html):
        assert ".pr-bar" in html

    def test_css_nba_item_defined(self, html):
        assert ".nba-item" in html

    def test_css_dp_card_defined(self, html):
        assert ".dp-card" in html

    def test_css_prog_row_defined(self, html):
        assert ".prog-row" in html

    def test_css_prop_strength_area_defined(self, html):
        assert ".prop-strength-area" in html

    def test_css_prompt_box_defined(self, html):
        assert ".prompt-box" in html
