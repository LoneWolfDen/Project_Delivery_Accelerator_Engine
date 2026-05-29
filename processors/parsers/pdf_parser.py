"""PDF parser – extracts text from .pdf files.

Uses ``pypdf`` (pure-Python, open-source, no binary deps) when available.
Falls back to a clear error message if the library is not installed so the
rest of the app continues to work.

Install:
    pip install pypdf          # already included in extras [docs]
"""

from pathlib import Path

from models.document import (
    ContentType,
    DocumentMetadata,
    DocumentSection,
    IngestedDocument,
    SourceType,
)


def parse(file_path: Path) -> IngestedDocument:
    """Parse a PDF file into an IngestedDocument.

    Extracts text page-by-page; each page becomes one DocumentSection.
    Empty pages are skipped.

    Args:
        file_path: Path to the .pdf file.

    Returns:
        IngestedDocument with one section per non-empty page.

    Raises:
        ImportError: If pypdf is not installed.
        ValueError: If the PDF cannot be read (encrypted, corrupt, etc.).
    """
    try:
        import pypdf  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "pypdf is required to parse PDF files. "
            "Install it with:  pip install pypdf"
        ) from exc

    try:
        reader = pypdf.PdfReader(str(file_path))
    except Exception as exc:
        raise ValueError(f"Could not open PDF '{file_path.name}': {exc}") from exc

    sections: list[DocumentSection] = []
    all_text_parts: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = text.strip()
        if not text:
            continue

        all_text_parts.append(text)
        sections.append(
            DocumentSection(
                heading=f"Page {page_num}",
                content=text,
                section_type="body",
                line_start=(page_num - 1) * 1,
                line_end=page_num,
            )
        )

    raw_text = "\n\n".join(all_text_parts)

    # Fallback: if pypdf extracted nothing (scanned/image PDF)
    if not sections:
        sections.append(
            DocumentSection(
                heading="",
                content=(
                    "[No text extracted – this PDF may contain scanned images. "
                    "Consider converting to a text-based format.]"
                ),
                section_type="body",
                line_start=0,
                line_end=0,
            )
        )
        raw_text = sections[0].content

    metadata = DocumentMetadata(
        title=file_path.stem.replace("_", " ").replace("-", " ").title(),
        source_type=_detect_source_type(raw_text, file_path),
        word_count=len(raw_text.split()),
        line_count=len(reader.pages),
    )

    return IngestedDocument(
        filename=file_path.name,
        file_path=str(file_path),
        content_type=ContentType.TEXT,
        metadata=metadata,
        sections=sections,
        raw_text=raw_text,
    )


def _detect_source_type(raw_text: str, file_path: Path) -> SourceType:
    """Heuristic source-type detection (mirrors plain_text parser logic)."""
    lower = raw_text.lower()
    name_lower = file_path.stem.lower()

    if any(k in name_lower for k in ("scope", "sow", "statement_of_work")):
        return SourceType.SOW
    if "proposal" in name_lower:
        return SourceType.PROPOSAL
    if any(k in name_lower for k in ("requirement", "nfr", "spec")):
        return SourceType.REQUIREMENTS
    if any(k in lower for k in ("scope of work", "deliverables", "statement of work")):
        return SourceType.SOW
    if any(k in lower for k in ("action items", "next steps", "meeting notes")):
        return SourceType.CALL_NOTES

    return SourceType.ARTEFACT
