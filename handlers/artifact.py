"""Artifact handlers — upload, text, toggle, delete, process, patch."""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Callable, Dict

from db.artifact_store_sql import (
    delete_artifact,
    list_artifacts,
    store_file_artifact,
    store_text_artifact,
    toggle_artifact_include,
)
from models.artifact import Artifact, validate_metadata_for_category
from processors.artifact_store import _load_registry, _save_registry
from processors.pipeline import JobStore, process_all_artifacts, process_artifact

logger = logging.getLogger(__name__)


def handle_list_artifacts(project_id: str, respond: Callable) -> None:
    respond({"artifacts": list_artifacts(project_id)})


def handle_artifact_upload(
    project_id: str,
    body: Dict[str, Any],
    respond: Callable,
    *,
    raw_multipart: bytes = b"",
    content_type: str = "",
) -> None:
    """Handle file artifact upload.

    ``raw_multipart`` / ``content_type`` are set by the HTTP layer when the
    request is multipart/form-data.  Otherwise ``body`` carries a base64
    payload.
    """
    file_content = b""
    file_name = ""
    category = ""
    title = ""
    metadata: Dict[str, Any] = {}

    if raw_multipart:
        file_content, file_name, category, title, metadata = _parse_multipart(
            raw_multipart, content_type
        )
    else:
        file_name = body.get("fileName", body.get("file_name", ""))
        content_b64 = body.get("content", "")
        category = body.get("category", "")
        title = body.get("title", "")
        metadata = body.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        if not file_name:
            respond({"error": "fileName is required"}, status=400)
            return
        if not content_b64:
            respond({"error": "content (base64) is required"}, status=400)
            return
        try:
            file_content = base64.b64decode(content_b64)
        except Exception:
            respond({"error": "Invalid base64 content"}, status=400)
            return

    if not category:
        respond({"error": "category is required"}, status=400)
        return

    try:
        artifact = store_file_artifact(
            project_id=project_id,
            file_name=file_name,
            file_content=file_content,
            category=category,
            title=title,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        respond({"artifact": artifact.to_api_dict()}, status=201)
    except ValueError as e:
        respond({"error": str(e)}, status=400)


def handle_artifact_text(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    text = body.get("text", "")
    category = body.get("category", "")
    title = body.get("title", "")
    metadata = body.get("metadata", {})

    if not category:
        respond({"errorCode": "INVALID_REQUEST", "message": "category is required"}, status=400)
        return
    if not text or not text.strip():
        respond({"errorCode": "INVALID_REQUEST", "message": "text is required"}, status=400)
        return

    if metadata and isinstance(metadata, dict):
        valid, errors = validate_metadata_for_category(category, metadata)
        if not valid:
            respond({"errorCode": "INVALID_REQUEST", "message": "; ".join(errors)}, status=400)
            return

    try:
        artifact = store_text_artifact(
            project_id=project_id,
            text=text,
            category=category,
            title=title,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        respond({"artifact": artifact.to_api_dict()}, status=201)
    except ValueError as e:
        respond({"error": str(e)}, status=400)


def handle_artifact_toggle(
    project_id: str, artifact_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    result = toggle_artifact_include(project_id, artifact_id, body.get("include", True))
    if result:
        respond({"artifact": result})
    else:
        respond({"error": "Artifact not found"}, status=404)


def handle_artifact_delete(
    project_id: str, artifact_id: str, respond: Callable
) -> None:
    if delete_artifact(project_id, artifact_id):
        respond({"status": "deleted", "artifactId": artifact_id})
    else:
        respond({"errorCode": "NOT_FOUND", "message": "Artifact not found"}, status=404)


def handle_process_artifact(
    project_id: str, artifact_id: str, respond: Callable
) -> None:
    try:
        job = process_artifact(project_id, artifact_id)
        respond({"job": job}, status=202)
    except Exception as e:
        respond({"errorCode": "INTERNAL_ERROR", "message": str(e)}, status=500)


def handle_process_all_artifacts(
    project_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    try:
        queued_ids = process_all_artifacts(
            project_id,
            body.get("onlyIncluded", True),
            force=body.get("force", True),
        )
        respond({"queuedArtifactIds": queued_ids}, status=202)
    except Exception as e:
        respond({"errorCode": "INTERNAL_ERROR", "message": str(e)}, status=500)


def handle_get_job(job_id: str, respond: Callable) -> None:
    job = JobStore.get_job(job_id)
    if job:
        respond(job)
    else:
        respond({"errorCode": "NOT_FOUND", "message": f"Job not found: {job_id}"}, status=404)


def handle_patch_artifact(
    project_id: str, artifact_id: str, body: Dict[str, Any], respond: Callable
) -> None:
    if not body:
        respond({"errorCode": "INVALID_REQUEST", "message": "Request body required"}, status=400)
        return

    registry = _load_registry(project_id)
    updated = False
    result_artifact = None

    for entry in registry:
        if entry.get("artifact_id") == artifact_id:
            if "include" in body:
                entry["include"] = bool(body["include"])
            if "title" in body:
                entry["title"] = body["title"]
            if "metadata" in body and isinstance(body["metadata"], dict):
                valid, errors = validate_metadata_for_category(
                    entry.get("category", ""), body["metadata"]
                )
                if not valid:
                    respond({"errorCode": "INVALID_REQUEST", "message": "; ".join(errors)}, status=400)
                    return
                entry["metadata"] = body["metadata"]
            updated = True
            result_artifact = Artifact.from_storage_dict(entry)
            break

    if not updated:
        respond({"errorCode": "NOT_FOUND", "message": "Artifact not found"}, status=404)
        return

    _save_registry(project_id, registry)
    respond({"artifact": result_artifact.to_api_dict()})


# ── Internal helper ────────────────────────────────────────────────────────────

def _parse_multipart(raw_data: bytes, content_type: str):
    """Extract (file_content, file_name, category, title, metadata) from raw multipart."""
    import re

    boundary_match = re.search(r"boundary=([^\s;]+)", content_type)
    if not boundary_match:
        return b"", "", "", "", {}

    boundary = boundary_match.group(1).encode()
    parts = raw_data.split(b"--" + boundary)

    file_content = b""
    file_name = ""
    category = ""
    title = ""
    metadata: Dict[str, Any] = {}

    for part in parts:
        if not part or part in (b"--\r\n", b"--"):
            continue
        if b"\r\n\r\n" not in part:
            continue
        headers_raw, body_bytes = part.split(b"\r\n\r\n", 1)
        headers_str = headers_raw.decode("utf-8", errors="replace")
        if body_bytes.endswith(b"\r\n"):
            body_bytes = body_bytes[:-2]

        name_match = re.search(r'name="([^"]+)"', headers_str)
        filename_match = re.search(r'filename="([^"]+)"', headers_str)

        if not name_match:
            continue
        field_name = name_match.group(1)

        if filename_match:
            file_name = filename_match.group(1)
            file_content = body_bytes
        elif field_name == "category":
            category = body_bytes.decode("utf-8", errors="replace").strip()
        elif field_name == "title":
            title = body_bytes.decode("utf-8", errors="replace").strip()
        elif field_name == "metadata":
            try:
                metadata = json.loads(body_bytes.decode("utf-8", errors="replace"))
            except Exception:
                metadata = {}

    return file_content, file_name, category, title, metadata
