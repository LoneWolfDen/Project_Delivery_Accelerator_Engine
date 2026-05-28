"""Tests for stories and gates data modules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "migration_dashboard"))

from stories_data import STORIES
from gates_data import GATES


class TestStoriesData:
    """Validate stories data structure."""

    def test_stories_not_empty(self):
        assert len(STORIES) > 0

    def test_all_stories_have_required_fields(self):
        for epic_id, roles in STORIES.items():
            for role, stories in roles.items():
                for story in stories:
                    assert "story" in story, f"{epic_id}/{role} missing story text"
                    assert "size" in story, f"{epic_id}/{role} missing size"
                    assert "ac" in story, f"{epic_id}/{role} missing acceptance criteria"

    def test_valid_tshirt_sizes(self):
        valid_sizes = {"XS", "S", "M", "L", "XL"}
        for epic_id, roles in STORIES.items():
            for role, stories in roles.items():
                for story in stories:
                    assert story["size"] in valid_sizes, (
                        f"{epic_id}/{role}: invalid size '{story['size']}'"
                    )

    def test_acceptance_criteria_not_empty(self):
        for epic_id, roles in STORIES.items():
            for role, stories in roles.items():
                for story in stories:
                    assert len(story["ac"]) > 0, (
                        f"{epic_id}/{role}: empty acceptance criteria"
                    )

    def test_story_text_not_empty(self):
        for epic_id, roles in STORIES.items():
            for role, stories in roles.items():
                for story in stories:
                    assert len(story["story"].strip()) > 0


class TestGatesData:
    """Validate NFR gates data structure."""

    def test_gates_not_empty(self):
        assert len(GATES) > 0

    def test_gate_count(self):
        assert len(GATES) == 14

    def test_all_gates_have_required_fields(self):
        required = ["gate_id", "source_epic", "source_app", "nfr", "gate_type", "validation", "blocks"]
        for gate in GATES:
            for field in required:
                assert field in gate, f"Gate {gate.get('gate_id')} missing {field}"

    def test_valid_gate_types(self):
        valid = {"story_start", "story_done", "epic_exit"}
        for gate in GATES:
            assert gate["gate_type"] in valid, (
                f"{gate['gate_id']}: invalid type '{gate['gate_type']}'"
            )

    def test_blocks_have_required_fields(self):
        for gate in GATES:
            for block in gate["blocks"]:
                assert "epic" in block, f"{gate['gate_id']} block missing epic"
                assert "story" in block, f"{gate['gate_id']} block missing story"
                assert "reason" in block, f"{gate['gate_id']} block missing reason"

    def test_gate_ids_unique(self):
        ids = [g["gate_id"] for g in GATES]
        assert len(ids) == len(set(ids)), "Duplicate gate IDs"

    def test_total_blocked_stories(self):
        total = sum(len(g["blocks"]) for g in GATES)
        assert total == 30, f"Expected 30 blocked stories, got {total}"
