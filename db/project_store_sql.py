"""SQLite-backed project registry + proposal store.

Dual-write: mirrors every mutation to projects.json and proposals/tracker.json
when file_write_enabled=True (default).

Public helpers called from project_manager.py wrappers:
  load_projects_sql / save_project_sql / delete_project_sql
  load_proposals_sql / save_proposal_sql
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.database import get_db, Database

PROJECTS_DIR = Path("projects_data")
PROJECTS_FILE = PROJECTS_DIR / "projects.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flags() -> tuple[bool, bool]:
    try:
        from admin.config import load_config
        cfg = load_config()
        return getattr(cfg, "sqlite_write_enabled", True), getattr(cfg, "file_write_enabled", True)
    except Exception:
        return True, True


# ── File helpers (dual-write targets) ─────────────────────────

def _rebuild_projects_file() -> None:
    _, file_on = _flags()
    if not file_on:
        return
    PROJECTS_DIR.mkdir(exist_ok=True)
    rows = get_db().fetchall("SELECT * FROM projects ORDER BY created_at")
    projects = [_row_to_project_dict(r) for r in rows]
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def _row_to_project_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "phase": row["phase"],
        "ai_backend": row["ai_backend"],
        "status": row["status"],
        "settings": Database.jload(row.get("settings"), {}),
        "files": Database.jload(row.get("files"), []),
        "file_toggles": Database.jload(row.get("file_toggles"), {}),
        "iteration": Database.jload(row.get("iteration"), {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "archived_at": row.get("archived_at", ""),
        "restored_at": row.get("restored_at", ""),
        # Legacy fields expected by project_manager consumers
        "context": None,
        "reviews": [],
    }


# ── Projects ───────────────────────────────────────────────────

def load_projects_sql() -> List[Dict[str, Any]]:
    """Return all projects (replaces loading projects.json)."""
    sql_on, _ = _flags()
    if not sql_on:
        return _load_projects_file()
    rows = get_db().fetchall("SELECT * FROM projects ORDER BY created_at")
    return [_row_to_project_dict(r) for r in rows]


def _load_projects_file() -> List[Dict[str, Any]]:
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def upsert_project_sql(project: Dict[str, Any]) -> None:
    """Insert or replace a project record."""
    sql_on, _ = _flags()
    if not sql_on:
        return
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO projects
           (id, name, description, phase, ai_backend, status, settings,
            files, file_toggles, iteration, created_at, updated_at,
            archived_at, restored_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            project["id"],
            project.get("name", ""),
            project.get("description", ""),
            project.get("phase", "pre-sales"),
            project.get("ai_backend", "files_only"),
            project.get("status", "active"),
            Database.jdump(project.get("settings", {})),
            Database.jdump(project.get("files", [])),
            Database.jdump(project.get("file_toggles", {})),
            Database.jdump(project.get("iteration", {})),
            project.get("created_at", _now()),
            project.get("updated_at", _now()),
            project.get("archived_at", ""),
            project.get("restored_at", ""),
        ),
    )
    db.commit()
    _rebuild_projects_file()


def save_all_projects_sql(projects: List[Dict[str, Any]]) -> None:
    """Bulk-upsert all projects (called by project_manager.save_projects)."""
    sql_on, _ = _flags()
    if not sql_on:
        return
    for p in projects:
        upsert_project_sql(p)
    _rebuild_projects_file()


# ── Proposals ─────────────────────────────────────────────────

def _proposals_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "proposals"


def _tracker_path(project_id: str) -> Path:
    return _proposals_dir(project_id) / "tracker.json"


def _rebuild_proposal_file(project_id: str) -> None:
    _, file_on = _flags()
    if not file_on:
        return
    tracker = load_proposal_sql(project_id)
    if not tracker:
        return
    p = _tracker_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(tracker, f, indent=2)


def load_proposal_sql(project_id: str) -> Optional[Dict[str, Any]]:
    sql_on, _ = _flags()
    if not sql_on:
        return _load_proposal_file(project_id)
    db = get_db()
    row = db.fetchone("SELECT * FROM proposals WHERE project_id=?", (project_id,))
    if not row:
        return None
    ver_rows = db.fetchall(
        "SELECT * FROM proposal_versions WHERE project_id=? ORDER BY version_number",
        (project_id,),
    )
    versions = [_row_to_proposal_version(v) for v in ver_rows]
    return {
        "project_id": row["project_id"],
        "proposal_name": row["proposal_name"],
        "client": row["client"],
        "current_version": row["current_version"],
        "total_versions": row["total_versions"],
        "versions": versions,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _load_proposal_file(project_id: str) -> Optional[Dict[str, Any]]:
    p = _tracker_path(project_id)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def _row_to_proposal_version(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version_id": row["version_id"],
        "version_number": row["version_number"],
        "label": row["label"],
        "status": row["status"],
        "created_at": row["created_at"],
        "files": Database.jload(row.get("files"), []),
        "notes": row["notes"],
        "changes_from_previous": row["changes_from_previous"],
        "context_version": row["context_version"],
        "feedback": Database.jload(row.get("feedback"), None),
    }


def save_proposal_sql(project_id: str, tracker: Dict[str, Any]) -> None:
    """Upsert proposal tracker + all versions."""
    sql_on, _ = _flags()
    if not sql_on:
        return
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO proposals
           (project_id, proposal_name, client, current_version,
            total_versions, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            project_id,
            tracker.get("proposal_name", ""),
            tracker.get("client", ""),
            tracker.get("current_version", ""),
            tracker.get("total_versions", 0),
            tracker.get("created_at", _now()),
            tracker.get("updated_at", _now()),
        ),
    )
    for v in tracker.get("versions", []):
        db.execute(
            """INSERT OR REPLACE INTO proposal_versions
               (version_id, project_id, version_number, label, status,
                files, notes, changes_from_previous, context_version,
                feedback, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                v["version_id"], project_id,
                v.get("version_number", 1),
                v.get("label", ""),
                v.get("status", "draft"),
                Database.jdump(v.get("files", [])),
                v.get("notes", ""),
                v.get("changes_from_previous", ""),
                v.get("context_version", ""),
                Database.jdump(v.get("feedback")) if v.get("feedback") else None,
                v.get("created_at", _now()),
            ),
        )
    db.commit()
    _rebuild_proposal_file(project_id)


# ── Pre-sales feedback (P9) ────────────────────────────────────

def save_presales_feedback(
    project_id: str,
    feedback_id: str,
    proposal_ver_id: str = "",
    review_id: str = "",
    source: str = "internal",
    responder_name: str = "",
    responder_email: str = "",
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    concerns: Optional[List[str]] = None,
    notes: str = "",
    next_action: str = "",
    status: str = "open",
) -> Dict[str, Any]:
    now = _now()
    db = get_db()
    existing = db.fetchone(
        "SELECT created_at FROM presales_feedback WHERE feedback_id=?", (feedback_id,)
    )
    created_at = existing["created_at"] if existing else now
    db.execute(
        """INSERT OR REPLACE INTO presales_feedback
           (feedback_id, project_id, proposal_ver_id, review_id, source,
            responder_name, responder_email, accepted, rejected, concerns,
            notes, next_action, status, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            feedback_id, project_id, proposal_ver_id, review_id, source,
            responder_name, responder_email,
            Database.jdump(accepted or []),
            Database.jdump(rejected or []),
            Database.jdump(concerns or []),
            notes, next_action, status, created_at, now,
        ),
    )
    db.commit()
    return load_presales_feedback_item(feedback_id)


def load_presales_feedback(project_id: str) -> List[Dict[str, Any]]:
    rows = get_db().fetchall(
        "SELECT * FROM presales_feedback WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )
    return [_row_to_feedback(r) for r in rows]


def load_presales_feedback_item(feedback_id: str) -> Optional[Dict[str, Any]]:
    row = get_db().fetchone(
        "SELECT * FROM presales_feedback WHERE feedback_id=?", (feedback_id,)
    )
    return _row_to_feedback(row) if row else None


def _row_to_feedback(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "feedback_id": row["feedback_id"],
        "project_id": row["project_id"],
        "proposal_ver_id": row.get("proposal_ver_id", ""),
        "review_id": row.get("review_id", ""),
        "source": row.get("source", "internal"),
        "responder_name": row.get("responder_name", ""),
        "responder_email": row.get("responder_email", ""),
        "accepted": Database.jload(row.get("accepted"), []),
        "rejected": Database.jload(row.get("rejected"), []),
        "concerns": Database.jload(row.get("concerns"), []),
        "notes": row.get("notes", ""),
        "next_action": row.get("next_action", ""),
        "status": row.get("status", "open"),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
    }


# ── External feedback tokens (P9) ─────────────────────────────

def create_feedback_token(
    project_id: str,
    proposal_ver_id: str = "",
    review_id: str = "",
    expires_days: int = 7,
) -> str:
    import uuid, secrets
    from datetime import timedelta
    token = secrets.token_urlsafe(24)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat()
    now = _now()
    get_db().execute(
        """INSERT INTO feedback_tokens
           (token, project_id, proposal_ver_id, review_id, expires_at, used, created_at)
           VALUES (?,?,?,?,?,0,?)""",
        (token, project_id, proposal_ver_id, review_id, expires_at, now),
    )
    get_db().commit()
    return token


def validate_feedback_token(token: str) -> Optional[Dict[str, Any]]:
    """Return token row if valid + unexpired + unused, else None."""
    row = get_db().fetchone(
        "SELECT * FROM feedback_tokens WHERE token=? AND used=0", (token,)
    )
    if not row:
        return None
    expires_at = row.get("expires_at", "")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) > exp:
                return None
        except ValueError:
            pass
    return dict(row)


def mark_token_used(token: str) -> None:
    get_db().execute(
        "UPDATE feedback_tokens SET used=1 WHERE token=?", (token,)
    )
    get_db().commit()
