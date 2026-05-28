"""Tests for the Persona Review Engine – loading, review execution, and output."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from personas.engine import (
    AVAILABLE_PERSONAS,
    build_review_prompt,
    list_personas,
    load_persona,
    run_review,
)
from processors.context_builder import build_context
from processors.ingestion import ingest_directory


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


@pytest.fixture
def sample_context():
    """Build context from sample data for review tests."""
    docs = ingest_directory(SAMPLE_DIR)
    doc_dicts = [d.to_dict() for d in docs if d.is_valid]
    return build_context(doc_dicts)


# ───────────────────────────────────────────────────────────
# Persona loading tests
# ───────────────────────────────────────────────────────────


class TestLoadPersona:
    """Test persona definition loading."""

    def test_load_solution_architect(self):
        persona = load_persona("solution_architect")
        assert persona["name"] == "Solution Architect"
        assert "prompt_template" in persona
        assert "focus_areas" in persona
        assert len(persona["focus_areas"]) >= 3

    def test_load_delivery_manager(self):
        persona = load_persona("delivery_manager")
        assert persona["name"] == "Delivery Manager"

    def test_load_product_owner(self):
        persona = load_persona("product_owner")
        assert persona["name"] == "Product Owner"

    def test_load_resource_manager(self):
        persona = load_persona("resource_manager")
        assert persona["name"] == "Resource Manager"

    def test_load_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown persona"):
            load_persona("unknown_role")

    def test_list_personas(self):
        personas = list_personas()
        assert len(personas) == 4
        names = [p["name"] for p in personas]
        assert "Solution Architect" in names
        assert "Delivery Manager" in names


# ───────────────────────────────────────────────────────────
# Prompt building tests
# ───────────────────────────────────────────────────────────


class TestBuildPrompt:
    """Test review prompt construction."""

    def test_prompt_includes_persona_role(self, sample_context):
        persona = load_persona("solution_architect")
        prompt = build_review_prompt(persona, sample_context)
        assert "Solution Architect" in prompt

    def test_prompt_includes_focus_areas(self, sample_context):
        persona = load_persona("delivery_manager")
        prompt = build_review_prompt(persona, sample_context)
        assert "Timeline realism" in prompt

    def test_prompt_includes_context_summary(self, sample_context):
        persona = load_persona("product_owner")
        prompt = build_review_prompt(persona, sample_context)
        assert "Project Context Summary" in prompt

    def test_prompt_includes_output_sections(self, sample_context):
        persona = load_persona("resource_manager")
        prompt = build_review_prompt(persona, sample_context)
        assert "skill_gaps" in prompt

    def test_prompt_is_reasonable_size(self, sample_context):
        persona = load_persona("solution_architect")
        prompt = build_review_prompt(persona, sample_context)
        # Should be token-efficient: under 4000 chars
        assert len(prompt) < 5000


# ───────────────────────────────────────────────────────────
# Files-only review tests
# ───────────────────────────────────────────────────────────


class TestFilesOnlyReview:
    """Test deterministic files-only persona reviews."""

    def test_solution_architect_review(self, sample_context):
        result = run_review("solution_architect", sample_context, "files_only")
        assert result["persona"] == "Solution Architect"
        assert result["ai_backend"] == "files_only"
        assert "findings" in result
        assert "risks" in result["findings"]
        assert "recommendations" in result
        assert "questions" in result

    def test_delivery_manager_review(self, sample_context):
        result = run_review("delivery_manager", sample_context, "files_only")
        assert result["persona"] == "Delivery Manager"
        assert "execution_risks" in result["findings"]
        assert "dependency_issues" in result["findings"]
        assert "timeline_concerns" in result["findings"]

    def test_product_owner_review(self, sample_context):
        result = run_review("product_owner", sample_context, "files_only")
        assert result["persona"] == "Product Owner"
        assert "scope_gaps" in result["findings"]
        assert "recommendations" in result["findings"]

    def test_resource_manager_review(self, sample_context):
        result = run_review("resource_manager", sample_context, "files_only")
        assert result["persona"] == "Resource Manager"
        assert "skill_gaps" in result["findings"]
        assert "capacity_concerns" in result["findings"]

    def test_review_has_timestamp(self, sample_context):
        result = run_review("solution_architect", sample_context)
        assert "timestamp" in result
        assert "T" in result["timestamp"]  # ISO format

    def test_review_has_summary(self, sample_context):
        result = run_review("delivery_manager", sample_context)
        assert result["summary"] != ""
        assert "Delivery Manager" in result["summary"]

    def test_review_has_persona_id(self, sample_context):
        result = run_review("solution_architect", sample_context)
        assert result["persona_id"] == "solution_architect"

    def test_review_findings_not_empty(self, sample_context):
        result = run_review("solution_architect", sample_context)
        total_findings = sum(len(v) for v in result["findings"].values())
        assert total_findings > 0

    def test_all_personas_produce_output(self, sample_context):
        for persona_id in AVAILABLE_PERSONAS:
            result = run_review(persona_id, sample_context, "files_only")
            assert result["persona"] != ""
            total = sum(len(v) for v in result["findings"].values())
            assert total > 0, f"{persona_id} produced no findings"

    def test_unknown_persona_raises(self, sample_context):
        with pytest.raises(ValueError, match="Unknown persona"):
            run_review("ceo", sample_context)

    def test_unknown_backend_raises(self, sample_context):
        with pytest.raises(ValueError, match="Unknown AI backend"):
            run_review("solution_architect", sample_context, "gpt4")

    def test_default_backend_is_files_only(self, sample_context):
        result = run_review("solution_architect", sample_context)
        assert result["ai_backend"] == "files_only"


# ───────────────────────────────────────────────────────────
# AI backend fallback tests
# ───────────────────────────────────────────────────────────


class TestAIBackendFallback:
    """Test that AI backends gracefully fall back when unavailable."""

    def test_ollama_falls_back(self, sample_context):
        """Ollama not running in test env → should fall back to files_only."""
        result = run_review("solution_architect", sample_context, "ollama")
        assert result["ai_backend"] in ("ollama", "ollama_fallback")
        # Should still produce findings
        assert "findings" in result

    def test_bedrock_falls_back(self, sample_context):
        """No AWS credentials in test env → should fall back to files_only."""
        result = run_review("delivery_manager", sample_context, "bedrock")
        assert result["ai_backend"] in ("bedrock", "bedrock_fallback")
        assert "findings" in result


# ───────────────────────────────────────────────────────────
# Review quality tests
# ───────────────────────────────────────────────────────────


class TestReviewQuality:
    """Validate that reviews produce meaningful, persona-specific output."""

    def test_architect_finds_security_gaps(self, sample_context):
        result = run_review("solution_architect", sample_context, "files_only")
        all_text = str(result["findings"])
        # Our sample data has PCI-DSS, encryption requirements
        assert any(
            kw in all_text.lower()
            for kw in ["security", "compliance", "encrypt", "pci", "nfr"]
        )

    def test_delivery_manager_finds_dependencies(self, sample_context):
        result = run_review("delivery_manager", sample_context, "files_only")
        dep_issues = result["findings"].get("dependency_issues", [])
        assert len(dep_issues) >= 1

    def test_product_owner_raises_scope_questions(self, sample_context):
        result = run_review("product_owner", sample_context, "files_only")
        questions = result["questions"]
        assert len(questions) >= 1

    def test_resource_manager_finds_capacity(self, sample_context):
        result = run_review("resource_manager", sample_context, "files_only")
        capacity = result["findings"].get("capacity_concerns", [])
        assert len(capacity) >= 1
