"""Tests for Proposal Version Tracking and Phase Transitions."""

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.proposals import (
    add_proposal_version,
    compare_proposal_versions,
    create_proposal,
    get_proposal,
    list_proposal_versions,
    update_proposal_status,
)
from processors.phases import (
    PHASES,
    VALID_TRANSITIONS,
    get_phase_history,
    get_phase_info,
    transition_phase,
)
from models.proposal import VALID_PROPOSAL_STATUSES


TEST_DIR = Path("/tmp/test_proposals_phases")
TEST_PROJECTS_FILE = TEST_DIR / "projects.json"


@pytest.fixture(autouse=True)
def clean_test_dir():
    """Create and clean test directory."""
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)
    TEST_DIR.mkdir(parents=True)
    # Create a minimal project in projects.json
    projects = [{"id": "proj-test", "name": "Test", "phase": "discovery", "iteration": {}}]
    with open(TEST_PROJECTS_FILE, "w") as f:
        json.dump(projects, f)
    yield
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


# ───────────────────────────────────────────────────────────
# Proposal tests
# ───────────────────────────────────────────────────────────


class TestProposalCreation:
    """Test proposal creation and versioning."""

    def test_create_proposal(self):
        result = create_proposal(TEST_DIR, "Test Proposal", "ClientCo")
        assert result["proposal_name"] == "Test Proposal"
        assert result["client"] == "ClientCo"
        assert result["current_version"] == "prop-v1"
        assert result["total_versions"] == 1

    def test_create_proposal_with_files(self):
        result = create_proposal(
            TEST_DIR, "Proposal", "Client",
            files=["doc1.pdf", "doc2.xlsx"],
            notes="Initial draft",
        )
        assert result["versions"][0]["files"] == ["doc1.pdf", "doc2.xlsx"]
        assert result["versions"][0]["notes"] == "Initial draft"

    def test_add_version(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        version = add_proposal_version(
            TEST_DIR, label="Revised", notes="Updated",
            changes="Added security section",
        )
        assert version["version_id"] == "prop-v2"
        assert version["label"] == "Revised"
        assert version["changes_from_previous"] == "Added security section"

    def test_add_version_supersedes_previous(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        add_proposal_version(TEST_DIR, label="v2")
        tracker = get_proposal(TEST_DIR)
        assert tracker["versions"][0]["status"] == "superseded"
        assert tracker["versions"][1]["status"] == "draft"

    def test_add_version_no_proposal_raises(self):
        empty_dir = TEST_DIR / "empty"
        empty_dir.mkdir()
        with pytest.raises(ValueError, match="No proposal exists"):
            add_proposal_version(empty_dir)

    def test_list_versions(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        add_proposal_version(TEST_DIR, label="v2")
        versions = list_proposal_versions(TEST_DIR)
        assert len(versions) == 2
        assert versions[0]["version_id"] == "prop-v1"
        assert versions[1]["version_id"] == "prop-v2"

    def test_update_status(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        result = update_proposal_status(TEST_DIR, "prop-v1", "submitted")
        assert result["status"] == "submitted"

    def test_update_invalid_status_raises(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        with pytest.raises(ValueError, match="Invalid status"):
            update_proposal_status(TEST_DIR, "prop-v1", "invalid_status")

    def test_update_nonexistent_version_raises(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        with pytest.raises(ValueError, match="Version not found"):
            update_proposal_status(TEST_DIR, "prop-v99", "submitted")


class TestProposalComparison:
    """Test comparing proposal versions."""

    def test_compare_versions(self):
        create_proposal(TEST_DIR, "Proposal", "Client", files=["doc1.pdf"])
        add_proposal_version(
            TEST_DIR, files=["doc1.pdf", "doc2.xlsx"],
            changes="Added pricing sheet",
        )
        result = compare_proposal_versions(TEST_DIR, "prop-v1", "prop-v2")
        assert result["version_a"] == "prop-v1"
        assert result["version_b"] == "prop-v2"
        assert "doc2.xlsx" in result["files"]["added"]
        assert result["changes_noted"] == "Added pricing sheet"

    def test_compare_shows_removed_files(self):
        create_proposal(TEST_DIR, "Proposal", "Client", files=["a.pdf", "b.pdf"])
        add_proposal_version(TEST_DIR, files=["a.pdf"])
        result = compare_proposal_versions(TEST_DIR, "prop-v1", "prop-v2")
        assert "b.pdf" in result["files"]["removed"]

    def test_compare_nonexistent_raises(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        with pytest.raises(ValueError, match="Version not found"):
            compare_proposal_versions(TEST_DIR, "prop-v1", "prop-v99")


class TestProposalStatuses:
    """Test valid proposal statuses."""

    def test_all_statuses_valid(self):
        expected = ["draft", "submitted", "under_review", "revised",
                    "accepted", "rejected", "superseded"]
        assert VALID_PROPOSAL_STATUSES == expected

    def test_initial_status_is_draft(self):
        create_proposal(TEST_DIR, "Proposal", "Client")
        tracker = get_proposal(TEST_DIR)
        assert tracker["versions"][0]["status"] == "draft"


# ───────────────────────────────────────────────────────────
# Phase transition tests
# ───────────────────────────────────────────────────────────


class TestPhaseTransitions:
    """Test SDLC phase transitions."""

    def test_valid_transition(self):
        result = transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        assert result["from_phase"] == "discovery"
        assert result["to_phase"] == "proposal"

    def test_invalid_phase_raises(self):
        with pytest.raises(ValueError, match="Invalid phase"):
            transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "invalid")

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError, match="Cannot transition"):
            transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "execution")

    def test_transition_records_reason(self):
        result = transition_phase(
            TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal",
            reason="Discovery complete"
        )
        assert result["reason"] == "Discovery complete"

    def test_transition_updates_project_phase(self):
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        with open(TEST_PROJECTS_FILE) as f:
            projects = json.load(f)
        assert projects[0]["phase"] == "proposal"

    def test_multi_step_transitions(self):
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "planning")
        with open(TEST_PROJECTS_FILE) as f:
            projects = json.load(f)
        assert projects[0]["phase"] == "planning"

    def test_can_go_back(self):
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "discovery")
        with open(TEST_PROJECTS_FILE) as f:
            projects = json.load(f)
        assert projects[0]["phase"] == "discovery"

    def test_project_not_found_raises(self):
        with pytest.raises(ValueError, match="Project not found"):
            transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "nonexistent", "proposal")


class TestPhaseHistory:
    """Test phase history tracking."""

    def test_history_after_transitions(self):
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "planning")
        history = get_phase_history(TEST_DIR, TEST_PROJECTS_FILE, "proj-test")
        assert len(history) == 2
        assert history[0]["phase"] == "proposal"
        assert history[1]["phase"] == "planning"
        assert history[1]["is_current"] is True

    def test_history_has_durations(self):
        transition_phase(TEST_DIR, TEST_PROJECTS_FILE, "proj-test", "proposal")
        history = get_phase_history(TEST_DIR, TEST_PROJECTS_FILE, "proj-test")
        assert "duration" in history[0]

    def test_history_empty_for_new_project(self):
        history = get_phase_history(TEST_DIR, TEST_PROJECTS_FILE, "proj-test")
        assert history == []


class TestPhaseInfo:
    """Test phase info and metadata."""

    def test_phases_in_order(self):
        assert PHASES == ["discovery", "proposal", "planning", "execution", "review"]

    def test_get_phase_info(self):
        info = get_phase_info()
        assert len(info) == 5
        assert info[0]["phase"] == "discovery"
        assert info[0]["order"] == 1
        assert "proposal" in info[0]["can_transition_to"]

    def test_all_phases_have_transitions(self):
        for phase in PHASES:
            assert phase in VALID_TRANSITIONS
            assert len(VALID_TRANSITIONS[phase]) >= 1
