"""Proposal models for multi-version pre-sales tracking.

Tracks multiple proposal versions per project:
- What changed between versions
- Which risks increased/decreased
- Which assumptions evolved
- Delta analysis across versions
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
