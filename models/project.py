"""Core project data models.

Defines the structure for projects, context packs, and review outputs.
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
