"""Proposal models for multi-version pre-sales tracking.

Tracks multiple proposal versions per project:
- What changed between versions
- Which risks increased/decreased
- Which assumptions evolved
- Delta analysis across versions
- P9: Pre-sales feedback loop (internal + external)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


VALID_PROPOSAL_STATUSES = [
    "draft",
    "submitted",
    "under_review",
    "revised",
    "accepted",
    "rejected",
    "superseded",
]

VALID_FEEDBACK_STATUSES = ["open", "actioned", "closed"]
VALID_FEEDBACK_SOURCES  = ["internal", "external"]


@dataclass
class ProposalVersion:
    """A single version of a proposal."""

    version_id: str = ""  # e.g. "prop-v1"
    version_number: int = 0
    label: str = ""  # e.g. "Initial submission", "Post-feedback revision"
    status: str = "draft"  # One of VALID_PROPOSAL_STATUSES
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files: List[str] = field(default_factory=list)  # Files included in this version
    notes: str = ""  # Author notes about this version
    changes_from_previous: str = ""  # What changed from last version
    context_version: str = ""  # Which intelligence version was current when this was created
    # P9: feedback captured against this version (summary; full records in presales_feedback table)
    feedback: Optional[Dict[str, Any]] = None


@dataclass
class ProposalTracker:
    """Tracks all proposal versions for a project."""

    project_id: str = ""
    proposal_name: str = ""
    client: str = ""
    current_version: str = ""  # Latest version_id
    total_versions: int = 0
    versions: List[ProposalVersion] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PresalesFeedback:
    """P9 – Feedback captured against a proposal version or review.

    Supports two sources:
    - internal: captured by the delivery team (PM, SA, etc.)
    - external: submitted by the client via a share link / form

    Schema mirrors the presales_feedback SQLite table.
    """

    feedback_id: str = ""
    project_id: str = ""
    proposal_ver_id: str = ""   # links to ProposalVersion.version_id
    review_id: str = ""         # links to Review.review_id (optional)
    source: str = "internal"    # "internal" | "external"
    responder_name: str = ""
    responder_email: str = ""
    accepted: List[str] = field(default_factory=list)   # items client accepted
    rejected: List[str] = field(default_factory=list)   # items client rejected
    concerns: List[str] = field(default_factory=list)   # concerns / questions raised
    notes: str = ""
    next_action: str = ""
    status: str = "open"        # "open" | "actioned" | "closed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id":    self.feedback_id,
            "project_id":     self.project_id,
            "proposal_ver_id": self.proposal_ver_id,
            "review_id":      self.review_id,
            "source":         self.source,
            "responder_name": self.responder_name,
            "responder_email": self.responder_email,
            "accepted":       self.accepted,
            "rejected":       self.rejected,
            "concerns":       self.concerns,
            "notes":          self.notes,
            "next_action":    self.next_action,
            "status":         self.status,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
        }
