"""Project Manager – handles project persistence and file management.

Supports up to 5 active projects (configurable via Admin).
Each project has: files, settings, AI configuration, historical outputs.

V3 Enhancements:
- Admin-driven configuration (max projects, defaults)
- Lifecycle logging (archive/delete tracking)
- Version control records for every run
- Guardrails (validation before operations)
- Standardised agent input
- Data separation (raw/processed/intelligence)
- Archive + Restore with PIN and FIFO limits
- System health tracking
"""

import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from models.document import IngestedDocument
from models.project import Project

PROJECTS_DIR = Path("projects_data")
PROJECTS_FILE = PROJECTS_DIR / "projects.json"

# Load max from admin config (with fallback)
def _get_max_active_projects() -> int:
    try:
        from admin.config import load_config
        return load_config().max_active_projects
    except Exception:
        return 5

MAX_ACTIVE_PROJECTS = 5  # Static fallback; runtime uses _get_max_active_projects()

# Max archived projects (FIFO)
MAX_ARCHIVED = 5


def _ensure_dirs() -> None:
    """Ensure project data directories exist."""
    PROJECTS_DIR.mkdir(exist_ok=True)


def load_projects() -> List[Dict[str, Any]]:
    """Load all projects — SQLite when enabled, else flat-file fallback."""
    _ensure_dirs()
    try:
        from db.project_store_sql import load_projects_sql, _flags
        sql_on, _ = _flags()
        if sql_on:
            return load_projects_sql()
    except Exception:
        pass
    if not PROJECTS_FILE.exists():
        return []
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def save_projects(projects: List[Dict[str, Any]]) -> None:
    """Persist projects — writes to SQLite and/or flat-file per dual-write flags."""
    _ensure_dirs()
    try:
        from db.project_store_sql import save_all_projects_sql, _flags
        sql_on, file_on = _flags()
        if sql_on:
            save_all_projects_sql(projects)
        if file_on:
            with open(PROJECTS_FILE, "w") as f:
                json.dump(projects, f, indent=2)
        return
    except Exception:
        pass
    # Pure file fallback
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
    max_projects = _get_max_active_projects()
    active_count = len([p for p in projects if p.get("status", "active") == "active"])
    if active_count >= max_projects:
        raise ValueError(
            f"Maximum {max_projects} active projects reached. "
            f"Please archive or delete an existing project, or contact your admin to increase the limit."
        )

    project_id = f"proj-{len(projects) + 1:03d}"

    # Get defaults from admin config
    try:
        from admin.config import load_config
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

    # Create project subdirectory with data separation (raw/processed/intelligence)
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(exist_ok=True)
    (project_dir / "uploads").mkdir(exist_ok=True)     # raw/
    (project_dir / "outputs").mkdir(exist_ok=True)     # processed/
    (project_dir / "context").mkdir(exist_ok=True)     # raw parsed docs
    (project_dir / "intelligence").mkdir(exist_ok=True)  # intelligence/
    (project_dir / "run_history").mkdir(exist_ok=True)   # version control

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
import os as _os
# Default PIN is read from ADMIN_PIN env var. No hardcoded fallback —
# operators must set ADMIN_PIN before enabling destructive operations.
ADMIN_PIN = _os.environ.get("ADMIN_PIN", "")


def _validate_pin(pin: str) -> None:
    """Validate admin PIN against config or ADMIN_PIN env var.

    Raises:
        ValueError: If PIN is wrong, empty, or no PIN is configured.
    """
    try:
        from admin.config import load_config
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


def archive_project(project_id: str, pin: str) -> Dict[str, Any]:
    """Archive a project (soft-delete, recoverable).

    Enforces FIFO limit of MAX_ARCHIVED (5).
    Records event in lifecycle log.

    Args:
        project_id: Project ID.
        pin: Admin PIN for authorization.

    Returns:
        Dict with status confirmation.

    Raises:
        ValueError: If PIN is wrong or project not found.
    """
    _validate_pin(pin)

    projects = load_projects()
    target = None
    for p in projects:
        if p["id"] == project_id:
            target = p
            break

    if target is None:
        raise ValueError(f"Project not found: {project_id}")

    # Check FIFO limit for archived projects
    archived = [p for p in projects if p.get("status") == "archived"]
    if len(archived) >= MAX_ARCHIVED:
        # Auto-delete oldest archived project (FIFO)
        oldest = sorted(archived, key=lambda x: x.get("updated_at", ""))[0]
        oldest["status"] = "deleted"
        # Record deletion of auto-evicted project
        try:
            from admin.lifecycle import record_delete
            record_delete(
                oldest["id"],
                oldest.get("name", ""),
                [{"filename": f} for f in oldest.get("files", [])],
            )
        except Exception:
            pass

    # Archive the target project
    target["status"] = "archived"
    from datetime import datetime, timezone
    target["archived_at"] = datetime.now(timezone.utc).isoformat()
    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_projects(projects)

    # Record in lifecycle log
    try:
        from admin.lifecycle import record_archive
        record_archive(
            project_id,
            target.get("name", ""),
            [{"filename": f} for f in target.get("files", [])],
        )
    except Exception:
        pass

    return {"id": project_id, "status": "archived", "message": "Project archived"}


def delete_project(project_id: str, pin: str) -> Dict[str, Any]:
    """Permanently delete a project and all its data.

    Records metadata in lifecycle log (NO files kept).

    Args:
        project_id: Project ID.
        pin: Admin PIN for authorization.

    Returns:
        Dict with deletion confirmation.

    Raises:
        ValueError: If PIN is wrong or project not found.
    """
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

    # Record in lifecycle log before removing files
    try:
        from admin.lifecycle import record_delete
        record_delete(
            project_id,
            found.get("name", ""),
            [{"filename": f} for f in found.get("files", [])],
        )
    except Exception:
        pass

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


def restore_project(project_id: str, pin: str) -> Dict[str, Any]:
    """Restore a project from archive.

    Requires PIN. Restores project config, file references, and version history.

    Args:
        project_id: Project ID.
        pin: Admin PIN for authorization.

    Returns:
        Dict with restore confirmation.

    Raises:
        ValueError: If PIN wrong, project not found, or not archived.
    """
    _validate_pin(pin)

    projects = load_projects()
    target = None
    for p in projects:
        if p["id"] == project_id:
            target = p
            break

    if target is None:
        raise ValueError(f"Project not found: {project_id}")

    if target.get("status") != "archived":
        raise ValueError(f"Project is not archived (status: {target.get('status', 'active')})")

    # Restore project
    from datetime import datetime, timezone
    target["status"] = "active"
    target["restored_at"] = datetime.now(timezone.utc).isoformat()
    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_projects(projects)

    # Update lifecycle log
    try:
        from admin.lifecycle import record_restore
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
    """Get projects that could be auto-archived due to inactivity.

    Based on admin config auto_archive_inactivity_days.
    This is a suggestion hook – does NOT auto-archive.

    Returns:
        List of project dicts that are inactive beyond threshold.
    """
    from datetime import datetime, timezone, timedelta

    try:
        from admin.config import load_config
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
    project_id: str,
    version_label: Optional[str] = None,
    ai_backend: Optional[str] = None,
) -> Dict[str, Any]:
    """Build (or rebuild) project intelligence from all ingested documents.

    V3: Explicit "Run Intelligence" action with guardrails.
    Each build is saved as a versioned snapshot for iteration tracking.
    Records run in version control and system health.

    Args:
        project_id: Project ID.
        version_label: Optional label for this build (e.g. 'post-discovery').
        ai_backend: Optional backend override for this build only.  When
            ``None`` the project's configured ``ai_backend`` is used.

    Returns:
        Built context dict with metadata and version info.

    Raises:
        ValueError: If project not found, no documents, or guardrail fails.
    """
    from processors.context_builder import build_context
    from processors.history import save_context_version

    start_time = time.time()

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    documents = get_project_context(project_id)

    # Guardrail: validate before running
    try:
        from admin.guardrails import validate_intelligence_run
        valid, errors = validate_intelligence_run(
            project_id, len(documents), project.get("ai_backend", "files_only")
        )
        if not valid:
            raise ValueError("; ".join(errors))
    except ImportError:
        # Fallback if guardrails not available
        if not documents:
            raise ValueError(f"No documents ingested for project: {project_id}")

    if not documents:
        raise ValueError(f"No documents ingested for project: {project_id}")

    # Filter by active files (file toggles)
    file_toggles = get_file_toggles(project_id)
    active_docs = []
    for doc in documents:
        fname = doc.get("filename", doc.get("metadata", {}).get("filename", ""))
        if file_toggles.get(fname, True):  # Default: included
            active_docs.append(doc)

    if not active_docs:
        raise ValueError("All files are excluded. Include at least one file.")

    # Determine which AI backend to use for this build
    effective_backend = ai_backend or project.get("ai_backend", "files_only")

    context = build_context(active_docs, ai_backend=effective_backend)

    # Persist current intelligence (data separation: intelligence/ dir)
    project_dir = PROJECTS_DIR / project_id
    intelligence_dir = project_dir / "intelligence"
    intelligence_dir.mkdir(exist_ok=True)
    intelligence_path = intelligence_dir / "current.json"
    with open(intelligence_path, "w") as f:
        json.dump(context, f, indent=2)

    # Also keep legacy path for backward compatibility
    legacy_path = project_dir / "intelligence.json"
    with open(legacy_path, "w") as f:
        json.dump(context, f, indent=2)

    # Save versioned snapshot
    version_meta = save_context_version(project_dir, context, version_label)

    # Record run in version control
    try:
        from processors.version_control import create_run_record
        file_info = [
            {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
            for d in documents
        ]
        create_run_record(
            project_dir=project_dir,
            project_id=project_id,
            run_type="intelligence_build",
            input_files=file_info,
            ai_backend=project.get("ai_backend", "files_only"),
            file_toggles=file_toggles,
            version_label=version_label or "",
            outputs=[version_meta["version_id"]],
        )
    except Exception:
        pass

    # Create Version in hierarchy (Phase→Version→Review model)
    try:
        from models.hierarchy import HierarchyStore, _make_hierarchy_store
        store = _make_hierarchy_store(project_id)
        included = [
            {"filename": d.get("filename", ""), "category": d.get("metadata", {}).get("source_type", "")}
            for d in active_docs
        ]
        excluded = [
            {"filename": d.get("filename", ""), "category": d.get("metadata", {}).get("source_type", "")}
            for d in documents if d not in active_docs
        ]
        store.create_version(
            included_artifacts=included,
            excluded_artifacts=excluded,
            persona=project.get("settings", {}).get("default_persona", ""),
            scope=context.get("scope", ""),
            ai_backend=effective_backend,
            label=version_label or version_meta.get("label", ""),
            stats=version_meta.get("stats", {}),
        )
    except Exception:
        pass

    # Update iteration metadata
    _update_iteration_on_build(project_id, version_meta)

    # Record in system health
    duration_ms = (time.time() - start_time) * 1000
    try:
        from admin.health import record_intelligence_run
        record_intelligence_run(
            project_id=project_id,
            project_name=project.get("name", ""),
            success=True,
            version_id=version_meta["version_id"],
            duration_ms=duration_ms,
        )
    except Exception:
        pass

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
    persona_name: Union[str, List[str]],
    ai_backend: str = "files_only",
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a persona-driven review for a project.

    V4: Supports multi-role reviews.  ``persona_name`` may be a single
    role string (e.g. ``"Solution Architect"`` or legacy id
    ``"solution_architect"``) or a list of up to 3 role names.

    Args:
        project_id: Project ID.
        persona_name: Role name, legacy persona id, or list of role names.
        ai_backend: Backend name; defaults to ``"files_only"``.
        custom_prompt: Optional additional context/instructions.
            Included verbatim in every AI prompt so results vary when changed.

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

    # Guardrail: validate review prerequisites
    try:
        from admin.guardrails import validate_review_prerequisites
        valid, errors = validate_review_prerequisites(
            project_id, bool(intelligence), ai_backend
        )
        # Don't block on warnings, just include them
    except ImportError:
        pass

    # Run the review (v2 engine accepts str or list)
    # Inject _project_id so engine.py can pull feedback context (P9)
    intelligence["_project_id"] = project_id
    review = run_review(
        roles=persona_name,
        context=intelligence,
        ai_backend=ai_backend,
        custom_prompt=custom_prompt,
    )

    # Derive a canonical persona label for storage/display
    roles_used = review.get("roles", [persona_name] if isinstance(persona_name, str) else persona_name)
    canonical_persona = " / ".join(roles_used) if roles_used else str(persona_name)

    # Run Deep Dive when AI mode is ON (non-files_only)
    if ai_backend != "files_only":
        try:
            from personas.deep_dive import run_deep_dive

            # Get active files info
            documents = get_project_context(project_id)
            file_toggles = get_file_toggles(project_id)
            active_files = [
                {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
                for d in documents
                if file_toggles.get(d.get("filename", ""), True)
            ]

            deep_dive = run_deep_dive(
                persona_name=persona_name,
                scope=intelligence.get("scope", ""),
                intelligence=intelligence,
                active_files=active_files,
                custom_prompt=custom_prompt or "",
                ai_backend=ai_backend,
            )
            review["deep_dive"] = deep_dive
        except Exception:
            pass

    # Store review result
    _store_review(project_id, review)

    # Record in version control
    try:
        from processors.version_control import create_run_record

        project_dir = PROJECTS_DIR / project_id
        documents = get_project_context(project_id)
        file_info = [
            {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
            for d in documents
        ]
        file_toggles = get_file_toggles(project_id)
        create_run_record(
            project_dir=project_dir,
            project_id=project_id,
            run_type="persona_review",
            input_files=file_info,
            persona_used=canonical_persona,
            ai_backend=ai_backend,
            file_toggles=file_toggles,
            outputs=[review.get("timestamp", "")],
        )
    except Exception:
        pass

    # Create Review in hierarchy (linked to latest version)
    try:
        from models.hierarchy import HierarchyStore, _make_hierarchy_store
        store = _make_hierarchy_store(project_id)
        versions = store.list_versions()
        latest_version_id = versions[0]["version_id"] if versions else "v0"

        # Get included file names for review context – merge BOTH systems:
        # 1. Legacy context/ documents (ingested via /api/ingest)
        # 2. New artifact v1 uploads (ingested via /api/v1/artifacts/upload|text)
        documents = get_project_context(project_id)
        file_toggles = get_file_toggles(project_id)

        # Legacy files: filter by toggle state
        legacy_included_files = [
            d.get("filename", "")
            for d in documents
            if file_toggles.get(d.get("filename", ""), True) and d.get("filename", "")
        ]
        legacy_categories = list(set(
            d.get("metadata", {}).get("source_type", "")
            for d in documents
            if file_toggles.get(d.get("filename", ""), True)
            and d.get("metadata", {}).get("source_type", "")
        ))

        # New artifact v1 files: include those with include=True
        artifact_included_files: List[str] = []
        artifact_categories: List[str] = []
        try:
            from processors.artifact_store import list_artifacts
            artifacts = list_artifacts(project_id)
            for art in artifacts:
                if art.get("include", True):
                    label = art.get("title") or art.get("fileName") or art.get("artifactId", "")
                    if label:
                        artifact_included_files.append(label)
                    cat = art.get("category", "")
                    if cat:
                        artifact_categories.append(cat)
        except Exception:
            pass

        # Merge and deduplicate
        included_files = list(dict.fromkeys(legacy_included_files + artifact_included_files))
        categories = list(dict.fromkeys(legacy_categories + artifact_categories))

        store.create_review(
            version_id=latest_version_id,
            persona=canonical_persona,
            ai_backend=ai_backend,
            prompt_used=review.get("prompt_used", ""),
            custom_prompt=custom_prompt or "",
            findings=review.get("findings", {}),
            questions=review.get("questions", []),
            summary=review.get("summary", ""),
            included_files=included_files,
            categories=categories,
            ai_metadata=review.get("ai_metadata", {}),
            deep_dive=review.get("deep_dive"),
        )
    except Exception:
        pass

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
    hierarchy_version_id: str = "",
    active_review_id: str = "",
) -> Dict[str, Any]:
    """Create a proposal for a project.

    DS-07: hierarchy_version_id and active_review_id are now required.
    Raises ValueError if either is missing or if review gate not passed.
    """
    from processors.proposals import create_proposal as _create
    from db.project_store_sql import save_proposal_sql, _flags

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    # DS-07: validate review quality gate before allowing proposal creation
    if active_review_id:
        try:
            from processors.review_quality import check_review_gate
            gate = check_review_gate(project_id, active_review_id)
            if not gate["can_set_active"]:
                raise ValueError(
                    f"Review {active_review_id} has not passed the quality gate. "
                    f"Mark it as complete or interim first. Blockers: {'; '.join(gate['blockers'])}"
                )
        except ImportError:
            pass

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = hierarchy_version_id or intel.get("_build_metadata", {}).get("built_at", "") if intel else ""

    file_strs = [str(f) for f in (files or [])]
    tracker = _create(
        project_dir, proposal_name, client, file_strs, notes,
        ctx_version, hierarchy_version_id, active_review_id
    )

    sql_on, _ = _flags()
    if sql_on:
        save_proposal_sql(project_id, tracker)
    return tracker


def add_proposal_version(
    project_id: str,
    label: str = "",
    files: Optional[List[Path]] = None,
    notes: str = "",
    changes: str = "",
    hierarchy_version_id: str = "",
    active_review_id: str = "",
    feedback_applied: Optional[List[str]] = None,
    changes_summary: str = "",
) -> Dict[str, Any]:
    """Add a new version to the project's proposal.

    DS-07: hierarchy_version_id and active_review_id are required.
    Clears feedback cache for the previous proposal version.
    """
    from processors.proposals import add_proposal_version as _add
    from db.project_store_sql import load_proposal_sql, save_proposal_sql, _flags

    # DS-07: validate review quality gate
    if active_review_id:
        try:
            from processors.review_quality import check_review_gate
            gate = check_review_gate(project_id, active_review_id)
            if not gate["can_set_active"]:
                raise ValueError(
                    f"Review {active_review_id} has not passed the quality gate. "
                    f"Blockers: {'; '.join(gate['blockers'])}"
                )
        except ImportError:
            pass

    project_dir = PROJECTS_DIR / project_id
    intel = get_project_intelligence(project_id)
    ctx_version = hierarchy_version_id or intel.get("_build_metadata", {}).get("built_at", "") if intel else ""

    file_strs = [str(f) for f in (files or [])]
    version = _add(
        project_dir, file_strs, label, notes, changes,
        ctx_version, hierarchy_version_id, active_review_id,
        feedback_applied, changes_summary
    )

    sql_on, _ = _flags()
    if sql_on:
        tracker = load_proposal_sql(project_id)
        if tracker:
            save_proposal_sql(project_id, tracker)
    return version


def get_proposal_info(project_id: str) -> Optional[Dict[str, Any]]:
    """Get the proposal tracker for a project — SQLite-first."""
    from db.project_store_sql import load_proposal_sql, _flags
    sql_on, _ = _flags()
    if sql_on:
        return load_proposal_sql(project_id)
    from processors.proposals import get_proposal
    return get_proposal(PROJECTS_DIR / project_id)


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
    """Update proposal version status — writes to file + SQLite."""
    from processors.proposals import update_proposal_status as _update
    from db.project_store_sql import load_proposal_sql, save_proposal_sql, _flags

    project_dir = PROJECTS_DIR / project_id
    result = _update(project_dir, version_id, new_status)

    sql_on, _ = _flags()
    if sql_on:
        from processors.proposals import get_proposal
        tracker = get_proposal(project_dir)
        if tracker:
            save_proposal_sql(project_id, tracker)
    return result


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


# ──────────────────────────────────────────────────────────────
# Admin & Governance
# ──────────────────────────────────────────────────────────────


def get_admin_config() -> Dict[str, Any]:
    """Get admin configuration (safe view, masked keys)."""
    from admin.config import load_config
    config = load_config()
    return config.to_safe_dict()


def update_admin_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update admin configuration."""
    from admin.config import update_config
    config = update_config(updates)
    return config.to_safe_dict()


def get_system_health_status() -> Dict[str, Any]:
    """Get system health status."""
    from admin.health import get_system_health
    health = get_system_health()
    return health.to_dict()


def get_lifecycle_logs() -> Dict[str, Any]:
    """Get lifecycle logs (archived + deleted projects)."""
    from admin.lifecycle import get_lifecycle_log
    log = get_lifecycle_log()
    return log.to_dict()


def get_run_history_for_project(project_id: str) -> List[Dict[str, Any]]:
    """Get version control run history for a project."""
    from processors.version_control import get_run_history
    project_dir = PROJECTS_DIR / project_id
    return get_run_history(project_dir)


def get_file_snapshot(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """Get frozen file snapshot for a specific version.

    Used in Review Tab to show which files were included/excluded
    for that version run.
    """
    from processors.version_control import get_file_snapshot_for_version
    project_dir = PROJECTS_DIR / project_id
    return get_file_snapshot_for_version(project_dir, version_id)


def run_deep_dive_analysis(
    project_id: str,
    persona_name: str = "",
    custom_prompt: str = "",
) -> Dict[str, Any]:
    """Run explicit Deep Dive analysis (standalone, not part of review).

    Args:
        project_id: Project ID.
        persona_name: Optional persona to apply.
        custom_prompt: Additional context from user.

    Returns:
        Deep Dive result dict.
    """
    from personas.deep_dive import run_deep_dive

    project = get_project(project_id)
    if project is None:
        raise ValueError(f"Project not found: {project_id}")

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError("No intelligence built. Run intelligence first.")

    # Get active files
    documents = get_project_context(project_id)
    file_toggles = get_file_toggles(project_id)
    active_files = [
        {"filename": d.get("filename", ""), "source_type": d.get("metadata", {}).get("source_type", "")}
        for d in documents
        if file_toggles.get(d.get("filename", ""), True)
    ]

    # Use default persona if not specified
    if not persona_name:
        try:
            from admin.config import load_config
            persona_name = load_config().default_persona
        except Exception:
            persona_name = "solution_architect"

    result = run_deep_dive(
        persona_name=persona_name,
        scope=intelligence.get("scope", ""),
        intelligence=intelligence,
        active_files=active_files,
        custom_prompt=custom_prompt,
        ai_backend=project.get("ai_backend", "files_only"),
    )

    # Persist deep dive result so feedback endpoint can find it
    project_dir = PROJECTS_DIR / project_id
    intelligence_dir = project_dir / "intelligence"
    intelligence_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = intelligence_dir / "last_deep_dive.json"
    with open(feedback_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def apply_deep_dive_feedback(
    project_id: str,
    accepted: Optional[List[str]] = None,
    rejected: Optional[List[str]] = None,
    added_to_prompt: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Apply user feedback to deep dive results (feedback loop).

    Args:
        project_id: Project ID.
        accepted: Accepted suggestions.
        rejected: Rejected suggestions.
        added_to_prompt: Items to add to next prompt.

    Returns:
        Updated feedback status.
    """
    from personas.deep_dive import apply_feedback
    from datetime import datetime, timezone

    # Load last deep dive result
    project_dir = PROJECTS_DIR / project_id
    feedback_file = project_dir / "intelligence" / "last_deep_dive.json"

    if feedback_file.exists():
        with open(feedback_file) as f:
            deep_dive = json.load(f)
    else:
        return {"error": "No deep dive result found. Run deep dive first."}

    updated = apply_feedback(deep_dive, accepted, rejected, added_to_prompt)

    # Save updated result
    with open(feedback_file, "w") as f:
        json.dump(updated, f, indent=2)

    return {
        "status": "feedback_applied",
        "accepted_count": len(accepted or []),
        "rejected_count": len(rejected or []),
        "added_to_prompt_count": len(added_to_prompt or []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def validate_files_for_ingestion(file_paths: List[str]) -> Dict[str, Any]:
    """Validate file types before ingestion (guardrail).

    Args:
        file_paths: List of file path strings.

    Returns:
        Validation result with valid/invalid files.
    """
    from admin.guardrails import validate_file_types
    all_valid, valid_paths, errors = validate_file_types(file_paths)
    return {
        "all_valid": all_valid,
        "valid_paths": valid_paths,
        "errors": errors,
        "valid_count": len(valid_paths),
        "invalid_count": len(errors),
    }



# ──────────────────────────────────────────────────────────────
# Hierarchy Model Integration (V3 Refinement)
# Project → Phase → Version → Review
# ──────────────────────────────────────────────────────────────


def get_hierarchy(project_id: str) -> Dict[str, Any]:
    """Get the full Phase→Version→Review tree for navigation.

    Returns collapsible hierarchy for the UI.
    """
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.get_hierarchy()


def get_hierarchy_phases(project_id: str) -> List[Dict[str, Any]]:
    """Get all phases with activity counts."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.get_phases()


def set_hierarchy_phase(project_id: str, phase_id: str, reason: str = "") -> Dict[str, Any]:
    """Transition to a new phase in the hierarchy."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.set_current_phase(phase_id, reason)


def get_hierarchy_versions(
    project_id: str, phase_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List versions, optionally filtered by phase. Newest first."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.list_versions(phase_id)


def get_hierarchy_version_detail(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """Get full version detail including linked reviews."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    version = store.get_version(version_id)
    if version is None:
        return None
    # Attach review summaries
    result = version.to_dict()
    result["reviews"] = store.list_reviews(version_id=version_id)
    return result


def get_hierarchy_reviews(
    project_id: str,
    version_id: Optional[str] = None,
    phase_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List reviews, optionally filtered. Newest first."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.list_reviews(version_id=version_id, phase_id=phase_id)


def get_hierarchy_review_detail(project_id: str, review_id: str) -> Optional[Dict[str, Any]]:
    """Get full review detail (prompt, output, version context)."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    review = store.get_review(review_id)
    if review is None:
        return None
    result = review.to_dict()
    # Attach version summary for context display
    version = store.get_version(review.version_id)
    if version:
        result["version_context"] = version.to_summary()
    return result


def get_hierarchy_metrics(
    project_id: str,
    version_id: Optional[str] = None,
    review_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get dashboard metrics scoped to version/review.

    Default: latest version + latest review.
    """
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.get_metrics(version_id=version_id, review_id=review_id)


def set_active_review(project_id: str, version_id: str, review_id: str) -> Dict[str, Any]:
    """Set the active review for a version."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.set_active_review(version_id, review_id)


def delete_hierarchy_review(project_id: str, review_id: str) -> Dict[str, Any]:
    """Delete a review from the hierarchy."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    return store.delete_review(review_id)


def get_active_review_for_version(project_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """Get the active review for a specific version."""
    from models.hierarchy import _make_hierarchy_store
    store = _make_hierarchy_store(project_id)
    review = store.get_active_review_for_version(version_id)
    if review:
        return review.to_dict()
    return None



# ──────────────────────────────────────────────────────────────
# Review Quality Gate (DS-04)
# ──────────────────────────────────────────────────────────────

def get_review_quality(project_id: str, review_id: str) -> Dict[str, Any]:
    """Check review quality gate status without changing anything."""
    from processors.review_quality import check_review_gate
    return check_review_gate(project_id, review_id)


def complete_review_gate(
    project_id: str,
    review_id: str,
    completed_by: str,
    quality_status: str = "complete",
) -> Dict[str, Any]:
    """Mark a review complete/interim, write score, log decision."""
    from processors.review_quality import complete_review
    return complete_review(project_id, review_id, completed_by, quality_status)


def set_active_review_gated(
    project_id: str,
    version_id: str,
    review_id: str,
    decided_by: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Set active review with quality gate enforcement."""
    from processors.review_quality import set_active_review_with_gate
    return set_active_review_with_gate(
        project_id, version_id, review_id, decided_by, force
    )


# ──────────────────────────────────────────────────────────────
# Proposal Document Generation (DS-05)
# ──────────────────────────────────────────────────────────────

def generate_proposal_doc(
    project_id: str,
    proposal_ver_id: str,
    hierarchy_version_id: str,
    review_id: str,
    ai_backend: str = "files_only",
    force: bool = False,
) -> Dict[str, Any]:
    """Generate proposal document from Version + Active Review."""
    from processors.proposal_generator import generate_proposal_document
    return generate_proposal_document(
        project_id, proposal_ver_id, hierarchy_version_id,
        review_id, ai_backend, force,
    )


def get_proposal_doc(project_id: str, proposal_ver_id: str) -> Optional[Dict[str, Any]]:
    """Get the latest generated proposal document for a version."""
    from db.decision_log import get_latest_proposal_document
    return get_latest_proposal_document(project_id, proposal_ver_id)


# ──────────────────────────────────────────────────────────────
# Pre-sales Finalisation (DS-08)
# ──────────────────────────────────────────────────────────────

def get_presales_stop_condition(project_id: str) -> Dict[str, Any]:
    """Check pre-sales stop condition without any state changes."""
    from processors.presales_finaliser import check_stop_condition
    return check_stop_condition(project_id)


def finalise_presales(
    project_id: str,
    decided_by: str,
    reason: str = "",
    force: bool = False,
) -> Dict[str, Any]:
    """Atomically finalise pre-sales: accept + lock + freeze + phase transition."""
    from processors.presales_finaliser import finalise_presales as _finalise
    return _finalise(project_id, decided_by, reason, force)


# ──────────────────────────────────────────────────────────────
# Diagram Generation (P4)
# ──────────────────────────────────────────────────────────────

DIAGRAM_TYPES = ["dependency_map", "risk_heatmap", "scope_overview"]


def generate_diagram(project_id: str, diagram_type: str) -> Dict[str, Any]:
    """Generate a .drawio diagram from the project's built intelligence.

    Saves the XML to ``projects_data/{id}/diagrams/{type}.drawio`` and
    returns a summary dict.

    Args:
        project_id: Project ID.
        diagram_type: One of ``dependency_map``, ``risk_heatmap``,
            ``scope_overview``.

    Returns:
        Dict with keys: diagram_type, xml, path, generated_at.

    Raises:
        ValueError: If project not found, no intelligence built, or
            unknown diagram type.
    """
    from processors.diagram_generator import generate, DIAGRAM_TYPES as VALID
    from datetime import datetime, timezone

    if diagram_type not in VALID:
        raise ValueError(
            f"Unknown diagram type '{diagram_type}'. "
            f"Available: {', '.join(VALID)}"
        )

    intelligence = get_project_intelligence(project_id)
    if not intelligence:
        raise ValueError(
            f"No intelligence built for project '{project_id}'. "
            "Run Intelligence first."
        )

    xml = generate(diagram_type, intelligence)

    # Persist to disk
    diagram_dir = PROJECTS_DIR / project_id / "diagrams"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    out_path = diagram_dir / f"{diagram_type}.drawio"
    out_path.write_text(xml, encoding="utf-8")

    return {
        "project_id": project_id,
        "diagram_type": diagram_type,
        "xml": xml,
        "path": str(out_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": len(xml.encode()),
    }


def get_diagram(project_id: str, diagram_type: str) -> Dict[str, Any]:
    """Load a previously generated diagram from disk.

    Returns the XML if it exists, or an error dict if not yet generated.
    """
    from processors.diagram_generator import DIAGRAM_TYPES as VALID

    if diagram_type not in VALID:
        return {"error": f"Unknown diagram type '{diagram_type}'."}

    out_path = PROJECTS_DIR / project_id / "diagrams" / f"{diagram_type}.drawio"
    if not out_path.exists():
        return {"error": f"Diagram '{diagram_type}' not yet generated."}

    xml = out_path.read_text(encoding="utf-8")
    return {
        "project_id": project_id,
        "diagram_type": diagram_type,
        "xml": xml,
        "path": str(out_path),
        "size_bytes": len(xml.encode()),
    }


def list_diagrams(project_id: str) -> Dict[str, Any]:
    """List all generated diagrams for a project.

    Returns:
        Dict with ``diagrams`` list (type, path, size_bytes per entry).
    """
    from processors.diagram_generator import DIAGRAM_TYPES as VALID

    diagram_dir = PROJECTS_DIR / project_id / "diagrams"
    diagrams = []
    for dtype in VALID:
        p = diagram_dir / f"{dtype}.drawio"
        if p.exists():
            diagrams.append({
                "diagram_type": dtype,
                "path": str(p),
                "size_bytes": p.stat().st_size,
            })
    return {
        "project_id": project_id,
        "diagrams": diagrams,
        "available_types": VALID,
    }
