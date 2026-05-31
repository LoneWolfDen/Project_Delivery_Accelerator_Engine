"""Project service — CRUD, persistence, lifecycle."""
from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from admin.config import load_config, update_config as _update_config
from admin.lifecycle import record_archive, record_delete, record_restore
from db.database import get_db
from db.project_store_sql import (
    _flags as _sql_flags,
    load_projects_sql,
    save_all_projects_sql,
)
from models.project import Project

logger = logging.getLogger(__name__)

PROJECTS_DIR = Path("projects_data")
PROJECTS_FILE = PROJECTS_DIR / "projects.json"

# Runtime admin PIN (operators set ADMIN_PIN env var)
ADMIN_PIN = os.environ.get("ADMIN_PIN", "")

# Max archived projects (FIFO eviction)
MAX_ARCHIVED = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_max_active_projects() -> int:
    try:
        return load_config().max_active_projects
    except Exception:
        return 5


def _ensure_dirs() -> None:
    PROJECTS_DIR.mkdir(exist_ok=True)


def _validate_pin(pin: str) -> None:
    try:
        configured_pin = load_config().admin_pin
    except Exception:
        configured_pin = ADMIN_PIN
    if not configured_pin:
        raise ValueError(
            "No admin PIN configured. Set the ADMIN_PIN environment variable "
            "or configure a PIN via the Admin panel before performing this action."
        )
    if pin != configured_pin:
        raise ValueError("Invalid PIN")


# ── Persistence ───────────────────────────────────────────────────────────────

def load_projects() -> List[Dict[str, Any]]:
    _ensure_dirs()
    try:
        sql_on, _ = _sql_flags()
        if sql_on:
            return load_projects_sql()
    except Exception:
        pass
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def save_projects(projects: List[Dict[str, Any]]) -> None:
    _ensure_dirs()
    try:
        sql_on, file_on = _sql_flags()
        if sql_on:
            save_all_projects_sql(projects)
        if file_on:
            with open(PROJECTS_FILE, "w") as f:
                json.dump(projects, f, indent=2)
        return
    except Exception:
        pass
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_project(name: str, description: str = "") -> Dict[str, Any]:
    projects = load_projects()
    max_projects = _get_max_active_projects()
    active_count = len([p for p in projects if p.get("status", "active") == "active"])
    if active_count >= max_projects:
        raise ValueError(
            f"Maximum {max_projects} active projects reached. "
            "Please archive or delete an existing project, or contact your admin."
        )

    project_id = f"proj-{uuid.uuid4().hex[:6]}"

    try:
        config = load_config()
        default_phase = config.default_phase
        default_backend = config.default_ai_backend
    except Exception:
        default_phase = "discovery"
        default_backend = "ollama"

    project = Project(
        id=project_id,
        name=name,
        description=description,
        phase=default_phase,
        ai_backend=default_backend,
    )
    project_dict = asdict(project)
    project_dict["status"] = "active"
    projects.append(project_dict)
    save_projects(projects)

    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    for sub in ("uploads", "outputs", "context", "intelligence", "run_history"):
        (project_dir / sub).mkdir(exist_ok=True)

    return project_dict


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    for p in load_projects():
        if p.get("id") == project_id:
            return p
    return None


def list_projects() -> List[Dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "phase": p.get("phase", "discovery"),
            "file_count": len(p.get("files", [])),
            "status": p.get("status", "active"),
        }
        for p in load_projects()
        if p.get("status", "active") not in ("deleted", "archived")
    ]


def list_all_projects() -> List[Dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "phase": p.get("phase", "discovery"),
            "file_count": len(p.get("files", [])),
            "status": p.get("status", "active"),
        }
        for p in load_projects()
        if p.get("status", "active") != "deleted"
    ]


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def archive_project(project_id: str, pin: str) -> Dict[str, Any]:
    _validate_pin(pin)
    projects = load_projects()
    target = next((p for p in projects if p["id"] == project_id), None)
    if target is None:
        raise ValueError(f"Project not found: {project_id}")

    archived = [p for p in projects if p.get("status") == "archived"]
    if len(archived) >= MAX_ARCHIVED:
        oldest = sorted(archived, key=lambda x: x.get("updated_at", ""))[0]
        oldest["status"] = "deleted"
        try:
            record_delete(oldest["id"], oldest.get("name", ""),
                          [{"filename": f} for f in oldest.get("files", [])])
        except Exception:
            pass

    target["status"] = "archived"
    target["archived_at"] = datetime.now(timezone.utc).isoformat()
    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_projects(projects)

    try:
        record_archive(project_id, target.get("name", ""),
                       [{"filename": f} for f in target.get("files", [])])
    except Exception:
        pass

    return {"id": project_id, "status": "archived", "message": "Project archived"}


def delete_project(project_id: str, pin: str) -> Dict[str, Any]:
    _validate_pin(pin)
    projects = load_projects()
    found = None
    for p in projects:
        if p["id"] == project_id:
            found = p
            p["status"] = "deleted"
            break
    if not found:
        raise ValueError(f"Project not found: {project_id}")

    save_projects(projects)

    try:
        record_delete(project_id, found.get("name", ""),
                      [{"filename": f} for f in found.get("files", [])])
    except Exception:
        pass

    project_dir = PROJECTS_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        db = get_db()
        for table in (
            "versions", "reviews", "phases", "artifacts", "proposals",
            "proposal_versions", "presales_feedback", "feedback_tokens",
            "proposal_documents", "decision_log",
        ):
            db.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        db.execute("DELETE FROM projects WHERE id=?", (project_id,))
        db.commit()
    except Exception:
        pass

    return {"id": project_id, "status": "deleted", "message": "Project permanently deleted"}


def restore_project(project_id: str, pin: str) -> Dict[str, Any]:
    _validate_pin(pin)
    projects = load_projects()
    target = next((p for p in projects if p["id"] == project_id), None)
    if target is None:
        raise ValueError(f"Project not found: {project_id}")
    if target.get("status") != "archived":
        raise ValueError(f"Project is not archived (status: {target.get('status', 'active')})")

    target["status"] = "active"
    target["restored_at"] = datetime.now(timezone.utc).isoformat()
    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_projects(projects)

    try:
        record_restore(project_id)
    except Exception:
        pass

    return {
        "id": project_id,
        "status": "active",
        "message": "Project restored from archive",
        "restored_at": target["restored_at"],
    }


def get_auto_archive_suggestions() -> List[Dict[str, Any]]:
    try:
        config = load_config()
        if not config.auto_archive_enabled:
            return []
        threshold_days = config.auto_archive_inactivity_days
    except Exception:
        return []

    projects = load_projects()
    now = datetime.now(timezone.utc)
    suggestions = []

    for p in projects:
        if p.get("status", "active") != "active":
            continue
        last_activity = p.get("updated_at", p.get("created_at", ""))
        if not last_activity:
            continue
        try:
            last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            inactive_days = (now - last_dt).days
            if inactive_days >= threshold_days:
                suggestions.append({
                    "project_id": p["id"],
                    "name": p.get("name", ""),
                    "inactive_days": inactive_days,
                    "threshold_days": threshold_days,
                    "last_activity": last_activity,
                })
        except (ValueError, TypeError):
            continue

    return suggestions


# ── File toggles ──────────────────────────────────────────────────────────────

def toggle_file_active(project_id: str, filename: str, active: bool) -> Dict[str, Any]:
    if get_project(project_id) is None:
        raise ValueError(f"Project not found: {project_id}")
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            file_toggles = p.get("file_toggles", {})
            file_toggles[filename] = active
            p["file_toggles"] = file_toggles
            break
    save_projects(projects)
    return {"filename": filename, "active": active}


def get_file_toggles(project_id: str) -> Dict[str, bool]:
    project = get_project(project_id)
    if project is None:
        return {}
    return project.get("file_toggles", {})


# ── Iteration metadata ────────────────────────────────────────────────────────

def update_iteration_on_build(project_id: str, version_meta: Dict[str, Any]) -> None:
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            iteration = p.get("iteration") or {}
            iteration["current_version"] = version_meta["version_id"]
            iteration["total_builds"] = version_meta["version_number"]
            iteration["last_build_at"] = version_meta["timestamp"]
            p["iteration"] = iteration
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    save_projects(projects)


def update_iteration_on_review(project_id: str) -> None:
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            iteration = p.get("iteration") or {}
            iteration["total_reviews"] = iteration.get("total_reviews", 0) + 1
            iteration["last_review_at"] = datetime.now(timezone.utc).isoformat()
            p["iteration"] = iteration
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    save_projects(projects)
