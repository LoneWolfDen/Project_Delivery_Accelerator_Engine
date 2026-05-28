"""Version Control – Records for every intelligence run.

Every run creates:
- version_id
- timestamp
- input_files[] (with active/inactive state)
- persona_used
- outputs[]
- file_snapshot (frozen file set for reproducibility)

Supports:
- View versions
- Compare (future hook)
- Tie file selection to version snapshot
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid


VERSIONS_DIR_NAME = "versions"


def create_run_record(
    project_dir: Path,
    project_id: str,
    run_type: str,
    input_files: List[Dict[str, Any]],
    persona_used: str = "",
    ai_backend: str = "files_only",
    outputs: Optional[List[str]] = None,
    file_toggles: Optional[Dict[str, bool]] = None,
    version_label: str = "",
) -> Dict[str, Any]:
    """Create a versioned run record for traceability.

    Args:
        project_dir: Project data directory.
        project_id: Project ID.
        run_type: 'intelligence_build' or 'persona_review'.
        input_files: List of file info dicts [{filename, active, source_type}].
        persona_used: Persona ID if review, empty if build.
        ai_backend: AI backend used.
        outputs: List of output identifiers.
        file_toggles: File active/inactive state at time of run.
        version_label: Optional human-readable label.

    Returns:
        Run record dict.
    """
    runs_dir = project_dir / "run_history"
    runs_dir.mkdir(exist_ok=True)

    # Generate unique run ID
    existing_runs = list(runs_dir.glob("run_*.json"))
    run_number = len(existing_runs) + 1
    run_id = f"run_{run_number:04d}"

    timestamp = datetime.now(timezone.utc).isoformat()

    # Build file snapshot (freeze file set for this version)
    file_snapshot = []
    for f in input_files:
        filename = f.get("filename", "") if isinstance(f, dict) else str(f)
        is_active = True
        if file_toggles and filename in file_toggles:
            is_active = file_toggles[filename]
        file_snapshot.append({
            "filename": filename,
            "active": is_active,
            "source_type": f.get("source_type", "unknown") if isinstance(f, dict) else "unknown",
        })

    record: Dict[str, Any] = {
        "run_id": run_id,
        "version_id": f"v{run_number}",
        "project_id": project_id,
        "run_type": run_type,
        "timestamp": timestamp,
        "label": version_label or f"{run_type} #{run_number}",
        "input_files": file_snapshot,
        "included_files": [f for f in file_snapshot if f["active"]],
        "excluded_files": [f for f in file_snapshot if not f["active"]],
        "persona_used": persona_used,
        "ai_backend": ai_backend,
        "outputs": outputs or [],
        "file_toggles_snapshot": file_toggles or {},
    }

    # Save run record
    run_file = runs_dir / f"{run_id}.json"
    with open(run_file, "w") as f:
        json.dump(record, f, indent=2)

    # Update run index
    _update_run_index(runs_dir, record)

    return record


def get_run_history(project_dir: Path) -> List[Dict[str, Any]]:
    """Get all run records for a project, newest first.

    Args:
        project_dir: Project data directory.

    Returns:
        List of run record summaries.
    """
    runs_dir = project_dir / "run_history"
    index_file = runs_dir / "index.json"

    if not index_file.exists():
        return []

    with open(index_file) as f:
        index = json.load(f)

    return sorted(index, key=lambda r: r.get("timestamp", ""), reverse=True)


def get_run_record(project_dir: Path, run_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific run record.

    Args:
        project_dir: Project data directory.
        run_id: Run identifier.

    Returns:
        Full run record, or None if not found.
    """
    runs_dir = project_dir / "run_history"
    run_file = runs_dir / f"{run_id}.json"

    if not run_file.exists():
        return None

    with open(run_file) as f:
        return json.load(f)


def get_file_snapshot_for_version(
    project_dir: Path, version_id: str
) -> Optional[Dict[str, Any]]:
    """Get the frozen file snapshot for a specific version.

    Ensures reproducibility by showing exactly which files were
    included/excluded at the time of that run.

    Args:
        project_dir: Project data directory.
        version_id: Version identifier (e.g. 'v1').

    Returns:
        File snapshot dict with included/excluded files.
    """
    runs_dir = project_dir / "run_history"
    if not runs_dir.exists():
        return None

    # Search by version_id
    for run_file in runs_dir.glob("run_*.json"):
        with open(run_file) as f:
            record = json.load(f)
        if record.get("version_id") == version_id:
            return {
                "version_id": version_id,
                "timestamp": record.get("timestamp", ""),
                "included_files": record.get("included_files", []),
                "excluded_files": record.get("excluded_files", []),
                "total_files": len(record.get("input_files", [])),
            }

    return None


def _update_run_index(runs_dir: Path, record: Dict[str, Any]) -> None:
    """Update the run history index file."""
    index_file = runs_dir / "index.json"
    index: List[Dict[str, Any]] = []

    if index_file.exists():
        with open(index_file) as f:
            index = json.load(f)

    # Store summary in index (not full record)
    summary = {
        "run_id": record["run_id"],
        "version_id": record["version_id"],
        "run_type": record["run_type"],
        "timestamp": record["timestamp"],
        "label": record["label"],
        "persona_used": record["persona_used"],
        "ai_backend": record["ai_backend"],
        "included_file_count": len(record["included_files"]),
        "excluded_file_count": len(record["excluded_files"]),
    }

    index.append(summary)

    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)
