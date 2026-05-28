"""Project Manager – handles project persistence and file management.

Supports up to 5 active projects (local mode).
Each project has: files, settings, AI configuration, historical outputs.
"""

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from models.document import IngestedDocument
from models.project import Project

PROJECTS_DIR = Path("projects_data")
PROJECTS_FILE = PROJECTS_DIR / "projects.json"
MAX_ACTIVE_PROJECTS = 5


def _ensure_dirs() -> None:
    """Ensure project data directories exist."""
    PROJECTS_DIR.mkdir(exist_ok=True)


def load_projects() -> List[Dict[str, Any]]:
    """Load all projects from disk."""
    _ensure_dirs()
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def save_projects(projects: List[Dict[str, Any]]) -> None:
    """Persist projects to disk."""
    _ensure_dirs()
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def create_project(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new project.

    Args:
        name: Project name.
        description: Optional project description.

    Returns:
        Project dict with id, name, and metadata.

    Raises:
        ValueError: If max active projects reached.
    """
    projects = load_projects()
    if len(projects) >= MAX_ACTIVE_PROJECTS:
        raise ValueError(f"Maximum {MAX_ACTIVE_PROJECTS} active projects allowed")

    project_id = f"proj-{len(projects) + 1:03d}"
    project = Project(
        id=project_id,
        name=name,
        description=description,
    )
    project_dict = asdict(project)
    projects.append(project_dict)
    save_projects(projects)

    # Create project subdirectory for uploads and outputs
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    (project_dir / "uploads").mkdir(exist_ok=True)
    (project_dir / "outputs").mkdir(exist_ok=True)
    (project_dir / "context").mkdir(exist_ok=True)

    return project_dict


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a project by ID."""
    projects = load_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p
    return None


def list_projects() -> List[Dict[str, Any]]:
    """List all active projects (summary view)."""
    projects = load_projects()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "phase": p.get("phase", "discovery"),
            "file_count": len(p.get("files", [])),
        }
        for p in projects
    ]



def ingest_files_to_project(
    project_id: str, file_paths: List[Path]
) -> Dict[str, Any]:
    """Ingest files into a project's context store.

    Parses each file, stores the structured IngestedDocument,
    and updates the project's file list.

    Args:
        project_id: ID of the target project.
        file_paths: List of paths to files to ingest.

    Returns:
        Dict with keys: ingested (count), errors (list), documents (list of summaries).

    Raises:
        ValueError: If project not found.
    """
    from processors.ingestion import ingest_file

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    context_dir = PROJECTS_DIR / project_id / "context"
    context_dir.mkdir(exist_ok=True)

    results: Dict[str, Any] = {"ingested": 0, "errors": [], "documents": []}

    for file_path in file_paths:
        path = Path(file_path)
        try:
            doc = ingest_file(path)
            # Store ingested document as JSON
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

    # Update project file list
    _update_project_files(project_id, file_paths)

    return results


def get_project_context(project_id: str) -> List[Dict[str, Any]]:
    """Load all ingested documents for a project.

    Args:
        project_id: Project ID.

    Returns:
        List of ingested document dicts from the context store.
    """
    context_dir = PROJECTS_DIR / project_id / "context"
    if not context_dir.exists():
        return []

    documents = []
    for json_file in sorted(context_dir.glob("*.json")):
        with open(json_file) as f:
            documents.append(json.load(f))
    return documents


def _update_project_files(project_id: str, file_paths: List[Path]) -> None:
    """Update the project's file list in persistence."""
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            existing_files = set(p.get("files", []))
            for fp in file_paths:
                existing_files.add(str(fp))
            p["files"] = sorted(existing_files)
            break
    save_projects(projects)
