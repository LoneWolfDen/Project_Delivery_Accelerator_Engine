"""Ingest service — file ingestion into a project's context store."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from processors.ingestion import ingest_file
from services.project import (
    PROJECTS_DIR,
    get_project,
    load_projects,
    save_projects,
)

logger = logging.getLogger(__name__)


def ingest_files_to_project(
    project_id: str, file_paths: List[Path]
) -> Dict[str, Any]:
    """Parse and store files into the project context directory."""
    if get_project(project_id) is None:
        raise ValueError(f"Project not found: {project_id}")

    context_dir = PROJECTS_DIR / project_id / "context"
    context_dir.mkdir(exist_ok=True)

    results: Dict[str, Any] = {"ingested": 0, "errors": [], "documents": []}
    project_root = Path(__file__).parent.parent  # repo root

    for file_path in file_paths:
        path = Path(file_path)
        if not path.is_absolute():
            path = project_root / path
        try:
            doc = ingest_file(path)
            doc_output_path = context_dir / f"{path.stem}.json"
            with open(doc_output_path, "w") as f:
                json.dump(doc.to_dict(), f, indent=2)
            results["ingested"] += 1
            results["documents"].append({
                "filename": doc.filename,
                "source_type": doc.metadata.source_type.value,
                "sections": doc.section_count,
                "word_count": doc.metadata.word_count,
                "is_valid": doc.is_valid,
            })
        except Exception as e:
            results["errors"].append({"file": str(path), "error": str(e)})

    _update_project_files(project_id, file_paths)
    return results


def get_project_context(project_id: str) -> List[Dict[str, Any]]:
    """Load all ingested documents for a project."""
    context_dir = PROJECTS_DIR / project_id / "context"
    if not context_dir.exists():
        return []
    documents = []
    for json_file in sorted(context_dir.glob("*.json")):
        with open(json_file) as f:
            documents.append(json.load(f))
    return documents


def _update_project_files(project_id: str, file_paths: List[Path]) -> None:
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            existing = set(p.get("files", []))
            for fp in file_paths:
                existing.add(str(fp))
            p["files"] = sorted(existing)
            break
    save_projects(projects)
