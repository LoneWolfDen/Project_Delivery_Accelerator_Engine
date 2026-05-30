"""Sprint 2 Regression Pack — Prompt Builder Foundation.

Covers:
  S2-02  prompt_builder_state persisted per review and returned by API
         (schema migration, dataclass field, store create/fetch, to_dict, to_summary)
  S2-03  Baseline vs Customised badge logic
         (pure helper function tested without a browser)

All tests use an isolated temp directory via PROJECTS_DATA_DIR.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Fresh temp dir + reset DB thread-local for every test."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    import threading

    import db.database as _db

    _db._BASE_DIR = tmp_path
    _db._thread_local = threading.local()
    yield


@pytest.fixture()
def store():
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite("proj-s2")


@pytest.fixture()
def version(store):
    return store.create_version(
        included_artifacts=[{"filename": "spec.md", "category": "scope"}],
        label="v1",
    )


# ── S2-02: prompt_builder_state schema and persistence ───────────────────────

class TestPromptBuilderStateSchema:
    """prompt_builder_state column is present and correctly typed."""

    def test_column_exists_in_schema(self):
        from db.database import get_db
        db = get_db()
        cols = {r[1] for r in db.execute("PRAGMA table_info(reviews)").fetchall()}
        assert "prompt_builder_state" in cols

    def test_column_default_is_null(self, store, version):
        """Reviews created without prompt_builder_state store NULL."""
        r = store.create_review(version_id=version.version_id, persona="SA")
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state is None

    def test_dataclass_field_exists(self):
        from models.hierarchy import Review
        assert "prompt_builder_state" in Review.__dataclass_fields__

    def test_dataclass_field_default_is_none(self):
        from models.hierarchy import Review
        r = Review()
        assert r.prompt_builder_state is None


class TestPromptBuilderStatePersistence:
    """prompt_builder_state survives the full write → read cycle."""

    def test_create_review_with_injected_questions(self, store, version):
        pbs = {"injected_questions": ["What is DR strategy?", "Any cost ceiling?"],
               "user_notes": ""}
        r = store.create_review(
            version_id=version.version_id,
            persona="Solution Architect",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state == pbs
        assert fetched.prompt_builder_state["injected_questions"] == [
            "What is DR strategy?", "Any cost ceiling?"
        ]

    def test_create_review_with_user_notes(self, store, version):
        pbs = {"injected_questions": [], "user_notes": "Budget cap £500K. AWS only."}
        r = store.create_review(
            version_id=version.version_id,
            persona="Delivery Manager",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state["user_notes"] == "Budget cap £500K. AWS only."

    def test_create_review_with_both_sections(self, store, version):
        pbs = {
            "injected_questions": ["Q1?", "Q2?"],
            "user_notes": "3 senior engineers available.",
        }
        r = store.create_review(
            version_id=version.version_id,
            persona="SA",
            prompt_builder_state=pbs,
        )
        fetched = store.get_review(r.review_id)
        assert len(fetched.prompt_builder_state["injected_questions"]) == 2
        assert fetched.prompt_builder_state["user_notes"] == "3 senior engineers available."

    def test_null_pbs_does_not_raise(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=None)
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state is None

    def test_pbs_questions_order_preserved(self, store, version):
        questions = ["Q3?", "Q1?", "Q2?"]
        pbs = {"injected_questions": questions, "user_notes": ""}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state["injected_questions"] == questions

    def test_pbs_empty_questions_list(self, store, version):
        pbs = {"injected_questions": [], "user_notes": "some notes"}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        fetched = store.get_review(r.review_id)
        assert fetched.prompt_builder_state["injected_questions"] == []
        assert fetched.prompt_builder_state["user_notes"] == "some notes"


class TestPromptBuilderStateInAPISurfaces:
    """prompt_builder_state appears in to_dict() and to_summary() outputs."""

    def test_pbs_in_to_dict(self, store, version):
        pbs = {"injected_questions": ["Q?"], "user_notes": "ctx"}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        d = store.get_review(r.review_id).to_dict()
        assert "prompt_builder_state" in d
        assert d["prompt_builder_state"]["injected_questions"] == ["Q?"]

    def test_null_pbs_in_to_dict(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        d = store.get_review(r.review_id).to_dict()
        assert d["prompt_builder_state"] is None

    def test_pbs_in_to_summary(self, store, version):
        pbs = {"injected_questions": ["What DR?"], "user_notes": ""}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        s = store.get_review(r.review_id).to_summary()
        assert "prompt_builder_state" in s
        assert s["prompt_builder_state"]["injected_questions"] == ["What DR?"]

    def test_null_pbs_in_to_summary(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        s = store.get_review(r.review_id).to_summary()
        assert s["prompt_builder_state"] is None

    def test_pbs_in_list_reviews(self, store, version):
        pbs = {"injected_questions": ["Q?"], "user_notes": "notes"}
        store.create_review(version_id=version.version_id, persona="SA",
                            prompt_builder_state=pbs)
        summaries = store.list_reviews(version_id=version.version_id)
        assert summaries[0]["prompt_builder_state"] == pbs

    def test_old_reviews_return_null_pbs_in_list(self, store, version):
        """Reviews created without pbs must return None in list_reviews() — no error."""
        store.create_review(version_id=version.version_id, persona="SA")
        summaries = store.list_reviews(version_id=version.version_id)
        assert summaries[0]["prompt_builder_state"] is None

    def test_mixed_reviews_pbs_and_null(self, store, version):
        """List containing both baseline and customised reviews returns correct pbs."""
        pbs = {"injected_questions": ["Q1?"], "user_notes": ""}
        store.create_review(version_id=version.version_id, persona="SA")  # baseline
        store.create_review(version_id=version.version_id, persona="DM",
                            prompt_builder_state=pbs)  # customised
        by_id = {s["review_id"]: s["prompt_builder_state"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id["r1"] is None
        assert by_id["r2"] == pbs


# ── S2-03: Baseline vs Customised badge logic ─────────────────────────────────

def _badge_is_customised(pbs) -> bool:
    """Mirror the exact JS badge logic in Python for unit testing:
       customised = pbs exists AND (injected_questions non-empty OR user_notes non-empty)
    """
    if not pbs:
        return False
    has_questions = bool((pbs.get("injected_questions") or []))
    has_notes = bool((pbs.get("user_notes") or "").strip())
    return has_questions or has_notes


class TestBaselineCustomisedBadgeLogic:
    """S2-03 — badge determination is correct for all pbs combinations."""

    # ── Baseline cases ────────────────────────────────────────────────────────

    def test_none_pbs_is_baseline(self):
        assert _badge_is_customised(None) is False

    def test_empty_dict_pbs_is_baseline(self):
        assert _badge_is_customised({}) is False

    def test_empty_questions_and_empty_notes_is_baseline(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": ""}) is False

    def test_whitespace_only_notes_is_baseline(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": "   "}) is False

    def test_none_notes_is_baseline(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": None}) is False

    # ── Customised cases ──────────────────────────────────────────────────────

    def test_one_injected_question_is_customised(self):
        assert _badge_is_customised({"injected_questions": ["Q?"], "user_notes": ""}) is True

    def test_multiple_injected_questions_is_customised(self):
        assert _badge_is_customised(
            {"injected_questions": ["Q1?", "Q2?", "Q3?"], "user_notes": ""}
        ) is True

    def test_non_empty_notes_is_customised(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": "notes"}) is True

    def test_both_questions_and_notes_is_customised(self):
        assert _badge_is_customised(
            {"injected_questions": ["Q?"], "user_notes": "Budget capped."}
        ) is True

    def test_notes_with_only_newlines_is_baseline(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": "\n\n"}) is False

    def test_notes_with_real_content_after_spaces_is_customised(self):
        assert _badge_is_customised({"injected_questions": [], "user_notes": "  real  "}) is True

    # ── Integration: badge logic matches stored pbs ───────────────────────────

    def test_stored_baseline_review_is_not_customised(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="SA")
        fetched = store.get_review(r.review_id)
        assert _badge_is_customised(fetched.prompt_builder_state) is False

    def test_stored_customised_review_is_customised(self, store, version):
        pbs = {"injected_questions": ["What is DR?"], "user_notes": "AWS only"}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        fetched = store.get_review(r.review_id)
        assert _badge_is_customised(fetched.prompt_builder_state) is True

    def test_stored_notes_only_review_is_customised(self, store, version):
        pbs = {"injected_questions": [], "user_notes": "Budget cap £500K"}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        fetched = store.get_review(r.review_id)
        assert _badge_is_customised(fetched.prompt_builder_state) is True

    def test_stored_questions_only_review_is_customised(self, store, version):
        pbs = {"injected_questions": ["Q?"], "user_notes": ""}
        r = store.create_review(version_id=version.version_id, persona="SA",
                                prompt_builder_state=pbs)
        fetched = store.get_review(r.review_id)
        assert _badge_is_customised(fetched.prompt_builder_state) is True
