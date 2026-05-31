"""Shared value types — dataclasses that cross domain boundaries.

Rules
-----
- All fields have defaults so callers can construct partial objects.
- No imports from services/, handlers/, or project_manager.
- No business logic — pure data carriers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Review seam ───────────────────────────────────────────────────────────────

@dataclass
class ReviewRequest:
    """Input contract for a persona review run."""

    project_id: str
    roles: List[str]
    ai_backend: str = "files_only"
    custom_prompt: Optional[str] = None
    previous_review_id: str = ""
    prompt_builder_state: Optional[Dict[str, Any]] = None


@dataclass
class ReviewResult:
    """Output contract returned by a ReviewAgent."""

    project_id: str
    review_id: str
    persona: str
    ai_backend: str
    findings: Dict[str, List[str]] = field(default_factory=dict)
    weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    missing_categories: List[str] = field(default_factory=list)
    summary: str = ""
    questions: List[str] = field(default_factory=list)
    ai_metadata: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_service_dict(cls, project_id: str, data: Dict[str, Any]) -> "ReviewResult":
        """Construct from the dict returned by services.review.run_persona_review."""
        roles = data.get("roles", [])
        persona = " / ".join(roles) if roles else data.get("persona", "")
        return cls(
            project_id=project_id,
            review_id=data.get("review_id", ""),
            persona=persona,
            ai_backend=data.get("ai_backend", "files_only"),
            findings=data.get("findings", {}),
            weaknesses=data.get("weaknesses", []),
            decision_points=data.get("decision_points", []),
            missing_categories=data.get("missing_categories", []),
            summary=data.get("summary", ""),
            questions=data.get("questions", []),
            ai_metadata=data.get("ai_metadata", {}),
            raw=data,
        )


# ── Event seam ────────────────────────────────────────────────────────────────

@dataclass
class Event:
    """A domain event published via ServiceBus.

    ``topic``   — dot-separated hierarchy, e.g. ``review.completed``
    ``payload`` — arbitrary serialisable dict
    ``source``  — originating module path, e.g. ``services.review``
    """

    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = ""


# ── Well-known event topics ───────────────────────────────────────────────────

class Topics:
    """String constants for all published event topics.

    Using a class of constants (not Enum) so values are plain strings and
    subscribers can pattern-match with startswith / split without coercion.
    """

    # Review lifecycle
    REVIEW_STARTED   = "review.started"
    REVIEW_COMPLETED = "review.completed"
    REVIEW_FAILED    = "review.failed"

    # Intelligence
    INTELLIGENCE_BUILT = "intelligence.built"

    # Proposal
    PROPOSAL_CREATED        = "proposal.created"
    PROPOSAL_VERSION_ADDED  = "proposal.version_added"
    PROPOSAL_FINALISED      = "proposal.finalised"

    # Deep-dive / SME
    DEEP_DIVE_COMPLETED = "deep_dive.completed"

    # Project lifecycle
    PROJECT_CREATED  = "project.created"
    PROJECT_ARCHIVED = "project.archived"
    PROJECT_DELETED  = "project.deleted"
