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



def build_project_intelligence(project_id: str) -> Dict[str, Any]:
    """Build (or rebuild) project intelligence from all ingested documents.

    Reads all context JSON files, runs the context builder,
    and persists the result.

    Args:
        project_id: Project ID.

    Returns:
        Built context dict with metadata.

    Raises:
        ValueError: If project not found or no documents ingested.
    """
    from processors.context_builder import build_context

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    documents = get_project_context(project_id)
    if not documents:
        raise ValueError(f"No documents ingested for project: {project_id}")

    context = build_context(documents)

    # Persist intelligence
    intelligence_path = PROJECTS_DIR / project_id / "intelligence.json"
    with open(intelligence_path, "w") as f:
        json.dump(context, f, indent=2)

    return context


def get_project_intelligence(project_id: str) -> Dict[str, Any]:
    """Load built intelligence for a project.

    Args:
        project_id: Project ID.

    Returns:
        Intelligence dict, or empty dict if not yet built.
    """
    intelligence_path = PROJECTS_DIR / project_id / "intelligence.json"
    if not intelligence_path.exists():
        return {}
    with open(intelligence_path) as f:
        return json.load(f)


def get_project_summary(project_id: str) -> str:
    """Get a token-efficient summary of project intelligence.

    Args:
        project_id: Project ID.

    Returns:
        Text summary suitable for prompt injection.
    """
    from processors.context_builder import build_context_summary

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        return "No intelligence built yet. Run build-context first."
    return build_context_summary(intelligence)



def run_persona_review(
    project_id: str,
    persona_name: str,
    ai_backend: str = "files_only",
) -> Dict[str, Any]:
    """Run a persona-driven review for a project.

    Loads built intelligence, runs the persona engine, stores the result.

    Args:
        project_id: Project ID.
        persona_name: Persona to use (e.g. 'solution_architect').
        ai_backend: 'files_only', 'ollama', or 'bedrock'.

    Returns:
        Review result dict.

    Raises:
        ValueError: If project not found or no intelligence built.
    """
    from personas.engine import run_review

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError(
            f"No intelligence built for project: {project_id}. "
            "Run build-context first."
        )

    # Run the review
    review = run_review(
        persona_name=persona_name,
        context=intelligence,
        ai_backend=ai_backend,
    )

    # Store review result
    _store_review(project_id, review)

    return review


def get_project_reviews(project_id: str) -> List[Dict[str, Any]]:
    """Load all stored reviews for a project.

    Args:
        project_id: Project ID.

    Returns:
        List of review result dicts, newest first.
    """
    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    if not reviews_dir.exists():
        return []

    reviews = []
    for json_file in sorted(reviews_dir.glob("*.json"), reverse=True):
        with open(json_file) as f:
            reviews.append(json.load(f))
    return reviews


def _store_review(project_id: str, review: Dict[str, Any]) -> None:
    """Persist a review result to disk."""
    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    reviews_dir.mkdir(exist_ok=True)

    persona_id = review.get("persona_id", "unknown")
    timestamp = review.get("timestamp", "").replace(":", "-").replace("+", "")[:19]
    filename = f"{persona_id}_{timestamp}.json"

    with open(reviews_dir / filename, "w") as f:
        json.dump(review, f, indent=2)
