"""Reconciliation Models — Sprint 3.

Defines the data shapes for:
- ReconciliationSelection  : user's explicit review selection (anchor + supplemental)
- ReconciliationInput      : normalised reviews ready for reconciliation
- ProvenanceRef            : lightweight source citation carried through reconciliation
- ReconciledItem           : a single reconciled finding/weakness/decision with provenance
- ReconciliationOutput     : full reconciliation result (consensus, divergent, decisions, weaknesses)

Design rules (from architecture):
- Traceability first — every important output item carries its source review(s)
- No auto-selection: anchor_review_id and selected_review_ids are always explicit
- Deterministic before LLM: output is structurally computed, not generated
- Backward-compatible: missing fields default safely
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Categories reconciled across reviews ─────────────────────────────────────

RECONCILABLE_CATEGORIES = (
    "risks",
    "assumptions",
    "dependencies",
    "constraints",
    "action_items",
    "weaknesses",
    "decision_points",
)


# ──────────────────────────────────────────────────────────────────────────────
# ReconciliationSelection
# Persisted on the Version: explicit user choice, never auto-populated.
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ReconciliationSelection:
    """User's explicit review selection for reconciliation preparation.

    Rules:
    - anchor_review_id    : required — the primary truth review
    - selected_review_ids : all reviews in the reconciliation (must include anchor)
    - Never auto-populated from "latest N reviews"
    - Active Review may be pre-populated as anchor in UI but user must confirm
    """

    version_id: str = ""
    project_id: str = ""
    anchor_review_id: str = ""
    selected_review_ids: List[str] = field(default_factory=list)
    selected_at: str = ""
    selected_by: str = ""  # optional — who made the selection

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReconciliationSelection":
        return cls(
            version_id=d.get("version_id", ""),
            project_id=d.get("project_id", ""),
            anchor_review_id=d.get("anchor_review_id", ""),
            selected_review_ids=d.get("selected_review_ids", []),
            selected_at=d.get("selected_at", ""),
            selected_by=d.get("selected_by", ""),
        )


# ──────────────────────────────────────────────────────────────────────────────
# ProvenanceRef
# Lightweight source citation — attached to reconciled items.
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ProvenanceRef:
    """Lightweight provenance citation for a reconciled item.

    Carried from the source review(s) so later proposal / UI steps can display
    "this finding came from review r3 (Solution Architect), artifact arch.docx §2".
    Not required to be complete — missing fields degrade gracefully.
    """

    review_id: str = ""
    review_persona: str = ""
    is_anchor: bool = False           # True when this review is the anchor
    artifact_id: str = ""             # optional artifact link
    artifact_name: str = ""
    section_reference: str = ""       # optional section within artifact

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceRef":
        return cls(
            review_id=d.get("review_id", ""),
            review_persona=d.get("review_persona", ""),
            is_anchor=bool(d.get("is_anchor", False)),
            artifact_id=d.get("artifact_id", ""),
            artifact_name=d.get("artifact_name", ""),
            section_reference=d.get("section_reference", ""),
        )


# ──────────────────────────────────────────────────────────────────────────────
# ReconciledItem
# A single item in the reconciliation output with its provenance.
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ReconciledItem:
    """One reconciled finding, decision, or weakness with lightweight provenance.

    id            : stable identifier within the reconciliation output
    text          : canonical text (de-duplicated, from anchor where conflict)
    category      : source category (risks / assumptions / decision_points / …)
    status        : inherited status if available (open / accepted / addressed / …)
    source_reviews: ProvenanceRef list — all reviews that contributed this item
    anchor_text   : the anchor review's exact text (preserved for fidelity)
    supplemental_texts: texts from supplemental reviews (for divergence display)
    """

    id: str = ""
    text: str = ""
    category: str = ""
    status: str = ""
    source_reviews: List[Dict[str, Any]] = field(default_factory=list)
    anchor_text: str = ""
    supplemental_texts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReconciledItem":
        return cls(
            id=d.get("id", ""),
            text=d.get("text", ""),
            category=d.get("category", ""),
            status=d.get("status", ""),
            source_reviews=d.get("source_reviews", []),
            anchor_text=d.get("anchor_text", ""),
            supplemental_texts=d.get("supplemental_texts", []),
        )


# ──────────────────────────────────────────────────────────────────────────────
# ReconciliationInput
# Normalised reviews prepared for reconciliation (not persisted, used in-memory).
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NormalisedReviewInput:
    """One review normalised for reconciliation processing.

    Built from a Review dataclass before reconciliation runs.
    """

    review_id: str = ""
    version_id: str = ""
    persona: str = ""
    is_anchor: bool = False
    findings: Dict[str, List[str]] = field(default_factory=dict)
    weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    artifact_refs: List[Dict[str, Any]] = field(default_factory=list)
    # lineage
    previous_review_id: str = ""
    created_at: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# ReconciliationOutput
# The full result of a reconciliation run — proposal-ready intelligence pack.
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ReconciliationOutput:
    """Full reconciliation result.

    Sections:
    - consensus_points      : items that appear (with high similarity) across all selected reviews
    - divergent_points      : items where reviews differ — conflict preserved with per-review text
    - confirmed_decisions   : decision_points with status != 'open' across selected reviews
    - open_decisions        : decision_points still open in at least one review
    - unresolved_weaknesses : weaknesses still 'open' across selected reviews
    - merged_findings       : de-duplicated flat list of all findings (all categories)
    - provenance_summary    : per-review summary (review_id, persona, is_anchor, item_count)

    Invariants:
    - anchor_review_id is always recorded
    - selected_review_ids always recorded (includes anchor)
    - reconciliation_id is stable (generated at creation)
    - created_at is set once and never updated
    - Each item in the above lists is a ReconciledItem dict with source_reviews provenance
    """

    reconciliation_id: str = ""
    project_id: str = ""
    version_id: str = ""
    anchor_review_id: str = ""
    selected_review_ids: List[str] = field(default_factory=list)
    created_at: str = ""

    # ── Core reconciliation sections ─────────────────────────
    consensus_points: List[Dict[str, Any]] = field(default_factory=list)
    divergent_points: List[Dict[str, Any]] = field(default_factory=list)
    confirmed_decisions: List[Dict[str, Any]] = field(default_factory=list)
    open_decisions: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_weaknesses: List[Dict[str, Any]] = field(default_factory=list)
    merged_findings: List[Dict[str, Any]] = field(default_factory=list)

    # ── Provenance summary (per-review metadata) ──────────────
    provenance_summary: List[Dict[str, Any]] = field(default_factory=list)

    # ── Meta ──────────────────────────────────────────────────
    # anchor_only = True when no supplemental reviews were selected
    anchor_only: bool = False
    # counts for quick display
    total_consensus: int = 0
    total_divergent: int = 0
    total_open_decisions: int = 0
    total_unresolved_weaknesses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Recompute summary counts from lists (defensive — always accurate)
        d["total_consensus"]            = len(self.consensus_points)
        d["total_divergent"]            = len(self.divergent_points)
        d["total_open_decisions"]       = len(self.open_decisions)
        d["total_unresolved_weaknesses"]= len(self.unresolved_weaknesses)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReconciliationOutput":
        return cls(
            reconciliation_id=d.get("reconciliation_id", ""),
            project_id=d.get("project_id", ""),
            version_id=d.get("version_id", ""),
            anchor_review_id=d.get("anchor_review_id", ""),
            selected_review_ids=d.get("selected_review_ids", []),
            created_at=d.get("created_at", ""),
            consensus_points=d.get("consensus_points", []),
            divergent_points=d.get("divergent_points", []),
            confirmed_decisions=d.get("confirmed_decisions", []),
            open_decisions=d.get("open_decisions", []),
            unresolved_weaknesses=d.get("unresolved_weaknesses", []),
            merged_findings=d.get("merged_findings", []),
            provenance_summary=d.get("provenance_summary", []),
            anchor_only=d.get("anchor_only", False),
            total_consensus=d.get("total_consensus", 0),
            total_divergent=d.get("total_divergent", 0),
            total_open_decisions=d.get("total_open_decisions", 0),
            total_unresolved_weaknesses=d.get("total_unresolved_weaknesses", 0),
        )
