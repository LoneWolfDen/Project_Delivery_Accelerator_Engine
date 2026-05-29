"""Proposal models — Decision System (DS-02).

Entity chain: Intelligence Version → Review (gate) → Proposal Version (gate)
              → Feedback Items (structured) → Injection → Loop → Finalise

Key changes from P9:
- ProposalVersion: adds hierarchy_version_id, active_review_id, previous_version_id,
  feedback_applied, changes_summary, quality_status, quality_score,
  completed_by, completed_at, lock_status, lock_reason
- PresalesFeedback: replaces flat accepted/rejected/concerns with
  feedback_items: List[FeedbackItem], adds raw_text
- New: FeedbackItem dataclass (the atomic unit of structured feedback)
- New: ProposalDocument dataclass (generated proposal sections)
- New constants: FEEDBACK_CATEGORIES, FEEDBACK_MAPPED_TO,
  FEEDBACK_CONFIDENCE, FEEDBACK_ITEM_STATUS
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Constants ──────────────────────────────────────────────────

VALID_PROPOSAL_STATUSES = [
    "draft", "submitted", "under_review", "revised",
    "accepted", "rejected", "superseded",
]
VALID_PROPOSAL_QUALITY  = ["draft", "interim", "complete"]
VALID_LOCK_STATUSES     = ["unlocked", "soft_locked"]

VALID_FEEDBACK_STATUSES = ["open", "actioned", "closed"]
VALID_FEEDBACK_SOURCES  = ["internal", "external"]

# DS-02: four feedback categories (change_requested is the new addition)
FEEDBACK_CATEGORIES = ["accepted", "rejected", "change_requested", "concerns"]

# DS-02: what each feedback item maps to in delivery terms
FEEDBACK_MAPPED_TO = [
    "risk", "gap", "scope_change", "constraint", "assumption", None
]

# DS-02: confidence enum (high/medium/low — for history readability)
FEEDBACK_CONFIDENCE = ["high", "medium", "low"]

# DS-02: lifecycle of a single feedback item
FEEDBACK_ITEM_STATUS = ["new", "addressed", "deferred", "rejected_by_team"]


# ── FeedbackItem — atomic unit of structured feedback ──────────

@dataclass
class FeedbackItem:
    """A single classified feedback statement from a client or internal reviewer.

    This replaces the flat string lists (accepted/rejected/concerns) used in P9.
    Every item has: text, category, mapping target, confidence, lifecycle status.
    """

    item_id: str = field(default_factory=lambda: f"fi_{uuid.uuid4().hex[:8]}")
    text: str = ""
    category: str = "concerns"          # accepted | rejected | change_requested | concerns
    mapped_to: Optional[str] = None     # risk | gap | scope_change | constraint | assumption | None
    confidence: str = "medium"          # high | medium | low
    status: str = "new"                 # new | addressed | deferred | rejected_by_team
    is_critical: bool = False           # auto-flagged or PM-overridden
    addressed_in_version: Optional[str] = None  # proposal_version.version_id where resolved
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id":              self.item_id,
            "text":                 self.text,
            "category":             self.category,
            "mapped_to":            self.mapped_to,
            "confidence":           self.confidence,
            "status":               self.status,
            "is_critical":          self.is_critical,
            "addressed_in_version": self.addressed_in_version,
            "created_at":           self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeedbackItem":
        return cls(
            item_id=d.get("item_id", f"fi_{uuid.uuid4().hex[:8]}"),
            text=d.get("text", ""),
            category=d.get("category", "concerns"),
            mapped_to=d.get("mapped_to"),
            confidence=d.get("confidence", "medium"),
            status=d.get("status", "new"),
            is_critical=bool(d.get("is_critical", False)),
            addressed_in_version=d.get("addressed_in_version"),
            created_at=d.get("created_at", _now()),
        )

    @property
    def is_blocking(self) -> bool:
        """True when this item must be resolved before finalisation."""
        return (
            self.is_critical
            and self.status == "new"
        )


def auto_flag_critical(item: FeedbackItem) -> FeedbackItem:
    """Auto-flag a FeedbackItem as critical based on category + mapped_to.

    Rules (PM can override):
      - change_requested AND mapped_to IN (scope_change, risk)  → critical
      - rejected AND mapped_to IN (scope_change, constraint)    → critical
    """
    if item.category == "change_requested" and item.mapped_to in ("scope_change", "risk"):
        item.is_critical = True
    elif item.category == "rejected" and item.mapped_to in ("scope_change", "constraint"):
        item.is_critical = True
    return item


# ── ProposalVersion ────────────────────────────────────────────

@dataclass
class ProposalVersion:
    """A single version of a client proposal.

    DS-02 adds hard traceability links to the hierarchy:
      hierarchy_version_id → which Build Intelligence snapshot
      active_review_id     → which review this proposal was generated from

    Both are REQUIRED when creating a proposal version (enforced by DS-07 gate).
    """

    version_id: str = ""
    version_number: int = 0
    label: str = ""
    status: str = "draft"               # VALID_PROPOSAL_STATUSES
    created_at: str = field(default_factory=_now)
    files: List[str] = field(default_factory=list)
    notes: str = ""
    changes_from_previous: str = ""     # kept for backward compat
    context_version: str = ""           # kept for backward compat (== hierarchy_version_id)

    # DS-02 traceability (replaces loose context_version string)
    hierarchy_version_id: str = ""      # FK → versions.version_id
    active_review_id: str = ""          # FK → reviews.review_id
    previous_version_id: str = ""       # FK → proposal_versions.version_id
    feedback_applied: List[str] = field(default_factory=list)  # feedback_ids resolved
    changes_summary: str = ""           # human summary of changes made

    # DS-02 quality gate
    quality_status: str = "draft"       # draft | interim | complete
    quality_score: int = 0              # 0–100
    completed_by: str = ""
    completed_at: str = ""

    # DS-02 soft lock
    lock_status: str = "unlocked"       # unlocked | soft_locked
    lock_reason: str = ""

    # P9 backward-compat: summary of feedback (full records in presales_feedback table)
    feedback: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id":            self.version_id,
            "version_number":        self.version_number,
            "label":                 self.label,
            "status":                self.status,
            "created_at":            self.created_at,
            "files":                 self.files,
            "notes":                 self.notes,
            "changes_from_previous": self.changes_from_previous,
            "context_version":       self.context_version,
            "hierarchy_version_id":  self.hierarchy_version_id,
            "active_review_id":      self.active_review_id,
            "previous_version_id":   self.previous_version_id,
            "feedback_applied":      self.feedback_applied,
            "changes_summary":       self.changes_summary,
            "quality_status":        self.quality_status,
            "quality_score":         self.quality_score,
            "completed_by":          self.completed_by,
            "completed_at":          self.completed_at,
            "lock_status":           self.lock_status,
            "lock_reason":           self.lock_reason,
            "feedback":              self.feedback,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProposalVersion":
        return cls(
            version_id=d.get("version_id", ""),
            version_number=d.get("version_number", 0),
            label=d.get("label", ""),
            status=d.get("status", "draft"),
            created_at=d.get("created_at", _now()),
            files=d.get("files", []),
            notes=d.get("notes", ""),
            changes_from_previous=d.get("changes_from_previous", ""),
            context_version=d.get("context_version", ""),
            hierarchy_version_id=d.get("hierarchy_version_id", ""),
            active_review_id=d.get("active_review_id", ""),
            previous_version_id=d.get("previous_version_id", ""),
            feedback_applied=d.get("feedback_applied", []),
            changes_summary=d.get("changes_summary", ""),
            quality_status=d.get("quality_status", "draft"),
            quality_score=d.get("quality_score", 0),
            completed_by=d.get("completed_by", ""),
            completed_at=d.get("completed_at", ""),
            lock_status=d.get("lock_status", "unlocked"),
            lock_reason=d.get("lock_reason", ""),
            feedback=d.get("feedback"),
        )

    @property
    def is_locked(self) -> bool:
        return self.lock_status == "soft_locked"

    @property
    def is_traceable(self) -> bool:
        """True when both required traceability links are set."""
        return bool(self.hierarchy_version_id and self.active_review_id)


# ── ProposalTracker ────────────────────────────────────────────

@dataclass
class ProposalTracker:
    """Tracks all proposal versions for a project."""

    project_id: str = ""
    proposal_name: str = ""
    client: str = ""
    current_version: str = ""
    total_versions: int = 0
    versions: List[ProposalVersion] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


# ── PresalesFeedback ───────────────────────────────────────────

@dataclass
class PresalesFeedback:
    """Feedback captured against a proposal version or review.

    DS-02: primary store is now feedback_items (List[FeedbackItem]).
    The flat accepted/rejected/concerns lists are kept as backward-compat
    computed views — populated from feedback_items on write.
    """

    feedback_id: str = field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:8]}")
    project_id: str = ""
    proposal_ver_id: str = ""
    review_id: str = ""
    source: str = "internal"            # internal | external
    responder_name: str = ""
    responder_email: str = ""

    # DS-02 structured items (primary)
    feedback_items: List[FeedbackItem] = field(default_factory=list)
    raw_text: str = ""                  # original pasted text for hybrid tagger

    # Backward-compat flat views (derived from feedback_items on write)
    accepted: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    change_requested: List[str] = field(default_factory=list)

    notes: str = ""
    next_action: str = ""
    status: str = "open"                # open | actioned | closed
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def sync_flat_views(self) -> None:
        """Recompute backward-compat flat lists from feedback_items."""
        self.accepted         = [i.text for i in self.feedback_items if i.category == "accepted"]
        self.rejected         = [i.text for i in self.feedback_items if i.category == "rejected"]
        self.concerns         = [i.text for i in self.feedback_items if i.category == "concerns"]
        self.change_requested = [i.text for i in self.feedback_items if i.category == "change_requested"]

    def to_dict(self) -> Dict[str, Any]:
        self.sync_flat_views()
        return {
            "feedback_id":     self.feedback_id,
            "project_id":      self.project_id,
            "proposal_ver_id": self.proposal_ver_id,
            "review_id":       self.review_id,
            "source":          self.source,
            "responder_name":  self.responder_name,
            "responder_email": self.responder_email,
            "feedback_items":  [i.to_dict() for i in self.feedback_items],
            "raw_text":        self.raw_text,
            "accepted":        self.accepted,
            "rejected":        self.rejected,
            "concerns":        self.concerns,
            "change_requested": self.change_requested,
            "notes":           self.notes,
            "next_action":     self.next_action,
            "status":          self.status,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
        }

    @property
    def blocking_items(self) -> List[FeedbackItem]:
        """Items that block finalisation."""
        return [i for i in self.feedback_items if i.is_blocking]

    @property
    def new_items(self) -> List[FeedbackItem]:
        """Items not yet addressed."""
        return [i for i in self.feedback_items if i.status == "new"]


# ── ProposalDocument ───────────────────────────────────────────

@dataclass
class GanttRow:
    """One row in the Gantt chart."""
    milestone: str = ""
    start_week: int = 1
    end_week: int = 2
    owner: str = ""
    phase: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone":  self.milestone,
            "start_week": self.start_week,
            "end_week":   self.end_week,
            "owner":      self.owner,
            "phase":      self.phase,
        }


@dataclass
class RiskEntry:
    """A single classified risk."""
    risk: str = ""
    category: str = ""          # technical | delivery | commercial | resource | external
    impact: str = "medium"      # high | medium | low
    probability: str = "medium" # high | medium | low
    mitigation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk":        self.risk,
            "category":    self.category,
            "impact":      self.impact,
            "probability": self.probability,
            "mitigation":  self.mitigation,
        }


@dataclass
class AssumptionEntry:
    """A single assumption, categorised by type."""
    assumption: str = ""
    category: str = ""  # delivery | resource | technical | process | organizational | existing_env | client

    def to_dict(self) -> Dict[str, Any]:
        return {"assumption": self.assumption, "category": self.category}


@dataclass
class DeliveryPhase:
    """A high-level delivery phase."""
    phase: str = ""
    description: str = ""
    duration_weeks: int = 0
    milestones: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase":          self.phase,
            "description":    self.description,
            "duration_weeks": self.duration_weeks,
            "milestones":     self.milestones,
        }


@dataclass
class ProposalDocument:
    """A generated proposal document derived from Version + Active Review.

    All sections are populated either by the LLM (AI mode) or by
    template extraction from review findings (files_only mode).
    """

    doc_id: str = field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    project_id: str = ""
    proposal_ver_id: str = ""
    generated_at: str = field(default_factory=_now)
    ai_backend: str = "files_only"

    # Traceability
    hierarchy_version_id: str = ""
    active_review_id: str = ""
    version_label: str = ""
    review_persona: str = ""

    # ── Document Sections ──────────────────────────────────────
    exec_summary: str = ""
    scope: str = ""                                              # scope statement
    delivery_phases: List[DeliveryPhase] = field(default_factory=list)
    gantt_data: List[GanttRow] = field(default_factory=list)
    risks: List[RiskEntry] = field(default_factory=list)
    assumptions: List[AssumptionEntry] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    responsibilities: Dict[str, Any] = field(default_factory=dict)  # RACI matrix
    acceptance_criteria: List[str] = field(default_factory=list)

    # Metadata
    word_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id":               self.doc_id,
            "project_id":           self.project_id,
            "proposal_ver_id":      self.proposal_ver_id,
            "generated_at":         self.generated_at,
            "ai_backend":           self.ai_backend,
            "hierarchy_version_id": self.hierarchy_version_id,
            "active_review_id":     self.active_review_id,
            "version_label":        self.version_label,
            "review_persona":       self.review_persona,
            "exec_summary":         self.exec_summary,
            "scope":                self.scope,
            "delivery_phases":      [p.to_dict() for p in self.delivery_phases],
            "gantt_data":           [g.to_dict() for g in self.gantt_data],
            "risks":                [r.to_dict() for r in self.risks],
            "assumptions":          [a.to_dict() for a in self.assumptions],
            "exclusions":           self.exclusions,
            "responsibilities":     self.responsibilities,
            "acceptance_criteria":  self.acceptance_criteria,
            "word_count":           self.word_count,
        }
