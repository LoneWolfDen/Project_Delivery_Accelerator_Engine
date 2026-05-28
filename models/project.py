"""Core project data models.

Defines the structure for projects, context packs, review outputs,
and iteration tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


@dataclass
class ProjectContext:
    """Structured context extracted from project documents."""

    scope: str = ""
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    summary: str = ""
    raw_extractions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReviewOutput:
    """Output from a persona-driven review."""

    persona: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risks: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class IterationMetadata:
    """Tracks iteration state for a project.

    Records which context version is current, how many reviews have been run,
    and the phase progression history.
    """

    current_version: str = ""  # e.g. "v3"
    total_builds: int = 0
    total_reviews: int = 0
    last_build_at: str = ""
    last_review_at: str = ""
    phase_history: List[Dict[str, str]] = field(default_factory=list)
    # Each entry: {"phase": "discovery", "entered_at": "...", "exited_at": "..."}


@dataclass
class Project:
    """Top-level project entity."""

    id: str = ""
    name: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: str = "discovery"  # discovery | proposal | planning | execution | review
    ai_backend: str = "ollama"  # ollama | bedrock | files_only
    context: Optional[ProjectContext] = None
    reviews: List[ReviewOutput] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    iteration: Optional[IterationMetadata] = None
