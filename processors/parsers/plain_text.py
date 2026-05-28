"""Plain text parser.

Handles .txt files: scope documents, call notes, general artefacts.
Splits on blank-line-separated blocks and heading-like patterns.
"""

import re
from pathlib import Path
from typing import List

from models.document import (
    ContentType,
    DocumentMetadata,
    DocumentSection,
    IngestedDocument,
    SourceType,
)


# Patterns for detecting structure in plain text
HEADING_PATTERN = re.compile(r"^([A-Z][A-Za-z /&\-]+)$")
BULLET_PATTERN = re.compile(r"^\s*[-*•]\s+")
NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+")


def parse(file_path: Path) -> IngestedDocument:
    """Parse a plain text file into an IngestedDocument.

    Args:
        file_path: Path to the .txt file.

    Returns:
        IngestedDocument with extracted sections and metadata.
    """
    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = file_path.read_text(encoding="latin-1")

    lines = raw_text.splitlines()
    sections = _extract_sections(lines)
    metadata = _extract_metadata(raw_text, lines, file_path)

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.TEXT,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _extract_sections(lines: List[str]) -> List[DocumentSection]:
    """Split text into logical sections based on headings and blank lines."""
    sections: List[DocumentSection] = []
    current_heading = ""
    current_content_lines: List[str] = []
    section_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect heading: all-caps-like line, not a bullet, at least 3 chars
        if HEADING_PATTERN.match(stripped) and len(stripped) >= 3 and not BULLET_PATTERN.match(line):
            # Save previous section
            if current_content_lines or current_heading:
                sections.append(DocumentSection(
                    heading=current_heading,
                    content="\n".join(current_content_lines).strip(),
                    section_type="body",
                    line_start=section_start,
                    line_end=i - 1,
                ))
            current_heading = stripped
            current_content_lines = []
            section_start = i
        else:
            current_content_lines.append(line)

    # Final section
    if current_content_lines or current_heading:
        sections.append(DocumentSection(
            heading=current_heading,
            content="\n".join(current_content_lines).strip(),
            section_type="body",
            line_start=section_start,
            line_end=len(lines) - 1,
        ))

    # If no sections were created (no headings found), treat as single body
    if not sections and lines:
        sections.append(DocumentSection(
            heading="",
            content="\n".join(lines).strip(),
            section_type="body",
            line_start=0,
            line_end=len(lines) - 1,
        ))

    return sections


def _extract_metadata(raw_text: str, lines: List[str], file_path: Path) -> DocumentMetadata:
    """Extract metadata from plain text content."""
    source_type = _detect_source_type(raw_text, file_path)

    return DocumentMetadata(
        title=file_path.stem.replace("_", " ").replace("-", " ").title(),
        source_type=source_type,
        word_count=len(raw_text.split()),
        line_count=len(lines),
    )


def _detect_source_type(raw_text: str, file_path: Path) -> SourceType:
    """Heuristic detection of what kind of document this is."""
    lower = raw_text.lower()
    name_lower = file_path.stem.lower()

    if "meeting" in name_lower or "transcript" in name_lower or "call" in name_lower:
        return SourceType.CALL_NOTES
    if "scope" in name_lower or "sow" in name_lower:
        return SourceType.SOW
    if "proposal" in name_lower:
        return SourceType.PROPOSAL
    if "requirement" in name_lower or "nfr" in name_lower:
        return SourceType.REQUIREMENTS

    # Content-based detection
    if "action items" in lower or "next steps" in lower:
        return SourceType.CALL_NOTES
    if "scope of work" in lower or "deliverables" in lower:
        return SourceType.SOW
    if "migration" in lower and "application" in lower:
        return SourceType.ARTEFACT

    return SourceType.PLAIN_TEXT
