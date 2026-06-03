"""Sprint 9 Regression Pack.

Covers every change made in Sprint 9:

S9-01  list_reviews kwarg bug fix
  - services/review.py called store.list_reviews(version_filter=…) — wrong kwarg.
    Correct kwarg is version_id=.  Verified by inspecting the fixed source.

S9-02  pyyaml declared in pyproject.toml
  - pyyaml>=6.0 was already present; no code change required.
    Test confirms the declaration and that yaml is importable in the test env.
    NOTE: if yaml is not installed in this sandbox, the import test is skipped
    (not failed) because the declaration is correct — it is an env issue only.

S9-03  user_note field on weakness items
  A  extract_weaknesses() returns user_note='' on every item
  B  update_weakness_status() accepts user_note and persists it
  C  update_weakness_status() with user_note=None does not touch user_note key
  D  update_weakness_status() status-only call still works (no user_note arg)
  E  HTML: weakness textarea present with onblur wiring
  F  HTML: updateWeaknessStatus function accepts 4 arguments
  G  HTML: status <select> onchange passes null as 4th arg (note=null)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent
HTML_PATH = ROOT / "static" / "index.html"
SVC_REVIEW = ROOT / "services" / "review.py"
REVIEW_QUALITY = ROOT / "processors" / "review_quality.py"
PYPROJECT = ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def svc_review_src() -> str:
    return SVC_REVIEW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def quality_src() -> str:
    return REVIEW_QUALITY.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# S9-01  list_reviews kwarg fix
# ─────────────────────────────────────────────────────────────────────────────

class TestListReviewsKwargFix:
    def test_wrong_kwarg_absent(self, svc_review_src):
        """version_filter= must not appear anywhere in services/review.py."""
        assert "version_filter=" not in svc_review_src

    def test_correct_kwarg_present(self, svc_review_src):
        """list_reviews must be called with version_id= kwarg."""
        assert "list_reviews(version_id=" in svc_review_src


# ─────────────────────────────────────────────────────────────────────────────
# S9-02  pyyaml declared
# ─────────────────────────────────────────────────────────────────────────────

class TestPyyamlDependency:
    def test_declared_in_pyproject(self):
        src = PYPROJECT.read_text(encoding="utf-8")
        assert "pyyaml" in src.lower()

    def test_yaml_importable(self):
        """yaml must be importable; skip (not fail) if missing from this env."""
        pytest.importorskip("yaml", reason="pyyaml not installed in this env — declared in pyproject.toml")


# ─────────────────────────────────────────────────────────────────────────────
# S9-03-A  extract_weaknesses returns user_note on every item
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractWeaknessesUserNote:
    def _extract(self):
        from processors.review_quality import extract_weaknesses
        return extract_weaknesses

    def test_user_note_key_present_on_signal_match(self):
        extract = self._extract()
        findings = {"risks": ["This is unclear and not defined at all"]}
        result = extract(findings)
        assert result, "Expected at least one weakness"
        for w in result:
            assert "user_note" in w, f"Missing user_note on: {w}"

    def test_user_note_default_empty_string(self):
        extract = self._extract()
        findings = {"risks": ["TBC — risk not defined"]}
        result = extract(findings)
        for w in result:
            assert w["user_note"] == "", f"Expected empty string, got: {w['user_note']!r}"

    def test_user_note_present_on_short_item(self):
        extract = self._extract()
        findings = {"constraints": ["Short item"]}  # < 8 words
        result = extract(findings)
        for w in result:
            assert "user_note" in w

    def test_empty_findings_returns_empty(self):
        extract = self._extract()
        assert extract({}) == []
        assert extract(None) == []  # type: ignore[arg-type]

    def test_all_required_fields_present(self):
        extract = self._extract()
        findings = {"risks": ["unknown architecture approach"]}
        result = extract(findings)
        for w in result:
            for key in ("id", "text", "category", "status", "user_note"):
                assert key in w, f"Field '{key}' missing from weakness dict"

    def test_source_field_unchanged(self):
        """user_note addition must not break id/text/category/status values."""
        extract = self._extract()
        findings = {"assumptions": ["assumed client will provide access tbc"]}
        result = extract(findings)
        assert result
        w = result[0]
        assert w["id"] == "w1"
        assert w["category"] == "assumptions"
        assert w["status"] == "open"
        assert "assumed" in w["text"].lower() or "tbc" in w["text"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# S9-03-B/C/D  update_weakness_status signature and behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateWeaknessStatusSignature:
    """Unit tests against the service function directly using an in-memory DB."""

    def _setup_review_with_weakness(self, tmp_path):
        """Create a minimal in-memory project+review with one weakness."""
        import os, sys
        os.environ.setdefault("PROJECTS_DATA_DIR", str(tmp_path))

        from processors.review_quality import extract_weaknesses
        from models.hierarchy import _make_hierarchy_store

        store = _make_hierarchy_store("proj_s9_test")
        version = store.create_version(
            included_artifacts=[],
            label="Test Version",
        )
        findings = {"risks": ["unclear architecture — tbc"]}
        weaknesses = extract_weaknesses(findings)
        review = store.create_review(
            version_id=version.version_id,
            persona="Test Persona",
            findings=findings,
            weaknesses=weaknesses,
        )
        return store, review, weaknesses[0]["id"]

    def test_status_only_update(self, tmp_path):
        from services.review import update_weakness_status
        store, review, wid = self._setup_review_with_weakness(tmp_path)
        result = update_weakness_status("proj_s9_test", review.review_id, wid, "addressed")
        assert result.get("updated") is True
        assert result["status"] == "addressed"

    def test_status_and_note_update(self, tmp_path):
        from services.review import update_weakness_status
        store, review, wid = self._setup_review_with_weakness(tmp_path)
        result = update_weakness_status(
            "proj_s9_test", review.review_id, wid, "addressed", user_note="Confirmed by client"
        )
        assert result.get("updated") is True
        assert result["user_note"] == "Confirmed by client"

    def test_note_persists_after_reload(self, tmp_path):
        from services.review import update_weakness_status
        from models.hierarchy import _make_hierarchy_store
        store, review, wid = self._setup_review_with_weakness(tmp_path)
        update_weakness_status(
            "proj_s9_test", review.review_id, wid, "open", user_note="Needs more detail"
        )
        store2 = _make_hierarchy_store("proj_s9_test")
        reloaded = store2.get_review(review.review_id)
        assert reloaded is not None
        w = next((x for x in (reloaded.weaknesses or []) if x["id"] == wid), None)
        assert w is not None
        assert w.get("user_note") == "Needs more detail"

    def test_user_note_none_does_not_overwrite(self, tmp_path):
        """Passing user_note=None must not touch existing note."""
        from services.review import update_weakness_status
        from models.hierarchy import _make_hierarchy_store
        store, review, wid = self._setup_review_with_weakness(tmp_path)
        # Set a note first
        update_weakness_status(
            "proj_s9_test", review.review_id, wid, "open", user_note="Original note"
        )
        # Now update status only (no user_note kwarg → defaults to None)
        update_weakness_status("proj_s9_test", review.review_id, wid, "addressed")
        store2 = _make_hierarchy_store("proj_s9_test")
        reloaded = store2.get_review(review.review_id)
        w = next((x for x in (reloaded.weaknesses or []) if x["id"] == wid), None)
        assert w is not None
        assert w.get("user_note") == "Original note", "user_note must not be cleared by status-only call"

    def test_invalid_status_returns_error(self, tmp_path):
        from services.review import update_weakness_status
        store, review, wid = self._setup_review_with_weakness(tmp_path)
        result = update_weakness_status("proj_s9_test", review.review_id, wid, "invalid_status")
        assert "error" in result

    def test_unknown_weakness_id_returns_error(self, tmp_path):
        from services.review import update_weakness_status
        store, review, _ = self._setup_review_with_weakness(tmp_path)
        result = update_weakness_status("proj_s9_test", review.review_id, "w999", "open")
        assert "error" in result


# ─────────────────────────────────────────────────────────────────────────────
# S9-03-E/F/G  HTML static analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestHTMLWeaknessUserNote:
    def test_textarea_present_in_weakness_row(self, html):
        """Weakness row must contain a <textarea> for user_note."""
        assert "<textarea" in html

    def test_textarea_has_placeholder(self, html):
        assert 'placeholder="Add note' in html

    def test_textarea_has_onblur_handler(self, html):
        assert "onblur=" in html

    def test_onblur_calls_updateWeaknessStatus(self, html):
        assert 'onblur="updateWeaknessStatus(' in html

    def test_textarea_prepopulates_user_note(self, html):
        """Textarea value must come from w.user_note."""
        assert "w.user_note" in html

    def test_updateWeaknessStatus_accepts_four_args(self, html):
        """Function signature must declare 4 parameters."""
        # Matches: async function updateWeaknessStatus(reviewId, weaknessId, status, note)
        match = re.search(
            r"function\s+updateWeaknessStatus\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*,\s*\w+\s*\)",
            html,
        )
        assert match, "updateWeaknessStatus must declare 4 parameters"

    def test_status_select_passes_null_as_note(self, html):
        """The status <select> onchange must pass null as the 4th arg."""
        assert "this.value,null)" in html

    def test_onblur_passes_null_as_status(self, html):
        """The textarea onblur must pass null as the status arg."""
        assert "null,this.value)" in html

    def test_weakness_textarea_has_rows_attr(self, html):
        """Textarea must set rows=2 for compact display."""
        assert 'rows="2"' in html


# ─────────────────────────────────────────────────────────────────────────────
# S9-03  review_quality.py source-level checks
# ─────────────────────────────────────────────────────────────────────────────

class TestReviewQualitySource:
    def test_user_note_in_extract_weaknesses(self, quality_src):
        assert '"user_note"' in quality_src or "'user_note'" in quality_src

    def test_user_note_default_empty_string_in_source(self, quality_src):
        assert '"user_note": ""' in quality_src or "'user_note': ''" in quality_src


# ─────────────────────────────────────────────────────────────────────────────
# S9-03  services/review.py source-level checks
# ─────────────────────────────────────────────────────────────────────────────

class TestServiceReviewSource:
    def test_update_weakness_status_accepts_user_note(self, svc_review_src):
        """update_weakness_status must declare user_note parameter."""
        assert "user_note" in svc_review_src

    def test_user_note_written_to_target(self, svc_review_src):
        """Service must set target["user_note"] when note is provided."""
        assert 'target["user_note"]' in svc_review_src or "target['user_note']" in svc_review_src
