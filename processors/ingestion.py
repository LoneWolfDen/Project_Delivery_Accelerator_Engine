"""File ingestion module.

Parses uploaded documents (SoW, transcripts, CSVs, PDFs, etc.)
and converts them into normalised text blocks for context building.
"""

from pathlib import Path
from typing import Dict, List, Any


def ingest_file(file_path: Path) -> Dict[str, Any]:
    """Parse a single file and return structured content.

    Args:
        file_path: Path to the uploaded file.

    Returns:
        Dictionary with keys: filename, content_type, sections, raw_text.
    """
    raise NotImplementedError("Ingestion pipeline not yet implemented")


def ingest_directory(dir_path: Path) -> List[Dict[str, Any]]:
    """Ingest all supported files in a directory.

    Args:
        dir_path: Path to directory containing project files.

    Returns:
        List of ingested file dictionaries.
    """
    raise NotImplementedError("Batch ingestion not yet implemented")
