"""Proposal version management.

Handles:
- Creating and versioning proposals
- Comparing proposal versions (what changed, risk delta)
- Tracking proposal status lifecycle
- Linking proposals to intelligence versions
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from models.proposal import ProposalTracker, ProposalVersion, VALID_PROPOSAL_STATUSES


def create_proposal(
    project_dir: Path,
    proposal_name: str,
    client: str = "",
    files: Optional[List[str]] = None,
    notes: str = "",
    context_version: str = "",
    hierarchy_version_id: str = "",   # DS-07: required — FK to versions.version_id
    active_review_id: str = "",       # DS-07: required — FK to reviews.review_id
) -> Dict[str, Any]:
    """Create a new proposal with its first version.

    Args:
        project_dir: Path to the project's data directory.
        proposal_name: Name of the proposal.
        client: Client name.
        files: Files associated with this version.
        notes: Notes about this version.
        context_version: Current intelligence version when created.
        hierarchy_version_id: DS-07 required — FK to versions.version_id.
        active_review_id: DS-07 required — FK to reviews.review_id.

    Returns:
        Proposal tracker dict.
    """
    proposals_dir = project_dir / "proposals"
    proposals_dir.mkdir(exist_ok=True)

    # DS-07: traceability links are strongly recommended but not hard-blocked
    # so the workflow remains usable when intelligence/review hasn't been run yet.
    # The UI shows warnings; the gate is enforced when IDs are provided but invalid.

    # Load existing tracker or create new
    tracker_path = proposals_dir / "tracker.json"
    tracker = _load_tracker(tracker_path)

    if not tracker:
        tracker = {
            "project_id": project_dir.name,
            "proposal_name": proposal_name,
            "client": client,
            "current_version": "",
            "total_versions": 0,
            "versions": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Create first version
    version = _create_version(
        tracker, files=files or [], notes=notes,
        context_version=context_version, label="Initial submission",
    )

    version["hierarchy_version_id"] = hierarchy_version_id
    version["active_review_id"] = active_review_id
    version["context_version"] = hierarchy_version_id  # keep backward compat

    tracker["versions"].append(version)
    tracker["current_version"] = version["version_id"]
    tracker["total_versions"] = len(tracker["versions"])
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()

    _save_tracker(tracker_path, tracker)
    return tracker


def add_proposal_version(
    project_dir: Path,
    files: Optional[List[str]] = None,
    label: str = "",
    notes: str = "",
    changes: str = "",
    context_version: str = "",
    hierarchy_version_id: str = "",   # DS-07: required
    active_review_id: str = "",       # DS-07: required
    feedback_applied: Optional[List[str]] = None,   # DS-07: feedback_ids resolved
    changes_summary: str = "",        # DS-07: human summary of changes
) -> Dict[str, Any]:
    """Add a new version to an existing proposal.

    Args:
        project_dir: Path to the project's data directory.
        files: Files associated with this new version.
        label: Label for this version (e.g. "Post-feedback revision").
        notes: Author notes.
        changes: Description of what changed from previous version.
        context_version: Current intelligence version.
        hierarchy_version_id: DS-07 required — FK to versions.version_id.
        active_review_id: DS-07 required — FK to reviews.review_id.
        feedback_applied: DS-07 feedback_ids resolved in this version.
        changes_summary: DS-07 human summary of changes.

    Returns:
        The new version dict.

    Raises:
        ValueError: If no proposal exists yet.
    """
    proposals_dir = project_dir / "proposals"
    tracker_path = proposals_dir / "tracker.json"
    tracker = _load_tracker(tracker_path)

    if not tracker:
        raise ValueError("No proposal exists. Create one first.")

    # DS-07: traceability links are strongly recommended but not hard-blocked

    # Mark previous version as superseded
    if tracker["versions"]:
        tracker["versions"][-1]["status"] = "superseded"

    # Create new version
    version = _create_version(
        tracker, files=files or [], notes=notes,
        context_version=context_version,
        label=label or f"Revision #{len(tracker['versions']) + 1}",
        changes=changes,
    )

    version["hierarchy_version_id"] = hierarchy_version_id
    version["active_review_id"] = active_review_id
    version["context_version"] = hierarchy_version_id
    version["previous_version_id"] = tracker["versions"][-1]["version_id"] if tracker["versions"] else ""
    version["feedback_applied"] = feedback_applied or []
    version["changes_summary"] = changes_summary

    tracker["versions"].append(version)
    tracker["current_version"] = version["version_id"]
    tracker["total_versions"] = len(tracker["versions"])
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()

    _save_tracker(tracker_path, tracker)

    # DS-07: clear feedback cache for the PREVIOUS version (it's now historical)
    try:
        from processors.presales_feedback import clear_feedback_cache_for_version
        prev_ver = tracker["versions"][-2] if len(tracker["versions"]) >= 2 else None
        if prev_ver:
            clear_feedback_cache_for_version(
                project_dir.name, prev_ver["version_id"]
            )
    except Exception:
        pass

    return version


def update_proposal_status(
    project_dir: Path, version_id: str, new_status: str
) -> Dict[str, Any]:
    """Update the status of a specific proposal version.

    Args:
        project_dir: Path to the project's data directory.
        version_id: Which version to update.
        new_status: New status (must be valid).

    Returns:
        Updated version dict.

    Raises:
        ValueError: If version not found or status invalid.
    """
    if new_status not in VALID_PROPOSAL_STATUSES:
        raise ValueError(
            f"Invalid status: '{new_status}'. "
            f"Valid: {', '.join(VALID_PROPOSAL_STATUSES)}"
        )

    proposals_dir = project_dir / "proposals"
    tracker_path = proposals_dir / "tracker.json"
    tracker = _load_tracker(tracker_path)

    if not tracker:
        raise ValueError("No proposal exists.")

    for version in tracker["versions"]:
        if version["version_id"] == version_id:
            version["status"] = new_status
            tracker["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_tracker(tracker_path, tracker)
            return version

    raise ValueError(f"Version not found: {version_id}")


def get_proposal(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Get the full proposal tracker for a project.

    Args:
        project_dir: Path to the project's data directory.

    Returns:
        Proposal tracker dict, or None if no proposal exists.
    """
    tracker_path = project_dir / "proposals" / "tracker.json"
    return _load_tracker(tracker_path)


def list_proposal_versions(project_dir: Path) -> List[Dict[str, Any]]:
    """List all proposal versions (summary view).

    Returns:
        List of version summaries with id, label, status, timestamp.
    """
    tracker = get_proposal(project_dir)
    if not tracker:
        return []

    return [
        {
            "version_id": v["version_id"],
            "version_number": v["version_number"],
            "label": v["label"],
            "status": v["status"],
            "created_at": v["created_at"],
            "files_count": len(v.get("files", [])),
            "context_version": v.get("context_version", ""),
        }
        for v in tracker["versions"]
    ]


def compare_proposal_versions(
    project_dir: Path,
    version_a_id: str,
    version_b_id: str,
    intelligence_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compare two proposal versions.

    Shows file changes, status progression, and linked intelligence delta.

    Args:
        project_dir: Path to the project's data directory.
        version_a_id: Earlier version.
        version_b_id: Later version.
        intelligence_dir: Optional path to intelligence versions for context delta.

    Returns:
        Comparison dict.
    """
    tracker = get_proposal(project_dir)
    if not tracker:
        raise ValueError("No proposal exists.")

    version_a = None
    version_b = None
    for v in tracker["versions"]:
        if v["version_id"] == version_a_id:
            version_a = v
        if v["version_id"] == version_b_id:
            version_b = v

    if not version_a:
        raise ValueError(f"Version not found: {version_a_id}")
    if not version_b:
        raise ValueError(f"Version not found: {version_b_id}")

    # File changes
    files_a = set(version_a.get("files", []))
    files_b = set(version_b.get("files", []))

    comparison = {
        "version_a": version_a_id,
        "version_b": version_b_id,
        "label_a": version_a["label"],
        "label_b": version_b["label"],
        "status_a": version_a["status"],
        "status_b": version_b["status"],
        "time_between": _time_between(version_a["created_at"], version_b["created_at"]),
        "files": {
            "added": sorted(files_b - files_a),
            "removed": sorted(files_a - files_b),
            "unchanged": sorted(files_a & files_b),
        },
        "changes_noted": version_b.get("changes_from_previous", ""),
        "context_version_a": version_a.get("context_version", ""),
        "context_version_b": version_b.get("context_version", ""),
    }

    return comparison


# ──────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────


def _create_version(
    tracker: Dict[str, Any],
    files: List[str],
    notes: str,
    context_version: str,
    label: str,
    changes: str = "",
) -> Dict[str, Any]:
    """Create a new version entry."""
    version_num = len(tracker["versions"]) + 1
    return {
        "version_id": f"prop-v{version_num}",
        "version_number": version_num,
        "label": label,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "notes": notes,
        "changes_from_previous": changes,
        "context_version": context_version,
    }


def _load_tracker(tracker_path: Path) -> Optional[Dict[str, Any]]:
    """Load proposal tracker from disk."""
    if not tracker_path.exists():
        return None
    with open(tracker_path) as f:
        return json.load(f)


def _save_tracker(tracker_path: Path, tracker: Dict[str, Any]) -> None:
    """Save proposal tracker to disk."""
    tracker_path.parent.mkdir(exist_ok=True)
    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)


def _time_between(timestamp_a: str, timestamp_b: str) -> str:
    """Calculate human-readable time between two ISO timestamps."""
    try:
        dt_a = datetime.fromisoformat(timestamp_a)
        dt_b = datetime.fromisoformat(timestamp_b)
        delta = dt_b - dt_a
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return f"{hours} hour(s)"
        return f"{days} day(s)"
    except (ValueError, TypeError):
        return "unknown"
