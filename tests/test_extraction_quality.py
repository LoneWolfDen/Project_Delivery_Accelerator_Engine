"""Tests for enhanced extraction pattern quality.

Validates that extraction produces clean, meaningful output:
- No table separator noise
- No fragment/too-short items
- Proper structured risk table parsing
- Fuzzy deduplication working
- Implicit assumption detection
- Constraint filtering (no vendor names / informational items)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.extractors.intelligence_extractor import extract_intelligence
from processors.extractors.patterns import (
    MIN_EXTRACTION_LENGTH,
    clean_extraction,
    extract_from_table,
    extract_table_rows,
    is_noise_line,
)
from processors.context_builder import build_context
from processors.ingestion import ingest_file, ingest_directory


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


# ───────────────────────────────────────────────────────────
# Noise filtering tests
# ───────────────────────────────────────────────────────────


class TestNoiseFiltering:
    """Test that noise is properly filtered out."""

    def test_table_separator_is_noise(self):
        assert is_noise_line("|------|--------|------------|")
        assert is_noise_line("| --- | --- | --- |")

    def test_short_items_are_noise(self):
        assert is_noise_line("PCI-DSS")
        assert is_noise_line("Risk")
        assert is_noise_line("Yes")

    def test_real_content_is_not_noise(self):
        assert not is_noise_line("Data loss during DB migration is a critical risk")
        assert not is_noise_line("Must maintain SOC2 certification throughout")

    def test_clean_extraction_removes_pipes(self):
        assert clean_extraction("| some text |") == "some text"
        assert clean_extraction("  | leading pipe text") == "leading pipe text"

    def test_clean_extraction_removes_bold_markers(self):
        assert "Risk" in clean_extraction("**Risk** something happens")

    def test_clean_extraction_preserves_content(self):
        text = "Data loss during DB migration"
        assert clean_extraction(text) == text


# ───────────────────────────────────────────────────────────
# Table parsing tests
# ───────────────────────────────────────────────────────────


class TestTableParsing:
    """Test markdown table extraction."""

    def test_extract_table_rows_basic(self):
        table = """\
| Risk | Impact | Likelihood |
|------|--------|------------|
| Data loss | Critical | Low |
| PCI gap | High | Medium |
"""
        rows = extract_table_rows(table)
        assert len(rows) == 2
        assert "Data loss" in rows[0][0]
        assert "Critical" in rows[0][1]

    def test_extract_table_rows_skips_header(self):
        table = """\
| Column A | Column B |
|----------|----------|
| value 1  | value 2  |
"""
        rows = extract_table_rows(table)
        assert len(rows) == 1
        assert "value 1" in rows[0][0]

    def test_extract_table_rows_no_table(self):
        text = "This is just normal text\nwith no table at all."
        rows = extract_table_rows(text)
        assert rows == []

    def test_extract_from_table_first_column(self):
        table = """\
| Risk | Impact |
|------|--------|
| Important risk item | High |
| Another risk here | Medium |
"""
        items = extract_from_table(table, target_column=0)
        assert len(items) == 2
        assert "Important risk item" in items[0]


# ───────────────────────────────────────────────────────────
# Risk extraction quality tests
# ───────────────────────────────────────────────────────────


class TestRiskExtractionQuality:
    """Test that risk extraction produces clean, meaningful items."""

    def test_no_table_separators_in_risks(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        extraction = extract_intelligence(doc.to_dict())
        for risk in extraction["risks"]:
            assert "---" not in risk, f"Table separator in risk: {risk}"
            assert not risk.startswith("|"), f"Pipe-prefixed risk: {risk}"

    def test_all_risks_above_min_length(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        extraction = extract_intelligence(doc.to_dict())
        for risk in extraction["risks"]:
            assert len(risk) >= MIN_EXTRACTION_LENGTH, f"Too short: {risk}"

    def test_risk_table_parsed_as_structured(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        extraction = extract_intelligence(doc.to_dict())
        # Should have structured risks with impact/likelihood
        structured = [r for r in extraction["risks"] if "impact:" in r.lower()]
        assert len(structured) >= 2, "Risk table not properly parsed"

    def test_narrative_risks_extracted(self):
        doc = ingest_file(SAMPLE_DIR / "sample_call_notes.txt")
        extraction = extract_intelligence(doc.to_dict())
        all_text = " ".join(extraction["risks"]).lower()
        assert "key person" in all_text or "vendor lock" in all_text


# ───────────────────────────────────────────────────────────
# Constraint extraction quality tests
# ───────────────────────────────────────────────────────────


class TestConstraintExtractionQuality:
    """Test that constraints are meaningful, not informational noise."""

    def test_no_vendor_names_in_constraints(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        vendor_noise = ["McKesson", "Sectra", "Agfa", "Cerner", "Kinaxis", "Dassault"]
        for constraint in ctx["constraints"]:
            for vendor in vendor_noise:
                assert vendor not in constraint, f"Vendor in constraint: {constraint}"

    def test_constraints_have_obligation_language(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        obligation_words = ["must", "cannot", "shall", "no ", "sla", "require", "encrypt", "compli"]
        meaningful = sum(
            1 for c in ctx["constraints"]
            if any(w in c.lower() for w in obligation_words)
        )
        assert meaningful >= len(ctx["constraints"]) * 0.5

    def test_no_informational_standards_as_constraints(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        for c in ctx["constraints"]:
            assert c != "DICOM 3.0 (medical imaging)"
            assert c != "EDI X12 (claims and billing)"


# ───────────────────────────────────────────────────────────
# Deduplication quality tests
# ───────────────────────────────────────────────────────────


class TestDeduplicationQuality:
    """Test that fuzzy deduplication works properly."""

    def test_no_exact_duplicates(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        for category in ["risks", "constraints", "dependencies"]:
            items = ctx[category]
            items_lower = [i.lower() for i in items]
            assert len(items_lower) == len(set(items_lower)), f"Duplicates in {category}"


# ───────────────────────────────────────────────────────────
# Assumption extraction quality tests
# ───────────────────────────────────────────────────────────


class TestAssumptionExtractionQuality:
    """Test that implicit assumptions are detected."""

    def test_budget_assumption_detected(self):
        doc = ingest_file(SAMPLE_DIR / "sample_call_notes.txt")
        extraction = extract_intelligence(doc.to_dict())
        all_assumptions = " ".join(extraction["assumptions"]).lower()
        assert "budget" in all_assumptions or "approved" in all_assumptions

    def test_full_context_has_assumptions(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        assert len(ctx["assumptions"]) >= 1


# ───────────────────────────────────────────────────────────
# Overall extraction metrics
# ───────────────────────────────────────────────────────────


class TestExtractionMetrics:
    """Test overall extraction quality metrics."""

    def test_risks_are_concise(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        for risk in ctx["risks"]:
            assert len(risk) <= 200, f"Risk too long: {risk[:50]}..."

    def test_total_extractions_reasonable(self):
        docs = ingest_directory(SAMPLE_DIR)
        doc_dicts = [d.to_dict() for d in docs if d.is_valid]
        ctx = build_context(doc_dicts)
        assert 3 <= len(ctx["risks"]) <= 20
        assert 5 <= len(ctx["constraints"]) <= 25
        assert len(ctx["action_items"]) >= 3
