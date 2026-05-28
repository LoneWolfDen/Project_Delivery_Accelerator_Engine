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
            "status": p.get("status", "active"),
        }
        for p in projects
        if p.get("status", "active") not in ("deleted", "archived")
    ]


def list_all_projects() -> List[Dict[str, Any]]:
    """List all projects including archived (for settings view)."""
    projects = load_projects()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "phase": p.get("phase", "discovery"),
            "file_count": len(p.get("files", [])),
            "status": p.get("status", "active"),
        }
        for p in projects
        if p.get("status", "active") != "deleted"
    ]


# Default PIN for destructive operations
ADMIN_PIN = "1234"


def archive_project(project_id: str, pin: str) -> Dict[str, Any]:
    """Archive a project (soft-delete, recoverable).

    Args:
        project_id: Project ID.
        pin: Admin PIN for authorization.

    Returns:
        Dict with status confirmation.

    Raises:
        ValueError: If PIN is wrong or project not found.
    """
    if pin != ADMIN_PIN:
        raise ValueError("Invalid PIN")

    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            p["status"] = "archived"
            save_projects(projects)
            return {"id": project_id, "status": "archived", "message": "Project archived"}
    raise ValueError(f"Project not found: {project_id}")


def delete_project(project_id: str, pin: str) -> Dict[str, Any]:
    """Permanently delete a project and all its data.

    Args:
        project_id: Project ID.
        pin: Admin PIN for authorization.

    Returns:
        Dict with deletion confirmation.

    Raises:
        ValueError: If PIN is wrong or project not found.
    """
    if pin != ADMIN_PIN:
        raise ValueError("Invalid PIN")

    projects = load_projects()
    found = False
    for p in projects:
        if p["id"] == project_id:
            p["status"] = "deleted"
            found = True
            break

    if not found:
        raise ValueError(f"Project not found: {project_id}")

    save_projects(projects)

    # Remove project data directory
    project_dir = PROJECTS_DIR / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    return {"id": project_id, "status": "deleted", "message": "Project permanently deleted"}


def toggle_file_active(project_id: str, filename: str, active: bool) -> Dict[str, Any]:
    """Toggle whether a file is included in the next review cycle.

    Args:
        project_id: Project ID.
        filename: Name of the ingested file (stem, without path).
        active: True to include in reviews, False to exclude.

    Returns:
        Updated file status dict.

    Raises:
        ValueError: If project or file not found.
    """
    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    # Load/update file toggles stored in project metadata
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
    """Get the active/inactive status of all files for a project.

    Returns:
        Dict mapping filename → bool (True = active/included).
    """
    project = get_project(project_id)
    if project is None:
        return {}
    return project.get("file_toggles", {})



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

    # Resolve relative paths against the project root (where server.py lives)
    project_root = Path(__file__).parent

    for file_path in file_paths:
        path = Path(file_path)
        # If path is not absolute, resolve relative to project root
        if not path.is_absolute():
            path = project_root / path
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



def build_project_intelligence(
    project_id: str, version_label: Optional[str] = None
) -> Dict[str, Any]:
    """Build (or rebuild) project intelligence from all ingested documents.

    Each build is saved as a versioned snapshot for iteration tracking.

    Args:
        project_id: Project ID.
        version_label: Optional label for this build (e.g. 'post-discovery').

    Returns:
        Built context dict with metadata and version info.

    Raises:
        ValueError: If project not found or no documents ingested.
    """
    from processors.context_builder import build_context
    from processors.history import save_context_version

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    documents = get_project_context(project_id)
    if not documents:
        raise ValueError(f"No documents ingested for project: {project_id}")

    context = build_context(documents)

    # Persist current intelligence
    intelligence_path = PROJECTS_DIR / project_id / "intelligence.json"
    with open(intelligence_path, "w") as f:
        json.dump(context, f, indent=2)

    # Save versioned snapshot
    project_dir = PROJECTS_DIR / project_id
    version_meta = save_context_version(project_dir, context, version_label)

    # Update iteration metadata
    _update_iteration_on_build(project_id, version_meta)

    # Attach version info to response
    context["_version"] = version_meta

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
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a persona-driven review for a project.

    Loads built intelligence, runs the persona engine, stores the result.

    Args:
        project_id: Project ID.
        persona_name: Persona to use (e.g. 'solution_architect').
        ai_backend: 'files_only', 'ollama', 'bedrock', or 'gemini'.
        custom_prompt: Optional additional context/instructions for the AI to consider.

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
        custom_prompt=custom_prompt,
    )

    # Store review result
    _store_review(project_id, review)

    # Update iteration tracking
    _update_iteration_on_review(project_id)

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



# ──────────────────────────────────────────────────────────────
# Iteration & History
# ──────────────────────────────────────────────────────────────


def get_project_versions(project_id: str) -> List[Dict[str, Any]]:
    """List all context build versions for a project.

    Args:
        project_id: Project ID.

    Returns:
        List of version metadata dicts, newest first.
    """
    from processors.history import list_context_versions

    project_dir = PROJECTS_DIR / project_id
    return list_context_versions(project_dir)


def get_project_version(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """Load a specific context version snapshot.

    Args:
        project_id: Project ID.
        version_id: e.g. 'v1', 'v2'.

    Returns:
        Full context snapshot, or None if not found.
    """
    from processors.history import get_context_version

    project_dir = PROJECTS_DIR / project_id
    return get_context_version(project_dir, version_id)


def compare_project_versions(
    project_id: str, version_a: str, version_b: str
) -> Dict[str, Any]:
    """Compare two context versions for a project.

    Args:
        project_id: Project ID.
        version_a: Earlier version (e.g. 'v1').
        version_b: Later version (e.g. 'v2').

    Returns:
        Comparison dict with added/removed/unchanged per category.
    """
    from processors.history import compare_context_versions

    project_dir = PROJECTS_DIR / project_id
    return compare_context_versions(project_dir, version_a, version_b)


def compare_project_reviews(
    project_id: str, review_file_a: str, review_file_b: str
) -> Dict[str, Any]:
    """Compare two review results for a project.

    Args:
        project_id: Project ID.
        review_file_a: Filename of earlier review.
        review_file_b: Filename of later review.

    Returns:
        Comparison dict showing evolution of findings.
    """
    from processors.history import compare_reviews

    reviews_dir = PROJECTS_DIR / project_id / "reviews"
    path_a = reviews_dir / review_file_a
    path_b = reviews_dir / review_file_b

    if not path_a.exists():
        raise ValueError(f"Review not found: {review_file_a}")
    if not path_b.exists():
        raise ValueError(f"Review not found: {review_file_b}")

    with open(path_a) as f:
        review_a = json.load(f)
    with open(path_b) as f:
        review_b = json.load(f)

    return compare_reviews(review_a, review_b)


def get_project_evolution(
    project_id: str, category: str = "risks"
) -> List[Dict[str, Any]]:
    """Get evolution timeline of a category across all versions.

    Args:
        project_id: Project ID.
        category: 'risks', 'assumptions', 'dependencies', 'constraints', or 'action_items'.

    Returns:
        Timeline list with counts and items per version.
    """
    from processors.history import get_evolution_timeline

    project_dir = PROJECTS_DIR / project_id
    return get_evolution_timeline(project_dir, category)


def get_project_review_history(
    project_id: str, persona_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get review history for a project, optionally filtered by persona.

    Args:
        project_id: Project ID.
        persona_id: Optional persona filter.

    Returns:
        List of review summaries, newest first.
    """
    from processors.history import get_review_history

    project_dir = PROJECTS_DIR / project_id
    return get_review_history(project_dir, persona_id)


def _update_iteration_on_build(project_id: str, version_meta: Dict[str, Any]) -> None:
    """Update project iteration metadata after a context build."""
    from datetime import datetime, timezone

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


def _update_iteration_on_review(project_id: str) -> None:
    """Update project iteration metadata after a review run."""
    from datetime import datetime, timezone

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



# ──────────────────────────────────────────────────────────────
# Proposal Management
# ──────────────────────────────────────────────────────────────


def create_proposal(
    project_id: str,
    proposal_name: str,
    client: str = "",
    files: Optional[List[Path]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """Create a proposal for a project.

    Args:
        project_id: Project ID.
        proposal_name: Name of the proposal.
        client: Client name.
        files: Files associated with this version.
        notes: Notes about this version.

    Returns:
        Proposal tracker dict.
    """
    from processors.proposals import create_proposal as _create

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = intel.get("_build_metadata", {}).get("built_at", "") if intel else ""

    file_strs = [str(f) for f in (files or [])]
    return _create(project_dir, proposal_name, client, file_strs, notes, ctx_version)


def add_proposal_version(
    project_id: str,
    label: str = "",
    files: Optional[List[Path]] = None,
    notes: str = "",
    changes: str = "",
) -> Dict[str, Any]:
    """Add a new version to the project's proposal.

    Args:
        project_id: Project ID.
        label: Version label.
        files: Files for this version.
        notes: Author notes.
        changes: What changed from previous.

    Returns:
        New version dict.
    """
    from processors.proposals import add_proposal_version as _add

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = intel.get("_build_metadata", {}).get("built_at", "") if intel else ""

    file_strs = [str(f) for f in (files or [])]
    return _add(project_dir, file_strs, label, notes, changes, ctx_version)


def get_proposal_info(project_id: str) -> Optional[Dict[str, Any]]:
    """Get the proposal tracker for a project."""
    from processors.proposals import get_proposal

    project_dir = PROJECTS_DIR / project_id
    return get_proposal(project_dir)


def list_proposal_versions_for_project(project_id: str) -> List[Dict[str, Any]]:
    """List all proposal versions for a project."""
    from processors.proposals import list_proposal_versions

    project_dir = PROJECTS_DIR / project_id
    return list_proposal_versions(project_dir)


def compare_proposals(
    project_id: str, version_a: str, version_b: str
) -> Dict[str, Any]:
    """Compare two proposal versions."""
    from processors.proposals import compare_proposal_versions

    project_dir = PROJECTS_DIR / project_id
    return compare_proposal_versions(project_dir, version_a, version_b)


def update_proposal_status(
    project_id: str, version_id: str, new_status: str
) -> Dict[str, Any]:
    """Update proposal version status."""
    from processors.proposals import update_proposal_status as _update

    project_dir = PROJECTS_DIR / project_id
    return _update(project_dir, version_id, new_status)


# ──────────────────────────────────────────────────────────────
# Phase Transitions
# ──────────────────────────────────────────────────────────────


def transition_project_phase(
    project_id: str, new_phase: str, reason: str = ""
) -> Dict[str, Any]:
    """Move a project to a new SDLC phase.

    Args:
        project_id: Project ID.
        new_phase: Target phase (discovery/proposal/planning/execution/review).
        reason: Optional reason for transition.

    Returns:
        Transition record dict.
    """
    from processors.phases import transition_phase

    project_dir = PROJECTS_DIR / project_id
    return transition_phase(project_dir, PROJECTS_FILE, project_id, new_phase, reason)


def get_phase_history_for_project(project_id: str) -> List[Dict[str, Any]]:
    """Get phase transition history for a project."""
    from processors.phases import get_phase_history

    project_dir = PROJECTS_DIR / project_id
    return get_phase_history(project_dir, PROJECTS_FILE, project_id)


def get_phase_info() -> List[Dict[str, Any]]:
    """Get info about all SDLC phases."""
    from processors.phases import get_phase_info
    return get_phase_info()
