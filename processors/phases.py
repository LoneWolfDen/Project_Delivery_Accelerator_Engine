"""Phase transition management.

Tracks project movement through SDLC phases:
  Discovery → Proposal → Planning → Execution → Review

Features:
- Validates phase transitions (can only move forward or back one step)
- Records entry/exit timestamps for each phase
- Provides phase history and duration analytics
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Valid SDLC phases in order
PHASES = ["discovery", "proposal", "planning", "execution", "review"]

# Valid transitions (current_phase → allowed_next_phases)
VALID_TRANSITIONS = {
    "discovery": ["proposal"],
    "proposal": ["discovery", "planning"],  # Can go back to discovery
    "planning": ["proposal", "execution"],
    "execution": ["planning", "review"],
    "review": ["execution", "planning"],  # Can loop back for iterations
}


def transition_phase(
    project_dir: Path,
    projects_file: Path,
    project_id: str,
    new_phase: str,
    reason: str = "",
) -> Dict[str, Any]:
    """Transition a project to a new phase.

    Args:
        project_dir: Path to the project's data directory.
        projects_file: Path to projects.json.
        project_id: Project ID.
        new_phase: Target phase.
        reason: Optional reason for the transition.

    Returns:
        Transition record dict.

    Raises:
        ValueError: If phase is invalid or transition not allowed.
    """
    if new_phase not in PHASES:
        raise ValueError(
            f"Invalid phase: '{new_phase}'. Valid: {', '.join(PHASES)}"
        )

    # Load project
    with open(projects_file) as f:
        projects = json.load(f)

    project = None
    for p in projects:
        if p["id"] == project_id:
            project = p
            break

    if not project:
        raise ValueError(f"Project not found: {project_id}")

    current_phase = project.get("phase", "discovery")

    # Validate transition
    allowed = VALID_TRANSITIONS.get(current_phase, [])
    if new_phase not in allowed:
        raise ValueError(
            f"Cannot transition from '{current_phase}' to '{new_phase}'. "
            f"Allowed: {', '.join(allowed)}"
        )

    timestamp = datetime.now(timezone.utc).isoformat()

    # Record transition
    transition_record = {
        "from_phase": current_phase,
        "to_phase": new_phase,
        "timestamp": timestamp,
        "reason": reason,
    }

    # Update phase history
    iteration = project.get("iteration") or {}
    phase_history = iteration.get("phase_history", [])

    # Close current phase entry
    if phase_history:
        phase_history[-1]["exited_at"] = timestamp

    # Open new phase entry
    phase_history.append({
        "phase": new_phase,
        "entered_at": timestamp,
        "exited_at": "",
        "reason": reason,
    })

    iteration["phase_history"] = phase_history
    project["iteration"] = iteration
    project["phase"] = new_phase
    project["updated_at"] = timestamp

    # Save
    with open(projects_file, "w") as f:
        json.dump(projects, f, indent=2)

    # Also save transition log
    _log_transition(project_dir, transition_record)

    return transition_record


def get_phase_history(project_dir: Path, projects_file: Path, project_id: str) -> List[Dict[str, Any]]:
    """Get the phase history for a project.

    Args:
        project_dir: Path to the project's data directory.
        projects_file: Path to projects.json.
        project_id: Project ID.

    Returns:
        List of phase history entries with durations.
    """
    with open(projects_file) as f:
        projects = json.load(f)

    project = None
    for p in projects:
        if p["id"] == project_id:
            project = p
            break

    if not project:
        return []

    iteration = project.get("iteration") or {}
    phase_history = iteration.get("phase_history", [])

    # Enrich with durations
    enriched = []
    for entry in phase_history:
        entered = entry.get("entered_at", "")
        exited = entry.get("exited_at", "")
        duration = _calculate_duration(entered, exited) if entered else "unknown"
        enriched.append({
            **entry,
            "duration": duration,
            "is_current": exited == "",
        })

    return enriched


def get_current_phase(projects_file: Path, project_id: str) -> str:
    """Get the current phase for a project."""
    with open(projects_file) as f:
        projects = json.load(f)

    for p in projects:
        if p["id"] == project_id:
            return p.get("phase", "discovery")

    return "unknown"


def get_phase_info() -> List[Dict[str, Any]]:
    """Get information about all phases and allowed transitions."""
    return [
        {
            "phase": phase,
            "order": i + 1,
            "can_transition_to": VALID_TRANSITIONS.get(phase, []),
        }
        for i, phase in enumerate(PHASES)
    ]


# ──────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────


def _log_transition(project_dir: Path, transition: Dict[str, Any]) -> None:
    """Append transition to the project's transition log."""
    log_path = project_dir / "transitions.json"
    log: List[Dict[str, Any]] = []

    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)

    log.append(transition)

    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


def _calculate_duration(entered: str, exited: str) -> str:
    """Calculate human-readable duration between two timestamps."""
    try:
        dt_entered = datetime.fromisoformat(entered)
        if exited:
            dt_exited = datetime.fromisoformat(exited)
        else:
            dt_exited = datetime.now(timezone.utc)

        delta = dt_exited - dt_entered
        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            return f"{days}d {hours}h"
        return f"{hours}h {(delta.seconds % 3600) // 60}m"
    except (ValueError, TypeError):
        return "unknown"
