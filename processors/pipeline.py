"""Processing Pipeline – Standardised artifact processing.

Pipeline stages: ingested → processing → processed | failed

Offline only (no AI API calls). Extracts text content from raw artifacts
and produces a unified ProcessedDocument JSON output.

Output stored under /projects/{projectId}/processed/{artifactId}.json

ProcessedDocument schema:
{
    "artifactId": "a_123",
    "projectId": "p_001",
    "category": "delivery_notes",
    "metadata": {...},
    "content": "extracted text...",
    "contentType": "text/plain",
    "tags": [],
    "createdAt": "2026-05-28T15:20:02Z"
}
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.artifact import (
    Artifact,
    ArtifactStatus,
    now_iso,
)
from processors.artifact_store import (
    get_artifact,
    get_artifact_text_content,
    update_artifact_status,
    _load_registry,
)

PROJECTS_DIR = Path("projects_data")


# ──────────────────────────────────────────────────────────────
# Job Tracking
# ──────────────────────────────────────────────────────────────

class JobStore:
    """Simple file-based job tracking.

    Jobs stored in /projects_data/jobs/{jobId}.json
    Designed for synchronous processing with job status tracking.
    """

    JOBS_DIR = PROJECTS_DIR / "jobs"

    @classmethod
    def create_job(cls, artifact_id: str, project_id: str) -> Dict[str, Any]:
        """Create a new processing job."""
        cls.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        job_id = f"j_{uuid.uuid4().hex[:6]}"
        job = {
            "jobId": job_id,
            "artifactId": artifact_id,
            "projectId": project_id,
            "status": "queued",
            "startedAt": None,
            "endedAt": None,
            "error": None,
            "createdAt": now_iso(),
        }
        cls._save_job(job)
        return job

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        path = cls.JOBS_DIR / f"{job_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            return json.load(f)

    @classmethod
    def update_job(
        cls,
        job_id: str,
        status: str,
        error: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update job status."""
        job = cls.get_job(job_id)
        if job is None:
            return None

        job["status"] = status
        if status == "processing" and not job["startedAt"]:
            job["startedAt"] = now_iso()
        if status in ("succeeded", "failed"):
            job["endedAt"] = now_iso()
        if error:
            job["error"] = error

        cls._save_job(job)
        return job

    @classmethod
    def _save_job(cls, job: Dict[str, Any]) -> None:
        """Persist job to disk."""
        cls.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        path = cls.JOBS_DIR / f"{job['jobId']}.json"
        with open(path, "w") as f:
            json.dump(job, f, indent=2)


# ──────────────────────────────────────────────────────────────
# Processing Pipeline
# ──────────────────────────────────────────────────────────────


def process_artifact(project_id: str, artifact_id: str) -> Dict[str, Any]:
    """Process a single artifact through the pipeline.

    Stages: ingested → processing → processed | failed

    Steps:
    1. Create job record
    2. Update artifact status to 'processing'
    3. Extract text content from raw artifact
    4. Build ProcessedDocument
    5. Save to /projects/{projectId}/processed/{artifactId}.json
    6. Update artifact status to 'processed' (or 'failed')
    7. Update job to 'succeeded' (or 'failed')

    Runs synchronously (offline, no AI calls).

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID to process.

    Returns:
        Job record dict.
    """
    # Create job
    job = JobStore.create_job(artifact_id, project_id)
    job_id = job["jobId"]

    # Get artifact
    artifact = get_artifact(project_id, artifact_id)
    if artifact is None:
        JobStore.update_job(job_id, "failed", "Artifact not found")
        return JobStore.get_job(job_id)

    # Update status to processing
    update_artifact_status(project_id, artifact_id, ArtifactStatus.PROCESSING.value)
    JobStore.update_job(job_id, "processing")

    try:
        # Extract text content
        content = get_artifact_text_content(project_id, artifact_id)

        if not content or not content.strip():
            raise ValueError("No text content could be extracted from artifact")

        # Determine content type
        content_type = _detect_content_type(artifact, content)

        # Extract tags (simple keyword extraction, offline)
        tags = _extract_tags(content, artifact.category)

        # Build ProcessedDocument
        processed_doc = {
            "artifactId": artifact_id,
            "projectId": project_id,
            "category": artifact.category,
            "metadata": artifact.metadata,
            "content": content,
            "contentType": content_type,
            "tags": tags,
            "createdAt": now_iso(),
        }

        # Save processed output
        _save_processed_document(project_id, artifact_id, processed_doc)

        # Update artifact status to processed
        update_artifact_status(project_id, artifact_id, ArtifactStatus.PROCESSED.value)
        JobStore.update_job(job_id, "succeeded")

    except Exception as e:
        # Mark as failed
        update_artifact_status(project_id, artifact_id, ArtifactStatus.FAILED.value)
        JobStore.update_job(job_id, "failed", str(e))

    return JobStore.get_job(job_id)


def process_all_artifacts(
    project_id: str, only_included: bool = True
) -> List[str]:
    """Process all eligible artifacts for a project.

    Args:
        project_id: Project ID.
        only_included: If True, only process artifacts with include=True.

    Returns:
        List of queued artifact IDs.
    """
    registry = _load_registry(project_id)
    queued_ids: List[str] = []

    for entry in registry:
        artifact = Artifact.from_storage_dict(entry)

        # Skip if not included (when only_included=True)
        if only_included and not artifact.include:
            continue

        # Skip if already processed (re-processing allowed by re-running)
        # Process all that are in 'ingested' or 'failed' status
        if artifact.status not in (
            ArtifactStatus.INGESTED.value,
            ArtifactStatus.FAILED.value,
        ):
            continue

        # Process synchronously
        process_artifact(project_id, artifact.artifact_id)
        queued_ids.append(artifact.artifact_id)

    return queued_ids


def get_processed_document(
    project_id: str, artifact_id: str
) -> Optional[Dict[str, Any]]:
    """Get the processed document output for an artifact.

    Args:
        project_id: Project ID.
        artifact_id: Artifact ID.

    Returns:
        ProcessedDocument dict, or None if not found.
    """
    path = _processed_path(project_id, artifact_id)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────
# Internal Helpers
# ──────────────────────────────────────────────────────────────


def _processed_dir(project_id: str) -> Path:
    """Get processed output directory for a project."""
    d = PROJECTS_DIR / project_id / "processed"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _processed_path(project_id: str, artifact_id: str) -> Path:
    """Get the path for a processed document."""
    return _processed_dir(project_id) / f"{artifact_id}.json"


def _save_processed_document(
    project_id: str, artifact_id: str, doc: Dict[str, Any]
) -> None:
    """Save processed document to disk."""
    path = _processed_path(project_id, artifact_id)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)


def _detect_content_type(artifact: Artifact, content: str) -> str:
    """Detect content type based on file extension and content.

    Returns:
        One of: text/plain, text/markdown, application/json
    """
    file_name = artifact.file_name.lower() if artifact.file_name else ""

    if file_name.endswith(".md"):
        return "text/markdown"
    if file_name.endswith(".json"):
        return "application/json"

    # Check if content looks like markdown
    md_indicators = ["# ", "## ", "- ", "* ", "```", "**", "__"]
    if any(indicator in content[:500] for indicator in md_indicators):
        return "text/markdown"

    # Check if content is valid JSON
    if content.strip().startswith("{") or content.strip().startswith("["):
        try:
            json.loads(content)
            return "application/json"
        except (json.JSONDecodeError, ValueError):
            pass

    return "text/plain"


def _extract_tags(content: str, category: str) -> List[str]:
    """Extract simple keyword tags from content (offline, no AI).

    Uses basic heuristic: looks for common project delivery keywords.

    Args:
        content: Text content.
        category: Artifact category for context.

    Returns:
        List of tag strings (max 10).
    """
    tags: List[str] = []

    # Always include category as a tag
    tags.append(category)

    # Common delivery keywords to detect
    keywords = {
        "risk": "risk",
        "dependency": "dependency",
        "blocker": "blocker",
        "deadline": "deadline",
        "milestone": "milestone",
        "budget": "budget",
        "stakeholder": "stakeholder",
        "requirement": "requirement",
        "constraint": "constraint",
        "assumption": "assumption",
        "decision": "decision",
        "action": "action_item",
        "security": "security",
        "performance": "performance",
        "migration": "migration",
        "integration": "integration",
        "testing": "testing",
        "deployment": "deployment",
    }

    content_lower = content.lower()
    for keyword, tag in keywords.items():
        if keyword in content_lower:
            tags.append(tag)

    # Deduplicate and cap at 10
    seen = set()
    unique_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    return unique_tags[:10]
