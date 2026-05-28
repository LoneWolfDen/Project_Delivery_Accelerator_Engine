"""Tests for the Context Builder – intelligence extraction and aggregation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.ingestion import ingest_file, ingest_directory
from processors.context_builder import (
    build_context,
    build_context_summary,
    merge_contexts,
)
from processors.extractors.intelligence_extractor import extract_intelligence


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


# ───────────────────────────────────────────────────────────
# Intelligence Extractor tests
# ───────────────────────────────────────────────────────────


class TestIntelligenceExtractor:
    """Test extraction from individual documents."""

    def test_extract_from_email(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        extraction = extract_intelligence(doc.to_dict())
        assert extraction["source"] == "sample_email.txt"
        assert extraction["source_type"] == "email"
        # Email contains constraints (SLA, encryption, no public internet)
        assert len(extraction["constraints"]) >= 1

    def test_extract_from_transcript(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        extraction = extract_intelligence(doc.to_dict())
        # Transcript has action items
        assert len(extraction["action_items"]) >= 3
        # Transcript mentions risks (latency, resource gap)
        assert len(extraction["risks"]) >= 1

    def test_extract_from_markdown_artefact(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        extraction = extract_intelligence(doc.to_dict())
        # Markdown has explicit Risks section
        assert len(extraction["risks"]) >= 2
        # Has resource requirements
        assert len(extraction["resources"]) >= 1
        # Has scope (Executive Summary)
        assert len(extraction["scope_fragments"]) >= 1

    def test_extract_from_call_notes(self):
        doc = ingest_file(SAMPLE_DIR / "sample_call_notes.txt")
        extraction = extract_intelligence(doc.to_dict())
        # Call notes have constraints and risks
        assert len(extraction["constraints"]) >= 1 or len(extraction["risks"]) >= 1

    def test_extract_from_scope_document(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        extraction = extract_intelligence(doc.to_dict())
        # Scope document has structured sections
        assert extraction["source_type"] in ("sow", "plain_text", "artefact")

    def test_extract_returns_required_keys(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        extraction = extract_intelligence(doc.to_dict())
        required_keys = [
            "source", "source_type", "risks", "assumptions",
            "dependencies", "constraints", "resources",
            "scope_fragments", "action_items",
        ]
        for key in required_keys:
            assert key in extraction, f"Missing key: {key}"

    def test_extract_deduplicates(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        extraction = extract_intelligence(doc.to_dict())
        # No exact duplicates in risks
        risks_lower = [r.lower() for r in extraction["risks"]]
        assert len(risks_lower) == len(set(risks_lower))


# ───────────────────────────────────────────────────────────
# Context Builder – build_context tests
# ───────────────────────────────────────────────────────────


class TestBuildContext:
    """Test full context building from multiple documents."""

    def test_build_from_empty_list(self):
        result = build_context([])
        assert result["scope"] == ""
        assert result["risks"] == []

    def test_build_from_single_document(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        result = build_context([doc.to_dict()])
        assert "_build_metadata" in result
        assert result["_build_metadata"]["document_count"] == 1
        assert result["_build_metadata"]["valid_documents"] == 1
        assert len(result["risks"]) >= 2

    def test_build_from_multiple_documents(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        result = build_context(doc_dicts)

        assert result["_build_metadata"]["document_count"] >= 4
        # Aggregated should have risks from multiple sources
        assert len(result["risks"]) >= 2
        # Should have action items from transcript
        assert len(result.get("action_items", [])) >= 1

    def test_build_produces_summary(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        result = build_context(doc_dicts)
        assert result["summary"] != ""
        assert "document" in result["summary"].lower()

    def test_build_has_scope(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        result = build_context([doc.to_dict()])
        assert result["scope"] != ""

    def test_build_deduplicates_across_documents(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        # Feed same document twice
        result = build_context([doc.to_dict(), doc.to_dict()])
        # Should deduplicate
        risks_lower = [r.lower() for r in result["risks"]]
        assert len(risks_lower) == len(set(risks_lower))

    def test_build_metadata_counts(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        result = build_context(doc_dicts)
        meta = result["_build_metadata"]
        assert meta["total_risks"] == len(result["risks"])
        assert meta["total_assumptions"] == len(result["assumptions"])
        assert meta["total_dependencies"] == len(result["dependencies"])
        assert meta["total_constraints"] == len(result["constraints"])

    def test_build_skips_invalid_documents(self):
        valid_doc = ingest_file(SAMPLE_DIR / "scope.txt").to_dict()
        invalid_doc = {"is_valid": False, "filename": "bad.txt", "sections": []}
        result = build_context([valid_doc, invalid_doc])
        assert result["_build_metadata"]["valid_documents"] == 1


# ───────────────────────────────────────────────────────────
# Context Builder – merge_contexts tests
# ───────────────────────────────────────────────────────────


class TestMergeContexts:
    """Test incremental context merging."""

    def test_merge_empty_existing(self):
        new_ctx = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        result = merge_contexts({}, new_ctx)
        assert result == new_ctx

    def test_merge_empty_new(self):
        existing = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        result = merge_contexts(existing, {})
        assert result == existing

    def test_merge_combines_risks(self):
        ctx1 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        ctx2 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_email.txt").to_dict()]
        )
        merged = merge_contexts(ctx1, ctx2)
        # Merged should have >= risks from either
        assert len(merged["risks"]) >= max(len(ctx1["risks"]), len(ctx2["risks"]))

    def test_merge_deduplicates(self):
        ctx1 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        # Merge same context with itself
        merged = merge_contexts(ctx1, ctx1)
        risks_lower = [r.lower() for r in merged["risks"]]
        assert len(risks_lower) == len(set(risks_lower))

    def test_merge_preserves_raw_extractions(self):
        ctx1 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        ctx2 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_transcript.txt").to_dict()]
        )
        merged = merge_contexts(ctx1, ctx2)
        assert len(merged["raw_extractions"]) == (
            len(ctx1["raw_extractions"]) + len(ctx2["raw_extractions"])
        )

    def test_merge_updates_metadata(self):
        ctx1 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_artefact.md").to_dict()]
        )
        ctx2 = build_context(
            [ingest_file(SAMPLE_DIR / "sample_email.txt").to_dict()]
        )
        merged = merge_contexts(ctx1, ctx2)
        assert "merged_at" in merged["_build_metadata"]


# ───────────────────────────────────────────────────────────
# Context Summary tests
# ───────────────────────────────────────────────────────────


class TestContextSummary:
    """Test context summary generation (for token-efficient prompts)."""

    def test_summary_includes_risks(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        summary = build_context_summary(ctx)
        assert "Risks" in summary

    def test_summary_includes_document_count(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        summary = build_context_summary(ctx)
        assert "documents" in summary.lower()

    def test_summary_not_too_long(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        summary = build_context_summary(ctx)
        # Summary should be concise (under 3000 chars for token efficiency)
        assert len(summary) < 3000

    def test_empty_context_summary(self):
        ctx = build_context([])
        summary = build_context_summary(ctx)
        assert "## Project Context Summary" in summary
