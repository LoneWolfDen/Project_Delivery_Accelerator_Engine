"""SQLite-backed artifact store – dual-write drop-in for processors/artifact_store.py.

Public API is identical to artifact_store.py so server.py needs no changes.
Dual-write: writes to SQLite + keeps artifacts.json in sync when file_write_enabled.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.database import get_db, Database
from models.artifact import (
    Artifact, ArtifactStatus,
    generate_artifact_id, now_iso,
    validate_category, validate_file_extension, VALID_CATEGORIES,
)

PROJECTS_DIR = Path("projects_data")


def _flags() -> tuple[bool, bool]:
    try:
        from admin.config import load_config
        cfg = load_config()
        return getattr(cfg, "sqlite_write_enabled", True), getattr(cfg, "file_write_enabled", True)
    except Exception:
        return True, True


def _registry_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "artifacts.json"


def _raw_dir(project_id: str) -> Path:
    d = PROJECTS_DIR / project_id / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Registry file helpers ──────────────────────────────────────

def _load_registry_file(project_id: str) -> List[Dict[str, Any]]:
    p = _registry_path(project_id)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def _save_registry_file(project_id: str, artifacts: List[Dict[str, Any]]) -> None:
    p = _registry_path(project_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(artifacts, f, indent=2)


def _rebuild_registry_file(project_id: str) -> None:
    """Rebuild artifacts.json from SQLite (used after any mutation)."""
    _, file_on = _flags()
    if not file_on:
        return
    rows = get_db().fetchall(
        "SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at", (project_id,)
    )
    arts = [_row_to_artifact(r).to_storage_dict() for r in rows]
    _save_registry_file(project_id, arts)


# ── Row converter ──────────────────────────────────────────────

def _row_to_artifact(row: Dict[str, Any]) -> Artifact:
    return Artifact(
        artifact_id=row["artifact_id"],
        project_id=row["project_id"],
        type=row["type"],
        file_name=row["file_name"],
        title=row["title"],
        category=row["category"],
        metadata=Database.jload(row.get("metadata"), {}),
        include=bool(row["include"]),
        status=row["status"],
        raw_path=row.get("raw_path", ""),
        text_content=row.get("text_content", ""),
        created_at=row["created_at"],
    )


# ── Public API ─────────────────────────────────────────────────

def store_file_artifact(
    project_id: str,
    file_name: str,
    file_content: bytes,
    category: str,
    title: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Artifact:
    if not validate_category(category):
        raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}")
    if not validate_file_extension(file_name):
        raise ValueError(f"Unsupported file type for '{file_name}'.")

    artifact_id = generate_artifact_id()
    raw_dir = _raw_dir(project_id)
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

    sql_on, _ = _flags()
    if sql_on:
        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO artifacts
               (artifact_id, project_id, type, file_name, title, category,
                metadata, include, status, raw_path, text_content, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                artifact_id, project_id, "file", file_name,
                title or file_name, category,
                Database.jdump(metadata or {}),
                1, ArtifactStatus.INGESTED.value,
                str(raw_path), "", artifact.created_at,
            ),
        )
        db.commit()

    _rebuild_registry_file(project_id)
    return artifact


def store_text_artifact(
    project_id: str,
    text: str,
    category: str,
    title: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Artifact:
    if not validate_category(category):
        raise ValueError(f"Invalid category '{category}'.")
    if not text or not text.strip():
        raise ValueError("Text content cannot be empty")

    artifact_id = generate_artifact_id()
    raw_dir = _raw_dir(project_id)
    text_file = raw_dir / f"{artifact_id}_text.json"
    text_blob = {"artifact_id": artifact_id, "title": title, "text": text,
                 "metadata": metadata or {}, "created_at": now_iso()}
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
        created_at=text_blob["created_at"],
        raw_path=str(text_file),
        text_content=text,
    )

    sql_on, _ = _flags()
    if sql_on:
        db = get_db()
        db.execute(
            """INSERT OR REPLACE INTO artifacts
               (artifact_id, project_id, type, file_name, title, category,
                metadata, include, status, raw_path, text_content, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                artifact_id, project_id, "text", "",
                title or "Pasted text", category,
                Database.jdump(metadata or {}),
                1, ArtifactStatus.INGESTED.value,
                str(text_file), text, artifact.created_at,
            ),
        )
        db.commit()

    _rebuild_registry_file(project_id)
    return artifact


def list_artifacts(project_id: str) -> List[Dict[str, Any]]:
    sql_on, _ = _flags()
    if sql_on:
        rows = get_db().fetchall(
            "SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at", (project_id,)
        )
        return [_row_to_artifact(r).to_api_dict() for r in rows]
    # File fallback
    from processors.artifact_store import list_artifacts as _list  # noqa: PLC0415
    return _list(project_id)


def get_artifact(project_id: str, artifact_id: str) -> Optional[Artifact]:
    sql_on, _ = _flags()
    if sql_on:
        row = get_db().fetchone(
            "SELECT * FROM artifacts WHERE project_id=? AND artifact_id=?",
            (project_id, artifact_id),
        )
        return _row_to_artifact(row) if row else None
    from processors.artifact_store import get_artifact as _get  # noqa: PLC0415
    return _get(project_id, artifact_id)


def toggle_artifact_include(
    project_id: str, artifact_id: str, include: bool
) -> Optional[Dict[str, Any]]:
    sql_on, _ = _flags()
    if sql_on:
        db = get_db()
        db.execute(
            "UPDATE artifacts SET include=? WHERE project_id=? AND artifact_id=?",
            (1 if include else 0, project_id, artifact_id),
        )
        db.commit()
        _rebuild_registry_file(project_id)
        row = db.fetchone(
            "SELECT * FROM artifacts WHERE project_id=? AND artifact_id=?",
            (project_id, artifact_id),
        )
        return _row_to_artifact(row).to_api_dict() if row else None
    from processors.artifact_store import toggle_artifact_include as _toggle  # noqa: PLC0415
    return _toggle(project_id, artifact_id, include)


def update_artifact_status(
    project_id: str, artifact_id: str, status: str
) -> Optional[Dict[str, Any]]:
    sql_on, _ = _flags()
    if sql_on:
        db = get_db()
        db.execute(
            "UPDATE artifacts SET status=? WHERE project_id=? AND artifact_id=?",
            (status, project_id, artifact_id),
        )
        db.commit()
        _rebuild_registry_file(project_id)
        row = db.fetchone(
            "SELECT * FROM artifacts WHERE project_id=? AND artifact_id=?",
            (project_id, artifact_id),
        )
        return _row_to_artifact(row).to_api_dict() if row else None
    from processors.artifact_store import update_artifact_status as _upd  # noqa: PLC0415
    return _upd(project_id, artifact_id, status)


def delete_artifact(project_id: str, artifact_id: str) -> bool:
    sql_on, _ = _flags()
    if sql_on:
        row = get_db().fetchone(
            "SELECT raw_path FROM artifacts WHERE project_id=? AND artifact_id=?",
            (project_id, artifact_id),
        )
        if row:
            rp = row.get("raw_path", "")
            if rp:
                p = Path(rp)
                if p.exists():
                    p.unlink()
            get_db().execute(
                "DELETE FROM artifacts WHERE project_id=? AND artifact_id=?",
                (project_id, artifact_id),
            )
            get_db().commit()
            _rebuild_registry_file(project_id)
            return True
        return False
    from processors.artifact_store import delete_artifact as _del  # noqa: PLC0415
    return _del(project_id, artifact_id)


def get_artifact_text_content(project_id: str, artifact_id: str) -> str:
    """Delegates to original implementation (file-reading logic unchanged)."""
    from processors.artifact_store import get_artifact_text_content as _get  # noqa: PLC0415
    # Sync: ensure artifact registry file exists for the original fn to read
    _rebuild_registry_file(project_id)
    return _get(project_id, artifact_id)


def _load_registry(project_id: str) -> List[Dict[str, Any]]:
    """Compatibility shim used by processors/pipeline.py."""
    sql_on, _ = _flags()
    if sql_on:
        rows = get_db().fetchall(
            "SELECT * FROM artifacts WHERE project_id=? ORDER BY created_at", (project_id,)
        )
        return [_row_to_artifact(r).to_storage_dict() for r in rows]
    return _load_registry_file(project_id)
