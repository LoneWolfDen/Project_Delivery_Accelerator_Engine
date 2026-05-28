"""Document models for the ingestion pipeline.

Defines the structure for ingested documents, sections, and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Any, Optional


class SourceType(str, Enum):
    """Type of source document."""

    EMAIL = "email"
    TRANSCRIPT = "transcript"
    CALL_NOTES = "call_notes"
    SOW = "sow"
    PROPOSAL = "proposal"
    REQUIREMENTS = "requirements"
    ARTEFACT = "artefact"
    CSV_DATA = "csv_data"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """File content type classification."""

    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    CSV = "text/csv"
    EMAIL = "message/rfc822"
    HTML = "text/html"
    UNKNOWN = "application/octet-stream"


@dataclass
class DocumentSection:
    """A logical section within an ingested document."""

    heading: str = ""
    content: str = ""
    section_type: str = "body"  # header | body | action_item | speaker_turn | metadata
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    line_start: int = 0
    line_end: int = 0


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document."""

    title: str = ""
    subject: str = ""
    source_type: SourceType = SourceType.UNKNOWN
    date: Optional[str] = None
    author: Optional[str] = None
    participants: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    word_count: int = 0
    line_count: int = 0


@dataclass
class IngestedDocument:
    """A fully parsed and structured document."""

    filename: str = ""
    file_path: str = ""
    content_type: ContentType = ContentType.UNKNOWN
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    sections: List[DocumentSection] = field(default_factory=list)
    raw_text: str = ""
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if document was ingested without errors."""
        return len(self.errors) == 0 and len(self.raw_text) > 0

    @property
    def section_count(self) -> int:
        """Number of extracted sections."""
        return len(self.sections)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "content_type": self.content_type.value,
            "metadata": {
                "title": self.metadata.title,
                "subject": self.metadata.subject,
                "source_type": self.metadata.source_type.value,
                "date": self.metadata.date,
                "author": self.metadata.author,
                "participants": self.metadata.participants,
                "tags": self.metadata.tags,
                "word_count": self.metadata.word_count,
                "line_count": self.metadata.line_count,
            },
            "sections": [
                {
                    "heading": s.heading,
                    "content": s.content,
                    "section_type": s.section_type,
                    "speaker": s.speaker,
                    "timestamp": s.timestamp,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                }
                for s in self.sections
            ],
            "raw_text": self.raw_text,
            "ingested_at": self.ingested_at,
            "errors": self.errors,
            "is_valid": self.is_valid,
            "section_count": self.section_count,
        }
