"""Phase 3 & Phase 4 Tests — V2 Iteration and Reconciliation.

All tests are static analysis (source file inspection) plus light
unit tests on backend handlers/services.  No live server, no DB,
no network calls.

Coverage:
  Phase 3 — Review Iteration
    P3-01  handle_iterate_review() exists in handlers/review.py
    P3-02  Requires roles or persona; returns 400 when missing
    P3-03  Requires previous_review_id from URL; returns 400 when empty
    P3-04  Builds ReviewRequest with previous_review_id set
    P3-05  /iterate route registered in server.py POST handler
    P3-06  Route pattern correctly extracts pid and rid from URL parts
    P3-07  iterateReview() added to api.js
    P3-08  iterateReview() POSTs to correct endpoint path
    P3-09  iterateReview() wraps scalar roles in an array
    P3-10  iterateReview() guarded by _useMock()
    P3-11  iterateReview() exposed on window.API
    P3-12  DetailPanel._onIterateSummaryClick exists
    P3-13  DetailPanel._onIterateSubmit exists
    P3-14  Iterate panel renders with persona select and prompt textarea
    P3-15  Iterate panel wired to _onIterateSubmit via onclick
    P3-16  _onIterateSubmit calls api.iterateReview
    P3-17  On success, _onIterateSubmit calls Dashboard.loadAll
    P3-18  _onIterateSummaryClick lazy-loads personas from /api/personas
    P3-19  Both handlers exported from DetailPanel IIFE
    P3-20  dashboard.js exposes DashboardRefresh global helper

  Phase 4 — Reconciliation
    P4-01  handle_reconcile_reviews() exists in handlers/hierarchy.py
    P4-02  Returns 400 when anchor_review_id missing
    P4-03  Calls svc.reconcile_reviews() with correct arguments
    P4-04  reconcile_reviews() exists in services/hierarchy.py
    P4-05  reconcile_reviews() raises ValueError for unknown anchor
    P4-06  reconcile_reviews() raises ValueError for unknown supplemental
    P4-07  reconcile_reviews() calls synthesize_reviews() with correct args
    P4-08  /reconcile route registered in server.py POST handler
    P4-09  reconcileReviews() added to api.js
    P4-10  reconcileReviews() POSTs to correct endpoint path
    P4-11  reconcileReviews() passes supplemental_review_ids in body
    P4-12  reconcileReviews() guarded by _useMock()
    P4-13  reconcileReviews() exposed on window.API
    P4-14  ReconciliationPanel.render() exists
    P4-15  ReconciliationPanel.onAnchorChange() exists
    P4-16  ReconciliationPanel.onRunReconcile() exists
    P4-17  ReconciliationPanel.renderResult() exists
    P4-18  render() stores project/version ids in dataset
    P4-19  onRunReconcile() collects supplemental checkboxes
    P4-20  onRunReconcile() calls api.reconcileReviews
    P4-21  onRunReconcile() shows result via renderResult()
    P4-22  onAnchorChange() rebuilds supplemental checkboxes
    P4-23  renderResult() renders reconciled_findings by category
    P4-24  renderResult() renders contradictions section
    P4-25  renderResult() renders reconciliation_notes
    P4-26  Dashboard.openReconcileDrawer() exists in dashboard.js
    P4-27  openReconcileDrawer() exported from Dashboard IIFE
    P4-28  Dashboard._renderDrawerContent handles 'reconcile' entity type
    P4-29  Accordion has reconcile ⇄ button per version
    P4-30  dashboard_v2.html loads reconciliation_panel.js
    P4-31  reconciliation_panel.js exists in static/v2/js/

  Regression — existing contracts preserved
    R-01  handlers/review.py existing functions unchanged
    R-02  handlers/hierarchy.py existing functions unchanged
    R-03  api.js existing functions still on window.API
    R-04  DetailPanel Phase 2 handlers still exported
    R-05  dashboard.js existing public methods still returned
"""


from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent

# ── Paths ─────────────────────────────────────────────────────────────────────
HANDLER_REVIEW    = ROOT / "handlers"    / "review.py"
HANDLER_HIERARCHY = ROOT / "handlers"    / "hierarchy.py"
SVC_HIERARCHY     = ROOT / "services"    / "hierarchy.py"
SERVER_PY         = ROOT / "server.py"
API_JS            = ROOT / "static"      / "v2" / "js"        / "api.js"
DASHBOARD_JS      = ROOT / "static"      / "v2" / "js"        / "dashboard.js"
ACCORDION_JS      = ROOT / "static"      / "v2" / "js"        / "accordion.js"
DETAIL_PANEL_JS   = ROOT / "ui"          / "v2" / "components" / "DetailPanel.js"
RECON_PANEL_JS    = ROOT / "ui"          / "v2" / "components" / "ReconciliationPanel.js"
RECON_SERVED      = ROOT / "static"      / "v2" / "js"        / "reconciliation_panel.js"
DASHBOARD_HTML    = ROOT / "static"      / "v2" / "dashboard_v2.html"

# ── Source fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def h_review_src():    return HANDLER_REVIEW.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def h_hierarchy_src(): return HANDLER_HIERARCHY.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def svc_hierarchy_src(): return SVC_HIERARCHY.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def server_src():  return SERVER_PY.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def api_js():      return API_JS.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def dashboard_js(): return DASHBOARD_JS.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def accordion_js(): return ACCORDION_JS.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def detail_js():   return DETAIL_PANEL_JS.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def recon_js():    return RECON_PANEL_JS.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def html():        return DASHBOARD_HTML.read_text(encoding="utf-8")

# ── JS helpers ────────────────────────────────────────────────────────────────

def _fn_exists(src: str, name: str) -> bool:
    return bool(re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\(", src))

def _fn_body(src: str, name: str) -> str:
    m = re.search(
        rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{([\s\S]+?)"
        rf"(?=\n\s*(?:async\s+)?function\s|\Z)", src,
    )
    if not m:
        pytest.fail(f"function {name}() not found in source")
    return m.group(1)

def _iife_return(src: str) -> str:
    """Extract the return {{...}} block from the first IIFE in src."""
    m = re.search(r"return\s*\{([^}]+)\}", src, re.DOTALL)
    if not m:
        pytest.fail("IIFE return block not found")
    return m.group(1)

# ═════════════════════════════════════════════════════════════════════════════
# Phase 3 — Backend
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase3BackendHandler:

    def test_p3_01_handle_iterate_review_defined(self, h_review_src):
        assert "handle_iterate_review" in h_review_src

    def test_p3_02_missing_roles_returns_400(self, h_review_src):
        # Source-level: handler must check for roles and respond with 400
        assert 'respond({"error": "roles (or persona) required"}, status=400)' in h_review_src

    def test_p3_03_empty_previous_id_returns_400(self, h_review_src):
        # Source-level: handler must check for previous_review_id and respond with 400
        assert "previous_review_id" in h_review_src
        assert 'status=400' in h_review_src

    def test_p3_04_builds_review_request_with_previous_review_id(self, h_review_src):
        assert "previous_review_id" in h_review_src
        assert "ReviewRequest" in h_review_src

    def test_p3_05_iterate_route_in_server_do_post(self, server_src):
        assert "/iterate" in server_src

    def test_p3_06_iterate_route_extracts_pid_and_rid(self, server_src):
        # Route must call handle_iterate_review with parts[3] and parts[6]
        assert "handle_iterate_review" in server_src
        assert "parts[3]" in server_src
        assert "parts[6]" in server_src



# ═════════════════════════════════════════════════════════════════════════════
# Phase 3 — Frontend (api.js + DetailPanel)
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase3FrontendApi:

    def test_p3_07_iterate_review_defined(self, api_js):
        assert _fn_exists(api_js, "iterateReview")

    def test_p3_08_posts_to_iterate_endpoint(self, api_js):
        body = _fn_body(api_js, "iterateReview")
        assert "/iterate" in body
        assert "'POST'" in body or '"POST"' in body

    def test_p3_09_wraps_scalar_roles_in_array(self, api_js):
        body = _fn_body(api_js, "iterateReview")
        # Must handle Array.isArray(roles) ? roles : [roles]
        assert "isArray" in body or "[roles]" in body

    def test_p3_10_guarded_by_use_mock(self, api_js):
        body = _fn_body(api_js, "iterateReview")
        assert "_useMock" in body

    def test_p3_11_exposed_on_window_api(self, api_js):
        m = re.search(r"window\.API\s*=\s*\{([^}]+)\}", api_js, re.DOTALL)
        assert m, "window.API block not found"
        assert "iterateReview" in m.group(1)


class TestPhase3FrontendDetailPanel:

    def test_p3_12_on_iterate_summary_click_exists(self, detail_js):
        assert "_onIterateSummaryClick" in detail_js

    def test_p3_13_on_iterate_submit_exists(self, detail_js):
        assert "_onIterateSubmit" in detail_js

    def test_p3_14_iterate_panel_has_persona_select(self, detail_js):
        assert "v2-iterate-persona-" in detail_js
        assert "<select" in detail_js

    def test_p3_14_iterate_panel_has_prompt_textarea(self, detail_js):
        assert "v2-iterate-prompt-" in detail_js
        assert "<textarea" in detail_js

    def test_p3_15_iterate_panel_wired_to_submit(self, detail_js):
        assert "_onIterateSubmit" in detail_js
        assert "onclick=" in detail_js

    def test_p3_16_on_iterate_submit_calls_api_iterate_review(self, detail_js):
        body = _fn_body(detail_js, "_onIterateSubmit")
        assert "iterateReview" in body

    def test_p3_17_on_iterate_submit_refreshes_hierarchy(self, detail_js):
        body = _fn_body(detail_js, "_onIterateSubmit")
        # Must call Dashboard.loadAll or DashboardRefresh after success
        assert "loadAll" in body or "DashboardRefresh" in body

    def test_p3_18_summary_click_lazy_loads_personas(self, detail_js):
        body = _fn_body(detail_js, "_onIterateSummaryClick")
        assert "/api/personas" in body
        assert "fetch" in body

    def test_p3_19_both_handlers_exported_from_iife(self, detail_js):
        returned = _iife_return(detail_js)
        assert "_onIterateSummaryClick" in returned
        assert "_onIterateSubmit" in returned

    def test_p3_20_dashboard_refresh_global_exported(self, dashboard_js):
        assert "DashboardRefresh" in dashboard_js
        assert "Dashboard.loadAll" in dashboard_js



# ═════════════════════════════════════════════════════════════════════════════
# Phase 4 — Backend
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase4BackendHandler:

    def test_p4_01_handle_reconcile_reviews_defined(self, h_hierarchy_src):
        assert "handle_reconcile_reviews" in h_hierarchy_src

    def test_p4_02_missing_anchor_returns_400(self, h_hierarchy_src):
        # Source-level: handler must check anchor_review_id and respond with 400
        assert "anchor_review_id" in h_hierarchy_src
        assert 'respond({"error": "anchor_review_id required"}, status=400)' in h_hierarchy_src

    def test_p4_03_calls_svc_reconcile_reviews(self, h_hierarchy_src):
        assert "svc.reconcile_reviews" in h_hierarchy_src
        assert "anchor_review_id" in h_hierarchy_src
        assert "supplemental_review_ids" in h_hierarchy_src
        assert "ai_backend" in h_hierarchy_src

    def test_p4_08_reconcile_route_in_server_do_post(self, server_src):
        assert "/hierarchy/reconcile" in server_src
        assert "handle_reconcile_reviews" in server_src


class TestPhase4BackendService:

    def test_p4_04_reconcile_reviews_in_service(self, svc_hierarchy_src):
        assert "def reconcile_reviews" in svc_hierarchy_src

    def test_p4_05_raises_for_unknown_anchor(self, tmp_path, monkeypatch):
        import os; os.environ.setdefault("PROJECTS_DATA_DIR", str(tmp_path))
        from services.hierarchy import reconcile_reviews
        with pytest.raises(ValueError, match="Anchor review not found"):
            reconcile_reviews("proj_p4_test", "no_such_anchor", [], "files_only")

    def test_p4_06_raises_for_unknown_supplemental(self, tmp_path, monkeypatch):
        """If anchor exists but a supplemental does not, ValueError is raised."""
        from models.hierarchy import _make_hierarchy_store
        store = _make_hierarchy_store("proj_p4_supp")
        version = store.create_version(included_artifacts=[], label="Test")
        review = store.create_review(
            version_id=version.version_id, persona="Test Persona", findings={}
        )
        from services.hierarchy import reconcile_reviews
        with pytest.raises(ValueError, match="Supplemental review not found"):
            reconcile_reviews("proj_p4_supp", review.review_id, ["ghost_id"], "files_only")

    def test_p4_07_calls_synthesize_reviews(self, svc_hierarchy_src):
        assert "synthesize_reviews" in svc_hierarchy_src
        assert "anchor_review=" in svc_hierarchy_src
        assert "supplemental_reviews=" in svc_hierarchy_src
        assert "version_scope=" in svc_hierarchy_src

    def test_p4_reconcile_single_review_returns_dict(self, tmp_path, monkeypatch):
        """Anchor-only reconciliation (no supplementals) returns a valid dict."""
        from models.hierarchy import _make_hierarchy_store
        store = _make_hierarchy_store("proj_p4_single")
        version = store.create_version(included_artifacts=[], label="Test V")
        review = store.create_review(
            version_id=version.version_id, persona="Test Persona",
            findings={"risks": ["Risk A"], "constraints": ["C1"]},
        )
        from services.hierarchy import reconcile_reviews
        result = reconcile_reviews("proj_p4_single", review.review_id, [], "files_only")
        assert isinstance(result, dict)
        assert "reconciled_findings" in result
        assert "source_review_ids" in result
        assert review.review_id in result["source_review_ids"]



# ═════════════════════════════════════════════════════════════════════════════
# Phase 4 — Frontend (api.js + ReconciliationPanel + Dashboard + Accordion)
# ═════════════════════════════════════════════════════════════════════════════

class TestPhase4FrontendApi:

    def test_p4_09_reconcile_reviews_defined(self, api_js):
        assert _fn_exists(api_js, "reconcileReviews")

    def test_p4_10_posts_to_reconcile_endpoint(self, api_js):
        body = _fn_body(api_js, "reconcileReviews")
        assert "/hierarchy/reconcile" in body
        assert "'POST'" in body or '"POST"' in body

    def test_p4_11_passes_supplemental_ids_in_body(self, api_js):
        body = _fn_body(api_js, "reconcileReviews")
        assert "supplemental_review_ids" in body

    def test_p4_12_guarded_by_use_mock(self, api_js):
        body = _fn_body(api_js, "reconcileReviews")
        assert "_useMock" in body

    def test_p4_13_exposed_on_window_api(self, api_js):
        m = re.search(r"window\.API\s*=\s*\{([^}]+)\}", api_js, re.DOTALL)
        assert m, "window.API block not found"
        assert "reconcileReviews" in m.group(1)


class TestPhase4ReconciliationPanel:

    def test_p4_14_render_defined(self, recon_js):
        assert _fn_exists(recon_js, "render")

    def test_p4_15_on_anchor_change_defined(self, recon_js):
        assert _fn_exists(recon_js, "onAnchorChange")

    def test_p4_16_on_run_reconcile_defined(self, recon_js):
        assert _fn_exists(recon_js, "onRunReconcile")

    def test_p4_17_render_result_defined(self, recon_js):
        assert _fn_exists(recon_js, "renderResult")

    def test_p4_18_render_stores_pid_vid_in_dataset(self, recon_js):
        body = _fn_body(recon_js, "render")
        assert "recPid" in body
        assert "recVid" in body

    def test_p4_19_on_run_reconcile_collects_checkboxes(self, recon_js):
        body = _fn_body(recon_js, "onRunReconcile")
        assert "querySelectorAll" in body
        assert "rec-supp-check-" in body

    def test_p4_20_on_run_reconcile_calls_api(self, recon_js):
        body = _fn_body(recon_js, "onRunReconcile")
        assert "reconcileReviews" in body

    def test_p4_21_on_run_reconcile_calls_render_result_on_success(self, recon_js):
        body = _fn_body(recon_js, "onRunReconcile")
        assert "renderResult" in body

    def test_p4_22_on_anchor_change_rebuilds_supplementals(self, recon_js):
        body = _fn_body(recon_js, "onAnchorChange")
        # Must rebuild the supplemental area
        assert "rec-supp-area-" in body
        assert "_renderSupplementalCheckboxes" in body or "innerHTML" in body

    def test_p4_23_render_result_shows_findings(self, recon_js):
        body = _fn_body(recon_js, "renderResult")
        assert "reconciled_findings" in body
        assert "_CAT_LABELS" in body

    def test_p4_24_render_result_shows_contradictions(self, recon_js):
        body = _fn_body(recon_js, "renderResult")
        assert "contradictions" in body
        assert "Conflicts" in body

    def test_p4_25_render_result_shows_notes(self, recon_js):
        body = _fn_body(recon_js, "renderResult")
        assert "reconciliation_notes" in body
        assert "Reconciliation Notes" in body

    def test_p4_panel_exposed_on_window(self, recon_js):
        assert "window.ReconciliationPanel" in recon_js

    def test_p4_all_public_methods_returned(self, recon_js):
        returned = _iife_return(recon_js)
        for fn in ("render", "renderResult", "onAnchorChange", "onRunReconcile"):
            assert fn in returned, f"{fn} not returned from ReconciliationPanel IIFE"


class TestPhase4Dashboard:

    def test_p4_26_open_reconcile_drawer_defined(self, dashboard_js):
        assert _fn_exists(dashboard_js, "openReconcileDrawer")

    def test_p4_27_open_reconcile_drawer_exported(self, dashboard_js):
        returned = _iife_return(dashboard_js)
        assert "openReconcileDrawer" in returned

    def test_p4_28_render_drawer_content_handles_reconcile_type(self, dashboard_js):
        body = _fn_body(dashboard_js, "_renderDrawerContent")
        assert "'reconcile'" in body or '"reconcile"' in body
        assert "ReconciliationPanel" in body

    def test_p4_open_reconcile_drawer_opens_drawer_with_reconcile_type(self, dashboard_js):
        body = _fn_body(dashboard_js, "openReconcileDrawer")
        assert "openDrawer" in body
        assert "'reconcile'" in body or '"reconcile"' in body


class TestPhase4AccordionAndHtml:

    def test_p4_29_accordion_has_reconcile_button(self, accordion_js):
        assert "openReconcileDrawer" in accordion_js
        assert "⇄" in accordion_js

    def test_p4_30_dashboard_html_loads_reconciliation_panel_js(self, html):
        assert "reconciliation_panel.js" in html

    def test_p4_31_reconciliation_panel_js_exists_in_static(self):
        assert RECON_SERVED.exists(), (
            f"reconciliation_panel.js not found at {RECON_SERVED}"
        )

    def test_p4_served_file_matches_source(self):
        """The served static copy must be identical to the source component."""
        src  = RECON_PANEL_JS.read_text(encoding="utf-8")
        served = RECON_SERVED.read_text(encoding="utf-8")
        assert src == served, (
            "ui/v2/components/ReconciliationPanel.js and "
            "static/v2/js/reconciliation_panel.js are out of sync"
        )



# ═════════════════════════════════════════════════════════════════════════════
# Regression — existing contracts preserved
# ═════════════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_r01_handle_review_still_present(self, h_review_src):
        assert "def handle_review(" in h_review_src

    def test_r01_handle_complete_review_still_present(self, h_review_src):
        assert "def handle_complete_review(" in h_review_src

    def test_r01_handle_weakness_status_still_present(self, h_review_src):
        assert "def handle_weakness_status(" in h_review_src

    def test_r01_handle_decision_status_still_present(self, h_review_src):
        assert "def handle_decision_status(" in h_review_src

    def test_r02_handle_compare_reviews_still_present(self, h_hierarchy_src):
        assert "def handle_compare_reviews(" in h_hierarchy_src

    def test_r02_handle_compare_versions_still_present(self, h_hierarchy_src):
        assert "def handle_compare_versions(" in h_hierarchy_src

    def test_r03_existing_api_functions_still_exposed(self, api_js):
        m = re.search(r"window\.API\s*=\s*\{([^}]+)\}", api_js, re.DOTALL)
        assert m, "window.API block not found"
        block = m.group(1)
        for fn in ("fetchProjects", "fetchHierarchy", "fetchMetrics",
                   "fetchVersions", "fetchReviews", "fetchReviewDetail",
                   "fetchVersionDetail", "updateWeaknessStatus", "updateDecisionStatus"):
            assert fn in block, f"{fn} removed from window.API"

    def test_r04_detail_panel_phase2_handlers_still_exported(self, detail_js):
        returned = _iife_return(detail_js)
        for fn in ("_onWeaknessStatusChange", "_onWeaknessNoteBlur", "_onDecisionStatusChange"):
            assert fn in returned, f"{fn} removed from DetailPanel IIFE return"

    def test_r05_dashboard_existing_methods_still_exported(self, dashboard_js):
        returned = _iife_return(dashboard_js)
        for fn in ("init", "loadAll", "renderAll", "onProjectChange",
                   "onVersionChange", "onReviewChange", "onRefresh",
                   "onCloseDrawer", "onSidebarVersionClick", "onSidebarReviewClick"):
            assert fn in returned, f"{fn} removed from Dashboard IIFE return"
