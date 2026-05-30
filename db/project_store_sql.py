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
        "version_id":            row["version_id"],
        "version_number":        row["version_number"],
        "label":                 row["label"],
        "status":                row["status"],
        "created_at":            row["created_at"],
        "files":                 Database.jload(row.get("files"), []),
        "notes":                 row["notes"],
        "changes_from_previous": row["changes_from_previous"],
        "context_version":       row.get("context_version", ""),
        "feedback":              Database.jload(row.get("feedback"), None),
        # DS-02 traceability
        "hierarchy_version_id":  row.get("hierarchy_version_id", ""),
        "active_review_id":      row.get("active_review_id", ""),
        "previous_version_id":   row.get("previous_version_id", ""),
        "feedback_applied":      Database.jload(row.get("feedback_applied"), []),
        "changes_summary":       row.get("changes_summary", ""),
        # DS-02 quality + lock
        "quality_status":        row.get("quality_status", "draft"),
        "quality_score":         row.get("quality_score", 0),
        "completed_by":          row.get("completed_by", ""),
        "completed_at":          row.get("completed_at", ""),
        "lock_status":           row.get("lock_status", "unlocked"),
        "lock_reason":           row.get("lock_reason", ""),
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
                files, notes, changes_from_previous, context_version, feedback,
                hierarchy_version_id, active_review_id, previous_version_id,
                feedback_applied, changes_summary,
                quality_status, quality_score, completed_by, completed_at,
                lock_status, lock_reason, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                v.get("version_id", ""), project_id,
                v.get("version_number", 1),
                v.get("label", ""),
                v.get("status", "draft"),
                Database.jdump(v.get("files", [])),
                v.get("notes", ""),
                v.get("changes_from_previous", ""),
                v.get("context_version", ""),
                Database.jdump(v.get("feedback")) if v.get("feedback") else None,
                v.get("hierarchy_version_id", ""),
                v.get("active_review_id", ""),
                v.get("previous_version_id", ""),
                Database.jdump(v.get("feedback_applied", [])),
                v.get("changes_summary", ""),
                v.get("quality_status", "draft"),
                v.get("quality_score", 0),
                v.get("completed_by", ""),
                v.get("completed_at", ""),
                v.get("lock_status", "unlocked"),
                v.get("lock_reason", ""),
                v.get("created_at", ""),
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
    # DS-02: primary structured store
    feedback_items: Optional[List[Dict[str, Any]]] = None,
    raw_text: str = "",
    # backward-compat flat lists (derived if not provided)
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    concerns: Optional[List[str]] = None,
    change_requested: Optional[List[str]] = None,
    notes: str = "",
    next_action: str = "",
    status: str = "open",
    # S6-03: hierarchy version scope (no proposal yet)
    version_id: str = "",
) -> Dict[str, Any]:
    """Save structured presales feedback.

    If feedback_items is provided, backward-compat flat lists are derived from it.
    If only flat lists are provided (legacy callers), feedback_items is built from them.
    """
    now = _now()
    db = get_db()
    existing = db.fetchone(
        "SELECT created_at FROM presales_feedback WHERE feedback_id=?", (feedback_id,)
    )
    created_at = existing["created_at"] if existing else now

    # Normalise: if feedback_items provided, derive flat views from them
    items = feedback_items or []
    if items:
        accepted        = [i["text"] for i in items if i.get("category") == "accepted"]
        rejected        = [i["text"] for i in items if i.get("category") == "rejected"]
        concerns        = [i["text"] for i in items if i.get("category") == "concerns"]
        change_requested = [i["text"] for i in items if i.get("category") == "change_requested"]
    else:
        # Legacy path: build minimal FeedbackItem dicts from flat lists
        import uuid as _uuid
        def _make_items(lst, cat):
            return [
                {
                    "item_id": f"fi_{_uuid.uuid4().hex[:8]}",
                    "text": t,
                    "category": cat,
                    "mapped_to": None,
                    "confidence": "medium",
                    "status": "new",
                    "is_critical": False,
                    "addressed_in_version": None,
                    "created_at": now,
                }
                for t in (lst or [])
            ]
        items = (
            _make_items(accepted or [], "accepted")
            + _make_items(rejected or [], "rejected")
            + _make_items(concerns or [], "concerns")
            + _make_items(change_requested or [], "change_requested")
        )

    db.execute(
        """INSERT OR REPLACE INTO presales_feedback
           (feedback_id, project_id, proposal_ver_id, review_id, source,
            responder_name, responder_email,
            feedback_items, raw_text, change_requested,
            accepted, rejected, concerns,
            notes, next_action, status, version_id, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            feedback_id, project_id, proposal_ver_id, review_id, source,
            responder_name, responder_email,
            Database.jdump(items),
            raw_text,
            Database.jdump(change_requested or []),
            Database.jdump(accepted or []),
            Database.jdump(rejected or []),
            Database.jdump(concerns or []),
            notes, next_action, status, version_id, created_at, now,
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
        "feedback_id":      row["feedback_id"],
        "project_id":       row["project_id"],
        "proposal_ver_id":  row.get("proposal_ver_id", ""),
        "review_id":        row.get("review_id", ""),
        "version_id":       row.get("version_id", ""),
        "source":           row.get("source", "internal"),
        "responder_name":   row.get("responder_name", ""),
        "responder_email":  row.get("responder_email", ""),
        "feedback_items":   Database.jload(row.get("feedback_items"), []),
        "raw_text":         row.get("raw_text", ""),
        "change_requested": Database.jload(row.get("change_requested"), []),
        "accepted":         Database.jload(row.get("accepted"), []),
        "rejected":         Database.jload(row.get("rejected"), []),
        "concerns":         Database.jload(row.get("concerns"), []),
        "notes":            row.get("notes", ""),
        "next_action":      row.get("next_action", ""),
        "status":           row.get("status", "open"),
        "created_at":       row.get("created_at", ""),
        "updated_at":       row.get("updated_at", ""),
    }


def update_proposal_version_fields(
    project_id: str,
    version_id: str,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Patch specific fields on a proposal_version row.

    Allowed kwargs: quality_status, quality_score, completed_by, completed_at,
    lock_status, lock_reason, status, hierarchy_version_id, active_review_id,
    previous_version_id, feedback_applied, changes_summary.
    """
    ALLOWED = {
        "quality_status", "quality_score", "completed_by", "completed_at",
        "lock_status", "lock_reason", "status",
        "hierarchy_version_id", "active_review_id",
        "previous_version_id", "feedback_applied", "changes_summary",
    }
    updates = {k: v for k, v in kwargs.items() if k in ALLOWED}
    if not updates:
        return load_proposal_sql(project_id)

    db = get_db()
    for col, val in updates.items():
        serialised = Database.jdump(val) if isinstance(val, (list, dict)) else val
        db.execute(
            f"UPDATE proposal_versions SET {col}=? WHERE project_id=? AND version_id=?",
            (serialised, project_id, version_id),
        )
    db.commit()
    _rebuild_proposal_file(project_id)
    return load_proposal_sql(project_id)


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
