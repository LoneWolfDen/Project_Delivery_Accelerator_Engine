"""Tests for the ingestion pipeline – parsers, routing, and integration."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.document import ContentType, IngestedDocument, SourceType
from processors.ingestion import ingest_file, ingest_directory, SUPPORTED_EXTENSIONS


SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"


# ───────────────────────────────────────────────────────────
# Ingestion routing tests
# ───────────────────────────────────────────────────────────


class TestIngestionRouting:
    """Test file type detection and parser routing."""

    def test_ingest_txt_file(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        assert isinstance(doc, IngestedDocument)
        assert doc.is_valid
        assert doc.content_type == ContentType.TEXT

    def test_ingest_csv_file(self):
        csv_files = list(SAMPLE_DIR.glob("*.csv"))
        assert len(csv_files) > 0
        doc = ingest_file(csv_files[0])
        assert doc.is_valid
        assert doc.content_type == ContentType.CSV

    def test_ingest_markdown_file(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        assert doc.is_valid
        assert doc.content_type == ContentType.MARKDOWN

    def test_ingest_email_txt(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        assert doc.is_valid
        assert doc.content_type == ContentType.EMAIL

    def test_ingest_transcript(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        assert doc.is_valid
        assert doc.content_type == ContentType.TEXT

    def test_ingest_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            ingest_file(Path("/nonexistent/file.txt"))

    def test_ingest_unsupported_extension_raises(self):
        # Create a temp file with unsupported extension
        tmp = Path("/tmp/test_unsupported.xyz")
        tmp.write_text("test")
        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                ingest_file(tmp)
        finally:
            tmp.unlink()

    def test_ingest_directory(self):
        docs = ingest_directory(SAMPLE_DIR)
        assert len(docs) >= 4  # at least our 4 sample fixtures + CSVs
        assert all(isinstance(d, IngestedDocument) for d in docs)


# ───────────────────────────────────────────────────────────
# Plain text parser tests
# ───────────────────────────────────────────────────────────


class TestPlainTextParser:
    """Test plain text parsing and section extraction."""

    def test_scope_document_has_sections(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        assert doc.section_count >= 3  # Multiple headings in scope.txt

    def test_call_notes_detected(self):
        doc = ingest_file(SAMPLE_DIR / "sample_call_notes.txt")
        assert doc.is_valid
        assert doc.metadata.word_count > 50

    def test_sections_have_content(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        for section in doc.sections:
            assert section.content.strip() != ""

    def test_metadata_word_count(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        assert doc.metadata.word_count > 100


# ───────────────────────────────────────────────────────────
# Email parser tests
# ───────────────────────────────────────────────────────────


class TestEmailParser:
    """Test email parsing (text-based emails)."""

    def test_email_extracts_metadata(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        assert doc.metadata.source_type == SourceType.EMAIL
        assert doc.metadata.author == "sarah.chen@clientcorp.com"
        assert "james.wilson@consultingfirm.com" in doc.metadata.participants

    def test_email_has_subject(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        assert "Cloud Migration" in doc.metadata.subject

    def test_email_has_body_section(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        body_sections = [s for s in doc.sections if s.section_type == "body"]
        assert len(body_sections) >= 1
        assert "data warehouse" in body_sections[0].content.lower()

    def test_email_participants_list(self):
        doc = ingest_file(SAMPLE_DIR / "sample_email.txt")
        assert len(doc.metadata.participants) == 3  # from, to, cc


# ───────────────────────────────────────────────────────────
# Transcript parser tests
# ───────────────────────────────────────────────────────────


class TestTranscriptParser:
    """Test meeting transcript parsing."""

    def test_transcript_extracts_speakers(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        speaker_turns = [s for s in doc.sections if s.section_type == "speaker_turn"]
        assert len(speaker_turns) >= 5

    def test_transcript_extracts_action_items(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        action_sections = [s for s in doc.sections if s.section_type == "action_item"]
        assert len(action_sections) >= 1
        assert "Raj Kumar" in action_sections[0].content

    def test_transcript_has_timestamps(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        speaker_turns = [s for s in doc.sections if s.section_type == "speaker_turn"]
        timestamped = [s for s in speaker_turns if s.timestamp]
        assert len(timestamped) >= 5

    def test_transcript_participants_extracted(self):
        doc = ingest_file(SAMPLE_DIR / "sample_transcript.txt")
        assert len(doc.metadata.participants) >= 4


# ───────────────────────────────────────────────────────────
# Markdown parser tests
# ───────────────────────────────────────────────────────────


class TestMarkdownParser:
    """Test markdown parsing."""

    def test_markdown_extracts_headings(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        headings = [s.heading for s in doc.sections if s.heading]
        assert "Executive Summary" in headings
        assert "Risks" in headings

    def test_markdown_title_from_h1(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        assert "Payment Gateway" in doc.metadata.title

    def test_markdown_has_multiple_sections(self):
        doc = ingest_file(SAMPLE_DIR / "sample_artefact.md")
        assert doc.section_count >= 5


# ───────────────────────────────────────────────────────────
# CSV parser tests
# ───────────────────────────────────────────────────────────


class TestCsvParser:
    """Test CSV parsing."""

    def test_csv_extracts_columns(self):
        csv_files = list(SAMPLE_DIR.glob("*.csv"))
        assert len(csv_files) > 0
        doc = ingest_file(csv_files[0])
        col_sections = [s for s in doc.sections if s.section_type == "metadata"]
        assert len(col_sections) >= 1

    def test_csv_has_data_summary(self):
        csv_files = list(SAMPLE_DIR.glob("*.csv"))
        doc = ingest_file(csv_files[0])
        summary = [s for s in doc.sections if s.heading == "Data Summary"]
        assert len(summary) == 1
        assert "Total rows" in summary[0].content

    def test_csv_source_type(self):
        csv_files = list(SAMPLE_DIR.glob("*.csv"))
        doc = ingest_file(csv_files[0])
        assert doc.metadata.source_type == SourceType.CSV_DATA


# ───────────────────────────────────────────────────────────
# IngestedDocument model tests
# ───────────────────────────────────────────────────────────


class TestIngestedDocument:
    """Test document serialisation and properties."""

    def test_to_dict(self):
        doc = ingest_file(SAMPLE_DIR / "scope.txt")
        d = doc.to_dict()
        assert "filename" in d
        assert "metadata" in d
        assert "sections" in d
        assert d["is_valid"] is True
        assert d["section_count"] >= 1

    def test_invalid_document(self):
        doc = IngestedDocument(filename="bad.txt", errors=["Parse failed"])
        assert not doc.is_valid
