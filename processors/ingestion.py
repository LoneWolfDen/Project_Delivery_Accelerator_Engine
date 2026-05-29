"""File ingestion module.

Detects file types and routes to appropriate parsers.
Returns structured IngestedDocument objects for context building.

Supported formats:
- Plain text (.txt) – scope docs, call notes, general artefacts
- Markdown (.md) – specs, proposals, structured docs
- CSV (.csv) – resource plans, tracking sheets
- Email (.eml, text-with-headers) – client correspondence
- Transcripts (auto-detected from .txt) – meeting recordings
- PDF (.pdf) – requires pypdf  (pip install pypdf)
- Word (.docx) – requires python-docx  (pip install python-docx)
"""

from pathlib import Path
from typing import List

from models.document import IngestedDocument

# Supported file extensions
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".eml", ".pdf", ".docx"}


def ingest_file(file_path: Path) -> IngestedDocument:
    """Parse a single file and return structured content.

    Detects file type and routes to the appropriate parser.

    Args:
        file_path: Path to the uploaded file.

    Returns:
        IngestedDocument with extracted sections and metadata.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file type is not supported.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    parser = _get_parser(path)
    return parser(path)



def ingest_directory(dir_path: Path) -> List[IngestedDocument]:
    """Ingest all supported files in a directory.

    Args:
        dir_path: Path to directory containing project files.

    Returns:
        List of IngestedDocument objects (one per file).
        Files that fail parsing are included with errors populated.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    documents: List[IngestedDocument] = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                doc = ingest_file(file_path)
                documents.append(doc)
            except Exception as e:
                documents.append(IngestedDocument(
                    filename=file_path.name,
                    file_path=str(file_path),
                    errors=[str(e)],
                ))

    return documents


def _get_parser(file_path: Path):
    """Route to the correct parser based on file extension and content.

    Args:
        file_path: Path to the file.

    Returns:
        Parser function that accepts a Path and returns IngestedDocument.
    """
    extension = file_path.suffix.lower()

    if extension == ".eml":
        from processors.parsers.email_parser import parse
        return parse

    if extension == ".csv":
        from processors.parsers.csv_parser import parse
        return parse

    if extension == ".md":
        from processors.parsers.markdown_parser import parse
        return parse

    if extension == ".txt":
        # Detect if it's an email or transcript
        return _detect_txt_parser(file_path)

    if extension == ".pdf":
        from processors.parsers.pdf_parser import parse
        return parse

    if extension == ".docx":
        from processors.parsers.docx_parser import parse
        return parse

    # Fallback
    from processors.parsers.plain_text import parse
    return parse


def _detect_txt_parser(file_path: Path):
    """Heuristic detection for .txt files: email, transcript, or plain text.

    Reads first 20 lines to classify.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            head_lines = [f.readline() for _ in range(20)]
    except Exception:
        from processors.parsers.plain_text import parse
        return parse

    head_text = "".join(head_lines).lower()

    # Check for email headers
    email_indicators = ["from:", "to:", "subject:", "date:", "sent:"]
    email_hits = sum(1 for ind in email_indicators if ind in head_text)
    if email_hits >= 2:
        from processors.parsers.email_parser import parse
        return parse

    # Check for transcript patterns (speaker turns)
    import re
    speaker_pattern = re.compile(r"^[A-Z][A-Za-z\s.]+:\s", re.MULTILINE)
    timestamp_pattern = re.compile(r"\[\d{1,2}:\d{2}")
    if speaker_pattern.search("".join(head_lines)) or timestamp_pattern.search("".join(head_lines)):
        from processors.parsers.transcript_parser import parse
        return parse

    # Default to plain text
    from processors.parsers.plain_text import parse
    return parse
