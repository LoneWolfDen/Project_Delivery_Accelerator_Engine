"""Markdown parser.

Handles .md files: structured docs, specs, proposals with markdown formatting.
Extracts sections based on # headings.
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

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")


def parse(file_path: Path) -> IngestedDocument:
    """Parse a markdown file into an IngestedDocument.

    Args:
        file_path: Path to the .md file.

    Returns:
        IngestedDocument with heading-based sections.
    """
    raw_text = file_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()
    sections = _extract_sections(lines)
    metadata = _extract_metadata(raw_text, lines, file_path)

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.MARKDOWN,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _extract_sections(lines: List[str]) -> List[DocumentSection]:
    """Extract sections based on markdown headings."""
    sections: List[DocumentSection] = []
    current_heading = ""
    current_content_lines: List[str] = []
    section_start = 0

    for i, line in enumerate(lines):
        match = HEADING_PATTERN.match(line)
        if match:
            # Save previous section
            if current_content_lines or current_heading:
                sections.append(DocumentSection(
                    heading=current_heading,
                    content="\n".join(current_content_lines).strip(),
                    section_type="body",
                    line_start=section_start,
                    line_end=i - 1,
                ))
            current_heading = match.group(2).strip()
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

    # Fallback: no headings found
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
    """Extract metadata from markdown content."""
    # Use first heading as title if available
    title = file_path.stem.replace("_", " ").replace("-", " ").title()
    for line in lines:
        match = HEADING_PATTERN.match(line)
        if match and match.group(1) == "#":
            title = match.group(2).strip()
            break

    return DocumentMetadata(
        title=title,
        source_type=SourceType.ARTEFACT,
        word_count=len(raw_text.split()),
        line_count=len(lines),
    )
