"""Project Manager – handles project persistence and file management.

Supports up to 5 active projects (local mode).
Each project has: files, settings, AI configuration, historical outputs.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECTS_FILE = Path("projects.json")
MAX_ACTIVE_PROJECTS = 5


def load_projects() -> List[Dict[str, Any]]:
    """Load all projects from disk."""
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def save_projects(projects: List[Dict[str, Any]]) -> None:
    """Persist projects to disk."""
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, indent=2)


def create_project(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new project.

    Raises:
        ValueError: If max active projects reached.
    """
    projects = load_projects()
    if len(projects) >= MAX_ACTIVE_PROJECTS:
        raise ValueError(f"Maximum {MAX_ACTIVE_PROJECTS} active projects allowed")

    from models.project import Project
    project = Project(
        id=f"proj-{len(projects) + 1:03d}",
        name=name,
        description=description,
    )
    # TODO: serialize dataclass and persist
    raise NotImplementedError("Project creation not yet fully implemented")


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a project by ID."""
    projects = load_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p
    return None
