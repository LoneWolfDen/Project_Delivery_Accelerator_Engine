"""CSV parser.

Handles .csv files: resource plans, tracking sheets, requirement lists.
Extracts column headers, row counts, and summary statistics.
"""

import csv
from pathlib import Path
from typing import List

from models.document import (
    ContentType,
    DocumentMetadata,
    DocumentSection,
    IngestedDocument,
    SourceType,
)



def parse(file_path: Path) -> IngestedDocument:
    """Parse a CSV file into an IngestedDocument.

    Args:
        file_path: Path to the .csv file.

    Returns:
        IngestedDocument with column headers and row summary.
    """
    raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = raw_text.splitlines()

    rows: List[List[str]] = []
    try:
        reader = csv.reader(lines)
        rows = list(reader)
    except csv.Error:
        return IngestedDocument(
            filename=file_path.name,
            file_path=str(file_path),
            content_type=ContentType.CSV,
            raw_text=raw_text,
            errors=["Failed to parse CSV"],
        )

    headers = rows[0] if rows else []
    data_rows = rows[1:] if len(rows) > 1 else []
    sections = _build_sections(headers, data_rows)
    metadata = _build_metadata(file_path, headers, data_rows, raw_text, lines)

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.CSV,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )



def _build_sections(
    headers: List[str], data_rows: List[List[str]]
) -> List[DocumentSection]:
    """Build sections from CSV data."""
    sections: List[DocumentSection] = []

    # Column headers section
    if headers:
        sections.append(DocumentSection(
            heading="Columns",
            content=", ".join(headers),
            section_type="metadata",
            line_start=0,
            line_end=0,
        ))

    # Summary section
    if data_rows:
        summary_lines = [
            f"Total rows: {len(data_rows)}",
            f"Total columns: {len(headers)}",
        ]
        # Show first 3 rows as sample
        sample_count = min(3, len(data_rows))
        for i in range(sample_count):
            row_dict = dict(zip(headers, data_rows[i])) if headers else {}
            row_str = "; ".join(f"{k}: {v}" for k, v in row_dict.items())
            summary_lines.append(f"Row {i+1}: {row_str}")

        sections.append(DocumentSection(
            heading="Data Summary",
            content="\n".join(summary_lines),
            section_type="body",
            line_start=1,
            line_end=len(data_rows),
        ))

    return sections


def _build_metadata(
    file_path: Path,
    headers: List[str],
    data_rows: List[List[str]],
    raw_text: str,
    lines: List[str],
) -> DocumentMetadata:
    """Build metadata for a CSV file."""
    return DocumentMetadata(
        title=file_path.stem.replace("_", " ").replace("-", " ").title(),
        source_type=SourceType.CSV_DATA,
        word_count=len(raw_text.split()),
        line_count=len(lines),
        tags=[f"cols:{len(headers)}", f"rows:{len(data_rows)}"],
    )
