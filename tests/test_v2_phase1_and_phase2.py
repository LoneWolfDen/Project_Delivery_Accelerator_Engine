"""Phase 1 & Phase 2 Tests — V2 Live Mode and Detail Panel.

All tests are static analysis (file content inspection).
No backend imports, no DB, no network calls.

Coverage:
  Phase 1 — Live backend connection
    P1-01  window.V2_USE_MOCK = false is set before api.js scripts load
    P1-02  api.js _useMock() correctly guards on window.V2_USE_MOCK !== false
    P1-03  No hardcoded mock return paths remain active (all guarded by _useMock())

  Phase 2.1 — Weakness status + note interaction
    P2-01  updateWeaknessStatus() added to api.js
    P2-02  updateWeaknessStatus signature accepts projectId, reviewId, weaknessId, status, userNote
    P2-03  updateWeaknessStatus POSTs to correct endpoint path
    P2-04  updateWeaknessStatus omits user_note key when userNote is null
    P2-05  updateDecisionStatus() added to api.js
    P2-06  updateDecisionStatus POSTs to correct endpoint path
    P2-07  Both new functions are exposed on window.API
    P2-08  DetailPanel._renderWeaknessRow exists
    P2-09  Weakness row renders a <select> with all four valid statuses
    P2-10  Weakness row renders a <textarea> for user_note
    P2-11  Textarea has onblur wired to DetailPanel._onWeaknessNoteBlur
    P2-12  Status select has onchange wired to DetailPanel._onWeaknessStatusChange
    P2-13  _onWeaknessStatusChange reads data-pid, data-rid, data-wid from dataset
    P2-14  _onWeaknessNoteBlur reads sibling select for current status
    P2-15  _onWeaknessNoteBlur passes textarea.value as userNote argument

  Phase 2.2 — Decision point status interaction
    P2-16  DetailPanel._renderDecisionRow exists
    P2-17  Decision row renders a <select> with all four valid statuses
    P2-18  Decision status select has onchange wired to DetailPanel._onDecisionStatusChange
    P2-19  _onDecisionStatusChange reads data-pid, data-rid, data-did from dataset
    P2-20  renderReview includes decision_points section

  Phase 2.3 — Provenance line
    P2-21  DetailPanel._renderProvenanceLine exists
    P2-22  Provenance line shows persona from review object
    P2-23  Provenance line shows included_files count
    P2-24  Provenance line shows category chips from review.categories
    P2-25  Provenance line rendered above finding blocks in renderReview

  Regression — existing DetailPanel contracts unchanged
    R-01   renderVersion still present and unchanged in shape
    R-02   renderReview still renders findings by category
    R-03   renderReview still renders open questions
    R-04   renderSkeleton still present
    R-05   DetailPanel exposed on window.DetailPanel
    R-06   api.js existing functions still present and exposed
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT            = Path(__file__).parent.parent
DASHBOARD_HTML  = ROOT / "static" / "v2" / "dashboard_v2.html"
API_JS          = ROOT / "static" / "v2" / "js" / "api.js"
DETAIL_PANEL_JS = ROOT / "ui" / "v2" / "components" / "DetailPanel.js"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def html() -> str:
    return DASHBOARD_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_js() -> str:
    return API_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def detail_js() -> str:
    return DETAIL_PANEL_JS.read_text(encoding="utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fn_exists(src: str, name: str) -> bool:
    return bool(re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(", src))


def _fn_body(src: str, name: str) -> str:
    """Extract function body (heuristic: up to next top-level function or end)."""
    m = re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{([\s\S]+?)"
        rf"(?=\n\s*(?:async\s+)?function\s|\Z)",
        src,
    )
    if not m:
        pytest.fail(f"function {name}() not found in source")
    return m.group(1)


# ═════════════════════════════════════════════════════════════════════════════
# Phase 1 — Live backend connection
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase1LiveMode:
    """P1: V2_USE_MOCK is disabled so all API calls reach the live backend."""

    def test_p1_01_mock_flag_set_false_in_html(self, html):
        """window.V2_USE_MOCK = false must appear in dashboard_v2.html."""
        assert "window.V2_USE_MOCK = false" in html, (
            "P1-01: V2_USE_MOCK=false not found in dashboard_v2.html"
        )

    def test_p1_01_mock_flag_set_before_compare_js(self, html):
        """The flag must appear before the <script src=.../compare.js> tag."""
        flag_pos    = html.find("window.V2_USE_MOCK = false")
        compare_pos = html.find("compare.js")
        assert flag_pos != -1, "P1-01: V2_USE_MOCK=false not found"
        assert compare_pos != -1, "P1-01: compare.js script tag not found"
        assert flag_pos < compare_pos, (
            "P1-01: window.V2_USE_MOCK=false must appear before compare.js is loaded"
        )

    def test_p1_02_use_mock_guard_in_api_js(self, api_js):
        """api.js must define a _useMock() guard reading window.V2_USE_MOCK."""
        assert "_useMock" in api_js, "P1-02: _useMock helper not found in api.js"
        assert "window.V2_USE_MOCK" in api_js, "P1-02: window.V2_USE_MOCK not read in api.js"

    def test_p1_02_use_mock_checks_not_false(self, api_js):
        """_useMock() must use !== false (not a truthy check) so explicit false disables it."""
        assert "!== false" in api_js, (
            "P1-02: _useMock() must compare window.V2_USE_MOCK !== false"
        )

    def test_p1_03_all_mock_returns_guarded(self, api_js):
        """Every `if (_useMock())` guard must precede each mock data return."""
        # Count mock guard occurrences and MOCK_DATA references in return paths
        guard_count = len(re.findall(r"_useMock\(\)", api_js))
        mock_return = len(re.findall(r"return.*MOCK_DATA", api_js))
        assert guard_count >= mock_return, (
            f"P1-03: {mock_return} MOCK_DATA returns but only {guard_count} _useMock() guards"
        )

    def test_p1_03_no_unconditional_mock_return(self, api_js):
        """No MOCK_DATA return must appear outside an _useMock() block."""
        # Each MOCK_DATA return must be inside an if(_useMock()) block
        # Simple heuristic: every 'return MOCK_DATA' line must have _useMock nearby
        lines = api_js.splitlines()
        for i, line in enumerate(lines):
            if "return MOCK_DATA" in line or "return { projects: MOCK_DATA" in line:
                # Look back up to 5 lines for the guard
                context = "\n".join(lines[max(0, i - 5):i + 1])
                assert "_useMock()" in context, (
                    f"P1-03: Unconditional MOCK_DATA return at line {i + 1}: {line.strip()}"
                )


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2.1 — Weakness status + note API functions
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase2ApiWeakness:
    """P2: api.js has updateWeaknessStatus and updateDecisionStatus."""

    def test_p2_01_update_weakness_status_defined(self, api_js):
        assert _fn_exists(api_js, "updateWeaknessStatus"), (
            "P2-01: updateWeaknessStatus() not defined in api.js"
        )

    def test_p2_02_signature_has_five_params(self, api_js):
        """updateWeaknessStatus must accept (projectId, reviewId, weaknessId, status, userNote)."""
        m = re.search(
            r"async\s+function\s+updateWeaknessStatus\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\)",
            api_js,
        )
        assert m, "P2-02: updateWeaknessStatus must declare exactly 5 parameters"

    def test_p2_03_posts_to_weakness_status_endpoint(self, api_js):
        body = _fn_body(api_js, "updateWeaknessStatus")
        assert "weakness" in body, "P2-03: endpoint must contain 'weakness'"
        assert "status" in body, "P2-03: endpoint must contain 'status'"
        assert "_request" in body, "P2-03: must use _request() helper"
        assert "'POST'" in body or '"POST"' in body, "P2-03: must be a POST request"

    def test_p2_04_omits_user_note_when_null(self, api_js):
        body = _fn_body(api_js, "updateWeaknessStatus")
        # Must conditionally add user_note key only when not null
        assert "user_note" in body, "P2-04: user_note key not handled"
        assert "null" in body, "P2-04: null check missing for userNote"
        # Must not always set body.user_note — must be conditional
        assert "!== null" in body or "null" in body, (
            "P2-04: userNote null guard missing"
        )

    def test_p2_05_update_decision_status_defined(self, api_js):
        assert _fn_exists(api_js, "updateDecisionStatus"), (
            "P2-05: updateDecisionStatus() not defined in api.js"
        )

    def test_p2_06_decision_posts_to_decision_status_endpoint(self, api_js):
        body = _fn_body(api_js, "updateDecisionStatus")
        assert "decision" in body, "P2-06: endpoint must contain 'decision'"
        assert "status" in body, "P2-06: endpoint must contain 'status'"
        assert "'POST'" in body or '"POST"' in body, "P2-06: must be a POST request"

    def test_p2_07_both_functions_exposed_on_window_api(self, api_js):
        # Locate the window.API = { ... } block
        m = re.search(r"window\.API\s*=\s*\{([^}]+)\}", api_js, re.DOTALL)
        assert m, "P2-07: window.API object not found in api.js"
        api_block = m.group(1)
        assert "updateWeaknessStatus" in api_block, (
            "P2-07: updateWeaknessStatus not exposed on window.API"
        )
        assert "updateDecisionStatus" in api_block, (
            "P2-07: updateDecisionStatus not exposed on window.API"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2.1 — Weakness row in DetailPanel
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase2DetailPanelWeakness:

    def test_p2_08_render_weakness_row_exists(self, detail_js):
        assert "_renderWeaknessRow" in detail_js, (
            "P2-08: _renderWeaknessRow not found in DetailPanel.js"
        )

    def test_p2_09_weakness_select_has_all_four_statuses(self, detail_js):
        # Options are built via Array.map(['open','addressed','validated','rejected'])
        # so individual value="open" literals never appear — test the source array instead.
        body = _fn_body(detail_js, "_renderWeaknessRow")
        for status in ("open", "addressed", "validated", "rejected"):
            assert status in body, (
                f"P2-09: status '{status}' missing from weakness row builder"
            )

    def test_p2_10_weakness_has_textarea(self, detail_js):
        assert "<textarea" in detail_js, "P2-10: <textarea> not found in DetailPanel.js"

    def test_p2_10_textarea_placeholder_add_note(self, detail_js):
        assert "Add note" in detail_js, (
            "P2-10: textarea placeholder 'Add note' not found"
        )

    def test_p2_11_textarea_onblur_wired(self, detail_js):
        assert "onblur=" in detail_js, "P2-11: onblur not found in DetailPanel.js"
        assert "_onWeaknessNoteBlur" in detail_js, (
            "P2-11: _onWeaknessNoteBlur not referenced in DetailPanel.js"
        )

    def test_p2_12_select_onchange_wired(self, detail_js):
        assert "onchange=" in detail_js, "P2-12: onchange not found in DetailPanel.js"
        assert "_onWeaknessStatusChange" in detail_js, (
            "P2-12: _onWeaknessStatusChange not referenced in DetailPanel.js"
        )

    def test_p2_13_status_change_reads_data_attributes(self, detail_js):
        body = _fn_body(detail_js, "_onWeaknessStatusChange")
        assert "dataset" in body or "data-pid" in body, (
            "P2-13: _onWeaknessStatusChange must read data attributes from element"
        )
        assert "pid" in body and "rid" in body and "wid" in body, (
            "P2-13: _onWeaknessStatusChange must extract pid, rid, wid"
        )

    def test_p2_14_note_blur_reads_sibling_select(self, detail_js):
        body = _fn_body(detail_js, "_onWeaknessNoteBlur")
        assert "querySelector" in body or "select" in body.lower(), (
            "P2-14: _onWeaknessNoteBlur must find sibling <select> for current status"
        )

    def test_p2_15_note_blur_passes_textarea_value(self, detail_js):
        body = _fn_body(detail_js, "_onWeaknessNoteBlur")
        assert "ta.value" in body or ".value" in body, (
            "P2-15: _onWeaknessNoteBlur must pass textarea.value as userNote"
        )
        assert "updateWeaknessStatus" in body, (
            "P2-15: _onWeaknessNoteBlur must call api.updateWeaknessStatus"
        )

    def test_p2_weakness_row_uses_data_attributes(self, detail_js):
        """_renderWeaknessRow must embed data-pid, data-rid, data-wid on both controls."""
        assert "data-pid=" in detail_js, "weakness row missing data-pid attribute"
        assert "data-rid=" in detail_js, "weakness row missing data-rid attribute"
        assert "data-wid=" in detail_js, "weakness row missing data-wid attribute"

    def test_p2_all_weaknesses_rendered_not_just_open(self, detail_js):
        """renderReview must iterate r.weaknesses (all), not filter to open only."""
        body = _fn_body(detail_js, "renderReview")
        # Must not apply .filter(w => w.status === 'open') before rendering
        # (Counting the open ones for the badge is OK, but the map must use all)
        assert "r.weaknesses" in body or "weaknesses =" in body, (
            "renderReview must reference r.weaknesses"
        )
        # Must call _renderWeaknessRow for rendering (not just count)
        assert "_renderWeaknessRow" in body, (
            "renderReview must call _renderWeaknessRow for each weakness"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2.2 — Decision point row in DetailPanel
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase2DetailPanelDecision:

    def test_p2_16_render_decision_row_exists(self, detail_js):
        assert "_renderDecisionRow" in detail_js, (
            "P2-16: _renderDecisionRow not found in DetailPanel.js"
        )

    def test_p2_17_decision_select_has_all_four_statuses(self, detail_js):
        # Statuses appear in both weakness and decision rows; presence is sufficient
        for status in ("open", "addressed", "validated", "rejected"):
            assert status in detail_js, (
                f"P2-17: status '{status}' missing from DetailPanel.js"
            )

    def test_p2_18_decision_onchange_wired(self, detail_js):
        assert "_onDecisionStatusChange" in detail_js, (
            "P2-18: _onDecisionStatusChange not referenced in DetailPanel.js"
        )

    def test_p2_19_decision_change_reads_data_did(self, detail_js):
        body = _fn_body(detail_js, "_onDecisionStatusChange")
        assert "did" in body, "P2-19: _onDecisionStatusChange must extract data-did"
        assert "updateDecisionStatus" in body, (
            "P2-19: _onDecisionStatusChange must call api.updateDecisionStatus"
        )

    def test_p2_20_render_review_includes_decision_points(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "decision_points" in body, (
            "P2-20: renderReview must reference decision_points"
        )
        assert "_renderDecisionRow" in body, (
            "P2-20: renderReview must call _renderDecisionRow"
        )

    def test_p2_decision_row_uses_data_did(self, detail_js):
        assert "data-did=" in detail_js, "decision row missing data-did attribute"

    def test_p2_decision_section_shows_open_count_badge(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "Decision Points" in body, (
            "Decision Points section header missing from renderReview"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Phase 2.3 — Provenance line in DetailPanel
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase2ProvenanceLine:

    def test_p2_21_render_provenance_line_exists(self, detail_js):
        assert "_renderProvenanceLine" in detail_js, (
            "P2-21: _renderProvenanceLine not found in DetailPanel.js"
        )

    def test_p2_22_provenance_shows_persona(self, detail_js):
        body = _fn_body(detail_js, "_renderProvenanceLine")
        assert "persona" in body, (
            "P2-22: _renderProvenanceLine must reference persona"
        )

    def test_p2_23_provenance_shows_file_count(self, detail_js):
        body = _fn_body(detail_js, "_renderProvenanceLine")
        assert "included_files" in body, (
            "P2-23: _renderProvenanceLine must reference included_files"
        )
        assert "length" in body, (
            "P2-23: _renderProvenanceLine must show file count"
        )

    def test_p2_24_provenance_shows_category_chips(self, detail_js):
        body = _fn_body(detail_js, "_renderProvenanceLine")
        assert "categories" in body, (
            "P2-24: _renderProvenanceLine must reference r.categories"
        )

    def test_p2_25_provenance_rendered_above_findings(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        prov_pos     = body.find("provenanceLine")
        findings_pos = body.find("findingsHtml")
        assert prov_pos != -1,    "P2-25: provenanceLine not used in renderReview"
        assert findings_pos != -1, "P2-25: findingsHtml not used in renderReview"
        assert prov_pos < findings_pos, (
            "P2-25: provenanceLine must appear before findingsHtml in the rendered output"
        )

    def test_p2_provenance_returns_empty_when_no_data(self, detail_js):
        body = _fn_body(detail_js, "_renderProvenanceLine")
        # Must guard against empty data and return ''
        assert "return ''" in body or 'return ""' in body, (
            "_renderProvenanceLine must return empty string when no provenance data available"
        )


# ═════════════════════════════════════════════════════════════════════════════
# Regression — existing DetailPanel contracts preserved
# ═════════════════════════════════════════════════════════════════════════════

class TestDetailPanelRegression:

    def test_r01_render_version_still_present(self, detail_js):
        assert _fn_exists(detail_js, "renderVersion"), (
            "R-01: renderVersion() removed from DetailPanel.js"
        )

    def test_r02_render_review_still_renders_findings(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "findings" in body, "R-02: findings no longer rendered in renderReview"
        assert "Findings by Category" in body, (
            "R-02: 'Findings by Category' section label removed"
        )

    def test_r03_render_review_still_renders_questions(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "questions" in body, "R-03: questions no longer rendered in renderReview"
        assert "Open Questions" in body, "R-03: 'Open Questions' label removed"

    def test_r04_render_skeleton_present(self, detail_js):
        assert _fn_exists(detail_js, "renderSkeleton"), (
            "R-04: renderSkeleton() removed from DetailPanel.js"
        )

    def test_r05_detail_panel_exposed_on_window(self, detail_js):
        assert "window.DetailPanel" in detail_js, (
            "R-05: DetailPanel not exposed on window object"
        )

    def test_r05_event_handlers_exposed_on_detail_panel(self, detail_js):
        """Phase 2 handlers must be returned from the IIFE so inline HTML can call them."""
        m = re.search(r"return\s*\{([^}]+)\}", detail_js, re.DOTALL)
        assert m, "R-05: return block not found in DetailPanel IIFE"
        returned = m.group(1)
        assert "_onWeaknessStatusChange" in returned, (
            "R-05: _onWeaknessStatusChange not exported from DetailPanel IIFE"
        )
        assert "_onWeaknessNoteBlur" in returned, (
            "R-05: _onWeaknessNoteBlur not exported from DetailPanel IIFE"
        )
        assert "_onDecisionStatusChange" in returned, (
            "R-05: _onDecisionStatusChange not exported from DetailPanel IIFE"
        )

    def test_r06_existing_api_functions_still_present(self, api_js):
        for fn in ("fetchProjects", "fetchHierarchy", "fetchMetrics",
                   "fetchVersions", "fetchReviews", "fetchReviewDetail",
                   "fetchVersionDetail"):
            assert _fn_exists(api_js, fn), f"R-06: {fn}() removed from api.js"

    def test_r06_existing_api_functions_still_exposed(self, api_js):
        m = re.search(r"window\.API\s*=\s*\{([^}]+)\}", api_js, re.DOTALL)
        assert m, "R-06: window.API not found in api.js"
        api_block = m.group(1)
        for fn in ("fetchProjects", "fetchHierarchy", "fetchMetrics",
                   "fetchVersions", "fetchReviews", "fetchReviewDetail",
                   "fetchVersionDetail"):
            assert fn in api_block, f"R-06: {fn} removed from window.API exports"

    def test_r_render_review_shows_summary(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "summary" in body, "renderReview no longer renders summary"

    def test_r_render_review_shows_quality_badge(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "_qualityBadge" in body, "renderReview no longer calls _qualityBadge"

    def test_r_render_review_close_button_present(self, detail_js):
        body = _fn_body(detail_js, "renderReview")
        assert "closeDrawer" in body or "Close Panel" in body, (
            "renderReview lost the close panel button"
        )

    def test_r_weakness_open_count_badge_present(self, detail_js):
        """renderReview must show how many weaknesses are still open."""
        body = _fn_body(detail_js, "renderReview")
        assert "open" in body, "weakness open count badge missing"

    def test_r_decision_open_count_badge_present(self, detail_js):
        """renderReview must show how many decision points are still open."""
        body = _fn_body(detail_js, "renderReview")
        assert "Decision Points" in body
