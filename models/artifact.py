"""Artifact Model – Schema and storage for ingested artefacts.

Supports two artifact types:
- file: Uploaded binary files (stored in raw/)
- text: Pasted text content (stored as JSON in raw/)

Every artifact has a mandatory category:
- project_artefact
- meetings_comms
- delivery_notes
- client_context
- architecture_design
- external_data

Designed for:
- Single-container Docker (file-based storage)
- Offline-first operation
- Non-technical users
- Open-source components only
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactType(str, Enum):
    FILE = "file"
    TEXT = "text"


class ArtifactCategory(str, Enum):
    PROJECT_ARTEFACT = "project_artefact"
    MEETINGS_COMMS = "meetings_comms"
    DELIVERY_NOTES = "delivery_notes"
    CLIENT_CONTEXT = "client_context"
    ARCHITECTURE_DESIGN = "architecture_design"
    EXTERNAL_DATA = "external_data"


class ArtifactStatus(str, Enum):
    INGESTED = "ingested"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# Valid categories list for validation
VALID_CATEGORIES = [c.value for c in ArtifactCategory]

# Supported file extensions for upload
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".eml", ".json", ".yaml", ".yml",
    ".pdf", ".docx", ".xlsx", ".pptx",
}


@dataclass
class Artifact:
    """Artifact data model.

    Matches the JSON schema specification:
    {
        "artifactId": "a_123",
        "projectId": "p_001",
        "type": "file" | "text",
        "fileName": "scope.pdf",
        "title": "Client scope document",
        "category": "project_artefact",
        "metadata": {},
        "include": true,
        "status": "ingested",
        "createdAt": "2026-05-28T15:10:00Z"
    }
    """

    artifact_id: str = ""
    project_id: str = ""
    type: str = "file"
    file_name: str = ""
    title: str = ""
    category: str = "project_artefact"
    metadata: Dict[str, Any] = field(default_factory=dict)
    include: bool = True
    status: str = "ingested"
    created_at: str = ""
    # Internal: path to raw file on disk
    raw_path: str = ""
    # Internal: extracted text content (for processing)
    text_content: str = ""

    def to_api_dict(self) -> Dict[str, Any]:
        """Serialize to API response format (camelCase keys)."""
        return {
            "artifactId": self.artifact_id,
            "projectId": self.project_id,
            "type": self.type,
            "fileName": self.file_name,
            "title": self.title,
            "category": self.category,
            "metadata": self.metadata,
            "include": self.include,
            "status": self.status,
            "createdAt": self.created_at,
        }

    def to_storage_dict(self) -> Dict[str, Any]:
        """Serialize for disk storage (includes internal fields)."""
        return asdict(self)

    @classmethod
    def from_storage_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Deserialize from disk storage."""
        return cls(
            artifact_id=data.get("artifact_id", ""),
            project_id=data.get("project_id", ""),
            type=data.get("type", "file"),
            file_name=data.get("file_name", ""),
            title=data.get("title", ""),
            category=data.get("category", "project_artefact"),
            metadata=data.get("metadata", {}),
            include=data.get("include", True),
            status=data.get("status", "ingested"),
            created_at=data.get("created_at", ""),
            raw_path=data.get("raw_path", ""),
            text_content=data.get("text_content", ""),
        )


def generate_artifact_id() -> str:
    """Generate a unique artifact ID."""
    return f"a_{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def validate_category(category: str) -> bool:
    """Validate that category is one of the allowed values."""
    return category in VALID_CATEGORIES


def validate_file_extension(filename: str) -> bool:
    """Validate that file extension is supported."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS
