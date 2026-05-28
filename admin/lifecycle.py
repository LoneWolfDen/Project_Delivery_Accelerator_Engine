"""Lifecycle Logging – Tracks archived and deleted project metadata.

Maintains rolling logs (last 5 entries) for:
- Archived projects (recoverable via PIN)
- Deleted projects (metadata only, no files)

Format:
{
    "project_id": "proj-001",
    "name": "Cloud Migration",
    "timestamp": "2025-01-15T10:30:00Z",
    "file_metadata": [...],
    "actions": ["archived", "restored", ...]
}
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LIFECYCLE_DIR = Path("projects_data")
LIFECYCLE_FILE = LIFECYCLE_DIR / "lifecycle_log.json"

MAX_LOG_ENTRIES = 5  # Rolling log, FIFO


class LifecycleLog:
    """Lifecycle log container."""

    def __init__(self, archived: Optional[List[Dict]] = None, deleted: Optional[List[Dict]] = None):
        self.archived: List[Dict[str, Any]] = archived or []
        self.deleted: List[Dict[str, Any]] = deleted or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archived": self.archived,
            "deleted": self.deleted,
            "archived_count": len(self.archived),
            "deleted_count": len(self.deleted),
            "max_entries": MAX_LOG_ENTRIES,
        }


def get_lifecycle_log() -> LifecycleLog:
    """Load lifecycle log from disk.

    Returns:
        LifecycleLog with archived and deleted entries.
    """
    LIFECYCLE_DIR.mkdir(exist_ok=True)

    if not LIFECYCLE_FILE.exists():
        return LifecycleLog()

    with open(LIFECYCLE_FILE) as f:
        data = json.load(f)

    return LifecycleLog(
        archived=data.get("archived", []),
        deleted=data.get("deleted", []),
    )


def _save_lifecycle_log(log: LifecycleLog) -> None:
    """Persist lifecycle log to disk."""
    LIFECYCLE_DIR.mkdir(exist_ok=True)
    with open(LIFECYCLE_FILE, "w") as f:
        json.dump({
            "archived": log.archived,
            "deleted": log.deleted,
        }, f, indent=2)


def record_archive(
    project_id: str,
    name: str,
    file_metadata: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Record a project archive event.

    Maintains FIFO rolling log (max 5 entries).
    Allows restore via PIN.

    Args:
        project_id: Project ID.
        name: Project name.
        file_metadata: List of file metadata dicts.

    Returns:
        Archive log entry.
    """
    log = get_lifecycle_log()

    entry: Dict[str, Any] = {
        "project_id": project_id,
        "name": name,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "file_metadata": file_metadata or [],
        "actions": ["archived"],
        "restore_allowed": True,
    }

    log.archived.append(entry)

    # FIFO: keep only last MAX_LOG_ENTRIES
    if len(log.archived) > MAX_LOG_ENTRIES:
        log.archived = log.archived[-MAX_LOG_ENTRIES:]

    _save_lifecycle_log(log)
    return entry


def record_restore(project_id: str) -> Optional[Dict[str, Any]]:
    """Record a project restore event.

    Updates the archive log entry to mark as restored.

    Args:
        project_id: Project ID to mark as restored.

    Returns:
        Updated entry, or None if not found.
    """
    log = get_lifecycle_log()

    for entry in log.archived:
        if entry["project_id"] == project_id:
            entry["actions"].append("restored")
            entry["restored_at"] = datetime.now(timezone.utc).isoformat()
            entry["restore_allowed"] = False
            _save_lifecycle_log(log)
            return entry

    return None


def record_delete(
    project_id: str,
    name: str,
    file_metadata: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Record a project deletion event.

    Stores metadata only (NO files kept).
    Maintains FIFO rolling log (max 5 entries).

    Args:
        project_id: Project ID.
        name: Project name.
        file_metadata: List of file metadata (names/types only, no content).

    Returns:
        Delete log entry.
    """
    log = get_lifecycle_log()

    entry: Dict[str, Any] = {
        "project_id": project_id,
        "name": name,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "file_metadata": file_metadata or [],
        "actions": ["deleted"],
    }

    log.deleted.append(entry)

    # FIFO: keep only last MAX_LOG_ENTRIES
    if len(log.deleted) > MAX_LOG_ENTRIES:
        log.deleted = log.deleted[-MAX_LOG_ENTRIES:]

    _save_lifecycle_log(log)
    return entry


def get_archived_projects() -> List[Dict[str, Any]]:
    """Get list of archived projects that can be restored.

    Returns:
        List of archive entries where restore is allowed.
    """
    log = get_lifecycle_log()
    return [e for e in log.archived if e.get("restore_allowed", True)]


def is_restore_allowed(project_id: str) -> bool:
    """Check if a project can be restored from archive.

    Args:
        project_id: Project ID.

    Returns:
        True if project is in archive and restore is allowed.
    """
    log = get_lifecycle_log()
    for entry in log.archived:
        if entry["project_id"] == project_id and entry.get("restore_allowed", True):
            return True
    return False
