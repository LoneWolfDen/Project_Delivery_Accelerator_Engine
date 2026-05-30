"""Sprint 1 Regression Pack — Foundation and Review Chain Stability.

Covers:
  S1-02  Explicit review chaining (previous_review_id stored and returned)
  S1-03  Iteration visibility (R1, R2, R3 labels from list_reviews)

All tests use an in-memory SQLite path via PROJECTS_DATA_DIR so they are
fully isolated and leave no files on disk.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point every test at a fresh temp directory so DBs never bleed across tests."""
    monkeypatch.setenv("PROJECTS_DATA_DIR", str(tmp_path))
    # Force db module to re-initialise its cached path on the next call.
    import db.database as _db
    _db._BASE_DIR = tmp_path
    # Clear thread-local connection cache so each test gets a fresh connection.
    import threading
    _db._thread_local = threading.local()
    yield


@pytest.fixture()
def store():
    """Return a fresh HierarchyStoreSQLite for project 'proj-s1'."""
    # Import after env is patched by isolated_db
    from db.hierarchy_store_sql import HierarchyStoreSQLite
    return HierarchyStoreSQLite("proj-s1")


@pytest.fixture()
def version(store):
    """Create and return a single version to attach reviews to."""
    return store.create_version(
        included_artifacts=[{"filename": "scope.txt", "category": "scope"}],
        label="Baseline",
    )


# ── S1-02: Explicit review chaining ──────────────────────────────────────────

class TestReviewChaining:
    """S1-02 — previous_review_id stored, persisted, and returned correctly."""

    def test_first_review_has_empty_previous(self, store, version):
        r = store.create_review(version_id=version.version_id, persona="Solution Architect")
        assert r.previous_review_id == ""

    def test_chained_review_stores_previous_review_id(self, store, version):
        r1 = store.create_review(version_id=version.version_id, persona="Solution Architect")
        r2 = store.create_review(
            version_id=version.version_id,
            persona="Delivery Manager",
            previous_review_id=r1.review_id,
        )
        assert r2.previous_review_id == r1.review_id

    def test_previous_review_id_survives_round_trip(self, store, version):
        """get_review() must return the persisted previous_review_id."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id,
            persona="DM",
            previous_review_id=r1.review_id,
        )
        fetched = store.get_review(r2.review_id)
        assert fetched is not None
        assert fetched.previous_review_id == r1.review_id

    def test_previous_review_id_in_to_dict(self, store, version):
        """to_dict() must expose previous_review_id."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id,
            persona="DM",
            previous_review_id=r1.review_id,
        )
        d = store.get_review(r2.review_id).to_dict()
        assert d["previous_review_id"] == r1.review_id

    def test_previous_review_id_in_to_summary(self, store, version):
        """to_summary() must expose previous_review_id."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id,
            persona="DM",
            previous_review_id=r1.review_id,
        )
        s = store.get_review(r2.review_id).to_summary()
        assert s["previous_review_id"] == r1.review_id

    def test_previous_review_id_in_list_reviews(self, store, version):
        """list_reviews() summaries must carry previous_review_id."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id,
            persona="DM",
            previous_review_id=r1.review_id,
        )
        summaries = {s["review_id"]: s for s in store.list_reviews(version_id=version.version_id)}
        assert summaries[r2.review_id]["previous_review_id"] == r1.review_id
        assert summaries[r1.review_id]["previous_review_id"] == ""

    def test_chain_across_three_reviews(self, store, version):
        """R1→R2→R3 — each links only to its direct predecessor."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(
            version_id=version.version_id, persona="DM",
            previous_review_id=r1.review_id,
        )
        r3 = store.create_review(
            version_id=version.version_id, persona="SA",
            previous_review_id=r2.review_id,
        )
        assert store.get_review(r3.review_id).previous_review_id == r2.review_id
        assert store.get_review(r2.review_id).previous_review_id == r1.review_id
        assert store.get_review(r1.review_id).previous_review_id == ""

    def test_existing_reviews_unaffected_by_migration(self, store, version):
        """Reviews created without previous_review_id default to empty string."""
        r = store.create_review(version_id=version.version_id, persona="SA")
        fetched = store.get_review(r.review_id)
        assert fetched.previous_review_id == ""

    def test_chained_review_different_version(self, store):
        """previous_review_id can reference a review on a different version."""
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        r1 = store.create_review(version_id=v1.version_id, persona="SA")
        r2 = store.create_review(
            version_id=v2.version_id, persona="DM",
            previous_review_id=r1.review_id,
        )
        fetched = store.get_review(r2.review_id)
        assert fetched.previous_review_id == r1.review_id

    def test_schema_column_exists(self, store):
        """The reviews table must have a previous_review_id column."""
        from db.database import get_db
        db = get_db()
        cols = {r[1] for r in db.execute("PRAGMA table_info(reviews)").fetchall()}
        assert "previous_review_id" in cols


# ── S1-03: Iteration visibility ───────────────────────────────────────────────

class TestIterationNumbers:
    """S1-03 — R1, R2, R3 labels computed per version from list_reviews()."""

    def test_first_review_is_r1(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        summaries = store.list_reviews(version_id=version.version_id)
        assert summaries[0]["iteration_number"] == 1

    def test_second_review_is_r2(self, store, version):
        store.create_review(version_id=version.version_id, persona="SA")
        store.create_review(version_id=version.version_id, persona="DM")
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id["r1"] == 1
        assert by_id["r2"] == 2

    def test_three_reviews_labelled_r1_r2_r3(self, store, version):
        for persona in ("SA", "DM", "EA"):
            store.create_review(version_id=version.version_id, persona=persona)
        by_id = {s["review_id"]: s["iteration_number"]
                 for s in store.list_reviews(version_id=version.version_id)}
        assert by_id["r1"] == 1
        assert by_id["r2"] == 2
        assert by_id["r3"] == 3

    def test_iteration_numbers_are_version_scoped(self, store):
        """Reviews on different versions each start at R1 independently."""
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        store.create_review(version_id=v1.version_id, persona="SA")  # r1
        store.create_review(version_id=v1.version_id, persona="DM")  # r2
        store.create_review(version_id=v2.version_id, persona="SA")  # r3 globally

        v1_revs = {s["review_id"]: s["iteration_number"]
                   for s in store.list_reviews(version_id=v1.version_id)}
        v2_revs = {s["review_id"]: s["iteration_number"]
                   for s in store.list_reviews(version_id=v2.version_id)}

        assert v1_revs["r1"] == 1
        assert v1_revs["r2"] == 2
        # r3 belongs to v2 and should be R1 within that version
        assert v2_revs["r3"] == 1

    def test_global_list_reviews_assigns_correct_iterations(self, store):
        """list_reviews() with no filter still computes per-version iteration numbers."""
        v1 = store.create_version(included_artifacts=[], label="v1")
        v2 = store.create_version(included_artifacts=[], label="v2")
        store.create_review(version_id=v1.version_id, persona="SA")
        store.create_review(version_id=v2.version_id, persona="DM")
        store.create_review(version_id=v1.version_id, persona="EA")

        all_revs = {s["review_id"]: s for s in store.list_reviews()}
        assert all_revs["r1"]["iteration_number"] == 1   # v1 R1
        assert all_revs["r2"]["iteration_number"] == 1   # v2 R1
        assert all_revs["r3"]["iteration_number"] == 2   # v1 R2

    def test_iteration_number_in_to_summary(self, store, version):
        """to_summary() exposes iteration_number key (may be 0 outside list_reviews)."""
        r = store.create_review(version_id=version.version_id, persona="SA")
        s = r.to_summary()
        assert "iteration_number" in s

    def test_list_reviews_returns_iteration_not_zero(self, store, version):
        """list_reviews() must not return 0 for any review in the result set."""
        store.create_review(version_id=version.version_id, persona="SA")
        store.create_review(version_id=version.version_id, persona="DM")
        for s in store.list_reviews(version_id=version.version_id):
            assert s["iteration_number"] > 0

    def test_delete_review_does_not_corrupt_remaining_iteration(self, store, version):
        """After deleting R2, R1 and R3 keep their computed iteration labels."""
        r1 = store.create_review(version_id=version.version_id, persona="SA")
        r2 = store.create_review(version_id=version.version_id, persona="DM")
        r3 = store.create_review(version_id=version.version_id, persona="EA")
        store.delete_review(r2.review_id)
        # After deletion, r1 and r3 remain; per-version ascending order preserved
        remaining = {s["review_id"]: s["iteration_number"]
                     for s in store.list_reviews(version_id=version.version_id)}
        assert r2.review_id not in remaining
        # r1 is still oldest → iteration 1, r3 is next → iteration 2
        assert remaining[r1.review_id] == 1
        assert remaining[r3.review_id] == 2
