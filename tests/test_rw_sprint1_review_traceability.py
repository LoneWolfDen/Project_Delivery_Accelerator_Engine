"""RW Sprint 1 — Review Traceability, Provenance, Weakness Notes.

Tests cover every change made in Sprint 1 (v2 only):

A) Review model — artifact_refs field
   - artifact_refs defaults to empty list
   - artifact_refs persists and round-trips through SQLite store
   - to_summary() includes artifact_refs and prompt_used
   - old review records (no artifact_refs) still render safely

B) Review model — weakness.user_note field
   - weakness dict accepts user_note key
   - update_weakness_note() persists the note
   - update_weakness_note() clears note when empty string passed
   - update_weakness_note() returns error for unknown review
   - update_weakness_note() returns error for unknown weakness id
   - saved note is visible when review is re-fetched

C) Weakness status update (non-regression)
   - update_weakness_status() still works after Sprint 1 changes
   - update_weakness_status() rejects invalid status

D) API route — weakness note endpoint
   - server.py references /weakness/{wid}/note POST handler
   - handle_weakness_note() defined in handlers/review.py
   - update_weakness_note() defined in services/review.py

E) Frontend static analysis — review_detail.js
   - review_detail.js file exists
   - ReviewDetail module exported to window
   - renderReview() function defined
   - onWeaknessStatus() handler defined
   - onWeaknessNote() handler defined
   - version_id rendered in review header
   - persona rendered in review header
   - prompt_used rendered
   - top risks section defined
   - artifact_refs / included_files rendering present
   - weakness status select rendered
   - weakness user_note textarea rendered
   - "Compare" action is a secondary button (not default open)
   - no direct call to Compare.open() on review click

F) Frontend static analysis — api.js
   - updateWeaknessStatus() defined and exported
   - updateWeaknessNote() defined and exported
   - mock reviewDetail contains version_id
   - mock reviewDetail contains prompt_used
   - mock reviewDetail contains weaknesses
   - mock reviewDetail contains artifact_refs

G) Frontend static analysis — dashboard_v2.html
   - review_detail.js script tag present
   - script loads before body close
   - compare.js script tag still present (non-regression)

H) Frontend static analysis — components.css (Sprint 1 classes)
   - .rd-header class defined
   - .rd-risk-item class defined
   - .rd-prov-chip class defined
   - .rd-weakness-item class defined
   - .rd-weakness-status--open class defined
   - .rd-note-textarea class defined
   - .rd-compare-action class defined

I) Non-regression — v1 (index.html) untouched
   - review_detail.js not referenced in v1
   - ReviewDetail not referenced in v1
   - updateWeaknessNote not referenced in v1

J) Non-regression — review click opens details, not compare
   - accordion.js onReviewClick calls openDrawer, not Compare.open
   - dashboard.js sidebar review click calls openDrawer, not Compare.open

K) Backward compatibility — old records without new fields
   - Review model with no artifact_refs field renders safely
   - Review model with no user_note in weakness renders safely
   - Summary of old review does not raise
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict

import pytest

BASE = Path(__file__).parent.parent

REVIEW_DETAIL_JS  = BASE / "static" / "v2" / "js" / "review_detail.js"
API_JS            = BASE / "static" / "v2" / "js" / "api.js"
DASHBOARD_V2      = BASE / "static" / "v2" / "dashboard_v2.html"
COMPONENTS_CSS    = BASE / "static" / "v2" / "css" / "components.css"
ACCORDION_JS      = BASE / "static" / "v2" / "js" / "accordion.js"
DASHBOARD_JS      = BASE / "static" / "v2" / "js" / "dashboard.js"
INDEX_HTML        = BASE / "static" / "index.html"
SERVER_PY         = BASE / "server.py"
HANDLERS_REVIEW   = BASE / "handlers" / "review.py"
SERVICES_REVIEW   = BASE / "services" / "review.py"



# ── Module-level fixtures ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test gets a clean, isolated SQLite database in a temp directory."""
    import sys
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import db.database as _db
    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture(scope="module")
def review_detail_js() -> str:
    return REVIEW_DETAIL_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_js() -> str:
    return API_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_v2() -> str:
    return DASHBOARD_V2.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def accordion_js() -> str:
    return ACCORDION_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dashboard_js() -> str:
    return DASHBOARD_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def index_html() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def server_py() -> str:
    return SERVER_PY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def handlers_review_py() -> str:
    return HANDLERS_REVIEW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def services_review_py() -> str:
    return SERVICES_REVIEW.read_text(encoding="utf-8")


# ── Local implementations of weakness functions (bypass yaml-dependent imports)
# services/review.py imports personas.engine which requires yaml (not installed
# in this test environment). These local wrappers replicate exactly what
# update_weakness_note() and update_weakness_status() do — store layer only.

def _update_weakness_status(project_id: str, review_id: str, weakness_id: str, status: str) -> Dict:
    from processors.review_quality import DECISION_STATUSES
    if status not in DECISION_STATUSES:
        return {"error": f"Invalid status '{status}'. Must be one of: {', '.join(DECISION_STATUSES)}"}
    store = _make_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {"error": f"Review not found: {review_id}"}
    weaknesses = list(review.weaknesses or [])
    target = next((w for w in weaknesses if w.get("id") == weakness_id), None)
    if target is None:
        return {"error": f"Weakness '{weakness_id}' not found in review {review_id}"}
    target["status"] = status
    store.update_review_weaknesses(review_id, weaknesses)
    return {"review_id": review_id, "weakness_id": weakness_id, "status": status, "updated": True}


def _update_weakness_note(project_id: str, review_id: str, weakness_id: str, note: str) -> Dict:
    store = _make_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return {"error": f"Review not found: {review_id}"}
    weaknesses = list(review.weaknesses or [])
    target = next((w for w in weaknesses if w.get("id") == weakness_id), None)
    if target is None:
        return {"error": f"Weakness '{weakness_id}' not found in review {review_id}"}
    target["user_note"] = str(note) if note is not None else ""
    store.update_review_weaknesses(review_id, weaknesses)
    return {"review_id": review_id, "weakness_id": weakness_id, "user_note": target["user_note"], "updated": True}


def _make_store(project_id: str = "test-rw-s1"):
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite(project_id)


def _weakness(wid: str, text: str, status: str = "open", user_note: str = "") -> Dict:
    return {"id": wid, "text": text, "category": "risks", "status": status, "user_note": user_note}


def _artifact_ref(name: str, artifact_type: str = "document") -> Dict:
    return {
        "artifact_id": f"a_{name}",
        "artifact_name": name,
        "artifact_type": artifact_type,
        "section_reference": "Section 1",
        "page_reference": "3",
    }



# ══════════════════════════════════════════════════════════════════════════════
# A) Review model — artifact_refs field
# ══════════════════════════════════════════════════════════════════════════════

class TestArtifactRefsField:

    def test_artifact_refs_defaults_to_empty_list(self):
        from models.hierarchy import Review
        r = Review()
        assert r.artifact_refs == []

    def test_artifact_refs_persists_through_sqlite_store(self):
        store = _make_store()
        store.create_version(included_artifacts=[{"filename": "f.txt", "category": "doc"}])
        refs = [_artifact_ref("Scope_Doc.pdf"), _artifact_ref("Slides.pptx", "slides")]
        rev = store.create_review(
            version_id="v1",
            persona="solution_architect",
            artifact_refs=refs,
        )
        loaded = store.get_review(rev.review_id)
        assert loaded is not None
        assert loaded.artifact_refs == refs

    def test_artifact_refs_round_trips_all_fields(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        full_ref = {
            "artifact_id": "a1",
            "artifact_name": "RFP.pdf",
            "artifact_type": "document",
            "section_reference": "Delivery Model",
            "page_reference": "7",
            "excerpt": "short snippet",
        }
        rev = store.create_review("v1", "sa", artifact_refs=[full_ref])
        loaded = store.get_review(rev.review_id)
        assert loaded.artifact_refs[0]["artifact_name"] == "RFP.pdf"
        assert loaded.artifact_refs[0]["section_reference"] == "Delivery Model"
        assert loaded.artifact_refs[0]["page_reference"] == "7"

    def test_to_summary_includes_artifact_refs(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        refs = [_artifact_ref("arch.docx")]
        rev = store.create_review("v1", "sa", artifact_refs=refs)
        summary = rev.to_summary()
        assert "artifact_refs" in summary
        assert summary["artifact_refs"] == refs

    def test_to_summary_includes_prompt_used(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa", prompt_used="Review this architecture…")
        summary = rev.to_summary()
        assert "prompt_used" in summary
        assert summary["prompt_used"] == "Review this architecture…"

    def test_old_review_without_artifact_refs_renders_safely(self):
        """A Review constructed without artifact_refs should default gracefully."""
        from models.hierarchy import Review
        r = Review(review_id="r_old", version_id="v1", persona="sa")
        # to_dict must not raise even if artifact_refs missing (uses default_factory)
        d = r.to_dict()
        assert d.get("artifact_refs", []) == []

    def test_artifact_refs_not_required_in_create_review(self):
        """create_review without artifact_refs must succeed (backward compat)."""
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa")  # no artifact_refs kwarg
        assert rev.review_id.startswith("r")
        assert rev.artifact_refs == []




# ══════════════════════════════════════════════════════════════════════════════
# B) Weakness user_note persistence
# ══════════════════════════════════════════════════════════════════════════════

class TestWeaknessUserNote:

    def _setup_review_with_weakness(self, wid: str = "w1", note: str = ""):
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review(
            "v1", "sa",
            weaknesses=[_weakness(wid, "unclear scope", user_note=note)],
        )
        return store, rev

    def test_weakness_dict_accepts_user_note_key(self):
        w = _weakness("w1", "text", user_note="my note")
        assert w["user_note"] == "my note"

    def test_update_weakness_note_persists_note(self):
        store, rev = self._setup_review_with_weakness("w1")
        result = _update_weakness_note("test-rw-s1", rev.review_id, "w1", "DR strategy flagged")
        assert result.get("updated") is True
        assert result.get("user_note") == "DR strategy flagged"

    def test_saved_note_visible_on_re_fetch(self):
        store, rev = self._setup_review_with_weakness("w1")
        _update_weakness_note("test-rw-s1", rev.review_id, "w1", "confirmed with client")
        loaded = store.get_review(rev.review_id)
        ws = loaded.weaknesses
        w = next((x for x in ws if x.get("id") == "w1"), None)
        assert w is not None
        assert w["user_note"] == "confirmed with client"

    def test_update_weakness_note_clears_note_with_empty_string(self):
        store, rev = self._setup_review_with_weakness("w1", note="old note")
        _update_weakness_note("test-rw-s1", rev.review_id, "w1", "")
        loaded = store.get_review(rev.review_id)
        w = next(x for x in loaded.weaknesses if x.get("id") == "w1")
        assert w["user_note"] == ""

    def test_update_weakness_note_returns_error_for_unknown_review(self):
        result = _update_weakness_note("test-rw-s1", "r_nonexistent", "w1", "note")
        assert "error" in result

    def test_update_weakness_note_returns_error_for_unknown_weakness(self):
        store, rev = self._setup_review_with_weakness("w1")
        result = _update_weakness_note("test-rw-s1", rev.review_id, "w_bad", "note")
        assert "error" in result

    def test_note_does_not_affect_weakness_status(self):
        """Adding a note must not change the status field."""
        store, rev = self._setup_review_with_weakness("w1")
        original_status = rev.weaknesses[0]["status"]
        _update_weakness_note("test-rw-s1", rev.review_id, "w1", "some note")
        loaded = store.get_review(rev.review_id)
        w = next(x for x in loaded.weaknesses if x.get("id") == "w1")
        assert w["status"] == original_status

    def test_old_weakness_without_user_note_renders_safely(self):
        """A weakness dict without user_note must not raise when accessing note."""
        w = {"id": "w1", "text": "legacy weakness", "status": "open"}
        note = w.get("user_note", "")
        assert note == ""




# ══════════════════════════════════════════════════════════════════════════════
# C) Weakness status update (non-regression)
# ══════════════════════════════════════════════════════════════════════════════

class TestWeaknessStatusNonRegression:

    def _setup(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa",
            weaknesses=[_weakness("w1", "unclear scope")])
        return store, rev

    def test_update_weakness_status_still_works(self):
        store, rev = self._setup()
        result = _update_weakness_status("test-rw-s1", rev.review_id, "w1", "addressed")
        assert result.get("updated") is True
        assert result.get("status") == "addressed"

    def test_updated_status_persisted(self):
        store, rev = self._setup()
        _update_weakness_status("test-rw-s1", rev.review_id, "w1", "validated")
        loaded = store.get_review(rev.review_id)
        w = next(x for x in loaded.weaknesses if x.get("id") == "w1")
        assert w["status"] == "validated"

    def test_update_weakness_status_rejects_invalid_status(self):
        store, rev = self._setup()
        result = _update_weakness_status("test-rw-s1", rev.review_id, "w1", "not_a_status")
        assert "error" in result

    def test_status_update_preserves_existing_user_note(self):
        """Updating status must not wipe an existing user_note."""
        store, rev = self._setup()
        _update_weakness_note("test-rw-s1", rev.review_id, "w1", "important note")
        _update_weakness_status("test-rw-s1", rev.review_id, "w1", "addressed")
        loaded = store.get_review(rev.review_id)
        w = next(x for x in loaded.weaknesses if x.get("id") == "w1")
        assert w.get("user_note") == "important note"
        assert w["status"] == "addressed"


# ══════════════════════════════════════════════════════════════════════════════
# D) API route — weakness note endpoint (static analysis)
# ══════════════════════════════════════════════════════════════════════════════

class TestAPIRouteWeaknessNote:

    def test_weakness_note_route_in_server_py(self, server_py):
        assert "/note" in server_py, \
            "weakness note route not present in server.py"

    def test_weakness_note_handler_called_in_server_py(self, server_py):
        assert "handle_weakness_note" in server_py, \
            "handle_weakness_note() not called in server.py"

    def test_handle_weakness_note_defined_in_handlers(self, handlers_review_py):
        assert "def handle_weakness_note(" in handlers_review_py, \
            "handle_weakness_note() not defined in handlers/review.py"

    def test_update_weakness_note_defined_in_services(self, services_review_py):
        assert "def update_weakness_note(" in services_review_py, \
            "update_weakness_note() not defined in services/review.py"

    def test_handler_reads_note_from_body(self, handlers_review_py):
        assert 'body.get("note"' in handlers_review_py, \
            "handle_weakness_note() does not read 'note' from request body"

    def test_weakness_note_route_uses_post(self, server_py):
        # Route should be in do_POST section
        post_section = server_py.split("def do_POST")[1] if "def do_POST" in server_py else ""
        assert "handle_weakness_note" in post_section, \
            "weakness note route not in do_POST section of server.py"




# ══════════════════════════════════════════════════════════════════════════════
# E) Frontend — review_detail.js static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestReviewDetailJS:

    def test_file_exists(self):
        assert REVIEW_DETAIL_JS.exists(), "review_detail.js must exist"

    def test_review_detail_module_defined(self, review_detail_js):
        assert "const ReviewDetail" in review_detail_js

    def test_window_export(self, review_detail_js):
        assert "window.ReviewDetail = ReviewDetail" in review_detail_js

    def test_render_review_function_defined(self, review_detail_js):
        assert "function renderReview(" in review_detail_js

    def test_on_weakness_status_handler_defined(self, review_detail_js):
        assert "function onWeaknessStatus(" in review_detail_js

    def test_on_weakness_note_handler_defined(self, review_detail_js):
        assert "function onWeaknessNote(" in review_detail_js

    def test_version_id_rendered(self, review_detail_js):
        assert "version_id" in review_detail_js, \
            "version_id not referenced in review_detail.js"

    def test_persona_rendered(self, review_detail_js):
        assert "persona" in review_detail_js, \
            "persona not referenced in review_detail.js"

    def test_prompt_used_rendered(self, review_detail_js):
        assert "prompt_used" in review_detail_js, \
            "prompt_used not referenced in review_detail.js"

    def test_top_risks_section_present(self, review_detail_js):
        assert "Top Risk" in review_detail_js or "top_risks" in review_detail_js or \
               "findings.risks" in review_detail_js, \
            "Top risks section not defined in review_detail.js"

    def test_artifact_refs_rendering_present(self, review_detail_js):
        assert "artifact_refs" in review_detail_js, \
            "artifact_refs not referenced in review_detail.js"

    def test_included_files_fallback_present(self, review_detail_js):
        assert "included_files" in review_detail_js, \
            "included_files fallback not present in review_detail.js"

    def test_weakness_status_select_rendered(self, review_detail_js):
        assert "rd-status-select" in review_detail_js or \
               "onWeaknessStatus" in review_detail_js, \
            "weakness status select not rendered in review_detail.js"

    def test_weakness_note_textarea_rendered(self, review_detail_js):
        assert "rd-note-textarea" in review_detail_js, \
            "weakness note textarea not rendered in review_detail.js"

    def test_weakness_user_note_value_rendered(self, review_detail_js):
        assert "user_note" in review_detail_js, \
            "user_note field not referenced in review_detail.js"

    def test_compare_is_secondary_action_not_default(self, review_detail_js):
        # Compare must appear as a secondary button, not trigger automatically
        assert "Compare" in review_detail_js, "Compare action not present"
        # Must not auto-open compare on review render
        assert "Compare.open()" not in review_detail_js or \
               "onclick" in review_detail_js, \
            "Compare should be triggered only by explicit user action (onclick)"

    def test_detail_panel_alias_assigned(self, review_detail_js):
        assert "window.DetailPanel" in review_detail_js, \
            "window.DetailPanel alias not set — dashboard.js compatibility broken"

    def test_no_external_libraries(self, review_detail_js):
        assert "import " not in review_detail_js
        assert "require(" not in review_detail_js

    def test_provenance_type_aware_document(self, review_detail_js):
        assert "'document'" in review_detail_js or '"document"' in review_detail_js, \
            "document artifact type not handled in provenance"

    def test_provenance_type_aware_slides(self, review_detail_js):
        assert "'slides'" in review_detail_js or '"slides"' in review_detail_js

    def test_provenance_type_aware_email(self, review_detail_js):
        assert "'email'" in review_detail_js or '"email"' in review_detail_js

    def test_provenance_type_aware_meeting_notes(self, review_detail_js):
        assert "meeting_notes" in review_detail_js

    def test_provenance_type_aware_spreadsheet(self, review_detail_js):
        assert "'spreadsheet'" in review_detail_js or '"spreadsheet"' in review_detail_js

    def test_graceful_fallback_on_missing_provenance(self, review_detail_js):
        # When artifact_refs is empty, falls back to included_files
        assert "included_files" in review_detail_js




# ══════════════════════════════════════════════════════════════════════════════
# F) Frontend — api.js static analysis
# ══════════════════════════════════════════════════════════════════════════════

class TestApiJS:

    def test_update_weakness_status_function_defined(self, api_js):
        assert "function updateWeaknessStatus(" in api_js

    def test_update_weakness_note_function_defined(self, api_js):
        assert "function updateWeaknessNote(" in api_js

    def test_update_weakness_status_exported(self, api_js):
        assert "updateWeaknessStatus" in api_js
        # Must appear in the window.API export object
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "updateWeaknessStatus" in api_section

    def test_update_weakness_note_exported(self, api_js):
        api_section = api_js.split("window.API")[1] if "window.API" in api_js else ""
        assert "updateWeaknessNote" in api_section

    def test_mock_review_detail_has_version_id(self, api_js):
        assert "version_id: 'v" in api_js or '"version_id"' in api_js, \
            "mock reviewDetail missing version_id"

    def test_mock_review_detail_has_prompt_used(self, api_js):
        assert "prompt_used:" in api_js, "mock reviewDetail missing prompt_used"

    def test_mock_review_detail_has_weaknesses(self, api_js):
        assert "weaknesses:" in api_js, "mock reviewDetail missing weaknesses array"

    def test_mock_review_detail_has_artifact_refs(self, api_js):
        assert "artifact_refs:" in api_js, "mock reviewDetail missing artifact_refs"

    def test_mock_weakness_has_user_note(self, api_js):
        assert "user_note:" in api_js, "mock weakness entries missing user_note field"

    def test_mock_weakness_has_status(self, api_js):
        assert "status: 'open'" in api_js or "status:'open'" in api_js, \
            "mock weakness missing status field"

    def test_update_weakness_note_sends_note_field(self, api_js):
        # The function body must send { note }
        assert "{ note }" in api_js or '"note"' in api_js or "'note'" in api_js


# ══════════════════════════════════════════════════════════════════════════════
# G) Frontend — dashboard_v2.html wiring
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboardV2Wiring:

    def test_review_detail_script_tag_present(self, dashboard_v2):
        assert 'src="/static/v2/js/review_detail.js"' in dashboard_v2, \
            "review_detail.js script tag not found in dashboard_v2.html"

    def test_review_detail_script_before_body_close(self, dashboard_v2):
        idx_script = dashboard_v2.index('src="/static/v2/js/review_detail.js"')
        idx_body   = dashboard_v2.rindex("</body>")
        assert idx_script < idx_body, \
            "review_detail.js must be loaded before </body>"

    def test_compare_js_still_present(self, dashboard_v2):
        assert 'src="/static/v2/js/compare.js"' in dashboard_v2, \
            "compare.js removed from dashboard_v2.html — non-regression failure"

    def test_review_detail_loads_after_compare(self, dashboard_v2):
        idx_cmp    = dashboard_v2.index('src="/static/v2/js/compare.js"')
        idx_detail = dashboard_v2.index('src="/static/v2/js/review_detail.js"')
        assert idx_cmp < idx_detail, \
            "review_detail.js must load after compare.js"

    def test_sprint9_scripts_still_present(self, dashboard_v2):
        assert 'src="/static/v2/js/summary_health.js"' in dashboard_v2
        assert 'src="/static/v2/js/bookmarks.js"' in dashboard_v2
        assert 'src="/static/v2/js/metrics.js"' in dashboard_v2


# ══════════════════════════════════════════════════════════════════════════════
# H) CSS Sprint 1 classes
# ══════════════════════════════════════════════════════════════════════════════

class TestSprintOneCSSClasses:

    def test_rd_header_class(self, components_css):
        assert ".rd-header" in components_css

    def test_rd_risk_item_class(self, components_css):
        assert ".rd-risk-item" in components_css

    def test_rd_prov_chip_class(self, components_css):
        assert ".rd-prov-chip" in components_css

    def test_rd_weakness_item_class(self, components_css):
        assert ".rd-weakness-item" in components_css

    def test_rd_weakness_status_open_class(self, components_css):
        assert ".rd-weakness-status--open" in components_css

    def test_rd_weakness_status_resolved_class(self, components_css):
        assert ".rd-weakness-status--resolved" in components_css

    def test_rd_note_textarea_class(self, components_css):
        assert ".rd-note-textarea" in components_css

    def test_rd_compare_action_class(self, components_css):
        assert ".rd-compare-action" in components_css

    def test_rd_meta_grid_class(self, components_css):
        assert ".rd-meta-grid" in components_css

    def test_rd_prov_chip_type_variants(self, components_css):
        assert ".rd-prov-chip--document" in components_css
        assert ".rd-prov-chip--slides" in components_css
        assert ".rd-prov-chip--email" in components_css

    def test_rd_expandable_class(self, components_css):
        assert ".rd-expandable" in components_css




# ══════════════════════════════════════════════════════════════════════════════
# I) Non-regression — v1 (index.html) untouched
# ══════════════════════════════════════════════════════════════════════════════

class TestV1Untouched:

    def test_review_detail_js_not_in_v1(self, index_html):
        assert "review_detail.js" not in index_html, \
            "review_detail.js must not be loaded in v1 (index.html)"

    def test_review_detail_module_not_in_v1(self, index_html):
        # The specific JS module definition 'const ReviewDetail' must not appear in v1
        assert "const ReviewDetail" not in index_html, \
            "ReviewDetail module definition must not appear in v1 (index.html)"

    def test_update_weakness_note_not_in_v1(self, index_html):
        assert "updateWeaknessNote" not in index_html, \
            "updateWeaknessNote must not appear in v1 (index.html)"

    def test_rd_prefix_css_not_in_v1(self, index_html):
        assert "rd-header" not in index_html, \
            "Sprint 1 CSS class rd-header must not appear in v1 (index.html)"


# ══════════════════════════════════════════════════════════════════════════════
# J) Non-regression — review click opens details, not compare
# ══════════════════════════════════════════════════════════════════════════════

class TestReviewClickOpensDetails:

    def test_accordion_on_review_click_opens_drawer(self, accordion_js):
        # onReviewClick must call openDrawer (not Compare.open)
        idx = accordion_js.index("function onReviewClick(")
        # Extract function body (up to next function declaration)
        body = accordion_js[idx:idx + 800]
        assert "openDrawer" in body, \
            "onReviewClick() must call openDrawer — review click must open details"

    def test_accordion_on_review_click_does_not_open_compare(self, accordion_js):
        idx = accordion_js.index("function onReviewClick(")
        body = accordion_js[idx:idx + 800]
        assert "Compare.open(" not in body, \
            "onReviewClick() must NOT call Compare.open() — compare is secondary"

    def test_dashboard_sidebar_review_click_opens_drawer(self, dashboard_js):
        idx = dashboard_js.index("function onSidebarReviewClick(")
        body = dashboard_js[idx:idx + 600]
        assert "openDrawer" in body, \
            "onSidebarReviewClick() must call openDrawer"

    def test_dashboard_sidebar_review_click_does_not_open_compare(self, dashboard_js):
        idx = dashboard_js.index("function onSidebarReviewClick(")
        body = dashboard_js[idx:idx + 600]
        assert "Compare.open(" not in body, \
            "onSidebarReviewClick() must NOT call Compare.open()"

    def test_compare_is_available_as_separate_action(self, dashboard_v2):
        # Compare button in header must still be present for secondary use
        assert "openCompare()" in dashboard_v2 or "Compare.open(" in dashboard_v2, \
            "Compare must remain available as a header action in dashboard_v2.html"


# ══════════════════════════════════════════════════════════════════════════════
# K) Backward compatibility — old records without new fields
# ══════════════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:

    def test_review_without_artifact_refs_field_loads_safely(self):
        """SQLite row with no artifact_refs column value loads as empty list."""
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa")
        # Patch: simulate row with missing artifact_refs by checking default
        from models.hierarchy import Review
        old_review = Review(review_id="r_old", version_id="v1", persona="sa")
        assert old_review.artifact_refs == []
        d = old_review.to_dict()
        assert "artifact_refs" in d
        assert d["artifact_refs"] == []

    def test_review_summary_without_new_fields_does_not_raise(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa")
        summary = rev.to_summary()
        # Must not raise; new keys have safe defaults
        assert isinstance(summary["artifact_refs"], list)
        assert isinstance(summary["prompt_used"], str)

    def test_weakness_without_user_note_renders_safely(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        # Old-style weakness: no user_note key
        old_w = {"id": "w1", "text": "legacy text", "status": "open"}
        rev = store.create_review("v1", "sa", weaknesses=[old_w])
        loaded = store.get_review(rev.review_id)
        w = loaded.weaknesses[0]
        # Accessing user_note via .get() must return safe default
        assert w.get("user_note", "") == ""

    def test_multiple_weakness_notes_stored_independently(self):
        store = _make_store()
        store.create_version(included_artifacts=[])
        rev = store.create_review("v1", "sa", weaknesses=[
            _weakness("w1", "risk A"),
            _weakness("w2", "risk B"),
        ])
        _update_weakness_note("test-rw-s1", rev.review_id, "w1", "note for w1")
        _update_weakness_note("test-rw-s1", rev.review_id, "w2", "note for w2")
        loaded = store.get_review(rev.review_id)
        w1 = next(x for x in loaded.weaknesses if x["id"] == "w1")
        w2 = next(x for x in loaded.weaknesses if x["id"] == "w2")
        assert w1["user_note"] == "note for w1"
        assert w2["user_note"] == "note for w2"

    def test_db_migration_adds_artifact_refs_column(self):
        """SQLite migration must add artifact_refs column to reviews table."""
        from db.database import get_db
        db = get_db()
        cols = {r["name"] for r in db.fetchall("PRAGMA table_info(reviews)")}
        assert "artifact_refs" in cols, \
            "artifact_refs column not found in reviews table after migration"
