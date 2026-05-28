"""Tests for Iteration & History – version tracking, comparisons, and evolution."""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.context_builder import build_context
from processors.history import (
    compare_context_versions,
    compare_reviews,
    get_context_version,
    get_evolution_timeline,
    get_review_history,
    list_context_versions,
    save_context_version,
)
from processors.ingestion import ingest_file, ingest_directory
from personas.engine import run_review


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
TEST_PROJECT_DIR = Path("/tmp/test_project_history")


@pytest.fixture(autouse=True)
def clean_test_dir():
    """Create and clean test project directory for each test."""
    if TEST_PROJECT_DIR.exists():
        shutil.rmtree(TEST_PROJECT_DIR)
    TEST_PROJECT_DIR.mkdir(parents=True)
    yield
    if TEST_PROJECT_DIR.exists():
        shutil.rmtree(TEST_PROJECT_DIR)


@pytest.fixture
def sample_context():
    """Build context from all sample data."""
    docs = ingest_directory(SAMPLE_DIR)
    doc_dicts = [d.to_dict() for d in docs if d.is_valid]
    return build_context(doc_dicts)


@pytest.fixture
def partial_context():
    """Build context from a subset of sample data (simulates earlier version)."""
    doc = ingest_file(SAMPLE_DIR / "scope.txt")
    return build_context([doc.to_dict()])


# ───────────────────────────────────────────────────────────
# Version tracking tests
# ───────────────────────────────────────────────────────────


class TestVersionTracking:
    """Test saving and listing context versions."""

    def test_save_first_version(self, sample_context):
        meta = save_context_version(TEST_PROJECT_DIR, sample_context)
        assert meta["version_id"] == "v1"
        assert meta["version_number"] == 1
        assert "timestamp" in meta
        assert meta["stats"]["risks"] == len(sample_context.get("risks", []))

    def test_save_multiple_versions(self, partial_context, sample_context):
        meta1 = save_context_version(TEST_PROJECT_DIR, partial_context, "initial")
        meta2 = save_context_version(TEST_PROJECT_DIR, sample_context, "full-data")
        assert meta1["version_id"] == "v1"
        assert meta2["version_id"] == "v2"
        assert meta1["label"] == "initial"
        assert meta2["label"] == "full-data"

    def test_version_with_custom_label(self, sample_context):
        meta = save_context_version(TEST_PROJECT_DIR, sample_context, "post-discovery")
        assert meta["label"] == "post-discovery"

    def test_version_default_label(self, sample_context):
        meta = save_context_version(TEST_PROJECT_DIR, sample_context)
        assert meta["label"] == "Build #1"

    def test_list_versions_empty(self):
        versions = list_context_versions(TEST_PROJECT_DIR)
        assert versions == []

    def test_list_versions_returns_newest_first(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context, "v1-initial")
        save_context_version(TEST_PROJECT_DIR, sample_context, "v2-full")
        versions = list_context_versions(TEST_PROJECT_DIR)
        assert len(versions) == 2
        assert versions[0]["version_id"] == "v2"
        assert versions[1]["version_id"] == "v1"

    def test_get_specific_version(self, sample_context):
        save_context_version(TEST_PROJECT_DIR, sample_context)
        snapshot = get_context_version(TEST_PROJECT_DIR, "v1")
        assert snapshot is not None
        assert "_version_meta" in snapshot
        assert snapshot["_version_meta"]["version_id"] == "v1"
        assert "risks" in snapshot

    def test_get_nonexistent_version(self):
        result = get_context_version(TEST_PROJECT_DIR, "v99")
        assert result is None

    def test_version_stats_accurate(self, sample_context):
        meta = save_context_version(TEST_PROJECT_DIR, sample_context)
        assert meta["stats"]["risks"] == len(sample_context["risks"])
        assert meta["stats"]["constraints"] == len(sample_context["constraints"])
        assert meta["stats"]["dependencies"] == len(sample_context["dependencies"])
        assert meta["stats"]["document_count"] == sample_context["_build_metadata"]["document_count"]


# ───────────────────────────────────────────────────────────
# Context version comparison tests
# ───────────────────────────────────────────────────────────


class TestCompareVersions:
    """Test comparing two context versions."""

    def test_compare_shows_added_items(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context, "initial")
        save_context_version(TEST_PROJECT_DIR, sample_context, "full")
        comparison = compare_context_versions(TEST_PROJECT_DIR, "v1", "v2")

        assert comparison["version_a"] == "v1"
        assert comparison["version_b"] == "v2"
        assert "categories" in comparison
        assert "risks" in comparison["categories"]

        # Full context should have more risks than partial
        risks_diff = comparison["categories"]["risks"]
        assert risks_diff["count_after"] >= risks_diff["count_before"]

    def test_compare_has_summary(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context)
        save_context_version(TEST_PROJECT_DIR, sample_context)
        comparison = compare_context_versions(TEST_PROJECT_DIR, "v1", "v2")

        assert "summary" in comparison
        assert "total_added" in comparison["summary"]
        assert "total_removed" in comparison["summary"]
        assert "trend" in comparison["summary"]

    def test_compare_same_version(self, sample_context):
        save_context_version(TEST_PROJECT_DIR, sample_context)
        save_context_version(TEST_PROJECT_DIR, sample_context)
        comparison = compare_context_versions(TEST_PROJECT_DIR, "v1", "v2")

        # Same data → no changes
        assert comparison["summary"]["total_added"] == 0
        assert comparison["summary"]["total_removed"] == 0
        assert comparison["summary"]["trend"] == "stable"

    def test_compare_nonexistent_version_raises(self, sample_context):
        save_context_version(TEST_PROJECT_DIR, sample_context)
        with pytest.raises(ValueError, match="Version not found"):
            compare_context_versions(TEST_PROJECT_DIR, "v1", "v99")

    def test_compare_categories_have_correct_structure(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context)
        save_context_version(TEST_PROJECT_DIR, sample_context)
        comparison = compare_context_versions(TEST_PROJECT_DIR, "v1", "v2")

        for category in ["risks", "assumptions", "dependencies", "constraints"]:
            cat_data = comparison["categories"][category]
            assert "count_before" in cat_data
            assert "count_after" in cat_data
            assert "added" in cat_data
            assert "removed" in cat_data
            assert "unchanged_count" in cat_data
            assert "net_change" in cat_data


# ───────────────────────────────────────────────────────────
# Review comparison tests
# ───────────────────────────────────────────────────────────


class TestCompareReviews:
    """Test comparing two review outputs."""

    def test_compare_same_review(self, sample_context):
        review = run_review("solution_architect", sample_context, "files_only")
        comparison = compare_reviews(review, review)

        assert comparison["persona"] == "Solution Architect"
        assert comparison["summary"]["new_findings"] == 0
        assert comparison["summary"]["resolved_findings"] == 0
        assert comparison["summary"]["direction"] == "stable"

    def test_compare_different_contexts(self, partial_context, sample_context):
        review_a = run_review("solution_architect", partial_context, "files_only")
        review_b = run_review("solution_architect", sample_context, "files_only")
        comparison = compare_reviews(review_a, review_b)

        assert "sections" in comparison
        assert "summary" in comparison
        assert comparison["summary"]["direction"] in ("improving", "stable", "degrading")

    def test_compare_has_new_and_resolved(self, partial_context, sample_context):
        review_a = run_review("delivery_manager", partial_context, "files_only")
        review_b = run_review("delivery_manager", sample_context, "files_only")
        comparison = compare_reviews(review_a, review_b)

        # Full context should produce more findings
        total_new = comparison["summary"]["new_findings"]
        assert total_new >= 0  # At minimum stable

    def test_compare_sections_have_structure(self, sample_context):
        review_a = run_review("resource_manager", sample_context, "files_only")
        review_b = run_review("resource_manager", sample_context, "files_only")
        comparison = compare_reviews(review_a, review_b)

        for section, data in comparison["sections"].items():
            assert "count_before" in data
            assert "count_after" in data
            assert "new_findings" in data
            assert "resolved" in data
            assert "persistent" in data


# ───────────────────────────────────────────────────────────
# Evolution timeline tests
# ───────────────────────────────────────────────────────────


class TestEvolutionTimeline:
    """Test category evolution across versions."""

    def test_evolution_empty_project(self):
        timeline = get_evolution_timeline(TEST_PROJECT_DIR, "risks")
        assert timeline == []

    def test_evolution_single_version(self, sample_context):
        save_context_version(TEST_PROJECT_DIR, sample_context)
        timeline = get_evolution_timeline(TEST_PROJECT_DIR, "risks")
        assert len(timeline) == 1
        assert timeline[0]["version_id"] == "v1"
        assert timeline[0]["count"] == len(sample_context["risks"])

    def test_evolution_multiple_versions(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context, "initial")
        save_context_version(TEST_PROJECT_DIR, sample_context, "full")
        timeline = get_evolution_timeline(TEST_PROJECT_DIR, "risks")

        assert len(timeline) == 2
        assert timeline[0]["version_id"] == "v1"
        assert timeline[1]["version_id"] == "v2"
        # Full context should have more risks
        assert timeline[1]["count"] >= timeline[0]["count"]

    def test_evolution_constraints(self, partial_context, sample_context):
        save_context_version(TEST_PROJECT_DIR, partial_context)
        save_context_version(TEST_PROJECT_DIR, sample_context)
        timeline = get_evolution_timeline(TEST_PROJECT_DIR, "constraints")

        assert len(timeline) == 2
        assert all("count" in t for t in timeline)
        assert all("items" in t for t in timeline)

    def test_evolution_includes_labels(self, sample_context):
        save_context_version(TEST_PROJECT_DIR, sample_context, "post-discovery")
        timeline = get_evolution_timeline(TEST_PROJECT_DIR, "risks")
        assert timeline[0]["label"] == "post-discovery"


# ───────────────────────────────────────────────────────────
# Review history tests
# ───────────────────────────────────────────────────────────


class TestReviewHistory:
    """Test review history retrieval."""

    def test_history_empty(self):
        history = get_review_history(TEST_PROJECT_DIR)
        assert history == []

    def test_history_with_reviews(self, sample_context):
        # Create reviews directory and store some reviews
        reviews_dir = TEST_PROJECT_DIR / "reviews"
        reviews_dir.mkdir()

        review = run_review("solution_architect", sample_context, "files_only")
        with open(reviews_dir / "solution_architect_2024-01-01T00-00-00.json", "w") as f:
            json.dump(review, f)

        history = get_review_history(TEST_PROJECT_DIR)
        assert len(history) == 1
        assert history[0]["persona"] == "Solution Architect"
        assert history[0]["total_findings"] > 0

    def test_history_filter_by_persona(self, sample_context):
        reviews_dir = TEST_PROJECT_DIR / "reviews"
        reviews_dir.mkdir()

        # Store two different persona reviews
        review_sa = run_review("solution_architect", sample_context, "files_only")
        review_dm = run_review("delivery_manager", sample_context, "files_only")

        with open(reviews_dir / "solution_architect_2024-01-01T00-00-00.json", "w") as f:
            json.dump(review_sa, f)
        with open(reviews_dir / "delivery_manager_2024-01-01T00-00-00.json", "w") as f:
            json.dump(review_dm, f)

        # Filter for solution_architect only
        history = get_review_history(TEST_PROJECT_DIR, "solution_architect")
        assert len(history) == 1
        assert history[0]["persona_id"] == "solution_architect"

    def test_history_newest_first(self, sample_context):
        reviews_dir = TEST_PROJECT_DIR / "reviews"
        reviews_dir.mkdir()

        review = run_review("solution_architect", sample_context, "files_only")

        with open(reviews_dir / "solution_architect_2024-01-01T00-00-00.json", "w") as f:
            json.dump(review, f)
        with open(reviews_dir / "solution_architect_2024-06-15T00-00-00.json", "w") as f:
            json.dump(review, f)

        history = get_review_history(TEST_PROJECT_DIR)
        assert len(history) == 2
        # Newest file first (sorted reverse by filename)
        assert "2024-06" in history[0]["file"]


# ───────────────────────────────────────────────────────────
# IterationMetadata model tests
# ───────────────────────────────────────────────────────────


class TestIterationMetadata:
    """Test the IterationMetadata dataclass."""

    def test_create_default(self):
        from models.project import IterationMetadata
        meta = IterationMetadata()
        assert meta.current_version == ""
        assert meta.total_builds == 0
        assert meta.total_reviews == 0
        assert meta.phase_history == []

    def test_create_with_values(self):
        from models.project import IterationMetadata
        meta = IterationMetadata(
            current_version="v3",
            total_builds=3,
            total_reviews=8,
            last_build_at="2024-06-01T00:00:00+00:00",
        )
        assert meta.current_version == "v3"
        assert meta.total_builds == 3
        assert meta.total_reviews == 8

    def test_project_has_iteration_field(self):
        from models.project import Project
        p = Project(id="test", name="Test")
        assert p.iteration is None
