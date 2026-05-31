"""Project handlers — CRUD, lifecycle, file toggles."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict

import services.project as svc


def handle_create_project(body: Dict[str, Any], respond: Callable) -> None:
    name = body.get("name")
    if not name:
        respond({"error": "Project name required"}, status=400)
        return
    try:
        project = svc.create_project(name=name, description=body.get("description", ""))
        respond({"project": project}, status=201)
    except ValueError as e:
        respond({"error": str(e)}, status=409)


def handle_archive_project(project_id: str, body: Dict[str, Any], respond: Callable) -> None:
    try:
        result = svc.archive_project(project_id, body.get("pin", ""))
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=403)


def handle_restore_project(project_id: str, body: Dict[str, Any], respond: Callable) -> None:
    try:
        result = svc.restore_project(project_id, body.get("pin", ""))
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=403)


def handle_delete_project(project_id: str, body: Dict[str, Any], respond: Callable) -> None:
    try:
        result = svc.delete_project(project_id, body.get("pin", ""))
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=403)


def handle_toggle_file(project_id: str, body: Dict[str, Any], respond: Callable) -> None:
    filename = body.get("filename", "")
    if not filename:
        respond({"error": "filename required"}, status=400)
        return
    try:
        result = svc.toggle_file_active(project_id, filename, body.get("active", True))
        respond(result)
    except ValueError as e:
        respond({"error": str(e)}, status=400)
