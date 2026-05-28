"""Artifact Store – Persistence layer for artefact registry.

Stores artifacts in:
- /projects_data/{project_id}/raw/          (uploaded files & text blobs)
- /projects_data/{project_id}/artifacts.json (registry index)

Designed for single-container Docker, offline-first, file-based storage.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.artifact import (
    Artifact,
    ArtifactStatus,
    generate_artifact_id,
    now_iso,
    validate_category,
    validate_file_extension,
    VALID_CATEGORIES,
)

PROJECTS_DIR = Path("projects_data")


def _project_dir(project_id: str) -> Path:
    """Get project data directory."""
    return PROJECTS_DIR / project_id


def _raw_dir(project_id: str) -> Path:
    """Get raw storage directory for a project."""
    d = _project_dir(project_id) / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _registry_path(project_id: str) -> Path:
    """Get artifact registry file path."""
    return _project_dir(project_id) / "artifacts.json"


def _load_registry(project_id: str) -> List[Dict[str, Any]]:
    """Load artifact registry from disk."""
    path = _registry_path(project_id)
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _save_registry(project_id: str, artifacts: List[Dict[str, Any]]) -> None:
    """Save artifact registry to disk."""
    path = _registry_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(artifacts, f, indent=2)


def store_file_artifact(
    project_id: str,
    file_name: str,
    file_content: bytes,
    category: str,
    title: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Artifact:
    """Store an uploaded file artifact.

    Saves binary content to raw/ and registers in artifacts.json.

    Args:
        project_id: Project ID.
        file_name: Original filename.
        file_content: Binary file content.
        category: Artifact category (required, must be valid).
        title: Optional human-readable title.
        metadata: Optional additional metadata.

    Returns:
        Created Artifact instance.

    Raises:
        ValueError: If category invalid or file extension not supported.
    """
    if not validate_category(category):
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )

    if not validate_file_extension(file_name):
        raise ValueError(
            f"Unsupported file type for '{file_name}'. "
            f"Supported extensions: .txt, .md, .csv, .eml, .json, .yaml, .yml, .pdf, .docx, .xlsx, .pptx"
        )

    artifact_id = generate_artifact_id()
    raw_dir = _raw_dir(project_id)

    # Save file to raw/ with artifact_id prefix to avoid collisions
    safe_name = f"{artifact_id}_{file_name}"
    raw_path = raw_dir / safe_name
    with open(raw_path, "wb") as f:
        f.write(file_content)

    artifact = Artifact(
        artifact_id=artifact_id,
        project_id=project_id,
        type="file",
        file_name=file_name,
        title=title or file_name,
        category=category,
        metadata=metadata or {},
        include=True,
        status=ArtifactStatus.INGESTED.value,
        created_at=now_iso(),
        raw_path=str(raw_path),
    )

    # Add to registry
    registry = _load_registry(project_id)
    registry.append(artifact.to_storage_dict())
    _save_registry(project_id, registry)

    return artifact


def store_text_artifact(
    project_id: str,
    text: str,
    category: str,
    title: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Artifact:
    """Store a text (pasted) artifact.

    Saves text content as JSON blob in raw/ and registers in artifacts.json.

    Args:
        project_id: Project ID.
        text: Text content to store.
        category: Artifact category (required, must be valid).
        title: Optional human-readable title.
        metadata: Optional additional metadata.

    Returns:
        Created Artifact instance.

    Raises:
        ValueError: If category invalid or text empty.
    """
    if not validate_category(category):
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}"
        )

    if not text or not text.strip():
        raise ValueError("Text content cannot be empty")

    artifact_id = generate_artifact_id()
    raw_dir = _raw_dir(project_id)

    # Save text as JSON blob in raw/
    text_file = raw_dir / f"{artifact_id}_text.json"
    text_blob = {
        "artifact_id": artifact_id,
        "title": title,
        "text": text,
        "metadata": metadata or {},
        "created_at": now_iso(),
    }
    with open(text_file, "w") as f:
        json.dump(text_blob, f, indent=2)

    artifact = Artifact(
        artifact_id=artifact_id,
        project_id=project_id,
        type="text",
        file_name="",
        title=title or "Pasted text",
        category=category,
        metadata=metadata or {},
        include=True,
        status=ArtifactStatus.INGESTED.value,
        created_at=now_iso(),
        raw_path=str(text_file),
        text_content=text,
    )

    # Add to registry
    registry = _load_registry(project_id)
    registry.append(artifact.to_storage_dict())
    _save_registry(project_id, registry)

    return artifact


def list_artifacts(project_id: str) -> List[Dict[str, Any]]:
    """List all artifacts for a project (API format).

    Args:
        project_id: Project ID.

    Returns:
        List of artifact dicts in API response format.
    """
    registry = _load_registry(project_id)
    return [Artifact.from_storage_dict(a).to_api_dict() for a in registry]


def get_artifact(project_id: str, artifact_id: str) -> Optional[Artifact]:
    """Get a single artifact by ID.

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.

    Returns:
        Artifact instance, or None if not found.
    """
    registry = _load_registry(project_id)
    for a in registry:
        if a.get("artifact_id") == artifact_id:
            return Artifact.from_storage_dict(a)
    return None


def toggle_artifact_include(
    project_id: str, artifact_id: str, include: bool
) -> Optional[Dict[str, Any]]:
    """Toggle artifact include/exclude state.

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.
        include: New include state.

    Returns:
        Updated artifact API dict, or None if not found.
    """
    registry = _load_registry(project_id)
    for a in registry:
        if a.get("artifact_id") == artifact_id:
            a["include"] = include
            _save_registry(project_id, registry)
            return Artifact.from_storage_dict(a).to_api_dict()
    return None


def update_artifact_status(
    project_id: str, artifact_id: str, status: str
) -> Optional[Dict[str, Any]]:
    """Update artifact processing status.

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.
        status: New status (ingested/processing/processed/failed).

    Returns:
        Updated artifact API dict, or None if not found.
    """
    registry = _load_registry(project_id)
    for a in registry:
        if a.get("artifact_id") == artifact_id:
            a["status"] = status
            _save_registry(project_id, registry)
            return Artifact.from_storage_dict(a).to_api_dict()
    return None


def delete_artifact(project_id: str, artifact_id: str) -> bool:
    """Delete an artifact (remove from registry and raw storage).

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.

    Returns:
        True if deleted, False if not found.
    """
    registry = _load_registry(project_id)
    updated = []
    deleted = False
    for a in registry:
        if a.get("artifact_id") == artifact_id:
            # Remove raw file
            raw_path = a.get("raw_path", "")
            if raw_path:
                p = Path(raw_path)
                if p.exists():
                    p.unlink()
            deleted = True
        else:
            updated.append(a)

    if deleted:
        _save_registry(project_id, updated)
    return deleted


def get_artifact_text_content(project_id: str, artifact_id: str) -> str:
    """Get text content of an artifact (for processing).

    For text artifacts: returns stored text.
    For file artifacts: reads file content (text-based files only).

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.

    Returns:
        Text content string.
    """
    artifact = get_artifact(project_id, artifact_id)
    if artifact is None:
        return ""

    if artifact.type == "text":
        # Load from stored text blob
        if artifact.text_content:
            return artifact.text_content
        if artifact.raw_path:
            p = Path(artifact.raw_path)
            if p.exists():
                with open(p) as f:
                    blob = json.load(f)
                return blob.get("text", "")
        return ""

    # File type: read text content
    if artifact.raw_path:
        p = Path(artifact.raw_path)
        if p.exists():
            ext = p.suffix.lower()
            if ext in {".txt", ".md", ".csv", ".eml", ".json", ".yaml", ".yml"}:
                with open(p) as f:
                    return f.read()
    return ""
