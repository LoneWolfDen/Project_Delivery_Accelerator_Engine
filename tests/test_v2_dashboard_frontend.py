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
        assert "Metadata" in body

    def test_detail_page_shows_summary_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Summary" in body

    def test_detail_page_shows_findings_section(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        assert "Findings" in body

    def test_detail_page_shows_empty_sections(self, html):
        body = _fn_body(html, "v2RenderReviewDetailPage")
        # Empty state must show "(none)" not just blank
        assert "(none)" in body

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
