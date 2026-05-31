"""Ingest handlers — file ingestion and validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

import services.ingest as svc
import services.admin as admin_svc


def handle_ingest(body: Dict[str, Any], respond: Callable) -> None:
    project_id = body.get("project_id")
    file_paths = body.get("file_paths", [])
    if not project_id:
        respond({"error": "project_id required"}, status=400)
        return
    if not file_paths:
        respond({"error": "file_paths required"}, status=400)
        return
    try:
        result = svc.ingest_files_to_project(project_id, [Path(fp) for fp in file_paths])
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=404)
    except Exception as e:
        respond({"error": str(e)}, status=500)


def handle_validate_files(body: Dict[str, Any], respond: Callable) -> None:
    file_paths = body.get("file_paths", [])
    if not file_paths:
        respond({"error": "file_paths required"}, status=400)
        return
    respond(admin_svc.validate_files_for_ingestion(file_paths))
